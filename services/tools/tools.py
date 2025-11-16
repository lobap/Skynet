import asyncio
import aiofiles
import os
from dotenv import load_dotenv
from . import vault

load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'backend', '.env'))

async def execute_shell(command: str) -> str:
    try:
        if command.startswith('sudo '):
            password = vault.get_credential('sudo_password') or os.getenv('SUDO_PASSWORD', '')
            user = vault.get_credential('sudo_user') or os.getenv('SUDO_USER', '')
            if not password:
                return "Error: sudo password not found in vault or .env. Use store_credential tool to set it."
            if user:
                command = command.replace('sudo ', f'sudo -u {user} ', 1)
            # Use -S to read password from stdin
            process = await asyncio.create_subprocess_shell(command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, stdin=asyncio.subprocess.PIPE)
            stdout, stderr = await process.communicate(input=password.encode() + b'\n')
        else:
            process = await asyncio.create_subprocess_shell(command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            stdout, stderr = await process.communicate()
        return stdout.decode() if process.returncode == 0 else f"Error (code {process.returncode}): {stderr.decode()}"
    except Exception as e:
        return f"Exception: {str(e)}"

async def file_manager(action: str, path: str, content: str = None) -> str:
    try:
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