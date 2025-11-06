# C:\GAKUSAI\enpo_v2\enpa_portal_v2_backend\app\tool10\schemas.py

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

# --- 1. Schema cho MỘT Hàng Sản Phẩm (Đổi tên từ CouponInput cũ) ---
# Tên này mô tả cấu trúc của một object trong mảng productRows
class ProductRowSchema(BaseModel):
    # Các trường dữ liệu mà Frontend gửi cho MỖI HÀNG
    id: Optional[int] = None
    template: str = Field(..., description="Template key (e.g. 1〜10)")
    file_name: str = Field(..., description="Tên file đầu ra (không có đuôi .jpg)")
    message1: str
    message2: Optional[str] = None
    available_condition: Optional[str] = None
    discount_value: int
    discount_unit: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


# --- 2. Schema KHỚP VỚI PAYLOAD TỪ FRONTEND ---
# Frontend gửi: { "productRows": [...] }
# Tên này (CouponInput) phải được giữ nguyên vì file router đang import nó
class CouponInput(BaseModel):
    productRows: List[ProductRowSchema] = Field(
        ..., 
        description="Danh sách các hàng dữ liệu sản phẩm/coupon từ Frontend."
    )


# --- 3. Schemas cho Phản hồi Job (Giữ nguyên) ---
class CouponJobResponse(BaseModel):
    jobId: str # Lưu ý: Frontend dùng camelCase 'jobId'
    status: str = "pending"
    total: int
    created_at: datetime


class CouponJobStatusResponse(BaseModel):
    jobId: str # Lưu ý: Frontend dùng camelCase 'jobId'
    status: str
    progress: float
    total: int
    completed: int
    failed: int
    message: Optional[str] = None
    result_files: Optional[List[str]] = None