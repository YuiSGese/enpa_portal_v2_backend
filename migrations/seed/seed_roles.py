import sys
import os

# Thêm root project vào sys.path để import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.domain.entities.RoleEntity import RoleEntity

def seed_roles():
    db = SessionLocal()

    roles_data = [
        {"role_name": "ROLE_ADMIN", "description": "Quản trị toàn bộ hệ thống"},
        {"role_name": "ROLE_USER", "description": "Quản lý dữ liệu, báo cáo"},
    ]

    for role in roles_data:
        existing_role = db.query(RoleEntity).filter_by(role_name=role["role_name"]).first()
        if not existing_role:
            new_role = RoleEntity(
                role_name=role["role_name"],
                description=role["description"]
            )
            db.add(new_role)

    db.commit()
    db.close()
    print("Seeding roles completed!")

if __name__ == "__main__":
    seed_roles()
