import ollama
import json
import os
import inspect
from dotenv import load_dotenv
from ..tools import registry
from ..tools.custom.planner import manage_plan
from ..tools.custom import git_ops
from ..database.models import ChatLog, SystemLog
from sqlalchemy.orm import Session

load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'backend', '.env'))

# Use the FAST model for routing/orchestration
MODEL = os.getenv("MODEL_FAST", "llama3.1:8b")
HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
MAX_STEPS = int(os.getenv("MAX_AGENT_STEPS", "10"))

# Simplified System Prompt for the Router
ROUTER_SYSTEM_PROMPT = """You are the Skynet Interface. 
You do NOT write complex code or plans yourself. 
You route tasks to your expert tools. 
- If the user asks for a feature or complex goal, call 'manage_plan' with action='create'.
- If they ask for a fix or code change, call 'run_safe_edit' (which uses the Coding Expert).
- IMPORTANT: Before applying any critical code change, you SHOULD call 'review_code_changes'.
- If they ask for simple info, use 'execute_shell' or 'browser_use'.

Respond in exact JSON: {"thought": "reasoning", "action": {"name": "tool_name", "parameters": {"arg1": "value1"}}} or {"thought": "reasoning", "action": {"name": "task_complete"}}
Ensure you provide ALL required parameters for the tools as defined in the Tools list.
"""

async def run_agent_loop(goal: str, db_session: Session, websocket=None, conversation_id: int = None):
    try:
        if websocket:
            await websocket.send_text(json.dumps({"role": "system", "content": "Agent starting..."}))

        client = ollama.AsyncClient(host=HOST)
        
        try:
            TOOL_MAP = registry.get_tool_map()
            TOOLS_PROMPT = registry.get_tools_prompt()
        except Exception as e:
            error_msg = f"Error loading tools: {str(e)}"
            print(error_msg)
            if websocket:
                await websocket.send_text(json.dumps({"role": "agent-action", "content": error_msg}))
            return
        
        SYSTEM_PROMPT = ROUTER_SYSTEM_PROMPT + "\n\n" + TOOLS_PROMPT
        
        history = [{"role": "system", "content": SYSTEM_PROMPT}]
        
        if conversation_id:
            logs = db_session.query(ChatLog).filter(ChatLog.conversation_id == conversation_id).order_by(ChatLog.timestamp).all()
            for log in logs:
                role = "user" if log.role == "user" else "assistant"
                if log.role == "agent-thought":
                    content = json.dumps({"thought": log.content, "action": {}})
                    history.append({"role": "assistant", "content": content})
                elif log.role == "agent-action":
                    history.append({"role": "user", "content": log.content})
                else:
                    history.append({"role": role, "content": log.content})
        else:
            history.append({"role": "user", "content": goal})

        recent_signatures = []
        
        for step in range(MAX_STEPS):
            # Inject Plan Status
            try:
                plan_status = await manage_plan("read")
            except Exception as e:
                plan_status = f"Error reading plan: {e}"

            reminder = f"CURRENT PLAN STATUS:\n{plan_status}\n\nFocus on the ACTIVE step. Use manage_plan to update status when done."
            
            current_history = history.copy()
            current_history.append({"role": "system", "content": reminder})
            
            # Error Recovery Injection
            if len(history) > 2:
                last_msg = history[-1]["content"]
                if any(x in last_msg for x in ["Error", "Exception", "Failed", "FAILED"]):
                    recovery_prompt = "System Alert: Previous action failed. You MUST use `attempt_fix` (for code errors) or `learn_tech` (for missing knowledge) to resolve this before asking the user. Do not apologize, just fix it."
                    current_history.append({"role": "system", "content": recovery_prompt})
            
            # Prevent CPU lockup
            await asyncio.sleep(0.5)
            
            try:
                response = await client.chat(model=MODEL, messages=current_history, format="json")
            except Exception as e:
                error_msg = f"CRITICAL ERROR: Could not connect to AI Model ({MODEL}). Is Ollama running? Details: {str(e)}"
                print(error_msg)
                if websocket:
                    await websocket.send_text(json.dumps({"role": "agent-action", "content": error_msg}))
                return

            try:
                thought_action = json.loads(response['message']['content'])
            except json.JSONDecodeError:
                error_msg = "Error: Invalid JSON response from LLM"
                if websocket:
                    await websocket.send_text(json.dumps({"role": "agent-action", "content": error_msg}))
                return
                
            thought = thought_action.get('thought', '')
            action = thought_action.get('action', {})
            
            if websocket:
                await websocket.send_text(json.dumps({"role": "agent-thought", "content": thought}))
            db_session.add(ChatLog(role="agent-thought", content=thought, conversation_id=conversation_id))
            db_session.commit()
            
            if action.get('name') == 'task_complete':
                # Auto-commit logic
                commit_hash = None
                try:
                    repo = git_ops.get_repo()
                    if repo.is_dirty(untracked_files=True):
                        # Generate commit message
                        commit_prompt = f"Generate a concise git commit message (max 50 chars) for the following task: {goal}. Output ONLY the message."
                        commit_resp = await client.chat(model=MODEL, messages=[{"role": "user", "content": commit_prompt}])
                        commit_msg = commit_resp['message']['content'].strip().replace('"', '')
                        
                        # Execute commit
                        result = git_ops.git_commit(commit_msg)
                        if "Committed successfully" in result:
                            # Extract hash from result string "[hash] message"
                            import re
                            match = re.search(r'\[(.*?)\]', result)
                            if match:
                                commit_hash = match.group(1)
                            
                            # Log commit action
                            if websocket:
                                await websocket.send_text(json.dumps({"role": "agent-action", "content": f"Auto-Commit: {result}"}))
                except Exception as e:
                    print(f"Auto-commit failed: {e}")

                # Log success
                db_session.add(SystemLog(
                    type="SUCCESS",
                    title="Task Completed",
                    description=f"Goal: {goal[:50]}... completed.",
                    commit_hash=commit_hash
                ))
                db_session.commit()
                break
                
            if 'name' in action and 'parameters' in action:
                tool_name = action['name']
                params = action['parameters']
                signature = json.dumps({"tool": tool_name, "params": params}, sort_keys=True)
                
                if tool_name in TOOL_MAP:
                    if signature in recent_signatures[-2:]:
                        observation = "Loop detected: you just attempted the same action. Change strategy or gather missing resources before retrying."
                    else:
                        func = TOOL_MAP[tool_name]
                        try:
                            if inspect.iscoroutinefunction(func):
                                observation = await func(**params)
                            else:
                                observation = func(**params)
                        except TypeError as e:
                            observation = f"Error calling tool '{tool_name}': {str(e)}. Check your parameters. Ensure you are providing all required arguments."
                        except Exception as e:
                            observation = f"Tool execution error: {str(e)}"
                else:
                    observation = f"Tool '{tool_name}' not found. Available tools: {list(TOOL_MAP.keys())}"
                
                recent_signatures.append(signature)
                if len(recent_signatures) > 6:
                    recent_signatures.pop(0)
            else:
                observation = "No action specified."
                
            if websocket:
                await websocket.send_text(json.dumps({"role": "agent-action", "content": observation}))
            db_session.add(ChatLog(role="agent-action", content=observation, conversation_id=conversation_id))
            db_session.commit()
            
            history.extend([{"role": "assistant", "content": json.dumps(thought_action)}, {"role": "user", "content": observation}])
            
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"FATAL AGENT ERROR: {error_trace}")
        if websocket:
            await websocket.send_text(json.dumps({"role": "agent-action", "content": f"FATAL AGENT ERROR: {str(e)}"}))