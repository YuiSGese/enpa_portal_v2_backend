from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.domain.repositories.user_repository import UserRepository
from app.core.bcrypt import get_password_hash
from app.api.staff.staff_schemas import StaffCreateRequest, StaffCreateResponse, StaffListResponse, StaffDeleteResponse
from app.core.security import require_roles
from app.domain.entities.RoleEntity import Role
from app.domain.response.custom_response import custom_error_response
from app.domain.entities.UserEntity import UserEntity
from app.core.security import get_user_login
from app.api.staff.staff_repository import staff_repository

router = APIRouter(prefix="/staff", tags=["staff"])

@router.post("/create", response_model=StaffCreateResponse)
def create_staff(request: Request, form_data: StaffCreateRequest, db: Session = Depends(get_db), user=Depends(require_roles(Role.ADMIN))):

    try:
        repo = staff_repository(db)
        user_check_exist_username = repo.get_by_username(form_data.username)

        # check username 
        if(user_check_exist_username): 
            return custom_error_response(400, "ユーザー名が存在しました。")
        
        user_check_exist_email = repo.get_by_email(form_data.email)

        # check mail 
        if(user_check_exist_email): 
            return custom_error_response(400, "メールアドレスが存在しました。")
        
        usernameLogin = get_user_login(request)
        userLogin = repo.get_by_username(usernameLogin)

        user_role_id = 2 # default ROLE_USER
        if form_data.is_admin:
            user_role_id = 1 # ROLE_ADMIN

        new_user = UserEntity(
            form_data.username,
            get_password_hash(form_data.password),
            form_data.email,     
            userLogin.company_id,
            user_role_id
        )

        userCreated = repo.create_user(new_user)

        return {
            "detail": "ユーザー" + userCreated.username + "作成された",
            "user": userCreated
        }
    except Exception as e:
        print(e)
        return custom_error_response(400, "問題が発生しました!! もう一度お試しください")
    

@router.get("/list", response_model=StaffListResponse)
def staff_list(company_id: int, db: Session = Depends(get_db), user=Depends(require_roles(Role.ADMIN))):
    try:
        repo = staff_repository(db)
        users  = repo.get_list_user_by_company_id(company_id)
        return {
            "count": len(users),
            "list": users
        }
    except Exception as e:
        return custom_error_response(400, "問題が発生しました!! もう一度お試しください")

@router.delete("/delete", response_model=StaffDeleteResponse)
def staff_delete(username: str, db: Session = Depends(get_db), user=Depends(require_roles(Role.ADMIN))):
    try:
        repo = staff_repository(db)
        user  = repo.delete_user_by_username(username)
        if user != None:        
            return {
                "detail": "ユーザー" + user.username + "削除された",
                "user": user
            }
        
        return {
            "detail": "ユーザーが存在しません。",
            "user": None
        }
    except Exception as e:
        return custom_error_response(400, "問題が発生しました!! もう一度お試しください")
