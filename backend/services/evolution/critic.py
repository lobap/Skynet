"""Code critic with static analysis for generated code."""

import ast
import re
from dataclasses import dataclass, field
from typing import List, Tuple

FORBIDDEN_PATTERNS: List[Tuple[str, str]] = [
    (r'os\.system\s*\(', "Use execute_shell instead"),
    (r'subprocess\.(run|call|Popen)', "Use execute_shell wrapper"),
    (r'\beval\s*\(', "eval() forbidden"),
    (r'\bexec\s*\(', "exec() forbidden"),
    (r'__import__\s*\(', "Dynamic imports forbidden"),
]

PROTECTED_PATHS = ['main.py', 'orchestrator.py', 'config.py', 'registry.py']
BANNED_IMPORTS = ['ctypes', 'multiprocessing']


@dataclass
class ValidationResult:
    """Result of code validation."""
    passed: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class CodeCritic:
    """Validates generated code for safety and correctness."""
    
    def validate(self, code: str, tool_name: str = "") -> ValidationResult:
        """Run all validation checks."""
        errors, warnings = [], []
        
        # Syntax check
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return ValidationResult(False, [f"Syntax error L{e.lineno}: {e.msg}"])
        
        # Pattern checks
        for pattern, msg in FORBIDDEN_PATTERNS:
            if re.search(pattern, code):
                errors.append(msg)
        
        # Import checks
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in BANNED_IMPORTS:
                        errors.append(f"Banned import: {alias.name}")
            elif isinstance(node, ast.ImportFrom) and node.module:
                if node.module.split('.')[0] in BANNED_IMPORTS:
                    errors.append(f"Banned import: {node.module}")
        
        # Function check
        funcs = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        if not funcs:
            errors.append("No functions defined")
        
        # Protected path check
        for path in PROTECTED_PATHS:
            if f'"{path}"' in code or f"'{path}'" in code:
                errors.append(f"Protected file access: {path}")
        
        return ValidationResult(len(errors) == 0, errors, warnings)


critic = CodeCritic()
