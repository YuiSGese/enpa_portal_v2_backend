import sys
import os

# Thêm project root vào sys.path để import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.domain.entities.user_entity import User

def seed_users():
    db = SessionLocal()

    users_data = [
        {"name": "Alice", "email": "alice@example.com", "password": "pass123"},
        {"name": "Bob", "email": "bob@example.com", "password": "pass123"},
        {"name": "Charlie", "email": "charlie@example.com", "password": "pass123"},
    ]

    for user in users_data:
        # Kiểm tra email đã tồn tại chưa
        existing_user = db.query(User).filter_by(email=user["email"]).first()
        if not existing_user:
            new_user = User(
                name=user["name"],
                email=user["email"],
                password=user["password"]
            )
            db.add(new_user)

    db.commit()
    db.close()
    print("Seeding completed!")

if __name__ == "__main__":
    seed_users()
