from sqlalchemy import Column, Integer, String, DateTime, Date, Boolean, func
from app.core.database import Base

class RoleEntity(Base):
    __tablename__ = "m_roles"

    id = Column(Integer, primary_key=True, index=True)
    role_name = Column(String(50), unique=True, nullable=False)
    description = Column(String(255), nullable=True)
    delete_flg = Column(Boolean, nullable=True, server_default="0")
    create_datetime = Column(DateTime, server_default=func.now())
    update_datetime = Column(DateTime, server_default=func.now())
