import os # 👈 Thêm vào
from fastapi import FastAPI, APIRouter
from app.core.validation_handler import ValidationHandler
from fastapi.exceptions import RequestValidationError
from app.core.middleware import jwt_role_middleware
from app.core.cors import setup_cors

# Import các router
from app.tool03 import router as tool03_router
from app.test import router as test_router
from app.api.login import login_router as login_router
from app.api.staff import staff_router as staff_router
from app.api.registration import registration_router

# --- 💡 THAY ĐỔI CHÍNH ---
# 1. Đọc biến môi trường. Nếu không có, mặc định là "development"
APP_ENV = os.getenv("APP_ENV", "development")

# 2. Quyết định prefix dựa trên môi trường
# Nếu là "production" (AWS), dùng /api-be. Nếu là "development" (local), dùng "" (rỗng).
API_PREFIX = "/api-be" if APP_ENV == "production" else ""
# --- Hết thay đổi ---

APP_NAME = "Enpa Portal V2 API"
# APP_ENV = "development" # 👈 Xóa (hoặc comment) dòng hardcode này

app = FastAPI(title=APP_NAME)

app.middleware("http")(jwt_role_middleware)
setup_cors(app, env=APP_ENV) # 👈 Dùng biến APP_ENV động
app.add_exception_handler(RequestValidationError, ValidationHandler)

# 3. Khởi tạo router "master" với prefix (động)
api_router = APIRouter(prefix=API_PREFIX) # 👈 Dùng biến API_PREFIX

# 4. Include tất cả các router con
api_router.include_router(test_router.router)
api_router.include_router(login_router.router) # Sẽ là /auth/login (local) hoặc /api-be/auth/login (AWS)
api_router.include_router(tool03_router.router)       
api_router.include_router(staff_router.router)       
api_router.include_router(registration_router.router)              

# 5. Include router "master" vào app
app.include_router(api_router)

@app.get("/")
async def root():
    return {"message": f"{APP_NAME} backend is running 🚀"}