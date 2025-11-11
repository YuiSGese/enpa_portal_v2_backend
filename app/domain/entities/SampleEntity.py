import uuid
from sqlalchemy import Column, CHAR, String, DateTime, Date, Boolean, func
from app.core.database import Base

class SampleEntity(Base):
    __tablename__ = "toolxx_sample"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # them truong cua table



    delete_flg = Column(Boolean, nullable=True, server_default="0")
    create_datetime = Column(DateTime, server_default=func.now())
    update_datetime = Column(DateTime, server_default=func.now())