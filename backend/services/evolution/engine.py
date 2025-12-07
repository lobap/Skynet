"""Evolution Engine - Self-improvement orchestration."""

from dataclasses import dataclass
from pathlib import Path
from backend.logger import logger
from .architect import architect, builder, ToolInterface
from .critic import critic
from .sandbox import sandbox


@dataclass
class EvolutionResult:
    """Evolution attempt result."""
    success: bool
    tool_name: str
    message: str
    code: str = ""
    attempts: int = 0
    git_synced: bool = False


class EvolutionEngine:
    """Orchestrates: Design → Build → Validate → Test → Deploy → Git."""
    
    MAX_RETRIES = 3
    TOOLS_DIR = Path(__file__).parent.parent / "tools" / "custom"
    
    async def evolve(self, description: str, tool_name: str, websocket=None) -> EvolutionResult:
        """Full evolution cycle."""
        logger.info(f"🧬 Evolving: {tool_name}")
        
        # 1. Design interface
        await self._status(websocket, f"🧬 Designing {tool_name}...")
        interface = await architect.design_interface(description, tool_name)
        if not interface:
            return EvolutionResult(False, tool_name, "Interface design failed")
        
        # 2. Build → Validate → Test loop
        for attempt in range(1, self.MAX_RETRIES + 1):
            await self._status(websocket, f"🔨 Building (attempt {attempt})...")
            
            code = await builder.generate_code(interface)
            if not code:
                continue
            
            # Validate
            await self._status(websocket, f"🔍 Validating...")
            validation = critic.validate(code, tool_name)
            
            if not validation.passed:
                code = await builder.fix_code(code, validation.errors)
                validation = critic.validate(code, tool_name)
                if not validation.passed:
                    continue
            
            # Test in sandbox
            await self._status(websocket, f"🧪 Testing...")
            test_code = await builder.generate_test(interface, code)
            if not test_code:
                continue
            
            result = await sandbox.run_tests(code, test_code)
            
            if result.success:
                # Deploy
                await self._status(websocket, f"🚀 Deploying...")
                deploy = await self._deploy(interface.name, code, test_code, websocket)
                
                if deploy["success"]:
                    return EvolutionResult(
                        True, interface.name,
                        f"Evolved: {interface.name}",
                        code, attempt, deploy.get("git_synced", False)
                    )
            else:
                code = await builder.fix_code(code, [result.error or "Test failed"])
        
        return EvolutionResult(False, tool_name, f"Failed after {self.MAX_RETRIES} attempts", attempts=self.MAX_RETRIES)
    
    async def _deploy(self, name: str, code: str, test_code: str, websocket=None) -> dict:
        """Save and persist to Git."""
        try:
            self.TOOLS_DIR.mkdir(parents=True, exist_ok=True)
            
            tool_path = self.TOOLS_DIR / f"{name}.py"
            test_path = self.TOOLS_DIR / f"test_{name}.py"
            
            tool_path.write_text(code)
            test_path.write_text(test_code)
            logger.info(f"📁 Saved: {name}.py")
            
            # Git persist
            await self._status(websocket, f"🔄 Syncing to Git...")
            git_synced = await self._git_persist(name, str(tool_path), str(test_path))
            
            return {"success": True, "git_synced": git_synced}
        except Exception as e:
            logger.error(f"Deploy failed: {e}")
            return {"success": False}
    
    async def _git_persist(self, name: str, tool_path: str, test_path: str) -> bool:
        """Commit and push to origin."""
        try:
            from ..tools.custom.git_ops import auto_commit
            
            result = await auto_commit(tool_path, f"Evolved: {name}")
            if result.get("success"):
                await auto_commit(test_path, f"Tests: {name}")
                return result.get("pushed", False)
            return False
        except Exception as e:
            logger.warning(f"Git persist failed: {e}")
            return False
    
    async def _status(self, websocket, message: str):
        """Send status update."""
        if websocket:
            try:
                import json
                await websocket.send_json({
                    "type": "terminal-output",
                    "content": json.dumps({"type": "evolution", "content": message})
                })
            except:
                pass
        logger.debug(message)


# Backwards compatibility
async def evolve_capability(description: str, tool_name: str, websocket=None) -> EvolutionResult:
    return await evolution_engine.evolve(description, tool_name, websocket)

evolution_engine = EvolutionEngine()
