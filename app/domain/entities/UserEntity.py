from sqlalchemy import Column, Integer, String, DateTime, Date, Boolean, func
from app.core.database import Base

class UserEntity(Base):
    __tablename__ = "m_users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(150), nullable=False, unique=True)
    email = Column(String(254), nullable=True, unique=True)
    password = Column(String(128), nullable=False)
    last_login = Column(DateTime, nullable=True)
    chatwork_id = Column(String(9), nullable=False)
    company_id = Column(Integer, nullable=True)
    role_id = Column(Integer, nullable=True)
    delete_flg = Column(Boolean, nullable=True, server_default="0")
    create_datetime = Column(DateTime, server_default=func.now())
    update_datetime = Column(DateTime, server_default=func.now())

    def __init__(
        self,
        username: str,
        password: str,
        chatwork_id: str,
        email: str | None = None,
        company_id: Integer | None = None,
        role_id: int | None = None,
    ):
        self.username = username
        self.password = password
        self.chatwork_id = chatwork_id
        self.email = email
        self.company_id = company_id
        self.role_id = role_id