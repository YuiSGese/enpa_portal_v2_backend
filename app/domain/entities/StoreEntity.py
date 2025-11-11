import uuid
from sqlalchemy import Column, Integer, String, DateTime, CHAR, Date, Boolean, func
from app.core.database import Base

class StoreEntity(Base):
    __tablename__ = "m_stores"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    store_name = Column(String(100), nullable=False)
    rlogin_id = Column(String(100), nullable=True)
    rlogin_pw = Column(String(100), nullable=True)
    path_name = Column(String(100), nullable=False)
    get_search_type = Column(String(10), nullable=True)
    company_id = Column(CHAR(36), nullable=True)
    ftp_password = Column(String(100), nullable=True)
    ftp_username = Column(String(100), nullable=True)
    consulting = Column(Boolean, nullable=True)
    end_date = Column(Date, nullable=True)
    start_date = Column(Date, nullable=True)
    telephone_number = Column(String(100), nullable=True)
     
    delete_flg = Column(Boolean, nullable=True, server_default="0")
    create_datetime = Column(DateTime, server_default=func.now())
    update_datetime = Column(DateTime, server_default=func.now())