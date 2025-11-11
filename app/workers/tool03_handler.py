# -*- coding: utf-8 -*-
import os
import uuid
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional
from PIL import Image, ImageDraw, ImageFont
import asyncio
from decimal import Decimal, ROUND_HALF_UP
import time
import tempfile
import logging
import datetime 
import json 
import ftplib # --- THÊM: Import FTP ---

# --- Import CSDL (Rất quan trọng) ---
from app.core.database import SessionLocal, engine
from app.domain.entities.JobEntity import JobEntity
from sqlalchemy.orm import Session
# ------------------------------------

# --- Import S3 Client (Mới) ---
from app.core import s3_client
# ------------------------------

# Import schemas (chỉ để type hint)
from app.tool03.schemas import Tool03ProductRowInput, Tool03ImageResult

# Cấu hình logging (sẽ dùng chung với worker.py)
logger = logging.getLogger(__name__)

# === HÀM HELPER CẬP NHẬT CSDL ===
def update_job_status(
    db_session: Session, 
    job_id: str, 
    status: str, 
    message: Optional[str] = None
):
    """Hàm helper để cập nhật trạng thái job trong CSDL."""
    try:
        job = db_session.query(JobEntity).filter(JobEntity.job_id == job_id).first()
        if job:
            job.status = status
            if message:
                job.message = message
            db_session.commit()
            logger.info(f"[Job {job_id}] Cập nhật CSDL: status={status}.")
        else:
            logger.error(f"[Job {job_id}] LỖI NGHIÊM TRỌNG: Không tìm thấy job trong CSDL để cập nhật status!")
    except Exception as e:
        db_session.rollback()
        logger.error(f"[Job {job_id}] Lỗi CSDL khi cập nhật status={status}: {e}", exc_info=True)
        # Nếu CSDL lỗi, chúng ta nên raise Exception
        # để worker loop biết và KHÔNG xóa message SQS
        raise e

# === HÀM CHÍNH (Được gọi bởi worker.py) ===

def process_tool03_job(job_data: Dict[str, Any]) -> bool:
    """
    Hàm xử lý chính cho Tool03 (TẠO ẢNH).
    Được gọi bởi worker.py khi có job SQS (type: 'tool03').
    
    :param job_data: Nội dung message SQS (đã parse)
    :return: True (Xóa SQS) hoặc False (Giữ SQS - để retry)
    """
    
    job_id = job_data.get('job_id')
    if not job_id:
        logger.error("[Worker] Lỗi: Nhận được job SQS (tool03) nhưng không có 'job_id'. Xóa SQS.")
        return True # Xóa message SQS (lỗi không thể retry)

    logger.info(f"[Job {job_id}] Bắt đầu xử lý (Tool 03 - TẠO ẢNH).")
    
    # Tạo một session CSDL riêng biệt cho job này
    db_session = SessionLocal()
    
    # Biến trạng thái
    job: Optional[JobEntity] = None # (SỬA LAZY LOAD: Khai báo job ở đây)
    job_payload_str: Optional[str] = None
    payload_rows: List[Tool03ProductRowInput] = []
    
    # Biến kết quả (sẽ được lưu vào CSDL)
    final_job_status = "FAILED"
    final_job_message = None
    final_results_dict: Dict[str, Any] = {} # (SỬA LỖI PATCH)
    
    # Biến cờ (để quyết định xóa SQS)
    should_delete_sqs_message = False 
    
    # Tạo thư mục tạm (duy nhất) để chứa ảnh
    temp_dir_for_job = tempfile.mkdtemp(prefix=f"tool03_{job_id}_")
    temp_dir_path = Path(temp_dir_for_job)

    try:
        # --- 1. Lấy Job Payload từ CSDL ---
        try:
            # (SỬA LAZY LOAD: Gán job vào biến scope ngoài)
            job = db_session.query(JobEntity).filter(JobEntity.job_id == job_id).first()
            if not job:
                logger.error(f"[Job {job_id}] Lỗi: Job không tìm thấy trong CSDL. Xóa SQS.")
                return True # Xóa SQS (OK - vì nằm trong try lồng nhau)
            
            job_payload_str = job.job_payload
            if not job_payload_str:
                 logger.error(f"[Job {job_id}] Lỗi: Job có trong CSDL nhưng 'job_payload' rỗng. Xóa SQS.")
                 return True # Xóa SQS (OK - vì nằm trong try lồng nhau)
                 
            # Parse payload
            payload_data = json.loads(job_payload_str)
            # Chuyển đổi dicts thành Pydantic models (để validate)
            payload_rows = [Tool03ProductRowInput(**row) for row in payload_data]
            
            if not payload_rows:
                 logger.error(f"[Job {job_id}] Lỗi: 'job_payload' hợp lệ nhưng không có 'productRows'. Xóa SQS.")
                 return True # Xóa SQS (OK - vì nằm trong try lồng nhau)
                 
            # === (SỬA LỖI PATCH) Lấy date_folder ===
            date_folder = job.create_datetime.strftime('%Y%m%d')
            # === (KẾT THÚC SỬA LỖI) ===

        except json.JSONDecodeError:
            logger.error(f"[Job {job_id}] Lỗi: Không thể parse 'job_payload' từ CSDL. Xóa SQS.", exc_info=True)
            return True # Xóa SQS (OK - vì nằm trong try lồng nhau)
        except Exception as e:
            logger.error(f"[Job {job_id}] Lỗi CSDL khi đọc job payload: {e}", exc_info=True)
            return False # Lỗi CSDL -> Giữ SQS để retry (OK - vì nằm trong try lồng nhau)

        # --- 2. Cập nhật Status: RUNNING ---
        update_job_status(db_session, job_id, "RUNNING")
        
        # === (SỬA LỖI PATCH) XÓA BỎ VIỆC DỌN DẸP S3 ===
        # (Việc dọn dẹp (nếu cần) sẽ do controller xử lý khi merge)
        # s3_prefix = f"tool03/{date_folder}/{job_id}/"
        # logger.info(f"[Job {job_id}] Dọn dẹp S3 prefix: {s3_prefix}...")
        # cleanup_success = s3_client.delete_files_by_prefix_from_s3(prefix=s3_prefix)
        # if not cleanup_success:
        #      logger.error(f"[Job {job_id}] Lỗi: Không thể dọn dẹp S3 prefix. Hủy job.")
        #      update_job_status(db_session, job_id, "FAILED", message="Lỗi hệ thống: Không thể dọn dẹp S3 (storage).")
        #      return True
        # === (KẾT THÚC SỬA LỖI PATCH) ===
        

        # --- 3. Vòng lặp xử lý ảnh (Logic chính) ---
        logger.info(f"[Job {job_id}] Bắt đầu xử lý {len(payload_rows)} ảnh...")
        
        factory = ImageFactory() # Khởi tạo factory (chứa các hàm A, B, C...)
        
        # === (SỬA LỖI PATCH) Khởi tạo results từ CSDL ===
        try:
            if job.job_results:
                final_results_dict = json.loads(job.job_results)
                logger.info(f"[Job {job_id}] Đã khôi phục {len(final_results_dict)} kết quả cũ (cho PATCH).")
            else:
                final_results_dict = {}
        except json.JSONDecodeError:
            final_results_dict = {} # Bắt đầu mới nếu JSON hỏng
        # === (KẾT THÚC SỬA LỖI PATCH) ===
        
        error_count = 0
        processed_count = 0 # (Đếm số ảnh *thực sự* chạy)

        for index, row in enumerate(payload_rows):
            row_id = row.id # (frontend ID)
            
            # === (SỬA LỖI PATCH) START ===
            # Kiểm tra xem row này đã 'Success' trong results cũ chưa
            if row_id in final_results_dict and final_results_dict[row_id].get('status') == 'Success':
                logger.debug(f"[Job {job_id}] Bỏ qua {row.productCode} (đã 'Success' từ trước).")
                continue # Bỏ qua, giữ lại kết quả cũ
            # === (KẾT THÚC SỬA LỖI PATCH) ===
            
            processed_count += 1
            current_result = Tool03ImageResult(status="Processing", filename=None, message=None)
            final_results_dict[row_id] = current_result.model_dump()
            
            # (Phần logic factory key giống hệt service.py cũ)
            template_name = row.template or "テンプレートA"
            base_key = template_name.replace("テンプレート", "")
            factory_key = base_key
            has_mobile_data = bool(row.mobileStartDate and row.mobileEndDate)
            potential_mobile_key = f"{base_key}-2"
            
            # (Kiểm tra xem key B-2, C-2... có tồn tại không)
            if has_mobile_data and hasattr(factory, f"draw_template_{potential_mobile_key}"):
                factory_key = potential_mobile_key
            
            logger.debug(f"[Job {job_id}] Đang xử lý {row.productCode} (Template: {factory_key})")
            
            try:
                # 3.1. Tạo ảnh (trong bộ nhớ)
                img: Image.Image = factory.draw(row, factory_key)
                
                # 3.2. Lưu ảnh vào thư mục TẠM
                output_filename = f"{row.productCode}.jpg"
                local_temp_path = temp_dir_path / output_filename
                img.save(local_temp_path, "JPEG", quality=95)
                img.close()
                
                # 3.3. Upload ảnh TẠM lên S3
                s3_object_key = f"tool03/{date_folder}/{job_id}/{output_filename}"
                upload_success = s3_client.upload_file_to_s3(
                    local_file_path=str(local_temp_path),
                    object_key=s3_object_key
                )
                
                if upload_success:
                    current_result.status = "Success"
                    current_result.filename = output_filename
                else:
                    error_count += 1
                    current_result.status = "Error"
                    current_result.message = "Lỗi: Upload S3 thất bại."

            except Exception as draw_error:
                logger.error(f"[Job {job_id}] Lỗi khi tạo ảnh {row.productCode} (Template: {factory_key}): {draw_error}", exc_info=True)
                error_count += 1
                current_result.status = "Error"
                current_result.message = f"Lỗi tạo ảnh: {draw_error}"
            
            # Cập nhật dict kết quả
            final_results_dict[row_id] = current_result.model_dump()

            # === SỬA LỖI (Lazy Load) START ===
            # Cập nhật CSDL (job_results và progress) sau mỗi lần xử lý
            # để frontend có thể "lazy load"
            try:
                # (job object đã được lấy ở đầu hàm)
                if job:
                    job.job_results = json.dumps(final_results_dict) # Ghi đè JSON mới nhất
                    job.progress = len(final_results_dict) # (SỬA LỖI PATCH)
                    db_session.commit()
                    logger.info(f"[Job {job_id}] Đã cập nhật CSDL (Progress: {len(final_results_dict)}/{len(payload_rows)})")
                else:
                    # (Trường hợp này không nên xảy ra)
                    logger.error(f"[Job {job_id}] Lỗi (trong-loop): Không tìm thấy 'job' object để cập nhật lazy load.")
            except Exception as loop_db_e:
                db_session.rollback()
                logger.error(f"[Job {job_id}] Lỗi CSDL (trong-loop) khi cập nhật results: {loop_db_e}", exc_info=True)
                # Không raise, tiếp tục xử lý ảnh tiếp theo
            # === SỬA LỖI (Lazy Load) END ===

        # --- 4. Hoàn tất vòng lặp ---
        
        # (SỬA LỖI PATCH) Đếm lại tổng số lỗi cuối cùng
        total_errors_final = sum(1 for res in final_results_dict.values() if res['status'] == 'Error')
        
        if total_errors_final == 0:
            final_job_status = "COMPLETED"
        else:
            final_job_status = "COMPLETED_WITH_ERRORS"
            
        logger.info(f"[Job {job_id}] Hoàn thành xử lý. Đã chạy {processed_count} ảnh. Status: {final_job_status}. Tổng lỗi: {total_errors_final}/{len(payload_rows)}.")
        
        # Đã xử lý xong (dù lỗi hay không) -> Xóa SQS
        should_delete_sqs_message = True 

    except Exception as e:
        # --- 5. Lỗi Hệ thống (Bên ngoài vòng lặp) ---
        # Ví dụ: Lỗi CSDL (lúc update RUNNING), Lỗi S3 (lúc Dọn dẹp)
        logger.critical(f"[Job {job_id}] LỖI HỆ THỐNG khi đang xử lý (TẠO ẢNH): {e}", exc_info=True)
        final_job_status = "FAILED"
        final_job_message = f"Lỗi hệ thống: {e}"
        
        # Nếu lỗi là CSDL (e.g., OperationalError), chúng ta không nên xóa SQS
        # (Giả định rằng `update_job_status` sẽ raise Exception nếu CSDL sập)
        should_delete_sqs_message = False 

    finally:
        # --- 6. Cập nhật CSDL (Lần cuối) & Dọn dẹp ---
        
        db_update_success = False
        
        try:
            # (SỬA LỖI (Lazy Load): 'job' object đã có, không cần query lại)
            # job = db_session.query(JobEntity).filter(JobEntity.job_id == job_id).first()
            if job:
                job.status = final_job_status
                job.message = final_job_message
                
                # (SỬA LỖI PATCH): Cập nhật job_results LẦN CUỐI
                # (Rất quan trọng nếu vòng lặp không chạy lần nào)
                job.job_results = json.dumps(final_results_dict)
                job.progress = len(final_results_dict)
                
                db_session.commit()
                logger.info(f"[Job {job_id}] Cập nhật CSDL: status={final_job_status} (Final).")
                db_update_success = True
            else:
                 logger.error(f"[Job {job_id}] Lỗi: Không tìm thấy job để CẬP NHẬT KẾT QUẢ CUỐI CÙNG.")
                 should_delete_sqs_message = True
                 
        except Exception as db_e:
            db_session.rollback()
            logger.error(f"[Job {job_id}] Lỗi khi CẬP NHẬT KẾT QUẢ (TẠO ẢNH) vào CSDL: {db_e}", exc_info=True)
            should_delete_sqs_message = False 
        
        # Đóng session CSDL
        if db_session:
            db_session.close()
            
        # Xóa thư mục tạm (luôn luôn)
        if temp_dir_path.exists():
            try:
                shutil.rmtree(temp_dir_path)
                logger.info(f"[Job {job_id}] Đã xóa thư mục tạm: {temp_dir_for_job}")
            except Exception as rm_e:
                logger.warning(f"[Job {job_id}] Lỗi khi xóa thư mục tạm {temp_dir_for_job}: {rm_e}")
                
    # --- SỬA LỖI PYLANCE (Di chuyển return ra ngoài) ---
    # Trả về kết quả (True=Xóa SQS, False=Retry)
    return should_delete_sqs_message

# =====================================================================
# === HÀM XỬ LÝ FTP (MỚI) ===
# =====================================================================
# ... (Hàm process_tool03_ftp_job không thay đổi) ...
def process_tool03_ftp_job(job_data: Dict[str, Any]) -> bool:
    """
    Hàm xử lý chính cho Tool03 (UPLOAD FTP).
    Được gọi bởi worker.py khi có job SQS (type: 'tool03_ftp').
    
    :param job_data: Nội dung message SQS (đã parse)
    :return: True (Xóa SQS) hoặc False (Giữ SQS - để retry)
    """
    job_id = job_data.get('job_id')
    target = job_data.get('target') # "gold" hoặc "rcabinet"
    
    if not job_id or not target:
        logger.error(f"[Worker] Lỗi: Nhận được job SQS (tool03_ftp) nhưng thiếu 'job_id' hoặc 'target'. Xóa SQS. Data: {job_data}")
        return True # Xóa message SQS (lỗi không thể retry)

    logger.info(f"[Job {job_id}] Bắt đầu xử lý (Tool 03 - FTP Upload). Target: {target}")

    # Tạo session CSDL
    db_session = SessionLocal()
    
    # Biến trạng thái CSDL
    ftp_status_key = f"ftp_status_{target}" # (e.g., ftp_status_gold)
    ftp_error_key = f"ftp_error_{target}" # (e.g., ftp_error_gold)
    
    # Biến cờ (để quyết định xóa SQS)
    should_delete_sqs_message = False

    # Tạo thư mục tạm (duy nhất) để chứa ảnh download từ S3
    temp_dir_for_ftp = tempfile.mkdtemp(prefix=f"ftp_{job_id}_{target}_")
    temp_dir_path = Path(temp_dir_for_ftp)

    try:
        # --- 1. Lấy Job (Đọc CSDL) ---
        job = db_session.query(JobEntity).filter(JobEntity.job_id == job_id).first()
        if not job:
            logger.error(f"[Job {job_id}] Lỗi (FTP): Job không tìm thấy trong CSDL. Xóa SQS.")
            return True # Xóa SQS
            
        # Lấy danh sách file (results)
        if not job.job_results:
             logger.error(f"[Job {job_id}] Lỗi (FTP): Job có trong CSDL nhưng 'job_results' rỗng (chưa tạo ảnh?). Xóa SQS.")
             update_job_status(db_session, job_id, job.status, message=f"Lỗi FTP: Không tìm thấy kết quả ảnh (job_results) để upload.")
             return True # Xóa SQS

        # Parse results
        results_data = json.loads(job.job_results)
        
        # === (SỬA LỖI PATCH) Lấy date_folder ===
        date_folder = job.create_datetime.strftime('%Y%m%d')
        # === (KẾT THÚC SỬA LỖI) ===
        
        # Lấy danh sách file "Success"
        files_to_upload: List[Dict[str, str]] = []
        for row_id, result in results_data.items():
            if result.get('status') == 'Success' and result.get('filename'):
                files_to_upload.append(result)
                
        if not files_to_upload:
            logger.warning(f"[Job {job_id}] (FTP): Không có file 'Success' nào trong job_results để upload. Đánh dấu SUCCESS.")
            # === (SỬA LỖI FTP 2) ===
            setattr(job, ftp_status_key, "SUCCESS")
            # ========================
            setattr(job, ftp_error_key, "Không có file 'Success' để upload.")
            db_session.commit()
            return True # Xóa SQS

        # --- 2. Cập nhật Status: UPLOADING ---
        setattr(job, ftp_status_key, "UPLOADING")
        setattr(job, ftp_error_key, None)
        db_session.commit()
        logger.info(f"[Job {job_id}] Cập nhật CSDL (FTP): status=UPLOADING")

        # --- 3. Download file từ S3 về thư mục tạm ---
        logger.info(f"[Job {job_id}] (FTP): Bắt đầu download {len(files_to_upload)} file từ S3 về thư mục tạm...")
        
        for file_info in files_to_upload:
            # === (SỬA LỖI PATCH) Dùng S3 key MỚI ===
            s3_object_key = f"tool03/{date_folder}/{job_id}/{file_info['filename']}"
            # === (KẾT THÚC SỬA LỖI) ===
            local_temp_path = temp_dir_path / file_info['filename']
            
            download_success = s3_client.download_file_from_s3(
                object_key=s3_object_key,
                local_file_path=str(local_temp_path)
            )
            if not download_success:
                # Nếu 1 file lỗi -> Hủy toàn bộ job FTP
                logger.error(f"[Job {job_id}] (FTP): Lỗi download file từ S3: {s3_object_key}. Hủy job FTP.")
                raise Exception(f"Lỗi S3: Không thể download file {s3_object_key}")

        logger.info(f"[Job {job_id}] (FTP): Download S3 hoàn tất. Bắt đầu kết nối FTP...")

        # --- 4. Thực hiện Logic FTP (Lấy từ service.py cũ) ---
        # ... (Logic FTP không thay đổi) ...
        ftp_configs = {
            "gold": {
                "host": "ftp.rakuten.ne.jp", "port": 16910, "user": "auc-ronnefeldt",
                "password": "Ronne@04", "remote_dir": "/public_html/tools/03/"
            },
            "rcabinet": {
                 "host": "upload.rakuten.ne.jp", "port": 16910, "user": "auc-ronnefeldt",
                 "password": "Ronne@04", "remote_dir": "/images/"
            }
        }
        config = ftp_configs.get(target)
        if not config:
             raise ValueError(f"Cấu hình FTP target '{target}' không tồn tại.")
        ftp = ftplib.FTP()
        ftp.connect(config['host'], config['port'], timeout=30) # 30 giây timeout
        ftp.login(config['user'], config['password'])
        ftp.set_pasv(True)
        try:
             ftp.cwd(config['remote_dir'])
        except ftplib.error_perm as e:
             if "550" in str(e): # Thư mục không tồn tại
                  logger.warning(f"[Job {job_id}] (FTP): Thư mục {config['remote_dir']} không tồn tại. Đang thử tạo...")
                  parts = Path(config['remote_dir']).parts
                  current_dir = "/"
                  for part in parts:
                      if not part or part == "/": continue
                      current_dir = os.path.join(current_dir, part)
                      try:
                          ftp.mkd(current_dir)
                      except ftplib.error_perm as mkd_e:
                          if "550" not in str(mkd_e): # Bỏ qua nếu đã tồn tại
                              raise
                  ftp.cwd(config['remote_dir'])
             else:
                  raise # Lỗi permission
        for file_info in files_to_upload:
            local_path = temp_dir_path / file_info['filename']
            remote_path = file_info['filename'] # Chỉ upload file (không có thư mục job_id)
            with open(local_path, 'rb') as file:
                ftp.storbinary(f'STOR {remote_path}', file)
                logger.info(f"[Job {job_id}] (FTP): Upload thành công: {remote_path}")
        logger.info(f"[Job {job_id}] (FTP): Upload {target} thành công {len(files_to_upload)} file.")

        
        # --- 5. Hoàn tất (Thành công) ---
        # === (SỬA LỖI FTP 1) ===
        setattr(job, ftp_status_key, "SUCCESS")
        # =======================
        setattr(job, ftp_error_key, None)
        db_session.commit()
        
        should_delete_sqs_message = True # Xóa SQS
        
    except Exception as e:
        # --- 5. Hoàn tất (Thất bại) ---
        # ... (Logic xử lý lỗi FTP không thay đổi) ...
        error_message = f"Lỗi FTP ({target}): {e}"
        logger.error(f"[Job {job_id}] {error_message}", exc_info=True)
        try:
            job = db_session.query(JobEntity).filter(JobEntity.job_id == job_id).first()
            if job:
                setattr(job, ftp_status_key, "FAILED")
                setattr(job, ftp_error_key, error_message)
                db_session.commit()
            should_delete_sqs_message = True
        except Exception as db_e:
            db_session.rollback()
            logger.error(f"[Job {job_id}] Lỗi CSDL khi đang xử lý LỖI FTP: {db_e}", exc_info=True)
            should_delete_sqs_message = False

    finally:
        # --- 6. Dọn dẹp ---
        # ... (Logic dọn dẹp không thay đổi) ...
        if db_session:
            db_session.close()
        if temp_dir_path.exists():
            try:
                shutil.rmtree(temp_dir_path)
                logger.info(f"[Job {job_id}] (FTP): Đã xóa thư mục tạm: {temp_dir_for_ftp}")
            except Exception as rm_e:
                logger.warning(f"[Job {job_id}] (FTP): Lỗi khi xóa thư mục tạm {temp_dir_for_ftp}: {rm_e}")
                
    # Trả về kết quả
    return should_delete_sqs_message

# =====================================================================
# === FACTORY LOGIC (Di dời từ service.py) ===
# (Toàn bộ logic tạo ảnh nằm ở đây, tách biệt khỏi API)
# =====================================================================

# --- HELPER FUNCTIONS (Giống service.py cũ) ---
# ... (Toàn bộ logic Factory không thay đổi) ...
def calculate_font_size(text: str, font_path: str, box_width: int, box_height: int) -> int:
    font_size = 1
    max_font_size = box_height + 10
    try:
        while font_size <= max_font_size:
            font = ImageFont.truetype(str(font_path), font_size)
            bbox = font.getbbox(text)
            if bbox is None: return max(1, font_size - 1)
            width = bbox[2] - bbox[0]
            height = bbox[3] - bbox[1]
            if width > box_width or height > box_height:
                return max(1, font_size - 1)
            font_size += 1
        return max(1, font_size - 1)
    except IOError:
        logger.error(f"フォントファイルを開けません: {font_path}")
        return 1
    except Exception as e:
        logger.error(f"フォント '{font_path}' のサイズ計算中にエラー: {e}")
        return 1
try:
    HANDLER_FILE_PATH = Path(__file__).resolve()
    APP_DIR = HANDLER_FILE_PATH.parent.parent
    PROJECT_ROOT = APP_DIR.parent
    ASSETS_DIR = PROJECT_ROOT / "assets"
    if not ASSETS_DIR.is_dir():
        ASSETS_DIR = APP_DIR / "assets"
        if not ASSETS_DIR.is_dir():
            ASSETS_DIR = PROJECT_ROOT / "app" / "assets"
            if not ASSETS_DIR.is_dir():
                raise FileNotFoundError("Không tìm thấy thư mục 'assets' (đã tìm ở /assets, /app/assets)")
    FONTS_DIR = ASSETS_DIR / "fonts"
    if not FONTS_DIR.is_dir():
         raise FileNotFoundError(f"Không tìm thấy thư mục Fonts: {FONTS_DIR}")
    TOOL03_TEMPLATES_DIR_OPTION1 = ASSETS_DIR / "tool03" / "templates"
    TOOL03_TEMPLATES_DIR_OPTION2 = APP_DIR / "tool03" / "assets" / "templates"
    if TOOL03_TEMPLATES_DIR_OPTION1.is_dir():
        TOOL03_TEMPLATES_DIR = TOOL03_TEMPLATES_DIR_OPTION1
    elif TOOL03_TEMPLATES_DIR_OPTION2.is_dir():
        TOOL03_TEMPLATES_DIR = TOOL03_TEMPLATES_DIR_OPTION2
    else:
        raise FileNotFoundError(f"Không tìm thấy thư mục 'tool03/templates' (Đã tìm {TOOL03_TEMPLATES_DIR_OPTION1} và {TOOL03_TEMPLATES_DIR_OPTION2})")
    logger.info(f"Đã load thành công Assets: {ASSETS_DIR}")
    logger.info(f"Đã load thành công Fonts: {FONTS_DIR}")
    logger.info(f"Đã load thành công Templates Tool03: {TOOL03_TEMPLATES_DIR}")
except Exception as path_e:
     logger.critical(f"LỖI NGHIÊM TRỌNG KHI LOAD PATHS: {path_e}", exc_info=True)
     raise path_e
class ImageFactory:
    def __init__(self):
        self.font_path_arial=FONTS_DIR/'ARIALNB.TTF';self.font_path_yugothB=FONTS_DIR/'YuGothB.ttc';self.font_path_noto_sans_black=FONTS_DIR/'NotoSansJP-Black.ttf';self.font_path_noto_sans_bold=FONTS_DIR/'NotoSansJP-Bold.ttf';self.font_path_noto_sans_medium=FONTS_DIR/'NotoSansJP-Medium.ttf';self.font_path_noto_serif_extrabold=FONTS_DIR/'NotoSerifJP-ExtraBold.ttf';self.font_path_reddit=FONTS_DIR/'RedditSans-ExtraBold.ttf';self.font_path_reddit_condensed_extrabold=FONTS_DIR/'RedditSansCondensed-ExtraBold.ttf';self.font_path_shippori_bold=FONTS_DIR/'ShipporiMinchoB1-Bold.ttf';self.font_path_public_sans_bold=FONTS_DIR/'PublicSans-Bold.ttf'
        self.WHITE=(255,255,255);self.BLACK=(0,0,0);self.RED=(255,0,0)
        self.width=800;self.height=800
        self.mobile_start_datetime_params={'font_path':self.font_path_noto_sans_black,'font_color':self.WHITE,'x1':35,'y1':1250,'x2':475,'y2':1319,'align':'right'};
        self.mobile_end_datetime_params={'font_path':self.font_path_noto_sans_black,'font_color':self.WHITE,'x1':535,'y1':1250,'x2':975,'y2':1319,'align':'left'}
    def get_template_path(self, template_key: str, has_mobile_data: bool) -> Path:
        base_key = template_key.split('-')[0]
        template_file_name_base = f"template_{base_key}"
        suffix = ".jpg"
        mobile_template_path = TOOL03_TEMPLATES_DIR / f"{template_file_name_base}-2{suffix}"
        normal_template_path = TOOL03_TEMPLATES_DIR / f"{template_file_name_base}{suffix}"
        if has_mobile_data and mobile_template_path.exists():
            logger.debug(f"Sử dụng template Mobile: {mobile_template_path.name}")
            return mobile_template_path
        if not normal_template_path.exists():
            logger.error(f"Template cơ bản không tồn tại: {normal_template_path}")
            raise FileNotFoundError(f"Template cơ bản không tồn tại: {normal_template_path}")
        logger.debug(f"Sử dụng template Thường: {normal_template_path.name}")
        return normal_template_path
    def _get_text_size(self, text: str, font: ImageFont.FreeTypeFont) -> tuple[int, int]:
        try:
            bbox = font.getbbox(text)
            if bbox is None: return 0, 0
            width = bbox[2] - bbox[0]
            height = bbox[3] - bbox[1]
            return width, height
        except Exception as e:
            logger.error(f"Lỗi _get_text_size cho '{text}': {e}")
            return 0, 0
    def _place_text(self, draw: ImageDraw.Draw, params: Dict[str, Any]):
        text = str(params.get('text', ''))
        if not text:
            return
        font_path = str(params['font_path'])
        font_color = params['font_color']
        x1, y1, x2, y2 = params['x1'], params['y1'], params['x2'], params['y2']
        align = params.get('align', 'left')
        box_width = x2 - x1
        box_height = y2 - y1
        if box_width <= 0 or box_height <= 0:
            logger.warning(f"Bounding box không hợp lệ cho text '{text}': ({x1},{y1})-({x2},{y2})")
            return
        font_size = calculate_font_size(text, font_path, box_width, box_height)
        if font_size <= 0:
             logger.warning(f"Font size tính toán = 0 cho text '{text}'")
             return
        try:
            font = ImageFont.truetype(font_path, font_size)
            text_width, _ = self._get_text_size(text, font)
            if align == 'left':
                x = x1
            elif align == 'center':
                x = x1 + (box_width - text_width) / 2
            elif align == 'right':
                x = x2 - text_width
            else:
                x = x1
            bbox = font.getbbox(text)
            if bbox is None: raise ValueError("font.getbbox() trả về None")
            text_actual_height = bbox[3] - bbox[1]
            y_offset = bbox[1]
            y = y1 + (box_height - text_actual_height) / 2 - y_offset
            draw.text((x, y), text, fill=font_color, font=font)
        except Exception as e:
            logger.error(f"Lỗi khi vẽ text '{text}' (Font {font_path} Size {font_size}): {e}", exc_info=True)
    def _format_price(self, price_str: Optional[str]) -> str:
        if price_str is None: return ""
        try:
            price_decimal = Decimal(price_str).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
            return f"{int(price_decimal):,}"
        except Exception:
            return str(price_str)
    def _calculate_discount_display(self, regular_price_str: Optional[str], sale_price_str: Optional[str], discount_type: Optional[str]) -> str:
        if regular_price_str is None or sale_price_str is None: return ""
        try:
            regular_price = Decimal(regular_price_str)
            sale_price = Decimal(sale_price_str)
            if regular_price <= 0 or regular_price <= sale_price: return ""
            difference = regular_price - sale_price
            if discount_type == "yen":
                discount_val = difference.quantize(Decimal('1'), rounding=ROUND_HALF_UP)
                return f"{int(discount_val):,}円"
            else:
                percentage = (difference / regular_price * 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
                return f"{int(percentage)}%"
        except Exception as e:
            logger.warning(f"Lỗi tính toán giảm giá ({regular_price_str}, {sale_price_str}, {discount_type}): {e}")
            return ""
    def _format_datetime_jp(self, iso_str: Optional[str]) -> str:
        if not iso_str:
            return ""
        try:
            dt = datetime.datetime.fromisoformat(iso_str)
            return f"{dt.month}月{dt.day}日{dt.hour}:{dt.minute:02d}"
        except ValueError:
            logger.warning(f"Sai định dạng datetime ISO: {iso_str}")
            return iso_str 
        except Exception as e:
            logger.error(f"Lỗi format datetime ({iso_str}): {e}")
            return iso_str 
    def _place_price_group(self, draw: ImageDraw.Draw, price_params: Dict, unit_params: Dict, suffix_params: Dict):
        price_text = str(price_params.get('text', ''))
        unit_text = str(unit_params.get('text', ''))
        suffix_text = str(suffix_params.get('text', ''))
        if not price_text: return
        gap_width = 5
        try:
            price_font = ImageFont.truetype(str(price_params['font_path']), price_params['font_size'])
            unit_font = ImageFont.truetype(str(unit_params['font_path']), unit_params['font_size']) if unit_text else None
            suffix_font = ImageFont.truetype(str(suffix_params['font_path']), suffix_params['font_size']) if suffix_text else None
            price_w, _ = self._get_text_size(price_text, price_font)
            unit_w, _ = self._get_text_size(unit_text, unit_font) if unit_font else (0, 0)
            suffix_w, _ = self._get_text_size(suffix_text, suffix_font) if suffix_font else (0, 0)
            total_width = price_w
            if unit_text: total_width += gap_width + unit_w
            if suffix_text: total_width += gap_width + suffix_w
            container_width = price_params['x_end'] - price_params['x_origin']
            start_x = price_params['x_origin'] + (container_width - total_width) / 2
            price_y = price_params['y_origin']
            draw.text((start_x, price_y), price_text, fill=price_params['font_color'], font=price_font)
            current_x = start_x + price_w
            if unit_font:
                current_x += gap_width
                unit_y = price_y + unit_params.get('dy', 0)
                draw.text((current_x, unit_y), unit_text, fill=unit_params['font_color'], font=unit_font)
                current_x += unit_w
            if suffix_font:
                current_x += gap_width
                suffix_y = price_y + suffix_params.get('dy', 0)
                draw.text((current_x, suffix_y), suffix_text, fill=suffix_params['font_color'], font=suffix_font)
        except Exception as e:
            logger.error(f"Lỗi _place_price_group cho giá '{price_text}': {e}", exc_info=True)
    def draw(self, row_data: Tool03ProductRowInput, template_key: str) -> Image.Image:
        has_mobile_data = bool(row_data.mobileStartDate and row_data.mobileEndDate)
        draw_function_name = f"draw_template_{template_key}"
        draw_function = getattr(self, draw_function_name, None)
        if not callable(draw_function):
            logger.error(f"Không tìm thấy hàm vẽ cho template key: '{template_key}' (Đã tìm {draw_function_name})")
            raise NotImplementedError(f"Template không được hỗ trợ: {template_key}")
        original_height = self.height # (Lưu lại height gốc)
        try:
            template_path = self.get_template_path(template_key, has_mobile_data)
            if has_mobile_data and template_path.name.endswith("-2.jpg"):
                self.height = 1370 # Tạm thời đổi height
            img = Image.open(template_path).convert("RGB")
            draw_obj = ImageDraw.Draw(img)
            draw_function(draw_obj, row_data)
            if has_mobile_data and template_path.name.endswith("-2.jpg"):
                 self.draw_mobile_details(draw_obj, row_data) # Vẽ phần mobile
            return img
        except FileNotFoundError:
            logger.error(f"Không tìm thấy file template cho key '{template_key}' (Mobile: {has_mobile_data})")
            raise
        except Exception as e:
            logger.error(f"Lỗi không xác định khi vẽ template '{template_key}': {e}", exc_info=True)
            raise
        finally:
            self.height = original_height # (Reset height)
    def draw_mobile_details(self, draw: ImageDraw.Draw, row_data: Tool03ProductRowInput):
        if row_data.mobileStartDate:
            self._place_text(draw, {**self.mobile_start_datetime_params, 'text': self._format_datetime_jp(row_data.mobileStartDate)})
        if row_data.mobileEndDate:
            self._place_text(draw, {**self.mobile_end_datetime_params, 'text': self._format_datetime_jp(row_data.mobileEndDate)})
    def draw_template_A(self, draw: ImageDraw.Draw, row_data: Tool03ProductRowInput):
        self.width, self.height = 800, 880
        RED = (189, 41, 39)
        start_datetime_params={'font_path':self.font_path_noto_sans_black,'font_color':self.BLACK,'x1':270,'y1':80,'x2':771,'y2':125,'align':'center'}
        end_datetime_params={'font_path':self.font_path_noto_sans_black,'font_color':self.BLACK,'x1':270,'y1':190,'x2':771,'y2':235,'align':'center'}
        message_params={'font_path':self.font_path_noto_sans_black,'font_color':RED,'x1':30,'y1':280,'x2':770,'y2':370,'align':'center'}
        price_type_params={'font_path':self.font_path_noto_sans_bold, 'font_color':self.WHITE, 'x1':65, 'y1':410, 'x2':805, 'y2':450, 'align':'left'}
        normal_price_group={
            'price': {'text':'', 'font_path':self.font_path_public_sans_bold,'font_size':60,'font_color':self.WHITE,'x_origin':330,'x_end':740,'y_origin':395},
            'unit':  {'text':'円', 'font_path':self.font_path_noto_sans_black, 'font_size':30,'font_color':self.WHITE,'dy':20},
            'suffix':{'text':'のところ','font_path':self.font_path_noto_sans_black,'font_size':25,'font_color':self.WHITE,'dy':25}
        }
        discount_group={
             'price': {'text':'', 'font_path':self.font_path_public_sans_bold,'font_size':85,'font_color':self.BLACK,'x_origin':0,'x_end':self.width,'y_origin':485},
             'unit':  {'text':'', 'font_path':self.font_path_noto_sans_black, 'font_size':50,'font_color':self.BLACK,'dy':20},
             'suffix':{'text':'OFF','font_path':self.font_path_noto_sans_black,'font_size':30,'font_color':self.BLACK,'dy':45}
        }
        sale_price_group={
            'price': {'text':'', 'font_path':self.font_path_public_sans_bold,'font_size':160,'font_color':RED,'x_origin':0,'x_end':self.width,'y_origin':620},
            'unit':  {'text':'円', 'font_path':self.font_path_noto_sans_black, 'font_size':50,'font_color':RED,'dy':90},
            'suffix':{'text':'税込','font_path':self.font_path_noto_sans_black,'font_size':20,'font_color':RED,'dy':70}
        }
        self._place_text(draw, {**start_datetime_params, 'text': self._format_datetime_jp(row_data.startDate)})
        self._place_text(draw, {**end_datetime_params, 'text': self._format_datetime_jp(row_data.endDate)})
        self._place_text(draw, {**message_params, 'text': row_data.saleText or ""})
        self._place_text(draw, {**price_type_params, 'text': row_data.priceType or ""})
        normal_price_group['price']['text'] = self._format_price(row_data.regularPrice)
        sale_price_group['price']['text'] = self._format_price(row_data.salePrice)
        discount_text_val = self._calculate_discount_display(row_data.regularPrice, row_data.salePrice, row_data.discountType)
        discount_number = discount_text_val.replace('%', '').replace('円', '')
        discount_unit_text = '%' if '%' in discount_text_val else '円' if '円' in discount_text_val else ''
        discount_group['price']['text'] = discount_number
        discount_group['unit']['text'] = discount_unit_text
        self._place_price_group(draw, normal_price_group['price'], normal_price_group['unit'], normal_price_group['suffix'])
        self._place_price_group(draw, discount_group['price'], discount_group['unit'], discount_group['suffix'])
        self._place_price_group(draw, sale_price_group['price'], sale_price_group['unit'], sale_price_group['suffix'])
    def draw_template_B(self, draw: ImageDraw.Draw, row_data: Tool03ProductRowInput):
        self.width, self.height = 1000, 1000
        YELLOW=(255,239,0); RED=(215,0,0)
        start_datetime_params={'font_path':self.font_path_noto_sans_black,'font_color':RED,'x1':25,'y1':162,'x2':465,'y2':231,'align':'right'}
        end_datetime_params={'font_path':self.font_path_noto_sans_black,'font_color':RED,'x1':555,'y1':162,'x2':995,'y2':231,'align':'left'}
        message_params={'font_path':self.font_path_noto_sans_black,'font_color':RED,'x1':107,'y1':38,'x2':894,'y2':148,'align':'center'}
        price_type_params={'font_path':self.font_path_noto_sans_black, 'font_color':self.WHITE, 'x1':0, 'y1':310, 'x2':1000, 'y2':360, 'align':'center'}
        normal_price_group={
            'price': {'text':'','font_path':self.font_path_reddit,'font_size':130,'font_color':self.WHITE,'x_origin':0,'x_end':self.width,'y_origin':370},
            'unit':  {'text':'円','font_path':self.font_path_noto_sans_black,'font_size':70,'font_color':self.WHITE,'dy':35},
            'suffix':{'text':'のところ','font_path':self.font_path_noto_sans_black,'font_size':50,'font_color':self.WHITE,'dy':65}
        }
        discount_group={
             'price': {'text':'','font_path':self.font_path_reddit,'font_size':95,'font_color':RED,'x_origin':0,'x_end':self.width,'y_origin':540},
             'unit':  {'text':'','font_path':self.font_path_noto_sans_black,'font_size':60,'font_color':RED,'dy':20},
             'suffix':{'text':'OFF','font_path':self.font_path_noto_sans_black,'font_size':40,'font_color':RED,'dy':45}
        }
        sale_price_group={
            'price': {'text':'','font_path':self.font_path_reddit,'font_size':230,'font_color':YELLOW,'x_origin':0,'x_end':self.width,'y_origin':660},
            'unit':  {'text':'円','font_path':self.font_path_noto_sans_black,'font_size':70,'font_color':YELLOW,'dy':130},
            'suffix':{'text':'税込','font_path':self.font_path_noto_sans_black,'font_size':30,'font_color':YELLOW,'dy':100}
        }
        self._place_text(draw, {**start_datetime_params, 'text': self._format_datetime_jp(row_data.startDate)})
        self._place_text(draw, {**end_datetime_params, 'text': self._format_datetime_jp(row_data.endDate)})
        self._place_text(draw, {**message_params, 'text': row_data.saleText or ""})
        self._place_text(draw, {**price_type_params, 'text': row_data.priceType or ""})
        normal_price_group['price']['text'] = self._format_price(row_data.regularPrice)
        sale_price_group['price']['text'] = self._format_price(row_data.salePrice)
        discount_text_val = self._calculate_discount_display(row_data.regularPrice, row_data.salePrice, row_data.discountType)
        discount_number = discount_text_val.replace('%', '').replace('円', '')
        discount_unit_text = '%' if '%' in discount_text_val else '円' if '円' in discount_text_val else ''
        discount_group['price']['text'] = discount_number
        discount_group['unit']['text'] = discount_unit_text
        self._place_price_group(draw, normal_price_group['price'], normal_price_group['unit'], normal_price_group['suffix'])
        self._place_price_group(draw, discount_group['price'], discount_group['unit'], discount_group['suffix'])
        self._place_price_group(draw, sale_price_group['price'], sale_price_group['unit'], sale_price_group['suffix'])
    def draw_template_B_2(self, draw: ImageDraw.Draw, row_data: Tool03ProductRowInput):
        self.draw_template_B(draw, row_data)
    def draw_template_C(self, draw: ImageDraw.Draw, row_data: Tool03ProductRowInput):
        self.width, self.height = 1000, 1000
        YELLOW=(235, 210, 150); RED=(150,0,0)
        start_datetime_params={'font_path':self.font_path_shippori_bold,'font_color':self.WHITE,'x1':25,'y1':187,'x2':465,'y2':252,'align':'right'}
        end_datetime_params={'font_path':self.font_path_shippori_bold,'font_color':self.WHITE,'x1':530,'y1':187,'x2':960,'y2':252,'align':'left'}
        message_params={'font_path':self.font_path_shippori_bold,'font_color':self.WHITE,'x1':107,'y1':38,'x2':894,'y2':170,'align':'center'}
        price_type_params={'font_path':self.font_path_shippori_bold, 'font_color':self.WHITE, 'x1':0, 'y1':310, 'x2':1000, 'y2':360, 'align':'center'}
        normal_price_group={
            'price': {'text':'','font_path':self.font_path_shippori_bold,'font_size':130,'font_color':self.WHITE,'x_origin':0,'x_end':self.width,'y_origin':360},
            'unit':  {'text':'円','font_path':self.font_path_shippori_bold,'font_size':70,'font_color':self.WHITE,'dy':65},
            'suffix':{'text':'のところ','font_path':self.font_path_shippori_bold,'font_size':50,'font_color':self.WHITE,'dy':95}
        }
        discount_group={
             'price': {'text':'','font_path':self.font_path_shippori_bold,'font_size':95,'font_color':RED,'x_origin':0,'x_end':self.width,'y_origin':530},
             'unit':  {'text':'','font_path':self.font_path_shippori_bold,'font_size':60,'font_color':RED,'dy':40},
             'suffix':{'text':'OFF','font_path':self.font_path_shippori_bold,'font_size':40,'font_color':RED,'dy':65}
        }
        sale_price_group={
            'price': {'text':'','font_path':self.font_path_shippori_bold,'font_size':200,'font_color':YELLOW,'x_origin':0,'x_end':self.width,'y_origin':650},
            'unit':  {'text':'円','font_path':self.font_path_shippori_bold,'font_size':70,'font_color':YELLOW,'dy':145},
            'suffix':{'text':'税込','font_path':self.font_path_shippori_bold,'font_size':30,'font_color':YELLOW,'dy':115}
        }
        self._place_text(draw, {**start_datetime_params, 'text': self._format_datetime_jp(row_data.startDate)})
        self._place_text(draw, {**end_datetime_params, 'text': self._format_datetime_jp(row_data.endDate)})
        self._place_text(draw, {**message_params, 'text': row_data.saleText or ""})
        self._place_text(draw, {**price_type_params, 'text': row_data.priceType or ""})
        normal_price_group['price']['text'] = self._format_price(row_data.regularPrice)
        sale_price_group['price']['text'] = self._format_price(row_data.salePrice)
        discount_text_val = self._calculate_discount_display(row_data.regularPrice, row_data.salePrice, row_data.discountType)
        discount_number = discount_text_val.replace('%', '').replace('円', '')
        discount_unit_text = '%' if '%' in discount_text_val else '円' if '円' in discount_text_val else ''
        discount_group['price']['text'] = discount_number
        discount_group['unit']['text'] = discount_unit_text
        self._place_price_group(draw, normal_price_group['price'], normal_price_group['unit'], normal_price_group['suffix'])
        self._place_price_group(draw, discount_group['price'], discount_group['unit'], discount_group['suffix'])
        self._place_price_group(draw, sale_price_group['price'], sale_price_group['unit'], sale_price_group['suffix'])
    def draw_template_C_2(self, draw: ImageDraw.Draw, row_data: Tool03ProductRowInput):
        self.draw_template_C(draw, row_data)
    def draw_template_D(self, draw: ImageDraw.Draw, row_data: Tool03ProductRowInput):
        self.width, self.height = 1000, 1000
        BROWN=(90,70,50); RED=(215,0,0)
        start_datetime_params={'font_path':self.font_path_noto_sans_black,'font_color':self.WHITE,'x1':25,'y1':187,'x2':465,'y2':252,'align':'right'}
        end_datetime_params={'font_path':self.font_path_noto_sans_black,'font_color':self.WHITE,'x1':530,'y1':187,'x2':960,'y2':252,'align':'left'}
        message_params={'font_path':self.font_path_noto_sans_black,'font_color':self.WHITE,'x1':107,'y1':38,'x2':894,'y2':170,'align':'center'}
        price_type_params={'font_path':self.font_path_noto_sans_black, 'font_color':BROWN, 'x1':0, 'y1':315, 'x2':1000, 'y2':370, 'align':'center'}
        normal_price_group={
            'price': {'text':'','font_path':self.font_path_public_sans_bold,'font_size':130,'font_color':BROWN,'x_origin':0,'x_end':self.width,'y_origin':380},
            'unit':  {'text':'円','font_path':self.font_path_noto_sans_black,'font_size':70,'font_color':BROWN,'dy':35},
            'suffix':{'text':'のところ','font_path':self.font_path_noto_sans_black,'font_size':50,'font_color':BROWN,'dy':60}
        }
        discount_group={
             'price': {'text':'','font_path':self.font_path_public_sans_bold,'font_size':85,'font_color':self.WHITE,'x_origin':0,'x_end':self.width,'y_origin':550},
             'unit':  {'text':'','font_path':self.font_path_noto_sans_black,'font_size':50,'font_color':self.WHITE,'dy':15},
             'suffix':{'text':'OFF','font_path':self.font_path_noto_sans_black,'font_size':30,'font_color':self.WHITE,'dy':40}
        }
        sale_price_group={
            'price': {'text':'','font_path':self.font_path_public_sans_bold,'font_size':200,'font_color':RED,'x_origin':0,'x_end':self.width,'y_origin':700},
            'unit':  {'text':'円','font_path':self.font_path_noto_sans_black,'font_size':70,'font_color':RED,'dy':95},
            'suffix':{'text':'税込','font_path':self.font_path_noto_sans_black,'font_size':30,'font_color':RED,'dy':65}
        }
        self._place_text(draw, {**start_datetime_params, 'text': self._format_datetime_jp(row_data.startDate)})
        self._place_text(draw, {**end_datetime_params, 'text': self._format_datetime_jp(row_data.endDate)})
        self._place_text(draw, {**message_params, 'text': row_data.saleText or ""})
        self._place_text(draw, {**price_type_params, 'text': row_data.priceType or ""})
        normal_price_group['price']['text'] = self._format_price(row_data.regularPrice)
        sale_price_group['price']['text'] = self._format_price(row_data.salePrice)
        discount_text_val = self._calculate_discount_display(row_data.regularPrice, row_data.salePrice, row_data.discountType)
        discount_number = discount_text_val.replace('%', '').replace('円', '')
        discount_unit_text = '%' if '%' in discount_text_val else '円' if '円' in discount_text_val else ''
        discount_group['price']['text'] = discount_number
        discount_group['unit']['text'] = discount_unit_text
        self._place_price_group(draw, normal_price_group['price'], normal_price_group['unit'], normal_price_group['suffix'])
        self._place_price_group(draw, discount_group['price'], discount_group['unit'], discount_group['suffix'])
        self._place_price_group(draw, sale_price_group['price'], sale_price_group['unit'], sale_price_group['suffix'])
    def draw_template_D_2(self, draw: ImageDraw.Draw, row_data: Tool03ProductRowInput):
        self.draw_template_D(draw, row_data)
    def draw_template_E(self, draw: ImageDraw.Draw, row_data: Tool03ProductRowInput):
        self.width, self.height = 1000, 1000
        SILVER=(204,204,204); GOLD=(235, 210, 150)
        start_datetime_params={'font_path':self.font_path_shippori_bold,'font_color':self.BLACK,'x1':25,'y1':200,'x2':465,'y2':265,'align':'right'}
        end_datetime_params={'font_path':self.font_path_shippori_bold,'font_color':self.BLACK,'x1':530,'y1':200,'x2':960,'y2':265,'align':'left'}
        message_params={'font_path':self.font_path_shippori_bold,'font_color':self.BLACK,'x1':107,'y1':38,'x2':894,'y2':170,'align':'center'}
        price_type_params={'font_path':self.font_path_shippori_bold, 'font_color':SILVER, 'x1':0, 'y1':325, 'x2':1000, 'y2':385, 'align':'center'}
        normal_price_group={
            'price': {'text':'','font_path':self.font_path_shippori_bold,'font_size':130,'font_color':SILVER,'x_origin':0,'x_end':self.width,'y_origin':360},
            'unit':  {'text':'円','font_path':self.font_path_shippori_bold,'font_size':70,'font_color':SILVER,'dy':65},
            'suffix':{'text':'のところ','font_path':self.font_path_shippori_bold,'font_size':50,'font_color':SILVER,'dy':95}
        }
        discount_params={
            'font_path':self.font_path_shippori_bold,
            'font_color':GOLD,
            'x1': 645, 'y1': 620, 'x2': 965, 'y2': 670,
            'align':'center'
        }
        sale_price_group={
            'price': {'text':'','font_path':self.font_path_shippori_bold,'font_size':200,'font_color':GOLD,'x_origin':0,'x_end':self.width,'y_origin':650},
            'unit':  {'text':'円','font_path':self.font_path_shippori_bold,'font_size':70,'font_color':GOLD,'dy':145},
            'suffix':{'text':'税込','font_path':self.font_path_shippori_bold,'font_size':30,'font_color':GOLD,'dy':115}
        }
        self._place_text(draw, {**start_datetime_params, 'text': self._format_datetime_jp(row_data.startDate)})
        self._place_text(draw, {**end_datetime_params, 'text': self._format_datetime_jp(row_data.endDate)})
        self._place_text(draw, {**message_params, 'text': row_data.saleText or ""})
        self._place_text(draw, {**price_type_params, 'text': row_data.priceType or ""})
        normal_price_group['price']['text'] = self._format_price(row_data.regularPrice)
        sale_price_group['price']['text'] = self._format_price(row_data.salePrice)
        discount_text_val = self._calculate_discount_display(row_data.regularPrice, row_data.salePrice, row_data.discountType)
        discount_display_text = ""
        if discount_text_val:
         discount_number = discount_text_val.replace('%', '').replace('円', '')
         if '%' in discount_text_val:
             discount_display_text = f"{discount_number}%OFF"
         elif '円' in discount_text_val:
             discount_display_text = f"{discount_number}円OFF"
        self._place_text(draw, {**discount_params, 'text': discount_display_text})
        self._place_price_group(draw, normal_price_group['price'], normal_price_group['unit'], normal_price_group['suffix'])
        self._place_price_group(draw, sale_price_group['price'], sale_price_group['unit'], sale_price_group['suffix'])
    def draw_template_E_2(self, draw: ImageDraw.Draw, row_data: Tool03ProductRowInput):
        self.draw_template_E(draw, row_data)
    def draw_template_F(self, draw: ImageDraw.Draw, row_data: Tool03ProductRowInput):
        self.width, self.height = 1000, 1000
        BLACK=(93, 95, 96); GOLD=(210, 172, 67)
        start_datetime_params={'font_path':self.font_path_shippori_bold,'font_color':GOLD,'x1':25,'y1':187,'x2':465,'y2':252,'align':'right'}
        end_datetime_params={'font_path':self.font_path_shippori_bold,'font_color':GOLD,'x1':530,'y1':187,'x2':960,'y2':252,'align':'left'}
        message_params={'font_path':self.font_path_shippori_bold,'font_color':GOLD,'x1':107,'y1':38,'x2':894,'y2':170,'align':'center'}
        price_type_params={'font_path':self.font_path_shippori_bold, 'font_color':BLACK, 'x1':0, 'y1':320, 'x2':1000, 'y2':370, 'align':'center'}
        normal_price_group={
            'price': {'text':'','font_path':self.font_path_shippori_bold,'font_size':130,'font_color':BLACK,'x_origin':0,'x_end':self.width,'y_origin':360},
            'unit':  {'text':'円','font_path':self.font_path_shippori_bold,'font_size':70,'font_color':BLACK,'dy':65},
            'suffix':{'text':'のところ','font_path':self.font_path_shippori_bold,'font_size':50,'font_color':BLACK,'dy':95}
        }
        discount_group={
             'price': {'text':'','font_path':self.font_path_shippori_bold,'font_size':95,'font_color':self.WHITE,'x_origin':0,'x_end':self.width,'y_origin':530},
             'unit':  {'text':'','font_path':self.font_path_shippori_bold,'font_size':60,'font_color':self.WHITE,'dy':40},
             'suffix':{'text':'OFF','font_path':self.font_path_shippori_bold,'font_size':40,'font_color':self.WHITE,'dy':65}
        }
        sale_price_group={
            'price': {'text':'','font_path':self.font_path_shippori_bold,'font_size':200,'font_color':GOLD,'x_origin':0,'x_end':self.width,'y_origin':650},
            'unit':  {'text':'円','font_path':self.font_path_shippori_bold,'font_size':70,'font_color':GOLD,'dy':145},
            'suffix':{'text':'税込','font_path':self.font_path_shippori_bold,'font_size':30,'font_color':GOLD,'dy':115}
        }
        self._place_text(draw, {**start_datetime_params, 'text': self._format_datetime_jp(row_data.startDate)})
        self._place_text(draw, {**end_datetime_params, 'text': self._format_datetime_jp(row_data.endDate)})
        self._place_text(draw, {**message_params, 'text': row_data.saleText or ""})
        self._place_text(draw, {**price_type_params, 'text': row_data.priceType or ""})
        normal_price_group['price']['text'] = self._format_price(row_data.regularPrice)
        sale_price_group['price']['text'] = self._format_price(row_data.salePrice)
        discount_text_val = self._calculate_discount_display(row_data.regularPrice, row_data.salePrice, row_data.discountType)
        discount_number = discount_text_val.replace('%', '').replace('円', '')
        discount_unit_text = '%' if '%' in discount_text_val else '円' if '円' in discount_text_val else ''
        discount_group['price']['text'] = discount_number
        discount_group['unit']['text'] = discount_unit_text
        self._place_price_group(draw, normal_price_group['price'], normal_price_group['unit'], normal_price_group['suffix'])
        self._place_price_group(draw, discount_group['price'], discount_group['unit'], discount_group['suffix'])
        self._place_price_group(draw, sale_price_group['price'], sale_price_group['unit'], sale_price_group['suffix'])
    def draw_template_F_2(self, draw: ImageDraw.Draw, row_data: Tool03ProductRowInput):
        self.draw_template_F(draw, row_data)