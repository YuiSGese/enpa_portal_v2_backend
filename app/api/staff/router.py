from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.domain.repositories.user_repository import UserRepository
from app.domain.repositories.role_repository import RoleRepository
from app.api.login.validate import LoginRequest, LoginResponse
from app.core.bcrypt import verify_password, get_password_hash
from app.core.security import create_access_token
from app.api.staff.validate import StaffCreateRequest, StaffCreateResponse
from app.core.security import require_roles
from app.domain.entities.RoleEntity import Role
from app.domain.response.custom_response import custom_error_response
from app.domain.entities.UserEntity import UserEntity
from app.core.security import get_user_login

router = APIRouter(prefix="/staff", tags=["staff"])

@router.post("/create_staff", response_model=StaffCreateResponse)
def create_staff(request: Request, form_data: StaffCreateRequest, db: Session = Depends(get_db), user=Depends(require_roles(Role.ADMIN))):

    try:
        repo = UserRepository(db)
        user_check_exist_username = repo.get_by_username(form_data.username)

        # check username 
        if(user_check_exist_username): 
            return custom_error_response(400, "Username exists!")
        
        user_check_exist_email = repo.get_by_email(form_data.email)

        # check mail 
        if(user_check_exist_email): 
            return custom_error_response(400, "Email exists!")
        
        usernameLogin = get_user_login(request)
        userLogin = repo.get_by_username(usernameLogin)

        user_role_id = 2 # default ROLE_USER
        if form_data.is_admin:
            user_role_id = 1 # ROLE_ADMIN

        new_user = UserEntity(
            form_data.username,
            get_password_hash(form_data.password),
            form_data.chatwork_id,
            form_data.email,     
            userLogin.company_id,
            user_role_id
        )

        new_user.password = get_password_hash(form_data.password)

        userCreated = repo.create_user(new_user)

        return {
            "detail": "create user " + userCreated.username + " success!",
            "user": userCreated
        }
    except Exception as e:
        print(e)
        return custom_error_response(400, "Something went wrong!!, try again")