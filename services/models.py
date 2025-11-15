from sqlalchemy import Column, Integer, String, DateTime
from .database import Base
from datetime import datetime

class ChatLog(Base):
    __tablename__ = "chat_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    role = Column(String)
    content = Column(String)