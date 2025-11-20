import os
import ast
import shutil
import subprocess
import sys
import asyncio
from ..ai_utils import consult_ai

# Determine project root dynamically
# Current file: services/tools/custom/dev_tools.py
# Root: ../../../../
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
MODEL_CODING = os.getenv("MODEL_CODING", "qwen2.5-coder:7b")

async def generate_code(requirements: str, context_files: list[str] = None) -> str:
    """
    Generates production-ready code using the specialized Coding Model.
    Args:
        requirements: Description of the feature or fix.
        context_files: List of file paths to read for context.
    Returns:
        Generated code string.
    """
    context_content = ""
    if context_files:
        for path in context_files:
            try:
                full_path = path if os.path.isabs(path) else os.path.join(BASE_DIR, path)
                if os.path.exists(full_path):
                    with open(full_path, 'r', encoding='utf-8') as f:
                        context_content += f"\n--- FILE: {path} ---\n{f.read()}\n"
            except Exception as e:
                context_content += f"\nError reading {path}: {e}\n"

    system_prompt = """You are a Senior Software Engineer.
    Write clean, efficient, and error-free Python code based on the user's requirements.
    - Return ONLY the code block. No markdown formatting like ```python.
    - Include necessary imports.
    - Follow PEP 8 standards.
    """
    
    user_input = f"Requirements:\n{requirements}\n\nContext:\n{context_content}"
    
    code = await consult_ai(MODEL_CODING, system_prompt, user_input)
    # Strip markdown if present
    code = code.replace("```python", "").replace("```", "").strip()
    return code

def inspect_code(path: str) -> str:
    """
    Reads a file and returns its content along with a structural summary (classes/functions).
    Useful for understanding code structure before editing.
    """
    try:
        if not os.path.isabs(path):
            path = os.path.join(BASE_DIR, path)
            
        if not os.path.exists(path):
            return f"Error: File {path} not found."
            
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        summary = []
        try:
            tree = ast.parse(content)
            for node in tree.body:
                if isinstance(node, ast.ClassDef):
                    summary.append(f"Class: {node.name}")
                    methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                    if methods:
                        summary.append(f"  Methods: {', '.join(methods)}")
                elif isinstance(node, ast.FunctionDef):
                    summary.append(f"Function: {node.name}")
                elif isinstance(node, ast.AsyncFunctionDef):
                    summary.append(f"Async Function: {node.name}")
                    
        except SyntaxError:
            summary.append("Error parsing Python syntax for summary.")
            
        structure = "\n".join(summary)
        return f"FILE: {path}\nSTRUCTURE:\n{structure}\n\nCONTENT:\n{content}"
    except Exception as e:
        return f"Error inspecting code: {str(e)}"

def run_safe_edit(target_file: str, new_content: str, test_content: str) -> str:
    """
    Safely updates a file by:
    1. Backing up the original.
    2. Applying changes (Optimistic Application).
    3. Running a verification test.
    4. Rolling back if the test fails.
    
    This ensures tests can import the module normally without complex dynamic loading.
    """
    # Resolve path
    if not os.path.isabs(target_file):
        target_file = os.path.join(BASE_DIR, target_file)
        
    if not os.path.exists(target_file):
        return f"Error: Target file {target_file} does not exist. Use file_manager to create new files."

    backup_path = target_file + ".bak"
    test_path = os.path.join(os.path.dirname(target_file), "test_verification_temp.py")
    
    try:
        # 1. Backup
        shutil.copy2(target_file, backup_path)
        
        # 2. Apply New Content
        with open(target_file, 'w', encoding='utf-8') as f:
            f.write(new_content)
            
        # 3. Write Test
        with open(test_path, 'w', encoding='utf-8') as f:
            f.write(test_content)
            
        # 4. Run Test
        # We run it as a subprocess to isolate it
        # We use the current python executable
        result = subprocess.run(
            [sys.executable, test_path],
            capture_output=True,
            text=True,
            cwd=BASE_DIR # Run from root to ensure imports like 'services.tools' work
        )
        
        # 5. Decision
        if result.returncode == 0:
            # Success
            os.remove(backup_path)
            if os.path.exists(test_path):
                os.remove(test_path)
            return f"SUCCESS: Code updated and verified.\nTest Output:\n{result.stdout}"
        else:
            # Failure - Rollback
            shutil.move(backup_path, target_file) # Restore original
            if os.path.exists(test_path):
                os.remove(test_path)
            return f"FAILED: Tests didn't pass. Rolled back changes.\nError Output:\n{result.stderr}\nStandard Output:\n{result.stdout}"
            
    except Exception as e:
        # Emergency Rollback
        if os.path.exists(backup_path):
            shutil.move(backup_path, target_file)
        if os.path.exists(test_path):
            os.remove(test_path)
        return f"CRITICAL ERROR in run_safe_edit: {str(e)}. Changes rolled back."
