import sys
import os
import time
import logging
import json
from typing import Dict, Any, Callable

# === SỬA LỖI IMPORT (Dòng 6-8) ===
# Thêm thư mục gốc (project root) vào sys.path
# để Python tìm thấy 'app'
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.append(PROJECT_ROOT)
# =================================

from app.core import sqs_client
from app.core.database import SessionLocal, engine # (Import để kiểm tra kết nối)
from sqlalchemy import text 

# === IMPORT HANDLERS ===
# Chúng ta import handler cho TẤT CẢ các tool ở đây
from app.tool03 import service as tool03_service
# (Khi có tool04, bạn sẽ import: from app.workers import tool04_handler)
# ========================

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# === BẢNG ĐIỀU PHỐI (HANDLER REGISTRY) ===
# Bảng này "map" (ánh xạ) `job_type` (từ SQS)
# với hàm Python (handler) sẽ xử lý nó.

# (Một handler PHẢI nhận 1 param: job_data (dict)
#  Và PHẢI trả về 1 bool: True (Xóa SQS) hoặc False (Giữ SQS - để retry))
HANDLER_MAP: Dict[str, Callable[[Dict[str, Any]], bool]] = {
    
    # Job Tạo ảnh Tool 03
    "tool03": tool03_service.process_tool03_job, 
    
    # Job Upload FTP Tool 03 (MỚI)
    
    "tool03_ftp": tool03_service.process_tool03_ftp_job,
    
    # (Khi có tool04, bạn sẽ thêm:)
    # "tool04": tool04_handler.process_tool04_job, 
}
# ==========================================


def check_db_connection():
    """Kiểm tra kết nối CSDL khi worker khởi động."""
    try:
        db = SessionLocal()
        # === SỬA LỖI 2: Xóa 'engine.' ===
        db.execute(text("SELECT 1")) 
        db.close()
        logger.info("✅ Kết nối CSDL (MariaDB) thành công.")
        return True
    except Exception as e:
        logger.critical(f"❌ LỖI NGHIÊM TRỌNG: Không thể kết nối CSDL (MariaDB) khi khởi động.")
        logger.critical(e)
        return False

def main_loop():
    """Vòng lặp chính của Worker."""
    
    logger.info("--- Worker Bắt đầu ---")
    
    # Đăng ký handlers
    registered_handlers = list(HANDLER_MAP.keys())
    logger.info(f"Đã đăng ký handlers cho: {registered_handlers}")
    
    # Kiểm tra CSDL
    if not check_db_connection():
         logger.error("Hủy worker do lỗi kết nối CSDL.")
         return

    while True:
        try:
            logger.info("Đang chờ job từ SQS (long polling 5s)...")
            
            # 1. Nhận message (long polling)
            message = sqs_client.receive_sqs_message()
            
            if not message:
                # (Không có message, tiếp tục vòng lặp)
                continue

            # 2. Parse message
            receipt_handle = message['ReceiptHandle']
            try:
                 message_body = json.loads(message['Body'])
                 job_type = message_body.get('job_type')
                 job_data = message_body.get('data', {})
                 job_id = job_data.get('job_id', 'N/A')
                 
            except json.JSONDecodeError:
                 logger.error(f"Lỗi: Không thể parse SQS message body: {message['Body']}")
                 # Lỗi không thể retry -> Xóa message
                 sqs_client.delete_sqs_message(receipt_handle)
                 continue
            except Exception as e:
                 logger.error(f"Lỗi lạ khi parse SQS message: {e}", exc_info=True)
                 sqs_client.delete_sqs_message(receipt_handle)
                 continue

            logger.info(f"Đã nhận job! Job ID: {job_id}, Job Type: {job_type}")

            # 3. Điều phối (Dispatch)
            handler_function = HANDLER_MAP.get(job_type)
            
            if not handler_function:
                logger.error(f"Lỗi: Không tìm thấy handler nào cho job_type: '{job_type}'. Xóa SQS.")
                sqs_client.delete_sqs_message(receipt_handle)
                continue

            # 4. Thực thi (Execute)
            try:
                logger.info(f"Đang giao job '{job_type}' (ID: {job_id}) cho handler...")
                
                # Đây là nơi xử lý logic nặng (Tạo ảnh, FTP...)
                # handler_function PHẢI trả về True (Thành công/Lỗi nghiệp vụ -> Xóa SQS)
                # hoặc False (Lỗi hệ thống -> Giữ SQS)
                
                start_time = time.time()
                should_delete = handler_function(job_data)
                end_time = time.time()
                
                logger.info(f"Handler '{job_type}' (ID: {job_id}) thực thi xong. (Mất {end_time - start_time:.2f}s). Kết quả: {'XÓA SQS' if should_delete else 'GIỮ SQS (Retry)'}")

                # 5. Xóa SQS (Nếu handler báo thành công)
                if should_delete:
                    sqs_client.delete_sqs_message(receipt_handle)
                else:
                    logger.warning(f"Handler (ID: {job_id}) trả về False. SQS message sẽ KHÔNG bị xóa và sẽ được retry.")
                    
            except Exception as e:
                # (Lỗi này không nên xảy ra, vì handler đã có try/except)
                logger.critical(f"LỖI HỆ THỐNG: Handler '{job_type}' (ID: {job_id}) crash (ném Exception): {e}", exc_info=True)
                # Vì handler crash, chúng ta không xóa SQS để retry
                logger.error("SQS message sẽ KHÔNG bị xóa và sẽ được retry.")

        except Exception as e:
            # (Lỗi ở vòng lặp chính, ví dụ: SQS client sập)
            logger.critical(f"LỖI VÒNG LẶP CHÍNH CỦA WORKER: {e}", exc_info=True)
            # Chờ 5 giây trước khi thử lại
            time.sleep(5)


if __name__ == "__main__":
    try:
        main_loop()
    except KeyboardInterrupt:
        logger.info("--- Worker Đã Tắt (Ctrl+C) ---")
        sys.exit(0)