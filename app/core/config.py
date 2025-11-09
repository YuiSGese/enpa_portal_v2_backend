# from dotenv import load_dotenv
# import os

# load_dotenv()  # đọc .env

# DB_USER = os.getenv("DB_USER")
# DB_PASS = os.getenv("DB_PASS")
# DB_HOST = os.getenv("DB_HOST")
# DB_PORT = os.getenv("DB_PORT")
# DB_NAME = os.getenv("DB_NAME")
# DB_ECHO = os.getenv("DB_ECHO", "false").lower() == "true"
# DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", 5))
# DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", 10))
# DB_POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", 3600))
# DB_ISOLATION_LEVEL = os.getenv("DB_ISOLATION_LEVEL", "READ COMMITTED")
# SECRET_KEY = os.getenv("SECRET_KEY", "change-me")
# TOKEN_PREFIX = os.getenv("TOKEN_PREFIX", "Bearer ")
# TOKEN_EXPIRATION_AFTER = int(os.getenv("TOKEN_EXPIRATION_AFTER", 60))
# ALGORITHM = os.getenv("ALGORITHM", "HS256")

# # --- THÊM BIẾN MỚI CHO ADMIN INIT ---
# ADMIN_INIT_PASSWORD = os.getenv("ADMIN_INIT_PASSWORD", "default_admin_pass")

from dotenv import load_dotenv
import os

load_dotenv()  # đọc .env

# --- Biến Môi trường Chung ---
APP_ENV = os.getenv("APP_ENV", "development")

# --- Cấu hình Database ---
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
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

# --- Cấu hình AWS (MỚI - Checklist 3.2) ---
# Endpoint "giả" (local) hoặc "thật" (production)
# Khi ở production, các biến này sẽ KHÔNG được set (None),
# và boto3 sẽ tự động dùng endpoint thật của AWS.
AWS_ENDPOINT_URL_SQS = os.getenv("AWS_ENDPOINT_URL_SQS")
AWS_ENDPOINT_URL_S3 = os.getenv("AWS_ENDPOINT_URL_S3")

# Tên tài nguyên AWS
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
SQS_QUEUE_NAME = os.getenv("SQS_QUEUE_NAME")


# --- Biến cho Seeding ---
ADMIN_INIT_PASSWORD = os.getenv("ADMIN_INIT_PASSWORD", "default_admin_pass")