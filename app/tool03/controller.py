# -*- coding: utf-8 -*-
import uuid
from fastapi import BackgroundTasks, HTTPException
from typing import List, Optional, Dict
import os
import shutil
import logging 

# Đồng thời directory (.) import schemas và service
from . import schemas
from . import service as tool03_service

# --- start_image_generation_job function ---
def start_image_generation_job(
    product_rows: List[schemas.Tool03ProductRowInput],
    background_tasks: BackgroundTasks
) -> schemas.Tool03CreateJobResponse:
    if not product_rows:
        raise HTTPException(status_code=400, detail="商品リストを空にすることはできません")

    job_id = str(uuid.uuid4())
    # Thêm job vào background tasks
    background_tasks.add_task(tool03_service.generate_images_background, job_id, product_rows)

    # Trả về job_id ngay lập tức
    return schemas.Tool03CreateJobResponse(jobId=job_id, totalItems=len(product_rows))

# --- get_job_status_controller function ---
def get_job_status_controller(job_id: str) -> Optional[schemas.Tool03JobStatusResponse]:
    status_dict = tool03_service.get_job_status(job_id)
    if status_dict:
        # --- Thêm job_id vào dictionary ---
        status_dict_with_id = {"jobId": job_id, **status_dict}
        # ---------------------------
        try:
            # Chuyển đổi dict sang Pydantic model để xác thực và trả về
            return schemas.Tool03JobStatusResponse(**status_dict_with_id)
        except Exception as e:
            # Ghi log nếu có lỗi xác thực không mong muốn
            logging.error(f"ジョブ {job_id} の JobStatusResponse 検証エラー: {e}") # <<< Đã sửa logger -> logging
            logging.error(f"元のデータ: {status_dict_with_id}") # <<< Đã sửa logger -> logging
            # Trả về lỗi 500 nếu cấu trúc dữ liệu không khớp model
            raise HTTPException(status_code=500, detail="ジョブステータスデータの処理エラー。")

    # Trả về None nếu service không tìm thấy job (router sẽ trả về 404)
    return None


# --- get_image_file_path_controller function ---
def get_image_file_path_controller(job_id: str, filename: str) -> Optional[str]:
     job_dir = tool03_service.JOB_STORAGE_BASE_DIR / job_id
     file_path = job_dir / filename
     # Kiểm tra path traversal attack
     if not str(file_path.resolve()).startswith(str(job_dir.resolve())):
          logging.warning(f"パストラバーサルの試行: {job_id}/{filename}") # <<< Đã sửa logger -> logging
          return None
     if file_path.is_file():
          return str(file_path)
     return None

# --- create_images_zip_controller function ---
def create_images_zip_controller(job_id: str) -> Optional[str]:
    try:
        zip_path = tool03_service.create_job_zip_archive(job_id)
        return zip_path
    except FileNotFoundError:
         raise HTTPException(status_code=404, detail="ジョブディレクトリが見つかりません。")
    except Exception as e:
         logging.error(f"ジョブ {job_id} の Zip 作成エラー: {e}", exc_info=True) # <<< Đã sửa logger -> logging
         raise HTTPException(status_code=500, detail="Zip ファイルの作成に失敗しました。")

# --- start_ftp_upload_controller function ---
def start_ftp_upload_controller(job_id: str, target: str, background_tasks: BackgroundTasks):
    job_status = tool03_service.get_job_status(job_id)
    if not job_status:
        raise HTTPException(status_code=404, detail="ジョブが見つかりません。")

    # (Optional check if job is completed - currently commented out)
    # if job_status.get("status") not in ["Completed", "Completed with errors"]:
    #     raise HTTPException(status_code=400, detail="ジョブはまだ完了していません。")

    logging.info(f"ジョブ {job_id} の {target} への FTP アップロードタスクをバックグラウンドに追加します。") # <<< Đã sửa logger -> logging
    background_tasks.add_task(tool03_service.upload_job_images_to_ftp, job_id, target)

# --- start_image_regeneration_job function ---
def start_image_regeneration_job(
    job_id: str,
    modified_rows: List[schemas.Tool03ProductRowInput],
    background_tasks: BackgroundTasks
):
    """Thêm background task để tái tạo ảnh cụ thể."""
    # Kiểm tra job tồn tại
    existing_job_status = tool03_service.get_job_status(job_id)
    if not existing_job_status:
        raise HTTPException(status_code=404, detail="ジョブが見つかりません")

    # (Optional check if job is not in failed state - currently commented out)
    # if existing_job_status.get("status") == "Failed":
    #     raise HTTPException(status_code=400, detail="失敗したジョブは更新できません。")

    logging.info(f"ジョブ {job_id} に {len(modified_rows)} 件の画像再生成タスクを追加します。") # <<< Đã sửa logger -> logging
    background_tasks.add_task(tool03_service.regenerate_specific_images_background, job_id, modified_rows)
