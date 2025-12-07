"""Architect and Builder for code generation."""

import json
import re
import ollama
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from backend.config import settings
from backend.logger import logger
from . import prompts


@dataclass
class ToolInterface:
    """Tool interface specification."""
    name: str
    description: str
    parameters: List[Dict[str, Any]]
    return_type: str = "str"


class Architect:
    """Designs tool interfaces."""
    
    def __init__(self):
        self.client = ollama.AsyncClient(host=settings.OLLAMA_HOST)
    
    async def design_interface(self, description: str, tool_name: str) -> Optional[ToolInterface]:
        """Design interface for a new tool."""
        try:
            response = await self.client.chat(
                model=settings.MODEL_FAST,
                messages=[
                    {"role": "system", "content": prompts.ARCHITECT_SYSTEM_PROMPT},
                    {"role": "user", "content": f"Design: {description}\nName: {tool_name}"}
                ],
                format="json"
            )
            
            data = self._parse_json(response['message']['content'])
            if not data:
                return None
            
            return ToolInterface(
                name=data.get('name', tool_name),
                description=data.get('description', description),
                parameters=data.get('parameters', []),
                return_type=data.get('return_type', 'str')
            )
        except Exception as e:
            logger.error(f"Architect failed: {e}")
            return None
    
    def _parse_json(self, content: str) -> Optional[dict]:
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            match = re.search(r'\{.*\}', content, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except:
                    pass
        return None


class Builder:
    """Generates implementation code."""
    
    def __init__(self):
        self.client = ollama.AsyncClient(host=settings.OLLAMA_HOST)
    
    async def generate_code(self, interface: ToolInterface) -> str:
        """Generate implementation code."""
        prompt = f"Create function '{interface.name}': {interface.description}\nParams: {json.dumps(interface.parameters)}"
        return await self._generate(prompts.BUILDER_SYSTEM_PROMPT, prompt)
    
    async def generate_test(self, interface: ToolInterface, code: str) -> str:
        """Generate pytest tests."""
        prompt = prompts.TEST_GENERATOR_PROMPT.format(code=code, interface=json.dumps({
            'name': interface.name, 'parameters': interface.parameters
        }))
        test = await self._generate("Write pytest tests.", prompt)
        
        if "import pytest" not in test:
            test = "import pytest\n" + test
        if f"from tool_under_test import" not in test:
            test = f"from tool_under_test import {interface.name}\n" + test
        return test
    
    async def fix_code(self, code: str, errors: List[str]) -> str:
        """Fix code based on errors."""
        prompt = prompts.CRITIC_FEEDBACK_PROMPT.format(errors="\n".join(errors), code=code)
        return await self._generate(prompts.BUILDER_SYSTEM_PROMPT, prompt)
    
    async def _generate(self, system: str, prompt: str) -> str:
        try:
            response = await self.client.chat(
                model=settings.MODEL_CODING,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}]
            )
            code = response['message']['content']
            
            # Strip markdown
            if "```python" in code:
                code = code.split("```python")[1].split("```")[0]
            elif "```" in code:
                code = code.split("```")[1].split("```")[0]
            return code.strip()
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            return ""


architect = Architect()
builder = Builder()
