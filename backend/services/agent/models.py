from pydantic import BaseModel, Field, field_validator
from typing import Optional, Any


class AgentAction(BaseModel):
    """Structured action from the agent."""
    name: str = Field(..., description="Tool name to execute")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Tool parameters")
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or v.lower() in ('none', 'null', ''):
            raise ValueError("Action name cannot be empty or None")
        return v


class AgentResponse(BaseModel):
    """Structured response from the LLM agent."""
    thought: str = Field(default="", description="Agent's reasoning")
    action: Optional[AgentAction] = Field(default=None, description="Action to execute")
    
    @classmethod
    def from_llm_response(cls, content: str) -> "AgentResponse":
        """Parse LLM response string into structured AgentResponse."""
        import json
        import re
        
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        
        match = re.search(r'\{.*\}', content, re.DOTALL)
        if match:
            content = match.group()
        
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            return cls(
                thought=f"Failed to parse response: {e}",
                action=AgentAction(name="reply_to_user", parameters={"message": content[:500]})
            )
        
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
    
    BLOCKED_PATTERNS = [
        "rm -rf /",
        "rm -rf ~",
        "rm -rf .",
        "chmod 777",
        ":(){ :|:& };:",
        "> /dev/sda",
        "mkfs.",
        "dd if=",
        "wget.*|.*sh",
        "curl.*|.*sh",
        "sudo rm",
        "sudo chmod",
        "format c:",
        "del /f /s /q",
    ]
    
    ALLOWED_PREFIXES = [
        "ls", "cat", "echo", "pwd", "cd", "mkdir", "touch",
        "pip install", "pip list", "pip show",
        "python", "node", "npm",
        "git status", "git log", "git diff", "git add", "git commit",
        "docker ps", "docker logs", "docker images",
        "curl", "wget",
        "head", "tail", "grep", "find", "wc",
    ]
    
    @classmethod
    def is_safe(cls, command: str) -> tuple[bool, str]:
        """Check if command is safe to execute. Returns (is_safe, reason)."""
        cmd_lower = command.lower().strip()
        
        for pattern in cls.BLOCKED_PATTERNS:
            if pattern in cmd_lower:
                return False, f"Blocked pattern detected: {pattern}"
        
        return True, "Command appears safe"
    
    @classmethod
    def audit_log(cls, command: str, result: str, user: str = "agent") -> None:
        """Log command execution for audit trail."""
        import logging
        logger = logging.getLogger("skynet.audit")
        logger.info(f"[{user}] Command: {command[:200]} | Result: {result[:100]}")
