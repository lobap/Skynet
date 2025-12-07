"""Development tools: code generation, inspection, safe editing."""

import os
import ast
import shutil
import subprocess
import sys
from backend.config import settings
from ..ai_utils import consult_ai

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

SYSTEM_PROMPT = """You are a Senior Software Engineer.
Write clean, efficient Python code based on requirements.
- Return ONLY code, no markdown
- Include imports
- Follow PEP 8"""


async def generate_code(requirements: str, context_files: list[str] | None = None) -> str:
    """Generate code using coding model.
    
    Args:
        requirements: Feature/fix description
        context_files: Files for context
    """
    context = _read_context(context_files or [])
    user_input = f"Requirements:\n{requirements}\n\nContext:\n{context}"
    
    code = await consult_ai(settings.MODEL_CODING, SYSTEM_PROMPT, user_input)
    return code.replace("```python", "").replace("```", "").strip()


def inspect_code(path: str) -> str:
    """Read file with structural summary."""
    try:
        path = _resolve_path(path)
        if not os.path.exists(path):
            return f"Not found: {path}"
        
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        summary = _get_structure(content)
        return f"FILE: {path}\nSTRUCTURE:\n{summary}\n\nCONTENT:\n{content}"
    except Exception as e:
        return f"Error: {e}"


def run_safe_edit(target_file: str, new_content: str, test_content: str) -> str:
    """Apply changes with backup and test verification.
    
    1. Backup original
    2. Apply changes
    3. Run test
    4. Rollback if failed
    """
    target = _resolve_path(target_file)
    if not os.path.exists(target):
        return f"Not found: {target}"
    
    backup = target + ".bak"
    test_path = os.path.join(os.path.dirname(target), "_test_temp.py")
    
    try:
        shutil.copy2(target, backup)
        
        with open(target, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        with open(test_path, 'w', encoding='utf-8') as f:
            f.write(test_content)
        
        result = subprocess.run(
            [sys.executable, test_path],
            capture_output=True, text=True, cwd=BASE_DIR
        )
        
        if result.returncode == 0:
            os.remove(backup)
            _cleanup(test_path)
            return f"SUCCESS: Verified\n{result.stdout}"
        
        shutil.move(backup, target)
        _cleanup(test_path)
        return f"FAILED: Rolled back\n{result.stderr}"
    except Exception as e:
        if os.path.exists(backup):
            shutil.move(backup, target)
        _cleanup(test_path)
        return f"ERROR: {e}"


def _resolve_path(path: str) -> str:
    """Resolve relative path to absolute."""
    return path if os.path.isabs(path) else os.path.join(BASE_DIR, path)


def _read_context(files: list[str]) -> str:
    """Read content from context files."""
    content = ""
    for path in files:
        try:
            full = _resolve_path(path)
            if os.path.exists(full):
                with open(full, 'r', encoding='utf-8') as f:
                    content += f"\n--- {path} ---\n{f.read()}\n"
        except Exception as e:
            content += f"\nError {path}: {e}\n"
    return content


def _get_structure(content: str) -> str:
    """Extract function/class structure from code."""
    summary = []
    try:
        tree = ast.parse(content)
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                methods = [n.name for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
                summary.append(f"Class: {node.name} ({', '.join(methods)})")
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                prefix = "async " if isinstance(node, ast.AsyncFunctionDef) else ""
                summary.append(f"{prefix}def {node.name}")
    except SyntaxError:
        summary.append("Syntax error")
    return "\n".join(summary)


def _cleanup(path: str):
    """Remove file if exists."""
    if os.path.exists(path):
        os.remove(path)
