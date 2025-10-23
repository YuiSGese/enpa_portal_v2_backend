# 📘 Hướng dẫn sử dụng dự án Backend - EmpaPortal V2

Tài liệu này giúp thành viên mới trong team hiểu rõ **cấu trúc dự án backend** (FastAPI + MySQL) của hệ thống EmpaPortal V2, bao gồm:

- Giải thích chức năng từng thư mục, class, và file quan trọng
- Ví dụ minh họa quy trình khi tạo một công cụ (tool) mới

---

## 🧱 1. Tổng quan dự án

Dự án backend được phát triển bằng **Python (FastAPI)** với kiến trúc **Clean Architecture**, chia thành nhiều tầng rõ ràng để đảm bảo dễ bảo trì, mở rộng và tái sử dụng.

Mỗi tầng có vai trò riêng:

| Tầng                    | Vai trò chính                                  | Mô tả ngắn                           |
| ----------------------- | ---------------------------------------------- | ------------------------------------ |
| **API Layer**           | Giao tiếp giữa frontend (Next.js) và backend   | Xử lý request/response HTTP          |
| **Domain Layer**        | Chứa toàn bộ logic nghiệp vụ của hệ thống      | Quản lý entity, repository, service  |
| **Core Layer**          | Cấu hình hệ thống (DB, log, env, config)       | Liên kết với hạ tầng, MySQL          |
| **Storage Layer**       | Quản lý cache và cơ sở dữ liệu vật lý          | Chứa script SQL, cache data          |
| **Middleware/Internal** | Xử lý logic nội bộ, bảo mật, logging, task nền | Không tương tác trực tiếp với client |
| **Document/Tests**      | Tài liệu & kiểm thử hệ thống                   | README, SQL scripts, unit test       |

---

## 📂 2. Cấu trúc thư mục (chi tiết các cấp)

```
.
├── app
│   ├── __init__.py
│   ├── api                      # Tầng giao tiếp với frontend
│   │   ├── controllers           # Xử lý request/response, gọi service
│   │   │   ├── tool03_controller.py
│   │   │   ├── tool04_controller.py
│   │   │   └── user_controller.py
│   │   ├── routes                # Định nghĩa endpoint API
│   │   │   ├── tool03_router.py
│   │   │   ├── tool04_router.py
│   │   │   └── user_route.py
│   │   └── validators            # Xác thực dữ liệu vào/ra (Pydantic models)
│   │       ├── tool03_validator.py
│   │       ├── tool04_validator.py
│   │       └── user_validator.py
│   │
│   ├── core                     # Cấu hình, kết nối và logging
│   │   ├── config.py             # Cấu hình biến môi trường (.env)
│   │   ├── database.py           # Kết nối tới MySQL
│   │   └── logger.py             # Ghi log hệ thống
│   │
│   ├── domain                   # Logic nghiệp vụ (business logic)
│   │   ├── entities              # Mô hình ORM cho từng bảng DB
│   │   │   ├── tool03_entity.py
│   │   │   ├── tool04_entity.py
│   │   │   └── user_entity.py
│   │   ├── repositories          # CRUD, thao tác trực tiếp DB
│   │   │   ├── tool03_repository.py
│   │   │   ├── tool04_repository.py
│   │   │   └── user_repository.py
│   │   └── services              # Logic nghiệp vụ chính, xử lý dữ liệu
│   │       ├── tool03_service.py
│   │       ├── tool04_service.py
│   │       └── user_service.py
│   │
│   ├── internal                 # Xử lý tác vụ nội bộ (cronjob, async job...)
│   ├── middleware               # Middleware như auth, CORS, rate limit
│   ├── storage                  # Lưu trữ, cache và SQL script
│   │   ├── cache/               # Dành cho Redis hoặc cache tạm
│   │   └── database/            # File SQL hoặc migration script
│   └── main.py                  # Điểm khởi động của ứng dụng FastAPI
│
├── document                    # Tài liệu nội bộ và script SQL
│   └── database
│       └── 001_init.sql         # File tạo cơ sở dữ liệu MySQL ban đầu
│
├── scripts                     # Script tiện ích (ví dụ: sinh file tool mới)
│   └── new_tool.py
│
├── tests                       # Unit test và integration test
├── requirements.txt             # Danh sách thư viện Python
└── README.md                    # Tài liệu chính của dự án
```

---

## ⚙️ 3. Chức năng chi tiết từng thư mục

### 📁 `app/api/`

- **controllers/**: nhận request, xử lý dữ liệu input, gọi service phù hợp.
- **routes/**: khai báo các endpoint (`/api/tool03`, `/api/users`, ...).
- **validators/**: định nghĩa dữ liệu vào/ra bằng Pydantic (`Tool03Request`, `Tool03Response`).

### 📁 `app/domain/`

- **entities/**: ánh xạ các bảng DB bằng SQLAlchemy (ORM).
- **repositories/**: thao tác trực tiếp với DB (insert, update, select, delete).
- **services/**: xử lý nghiệp vụ (gọi nhiều repository, kiểm tra logic, validate nghiệp vụ).

### 📁 `app/core/`

- **config.py**: đọc file `.env` để lấy biến môi trường (DB_HOST, DB_USER,...)
- **database.py**: tạo `engine`, `SessionLocal` kết nối đến MySQL.
- **logger.py**: cấu hình log, lưu log ra file `logs/app.log`.

### 📁 `app/storage/`

- **database/**: lưu các file SQL tạo database hoặc migration (ví dụ: `001_init.sql`).
- **cache/**: dành cho Redis hoặc các file cache.

### 📁 `document/`

- Lưu các tài liệu kỹ thuật, hướng dẫn, file SQL.

  - Ví dụ: `document/database/001_init.sql` để khởi tạo DB.

### 📁 `scripts/`

- Chứa các script tiện ích phục vụ phát triển.

  - Ví dụ: `new_tool.py` để tự động tạo cấu trúc file cho tool mới.

### 📁 `tests/`

- Chứa các file test (unit test, integration test) để đảm bảo chất lượng code.

---

## 🧠 4. Khi tạo một công cụ mới (ví dụ: Tool03)

Một công cụ trong hệ thống EmpaPortal thường có **6 file chính**, được tạo trong hai tầng: `api` và `domain`.

| File                                           | Vai trò                                   |
| ---------------------------------------------- | ----------------------------------------- |
| `app/api/controllers/tool03_controller.py`     | Nhận request, gọi service, xử lý response |
| `app/api/routes/tool03_router.py`              | Định nghĩa endpoint `/api/tool03`         |
| `app/api/validators/tool03_validator.py`       | Định nghĩa schema (request/response)      |
| `app/domain/entities/tool03_entity.py`         | Định nghĩa bảng dữ liệu (ORM)             |
| `app/domain/repositories/tool03_repository.py` | CRUD với DB                               |
| `app/domain/services/tool03_service.py`        | Xử lý logic nghiệp vụ, gọi repository     |

### 🔄 Luồng hoạt động

1. Frontend gửi request tới `/api/tool03`.
2. `tool03_router.py` nhận request → chuyển tới `tool03_controller.py`.
3. `tool03_controller` xử lý dữ liệu đầu vào (`tool03_validator`) → gọi `tool03_service`.
4. `tool03_service` xử lý nghiệp vụ, gọi `tool03_repository` để ghi DB.
5. `tool03_repository` thao tác trên bảng `tool03_entity` (ORM) → lưu xuống MySQL.
6. Trả response JSON về frontend.

---

## ✅ 5. Tổng kết

Dự án backend EmpaPortal V2 tuân theo mô hình **Clean Architecture**, giúp:

- Dễ bảo trì và mở rộng từng công cụ riêng lẻ.
- Phân chia rõ vai trò giữa giao tiếp (API), nghiệp vụ (Domain) và hạ tầng (Core).
- Dễ dàng thêm tính năng mới (tool, user, shop...) chỉ bằng việc thêm 6 file theo chuẩn.

📁 Mọi thông tin về database nằm trong `document/database/`
📄 Tài liệu này nằm trong `README.md` để team đọc hiểu cấu trúc và quy tắc chung.
