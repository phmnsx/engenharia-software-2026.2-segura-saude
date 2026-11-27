from sqlalchemy import Column, String, JSON, DateTime, Enum
from datetime import datetime
from common.outbox.db import Base
import uuid

class OutboxMessage(Base):
    __tablename__ = "outbox_messages"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    queue_name = Column(String, nullable=False)
    payload = Column(JSON, nullable=False)
    status = Column(String, default="PENDENTE")
    created_at = Column(DateTime, default=datetime.utcnow)