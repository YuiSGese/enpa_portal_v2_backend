from datetime import datetime, timedelta
from jose import jwt
from app.core.config import TOKEN_EXPIRATION_AFTER, SECRET_KEY, ALGORITHM
from jose import jwt, JWTError
from fastapi import HTTPException, status, Request

def create_access_token(data: dict, user_name: str, role_name: str, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=TOKEN_EXPIRATION_AFTER))
    to_encode.update(
        {
            "exp": expire, 
            "user_name": user_name, 
            "role_name": role_name
        }
    )
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

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
    
def require_roles(*allowed_roles: str):
    def dependency(request: Request):
        user = getattr(request.state, "user", None)
        if not user or user.get("role_name") not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Permission denied") 
        return user
    return dependency