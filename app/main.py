from fastapi import FastAPI
from app.core.logger import logger
from app.core.config import settings
from app.api.routes import user_route

app = FastAPI(title=settings.APP_NAME)
app.include_router(user_route.router)

@app.on_event("startup")
async def startup_event():
    logger.info(f"🚀 {settings.APP_NAME} is starting in {settings.APP_ENV} mode")

@app.get("/")
async def root():
    return {"message": f"{settings.APP_NAME} backend is running 🚀"}