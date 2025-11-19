import os
import importlib.util
import inspect
import json
from . import tools

# Base tools that are always available
BASE_TOOLS = {
    "execute_shell": tools.execute_shell,
    "file_manager": tools.file_manager,
    "store_credential": tools.store_credential,
    "get_credential": tools.get_credential,
}

CUSTOM_TOOLS_DIR = os.path.join(os.path.dirname(__file__), "custom")

def load_custom_tools():
    """
    Scans the custom tools directory and loads any python scripts as modules.
    Returns a dictionary of callable functions found in those modules.
    """
    custom_tools = {}
    if not os.path.exists(CUSTOM_TOOLS_DIR):
        return custom_tools

    for filename in os.listdir(CUSTOM_TOOLS_DIR):
        if filename.endswith(".py") and filename != "__init__.py":
            module_name = filename[:-3]
            
            try:
                # Import using full package path to support relative imports
                full_module_name = f"services.tools.custom.{module_name}"
                module = importlib.import_module(full_module_name)
                
                # Inspect module for functions
                for name, obj in inspect.getmembers(module):
                    if inspect.isfunction(obj) and not name.startswith("_"):
                        # Avoid conflicts with base tools or imports
                        # We assume any public function in the file is a tool
                        custom_tools[name] = obj
            except Exception as e:
                print(f"Error loading custom tool {filename}: {e}")
                
    return custom_tools

def get_tool_map():
    """
    Returns the combined map of base and custom tools.
    """
    tool_map = BASE_TOOLS.copy()
    tool_map.update(load_custom_tools())
    return tool_map

def get_tools_prompt():
    """
    Generates the 'Tools:' section for the system prompt dynamically.
    """
    tool_map = get_tool_map()
    prompt_lines = ["Tools:"]
    
    for name, func in tool_map.items():
        try:
            # Generate a simple schema from the function signature
            sig = inspect.signature(func)
            params = {}
            for param_name, param in sig.parameters.items():
                # Skip 'self' or 'cls' if they somehow appear (shouldn't for module functions)
                if param_name in ['self', 'cls']:
                    continue
                
                # Get type annotation if available, else string
                param_type = "string"
                if param.annotation != inspect.Parameter.empty:
                    if param.annotation == int:
                        param_type = "integer"
                    elif param.annotation == bool:
                        param_type = "boolean"
                
                # Check if optional
                is_optional = param.default != inspect.Parameter.empty
                
                params[param_name] = f"<{param_type}>" + (" (optional)" if is_optional else "")
                
            # Create the JSON-like signature string
            # e.g. execute_shell: {"command": "cmd"} - Run shell commands...
            
            # Use docstring as description
            doc = (func.__doc__ or "").strip().split('\n')[0]
            
            # Format: tool_name: {"param": "type"} - Description
            params_json = json.dumps(params)
            
            prompt_lines.append(f"- {name}: {params_json} - {doc}")
        except Exception as e:
            print(f"Error generating prompt for tool {name}: {e}")
            continue
        
    return "\n".join(prompt_lines)
