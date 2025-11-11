import uuid
from sqlalchemy import Column, Integer, String, DateTime, CHAR, Boolean, func
from app.core.database import Base

class ProvisionalRegistration(Base):
    __tablename__ = "m_provisional_registrations"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    company_name = Column(String(150), nullable=False)
    person_name = Column(String(100), nullable=False)
    email = Column(String(254), nullable=False)
    telephone_number = Column(String(100), nullable=False)
    remarks = Column(String(150), nullable=True)
    consulting_flag = Column(CHAR(1), nullable=False)
    invalid_flag = Column(CHAR(1), nullable=False)
    expiration_datetime = Column(DateTime(timezone=True), nullable=False)
    update_datetime = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    create_datetime = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
