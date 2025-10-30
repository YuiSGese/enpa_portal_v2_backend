from fastapi import APIRouter, Depends, status, HTTPException
from app.tool07.shemas import SettingsBase, SettingsRead
from app.tool07.service import Tool07Service, get_tool07_service
from typing import Dict, Any

router = APIRouter(
    prefix="/tool07",
    tags=["Tool07: Review Image"],
    responses={404: {"description": "Not found"}},
)

@router.get("/settings", response_model=SettingsRead)
def get_tool_settings(service: Tool07Service = Depends(get_tool07_service)):
    """Lấy cấu hình hiện tại của công cụ Review Image."""
    try:
        settings = service.get_settings()
        return settings
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi tải cấu hình: {e}")

@router.post("/settings", status_code=status.HTTP_204_NO_CONTENT)
def save_tool_settings(settings: SettingsBase, service: Tool07Service = Depends(get_tool07_service)):
    """Lưu cấu hình mới của công cụ Review Image."""
    try:
        service.save_settings(settings)
        return {"message": "Cấu hình đã được lưu thành công."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi lưu cấu hình: {e}")

@router.post("/run-manual", status_code=status.HTTP_200_OK)
def run_tool_manually(service: Tool07Service = Depends(get_tool07_service)):
    """Chạy công cụ Review Image thủ công (Chỉ dành cho testing hoặc admin)."""
    try:
        service.run_full_process()
        return {"message": "Tác vụ chạy thủ công đã hoàn tất. Vui lòng kiểm tra logs."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi chạy tác vụ thủ công: {e}")
