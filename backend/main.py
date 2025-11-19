import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from fastapi import FastAPI, WebSocket, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi import WebSocketDisconnect
from sqlalchemy.orm import Session
from services.database import database, models
from services.agent import orchestrator
from dotenv import load_dotenv
import json
import socket

load_dotenv()

models.Base.metadata.create_all(bind=database.engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4321"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/info")
async def get_system_info():
    return {
        "model": os.getenv("OLLAMA_MODEL", "unknown"),
        "hostname": socket.gethostname()
    }

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

frontend_dist = os.path.join(os.path.dirname(__file__), "../frontend/dist")

app.mount("/_astro", StaticFiles(directory=os.path.join(frontend_dist, "_astro")), name="astro")

@app.get("/")
async def read_root():
    return FileResponse(os.path.join(frontend_dist, "index.html"))

@app.get("/api/conversations")
async def get_conversations(db: Session = Depends(get_db)):
    return db.query(models.Conversation).order_by(models.Conversation.created_at.desc()).all()

@app.get("/api/conversations/{conversation_id}")
async def get_conversation(conversation_id: int, db: Session = Depends(get_db)):
    logs = db.query(models.ChatLog).filter(models.ChatLog.conversation_id == conversation_id).order_by(models.ChatLog.timestamp).all()
    return [{"role": log.role, "content": log.content} for log in logs]

@app.post("/api/conversations")
async def create_conversation(db: Session = Depends(get_db)):
    new_chat = models.Conversation(title="New Chat")
    db.add(new_chat)
    db.commit()
    db.refresh(new_chat)
    return {"id": new_chat.id, "title": new_chat.title}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, db: Session = Depends(get_db)):
    await websocket.accept()
    # No initial history sent automatically, client requests it via REST or sends conversation_id
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            goal = message.get("goal", "")
            conversation_id = message.get("conversation_id")
            
            if not conversation_id:
                # Create new conversation if not provided
                new_chat = models.Conversation(title=goal[:30] + "..." if len(goal) > 30 else goal)
                db.add(new_chat)
                db.commit()
                db.refresh(new_chat)
                conversation_id = new_chat.id
                await websocket.send_text(json.dumps({"type": "conversation_created", "id": conversation_id, "title": new_chat.title}))
            
            # Save user message
            db.add(models.ChatLog(role="user", content=goal, conversation_id=conversation_id))
            db.commit()
            
            # Run agent
            await orchestrator.run_agent_loop(goal, websocket, db, conversation_id)
    except WebSocketDisconnect:
        print("Client disconnected")