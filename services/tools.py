import asyncio
import aiofiles
import os

async def execute_shell(command: str) -> str:
    try:
        if command.startswith('sudo '):
            password = os.getenv('SUDO_PASSWORD', '')
            if not password:
                return "Error: SUDO_PASSWORD not set"
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