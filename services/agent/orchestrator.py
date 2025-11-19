import ollama
import json
import os
import inspect
from dotenv import load_dotenv
from ..tools import registry
from ..database.models import ChatLog
from sqlalchemy.orm import Session

load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'backend', '.env'))

MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
MAX_STEPS = int(os.getenv("MAX_AGENT_STEPS", "10"))

with open(os.path.join(os.path.dirname(__file__), 'leyes.txt'), "r") as f:
    BASE_SYSTEM_PROMPT = f.read()

async def run_agent_loop(goal: str, websocket, db_session: Session, conversation_id: int = None):
    client = ollama.AsyncClient(host=HOST)
    
    # Dynamic Tool Loading
    # We reload tools at the start of each loop to pick up any new tools created in the previous run
    TOOL_MAP = registry.get_tool_map()
    TOOLS_PROMPT = registry.get_tools_prompt()
    
    # Combine Base Laws with Dynamic Tools
    SYSTEM_PROMPT = BASE_SYSTEM_PROMPT + "\n\n" + TOOLS_PROMPT
    
    # Build history from DB
    history = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    if conversation_id:
        logs = db_session.query(ChatLog).filter(ChatLog.conversation_id == conversation_id).order_by(ChatLog.timestamp).all()
        for log in logs:
            # Map DB roles to LLM roles
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
        response = await client.chat(model=MODEL, messages=history, format="json")
        try:
            thought_action = json.loads(response['message']['content'])
        except json.JSONDecodeError:
            await websocket.send_text(json.dumps({"role": "agent-action", "content": "Error: Invalid JSON response from LLM"}))
            return
            
        thought = thought_action.get('thought', '')
        action = thought_action.get('action', {})
        
        # Send thought
        await websocket.send_text(json.dumps({"role": "agent-thought", "content": thought}))
        db_session.add(ChatLog(role="agent-thought", content=thought, conversation_id=conversation_id))
        db_session.commit()
        
        if action.get('name') == 'task_complete':
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
                        # Dynamic execution
                        if inspect.iscoroutinefunction(func):
                            observation = await func(**params)
                        else:
                            observation = func(**params)
                    except TypeError as e:
                        observation = f"Error calling tool '{tool_name}': {str(e)}. Check your parameters."
                    except Exception as e:
                        observation = f"Tool execution error: {str(e)}"
            else:
                observation = f"Tool '{tool_name}' not found. Available tools: {list(TOOL_MAP.keys())}"
            
            recent_signatures.append(signature)
            if len(recent_signatures) > 6:
                recent_signatures.pop(0)
        else:
            observation = "No action specified."
            
        # Send action result
        await websocket.send_text(json.dumps({"role": "agent-action", "content": observation}))
        db_session.add(ChatLog(role="agent-action", content=observation, conversation_id=conversation_id))
        db_session.commit()
        
        history.extend([{"role": "assistant", "content": json.dumps(thought_action)}, {"role": "user", "content": observation}])