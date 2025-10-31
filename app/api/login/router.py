from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.domain.repositories.user_repository import UserRepository
from app.domain.repositories.role_repository import RoleRepository
from app.api.login.validate import LoginRequest, LoginResponse
from app.core.bcrypt import verify_password
from app.core.security import create_access_token
from app.core.config import TOKEN_PREFIX

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/login", response_model=LoginResponse)
def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    repo = UserRepository(db)
    user = repo.get_by_username(login_data.username)
    
    if not user or not verify_password(login_data.password, user.password):
        raise HTTPException(status_code=400, detail="Invalid credentials")
    
    roleRepo = RoleRepository(db)
    role = roleRepo.get_by_id(user.role_id)

    token = create_access_token({"sub": str(user.id)}, user.username, role.role_name)
    
    return {
        "access_token": TOKEN_PREFIX + token,
        "user": user
    }