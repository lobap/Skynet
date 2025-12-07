"""Code generation and execution tool."""

import os
import asyncio
import tempfile
from backend.config import settings
from backend.logger import logger
from ..ai_utils import consult_ai

SYSTEM_PROMPT = """You are a Senior Python Developer.
Generate clean, executable Python code based on the requirements.
Rules:
- Return ONLY raw Python code, no markdown
- Include all imports at top
- Code must be self-contained and runnable
- Handle errors with try/except
- Use print() for output"""


async def run_code(
    requirements: str,
    filename: str | None = None,
    persist: bool = False,
    context_files: list[str] | None = None,
    websocket=None
) -> str:
    """Generate, save, and execute Python code.
    
    Args:
        requirements: What the code should do
        filename: Optional filename for persistence
        persist: Save permanently if True
        context_files: Files to read for context
        websocket: Optional websocket for streaming
    """
    context = _read_context_files(context_files or [])
    
    # Generate code
    user_input = f"Requirements:\n{requirements}"
    if context:
        user_input += f"\n\nContext:\n{context}"
    
    try:
        code = await consult_ai(settings.MODEL_CODING, SYSTEM_PROMPT, user_input)
        code = code.replace("```python", "").replace("```", "").strip()
    except Exception as e:
        return f"Code generation error: {e}"
    
    # Determine save path
    script_path = _get_script_path(filename, persist)
    
    try:
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(code)
        
        result = await _execute(script_path, websocket)
        
        if persist and filename:
            result += f"\nSaved: {script_path}"
        return result
        
    except Exception as e:
        logger.error(f"run_code error: {e}")
        return f"Exception: {e}"
    finally:
        if not persist and os.path.exists(script_path):
            try:
                os.remove(script_path)
            except:
                pass


def _read_context_files(paths: list[str]) -> str:
    """Read content from context files."""
    content = ""
    for path in paths:
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    content += f"\n--- {path} ---\n{f.read()}\n"
        except Exception as e:
            content += f"\nError reading {path}: {e}\n"
    return content


def _get_script_path(filename: str | None, persist: bool) -> str:
    """Get path for script file."""
    if persist and filename:
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        scripts_dir = os.path.join(base, "scripts", "generated")
        os.makedirs(scripts_dir, exist_ok=True)
        return os.path.join(scripts_dir, filename if filename.endswith('.py') else f"{filename}.py")
    
    fd, path = tempfile.mkstemp(suffix=".py", prefix="skynet_")
    os.close(fd)
    return path


async def _execute(script_path: str, websocket=None) -> str:
    """Execute script and capture output."""
    proc = await asyncio.create_subprocess_exec(
        'python', script_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    if websocket:
        return await _execute_streaming(proc, websocket)
    
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
    except asyncio.TimeoutError:
        proc.kill()
        return "Timeout after 120s"
    
    if proc.returncode != 0:
        return f"Failed (code {proc.returncode}):\n{stderr.decode()}"
    
    return f"Success:\n{stdout.decode()}"


async def _execute_streaming(proc, websocket) -> str:
    """Execute with websocket streaming."""
    import json
    stdout = b""
    
    while True:
        line = await proc.stdout.readline()
        if not line:
            break
        stdout += line
        try:
            await websocket.send_text(json.dumps({
                "role": "terminal-output",
                "content": line.decode()
            }))
        except:
            pass
    
    stderr = await proc.stderr.read()
    await proc.wait()
    
    if proc.returncode != 0:
        return f"Failed:\n{stderr.decode()}"
    return f"Success:\n{stdout.decode()}"
