try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.jobstores.memory import MemoryJobStore
    SCHEDULER_AVAILABLE = True
except ImportError:
    SCHEDULER_AVAILABLE = False
    AsyncIOScheduler = None
    MemoryJobStore = None

import logging

logging.basicConfig()
logging.getLogger('apscheduler').setLevel(logging.WARNING)

scheduler = AsyncIOScheduler(jobstores={'default': MemoryJobStore()}) if SCHEDULER_AVAILABLE else None


def start_scheduler():
    if scheduler and not scheduler.running:
        scheduler.start()
        print("APScheduler started.")
    elif not scheduler:
        print("APScheduler not available (module missing).")


def stop_scheduler():
    if scheduler and scheduler.running:
        scheduler.shutdown()
        print("APScheduler stopped.")
