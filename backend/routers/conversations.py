"""Conversation and WebSocket routes."""

import json
import asyncio
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from backend.services.database import models
from backend.services.agent import orchestrator
from backend.dependencies import get_db
from backend.logger import logger

router = APIRouter(prefix="/api")


@router.get("/conversations")
async def get_conversations(db: Session = Depends(get_db)):
    """List all conversations."""
    return db.query(models.Conversation).order_by(models.Conversation.created_at.desc()).all()


@router.get("/conversations/{cid}")
async def get_conversation(cid: int, db: Session = Depends(get_db)):
    """Get conversation by ID."""
    logs = db.query(models.ChatLog).filter(
        models.ChatLog.conversation_id == cid
    ).order_by(models.ChatLog.timestamp).all()
    return [{"role": l.role, "content": l.content, "timestamp": l.timestamp.isoformat()} for l in logs]


@router.get("/conversations/{cid}/logs")
async def get_logs(cid: int, limit: int = 50, offset: int = 0, db: Session = Depends(get_db)):
    """Paginated chat logs."""
    total = db.query(models.ChatLog).filter(models.ChatLog.conversation_id == cid).count()
    logs = db.query(models.ChatLog).filter(
        models.ChatLog.conversation_id == cid
    ).order_by(models.ChatLog.timestamp.desc()).offset(offset).limit(limit).all()
    
    return {
        "total": total, "offset": offset, "limit": limit,
        "has_more": offset + limit < total,
        "logs": [{"id": l.id, "role": l.role, "content": l.content, "timestamp": l.timestamp.isoformat()} 
                 for l in reversed(logs)]
    }


@router.get("/chat/latest")
async def get_latest(db: Session = Depends(get_db)):
    """Get latest conversation with logs."""
    conv = db.query(models.Conversation).order_by(models.Conversation.created_at.desc()).first()
    if not conv:
        return {"conversation": None, "logs": []}
    
    logs = db.query(models.ChatLog).filter(
        models.ChatLog.conversation_id == conv.id
    ).order_by(models.ChatLog.timestamp.desc()).limit(50).all()
    
    return {
        "conversation": {"id": conv.id, "title": conv.title, "created_at": conv.created_at.isoformat()},
        "logs": [{"id": l.id, "role": l.role, "content": l.content, "timestamp": l.timestamp.isoformat()} 
                 for l in reversed(logs)],
        "has_more": len(logs) == 50
    }


@router.post("/conversations")
async def create_conversation(db: Session = Depends(get_db)):
    """Create new conversation."""
    conv = models.Conversation(title="New Chat")
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return {"id": conv.id, "title": conv.title}


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, db: Session = Depends(get_db)):
    """WebSocket for real-time agent communication."""
    await websocket.accept()
    agent_task: asyncio.Task | None = None
    
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            
            # Handle stop action
            if msg.get("action") == "stop":
                if agent_task and not agent_task.done():
                    agent_task.cancel()
                    try:
                        await agent_task
                    except asyncio.CancelledError:
                        pass
                    await websocket.send_text(json.dumps({"role": "system", "content": "Stopped"}))
                continue
            
            goal = msg.get("goal", "")
            cid = msg.get("conversation_id")
            
            # Create conversation if needed
            if not cid:
                conv = models.Conversation(title=goal[:30] + "..." if len(goal) > 30 else goal)
                db.add(conv)
                db.commit()
                db.refresh(conv)
                cid = conv.id
                await websocket.send_text(json.dumps({
                    "type": "conversation_created", "id": cid, "title": conv.title
                }))
            
            # Log user message
            db.add(models.ChatLog(role="user", content=goal, conversation_id=cid))
            db.commit()
            
            # Cancel existing task
            if agent_task and not agent_task.done():
                agent_task.cancel()
                try:
                    await agent_task
                except asyncio.CancelledError:
                    pass
            
            # Start agent
            agent_task = asyncio.create_task(
                orchestrator.run_agent_loop(goal, db, websocket, cid)
            )
            
    except WebSocketDisconnect:
        if agent_task and not agent_task.done():
            agent_task.cancel()
        logger.info("Client disconnected")
