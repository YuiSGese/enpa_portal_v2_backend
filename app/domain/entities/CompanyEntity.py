from sqlalchemy import Column, Integer, String, DateTime, Date, Boolean, func
from app.core.database import Base

class CompanyEntity(Base):
    __tablename__ = "m_companies"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    company_name = Column(String(150), nullable=False)
    is_valid = Column(Boolean, nullable=False)       #chua hieu
    is_free_account = Column(Boolean, nullable=False) #chua hieu
    delete_flg = Column(Boolean, nullable=True, server_default="0")
    create_datetime = Column(DateTime, server_default=func.now())
    update_datetime = Column(DateTime, server_default=func.now())