import os
import sys
import importlib.util
import inspect
import json
from . import tools
from backend.logger import logger

BASE_TOOLS = {
    "execute_shell": tools.execute_shell,
    "file_manager": tools.file_manager,
    "store_credential": tools.store_credential,
    "get_credential": tools.get_credential,
    "task_complete": lambda: "Task Completed",
    "reply_to_user": lambda message: f"Replied: {message}",
}

BASE_TOOLS_METADATA = {
    "execute_shell": {
        "params": {"command": "<string>", "websocket": "<object> (optional)"},
        "description": "Execute shell commands on the system."
    },
    "file_manager": {
        "params": {"action": "<string> (read, write, create, create_dir, list)", "path": "<string>", "content": "<string> (optional)"},
        "description": "Read, write, and manage files and directories."
    },
    "store_credential": {
        "params": {"key": "<string>", "value": "<string>"},
        "description": "Securely store a credential in the vault."
    },
    "get_credential": {
        "params": {"key": "<string>"},
        "description": "Retrieve a credential from the vault."
    },
    "task_complete": {
        "params": {},
        "description": "Signal that the assigned task is fully completed."
    },
    "reply_to_user": {
        "params": {"message": "<string>"},
        "description": "Send a direct message to the user."
    }
}

CUSTOM_TOOLS_DIR = os.path.join(os.path.dirname(__file__), "custom")

def load_custom_tools():
    custom_tools = {}
    if not os.path.exists(CUSTOM_TOOLS_DIR):
        return custom_tools

    for filename in os.listdir(CUSTOM_TOOLS_DIR):
        if filename.endswith(".py") and filename != "__init__.py":
            module_name = filename[:-3]
            try:
                full_module_name = f"backend.services.tools.custom.{module_name}"
                
                if full_module_name in sys.modules:
                    module = importlib.reload(sys.modules[full_module_name])
                else:
                    module = importlib.import_module(full_module_name)
                    
                for name, obj in inspect.getmembers(module):
                    if inspect.isfunction(obj) and not name.startswith("_"):
                        custom_tools[name] = obj
            except Exception as e:
                logger.debug(f"Error loading custom tool {filename}: {e}")
    return custom_tools

def get_tool_map():
    tool_map = BASE_TOOLS.copy()
    tool_map.update(load_custom_tools())
    return tool_map

def get_tools_prompt():
    tool_map = get_tool_map()
    prompt_lines = ["Tools:"]
    
    for name, func in tool_map.items():
        try:
            if name in BASE_TOOLS_METADATA:
                meta = BASE_TOOLS_METADATA[name]
                params_json = json.dumps(meta["params"])
                doc = meta["description"]
            else:
                sig = inspect.signature(func)
                params = {}
                for param_name, param in sig.parameters.items():
                    if param_name in ['self', 'cls', 'websocket']:
                        continue
                    param_type = "string"
                    if param.annotation != inspect.Parameter.empty:
                        if param.annotation == int:
                            param_type = "integer"
                        elif param.annotation == bool:
                            param_type = "boolean"
                    is_optional = param.default != inspect.Parameter.empty
                    params[param_name] = f"<{param_type}>" + (" (optional)" if is_optional else "")
                
                doc = "Custom tool" 
                if func.__doc__:
                     doc = func.__doc__.strip().split('\n')[0]
                
                params_json = json.dumps(params)
            
            prompt_lines.append(f"- {name}: {params_json} - {doc}")
        except Exception as e:
            logger.debug(f"Error generating prompt for tool {name}: {e}")
            continue
        
    return "\n".join(prompt_lines)
