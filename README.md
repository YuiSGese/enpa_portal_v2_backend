# 📘 Hướng dẫn sử dụng dự án Backend - EmpaPortal V2

Tài liệu này giúp thành viên mới trong team hiểu rõ **cấu trúc dự án backend** (FastAPI + MySQL) của hệ thống EmpaPortal V2, bao gồm:

- Giải thích chức năng từng thư mục, class, và file quan trọng
- Giới thiệu cấu trúc module hóa gọn gàng (mỗi tool là một module độc lập)
- Ví dụ quy trình khi tạo một công cụ (tool) mới

## Getting Started

1. create database from ORM:
```bash
python migrations/create_tables.py
```
---

2. create database seeder (optional):
```bash
python migrations/seed_users.py
```
---

3. run the development server:
```bash
uvicorn app.main:app --reload --port 8000
```
---

## 🧱 1. Tổng quan dự án

Dự án backend được phát triển bằng **Python (FastAPI)**, sử dụng kiến trúc kết hợp giữa **Clean Architecture** và **Modular Architecture (feature-based)**.

Điều này có nghĩa là:

- Các thành phần cốt lõi như `core`, `domain`, `api` được dùng chung.
- Mỗi công cụ (tool) được tổ chức như một **module độc lập**, có đầy đủ controller, service, schema, và tài nguyên riêng.

---

## 📂 2. Cấu trúc thư mục (chi tiết)

```
.
├── app
│   ├── api                      # Endpoint chung của hệ thống
│   │   ├── controllers           # Xử lý request/response
│   │   │   └── user_controller.py
│   │   ├── routes                # Định nghĩa các endpoint HTTP
│   │   │   └── user_route.py
│   │   └── validators            # Kiểm tra dữ liệu bằng Pydantic
│   │       └── user_validator.py
│   │
│   ├── assets                    # Tài nguyên tĩnh toàn hệ thống (font, hình...)
│   │   └── fonts/
│   │       ├── NotoSansJP-Bold.ttf
│   │       └── WorkSans-Medium.ttf
│   │
│   ├── core                      # Thành phần lõi: cấu hình, kết nối DB, log
│   │   ├── config.py             # Đọc biến môi trường từ .env
│   │   ├── database.py           # Kết nối tới MySQL (SQLAlchemy)
│   │   └── logger.py             # Ghi log hệ thống
│   │
│   ├── domain                    # Logic nghiệp vụ chung (vd: quản lý user)
│   │   ├── entities              # Mô hình ORM ánh xạ bảng DB
│   │   ├── repositories          # CRUD, thao tác dữ liệu DB
│   │   └── services              # Xử lý logic nghiệp vụ
│   │
│   ├── internal                  # Tác vụ nội bộ (cronjob, background tasks...)
│   ├── middleware                # Middleware như auth, CORS, rate limit
│   ├── storage                   # Cache, file tạm, SQL script, migration
│   │   ├── cache/
│   │   └── database/
│   │
│   ├── tool03                    # Mỗi công cụ là 1 module độc lập
│   │   ├── controller.py         # Nhận request, gọi service, trả response
│   │   ├── service.py            # Logic nghiệp vụ chính của tool03
│   │   ├── schemas.py            # Định nghĩa schema request/response
│   │   ├── repository.py         # (tùy chọn) Xử lý CRUD nếu có DB
│   │   ├── assets/               # Template hoặc hình ảnh riêng của tool03
│   │   │   └── templates/
│   │   │       ├── template_A.jpg
│   │   │       └── template_B.jpg
│   │   └── __init__.py
│   │
│   └── main.py                   # Điểm khởi động chính của ứng dụng FastAPI
│
├── document                      # Tài liệu nội bộ và script SQL
│   └── database
│       └── 001_init.sql           # Tạo cơ sở dữ liệu ban đầu
│
├── scripts                        # Script tiện ích (vd: sinh file tool mới)
│   └── new_tool.py
│
├── tests                          # Unit test và integration test
├── requirements.txt               # Danh sách thư viện Python
└── README.md                      # Tài liệu chính của dự án
```

---

## ⚙️ 3. Giải thích chi tiết từng phần

### 📁 `app/api/`

- **controllers/**: Nhận request từ frontend, xử lý dữ liệu đầu vào, gọi service tương ứng.
- **routes/**: Khai báo các endpoint API (ví dụ: `/api/users`).
- **validators/**: Định nghĩa và xác thực dữ liệu bằng Pydantic models.

### 📁 `app/core/`

- **config.py**: Đọc file `.env` để lấy cấu hình môi trường.
- **database.py**: Tạo engine và session kết nối MySQL.
- **logger.py**: Cấu hình logging (ghi log ra console hoặc file `logs/app.log`).

### 📁 `app/domain/`

- **entities/**: ORM ánh xạ bảng DB.
- **repositories/**: Xử lý CRUD.
- **services/**: Thực thi logic nghiệp vụ (vd: tạo user, kiểm tra quyền...).

### 📁 `app/toolXX/`

- Mỗi tool (ví dụ `tool03`, `tool04`) là **một module riêng biệt**, có thể phát triển, test và triển khai độc lập.
- Mỗi tool gồm:

  - `controller.py`: Xử lý request/response.
  - `service.py`: Logic nghiệp vụ chính.
  - `schemas.py`: Xác thực dữ liệu (request, response).
  - `repository.py`: (tùy chọn) CRUD hoặc query DB.
  - `assets/`: Template hoặc hình ảnh riêng.

### 📁 `app/assets/`

- Chứa font, hình ảnh dùng chung cho toàn hệ thống (như font Nhật Bản, logo...).

### 📁 `app/middleware/`

- Middleware kiểm tra quyền, logging, bảo mật, rate-limit.

### 📁 `document/`

- Lưu tài liệu và các câu lệnh SQL khởi tạo DB (`001_init.sql`).

### 📁 `scripts/`

- Script hỗ trợ phát triển, ví dụ `new_tool.py` giúp sinh tự động cấu trúc tool mới.

### 📁 `tests/`

- Kiểm thử đơn vị (unit test) và kiểm thử tích hợp.

---

## 🧠 4. Khi tạo một công cụ mới (ví dụ: Tool04)

Một công cụ trong EmpaPortal được chia thành 4–5 file chính:

| File                           | Vai trò                                  |
| ------------------------------ | ---------------------------------------- |
| `app/tool04/controller.py`     | Xử lý request, gọi service, trả response |
| `app/tool04/service.py`        | Xử lý logic nghiệp vụ chính              |
| `app/tool04/schemas.py`        | Định nghĩa schema request/response       |
| `app/tool04/repository.py`     | (Tùy chọn) Thao tác DB                   |
| `app/tool04/assets/templates/` | Template hoặc file hình ảnh liên quan    |

### 🔄 Luồng hoạt động

1. Frontend gọi endpoint `/api/tool04`.
2. `controller.py` nhận request, xác thực dữ liệu qua `schemas.py`.
3. `controller.py` gọi `service.py` để xử lý logic.
4. `service.py` thao tác với DB (qua `repository.py`) hoặc xử lý file.
5. Kết quả trả về frontend dưới dạng JSON.

---

## ✅ 5. Tổng kết

Cấu trúc hiện tại là sự kết hợp giữa **Clean Architecture** và **Module-Based Architecture (feature-based)**:

- Gọn gàng, dễ đọc, dễ quản lý cho từng tool.
- Mỗi tool là một module độc lập có thể phát triển hoặc deploy riêng.
- Các thành phần dùng chung (DB, logging, config) nằm trong `core/`.
- Phù hợp cho dự án EmpaPortal: nhiều công cụ nhỏ, chạy độc lập, dễ bảo trì.

📁 Toàn bộ file tài liệu và SQL nằm trong `document/database/`
📄 Tài liệu này (`README.md`) giúp mọi thành viên nắm rõ cách tổ chức và quy tắc khi phát triển backend EmpaPortal V2.
