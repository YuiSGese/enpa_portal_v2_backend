# -*- coding: utf-8 -*-
from fastapi import FastAPI
# Giả sử settings được import từ đây
# from app.core.config import settings
# --- Tạm thời comment out settings nếu chưa dùng ---

# Import các router
# from app.tool03.api import router as tool03_api_router # Router mới cho Tool 03
from app.test import router as test_router

# Import các router khác nếu có (ví dụ: tool04_router...)

# Tạm thời gán giá trị cứng nếu settings chưa sẵn sàng
APP_NAME = "Enpa Portal V2 API" # settings.APP_NAME
APP_ENV = "development" # settings.APP_ENV

app = FastAPI(title=APP_NAME) # Sử dụng biến tạm

# Include các router
# app.include_router(tool03_api_router.router)
app.include_router(test_router.router)
# app.include_router(tool04_api_router.router) # Nếu có router tool04

@app.get("/")
async def root():
    # Sử dụng biến tạm
    return {"message": f"{APP_NAME} backend is running 🚀"}

# Các middleware, exception handlers... của bạn có thể đặt ở đây

