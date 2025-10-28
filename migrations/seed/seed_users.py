import sys
import os

# Thêm project root vào sys.path để import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.domain.entities.UserEntity import UserEntity

def seed_users():
    db = SessionLocal()

    users_data = [
        {
            "user_name": "Yui",
            "email": "yuice@example.com",
            "password": "$10$2gaTaMM1Lz1rL5TEGOI3kur/p0R5KegrIn1wDLjEK5JPgKXnWnx1q",
            "role_id": 1
        },
        {
            "user_name": "khanh",
            "email": "khanh@example.com",
            "password": "$2b$10$rMxBMOcHUvpzwB35k/0B6OPncZno1AKuHqk7DU/nuaXOd7wIxc.JC",
            "role_id": 2
        },
        {
            "user_name": "admin",
            "email": "admin@example.com",
            "password": "$2b$10$2gaTaMM1Lz1rL5TEGOI3kur/p0R5KegrIn1wDLjEK5JPgKXnWnx1q",
            "role_id": 2
        },
    ]

    for user in users_data:
        # Kiểm tra email đã tồn tại chưa
        existing_user = db.query(UserEntity).filter_by(email=user["email"]).first()
        if not existing_user:
            new_user = UserEntity(
                user_name=user["user_name"],
                email=user["email"],
                password=user["password"],
                role_id=user["role_id"],
                delete_flg=False
            )
            db.add(new_user)

    db.commit()
    db.close()
    print("Seeding completed!")

if __name__ == "__main__":
    seed_users()
