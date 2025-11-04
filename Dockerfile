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
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        libmariadb-dev \
        mariadb-client \
        curl && \
    rm -rf /var/lib/apt/lists/*

# Thư mục làm việc trong container
WORKDIR /app

# Copy file dependency trước để cache
COPY requirements.txt .

# Cài thư viện Python (production)
RUN pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ mã nguồn backend
COPY . .

# Mở port backend
EXPOSE 8000

# Lệnh chạy chính thức cho FastAPI backend
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]