"""Autonomous debugging tool."""

from backend.config import settings
from ..ai_utils import consult_ai
from .dev_tools import run_safe_edit, inspect_code


async def attempt_fix(file_path: str, error_trace: str) -> str:
    """Analyze error, generate fix, and apply safely.
    
    1. Analyze error with reasoning model
    2. Generate fix with coding model
    3. Create verification test
    4. Apply with rollback on failure
    """
    try:
        code = inspect_code(file_path)
        if "Error" in code and not code.startswith("FILE:"):
            return f"Could not read: {code}"
        
        # Analyze
        analysis = await consult_ai(
            settings.MODEL_REASONING,
            "Debugger: Find ROOT CAUSE and step-by-step solution",
            f"Code:\n{code}\n\nError:\n{error_trace}"
        )
        
        # Generate fix
        fixed = await consult_ai(
            settings.MODEL_CODING,
            "Rewrite FULL file to fix. Only code, no markdown, include imports",
            f"Original:\n{code}\n\nAnalysis:\n{analysis}"
        )
        fixed = fixed.replace("```python", "").replace("```", "").strip()
        
        # Generate test
        test = await consult_ai(
            settings.MODEL_CODING,
            "Generate verification test. Only code, no markdown",
            f"Fixed:\n{fixed}"
        )
        test = test.replace("```python", "").replace("```", "").strip()
        
        # Apply
        result = run_safe_edit(file_path, fixed, test)
        return f"Analysis: {analysis[:200]}...\n{result}"
    except Exception as e:
        return f"Debugger error: {e}"


# Alias
analyze_error_and_fix = attempt_fix
