"""AI-powered code review tool."""

from backend.config import settings
from ..ai_utils import consult_ai
from .dev_tools import inspect_code

PROMPT = """Senior Code Reviewer. Check:
1. SECURITY: No hardcoded creds, injection, unsafe shell
2. LOGIC: Syntactically correct, logically sound
3. LAWS: No harm, no violations

Return exactly: APPROVED or REJECTED: <reason>"""


async def review_code_changes(file_path: str, proposed_code: str) -> str:
    """Review code for security, logic, and compliance."""
    try:
        original = inspect_code(file_path)
        input_text = f"File: {file_path}\n\nOriginal:\n{original}\n\nProposed:\n{proposed_code}"
        
        verdict = await consult_ai(settings.MODEL_REASONING, PROMPT, input_text)
        return "APPROVED" if "APPROVED" in verdict.upper() else verdict
    except Exception as e:
        return f"Review error: {e}"
