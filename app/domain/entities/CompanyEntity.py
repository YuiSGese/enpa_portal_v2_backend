import uuid
from sqlalchemy import Column, CHAR, String, DateTime, Date, Boolean, func
from app.core.database import Base

class CompanyEntity(Base):
    __tablename__ = "m_companies"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    company_name = Column(String(150), nullable=False)
    is_valid = Column(Boolean, nullable=False, server_default="0")       #chua hieu
    is_free_account = Column(Boolean, nullable=False, server_default="0") #tai khoan co consulting_flag se true
    delete_flg = Column(Boolean, nullable=True, server_default="0")
    create_datetime = Column(DateTime, server_default=func.now())
    update_datetime = Column(DateTime, server_default=func.now())