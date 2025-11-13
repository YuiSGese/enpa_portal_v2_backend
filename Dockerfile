# ===============================
# 🐍 EmpaPortal V2 Backend - FastAPI
# Production Dockerfile
# ===============================

# --- Stage 1: Base image ---
FROM python:3.14-slim AS base

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

# Copy file dependency trước để tận dụng cache
COPY requirements.txt .

# === BƯỚC KHẮC PHỤC LỖI MARIADB_CONFIG ===
# Thiết lập biến môi trường để chỉ định vị trí của tiện ích mariadb_config
# mà pip install mariadb cần để biên dịch.
ENV MARIADB_CONFIG=/usr/bin/mariadb_config

# Cài thư viện Python (production)
RUN pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ mã nguồn backend
COPY . .

# Mở port backend (cho API service)
EXPOSE 8000
# CMD [...]