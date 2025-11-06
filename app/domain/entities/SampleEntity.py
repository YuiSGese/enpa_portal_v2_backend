from sqlalchemy import Column, Integer, String, DateTime, Date, Boolean, func
from app.core.database import Base

class SampleEntity(Base):
    __tablename__ = "tool03_sample"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    delete_flg = Column(Boolean, nullable=True, server_default="0")
    create_datetime = Column(DateTime, server_default=func.now())
    update_datetime = Column(DateTime, server_default=func.now())