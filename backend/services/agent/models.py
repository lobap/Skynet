"""Pydantic models for agent responses."""

import json
import re
from typing import Any
from pydantic import BaseModel, Field, field_validator


class AgentAction(BaseModel):
    """Tool action to execute."""
    name: str = Field(..., description="Tool name")
    parameters: dict[str, Any] = Field(default_factory=dict)
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or v.lower() in ('none', 'null', ''):
            raise ValueError("Empty action name")
        return v


class AgentResponse(BaseModel):
    """Structured LLM response."""
    thought: str = Field(default="")
    action: AgentAction | None = Field(default=None)
    
    @classmethod
    def from_llm_response(cls, content: str) -> "AgentResponse":
        """Parse LLM response into structured format."""
        original = content
        content = _clean_content(content)
        
        # Try parsing
        data = _try_parse(content)
        
        if data is None:
            return _extract_fallback(content, original)
        
        thought = data.get("thought", "")
        action_data = data.get("action", {})
        
        if isinstance(action_data, str):
            action_data = {"name": action_data, "parameters": {}}
        
        if not action_data or not action_data.get("name"):
            return cls(thought=thought, action=None)
        
        try:
            action = AgentAction(
                name=action_data.get("name", ""),
                parameters=action_data.get("parameters", {})
            )
        except ValueError:
            action = None
        
        return cls(thought=thought, action=action)


class CommandSecurity:
    """Security validation for shell commands."""
    
    @classmethod
    def is_safe(cls, command: str) -> tuple[bool, str]:
        """Check if command is safe."""
        from backend.config import settings
        
        cmd = command.lower().strip()
        for pattern in settings.SHELL_BLOCKED_PATTERNS:
            if pattern in cmd:
                return False, f"Blocked: {pattern}"
        return True, "Safe"


def _clean_content(content: str) -> str:
    """Clean markdown and extract JSON."""
    content = content.strip()
    
    # Remove code blocks
    for prefix in ("```json", "```"):
        if content.startswith(prefix):
            content = content[len(prefix):]
    if content.endswith("```"):
        content = content[:-3]
    content = content.strip()
    
    # Extract JSON object
    match = re.search(r'\{.*\}', content, re.DOTALL)
    if match:
        content = match.group()
    
    # Fix common issues
    content = re.sub(r',\s*}', '}', content)
    content = re.sub(r',\s*]', ']', content)
    
    return content


def _try_parse(content: str) -> dict | None:
    """Try to parse JSON content."""
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass
    
    # More aggressive cleanup
    try:
        cleaned = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', content)
        cleaned = re.sub(r'(\w+):', r'"\1":', cleaned)
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return None


def _extract_fallback(content: str, original: str) -> AgentResponse:
    """Extract thought/action via regex as fallback."""
    thought_match = re.search(r'"thought"\s*:\s*"([^"]*)"', content)
    action_match = re.search(r'"name"\s*:\s*"(\w+)"', content)
    
    if thought_match or action_match:
        thought = thought_match.group(1) if thought_match else ""
        action_name = action_match.group(1) if action_match else None
        
        if action_name:
            params = {}
            pm = re.search(r'"parameters"\s*:\s*\{([^}]*)\}', content)
            if pm:
                try:
                    params = json.loads('{' + pm.group(1) + '}')
                except:
                    pass
            return AgentResponse(thought=thought, action=AgentAction(name=action_name, parameters=params))
        return AgentResponse(thought=thought, action=None)
    
    # Complete failure - fallback to reply
    return AgentResponse(
        thought="Processing...",
        action=AgentAction(name="reply_to_user", parameters={"message": original[:300]})
    )
