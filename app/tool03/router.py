# -*- coding: utf-8 -*-
# Sửa dòng import này: thêm , Path
from fastapi import APIRouter, BackgroundTasks, HTTPException, Path, Body
from fastapi.responses import FileResponse
import os
import shutil
from typing import List, Dict

# Import schemas và controller từ cùng thư mục (.)
from . import schemas
from . import controller
from . import service as tool03_service # Import service để check job status

router = APIRouter(
    prefix="/tools/03",
    tags=["Tool 03 - 二重価格画像作成"],
)

# --- Endpoint /jobs (POST) ---
@router.post(
    "/jobs",
    response_model=schemas.Tool03CreateJobResponse,
    status_code=202 # Accepted
)
async def create_image_generation_job(
    request: schemas.Tool03CreateJobRequest,
    background_tasks: BackgroundTasks
):
    """Bắt đầu một job tạo ảnh nền."""
    return controller.start_image_generation_job(request.productRows, background_tasks)
# --- Endpoint /jobs/{job_id} (PATCH) ---
@router.patch(
    "/jobs/{job_id}",
    status_code=202 # Accepted
    # Không cần response_model vì chỉ nhận lệnh
)
async def update_image_generation_job(
    request: schemas.Tool03CreateJobRequest, # Tái sử dụng schema cũ
    background_tasks: BackgroundTasks,
    job_id: str = Path(..., description="ID của Job cần cập nhật", min_length=36, max_length=36)
):
    """Bắt đầu tác vụ nền để tạo lại các ảnh đã chỉ định trong job."""
    if not request.productRows:
         # Có thể trả về 200 OK hoặc 202 Accepted vì không có gì để làm
         return {"message": "No rows provided for update."} 

    # Gọi controller để bắt đầu tác vụ cập nhật nền
    controller.start_image_regeneration_job(job_id, request.productRows, background_tasks)
    return {"message": f"Image regeneration task for job {job_id} started."}

# --- Endpoint /jobs/{job_id}/status (GET) ---
@router.get(
    "/jobs/{job_id}/status",
    response_model=schemas.Tool03JobStatusResponse
)
async def get_job_status(
    # Sử dụng Path đã import
    job_id: str = Path(..., description="ID của Job cần kiểm tra", min_length=36, max_length=36) # Thêm ràng buộc độ dài UUID
):
    """Kiểm tra trạng thái của một job tạo ảnh."""
    status_data = controller.get_job_status_controller(job_id)
    if status_data is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return status_data

# --- Endpoint /jobs/{job_id}/image/{filename} (GET) ---
@router.get(
    "/jobs/{job_id}/image/{filename}",
    response_class=FileResponse
)
async def get_image_file(
    # Sử dụng Path đã import
    job_id: str = Path(..., description="ID của Job", min_length=36, max_length=36),
    filename: str = Path(..., description="Tên file ảnh cần lấy")
):
    """Lấy file ảnh đã được tạo bởi job."""
    file_path = controller.get_image_file_path_controller(job_id, filename)
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Image not found")
    # Kiểm tra filename có hợp lệ không (tránh lỗi bảo mật)
    if ".." in filename or filename.startswith("/"):
        raise HTTPException(status_code=400, detail="Invalid filename")

    return FileResponse(file_path, media_type="image/jpeg", filename=filename)


# --- Endpoint /jobs/{job_id}/download (GET) ---
@router.get(
    "/jobs/{job_id}/download",
    response_class=FileResponse
)
async def download_images_zip(
    # Sử dụng Path đã import
    job_id: str = Path(..., description="ID của Job cần tải về", min_length=36, max_length=36)
):
    """Tạo và tải về file zip chứa tất cả ảnh của job."""
    zip_path = controller.create_images_zip_controller(job_id)
    if not zip_path or not os.path.exists(zip_path):
        raise HTTPException(status_code=404, detail="Job not found or failed to create zip")
    # Tạo tên file zip trả về cho người dùng
    download_filename = "img.zip"

    # Sử dụng FileResponse để gửi file zip
    # background=BackgroundTask(os.remove, zip_path) # Tự động xóa file zip sau khi gửi (tùy chọn)
    return FileResponse(
        path=zip_path,
        filename=download_filename,
        media_type='application/zip',
        # background=BackgroundTask(os.remove, zip_path) # Bật nếu muốn tự xóa
    )

# --- Endpoint /jobs/{job_id}/upload (POST) ---
@router.post(
    "/jobs/{job_id}/upload",
    status_code=202 # Accepted
)
async def upload_images_to_ftp(
    # Sử dụng Path đã import
    job_id: str = Path(..., description="ID của Job cần upload", min_length=36, max_length=36),
    payload: Dict[str, str] = Body(..., example={"target": "gold"}),
    background_tasks: BackgroundTasks = BackgroundTasks() # Đổi tên biến để tránh trùng
):
    """Bắt đầu tác vụ upload ảnh lên FTP (GOLD hoặc R-Cabinet) trong nền."""
    target = payload.get("target")
    if target not in ["gold", "rcabinet"]:
        raise HTTPException(status_code=400, detail="Invalid target specified. Use 'gold' or 'rcabinet'.")

    # Gọi controller để bắt đầu upload nền
    controller.start_ftp_upload_controller(job_id, target, background_tasks)

    # Trả về 202 ngay lập tức
    return {"message": f"FTP upload task to {target} for job {job_id} started in background."}

