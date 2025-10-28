from fastapi import FastAPI
from app.core.validation_handler import ValidationHandler
from fastapi.exceptions import RequestValidationError
from app.core.middleware import jwt_role_middleware

# Import các router
# from app.tool03.api import router as tool03_api_router # Router mới cho Tool 03
from app.test import router as test_router
from app.api.login import router as login_router


# Import các router khác nếu có (ví dụ: tool04_router...)

APP_NAME = "Enpa Portal V2 API"
APP_ENV = "development"

app = FastAPI(title=APP_NAME) # Sử dụng biến tạm

# Đăng ký handler
app.add_exception_handler(RequestValidationError, ValidationHandler)

# Include các router
# app.include_router(tool03_api_router.router)
app.include_router(test_router.router)
app.include_router(login_router.router)
                   
# Thêm middleware
app.middleware("http")(jwt_role_middleware)

@app.get("/")
async def root():
    # Sử dụng biến tạm
    return {"message": f"{APP_NAME} backend is running 🚀"}

# Các middleware, exception handlers... của bạn có thể đặt ở đây

