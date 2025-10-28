# -*- coding: utf-8 -*-
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

# --- 入力スキーマ ---
class Tool03ProductRowInput(BaseModel):
        id: str # フロントエンドからの行ID (結果をマッピングするため)
        productCode: str = Field(..., description="商品管理番号")
        template: str = Field(..., description="テンプレート名 (例: テンプレートA)")
        startDate: str = Field(..., description="開始日時 (YYYY-MM-DDTHH:mm)")
        endDate: str = Field(..., description="終了日時 (YYYY-MM-DDTHH:mm)")
        priceType: str = Field(..., description="二重価格タイプ (当店通常価格, メーカー希望小売価格, クーポン利用で, custom)")
        customPriceType: Optional[str] = Field(None, description="店舗自由記入の二重価格文言")
        regularPrice: str = Field(..., description="通常価格（税込）（値）")
        salePrice: str = Field(..., description="セール価格（税込）（値）")
        saleText: Optional[str] = Field(None, description="セール文言 (12文字以内)")
        # discount: str # バックエンドで計算されます
        discountType: Optional[str] = Field("percent", description="割引表示タイプ ('percent' or 'yen')") # デフォルトは %
        mobileStartDate: Optional[str] = Field(None, description="楽天モバイル開始日時 (YYYY-MM-DDTHH:mm)")
        mobileEndDate: Optional[str] = Field(None, description="楽天モバイル終了日時 (YYYY-MM-DDTHH:mm)")

class Tool03CreateJobRequest(BaseModel):
        productRows: List[Tool03ProductRowInput]

# --- 出力スキーマ ---
class Tool03CreateJobResponse(BaseModel):
        jobId: str
        status: str = "Pending"
        totalItems: int

# --- ジョブステータス用スキーマ ---
class Tool03ImageResult(BaseModel):
        """画像1枚の処理結果"""
        status: str = Field(..., description="処理ステータス (Success, Error, Processing, Pending)") # Pending を追加
        filename: Optional[str] = Field(None, description="生成された画像ファイル名 (成功時)")
        message: Optional[str] = Field(None, description="エラーメッセージ (失敗時)")

class Tool03JobStatusResponse(BaseModel):
        """ジョブのステータス情報"""
        jobId: str
        status: str = Field(..., description="全体のステータス (Pending, Processing, Completed, Completed with errors, Failed)")
        progress: int = Field(..., description="処理済みの画像数 (Success または Error)")
        total: int = Field(..., description="処理対象の総画像数")
        results: Dict[str, Tool03ImageResult] = Field(..., description="各画像の詳細結果 (キーは row.id)")
        startTime: float
        endTime: Optional[float] = Field(None)
        message: Optional[str] = Field(None, description="全体のエラーメッセージ (ジョブが Failed の場合)") # 共通メッセージ追加

        # --- FTPステータスフィールドを追加 ---
        ftpUploadStatusGold: Optional[str] = Field("idle", description="FTP GOLD アップロードステータス (idle, uploading, success, failed)")
        ftpUploadErrorGold: Optional[str] = Field(None, description="FTP GOLD アップロードエラーメッセージ")
        ftpUploadStatusRcabinet: Optional[str] = Field("idle", description="FTP R-Cabinet アップロードステータス (idle, uploading, success, failed)")
        ftpUploadErrorRcabinet: Optional[str] = Field(None, description="FTP R-Cabinet アップロードエラーメッセージ")
        # ------------------------------------
