    # -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, BackgroundTasks
    # SỬA ĐƯỜNG DẪN IMPORT: Import từ cùng thư mục (.)
from .schemas import Tool03CreateJobRequest, Tool03CreateJobResponse
from . import controller as tool03_controller

router = APIRouter(
        prefix="/tools/03",
        tags=["Tool 03 - 二重価格画像作成"]
    )

@router.post("/jobs", response_model=Tool03CreateJobResponse, status_code=202)
async def create_tool03_job(
        request_data: Tool03CreateJobRequest,
        background_tasks: BackgroundTasks
    ):
        response = await tool03_controller.start_image_generation_job(request_data, background_tasks)
        return response
    
