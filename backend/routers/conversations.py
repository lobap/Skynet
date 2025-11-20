import json
import asyncio
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from services.database import models
from services.agent import orchestrator
from backend.dependencies import get_db
from backend.logger import logger

router = APIRouter()

@router.get("/api/conversations")
async def get_conversations(db: Session = Depends(get_db)):
    return db.query(models.Conversation).order_by(models.Conversation.created_at.desc()).all()

@router.get("/api/conversations/{conversation_id}")
async def get_conversation(conversation_id: int, db: Session = Depends(get_db)):
    logs = db.query(models.ChatLog).filter(models.ChatLog.conversation_id == conversation_id).order_by(models.ChatLog.timestamp).all()
    return [{"role": log.role, "content": log.content} for log in logs]

@router.post("/api/conversations")
async def create_conversation(db: Session = Depends(get_db)):
    new_chat = models.Conversation(title="New Chat")
    db.add(new_chat)
    db.commit()
    db.refresh(new_chat)
    return {"id": new_chat.id, "title": new_chat.title}

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, db: Session = Depends(get_db)):
    await websocket.accept()
    agent_task = None
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("action") == "stop":
                if agent_task and not agent_task.done():
                    agent_task.cancel()
                    try:
                        await agent_task
                    except asyncio.CancelledError:
                        pass
                    await websocket.send_text(json.dumps({"role": "system", "content": "Processing stopped by user."}))
                continue

            goal = message.get("goal", "")
            conversation_id = message.get("conversation_id")
            
            if not conversation_id:
                new_chat = models.Conversation(title=goal[:30] + "..." if len(goal) > 30 else goal)
                db.add(new_chat)
                db.commit()
                db.refresh(new_chat)
                conversation_id = new_chat.id
                await websocket.send_text(json.dumps({"type": "conversation_created", "id": conversation_id, "title": new_chat.title}))
            
            db.add(models.ChatLog(role="user", content=goal, conversation_id=conversation_id))
            db.commit()
            
            if agent_task and not agent_task.done():
                agent_task.cancel()
                try:
                    await agent_task
                except asyncio.CancelledError:
                    pass
            
            agent_task = asyncio.create_task(orchestrator.run_agent_loop(goal, db, websocket, conversation_id))
            
    except WebSocketDisconnect:
        if agent_task and not agent_task.done():
            agent_task.cancel()
        logger.info("Client disconnected")
