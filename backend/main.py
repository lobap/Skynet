import os
import ollama
import asyncio
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

models.Base.metadata.create_all(bind=database.engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting scheduler...")
    scheduler.start_scheduler()

    try:
        logger.info("Warming up Ollama models...")
        client = ollama.AsyncClient(host=settings.OLLAMA_HOST)
        
        async def warm_up(model):
            try:
                logger.info(f"Warming up {model}...")
                await client.chat(model=model, messages=[{"role": "user", "content": "ping"}])
                logger.info(f"Warm-up complete for {model}")
            except Exception as e:
                logger.warning(f"Warm-up failed for {model}: {e}")

        # Fire and forget warm-up for all models
        asyncio.create_task(asyncio.gather(
            warm_up(settings.MODEL_FAST),
            warm_up(settings.MODEL_REASONING),
            warm_up(settings.MODEL_CODING)
        ))
    except Exception as e:
        logger.warning(f"Ollama warm-up initiation failed: {e}")

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

if os.path.exists(os.path.join(frontend_dist, "_astro")):
    app.mount("/_astro", StaticFiles(directory=os.path.join(frontend_dist, "_astro")), name="astro")

@app.get("/")
async def read_root():
    if os.path.exists(os.path.join(frontend_dist, "index.html")):
        return FileResponse(os.path.join(frontend_dist, "index.html"))
    return JSONResponse(content={"message": "Frontend not built. Please run npm run build in frontend directory."}, status_code=404)

@app.get("/favicon.svg")
async def read_favicon():
    if os.path.exists(os.path.join(frontend_dist, "favicon.svg")):
        return FileResponse(os.path.join(frontend_dist, "favicon.svg"))
    return JSONResponse(content={"message": "Not found"}, status_code=404)