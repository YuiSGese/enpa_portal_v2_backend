from datetime import datetime
import uuid
from sqlalchemy import Column, CHAR, String, DateTime, Date, Boolean, func
from app.core.database import Base
import enum

class Role(enum.Enum):
    ADMIN = "ROLE_ADMIN"
    MANAGER = "ROLE_MANAGER"
    USER = "ROLE_USER"
    
class RoleEntity(Base):

    __tablename__ = "m_roles"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    role_name = Column(String(50), unique=True, nullable=False)
    note = Column(String(255), nullable=True)
    delete_flg = Column(Boolean, nullable=True, default=False)
    create_datetime = Column(DateTime, default=datetime.now)
    update_datetime = Column(DateTime, default=datetime.now, onupdate=datetime.now)
