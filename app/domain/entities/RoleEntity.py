import uuid
from sqlalchemy import Column, CHAR, String, DateTime, Date, Boolean, func
from app.core.database import Base
import enum

class Role(enum.Enum):
    ADMIN = "ROLE_ADMIN"
    USER = "ROLE_USER"
    
class RoleEntity(Base):

    __tablename__ = "m_roles"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    role_name = Column(String(50), unique=True, nullable=False)
    description = Column(String(255), nullable=True)
    delete_flg = Column(Boolean, nullable=True, server_default="0")
    create_datetime = Column(DateTime, server_default=func.now())
    update_datetime = Column(DateTime, server_default=func.now())
