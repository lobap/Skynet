"""FastAPI main application."""

import os
import asyncio
import ollama
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from backend.services.database import database, models
from backend import scheduler
from backend.routers import system, conversations
from backend.config import settings
from backend.logger import logger

# Initialize database
models.Base.metadata.create_all(bind=database.engine)

FRONTEND = os.path.join(os.path.dirname(__file__), "../frontend/dist")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """App lifecycle: startup and shutdown."""
    logger.info("Starting...")
    scheduler.start_scheduler()
    asyncio.create_task(_warmup_models())
    yield
    scheduler.stop_scheduler()
    logger.info("Stopped")


async def _warmup_models():
    """Warmup Ollama models in background."""
    try:
        client = ollama.AsyncClient(host=settings.OLLAMA_HOST)
        for model in [settings.MODEL_FAST, settings.MODEL_REASONING, settings.MODEL_CODING]:
            try:
                await client.chat(model=model, messages=[{"role": "user", "content": "ping"}])
                logger.info(f"Warmed: {model}")
            except Exception as e:
                logger.warning(f"Warmup failed: {model} - {e}")
    except Exception as e:
        logger.warning(f"Warmup init failed: {e}")


# App setup
app = FastAPI(title=settings.PROJECT_NAME, version=settings.VERSION, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4321"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def error_handler(request: Request, exc: Exception):
    logger.error(f"Error: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"message": "Internal Server Error"})


app.include_router(system.router)
app.include_router(conversations.router)

if os.path.exists(os.path.join(FRONTEND, "_astro")):
    app.mount("/_astro", StaticFiles(directory=os.path.join(FRONTEND, "_astro")), name="astro")


@app.get("/")
async def root():
    index = os.path.join(FRONTEND, "index.html")
    if os.path.exists(index):
        return FileResponse(index)
    return JSONResponse(status_code=404, content={"message": "Frontend not built"})


@app.get("/favicon.svg")
async def favicon():
    fav = os.path.join(FRONTEND, "favicon.svg")
    if os.path.exists(fav):
        return FileResponse(fav)
    return JSONResponse(status_code=404, content={"message": "Not found"})