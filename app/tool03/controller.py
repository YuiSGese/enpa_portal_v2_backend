# -*- coding: utf-8 -*-
import uuid
from fastapi import BackgroundTasks, HTTPException
from typing import List, Optional, Dict
import os
import shutil
import logging 
import json
import datetime # (Cần cho hàm Zip)
import tempfile # (Import)
from pathlib import Path # (Import)

# --- Import CSDL (Mới) ---
from sqlalchemy.orm import Session
from app.domain.entities.JobEntity import JobEntity
# ---------------------------

# Đồng thời directory (.) import schemas
from . import schemas

# --- Import Clients (Mới) ---
from app.core import sqs_client
from app.core import s3_client
from app.core import config
# ------------------------------

# (Service.py cũ không còn được dùng nữa)
# from . import service as tool03_service 

# Cấu hình logging
logger = logging.getLogger(__name__)

# === HÀM TẠO JOB (POST /jobs) (Đã tái cấu trúc CSDL) ===
# ... (Hàm start_image_generation_job không thay đổi) ...
def start_image_generation_job(
    product_rows: List[schemas.Tool03ProductRowInput],
    db: Session # (Đã thêm db)
) -> schemas.Tool03CreateJobResponse:
    
    if not product_rows:
        raise HTTPException(status_code=400, detail="商品リストを空にすることはできません")

    job_id = str(uuid.uuid4())
    
    # 1. Chuẩn bị Payload (dưới dạng list[dict])
    try:
        # (Chuyển đổi Pydantic model (product_rows) sang dict)
        payload_dict_list = [row.model_dump() for row in product_rows]
        job_payload_json = json.dumps(payload_dict_list)
        
    except Exception as e:
         logger.error(f"Lỗi khi serialize Pydantic model (job_payload): {e}", exc_info=True)
         raise HTTPException(status_code=500, detail=f"Lỗi hệ thống khi chuẩn bị job payload: {e}")
         
    # 2. Ghi Job PENDING vào CSDL
    try:
        new_job = JobEntity(
            job_id=job_id,
            job_type="tool03",
            status="PENDING",
            total_items=len(product_rows),
            job_payload=job_payload_json # (Lưu payload vào CSDL)
        )
        db.add(new_job)
        db.commit()
        logger.info(f"[API] Đã ghi Job PENDING vào CSDL: {job_id}")
        
    except Exception as e:
        db.rollback()
        logger.critical(f"[API] Lỗi CSDL khi ghi Job PENDING (job_id: {job_id}): {e}", exc_info=True)
        # === SỬA LỖI: Thêm str(e) vào detail ===
        raise HTTPException(status_code=500, detail=f"Lỗi CSDL khi tạo job: {str(e)}")

    # 3. Gửi Job SQS (Chỉ gửi ID)
    
    # === SỬA LỖI (TypeError): Chuẩn bị message_body ===
    # Worker (worker.py) mong đợi một dict có 'job_type' và 'data'
    sqs_message_body = {
        "job_type": "tool03",
        "data": {"job_id": job_id}
    }
    # ===============================================
    
    send_success_message_id = sqs_client.send_sqs_message(
        # === SỬA LỖI: Dùng đúng tên tham số 'message_body' ===
        message_body=sqs_message_body 
    )
    
    if not send_success_message_id:
        logger.error(f"[API] Lỗi SQS: Không thể gửi message cho job: {job_id}")
        # (Cập nhật CSDL -> FAILED)
        try:
             job = db.query(JobEntity).filter(JobEntity.job_id == job_id).first()
             if job:
                  job.status = "FAILED"
                  job.message = "Lỗi hệ thống: Không thể gửi job SQS."
                  db.commit()
        except Exception as db_e:
             logger.error(f"[API] Lỗi CSDL khi cập nhật SQS FAILED (job_id: {job_id}): {db_e}", exc_info=True)
             db.rollback()
             
        raise HTTPException(status_code=500, detail="Lỗi hệ thống: Không thể gửi job SQS.")

    logger.info(f"[API] Đã gửi Job SQS thành công (Type: tool03, ID: {job_id}).")

    # 4. Trả về job_id ngay lập tức
    return schemas.Tool03CreateJobResponse(jobId=job_id, totalItems=len(product_rows))


# === HÀM TÁI TẠO JOB (PATCH /jobs/{job_id}) (Đã tái cấu trúc CSDL) ===

def update_image_generation_job(
    job_id: str,
    product_rows: List[schemas.Tool03ProductRowInput], # (Đây là các hàng *đã sửa*)
    db: Session # (Đã thêm db)
):
    if not product_rows:
         # (Không làm gì, chỉ trả về 202)
         logger.warning(f"[API] Nhận được PATCH (job_id: {job_id}) nhưng 'productRows' rỗng. Bỏ qua.")
         return {"message": f"ジョブ {job_id} の更新リクエストを受け取りましたが、更新対象の行がありません。"} 

    logger.info(f"[API] Nhận được PATCH (job_id: {job_id}). Đang cập nhật CSDL (Merge) và gửi lại SQS...")

    # 1. Chuẩn bị Payload (dưới dạng list[dict])
    try:
        new_payload_rows = [row.model_dump() for row in product_rows]
        
    except Exception as e:
         logger.error(f"Lỗi khi serialize Pydantic model (job_payload PATCH): {e}", exc_info=True)
         raise HTTPException(status_code=500, detail=f"Lỗi hệ thống khi chuẩn bị job payload (PATCH): {e}")

    # 2. Cập nhật Job PENDING vào CSDL (LOGIC MERGE)
    try:
        job = db.query(JobEntity).filter(JobEntity.job_id == job_id).first()
        if not job:
            logger.error(f"[API] Lỗi PATCH: Không tìm thấy job_id {job_id} trong CSDL.")
            raise HTTPException(status_code=404, detail="ジョブが見つかりません。")
            
        # === (SỬA LỖI PATCH) START ===
        
        # a. Tải payload cũ
        try:
            old_payload_list = json.loads(job.job_payload or "[]")
            old_payload_map = {row['id']: row for row in old_payload_list}
        except json.JSONDecodeError:
            old_payload_map = {}
            
        # b. Tải results cũ
        try:
            old_results_dict = json.loads(job.job_results or "{}")
        except json.JSONDecodeError:
            old_results_dict = {}

        # c. Hợp nhất (Merge) payload MỚI vào CŨ
        for new_row in new_payload_rows:
            row_id = new_row['id']
            old_payload_map[row_id] = new_row # Ghi đè hoặc thêm mới
            
            # d. Xóa kết quả cũ của hàng này (để worker chạy lại)
            if row_id in old_results_dict:
                del old_results_dict[row_id]
                logger.info(f"[API] (PATCH) {job_id}: Đã xóa kết quả cũ cho row {row_id} (sẽ chạy lại).")
        
        # e. Lưu payload đã merge
        job.job_payload = json.dumps(list(old_payload_map.values()))
        
        # f. Lưu results đã bị xóa bớt
        job.job_results = json.dumps(old_results_dict)
        
        # g. Reset trạng thái
        job.status = "PENDING"
        job.message = None # Xóa lỗi cũ
        job.total_items = len(old_payload_map) # Tổng số mới
        
        # (Reset FTP status)
        job.ftp_status_gold = "IDLE"
        job.ftp_error_gold = None
        job.ftp_status_rcabinet = "IDLE"
        job.ftp_error_rcabinet = None
        # === (SỬA LỖI PATCH) END ===
        
        db.commit()
        logger.info(f"[API] Đã reset Job PENDING (PATCH/MERGE) vào CSDL: {job_id}")
        
    except HTTPException as e:
        db.rollback()
        raise e # Ném lại 404
    except Exception as e:
        db.rollback()
        logger.critical(f"[API] Lỗi CSDL khi reset Job PENDING (PATCH) (job_id: {job_id}): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Lỗi CSDL khi cập nhật job: {e}")

    # 3. Gửi Job SQS (Giống hệt hàm POST)
    
    # ... (Gửi SQS không thay đổi) ...
    sqs_message_body = {
        "job_type": "tool03",
        "data": {"job_id": job_id}
    }
    send_success_message_id = sqs_client.send_sqs_message(
        message_body=sqs_message_body
    )
    if not send_success_message_id:
         logger.error(f"[API] Lỗi SQS (PATCH): Không thể gửi message cho job: {job_id}")
         raise HTTPException(status_code=500, detail="Lỗi hệ thống: Đã cập nhật CSDL nhưng không thể gửi job SQS.")
    logger.info(f"[API] Đã gửi Job SQS (PATCH) thành công (Type: tool03, ID: {job_id}).")
    return {"message": f"ジョブ {job_id} の画像再生成タスクが開始されました。"}


# === HÀM LẤY STATUS (GET /jobs/{job_id}/status) (Đã tái cấu trúc CSDL) ===
def get_job_status_controller(job_id: str, db: Session) -> Optional[schemas.Tool03JobStatusResponse]:
    """
    Đọc trạng thái job trực tiếp từ CSDL.
    """
    try:
        job = db.query(JobEntity).filter(JobEntity.job_id == job_id).first()
        
        if not job:
            logger.warning(f"[API] (GET /status) 404: Không tìm thấy job_id: {job_id}")
            return None # (Router sẽ trả về 404)
            
        # Parse results (nếu có)
        results_dict = {}
        if job.job_results:
             try:
                  results_dict = json.loads(job.job_results)
             except json.JSONDecodeError:
                  logger.error(f"[API] (GET /status) Lỗi: Không thể parse job_results từ CSDL (job_id: {job_id})")
                  # (Không crash, chỉ trả về results rỗng)
                  
        # === (SỬA LỖI PATCH) Đếm progress từ results ===
        progress_count = 0
        if results_dict:
             progress_count = len(results_dict) # Đếm số key trong results
        # === (KẾT THÚC SỬA LỖI) ===
             
        # Map Entity -> Pydantic Schema
        status_response = schemas.Tool03JobStatusResponse(
            jobId=job.job_id,
            status=job.status,
            progress=progress_count, # (SỬA)
            total=job.total_items or 0,
            results=results_dict,
            startTime=job.create_datetime.timestamp(), # (Dùng create_datetime)
            endTime=job.update_datetime.timestamp() if job.status in ["COMPLETED", "FAILED", "COMPLETED_WITH_ERRORS"] else None,
            message=job.message,
            ftpUploadStatusGold=job.ftp_status_gold or "IDLE",
            ftpUploadErrorGold=job.ftp_error_gold,
            ftpUploadStatusRcabinet=job.ftp_status_rcabinet or "IDLE",
            ftpUploadErrorRcabinet=job.ftp_error_rcabinet
        )
        return status_response

    except Exception as e:
         logger.error(f"[API] (GET /status) Lỗi CSDL khi đọc job {job_id}: {e}", exc_info=True)
         raise HTTPException(status_code=500, detail="Lỗi CSDL khi đọc trạng thái job.")


# === HÀM LẤY LINK ẢNH (GET /jobs/{job_id}/image/{filename}) (Đã tái cấu trúc S3) ===
# ... (Hàm get_image_presigned_url_controller không thay đổi - đã có date_folder) ...
def get_image_presigned_url_controller(
    job_id: str, 
    filename: str,
    db: Session # <<< Thêm db Session
) -> Optional[str]:
    """
    Tạo một S3 Presigned URL cho file ảnh.
    """
    
    # (Bảo mật: Kiểm tra path traversal)
    if ".." in filename or filename.startswith("/"):
        logger.warning(f"[API] (GET /image) 400: Path traversal attempt: {job_id}/{filename}")
        return None # (Router sẽ trả về 400)
        
    # === Lấy create_datetime từ CSDL ===
    try:
        job = db.query(JobEntity).filter(JobEntity.job_id == job_id).first()
        if not job:
            logger.warning(f"[API] (GET /image) 404: Không tìm thấy job {job_id} khi lấy datetime.")
            return None
        
        date_folder = job.create_datetime.strftime('%Y%m%d')
    except Exception as e:
        logger.error(f"[API] (GET /image) 500: Lỗi CSDL khi lấy datetime cho job {job_id}: {e}")
        return None # (Router sẽ trả về 404, vì không thể tạo URL)
    # === (KẾT THÚC SỬA LỖI) ===
        
    # (Tạo S3 key MỚI)
    object_key = f"tool03/{date_folder}/{job_id}/{filename}"
    
    url = s3_client.create_presigned_url(object_key=object_key)
    
    if not url:
        logger.warning(f"[API] (GET /image) 404: Không thể tạo S3 URL (File không tồn tại?): {object_key}")
        return None # (Router sẽ trả về 404)
        
    return url


# === HÀM TẢI ZIP (GET /jobs/{job_id}/download) (Đã tái cấu trúc S3) ===
# ... (Hàm create_images_zip_controller không thay đổi - đã có date_folder) ...
def create_images_zip_controller(job_id: str, db: Session) -> (Optional[str], str):
    """
    Tạo file Zip (từ S3) và trả về đường dẫn file tạm (local_zip_path) 
    và tên file (download_filename).
    """
    
    # 1. Đọc CSDL để lấy danh sách file
    try:
        job = db.query(JobEntity).filter(JobEntity.job_id == job_id).first()
        if not job or not job.job_results:
             logger.warning(f"[API] (GET /download) 404: Không tìm thấy job hoặc job_results rỗng (job_id: {job_id})")
             raise HTTPException(status_code=404, detail="Job không tồn tại hoặc chưa xử lý xong.")
             
        results_data = json.loads(job.job_results)
        
        # Lấy danh sách file "Success"
        files_to_download: List[str] = [
            result['filename'] for result in results_data.values()
            if result.get('status') == 'Success' and result.get('filename')
        ]
        
        if not files_to_download:
            logger.warning(f"[API] (GET /download) 404: Job {job_id} không có file 'Success' nào.")
            raise HTTPException(status_code=404, detail="Job không có file nào xử lý thành công.")
            
        # Lấy date_folder
        date_folder = job.create_datetime.strftime('%Y%m%d')

    except json.JSONDecodeError:
         logger.error(f"[API] (GET /download) Lỗi: Không thể parse job_results từ CSDL (job_id: {job_id})")
         raise HTTPException(status_code=500, detail="Lỗi CSDL: Không thể đọc kết quả job.")
    except HTTPException as e:
         raise e # (Ném lại lỗi 404)
    except Exception as e:
         logger.error(f"[API] (GET /download) Lỗi CSDL khi đọc job {job_id}: {e}", exc_info=True)
         raise HTTPException(status_code=500, detail="Lỗi CSDL khi đọc job.")

    # 2. Tạo thư mục tạm (để chứa file S3)
    temp_dir_for_zip = tempfile.mkdtemp(prefix=f"zip_{job_id}_")
    temp_dir_path = Path(temp_dir_for_zip)
    
    try:
        # 3. Download từng file từ S3 về thư mục tạm
        logger.info(f"[API] (GET /download) {job_id}: Đang download {len(files_to_download)} file từ S3 về {temp_dir_for_zip}...")
        for filename in files_to_download:
            # Dùng S3 key MỚI
            s3_object_key = f"tool03/{date_folder}/{job_id}/{filename}"
            local_temp_path = temp_dir_path / filename
            
            download_success = s3_client.download_file_from_s3(
                object_key=s3_object_key,
                local_file_path=str(local_temp_path)
            )
            if not download_success:
                # Nếu 1 file lỗi -> Hủy toàn bộ
                logger.error(f"[API] (GET /download) {job_id}: Lỗi S3 khi download file {s3_object_key}.")
                raise HTTPException(status_code=500, detail=f"Lỗi S3: Không thể tải file {filename} từ S3.")

        # 4. Tạo file Zip (từ thư mục tạm)
        logger.info(f"[API] (GET /download) {job_id}: Download S3 xong. Đang nén Zip...")
        
        # (Tạo file Zip trong thư mục /tmp (tempfile.gettempdir()))
        today_str = datetime.date.today().strftime('%Y%m%d')
        
        # (Tên file theo yêu cầu)
        download_filename = f"{today_str}_image.zip"
        
        # (Nơi lưu file Zip trên ổ cứng server)
        local_zip_path_base = os.path.join(tempfile.gettempdir(), f"tool03_zip_{job_id}")
        
        local_zip_path = shutil.make_archive(
            base_name=local_zip_path_base,
            format='zip',
            root_dir=temp_dir_path # (Chỉ nén nội dung bên trong temp_dir_path)
        )
        
        logger.info(f"[API] (GET /download) {job_id}: Nén Zip thành công: {local_zip_path}")
        
        return local_zip_path, download_filename

    except Exception as e:
         # (Bao gồm HTTPException 500/404 từ bên trong)
         logger.error(f"[API] (GET /download) {job_id}: Lỗi khi tạo Zip: {e}", exc_info=True)
         if isinstance(e, HTTPException):
             raise e
         raise HTTPException(status_code=500, detail=f"Lỗi khi tạo Zip: {e}")
         
    finally:
         # 5. Dọn dẹp thư mục tạm (chứa file ảnh)
         # (File Zip sẽ được xóa bởi BackgroundTask trong router.py)
         if temp_dir_path.exists():
             try:
                 shutil.rmtree(temp_dir_path)
             except Exception as rm_e:
                 logger.warning(f"[API] (GET /download) {job_id}: Lỗi khi xóa thư mục tạm {temp_dir_for_zip}: {rm_e}")


# === HÀM TẢI FTP (POST /jobs/{job_id}/upload) (Đã tái cấu trúc CSDL) ===
# ... (Hàm start_ftp_upload_controller không thay đổi) ...
def start_ftp_upload_controller(
    job_id: str, 
    target: str, # "gold" hoặc "rcabinet"
    db: Session
):
    """
    Cập nhật CSDL và Gửi SQS job (loại 'tool03_ftp').
    """
    
    logger.info(f"[API] (POST /upload) {job_id}: Nhận lệnh upload FTP (Target: {target}).")

    # 1. Kiểm tra Job CSDL
    try:
        job = db.query(JobEntity).filter(JobEntity.job_id == job_id).first()
        if not job:
            logger.error(f"[API] (POST /upload) 404: Không tìm thấy job_id: {job_id}")
            raise HTTPException(status_code=404, detail="ジョブが見つかりません。")
            
        # (Kiểm tra xem job đã chạy xong chưa)
        if job.status not in ["COMPLETED", "COMPLETED_WITH_ERRORS"]:
            logger.warning(f"[API] (POST /upload) 400: Job {job_id} chưa chạy xong (Status: {job.status}).")
            raise HTTPException(status_code=400, detail=f"ジョブはまだ完了していません (Status: {job.status})。")

        # 2. Cập nhật CSDL (Reset trạng thái FTP)
        ftp_status_key = f"ftp_status_{target}" # (e.g., ftp_status_gold)
        ftp_error_key = f"ftp_error_{target}" # (e.g., ftp_error_gold)
        
        setattr(job, ftp_status_key, "PENDING")
        setattr(job, ftp_error_key, None)
        
        db.commit()
        logger.info(f"[API] (POST /upload) {job_id}: Cập nhật CSDL -> {ftp_status_key} = PENDING.")

    except HTTPException as e:
         raise e # (Ném lại lỗi 404/400)
    except Exception as e:
        db.rollback()
        logger.critical(f"[API] (POST /upload) {job_id}: Lỗi CSDL khi cập nhật FTP PENDING: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Lỗi CSDL khi cập nhật job: {e}")

    # 3. Gửi Job SQS (Loại mới: 'tool03_ftp')
    
    # ... (Gửi SQS không thay đổi) ...
    sqs_message_body = {
        "job_type": "tool03_ftp",
        "data": {
            "job_id": job_id,
            "target": target 
        }
    }
    send_success_message_id = sqs_client.send_sqs_message(
        message_body=sqs_message_body
    )
    if not send_success_message_id:
         logger.error(f"[API] (POST /upload) {job_id}: Lỗi SQS: Không thể gửi message FTP.")
         try:
             job = db.query(JobEntity).filter(JobEntity.job_id == job_id).first()
             if job:
                  setattr(job, ftp_status_key, "FAILED")
                  setattr(job, ftp_error_key, "Lỗi hệ thống: Không thể gửi job SQS (FTP).")
                  db.commit()
         except Exception as db_e:
             logger.error(f"[API] (POST /upload) {job_id}: Lỗi CSDL khi cập nhật SQS FAILED (FTP): {db_e}", exc_info=True)
             db.rollback()
         raise HTTPException(status_code=500, detail="Lỗi hệ thống: Không thể gửi job SQS (FTP).")
    logger.info(f"[API] (POST /upload) {job_id}: Đã gửi Job SQS (FTP) thành công.")
    return {"message": f"ジョブ {job_id} の {target} へのFTPアップロードタスクがバックグラウンドで開始されました。"}