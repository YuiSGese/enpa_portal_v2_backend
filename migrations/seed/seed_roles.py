import sys
import os

# Thêm root project vào sys.path để import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.domain.entities.RoleEntity import RoleEntity

def seed_roles():
    db = SessionLocal()

    roles_data = [
        {
            "id": "f97726eb-387d-4839-b686-368c32ba92b0",
            "role_name": "ROLE_ADMIN", 
            "note": "",
        },
        {
            "id": "f97726eb-387d-4839-b686-368c32ba92b1",
            "role_name": "ROLE_MANAGER", 
            "note": "",
        },
        {
            "id": "f97726eb-387d-4839-b686-368c32ba92b3",
            "role_name": "ROLE_USER", 
            "note": "",
        },
    ]

    for role in roles_data:
        existing_role = db.query(RoleEntity).filter_by(role_name=role["role_name"]).first()
        if not existing_role:
            new_role = RoleEntity(
                id=role["id"],
                role_name=role["role_name"],
                note=role["note"]
            )
            db.add(new_role)

    db.commit()
    db.close()
    print("Seeding roles completed!")

if __name__ == "__main__":
    seed_roles()
