# -*- coding: utf-8 -*-
import uuid
from fastapi import BackgroundTasks, HTTPException
from typing import List, Optional, Dict
import os
import shutil
from app.core.logger import logger # Import logger

# Import schemas và service từ cùng thư mục (.)
from . import schemas
from . import service as tool03_service

# --- Hàm start_image_generation_job (Giữ nguyên) ---
def start_image_generation_job(
    product_rows: List[schemas.Tool03ProductRowInput],
    background_tasks: BackgroundTasks
) -> schemas.Tool03CreateJobResponse:
    if not product_rows:
        raise HTTPException(status_code=400, detail="Product list cannot be empty")

    job_id = str(uuid.uuid4())
    # Thêm job vào background tasks
    background_tasks.add_task(tool03_service.generate_images_background, job_id, product_rows)

    # Trả về job_id ngay lập tức
    return schemas.Tool03CreateJobResponse(jobId=job_id, totalItems=len(product_rows))

# --- Hàm get_job_status_controller (SỬA LẠI) ---
def get_job_status_controller(job_id: str) -> Optional[schemas.Tool03JobStatusResponse]:
    status_dict = tool03_service.get_job_status(job_id)
    if status_dict:
        # --- THÊM job_id VÀO DICTIONARY ---
        status_dict_with_id = {"jobId": job_id, **status_dict}
        # ------------------------------------
        try:
            # Chuyển đổi dict sang Pydantic model để validate và trả về
            return schemas.Tool03JobStatusResponse(**status_dict_with_id)
        except Exception as e:
            # Ghi log nếu có lỗi validate bất ngờ
            logger.error(f"Lỗi khi validate JobStatusResponse cho job {job_id}: {e}")
            logger.error(f"Dữ liệu gốc: {status_dict_with_id}")
            # Trả về lỗi 500 nếu cấu trúc dữ liệu không khớp model
            raise HTTPException(status_code=500, detail="Lỗi xử lý dữ liệu trạng thái job.")
    return None # Trả về None nếu service không tìm thấy job (router sẽ trả 404)


# --- Hàm get_image_file_path_controller (Giữ nguyên) ---
def get_image_file_path_controller(job_id: str, filename: str) -> Optional[str]:
     job_dir = tool03_service.JOB_STORAGE_BASE_DIR / job_id
     file_path = job_dir / filename
     if not str(file_path.resolve()).startswith(str(job_dir.resolve())):
          logger.warning(f"Attempted path traversal: {job_id}/{filename}")
          return None
     if file_path.is_file():
          return str(file_path)
     return None
# === Tác vụ nền MỚI để tạo lại ảnh ===
async def regenerate_specific_images_background(job_id: str, modified_rows: List[Tool03ProductRowInput]):
    """Tác vụ nền để tạo lại các ảnh cụ thể trong một job đã tồn tại."""
    logger.info(f"[Job {job_id}] Bắt đầu TẠO LẠI {len(modified_rows)} ảnh.")

    # Lấy trạng thái job hiện tại
    current_job_data = job_tracker.get(job_id)
    if not current_job_data:
        logger.error(f"[Job {job_id}] Không tìm thấy job để tạo lại ảnh.")
        return

    job_dir = JOB_STORAGE_BASE_DIR / job_id
    if not job_dir.is_dir():
         logger.error(f"[Job {job_id}] Thư mục job không tồn tại: {job_dir}")
         current_job_data["status"] = "Failed"
         current_job_data["message"] = "Thư mục lưu trữ ảnh bị mất."
         return

    # Cập nhật trạng thái job thành Processing (nếu cần)
    current_job_data["status"] = "Processing"
    current_job_data["message"] = None # Xóa lỗi cũ nếu có
    current_job_data["endTime"] = None # Reset thời gian kết thúc

    local_error_count = 0 # Đếm lỗi chỉ trong lần chạy này

    try:
        for row in modified_rows:
            row_id = row.id
            logger.debug(f"[Job {job_id}] Đang TẠO LẠI ảnh cho row ID: {row_id} ({row.productCode})")

            # Cập nhật trạng thái của ảnh này thành Processing
            if row_id in current_job_data["results"]:
                current_job_data["results"][row_id]["status"] = "Processing"
                current_job_data["results"][row_id]["message"] = None
            else:
                 # Nếu row ID này chưa từng tồn tại (khó xảy ra nếu frontend gửi đúng)
                 current_job_data["results"][row_id] = Tool03ImageResult(status="Processing").model_dump()

            # Logic tạo ảnh giống như hàm generate_images_background
            template_name = row.template or "テンプレートA"
            base_key = template_name.replace("テンプレート", "")
            factory_key = base_key
            has_mobile_data = bool(row.mobileStartDate and row.mobileEndDate)
            potential_mobile_key = f"{base_key}-2"
            if has_mobile_data and potential_mobile_key in factory_registry._factories:
                factory_key = potential_mobile_key

            current_result_update = {"status": "Processing"} # Dùng dict để cập nhật

            try:
                factory = factory_registry.get_factory(factory_key)
                img: Image.Image = factory.draw(row, factory_key)
                output_filename = f"{row.productCode}.jpg"
                output_path = job_dir / output_filename
                img.save(output_path, "JPEG", quality=95) # Ghi đè file cũ
                current_result_update["status"] = "Success"
                current_result_update["filename"] = output_filename
                current_result_update["message"] = None
                img.close()

            except (FileNotFoundError, ValueError, NotImplementedError) as e:
                logger.error(f"[Job {job_id}] Lỗi TẠO LẠI ảnh ({row.productCode}, template '{factory_key}'): {e}")
                current_result_update["status"] = "Error"
                current_result_update["message"] = str(e)
                local_error_count += 1
            except Exception as draw_error:
                logger.error(f"[Job {job_id}] Lỗi không xác định khi TẠO LẠI ảnh ({row.productCode}, template '{factory_key}'): {draw_error}", exc_info=True)
                current_result_update["status"] = "Error"
                current_result_update["message"] = "Lỗi không xác định khi vẽ ảnh."
                local_error_count += 1
            finally:
                 # Cập nhật kết quả cho ảnh này trong job_tracker
                 if job_id in job_tracker and row_id in job_tracker[job_id]["results"]:
                     job_tracker[job_id]["results"][row_id].update(current_result_update)

            await asyncio.sleep(0.01)

        # --- Xác định trạng thái cuối cùng sau khi tạo lại ---
        # Kiểm tra xem còn ảnh nào đang Processing không (có thể do lỗi từ trước hoặc job bị cancel)
        # Hoặc kiểm tra xem có ảnh nào bị Error không (bao gồm cả lỗi mới và lỗi cũ)
        final_status = "Completed"
        has_errors = False
        if job_id in job_tracker: # Kiểm tra job còn không
             for res in job_tracker[job_id]["results"].values():
                  if res.get("status") == "Error":
                       has_errors = True
                       break
             if has_errors:
                  final_status = "Completed with errors"
        else:
             final_status = "Failed" # Job đã bị xóa?

        logger.info(f"[Job {job_id}] Hoàn thành TẠO LẠI ảnh. Status mới: {final_status}. Lỗi trong lần chạy này: {local_error_count}/{len(modified_rows)}.")

    except Exception as e:
        final_status = "Failed" # Lỗi nghiêm trọng trong quá trình tạo lại
        logger.error(f"[Job {job_id}] Gặp lỗi nghiêm trọng khi TẠO LẠI ảnh: {e}", exc_info=True)
        if job_id in job_tracker:
            job_tracker[job_id]["message"] = f"Lỗi hệ thống khi tạo lại ảnh: {e}"
    finally:
        # Cập nhật trạng thái cuối cùng và thời gian kết thúc nếu job còn
        if job_id in job_tracker:
            end_time = time.time()
            job_tracker[job_id]["status"] = final_status
            job_tracker[job_id]["endTime"] = end_time

# ... (các hàm khác như create_job_zip_archive, cleanup_old_jobs, upload_job_images_to_ftp giữ nguyên)
# --- Hàm create_images_zip_controller (Giữ nguyên) ---
def create_images_zip_controller(job_id: str) -> Optional[str]:
    try:
        zip_path = tool03_service.create_job_zip_archive(job_id)
        return zip_path
    except FileNotFoundError:
         raise HTTPException(status_code=404, detail="Job directory not found.")
    except Exception as e:
         logger.error(f"Error creating zip for job {job_id}: {e}", exc_info=True)
         raise HTTPException(status_code=500, detail="Failed to create zip file.")

# --- Hàm start_ftp_upload_controller (Giữ nguyên) ---
def start_ftp_upload_controller(job_id: str, target: str, background_tasks: BackgroundTasks):
    job_status = tool03_service.get_job_status(job_id)
    if not job_status:
        raise HTTPException(status_code=404, detail="Job not found.")
    # if job_status.get("status") not in ["Completed", "Completed with errors"]:
    #     raise HTTPException(status_code=400, detail="Job is not completed yet.")

    logger.info(f"Adding FTP upload task for job {job_id} to {target} into background.")
    background_tasks.add_task(tool03_service.upload_job_images_to_ftp, job_id, target)

# controller.py
# ... (các import và hàm khác)

def start_image_regeneration_job(
    job_id: str,
    modified_rows: List[schemas.Tool03ProductRowInput],
    background_tasks: BackgroundTasks
):
    """Thêm tác vụ nền để tạo lại các ảnh đã chỉ định."""
    # Kiểm tra xem job có tồn tại không
    existing_job_status = tool03_service.get_job_status(job_id)
    if not existing_job_status:
        raise HTTPException(status_code=404, detail="Job not found")
    # Kiểm tra job có đang lỗi không (tùy chọn)
    # if existing_job_status.get("status") == "Failed":
    #     raise HTTPException(status_code=400, detail="Cannot update a failed job.")

    logger.info(f"Adding image regeneration task for job {job_id} with {len(modified_rows)} items.")
    background_tasks.add_task(tool03_service.regenerate_specific_images_background, job_id, modified_rows)