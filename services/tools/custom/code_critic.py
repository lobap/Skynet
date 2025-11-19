import os
from ..ai_utils import consult_ai
from .dev_tools import inspect_code

MODEL_REASONING = os.getenv("MODEL_REASONING", "deepseek-r1:8b")

async def review_code_changes(file_path: str, proposed_code: str) -> str:
    """
    Acts as a Senior Code Reviewer.
    Checks for security flaws, logic errors, and compliance with system laws.
    Returns "APPROVED" or "REJECTED: <reason>".
    """
    try:
        # Get original code for comparison
        original_code = inspect_code(file_path)
        
        system_prompt = """You are a Senior Code Reviewer and Security Auditor.
        Review the proposed code changes against the original code.
        
        CRITERIA:
        1. SECURITY: No hardcoded credentials, no injection vulnerabilities, no unsafe shell execution without validation.
        2. LOGIC: The code must be syntactically correct and logically sound.
        3. LAWS: Must not violate the core system laws (Do no harm, etc.).
        
        If the code is safe and good, return exactly: APPROVED
        If there are issues, return exactly: REJECTED: <brief explanation of the issue>
        """
        
        user_input = f"File: {file_path}\n\nOriginal Code:\n{original_code}\n\nProposed Code:\n{proposed_code}"
        
        verdict = await consult_ai(MODEL_REASONING, system_prompt, user_input)
        
        if "APPROVED" in verdict.upper():
            return "APPROVED"
        else:
            return verdict
            
    except Exception as e:
        return f"Error during code review: {str(e)}"
