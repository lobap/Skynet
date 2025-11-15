import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from fastapi import FastAPI, WebSocket, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi import WebSocketDisconnect
from sqlalchemy.orm import Session
from services import database, models, orchestrator
import json

models.Base.metadata.create_all(bind=database.engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4321"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

frontend_dist = os.path.join(os.path.dirname(__file__), "../frontend/dist")

app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="static")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, db: Session = Depends(get_db)):
    await websocket.accept()
    for log in db.query(models.ChatLog).all():
        await websocket.send_text(json.dumps({"role": log.role, "content": log.content}))
    await websocket.send_text(json.dumps({"role": "agent-action", "content": "WebSocket connected successfully"}))
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            goal = message.get("goal", "")
            db.add(models.ChatLog(role="user", content=goal))
            db.commit()
            await orchestrator.run_agent_loop(goal, websocket, db)
    except WebSocketDisconnect:
        print("Client disconnected")