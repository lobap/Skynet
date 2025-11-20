import json
import os
import asyncio
from ..ai_utils import consult_ai

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
PLAN_FILE = os.path.join(BASE_DIR, "plan.json")
MODEL_REASONING = os.getenv("MODEL_REASONING", "deepseek-r1:1.5b")

async def manage_plan(action: str, tasks: list[str] = None, step_index: int = None, goal: str = None) -> str:
    """
    Manages the execution plan.
    - create: Uses DeepSeek to generate a detailed plan from a goal.
    - read: Returns current status.
    - mark_done: Advances step.
    - update: Modifies future steps.
    """
    try:
        if action == "create":
            if not goal and not tasks:
                return "Error: Provide 'goal' for AI generation or 'tasks' list for manual creation."
            
            if goal and not tasks:
                # AI Plan Generation
                system_prompt = """You are a Strategic Planner. 
                Break down the user's goal into a sequential, logical list of actionable steps.
                Each step must be clear and use available tools.
                Return a JSON object with a key "tasks" containing a list of strings.
                Example: {"tasks": ["Install nginx", "Configure firewall", "Start service"]}
                """
                response = await consult_ai(MODEL_REASONING, system_prompt, f"Goal: {goal}", json_mode=True)
                try:
                    data = json.loads(response)
                    tasks = data.get("tasks", [])
                except:
                    return f"Error parsing AI plan: {response}"

            plan = {
                "tasks": [{"description": t, "status": "pending"} for t in tasks],
                "current_step_index": 0
            }
            
            with open(PLAN_FILE, 'w') as f:
                json.dump(plan, f, indent=2)
                
            return f"Plan created with {len(tasks)} steps."
            
        elif action == "read":
            if not os.path.exists(PLAN_FILE):
                return "No active plan."
                
            with open(PLAN_FILE, 'r') as f:
                plan = json.load(f)
                
            tasks = plan.get("tasks", [])
            idx = plan.get("current_step_index", 0)
            
            output = []
            for i, task in enumerate(tasks):
                status = "[ ]"
                if task["status"] == "completed":
                    status = "[X]"
                elif i == idx:
                    status = "[ ] (ACTIVE)"
                
                output.append(f"{status} Step {i+1}: {task['description']}")
                
            if idx >= len(tasks):
                output.append("ALL STEPS COMPLETED.")
                
            return "\n".join(output)
            
        elif action == "mark_done":
            if not os.path.exists(PLAN_FILE):
                return "Error: No active plan to mark done."
                
            with open(PLAN_FILE, 'r') as f:
                plan = json.load(f)
                
            idx = plan.get("current_step_index", 0)
            tasks = plan.get("tasks", [])
            
            if idx < len(tasks):
                tasks[idx]["status"] = "completed"
                plan["current_step_index"] = idx + 1
                
                with open(PLAN_FILE, 'w') as f:
                    json.dump(plan, f, indent=2)
                
                next_step = "None (Plan Completed)"
                if idx + 1 < len(tasks):
                    next_step = tasks[idx+1]["description"]
                    
                return f"Step {idx+1} marked as done. Next step: {next_step}"
            else:
                return "Plan already completed."

        elif action == "update":
            if not tasks:
                return "Error: 'tasks' list is required for 'update'."
            
            if not os.path.exists(PLAN_FILE):
                return "Error: No active plan to update. Use 'create'."
                
            with open(PLAN_FILE, 'r') as f:
                plan = json.load(f)
                
            idx = plan.get("current_step_index", 0)
            # Keep completed tasks
            current_tasks = plan.get("tasks", [])[:idx]
            # Add new tasks
            new_tasks = [{"description": t, "status": "pending"} for t in tasks]
            
            plan["tasks"] = current_tasks + new_tasks
            
            with open(PLAN_FILE, 'w') as f:
                json.dump(plan, f, indent=2)
                
            return f"Plan updated. Steps from {idx+1} onwards replaced."
            
        return "Invalid action. Use create, read, mark_done, or update."
        
    except Exception as e:
        return f"Error managing plan: {str(e)}"
