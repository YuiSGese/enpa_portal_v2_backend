import uuid
from sqlalchemy import Column, Integer, String, DateTime, CHAR, Boolean, func
from app.core.database import Base

class UserEntity(Base):
    __tablename__ = "m_users"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(150), nullable=False, unique=True)
    email = Column(String(254), nullable=True, unique=True)
    password = Column(String(128), nullable=False)
    last_login = Column(DateTime, nullable=True)
    company_id = Column(CHAR(36), nullable=True)
    role_id = Column(CHAR(36), nullable=True)
    is_mail_verified = Column(Boolean, nullable=True, server_default="0")
    delete_flg = Column(Boolean, nullable=True, server_default="0")
    create_datetime = Column(DateTime, server_default=func.now())
    update_datetime = Column(DateTime, server_default=func.now())

    def __init__(
        self,
        username: str,
        password: str,
        email: str | None = None,
        company_id: str | None = None,
        role_id: str | None = None,
    ):
        self.username = username
        self.password = password
        self.email = email
        self.company_id = company_id
        self.role_id = role_id