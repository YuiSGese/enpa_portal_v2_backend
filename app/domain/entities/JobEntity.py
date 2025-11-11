# -*- coding: utf-8 -*-
from sqlalchemy import Column, Integer, String, DateTime, Text, func
from sqlalchemy.dialects.mysql import CHAR # Dùng CHAR(36) cho UUID
from app.core.database import Base
import uuid
from typing import Optional 

class JobEntity(Base):
    """
    Định nghĩa bảng 't_jobs' (Transaction Jobs).
    (Đã cập nhật 100% style giống UserEntity.py)
    """
    __tablename__ = 't_jobs'

    # --- Định nghĩa Cột (Columns) ---
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    job_id = Column(String(36), unique=True, nullable=False, index=True) 
    job_type = Column(String(50), nullable=False, index=True) 
    status = Column(String(50), nullable=False, default='PENDING', index=True) 
    
    # === SỬA LỖI: THÊM CÁC CỘT CÒN THIẾU ===
    total_items = Column(Integer, nullable=True, default=0) 
    
    job_payload = Column(Text, nullable=True) 
    job_results = Column(Text, nullable=True) 
    message = Column(Text, nullable=True) 

    # (Cột cho FTP)
    ftp_status_gold = Column(String(50), nullable=True, default='IDLE')
    ftp_error_gold = Column(Text, nullable=True)
    ftp_status_rcabinet = Column(String(50), nullable=True, default='IDLE')
    ftp_error_rcabinet = Column(Text, nullable=True)
    # === KẾT THÚC SỬA LỖI ===

    create_datetime = Column(DateTime, server_default=func.now())
    update_datetime = Column(DateTime, server_default=func.now()) 

    # --- Hàm Khởi tạo (__init__) ---
    # Style giống UserEntity.py
    
    def __init__(
        self,
        job_id: str,
        job_type: str,
        status: str = 'PENDING',
        job_payload: Optional[str] = None,
        total_items: int = 0  # === SỬA LỖI: THÊM total_items VÀO __init__ ===
    ):
        """
        Hàm khởi tạo khi API tạo một job mới.
        """
        self.job_id = job_id
        self.job_type = job_type
        self.status = status
        self.job_payload = job_payload
        self.total_items = total_items # === SỬA LỖI: GÁN total_items ===
        # (Các cột khác sẽ dùng default)