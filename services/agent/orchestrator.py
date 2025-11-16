import ollama
import json
import os
from dotenv import load_dotenv
from ..tools import tools
from ..database.models import ChatLog
from sqlalchemy.orm import Session

load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'backend', '.env'))

MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
MAX_STEPS = int(os.getenv("MAX_AGENT_STEPS", "10"))

with open(os.path.join(os.path.dirname(__file__), 'leyes.txt'), "r") as f:
    SYSTEM_PROMPT = f.read()

TOOL_MAP = {
    "execute_shell": tools.execute_shell,
    "file_manager": tools.file_manager,
    "store_credential": tools.store_credential,
    "get_credential": tools.get_credential,
}

async def run_agent_loop(goal: str, websocket, db_session: Session):
    client = ollama.AsyncClient(host=HOST)
    history = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": goal}]
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
        await websocket.send_text(json.dumps({"role": "agent-thought", "content": thought}))
        db_session.add(ChatLog(role="agent-thought", content=thought))
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
                    if tool_name == "execute_shell":
                        cmd = params.get('command', '')
                        if cmd:
                            observation = await TOOL_MAP[tool_name](cmd)
                        else:
                            observation = "Invalid parameters: missing command"
                    elif tool_name == "file_manager":
                        act = params.get('action', '')
                        path = params.get('path', '')
                        content = params.get('content', '')
                        if act and path:
                            observation = await TOOL_MAP[tool_name](act, path, content)
                        else:
                            observation = "Invalid parameters: missing action or path"
                    elif tool_name in ["store_credential", "get_credential"]:
                        key = params.get('key', '')
                        if key:
                            if tool_name == "store_credential":
                                value = params.get('value', '')
                                observation = await TOOL_MAP[tool_name](key, value) if value else "Invalid parameters: missing value"
                            else:
                                observation = await TOOL_MAP[tool_name](key)
                        else:
                            observation = "Invalid parameters: missing key"
                    else:
                        observation = "Unknown tool"
            else:
                observation = "Tool not found."
            recent_signatures.append(signature)
            if len(recent_signatures) > 6:
                recent_signatures.pop(0)
        else:
            observation = "No action specified."
        await websocket.send_text(json.dumps({"role": "agent-action", "content": observation}))
        db_session.add(ChatLog(role="agent-action", content=observation))
        db_session.commit()
        history.extend([{"role": "assistant", "content": json.dumps(thought_action)}, {"role": "user", "content": observation}])