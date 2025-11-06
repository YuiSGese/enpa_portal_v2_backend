# tool_35_coupon_image_creation/service.py
import os
import uuid
import zipfile
import traceback
from datetime import datetime
from typing import List
from fastapi import BackgroundTasks

from .schemas import CouponInput
from .factory.registry import factory_registry

from PIL import Image, ImageDraw
from .factory.base_factory import Factory


# Lưu trạng thái job trong bộ nhớ (có thể thay bằng Redis sau này)
job_tracker = {}


def generate_coupon_images_background(jobId: str, coupons: List[CouponInput], output_dir: str):
    """Background job tạo ảnh coupon."""
    total = len(coupons)
    completed = 0
    failed = 0

    job_tracker[jobId]["status"] = "running"

    try:
        os.makedirs(output_dir, exist_ok=True)
        img_dir = os.path.join(output_dir, "img")
        os.makedirs(img_dir, exist_ok=True)

        for i, coupon in enumerate(coupons, start=1):
            try:
                factory_class = factory_registry.get_factory(coupon.template)
                factory = factory_class()

                factory.draw_from_json(
                    data=coupon,
                    save_path=os.path.join(img_dir, f"coupon_{coupon.file_name}.jpg")
                )
                completed += 1
            except Exception as e:
                failed += 1
                print(f"[ERROR] {coupon.file_name}: {e}")
            
            # cập nhật tiến độ
            job_tracker[jobId]["completed"] = completed
            job_tracker[jobId]["failed"] = failed
            job_tracker[jobId]["progress"] = completed / total

        # tạo file ZIP kết quả
        zip_path = os.path.join(output_dir, f"coupon_result_{jobId}.zip")
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for img_file in os.listdir(img_dir):
                zipf.write(os.path.join(img_dir, img_file), arcname=img_file)

        job_tracker[jobId]["status"] = "completed"
        job_tracker[jobId]["result_files"] = [zip_path]
    except Exception as e:
        job_tracker[jobId]["status"] = "failed"
        job_tracker[jobId]["message"] = traceback.format_exc()
        print(traceback.format_exc())


def start_coupon_job(coupons: List[CouponInput], background_tasks: BackgroundTasks):
    """Tạo job ID và khởi động tác vụ nền."""
    jobId = str(uuid.uuid4())
    output_dir = os.path.join(os.getcwd(), "output", jobId)

    job_tracker[jobId] = {
        "jobId": jobId,
        "status": "pending",
        "total": len(coupons),
        "completed": 0,
        "failed": 0,
        "progress": 0.0,
        "created_at": datetime.now(),
        "result_files": []
    }

    background_tasks.add_task(generate_coupon_images_background, jobId, coupons, output_dir)
    return job_tracker[jobId]


def get_job_status(jobId: str):
    """Trả trạng thái hiện tại của job."""
    return job_tracker.get(jobId)
