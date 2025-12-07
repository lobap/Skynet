"""Plan management tool with AI-powered plan generation."""

import json
import os
from typing import Literal
from backend.config import settings
from ..ai_utils import consult_ai

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
PLAN_FILE = os.path.join(BASE_DIR, "plan.json")

ActionType = Literal["create", "read", "mark_done", "update"]


async def manage_plan(
    action: ActionType,
    tasks: list[str] | None = None,
    step_index: int | None = None,
    goal: str | None = None
) -> str:
    """Manage execution plan: create, read, mark_done, update."""
    try:
        if action == "create":
            return await _create_plan(goal, tasks)
        elif action == "read":
            return _read_plan()
        elif action == "mark_done":
            return _mark_done()
        elif action == "update":
            return _update_plan(tasks)
        return "Invalid action"
    except Exception as e:
        return f"Plan error: {e}"


async def _create_plan(goal: str | None, tasks: list[str] | None) -> str:
    """Create new plan from goal or task list."""
    if not goal and not tasks:
        return "Provide 'goal' or 'tasks'"
    
    if goal and not tasks:
        prompt = "Break into actionable steps. Return {\"tasks\": [\"step1\", \"step2\"...]}"
        response = await consult_ai(settings.MODEL_REASONING, prompt, f"Goal: {goal}", json_mode=True)
        try:
            tasks = json.loads(response).get("tasks", [])
        except:
            return f"Parse error: {response}"
    
    plan = {
        "tasks": [{"description": t, "status": "pending"} for t in (tasks or [])],
        "current_step_index": 0
    }
    
    with open(PLAN_FILE, 'w') as f:
        json.dump(plan, f, indent=2)
    
    return f"Plan created: {len(plan['tasks'])} steps"


def _read_plan() -> str:
    """Read current plan status."""
    if not os.path.exists(PLAN_FILE):
        return "No active plan"
    
    with open(PLAN_FILE, 'r') as f:
        plan = json.load(f)
    
    tasks = plan.get("tasks", [])
    idx = plan.get("current_step_index", 0)
    
    lines = []
    for i, task in enumerate(tasks):
        status = "[X]" if task["status"] == "completed" else ("[ ] (ACTIVE)" if i == idx else "[ ]")
        lines.append(f"{status} {i+1}: {task['description']}")
    
    if idx >= len(tasks):
        lines.append("ALL COMPLETE")
    
    return "\n".join(lines)


def _mark_done() -> str:
    """Mark current step as done."""
    if not os.path.exists(PLAN_FILE):
        return "No plan"
    
    with open(PLAN_FILE, 'r') as f:
        plan = json.load(f)
    
    idx = plan.get("current_step_index", 0)
    tasks = plan.get("tasks", [])
    
    if idx >= len(tasks):
        return "Already complete"
    
    tasks[idx]["status"] = "completed"
    plan["current_step_index"] = idx + 1
    
    with open(PLAN_FILE, 'w') as f:
        json.dump(plan, f, indent=2)
    
    next_step = tasks[idx + 1]["description"] if idx + 1 < len(tasks) else "Done"
    return f"Step {idx+1} done. Next: {next_step}"


def _update_plan(tasks: list[str] | None) -> str:
    """Update remaining steps."""
    if not tasks:
        return "Provide 'tasks'"
    
    if not os.path.exists(PLAN_FILE):
        return "No plan to update"
    
    with open(PLAN_FILE, 'r') as f:
        plan = json.load(f)
    
    idx = plan.get("current_step_index", 0)
    completed = plan.get("tasks", [])[:idx]
    new_tasks = [{"description": t, "status": "pending"} for t in tasks]
    
    plan["tasks"] = completed + new_tasks
    
    with open(PLAN_FILE, 'w') as f:
        json.dump(plan, f, indent=2)
    
    return f"Updated: {len(new_tasks)} new steps"
