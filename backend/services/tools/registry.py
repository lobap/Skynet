"""Tool registry for agent capabilities."""

import os
import sys
import json
import inspect
import importlib
from typing import Callable, Dict, Any
from backend.logger import logger
from . import tools

CUSTOM_TOOLS_DIR = os.path.join(os.path.dirname(__file__), "custom")

# Base tools with metadata
BASE_TOOLS: Dict[str, Callable] = {
    "execute_shell": tools.execute_shell,
    "file_manager": tools.file_manager,
    "store_credential": tools.store_credential,
    "get_credential": tools.get_credential,
    "task_complete": lambda: "Task Completed",
    "reply_to_user": lambda message: f"Replied: {message}",
}

BASE_METADATA: Dict[str, Dict[str, Any]] = {
    "execute_shell": {"params": {"command": "<string>"}, "desc": "Execute shell commands"},
    "file_manager": {"params": {"action": "read|write|list", "path": "<string>", "content": "<string> (opt)"}, "desc": "File operations"},
    "store_credential": {"params": {"key": "<string>", "value": "<string>"}, "desc": "Store credential"},
    "get_credential": {"params": {"key": "<string>"}, "desc": "Get credential"},
    "task_complete": {"params": {}, "desc": "Signal task completion"},
    "reply_to_user": {"params": {"message": "<string>"}, "desc": "Reply to user"},
}


def load_custom_tools() -> Dict[str, Callable]:
    """Load tools from custom/ directory."""
    tools_map = {}
    if not os.path.exists(CUSTOM_TOOLS_DIR):
        return tools_map
    
    for filename in os.listdir(CUSTOM_TOOLS_DIR):
        if not filename.endswith(".py") or filename.startswith("_"):
            continue
        
        module_name = filename[:-3]
        try:
            full_name = f"backend.services.tools.custom.{module_name}"
            
            if full_name in sys.modules:
                module = importlib.reload(sys.modules[full_name])
            else:
                module = importlib.import_module(full_name)
            
            for name, obj in inspect.getmembers(module):
                if inspect.isfunction(obj) and not name.startswith("_"):
                    tools_map[name] = obj
        except Exception as e:
            logger.debug(f"Load error {filename}: {e}")
    
    return tools_map


def get_tool_map() -> Dict[str, Callable]:
    """Get all available tools."""
    tool_map = BASE_TOOLS.copy()
    tool_map.update(load_custom_tools())
    return tool_map


def get_tools_prompt() -> str:
    """Generate tools documentation for LLM prompt."""
    lines = ["Tools:"]
    
    for name, func in get_tool_map().items():
        try:
            if name in BASE_METADATA:
                meta = BASE_METADATA[name]
                params = json.dumps(meta["params"])
                desc = meta["desc"]
            else:
                params, desc = _extract_func_info(func)
            
            lines.append(f"- {name}: {params} - {desc}")
        except Exception:
            continue
    
    return "\n".join(lines)


def _extract_func_info(func: Callable) -> tuple[str, str]:
    """Extract params and description from function."""
    sig = inspect.signature(func)
    params = {}
    
    for name, param in sig.parameters.items():
        if name in ('self', 'cls', 'websocket'):
            continue
        
        ptype = "string"
        if param.annotation != inspect.Parameter.empty:
            if param.annotation == int:
                ptype = "integer"
            elif param.annotation == bool:
                ptype = "boolean"
        
        optional = " (opt)" if param.default != inspect.Parameter.empty else ""
        params[name] = f"<{ptype}>{optional}"
    
    desc = func.__doc__.strip().split('\n')[0] if func.__doc__ else "Custom tool"
    return json.dumps(params), desc
