"""Core tools: shell execution, file management, credentials."""

import asyncio
import os
import re
from typing import Literal
import aiofiles
from backend.config import settings
from backend.logger import logger
from backend.services.agent.models import CommandSecurity
from . import vault

ActionType = Literal["read", "write", "create", "create_dir", "list"]
TIMEOUT = 120


async def execute_shell(command: str, websocket=None) -> str:
    """Execute shell command with security checks and auto-fix."""
    is_safe, reason = CommandSecurity.is_safe(command)
    if not is_safe:
        logger.warning(f"Blocked: {command}")
        return f"BLOCKED: {reason}"
    
    try:
        proc, stdout, stderr = await _run_command(command, websocket)
        
        if isinstance(stderr, str) and stderr.startswith("Error:"):
            return stderr
        
        if proc.returncode != 0:
            err = stderr.decode()
            fixed = await _try_auto_fix(command, err, websocket)
            if fixed:
                return fixed
            return f"Error ({proc.returncode}): {err}"
        
        return stdout.decode()
    except Exception as e:
        logger.error(f"Shell error: {e}")
        return f"Exception: {e}"


async def _run_command(cmd: str, websocket=None):
    """Execute command, handling sudo if needed."""
    if cmd.startswith('sudo '):
        return await _run_sudo(cmd)
    
    proc = await asyncio.create_subprocess_shell(
        cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    
    if websocket:
        return await _run_streaming(proc, websocket)
    
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), TIMEOUT)
        return proc, stdout, stderr
    except asyncio.TimeoutError:
        proc.kill()
        return proc, b"", f"Error: Timeout after {TIMEOUT}s"


async def _run_sudo(cmd: str):
    """Execute sudo command with password."""
    password = vault.get_credential('sudo_password') or settings.SUDO_PASSWORD
    if not password:
        return None, None, "Error: sudo password not found"
    
    cmd = cmd.replace('sudo ', 'sudo -S ', 1)
    proc = await asyncio.create_subprocess_shell(
        cmd, stdout=asyncio.subprocess.PIPE, 
        stderr=asyncio.subprocess.PIPE, stdin=asyncio.subprocess.PIPE
    )
    
    try:
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(input=password.encode() + b'\n'), TIMEOUT
        )
        return proc, stdout, stderr
    except asyncio.TimeoutError:
        proc.kill()
        return proc, b"", f"Error: Timeout after {TIMEOUT}s"


async def _run_streaming(proc, websocket):
    """Stream output to websocket."""
    import json
    stdout = b""
    
    while True:
        line = await proc.stdout.readline()
        if not line:
            break
        stdout += line
        try:
            await websocket.send_text(json.dumps({"role": "terminal-output", "content": line.decode()}))
        except:
            pass
    
    stderr = await proc.stderr.read()
    await proc.wait()
    return proc, stdout, stderr


async def _try_auto_fix(command: str, err: str, websocket) -> str | None:
    """Auto-install missing modules."""
    match = re.search(r"No module named '([^']+)'", err)
    if not match:
        return None
    
    module = match.group(1)
    if websocket:
        import json
        await websocket.send_text(json.dumps({
            "role": "terminal-output", 
            "content": f"[Auto-Fix] Installing {module}...\n"
        }))
    
    proc, stdout, stderr = await _run_command(f"pip install {module}", websocket)
    if proc.returncode != 0:
        return None
    
    proc, stdout, stderr = await _run_command(command, websocket)
    if proc.returncode == 0:
        return f"Auto-fixed '{module}'.\n{stdout.decode()}"
    return None


async def file_manager(action: ActionType, path: str, content: str | None = None) -> str:
    """File operations: read, write, create, create_dir, list."""
    try:
        path = os.path.expanduser(path)
        
        if action == "read":
            async with aiofiles.open(path, 'r') as f:
                return await f.read()
        elif action in ("write", "create"):
            os.makedirs(os.path.dirname(path), exist_ok=True)
            async with aiofiles.open(path, 'w') as f:
                await f.write(content or "")
            return "Written"
        elif action == "create_dir":
            os.makedirs(path, exist_ok=True)
            return "Created"
        elif action == "list":
            return "\n".join(os.listdir(path))
        return "Invalid action"
    except Exception as e:
        logger.error(f"File error: {e}")
        return f"Exception: {e}"


async def store_credential(key: str, value: str) -> str:
    """Store credential in vault."""
    try:
        vault.set_credential(key, value)
        return f"Stored: {key}"
    except Exception as e:
        return f"Error: {e}"


async def get_credential(key: str) -> str:
    """Retrieve credential from vault."""
    try:
        value = vault.get_credential(key)
        return f"{key}: {value}" if value else f"{key} not found"
    except Exception as e:
        return f"Error: {e}"
