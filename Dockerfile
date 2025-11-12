# ===============================
# 🐍 EmpaPortal V2 Backend - FastAPI
# Production Dockerfile
# ===============================

# --- Stage 1: Base image ---
FROM python:3.14-slim AS base

# Không ghi bytecode, xuất log tức thời
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Cài đặt các package cần thiết cho build và mariadb connector
# Đã thêm:
# 1. build-essential: Cần để biên dịch các package Python yêu cầu mã C (như mariadb).
# 2. libmariadb-dev: Cung cấp mariadb_config và các thư viện cần thiết để build Python package.
# 3. mariadb-client: Có thể hữu ích cho việc debug hoặc chạy migration thủ công, giữ lại theo file gốc của bạn.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        libmariadb-dev \
        mariadb-client \
        curl && \
    rm -rf /var/lib/apt/lists/*

# Thư mục làm việc trong container
WORKDIR /app

# Copy file dependency trước để tận dụng cache
COPY requirements.txt .

# Cài thư viện Python (production)
# Bước này sẽ thành công vì các dependency hệ thống đã có.
RUN pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ mã nguồn backend
COPY . .

# Mở port backend (cho API service)
EXPOSE 8000

# Lệnh CMD cuối cùng có thể trông như sau nếu bạn chạy uvicorn trực tiếp
# CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# Lệnh CMD sẽ được định nghĩa trong ECS Task Definition (Giai đoạn 3) - Giữ nguyên ghi chú này nếu bạn dùng ECS.