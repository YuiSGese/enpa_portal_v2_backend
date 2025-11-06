# tool_35_coupon_image_creation/router.py
from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import FileResponse
from .schemas import CouponInput, CouponJobResponse, CouponJobStatusResponse
from .controller import start_coupon_image_generation_job, get_job_status_controller
from .service import job_tracker

import os

router = APIRouter(prefix="/tools/10", tags=["Coupon Image Creation"])


@router.post("/jobs", response_model=CouponJobResponse)
# async def start_job(coupons: list[CouponInput], background_tasks: BackgroundTasks):
async def start_job(data: CouponInput, background_tasks: BackgroundTasks):
    """Nhận danh sách coupon (JSON) và khởi động job nền."""
    # return start_coupon_image_generation_job(coupons, background_tasks)
    return start_coupon_image_generation_job(data.productRows, background_tasks)


@router.get("/jobs/{job_id}", response_model=CouponJobStatusResponse)
async def get_status(job_id: str):
    """Truy vấn trạng thái job."""
    return get_job_status_controller(job_id)


@router.get("/jobs/{job_id}/download")
async def download_result(job_id: str):
    """Tải file ZIP kết quả sau khi job hoàn thành."""
    job = job_tracker.get(job_id)
    if not job or job["status"] != "completed":
        return {"error": "Job not completed or not found"}
    zip_path = job["result_files"][0]
    return FileResponse(zip_path, filename=os.path.basename(zip_path))
