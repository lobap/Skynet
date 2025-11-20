import os
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from services.database import database, models
from backend import scheduler
from backend.routers import system, conversations
from backend.config import settings
from backend.logger import logger

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

models.Base.metadata.create_all(bind=database.engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting scheduler...")
    scheduler.start_scheduler()
    yield
    logger.info("Stopping scheduler...")
    scheduler.stop_scheduler()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4321"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"message": "Internal Server Error"},
    )

app.include_router(system.router)
app.include_router(conversations.router)

frontend_dist = os.path.join(os.path.dirname(__file__), "../frontend/dist")

app.mount("/_astro", StaticFiles(directory=os.path.join(frontend_dist, "_astro")), name="astro")

@app.get("/")
async def read_root():
    return FileResponse(os.path.join(frontend_dist, "index.html"))

@app.get("/favicon.svg")
async def read_favicon():
    return FileResponse(os.path.join(frontend_dist, "favicon.svg"))