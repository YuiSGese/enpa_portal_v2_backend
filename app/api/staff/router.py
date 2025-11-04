from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.domain.repositories.user_repository import UserRepository
from app.domain.repositories.role_repository import RoleRepository
from app.api.login.validate import LoginRequest, LoginResponse
from app.core.bcrypt import verify_password
from app.core.security import create_access_token
from app.api.login.validate import StaffCreateRequest, StaffCreateResponse

router = APIRouter(prefix="/staff", tags=["staff"])

@router.post("/login", response_model=StaffCreateResponse)
def login(form_data: StaffCreateRequest, db: Session = Depends(get_db)):


    return {
        
    }