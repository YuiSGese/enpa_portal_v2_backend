from fastapi import Request
from jose import jwt, JWTError, ExpiredSignatureError
from datetime import datetime
from app.core.config import SECRET_KEY, ALGORITHM, TOKEN_PREFIX
from app.domain.response.custom_response import custom_error_response

# SỬA LỖI: Chúng ta định nghĩa các đường dẫn gốc (không có /api)
# mà chúng ta muốn miễn trừ (exempt).
BASE_EXEMPT_PATHS = [
    "/",                 # Cho health check (đường dẫn gốc)
    "/docs",             # Cho health check (FastAPI docs)
    "/redoc",
    "/openapi.json",
    "/auth/login",       # Đường dẫn đăng nhập (từ code cũ)
    "/registration",     # Đường dẫn đăng ký (từ code cũ)
    "/tools/03"          # Đường dẫn tool03 (chuẩn hóa)
]

# Tự động tạo thêm các đường dẫn có tiền tố /api
# để hỗ trợ cả môi trường Local (không /api) và AWS (có /api)
AWS_EXEMPT_PATHS = [f"/api{path}" for path in BASE_EXEMPT_PATHS]

# Giữ lại các đường dẫn đặc biệt từ code cũ (nếu có)
SPECIAL_EXEMPT_PATHS = [
    "/api/tools/03" # Giữ lại từ code cũ của bạn
]

# Gộp tất cả các đường dẫn miễn trừ lại
EXEMPT_PATHS = set(BASE_EXEMPT_PATHS + AWS_EXEMPT_PATHS + SPECIAL_EXEMPT_PATHS)


async def jwt_role_middleware(request: Request, call_next):
    
    path_to_check = request.url.path
    
    # Chuẩn hóa: Xóa dấu / ở cuối (nếu có) để khớp chính xác
    if len(path_to_check) > 1 and path_to_check.endswith('/'):
        path_to_check = path_to_check[:-1]

    # SỬA LỖI: Kiểm tra xem đường dẫn có nằm trong TẬP HỢP miễn trừ không
    # (Cách này nhanh và chính xác hơn .startswith())
    if path_to_check in EXEMPT_PATHS:
        return await call_next(request)
    
    # Kiểm tra .startswith() cho các đường dẫn con (ví dụ: /api/login/token)
    for exempt_prefix in EXEMPT_PATHS:
        if path_to_check.startswith(exempt_prefix):
            return await call_next(request)

    # Nếu không được miễn trừ, kiểm tra token
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