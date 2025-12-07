"""System information routes."""

import socket
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.services.database import models
from backend import scheduler
from backend.dependencies import get_db
from backend.config import settings

router = APIRouter(prefix="/api")


@router.get("/info")
async def info():
    """System and model info."""
    return {
        "models": {
            "orchestrator": settings.MODEL_FAST,
            "planner": settings.MODEL_REASONING,
            "coder": settings.MODEL_CODING
        },
        "hostname": socket.gethostname()
    }


@router.get("/changelog")
async def changelog(db: Session = Depends(get_db)):
    """Recent system logs."""
    return db.query(models.SystemLog).order_by(models.SystemLog.timestamp.desc()).limit(20).all()


@router.get("/tasks/active")
async def active_tasks():
    """Scheduled jobs."""
    if not scheduler.scheduler:
        return []
    return [{"id": j.id, "name": j.name, "next_run": str(j.next_run_time)} for j in scheduler.scheduler.get_jobs()]
