import ollama
import json
import os
from dotenv import load_dotenv
from . import tools
from .models import ChatLog
from sqlalchemy.orm import Session

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '../backend/.env'))

MODEL = os.getenv("OLLAMA_MODEL", "llama3:8b-instruct")
HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
MAX_STEPS = int(os.getenv("MAX_AGENT_STEPS", "10"))

with open(os.path.join(os.path.dirname(__file__), 'leyes.txt'), "r") as f:
    SYSTEM_PROMPT = f.read()

TOOL_MAP = {
    "execute_shell": tools.execute_shell,
    "file_manager": tools.file_manager,
}

async def run_agent_loop(goal: str, websocket, db_session: Session):
    client = ollama.AsyncClient(host=HOST)
    history = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": goal}]
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
            if tool_name in TOOL_MAP:
                observation = await TOOL_MAP[tool_name](params['command']) if tool_name == "execute_shell" else await TOOL_MAP[tool_name](params['action'], params['path'], params.get('content'))
            else:
                observation = "Tool not found."
        else:
            observation = "No action specified."
        await websocket.send_text(json.dumps({"role": "agent-action", "content": observation}))
        db_session.add(ChatLog(role="agent-action", content=observation))
        db_session.commit()
        history.extend([{"role": "assistant", "content": json.dumps(thought_action)}, {"role": "user", "content": observation}])