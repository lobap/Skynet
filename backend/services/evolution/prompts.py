"""LLM Prompts for Evolution Engine."""

ARCHITECT_SYSTEM_PROMPT = """Design minimal Python tool interfaces. Output JSON:
{"name": "tool_name", "description": "...", "parameters": [{"name": "x", "type": "str", "required": true}], "return_type": "str"}"""

BUILDER_SYSTEM_PROMPT = """Write clean async Python. Rules:
- Type hints required
- Docstrings required  
- No os.system/eval/exec
- Handle exceptions gracefully
Output only code, no explanation."""

TEST_GENERATOR_PROMPT = """Generate pytest tests for:
```python
{code}
```
Interface: {interface}
Include happy path and edge cases. Output only code."""

CRITIC_FEEDBACK_PROMPT = """Fix these errors:
{errors}

Original:
```python
{code}
```
Output fixed code only."""
