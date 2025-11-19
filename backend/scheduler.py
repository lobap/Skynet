from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.memory import MemoryJobStore
import logging

# Configure logging
logging.basicConfig()
logging.getLogger('apscheduler').setLevel(logging.DEBUG)

# Global scheduler instance
scheduler = AsyncIOScheduler(jobstores={'default': MemoryJobStore()})

def start_scheduler():
    if not scheduler.running:
        scheduler.start()
        print("APScheduler started.")

def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        print("APScheduler stopped.")
