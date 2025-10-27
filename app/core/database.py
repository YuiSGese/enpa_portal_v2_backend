# app/core/database.py
from __future__ import annotations
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


def _make_url() -> str:
    """
    Kết nối MariaDB qua TCP. Mặc định dùng mariadb-connector.
    Nếu muốn dùng PyMySQL (fallback), đổi 'mariadb+mariadbconnector' → 'mysql+pymysql'.
    """
    return (
        f"mariadb+mariadbconnector://{settings.DB_USER}:{settings.DB_PASS}"
        f"@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
    )


# Engine: KHÔNG truyền connect_args/unix_socket để tránh rẽ sang socket
engine: Engine = create_engine(
    _make_url(),
    echo=bool(settings.DB_ECHO),
    pool_pre_ping=True,
    pool_recycle=settings.DB_POOL_RECYCLE,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    isolation_level=settings.DB_ISOLATION_LEVEL,
)

# Session factory
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    class_=Session,
)

# Declarative Base
class Base(DeclarativeBase):
    pass

# FastAPI dependency
def get_db() -> Generator[Session, None, None]:
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()