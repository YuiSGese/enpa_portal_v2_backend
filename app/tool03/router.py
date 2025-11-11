# -*- coding: utf-8 -*-
from fastapi import APIRouter, BackgroundTasks, HTTPException, Path, Body, Depends
from fastapi.responses import FileResponse, JSONResponse
import os
import shutil
from typing import List, Dict, Any
import datetime
import logging

from starlette.background import BackgroundTask 

# --- Import CSDL (Mới) ---
from sqlalchemy.orm import Session
from app.core.database import get_db
# ---------------------------

from . import schemas
from . import controller

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/tools/03",
    tags=["Tool 03 - 二重価格画像作成"],
)

# === ENDPOINT: TẠO JOB ===
@router.post(
    "/jobs",
    response_model=schemas.Tool03CreateJobResponse,
    status_code=202
)
async def create_image_generation_job(
    request: schemas.Tool03CreateJobRequest,
    db: Session = Depends(get_db)
):
    """(Đã tái cấu trúc) Bắt đầu job tạo ảnh (CSDL + SQS)."""
    return controller.start_image_generation_job(request.productRows, db)

# === ENDPOINT: TÁI TẠO JOB ===
@router.patch(
    "/jobs/{job_id}",
    status_code=202
)
async def update_image_generation_job(
    request: schemas.Tool03CreateJobRequest,
    job_id: str = Path(..., description="更新対象のジョブID", min_length=36, max_length=36),
    db: Session = Depends(get_db)
):
    """(Đã tái cấu trúc) Tái tạo (thay thế) job (CSDL + SQS)."""
    return controller.update_image_generation_job(job_id, request.productRows, db)

# === ENDPOINT: LẤY STATUS ===
@router.get(
    "/jobs/{job_id}/status",
    response_model=schemas.Tool03JobStatusResponse
)
async def get_job_status(
    job_id: str = Path(..., description="確認対象のジョブID", min_length=36, max_length=36),
    db: Session = Depends(get_db)
):
    """(Đã tái cấu trúc) Lấy trạng thái job (Đọc từ CSDL)."""
    status_data = controller.get_job_status_controller(job_id, db)
    if status_data is None:
        raise HTTPException(status_code=404, detail="ジョブが見つかりません")
    return status_data

# === (SỬA LỖI 1) ENDPOINT: LẤY LINK ẢNH ===
@router.get(
    "/jobs/{job_id}/image/{filename}",
    response_class=JSONResponse 
)
async def get_image_file(
    job_id: str = Path(..., description="ジョブID", min_length=36, max_length=36),
    filename: str = Path(..., description="取得対象の画像ファイル名"),
    db: Session = Depends(get_db) # <<< (SỬA LỖI) Thêm CSDL
):
    """(Đã tái cấu trúc) Lấy S3 Presigned URL cho 1 file ảnh."""
    
    # (SỬA LỖI) Truyền db vào controller
    url = controller.get_image_presigned_url_controller(job_id, filename, db)
    
    if url is None:
         raise HTTPException(status_code=404, detail="画像が見つからないか、無効なファイル名です")
    
    return JSONResponse(content={"url": url})

# === ENDPOINT: TẢI ZIP ===
@router.get(
    "/jobs/{job_id}/download",
    response_class=FileResponse
)
async def download_images_zip(
    job_id: str = Path(..., description="ダウンロード対象のジョブID", min_length=36, max_length=36),
    db: Session = Depends(get_db)
):
    """(Đã tái cấu trúc) Tạo Zip (từ S3) và tải về."""
    
    try:
        local_zip_path, download_filename = controller.create_images_zip_controller(job_id, db)
        
        if not local_zip_path or not os.path.exists(local_zip_path):
             logger.error(f"[API] (GET /download) {job_id}: Controller chạy xong nhưng file Zip không tồn tại: {local_zip_path}")
             raise HTTPException(status_code=500, detail="Zip の作成に失敗しました (File not found after creation).")
        
        return FileResponse(
            path=local_zip_path,
            filename=download_filename,
            media_type='application/zip',
            background=BackgroundTask(os.remove, local_zip_path)
        )
        
    except HTTPException as e:
         raise e
    except Exception as e:
         logger.error(f"[API] (GET /download) {job_id}: Lỗi không xác định trong router: {e}", exc_info=True)
         raise HTTPException(status_code=500, detail=f"Lỗi router khi tạo Zip: {e}")

# === ENDPOINT: TẢI FTP ===
@router.post(
    "/jobs/{job_id}/upload",
    status_code=202
)
async def upload_images_to_ftp(
    job_id: str = Path(..., description="アップロード対象のジョブID", min_length=36, max_length=36),
    payload: Dict[str, str] = Body(..., example={"target": "gold"}),
    db: Session = Depends(get_db)
):
    """(Đã tái cấu trúc) Bắt đầu job upload FTP (CSDL + SQS)."""
    
    target = payload.get("target")
    if target not in ["gold", "rcabinet"]:
        raise HTTPException(status_code=400, detail="無効なターゲットが指定されました。'gold' または 'rcabinet' を使用してください。")

    return controller.start_ftp_upload_controller(job_id, target, db)