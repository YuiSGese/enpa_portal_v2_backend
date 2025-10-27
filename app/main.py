# -*- coding: utf-8 -*-
from fastapi import FastAPI
from app.core.logger import logger
# Giả sử settings được import từ đây
# from app.core.config import settings
# --- Tạm thời comment out settings nếu chưa dùng ---

# Import các router
from app.api.routes import user_route # Router user hiện có
from app.tool03 import router as tool03_router # Router mới cho Tool 03 (Đường dẫn đúng)
# Import các router khác nếu có (ví dụ: tool04_router...)

# Tạm thời gán giá trị cứng nếu settings chưa sẵn sàng
APP_NAME = "Enpa Portal V2 API" # settings.APP_NAME
APP_ENV = "development" # settings.APP_ENV

app = FastAPI(title=APP_NAME) # Sử dụng biến tạm

# Include các router
app.include_router(user_route.router)
app.include_router(tool03_router.router) # <<< SỬA LẠI TÊN Ở ĐÂY
# app.include_router(tool04_router.router) # Nếu có router tool04

@app.on_event("startup")
async def startup_event():
    # Sử dụng biến tạm
    logger.info(f"🚀 {APP_NAME} is starting in {APP_ENV} mode")

@app.get("/")
async def root():
    # Sử dụng biến tạm
    return {"message": f"{APP_NAME} backend is running 🚀"}

# Các middleware, exception handlers... của bạn có thể đặt ở đây

