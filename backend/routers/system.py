import socket
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from services.database import models
from backend import scheduler
from backend.dependencies import get_db
from backend.config import settings

router = APIRouter()

@router.get("/api/info")
async def get_system_info():
    return {
        "models": {
            "orchestrator": settings.MODEL_FAST,
            "planner": settings.MODEL_REASONING,
            "coder": settings.MODEL_CODING
        },
        "hostname": socket.gethostname()
    }

@router.get("/api/changelog")
async def get_changelog(db: Session = Depends(get_db)):
    logs = db.query(models.SystemLog).order_by(models.SystemLog.timestamp.desc()).limit(20).all()
    return logs

@router.get("/api/tasks/active")
async def get_active_tasks():
    if not scheduler.scheduler:
        return []
    jobs = scheduler.scheduler.get_jobs()
    return [{"id": job.id, "name": job.name, "next_run": str(job.next_run_time)} for job in jobs]
