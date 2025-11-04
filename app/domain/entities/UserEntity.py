from sqlalchemy import Column, Integer, String, DateTime, Date, Boolean, func
from app.core.database import Base

class UserEntity(Base):
    __tablename__ = "m_users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_name = Column(String(100), unique=True, index=True, nullable=False)
    password = Column(String(255), nullable=False)  
    email = Column(String(120), unique=True, index=True, nullable=True)
    path_name = Column(String(100), nullable=True)
    company_id = Column(String(100), nullable=True)
    store_name = Column(String(100), nullable=True)
    rlogin_id = Column(String(100), nullable=True)
    rlogin_pw = Column(String(100), nullable=True)
    service_secret = Column(String(100), nullable=True)
    license_key = Column(String(100), nullable=True)
    ftp_username = Column(String(100), nullable=True)
    ftp_password = Column(String(100), nullable=True)
    telephone_number = Column(String(100), nullable=True)
    get_search_type = Column(String(100), nullable=True)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    consulting = Column(Boolean, nullable=True)
    role_id = Column(Integer, nullable=True)
    delete_flg = Column(Boolean, nullable=True, server_default="0")
    create_datetime = Column(DateTime, server_default=func.now())
    update_datetime = Column(DateTime, server_default=func.now())