"""Agent orchestrator - Main execution loop."""

import json
import inspect
import asyncio
import traceback
import os
import ast
import ollama
from sqlalchemy.orm import Session

from ..tools import registry
from ..tools.custom.planner import manage_plan
from ..database.models import ChatLog
from ..evolution.engine import evolution_engine
from backend.config import settings
from backend.logger import logger
from . import prompts
from .models import AgentResponse


class Agent:
    """Agent that executes goals using available tools."""
    
    MAX_FAILURES = settings.MAX_CONSECUTIVE_FAILURES
    MAX_LOOPS = settings.MAX_CONSECUTIVE_LOOPS
    SIG_HISTORY = settings.SIGNATURE_HISTORY_SIZE
    
    def __init__(self, db: Session, websocket=None, conv_id: int | None = None):
        self.db = db
        self.ws = websocket
        self.conv_id = conv_id
        self.client = ollama.AsyncClient(host=settings.OLLAMA_HOST)
        self.tool_map = {}
        self.signatures = []
        self.history = []
        self.failures = 0
        self.loops = 0
        self.empty_actions = 0
    
    async def run(self, goal: str):
        """Execute goal through iterative tool use."""
        await self._init(goal)
        
        is_simple = len(goal.split()) < 5 and not any(
            x in goal.lower() for x in ['fix', 'create', 'run', 'check', 'test', 'deploy']
        )
        
        total_failures = 0
        
        for step in range(settings.MAX_AGENT_STEPS):
            if total_failures >= 10:
                await self._log("assistant", "No puedo completar esta tarea. Por favor, reformula tu solicitud.")
                return
            
            # Build context
            ctx = self.history.copy()
            if not is_simple:
                try:
                    plan = await manage_plan("read")
                    ctx.append({"role": "system", "content": f"PLAN:\n{plan}\n\nFocus on ACTIVE step."})
                except:
                    pass
            
            if len(self.history) > 2 and any(x in self.history[-1]["content"] for x in ["Error", "Exception"]):
                ctx.append({"role": "system", "content": prompts.get_recovery_prompt()})
            
            # Get LLM response
            try:
                response = await self._get_response(ctx)
            except:
                return
            
            # Parse response
            try:
                parsed = AgentResponse.from_llm_response(response['message']['content'])
            except Exception as e:
                self.failures += 1
                if self.failures > self.MAX_FAILURES:
                    await self._send("system", "CRITICAL: Too many errors.")
                    return
                continue
            
            self.failures = 0
            thought = parsed.thought
            action = {"name": parsed.action.name, "parameters": parsed.action.parameters} if parsed.action else {}
            
            if thought:
                await self._send("agent-thought", thought)
                await self._send("terminal-output", json.dumps({"type": "thought", "content": thought}))
            
            if not action.get('name'):
                continue
            
            # Handle special actions
            if action['name'] == 'task_complete':
                await self._log("agent-action", "Task Completed.")
                return
            
            if action['name'] == 'reply_to_user':
                await self._log("assistant", action.get('parameters', {}).get('message', ''))
                return
            
            # Execute tool
            result = await self._execute(action)
            
            # Check for stop conditions
            if result and ("FORCE_STOP" in str(result) or "CRITICAL" in str(result)):
                await self._log("assistant", "No puedo continuar. Por favor, reformula tu solicitud.")
                return
            
            if self.loops > self.MAX_LOOPS:
                await self._log("assistant", "Bucle detectado. Detengo para evitar ciclos infinitos.")
                return
            
            if result and any(x in str(result) for x in ["Error", "Failed", "does not exist"]):
                total_failures += 1
            
            # Log execution
            cmd = self._format_cmd(action)
            await self._send("terminal-output", json.dumps({"type": "command", "command": cmd, "output": str(result)}))
            await self._log("agent-action", f"Executed {action['name']}")
            
            # Broadcast plan if updated
            if action.get('name') == 'manage_plan':
                await self._broadcast_plan()
            
            self.history.extend([
                {"role": "assistant", "content": json.dumps({"thought": thought, "action": action})},
                {"role": "user", "content": str(result)}
            ])
            
            await asyncio.sleep(2.0)
    
    async def _init(self, goal: str):
        """Initialize agent state."""
        if self.ws:
            await self._send("system", "Agent starting...")
        
        self.tool_map = registry.get_tool_map()
        self.history = [{"role": "system", "content": prompts.get_system_prompt()}]
        
        if self.conv_id:
            self._load_history()
        else:
            self.history.append({"role": "user", "content": goal})
    
    def _load_history(self):
        """Load conversation history from DB."""
        logs = self.db.query(ChatLog).filter(
            ChatLog.conversation_id == self.conv_id
        ).order_by(ChatLog.timestamp).all()
        
        for log in logs:
            if log.role == "agent-thought":
                self.history.append({"role": "assistant", "content": json.dumps({"thought": log.content, "action": {}})})
            elif log.role == "agent-action":
                self.history.append({"role": "user", "content": log.content})
            else:
                role = "user" if log.role == "user" else "assistant"
                self.history.append({"role": role, "content": log.content})
    
    async def _get_response(self, history: list) -> dict:
        """Get LLM response with timeout."""
        if self.ws:
            await self._send("agent-thought", "Thinking...")
        
        try:
            return await asyncio.wait_for(
                self.client.chat(model=settings.MODEL_FAST, messages=history, format="json"),
                timeout=120.0
            )
        except asyncio.TimeoutError:
            logger.error("LLM timeout")
            raise
        except Exception as e:
            logger.error(f"LLM error: {e}")
            raise
    
    async def _execute(self, action: dict) -> str:
        """Execute tool action."""
        if not action.get('name'):
            self.empty_actions += 1
            if self.empty_actions > 2:
                return "FORCE_STOP: Reformula tu solicitud."
            return "No action specified."
        
        self.empty_actions = 0
        name = action['name']
        params = action.get('parameters', {})
        sig = json.dumps({"tool": name, "params": params}, sort_keys=True)
        
        # Check if tool exists
        if name not in self.tool_map:
            return await self._evolve_tool(name, params)
        
        # Detect loops
        if sig in self.signatures[-2:]:
            self.loops += 1
            if self.loops > self.MAX_LOOPS:
                return "CRITICAL: Loop detected. Use 'reply_to_user'."
            return "Loop detected. Change strategy."
        
        self.loops = 0
        
        # Execute
        func = self.tool_map[name]
        try:
            call_params = params.copy()
            if 'websocket' in inspect.signature(func).parameters:
                call_params['websocket'] = self.ws
            
            if inspect.iscoroutinefunction(func):
                result = await func(**call_params)
            else:
                result = func(**call_params)
        except Exception as e:
            result = f"Error: {e}"
        
        self.signatures.append(sig)
        if len(self.signatures) > self.SIG_HISTORY:
            self.signatures.pop(0)
        
        return result
    
    async def _evolve_tool(self, name: str, params: dict) -> str:
        """Attempt to evolve new capability."""
        await self._send("terminal-output", json.dumps({
            "type": "evolution",
            "content": f"🧬 Capability gap: '{name}'. Evolving..."
        }))
        
        try:
            result = await evolution_engine.evolve(
                description=f"Tool '{name}' that performs: {json.dumps(params)}",
                tool_name=name,
                websocket=self.ws
            )
            
            if result.success:
                await self._send("terminal-output", json.dumps({
                    "type": "evolution",
                    "content": f"✅ Evolved: {result.tool_name}"
                }))
                self.tool_map = registry.get_tool_map()
                
                if name in self.tool_map:
                    func = self.tool_map[name]
                    if inspect.iscoroutinefunction(func):
                        return await func(**params)
                    return func(**params)
            else:
                await self._send("terminal-output", json.dumps({
                    "type": "evolution",
                    "content": f"❌ Failed: {result.message}"
                }))
        except Exception as e:
            logger.error(f"Evolution error: {e}")
        
        available = ", ".join(sorted(self.tool_map.keys())[:15])
        return f"Tool '{name}' unavailable. Use: {available}..."
    
    async def _send(self, role: str, content):
        """Send message via websocket."""
        if self.ws:
            await self.ws.send_text(json.dumps({"role": role, "content": content}))
    
    async def _log(self, role: str, content: str):
        """Send and persist message."""
        await self._send(role, content)
        self.db.add(ChatLog(role=role, content=content, conversation_id=self.conv_id))
        self.db.commit()
    
    def _format_cmd(self, action: dict) -> str:
        """Format command for display."""
        name = action.get('name', '')
        params = action.get('parameters', {})
        
        if name == 'execute_shell':
            return params.get('command', f"{name} {json.dumps(params)}")
        if name == 'run_command':
            return params.get('CommandLine', f"{name} {json.dumps(params)}")
        return f"{name} {json.dumps(params)}"
    
    async def _broadcast_plan(self):
        """Broadcast plan update."""
        try:
            root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            plan_file = os.path.join(root, "plan.json")
            
            if os.path.exists(plan_file):
                with open(plan_file) as f:
                    data = json.load(f)
                
                md = "".join(
                    f"- [{'x' if t['status'] == 'completed' else ' '}] {t['description']}\n"
                    for t in data.get("tasks", [])
                )
                await self._send("system", {"type": "plan_update", "content": md})
        except Exception as e:
            logger.error(f"Plan broadcast error: {e}")


async def run_agent_loop(goal: str, db: Session, websocket=None, conv_id: int | None = None):
    """Entry point for agent execution."""
    try:
        agent = Agent(db, websocket, conv_id)
        await agent.run(goal)
    except Exception as e:
        logger.error(f"FATAL: {traceback.format_exc()}")
        if websocket:
            await websocket.send_text(json.dumps({"role": "agent-action", "content": f"FATAL: {e}"}))