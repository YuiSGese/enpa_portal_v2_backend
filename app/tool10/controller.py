# tool_35_coupon_image_creation/controller.py
from fastapi import BackgroundTasks, HTTPException
from .schemas import CouponInput, CouponJobResponse, CouponJobStatusResponse
from . import service


def start_coupon_image_generation_job(coupons: list[CouponInput], background_tasks: BackgroundTasks):
    job = service.start_coupon_job(coupons, background_tasks)
    return CouponJobResponse(
        jobId=job["jobId"],
        status=job["status"],
        total=job["total"],
        created_at=job["created_at"]
    )


def get_job_status_controller(jobId: str):
    job = service.get_job_status(jobId)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return CouponJobStatusResponse(**job)
