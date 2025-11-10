import sys
import os
from datetime import datetime

# Thêm project root vào sys.path để import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.domain.entities.UserEntity import UserEntity

def seed_users():
    db = SessionLocal()

    users_data = [
        {
            "username": "yui",
            "email": "yui@example.com",
            "password": "$2b$10$2gaTaMM1Lz1rL5TEGOI3kur/p0R5KegrIn1wDLjEK5JPgKXnWnx1q",  # hashed password
            "company_id": "f97726eb-387d-4839-b686-368c32ba92c0",
            "role_id": "f97726eb-387d-4839-b686-368c32ba92b0",
        },
        {
            "username": "khanh",
            "email": "khanh@example.com",
            "password": "$2b$10$2gaTaMM1Lz1rL5TEGOI3kur/p0R5KegrIn1wDLjEK5JPgKXnWnx1q",
            "company_id": "f97726eb-387d-4839-b686-368c32ba92c0",
            "role_id": "f97726eb-387d-4839-b686-368c32ba92b1",
        },
        {
            "username": "admin",
            "email": "admin@example.com",
            "password": "$2b$10$2gaTaMM1Lz1rL5TEGOI3kur/p0R5KegrIn1wDLjEK5JPgKXnWnx1q",
            "company_id": "f97726eb-387d-4839-b686-368c32ba92c0",
            "role_id": "f97726eb-387d-4839-b686-368c32ba92b0",
        },
    ]

    for user in users_data:
        existing_user = db.query(UserEntity).filter_by(email=user["email"]).first()
        if not existing_user:
            new_user = UserEntity(
                username=user["username"],
                email=user["email"],
                password=user["password"],
                company_id=user["company_id"],
                role_id=user["role_id"]
            )
            db.add(new_user)

    db.commit()
    db.close()
    print("Seeding completed!")

if __name__ == "__main__":
    seed_users()
