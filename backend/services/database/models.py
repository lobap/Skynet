"""SQLAlchemy models."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base


class Conversation(Base):
    """Chat conversation."""
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, default="New Chat")
    created_at = Column(DateTime, default=datetime.utcnow)
    logs = relationship("ChatLog", back_populates="conversation")


class ChatLog(Base):
    """Individual chat message."""
    __tablename__ = "chat_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"))
    timestamp = Column(DateTime, default=datetime.utcnow)
    role = Column(String)
    content = Column(String)
    conversation = relationship("Conversation", back_populates="logs")


class SystemLog(Base):
    """System event log."""
    __tablename__ = "system_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    type = Column(String)
    title = Column(String)
    description = Column(String)
    commit_hash = Column(String, nullable=True)