import os # 👈 Thêm vào
from fastapi import Request
from jose import jwt, JWTError, ExpiredSignatureError
from datetime import datetime
from app.core.config import SECRET_KEY, ALGORITHM, TOKEN_PREFIX
from app.domain.response.custom_response import custom_error_response

# --- 💡 THAY ĐỔI CHÍNH ---
# 1. Đọc biến môi trường (giống hệt main.py)
APP_ENV = os.getenv("APP_ENV", "development")
API_PREFIX = "/api-be" if APP_ENV == "production" else ""

# 2. Xây dựng danh sách miễn trừ (động)
EXEMPT_PATHS = [
    f"{API_PREFIX}/auth/login", 
    f"{API_PREFIX}/registration/",
    f"{API_PREFIX}/tools/03",
    # Các đường dẫn này KHÔNG có prefix
    "/docs",
    "/redoc", 
    "/openapi.json",
]  
# --- Hết thay đổi ---

async def jwt_role_middleware(request: Request, call_next):
    
    # Logic .startswith() của bạn vẫn đúng
    if any(request.url.path.startswith(path) for path in EXEMPT_PATHS):
        return await call_next(request)
    
    auth_header = request.headers.get("Authorization")
    
    # (Phần còn lại của file giữ nguyên)
    if not auth_header or not auth_header.startswith("Bearer "):
        return custom_error_response(401, "Authorization header missing")
    # ...