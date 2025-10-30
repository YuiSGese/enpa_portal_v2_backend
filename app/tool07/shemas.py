from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, DECIMAL, JSON, UniqueConstraint
from app.core.database import Base # Import Base từ app/core/database.py

# --- SQLAlchemy Models (ORM) ---

class SettingsModel(Base):
    """SQLAlchemy Model cho bảng settings (Tool07)."""
    __tablename__ = "settings"
    
    id = Column(Integer, primary_key=True) # Chỉ có id=1
    template_id = Column(String(50), nullable=False)
    min_review_placement = Column(Integer, nullable=False)
    min_review_display = Column(Integer, nullable=False)
    pc_width = Column(Integer, nullable=False)
    pc_unit = Column(String(5), nullable=False)
    sp_width = Column(Integer, nullable=False)
    sp_unit = Column(String(5), nullable=False)
    pc_position = Column(JSON) # Sử dụng JSON cho MariaDB/MySQL
    sp_position = Column(JSON) # Sử dụng JSON cho MariaDB/MySQL
    last_updated = Column(DateTime)

class ItemReviewModel(Base):
    """SQLAlchemy Model cho bảng review_data (Tool07)."""
    __tablename__ = "review_data"

    path_name = Column(String(255), primary_key=True)
    manageNumber = Column(String(50), primary_key=True)
    review_count = Column(Integer, nullable=False)
    review_averageRating = Column(DECIMAL(3, 2), nullable=False)
    template_id = Column(String(50), nullable=False)
    img_remote_url = Column(Text, nullable=False)
    img_width = Column(Integer, nullable=False)
    img_unit = Column(String(5), nullable=False)
    delete_flg = Column(String(1), nullable=False) # '0' hoặc '2'
    Update_datetime = Column(DateTime)
    
    __table_args__ = (
        UniqueConstraint('path_name', 'manageNumber', name='uq_item_review'),
    )

# --- Pydantic Schemas (Request/Response) ---

class SettingsBase(BaseModel):
    """Schema cơ sở cho cài đặt công cụ."""
    template_id: str
    min_review_placement: int
    min_review_display: int
    pc_width: int
    pc_unit: str
    sp_width: int
    sp_unit: str
    pc_position: List[str]
    sp_position: List[str]

class SettingsRead(SettingsBase):
    """Schema đọc cài đặt (bao gồm ID và last_updated)."""
    id: int
    last_updated: Optional[datetime] = None

    class Config:
        orm_mode = True # Hỗ trợ ánh xạ từ Model SQLAlchemy
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

class ItemReviewData(BaseModel):
    """Schema cho dữ liệu đánh giá sản phẩm đã xử lý."""
    path_name: str
    manageNumber: str
    review_count: int
    review_averageRating: float
    template_id: str
    img_remote_url: str
    img_width: int
    img_unit: str
    delete_flg: str
    Update_datetime: Optional[datetime] = None

    class Config:
        orm_mode = True
