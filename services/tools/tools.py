import asyncio
import aiofiles
import os
from dotenv import load_dotenv
from . import vault

load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'backend', '.env'))

async def execute_shell(command: str) -> str:
    try:
        TIMEOUT = 120
        
        async def run_proc(cmd):
            if cmd.startswith('sudo '):
                password = vault.get_credential('sudo_password') or os.getenv('SUDO_PASSWORD', '')
                if not password:
                    return None, None, "Error: sudo password not found in vault or .env. Use store_credential tool to set it."
                cmd = cmd.replace('sudo ', 'sudo -S ', 1)
                process = await asyncio.create_subprocess_shell(cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, stdin=asyncio.subprocess.PIPE)
                try:
                    stdout, stderr = await asyncio.wait_for(process.communicate(input=password.encode() + b'\n'), timeout=TIMEOUT)
                except asyncio.TimeoutError:
                    process.kill()
                    return None, None, f"Error: Command timed out after {TIMEOUT} seconds."
            else:
                process = await asyncio.create_subprocess_shell(cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                try:
                    stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=TIMEOUT)
                except asyncio.TimeoutError:
                    process.kill()
                    return None, None, f"Error: Command timed out after {TIMEOUT} seconds."
            return process, stdout, stderr

        process, stdout, stderr = await run_proc(command)
        if isinstance(stderr, str) and stderr.startswith("Error:"):
             return stderr

        if process.returncode != 0:
            err_msg = stderr.decode()
            if "ModuleNotFoundError: No module named" in err_msg:
                try:
                    import re
                    match = re.search(r"No module named '([^']+)'", err_msg)
                    if match:
                        module_name = match.group(1)
                        install_cmd = f"pip install {module_name}"
                        p_inst, out_inst, err_inst = await run_proc(install_cmd)
                        
                        if p_inst.returncode == 0:
                            process, stdout, stderr = await run_proc(command)
                            if process.returncode == 0:
                                return f"Auto-fixed missing dependency '{module_name}'.\nOutput:\n{stdout.decode()}"
                            else:
                                return f"Installed '{module_name}' but command still failed:\n{stderr.decode()}"
                        else:
                            return f"Failed to auto-install '{module_name}':\n{err_inst.decode()}\nOriginal Error:\n{err_msg}"
                except Exception as e:
                    return f"Error during self-healing: {str(e)}\nOriginal Error: {err_msg}"
            
            return f"Error (code {process.returncode}): {err_msg}"
            
        return stdout.decode()
    except Exception as e:
        return f"Exception: {str(e)}"

async def file_manager(action: str, path: str, content: str = None) -> str:
    try:
        path = os.path.expanduser(path)
        if action == "read":
            async with aiofiles.open(path, 'r') as f:
                return await f.read()
        elif action == "write" or action == "create":
            os.makedirs(os.path.dirname(path), exist_ok=True)
            async with aiofiles.open(path, 'w') as f:
                await f.write(content)
            return "File written successfully."
        elif action == "create_dir":
            os.makedirs(path, exist_ok=True)
            return "Directory created successfully."
        elif action == "list":
            return "\n".join(os.listdir(path))
        return "Invalid action."
    except Exception as e:
        return f"Exception: {str(e)}"

async def store_credential(key: str, value: str) -> str:
    try:
        vault.set_credential(key, value)
        return f"Credential '{key}' stored successfully in vault."
    except Exception as e:
        return f"Exception: {str(e)}"

async def get_credential(key: str) -> str:
    try:
        value = vault.get_credential(key)
        if value:
            return f"Credential '{key}': {value}"
        return f"Credential '{key}' not found in vault."
    except Exception as e:
        return f"Exception: {str(e)}"