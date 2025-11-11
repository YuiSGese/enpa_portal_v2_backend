from dotenv import load_dotenv
import os

load_dotenv()

# --- Biến Môi trường Chung ---
APP_ENV = os.getenv("APP_ENV", "development")

# --- Cấu hình Database ---
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
PUBLIC_FRONTEND_DOMAIN=os.getenv("PUBLIC_FRONTEND_DOMAIN")
PUBLIC_BACKEND_DOMAIN=os.getenv("PUBLIC_BACKEND_DOMAIN")
DB_ECHO = os.getenv("DB_ECHO", "false").lower() == "true"
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", 5))
DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", 10))
DB_POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", 3600))
DB_ISOLATION_LEVEL = os.getenv("DB_ISOLATION_LEVEL", "READ COMMITTED")

# --- Cấu hình JWT Auth ---
SECRET_KEY = os.getenv("SECRET_KEY", "change-me")
TOKEN_PREFIX = os.getenv("TOKEN_PREFIX", "Bearer ")
TOKEN_EXPIRATION_AFTER = int(os.getenv("TOKEN_EXPIRATION_AFTER", 60))
ALGORITHM = os.getenv("ALGORITHM", "HS256")

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = os.getenv("SMTP_PORT")
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")


# --- Cấu hình AWS (MỚI - Checklist 3.2) ---
AWS_ENDPOINT_URL_SQS = os.getenv("AWS_ENDPOINT_URL_SQS")
AWS_ENDPOINT_URL_S3 = os.getenv("AWS_ENDPOINT_URL_S3")

# === SỬA LỖI: Thêm dòng đọc AWS_REGION ===
AWS_REGION = os.getenv("AWS_REGION", "us-east-1") # (Thêm default 'us-east-1')
# ======================================

# Tên tài nguyên AWS
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
SQS_QUEUE_NAME = os.getenv("SQS_QUEUE_NAME")


# --- Biến cho Seeding ---
ADMIN_INIT_PASSWORD = os.getenv("ADMIN_INIT_PASSWORD", "default_admin_pass")
