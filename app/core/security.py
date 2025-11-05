from datetime import datetime, timedelta
from jose import jwt
from app.core.config import TOKEN_EXPIRATION_AFTER, SECRET_KEY, ALGORITHM, TOKEN_PREFIX
from jose import jwt, JWTError
from fastapi import HTTPException, status, Request
from app.domain.entities.RoleEntity import Role
from typing import Callable

def create_access_token(data: dict, user_name: str, role_name: str, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=int(TOKEN_EXPIRATION_AFTER)))
    
    to_encode.update(
        {
            "exp": expire, 
            "user_name": user_name, 
            "role_name": role_name
        }
    )
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_token_from_header(request: Request) -> str | None:
    """
    Lấy JWT token từ header Authorization (nếu có).
    Ví dụ:
        Authorization: Bearer <token>
    Kết quả trả về: <token> hoặc None nếu không hợp lệ.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return None

    if auth_header.startswith(TOKEN_PREFIX):
        return auth_header[len(TOKEN_PREFIX):].strip()

    # Không có tiền tố TOKEN_PREFIX
    return None

def get_token_property(token: str, property_name: str):
    """
    Giải mã JWT token và lấy giá trị của property_name.
    Nếu property không tồn tại -> trả về None.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get(property_name, None)

    except JWTError:
        return None
    
def get_user_login(request: Request) -> str | None:

    token = get_token_from_header(request)
    username = get_token_property(token, "user_name")
    return username

    
def require_roles(*allowed_roles: str | Role) -> Callable:
    def dependency(request: Request):
        user = getattr(request.state, "user", None)
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

        user_role = user.get("role_name")

        allowed_role_values = [
            role.value if hasattr(role, "value") else role for role in allowed_roles
        ]

        if user_role == Role.ADMIN.value:
            return user

        if user_role not in allowed_role_values:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied"
            )

        return user
    return dependency