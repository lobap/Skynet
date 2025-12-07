"""Agent prompts for LLM interactions."""

import json
from ..tools import registry

SYSTEM_PROMPT = """You are Skynet, a self-evolving AI with full codebase access.

WORKFLOW:
- run_code: Generate & execute Python (persist=True to save)
- execute_shell: Direct commands (ls, pip, etc.)
- browser_use: Navigate/screenshot websites (action required: "navigate"|"screenshot")

OUTPUT FORMAT (JSON only):
{"thought": "reasoning", "action": {"name": "tool_name", "parameters": {...}}}

TOOLS:
- reply_to_user: Respond to user
- task_complete: Mark task done

RULES:
- Always return valid JSON
- No markdown, plain text, or code blocks outside JSON
- Use 'python script.py' not 'python -m script.py'
"""


def get_system_prompt() -> str:
    """Get full system prompt with tools."""
    return SYSTEM_PROMPT + "\n\n" + registry.get_tools_prompt()


def get_tool_generation_system_prompt() -> str:
    """Prompt for generating new tools."""
    return """Generate async Python function.
Rules:
- Function name matches request
- Use async def with type hints + docstring
- Actual implementation, never 'pass'
- Return descriptive string
- Include try/except
- Return only code, no markdown
Libraries: stdlib, aiohttp, bs4, playwright"""


def get_tool_generation_user_prompt(name: str, params: dict) -> str:
    """User prompt for tool generation."""
    return f"""Create async function '{name}'.
Params: {json.dumps(params) if params else 'None'}
Must DO something useful, return results, handle errors."""


def get_recovery_prompt() -> str:
    """Prompt for error recovery."""
    return "Previous action failed. Use attempt_fix or learn_tech to resolve before asking user."
