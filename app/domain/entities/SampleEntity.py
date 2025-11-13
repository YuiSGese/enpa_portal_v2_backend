from datetime import datetime
import uuid
from sqlalchemy import Column, CHAR, String, DateTime, Date, Boolean, func
from app.core.database import Base

class SampleEntity(Base):
    __tablename__ = "toolxx_sample"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # them truong cua table



    delete_flg = Column(Boolean, nullable=True, default=False)
    create_datetime = Column(DateTime, default=datetime.now)
    update_datetime = Column(DateTime, default=datetime.now, onupdate=datetime.now)