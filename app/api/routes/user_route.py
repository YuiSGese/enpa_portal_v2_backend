from fastapi import APIRouter, Depends
from app.api.controllers.user_controller import create_user_controller, list_users_controller
from app.api.validators.user_validator import UserCreateRequest

router = APIRouter(prefix="/users", tags=["Users"])

@router.post("/", summary="Tạo người dùng mới")
def create_user(data: UserCreateRequest):
    return create_user_controller(data)

@router.get("/", summary="Danh sách người dùng")
def list_users():
    return list_users_controller()