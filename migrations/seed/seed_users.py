# import sys
# import os
# from datetime import datetime

# # Thêm project root vào sys.path để import app
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# from app.core.database import SessionLocal
# from app.domain.entities.UserEntity import UserEntity

# def seed_users():
#     db = SessionLocal()

#     users_data = [
#         {
#             "username": "yui",
#             "email": "yui@example.com",
#             "password": "$2b$10$2gaTaMM1Lz1rL5TEGOI3kur/p0R5KegrIn1wDLjEK5JPgKXnWnx1q",  # hashed password
#             "company_id": 1,
#             "role_id": 1
#         },
#         {
#             "username": "khanh",
#             "email": "khanh@example.com",
#             "password": "$2b$10$2gaTaMM1Lz1rL5TEGOI3kur/p0R5KegrIn1wDLjEK5JPgKXnWnx1q",
#             "company_id": 1,
#             "role_id": 2
#         },
#         {
#             "username": "admin",
#             "email": "admin@example.com",
#             "password": "$2b$10$2gaTaMM1Lz1rL5TEGOI3kur/p0R5KegrIn1wDLjEK5JPgKXnWnx1q",
#             "company_id": 1,
#             "role_id": 1
#         },
#     ]

#     for user in users_data:
#         existing_user = db.query(UserEntity).filter_by(email=user["email"]).first()
#         if not existing_user:
#             new_user = UserEntity(
#                 username=user["username"],
#                 email=user["email"],
#                 password=user["password"],
#                 company_id=user["company_id"],
#                 role_id=user["role_id"]
#             )
#             db.add(new_user)

#     db.commit()
#     db.close()
#     print("Seeding completed!")

# if __name__ == "__main__":
#     seed_users()
import sys
import os
from datetime import datetime

# Thêm project root vào sys.path để import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.domain.entities.UserEntity import UserEntity
from app.core.bcrypt import get_password_hash # <--- SỬA: Thay đổi import và hàm hash
from app.core.config import ADMIN_INIT_PASSWORD # <--- Dòng MỚI: Import mật khẩu từ SSM/Config

def seed_users():
    db = SessionLocal()

    # Mật khẩu mới sẽ được mã hóa từ biến môi trường (Lấy từ SSM)
    # GỌI HÀM HASH ĐÚNG TÊN TỪ BCrypt.py
    hashed_password_admin = get_password_hash(ADMIN_INIT_PASSWORD) # <--- SỬA: Dùng hàm get_password_hash

    # Tạm thời sửa lại data test để dùng mật khẩu ADMIN_INIT_PASSWORD
    users_data = [
        {
            "username": "yui",
            "email": "yui@example.com",
            "password": hashed_password_admin, # <--- SỬA
            "chatwork_id": "CW001",           # <--- THÊM 
            "company_id": 1,
            "role_id": 1
        },
        {
            "username": "khanh",
            "email": "khanh@example.com",
            "password": hashed_password_admin, # <--- SỬA
            "chatwork_id": "CW002",           # <--- THÊM
         
            "company_id": 1,
            "role_id": 2
        },
        {
            "username": "admin",
            "email": "admin@example.com",

            "password": hashed_password_admin, # <--- SỬA
            "chatwork_id": "CW003",           # <--- THÊM
            "company_id": 1,
            "role_id": 1
        },
    ]

    for user in users_data:
        existing_user = db.query(UserEntity).filter_by(email=user["email"]).first()
        if not existing_user:
            new_user = UserEntity(
                username=user["username"],
                email=user["email"],
                password=user["password"],
                chatwork_id=user["chatwork_id"], # <--- THÊM
                company_id=user["company_id"],
                role_id=user["role_id"]
            )
            db.add(new_user)

    db.commit()
    db.close()
    print("Seeding completed!")

if __name__ == "__main__":
    seed_users()