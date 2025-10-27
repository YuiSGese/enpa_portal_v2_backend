    # -*- coding: utf-8 -*-
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

    # --- Input Schemas ---
class Tool03ProductRowInput(BaseModel):
        id: str # ID của dòng từ Frontend (để map kết quả)
        productCode: str = Field(..., description="商品管理番号")
        template: str = Field(..., description="テンプレート名 (例: テンプレートA)")
        startDate: str = Field(..., description="開始日時 (YYYY-MM-DDTHH:mm)")
        endDate: str = Field(..., description="終了日時 (YYYY-MM-DDTHH:mm)")
        priceType: str = Field(..., description="二重価格タイプ (当店通常価格, メーカー希望小売価格, クーポン利用で, custom)")
        customPriceType: Optional[str] = Field(None, description="店舗自由記入の二重価格文言")
        regularPrice: str = Field(..., description="通常価格（税込）（値）")
        salePrice: str = Field(..., description="セール価格（税込）（値）")
        saleText: Optional[str] = Field(None, description="セール文言 (12文字以内)")
        # discount: str # Sẽ được tính toán ở backend
        discountType: Optional[str] = Field("percent", description="割引表示タイプ ('percent' or 'yen')") # Mặc định là %
        mobileStartDate: Optional[str] = Field(None, description="楽天モバイル開始日時 (YYYY-MM-DDTHH:mm)")
        mobileEndDate: Optional[str] = Field(None, description="楽天モバイル終了日時 (YYYY-MM-DDTHH:mm)")

class Tool03CreateJobRequest(BaseModel):
        productRows: List[Tool03ProductRowInput]

    # --- Output Schemas ---
class Tool03CreateJobResponse(BaseModel):
        jobId: str
        status: str = "Pending"
        totalItems: int

    # --- Schemas for Job Status ---
class Tool03ImageResult(BaseModel):
        """Kết quả xử lý cho một ảnh."""
        status: str = Field(..., description="Trạng thái xử lý (Success, Error, Processing)")
        filename: Optional[str] = Field(None, description="Tên file ảnh đã tạo (nếu thành công)")
        message: Optional[str] = Field(None, description="Thông báo lỗi (nếu thất bại)")

class Tool03JobStatusResponse(BaseModel):
        """Thông tin trạng thái của Job."""
        jobId: str
        status: str = Field(..., description="Trạng thái tổng thể (Pending, Processing, Completed, Completed with errors, Failed)")
        progress: int = Field(..., description="Số ảnh đã xử lý")
        total: int = Field(..., description="Tổng số ảnh cần xử lý")
        results: Dict[str, Tool03ImageResult] = Field(..., description="Kết quả chi tiết cho từng ảnh (key là row.id)")
        startTime: float = Field(...)
        endTime: Optional[float] = Field(None)
        message: Optional[str] = Field(None, description="Thông báo lỗi chung (nếu Job Failed)") # Thêm message lỗi chung
    
