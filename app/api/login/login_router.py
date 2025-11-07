from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.domain.repositories.user_repository import UserRepository
from app.domain.repositories.role_repository import RoleRepository
from app.api.login.login_schemas import LoginRequest, LoginResponse
from app.core.bcrypt import verify_password
from app.core.security import create_access_token
from app.core.config import TOKEN_PREFIX
from app.api.login.login_repository import login_repository


router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/login", response_model=LoginResponse)
def login(login_data: LoginRequest, db: Session = Depends(get_db)):

    repo = login_repository(db)

    user = repo.get_by_username(login_data.username)
    
    if not user or not verify_password(login_data.password, user.password):
        raise HTTPException(status_code=400, detail="アカウントまたはパスワードが正しくありません。")
    
    token = create_access_token({"sub": str(user.id)}, user.username, user.role_name)
    
    return {
        "access_token": TOKEN_PREFIX + token,
        "user": user
    }
