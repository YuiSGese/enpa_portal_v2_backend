from datetime import datetime
import uuid
from sqlalchemy import Column, Integer, String, DateTime, CHAR, Boolean, func
from app.core.database import Base

class ProvisionalRegistrationEntity(Base):
    __tablename__ = "m_provisional_registrations"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    company_name = Column(String(150), nullable=False)
    person_name = Column(String(100), nullable=False)
    email = Column(String(254), nullable=False)
    telephone_number = Column(String(100), nullable=False)
    note = Column(String(150), nullable=True)
    consulting_flag = Column(Boolean, nullable=False, server_default="0")
    invalid_flag= Column(Boolean, nullable=False, server_default="0")
    expiration_datetime = Column(DateTime, nullable=False)
    delete_flg = Column(Boolean, nullable=True, default=False)
    create_datetime = Column(DateTime, default=datetime.now)
    update_datetime = Column(DateTime, default=datetime.now, onupdate=datetime.now)
