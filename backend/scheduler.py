"""APScheduler integration for scheduled tasks."""

import logging
from backend.logger import logger

try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.jobstores.memory import MemoryJobStore
    scheduler = AsyncIOScheduler(jobstores={'default': MemoryJobStore()})
except ImportError:
    scheduler = None

logging.getLogger('apscheduler').setLevel(logging.WARNING)


def start_scheduler():
    """Start the scheduler if available."""
    if scheduler and not scheduler.running:
        scheduler.start()
        logger.info("Scheduler started")
    elif not scheduler:
        logger.warning("APScheduler not installed")


def stop_scheduler():
    """Stop the scheduler."""
    if scheduler and scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler stopped")
