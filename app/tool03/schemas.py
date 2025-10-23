# -*- coding: utf-8 -*-
from pydantic import BaseModel, Field
from typing import List, Optional

# Định nghĩa cấu trúc dữ liệu cho một hàng sản phẩm gửi từ Frontend
class Tool03ProductRowInput(BaseModel):
    id: str # ID tạm thời từ frontend, dùng để map kết quả
    productCode: str = Field(..., alias="productCode", description="商品管理番号")
    template: str = Field(..., description="テンプレート名 (例: 'テンプレートA')")
    startDate: str = Field(..., alias="startDate", description="セール開始日時 (ISO format)")
    endDate: str = Field(..., alias="endDate", description="セール終了日時 (ISO format)")
    priceType: str = Field(..., alias="priceType", description="二重価格タイプ ('当店通常価格', 'メーカー希望小売価格', 'クーポン利用で', 'custom')")
    customPriceType: Optional[str] = Field(None, alias="customPriceType", description="二重価格自由記入 (priceTypeが'custom'の場合)")
    regularPrice: str = Field(..., alias="regularPrice", description="通常価格")
    salePrice: str = Field(..., alias="salePrice", description="セール価格")
    saleText: Optional[str] = Field(None, alias="saleText", description="セール文言 (最大12文字)")
    # discount: str # Frontend tự tính, không cần gửi
    discountType: Optional[str] = Field("percent", alias="discountType", description="割引表示タイプ ('percent' or 'yen')")
    mobileStartDate: Optional[str] = Field(None, alias="mobileStartDate", description="楽天モバイル開始日時 (ISO format, Optional)")
    mobileEndDate: Optional[str] = Field(None, alias="mobileEndDate", description="楽天モバイル終了日時 (ISO format, Optional)")

    class Config:
        populate_by_name = True # Cho phép dùng alias khi nhận JSON

# Định nghĩa cấu trúc dữ liệu cho request tạo job
class Tool03CreateJobRequest(BaseModel):
    rows: List[Tool03ProductRowInput] = Field(..., description="商品情報のリスト")

# Định nghĩa cấu trúc dữ liệu cho response khi tạo job thành công
class Tool03CreateJobResponse(BaseModel):
    jobId: str = Field(..., description="生成されたジョブID")
    status: str = Field(default="Pending", description="ジョブの初期ステータス")
    totalItems: int = Field(..., description="処理対象のアイテム総数")
