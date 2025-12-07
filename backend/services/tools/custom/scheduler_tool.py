"""Task scheduling with APScheduler."""

import asyncio
from backend.scheduler import scheduler
from backend.services.agent import orchestrator
from backend.services.database import database

try:
    from apscheduler.triggers.cron import CronTrigger
except ImportError:
    CronTrigger = None


async def _run_agent(goal: str):
    """Run agent in headless mode."""
    db = database.SessionLocal()
    try:
        await orchestrator.run_agent_loop(goal, db, None)
    finally:
        db.close()


def schedule_task(prompt: str, cron: str) -> str:
    """Schedule recurring task with cron syntax.
    
    Format: minute hour day month day_of_week
    Example: "0 9 * * 1" (Monday 9 AM)
    """
    if not scheduler or not CronTrigger:
        return "APScheduler not available"
    
    try:
        parts = cron.split()
        if len(parts) != 5:
            return "Cron needs 5 fields"
        
        trigger = CronTrigger(
            minute=parts[0], hour=parts[1], 
            day=parts[2], month=parts[3], day_of_week=parts[4]
        )
        
        job = scheduler.add_job(_run_agent, trigger=trigger, args=[prompt], name=prompt[:50])
        return f"Scheduled: {prompt} (ID: {job.id})"
    except Exception as e:
        return f"Schedule error: {e}"
