import os
import asyncio
import tempfile
from ..ai_utils import consult_ai
from backend.config import settings
from backend.logger import logger


async def run_code(
    requirements: str,
    filename: str = None,
    persist: bool = False,
    context_files: list[str] = None,
    websocket=None
) -> str:
    """
    Unified tool that generates Python code, saves it, and executes it.
    
    Args:
        requirements: Description of what the code should do.
        filename: Optional filename to save the code (e.g., "my_script.py").
                  If not provided, uses a temp file.
        persist: If True, saves the file permanently in the project's scripts dir.
                 If False, uses a temporary file that is deleted after execution.
        context_files: Optional list of file paths to read for context.
        websocket: Optional websocket for streaming output.
    
    Returns:
        Execution output or error message.
    """
    context_content = ""
    if context_files:
        for path in context_files:
            try:
                if os.path.exists(path):
                    with open(path, 'r', encoding='utf-8') as f:
                        context_content += f"\n--- FILE: {path} ---\n{f.read()}\n"
            except Exception as e:
                context_content += f"\nError reading {path}: {e}\n"

    system_prompt = """You are a Senior Python Developer.
Generate clean, executable Python code based on the requirements.
Rules:
- Return ONLY the raw Python code, no markdown.
- Include all necessary imports at the top.
- The code must be self-contained and runnable with `python script.py`.
- Handle errors gracefully with try/except.
- If the task requires output, use print() statements.
"""
    
    user_input = f"Requirements:\n{requirements}"
    if context_content:
        user_input += f"\n\nContext Files:\n{context_content}"
    
    try:
        code = await consult_ai(settings.MODEL_CODING, system_prompt, user_input)
        code = code.replace("```python", "").replace("```", "").strip()
    except Exception as e:
        return f"Error generating code: {e}"

    if persist and filename:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        scripts_dir = os.path.join(base_dir, "scripts", "generated")
        os.makedirs(scripts_dir, exist_ok=True)
        script_path = os.path.join(scripts_dir, filename if filename.endswith('.py') else f"{filename}.py")
    else:
        fd, script_path = tempfile.mkstemp(suffix=".py", prefix="skynet_exec_")
        os.close(fd)

    try:
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(code)
        
        process = await asyncio.create_subprocess_exec(
            'python', script_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout_data = b""
        stderr_data = b""
        
        if websocket:
            import json
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                stdout_data += line
                try:
                    await websocket.send_text(json.dumps({
                        "role": "terminal-output",
                        "content": line.decode()
                    }))
                except Exception:
                    pass
            stderr_data = await process.stderr.read()
            await process.wait()
        else:
            try:
                stdout_data, stderr_data = await asyncio.wait_for(
                    process.communicate(),
                    timeout=120.0
                )
            except asyncio.TimeoutError:
                process.kill()
                return "Error: Execution timed out after 120 seconds."

        output = stdout_data.decode()
        errors = stderr_data.decode()

        if process.returncode != 0:
            result = f"Execution failed (code {process.returncode}):\n{errors}"
            if output:
                result += f"\nOutput before error:\n{output}"
            return result

        result = f"Execution successful.\nOutput:\n{output}"
        if persist and filename:
            result += f"\nCode saved to: {script_path}"
        return result

    except Exception as e:
        logger.error(f"Error in run_code: {e}")
        return f"Exception: {e}"
    finally:
        if not persist and os.path.exists(script_path):
            try:
                os.remove(script_path)
            except Exception:
                pass
