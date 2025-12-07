"""Sandbox execution for testing generated code."""

import sys
import asyncio
import tempfile
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
from backend.logger import logger


@dataclass
class SandboxResult:
    """Result of sandbox execution."""
    success: bool
    output: str = ""
    error: Optional[str] = None


class SandboxRunner:
    """Runs code in isolation with timeout."""
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
    
    async def run_tests(self, tool_code: str, test_code: str) -> SandboxResult:
        """Execute tests in isolated environment."""
        with tempfile.TemporaryDirectory(prefix="skynet_") as tmpdir:
            tmp = Path(tmpdir)
            (tmp / "tool_under_test.py").write_text(tool_code)
            (tmp / "test_tool.py").write_text(test_code)
            (tmp / "__init__.py").write_text("")
            
            try:
                proc = await asyncio.create_subprocess_exec(
                    sys.executable, "-m", "pytest", "test_tool.py", "-v", "--tb=short",
                    cwd=str(tmp),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env={**__import__('os').environ, "PYTHONPATH": str(tmp)}
                )
                
                stdout, stderr = await asyncio.wait_for(proc.communicate(), self.timeout)
                output = stdout.decode('utf-8', errors='replace')
                
                if proc.returncode == 0:
                    logger.info("✅ Sandbox tests passed")
                    return SandboxResult(True, output)
                else:
                    return SandboxResult(False, output, stderr.decode('utf-8', errors='replace'))
                    
            except asyncio.TimeoutError:
                proc.kill()
                return SandboxResult(False, "", f"Timeout after {self.timeout}s")
            except Exception as e:
                return SandboxResult(False, "", str(e))


sandbox = SandboxRunner()
