    # -*- coding: utf-8 -*-
import uuid
from fastapi import BackgroundTasks, HTTPException
    # SỬA ĐƯỜNG DẪN IMPORT: Import từ cùng thư mục (.)
from .schemas import Tool03CreateJobRequest, Tool03CreateJobResponse
from . import service as tool03_service # Import service từ cùng thư mục

async def start_image_generation_job(
        request_data: Tool03CreateJobRequest,
        background_tasks: BackgroundTasks
    ) -> Tool03CreateJobResponse:
        if not request_data.rows:
            raise HTTPException(status_code=400, detail="商品リストが空です。")

        job_id = str(uuid.uuid4())
        total_items = len(request_data.rows)

        background_tasks.add_task(
            tool03_service.generate_images_background,
            job_id=job_id,
            product_rows=request_data.rows
        )

        return Tool03CreateJobResponse(jobId=job_id, totalItems=total_items)
    
