import ollama
import json
import inspect
import asyncio
import traceback
import os
from sqlalchemy.orm import Session

from ..tools import registry
from ..tools.custom.planner import manage_plan
from ..tools.custom import git_ops
from ..database.models import ChatLog
from backend.config import settings
from backend.logger import logger
from . import prompts
from .models import AgentResponse


class Agent:
    # Use centralized settings
    MAX_CONSECUTIVE_FAILURES = settings.MAX_CONSECUTIVE_FAILURES
    MAX_CONSECUTIVE_LOOPS = settings.MAX_CONSECUTIVE_LOOPS
    SIGNATURE_HISTORY_SIZE = settings.SIGNATURE_HISTORY_SIZE
    
    def __init__(self, db_session: Session, websocket=None, conversation_id: int = None):
        self.db_session = db_session
        self.websocket = websocket
        self.conversation_id = conversation_id
        self.client = ollama.AsyncClient(host=settings.OLLAMA_HOST)
        self.tool_map = {}
        self.recent_signatures = []
        self.history = []
        self.consecutive_failures = 0
        self.consecutive_plain_replies = 0
        self.consecutive_loops = 0

    async def initialize(self, goal: str):
        if self.websocket:
            await self._send("system", "Agent starting...")

        self.tool_map = registry.get_tool_map()
        system_prompt = prompts.get_system_prompt()
        self.history = [{"role": "system", "content": system_prompt}]

        if self.conversation_id:
            self._load_history_from_db()
        else:
            self.history.append({"role": "user", "content": goal})

    def _load_history_from_db(self):
        logs = self.db_session.query(ChatLog).filter(
            ChatLog.conversation_id == self.conversation_id
        ).order_by(ChatLog.timestamp).all()
        
        for log in logs:
            role = "user" if log.role == "user" else "assistant"
            if log.role == "agent-thought":
                content = json.dumps({"thought": log.content, "action": {}})
                self.history.append({"role": "assistant", "content": content})
            elif log.role == "agent-action":
                self.history.append({"role": "user", "content": log.content})
            else:
                self.history.append({"role": role, "content": log.content})

    async def _send(self, role, content):
        if self.websocket:
            await self.websocket.send_text(json.dumps({"role": role, "content": content}))

    async def _log(self, role, content):
        await self._send(role, content)
        self.db_session.add(ChatLog(role=role, content=content, conversation_id=self.conversation_id))
        self.db_session.commit()

    async def _get_llm_response(self, current_history):
        try:
            if self.websocket:
                await self._send("agent-thought", "Thinking...")

            response = await asyncio.wait_for(
                self.client.chat(model=settings.MODEL_FAST, messages=current_history, format="json"),
                timeout=120.0
            )
            return response
        except asyncio.TimeoutError:
            error_msg = f"Error: AI Model ({settings.MODEL_FAST}) timed out."
            logger.error(error_msg)
            await self._send("agent-action", error_msg)
            raise Exception(error_msg)
        except Exception as e:
            error_msg = f"CRITICAL: Could not connect to AI Model. Details: {e}"
            logger.error(error_msg)
            await self._send("agent-action", error_msg)
            raise Exception(error_msg)

    async def _generate_new_tool_code(self, tool_name, params):
        system_prompt = prompts.get_tool_generation_system_prompt()
        user_prompt = prompts.get_tool_generation_user_prompt(tool_name, params)
        
        try:
            response = await self.client.chat(model=settings.MODEL_CODING, messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ])
            code = response['message']['content']
            if "```python" in code:
                code = code.split("```python")[1].split("```")[0].strip()
            elif "```" in code:
                code = code.split("```")[1].split("```")[0].strip()
            return code
        except Exception as e:
            logger.error(f"Failed to generate tool code: {e}")
            return None

    async def _execute_tool(self, action):
        if not (isinstance(action, dict) and 'name' in action):
            self.consecutive_empty_actions = getattr(self, 'consecutive_empty_actions', 0) + 1
            if self.consecutive_empty_actions > 2:
                return "FORCE_STOP: No puedo procesar esta solicitud. Intenta de nuevo con una petición más específica."
            return "No action specified."
        
        self.consecutive_empty_actions = 0
        tool_name = action['name']
        params = action.get('parameters', {})
        signature = json.dumps({"tool": tool_name, "params": params}, sort_keys=True)
        
        if tool_name not in self.tool_map:
            # DISABLED: Dynamic tool generation is unreliable
            # Instead, tell the agent to use existing tools
            available = ", ".join(sorted(self.tool_map.keys())[:15])
            return f"Tool '{tool_name}' does not exist. Use an existing tool. Available: {available}... Use 'reply_to_user' if you cannot complete the task."

        if signature in self.recent_signatures[-2:]:
            self.consecutive_loops += 1
            if self.consecutive_loops > self.MAX_CONSECUTIVE_LOOPS:
                return "CRITICAL: Infinite Loop Detected. Use 'reply_to_user' tool immediately."
            return "Loop detected: same action attempted. Change strategy."
        
        self.consecutive_loops = 0
        
        func = self.tool_map[tool_name]
        try:
            sig = inspect.signature(func)
            call_params = params.copy()
            if 'websocket' in sig.parameters:
                call_params['websocket'] = self.websocket

            if inspect.iscoroutinefunction(func):
                observation = await func(**call_params)
            else:
                observation = func(**call_params)
        except TypeError as e:
            observation = f"Error calling tool '{tool_name}': {e}. Check parameters."
        except Exception as e:
            observation = f"Tool execution error: {e}"
        
        self.recent_signatures.append(signature)
        if len(self.recent_signatures) > self.SIGNATURE_HISTORY_SIZE:
            self.recent_signatures.pop(0)
            
        return observation

    async def _handle_dynamic_tool_creation(self, tool_name, params):
        await self._send("agent-action", f"Tool '{tool_name}' not found. Generating...")
        
        code = await self._generate_new_tool_code(tool_name, params)
        if not code:
            return f"Failed to generate code for tool '{tool_name}'."
        
        tool_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tools", "custom", f"{tool_name}.py")
        
        if "import " not in code:
            code = "import asyncio\nimport os\nimport json\n\n" + code
        
        with open(tool_path, "w") as f:
            f.write(code)
        
        await self._send("agent-action", f"Evolution complete. Learned: {tool_name}. Reloading...")
        self.tool_map = registry.get_tool_map()
        
        if tool_name in self.tool_map:
            func = self.tool_map[tool_name]
            try:
                if inspect.iscoroutinefunction(func):
                    return await func(**params)
                else:
                    return func(**params)
            except Exception as e:
                return f"Error executing newly created tool '{tool_name}': {e}"
        
        return f"Failed to load generated tool '{tool_name}'."

    async def run(self, goal: str):
        await self.initialize(goal)
        
        is_chitchat = len(goal.split()) < 5 and not any(x in goal.lower() for x in ['fix', 'create', 'run', 'check', 'test', 'deploy'])
        
        total_failures = 0  # Global failure counter
        MAX_TOTAL_FAILURES = 10  # Hard stop after this many failures
        
        for step in range(settings.MAX_AGENT_STEPS):
            # CIRCUIT BREAKER: Force stop if too many failures
            if total_failures >= MAX_TOTAL_FAILURES:
                await self._log("assistant", "Lo siento, no puedo completar esta tarea con las herramientas disponibles. Por favor, reformula tu solicitud.")
                return
            
            current_history = self.history.copy()
            
            if not is_chitchat:
                try:
                    plan_status = await manage_plan("read")
                except Exception as e:
                    plan_status = f"Error reading plan: {e}"
                reminder = f"CURRENT PLAN STATUS:\n{plan_status}\n\nFocus on the ACTIVE step."
                current_history.append({"role": "system", "content": reminder})
            
            if len(self.history) > 2:
                last_msg = self.history[-1]["content"]
                if any(x in last_msg for x in ["Error", "Exception", "Failed"]):
                    current_history.append({"role": "system", "content": prompts.get_recovery_prompt()})
            
            await asyncio.sleep(0.1)
            
            try:
                response = await self._get_llm_response(current_history)
            except Exception:
                return

            try:
                content = response['message']['content']
                parsed = AgentResponse.from_llm_response(content)
            except Exception as e:
                self.consecutive_failures += 1
                logger.error(f"Response parsing error: {e}")
                if self.consecutive_failures > self.MAX_CONSECUTIVE_FAILURES:
                    await self._send("system", "CRITICAL: Too many errors. Stopping.")
                    return
                continue
            
            self.consecutive_failures = 0
            thought = parsed.thought
            action = {"name": parsed.action.name, "parameters": parsed.action.parameters} if parsed.action else {}
            
            if thought:
                await self._send("agent-thought", thought)
                await self._send("terminal-output", json.dumps({"type": "thought", "content": thought}))

            if not action or not action.get('name'):
                continue

            if action.get('name') == 'task_complete':
                await self._log("agent-action", "Task Completed.")
                return

            if action.get('name') == 'reply_to_user':
                self.consecutive_plain_replies += 1
                message = action.get('parameters', {}).get('message', '')
                await self._log("assistant", message)
                return
            else:
                self.consecutive_plain_replies = 0
                observation = await self._execute_tool(action)
                
                # FORCE STOP: Check for critical loop/failure signals
                if observation and ("FORCE_STOP" in str(observation) or "CRITICAL" in str(observation)):
                    await self._log("assistant", "No puedo continuar con esta tarea. Por favor, reformula tu solicitud o proporciona más contexto.")
                    return
                
                # Check consecutive loops threshold
                if self.consecutive_loops > self.MAX_CONSECUTIVE_LOOPS:
                    await self._log("assistant", "He detectado un bucle repetitivo. Detengo para evitar ciclos infinitos. Por favor, intenta con una solicitud diferente.")
                    return
                
                # Count failures
                if observation and any(x in str(observation) for x in ["Error", "CRITICAL", "Failed", "does not exist", "Loop detected"]):
                    total_failures += 1
                
                tool_name = action.get('name')
                cmd_display = f"{tool_name} {json.dumps(action.get('parameters', {}))}"
                if tool_name == 'execute_shell':
                    cmd_display = action.get('parameters', {}).get('command', cmd_display)
                elif tool_name == 'run_command':
                    cmd_display = action.get('parameters', {}).get('CommandLine', cmd_display)
                
                await self._send("terminal-output", json.dumps({
                    "type": "command",
                    "command": cmd_display,
                    "output": str(observation)
                }))
                
                await self._log("agent-action", f"Executed {tool_name}")

            if isinstance(action, dict) and action.get('name') == 'manage_plan' and self.websocket:
                await self._broadcast_plan_update()

            self.history.extend([
                {"role": "assistant", "content": json.dumps({"thought": thought, "action": action})},
                {"role": "user", "content": str(observation)}
            ])
            
            await asyncio.sleep(2.0)

    async def _broadcast_plan_update(self):
        try:
            root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            plan_file = os.path.join(root_dir, "plan.json")
            if os.path.exists(plan_file):
                with open(plan_file, 'r') as f:
                    plan_data = json.load(f)
                    tasks = plan_data.get("tasks", [])
                    idx = plan_data.get("current_step_index", 0)
                    plan_md = ""
                    for i, task in enumerate(tasks):
                        status = "[x]" if task["status"] == "completed" else "[ ]"
                        plan_md += f"- {status} {task['description']}\n"
                    
                    await self._send("system", {"type": "plan_update", "content": plan_md})
        except Exception as e:
            logger.error(f"Failed to broadcast plan update: {e}")


async def run_agent_loop(goal: str, db_session: Session, websocket=None, conversation_id: int = None):
    try:
        agent = Agent(db_session, websocket, conversation_id)
        await agent.run(goal)
    except Exception as e:
        error_trace = traceback.format_exc()
        logger.error(f"FATAL AGENT ERROR: {error_trace}")
        if websocket:
            await websocket.send_text(json.dumps({"role": "agent-action", "content": f"FATAL ERROR: {e}"}))