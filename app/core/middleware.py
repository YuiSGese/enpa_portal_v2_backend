from fastapi import Request
from jose import jwt, JWTError, ExpiredSignatureError
from datetime import datetime
from app.core.config import SECRET_KEY, ALGORITHM, TOKEN_PREFIX
from app.domain.response.custom_response import custom_error_response

# các route không cần check
EXEMPT_PATHS = [
    "/auth/login", 
    "/auth/register",
    "/docs",
    "/redoc", 
    "/openapi.json",
    "/tools/03",
    "/tools/10/"
]  

async def jwt_role_middleware(request: Request, call_next):
    # nếu path bắt đầu bằng bất kỳ prefix nào trong EXEMPT_PREFIXES → bỏ qua
    if any(request.url.path.startswith(path) for path in EXEMPT_PATHS):
        return await call_next(request)
    
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return custom_error_response(401, "Authorization header missing")

    token = auth_header[len(TOKEN_PREFIX):].strip()
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # lưu payload vào request.state để dùng trong route
        request.state.user = {
            "user_name": payload.get("user_name"),
            "role_name": payload.get("role_name")
        }
    except ExpiredSignatureError:
        return custom_error_response(401, "Token expired")
    except JWTError:
        return custom_error_response(401, "Invalid token")
    
    
    return await call_next(request)
