from backend.scheduler import scheduler
from apscheduler.triggers.cron import CronTrigger
from services.agent import orchestrator
from services.database import database
import asyncio

async def run_scheduled_agent(goal: str):
    db = database.SessionLocal()
    try:
        # We pass None for websocket to run in headless mode
        await orchestrator.run_agent_loop(goal, db_session=db, websocket=None)
    finally:
        db.close()

def schedule_task(prompt: str, cron: str) -> str:
    """
    Schedules a recurring task using cron syntax (5 fields).
    Format: minute hour day month day_of_week
    Example: "0 9 * * 1" (Every Monday at 9 AM)
    """
    try:
        parts = cron.split()
        if len(parts) != 5:
            return "Error: Cron string must have 5 fields (minute hour day month day_of_week)"
            
        trigger = CronTrigger(
            minute=parts[0],
            hour=parts[1],
            day=parts[2],
            month=parts[3],
            day_of_week=parts[4]
        )
        
        job = scheduler.add_job(
            run_scheduled_agent,
            trigger=trigger,
            args=[prompt],
            name=prompt[:50]
        )
        
        return f"Task scheduled successfully: '{prompt}' (ID: {job.id})"
    except Exception as e:
        return f"Failed to schedule task: {str(e)}"
