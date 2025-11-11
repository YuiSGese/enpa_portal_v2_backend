from fastapi import FastAPI
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

# Import các router khác nếu có (ví dụ: tool04_router...)

APP_NAME = "Enpa Portal V2 API"
APP_ENV = "development"

app = FastAPI(title=APP_NAME)

# Thêm middleware
app.middleware("http")(jwt_role_middleware)

# Gọi setup CORS
setup_cors(app, env=APP_ENV)

# Đăng ký handler
app.add_exception_handler(RequestValidationError, ValidationHandler)

# Include các router
# app.include_router(tool03_api_router.router)
app.include_router(test_router.router)
app.include_router(login_router.router)
app.include_router(tool03_router.router)       
app.include_router(staff_router.router)       
app.include_router(registration_router.router)              

@app.get("/")
async def root():
    # Sử dụng biến tạm
    return {"message": f"{APP_NAME} backend is running 🚀"}

# Các middleware, exception handlers... của bạn có thể đặt ở đây