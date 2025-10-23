from fastapi import Depends
from sqlalchemy.orm import Session
from app.domain.repositories.user_repository import UserRepository
from app.domain.services.user_service import UserService
from app.core.database import get_db
from app.api.validators.user_validator import UserCreateRequest

def create_user_controller(data: UserCreateRequest, db: Session = Depends(get_db)):
    repo = UserRepository(db)
    service = UserService(repo)
    return service.create_user(data.name, data.email, data.password)

def list_users_controller(db: Session = Depends(get_db)):
    repo = UserRepository(db)
    service = UserService(repo)
    return service.list_users()