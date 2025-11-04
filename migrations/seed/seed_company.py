import sys
import os
from datetime import datetime

# Thêm project root vào sys.path để import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.domain.entities.CompanyEntity import CompanyEntity

def seed_company():
    db = SessionLocal()

    company_data = [
        {
            "company_name": "Gakusai株式会社",
        }
    ]

    for data in company_data:
        existing_data = db.query(CompanyEntity).filter_by(company_name=data["company_name"]).first()
        if not existing_data:
            new_data = CompanyEntity(
                company_name=data["company_name"],
                delete_flg=False,
                create_datetime=datetime.now(),
                update_datetime=datetime.now()
            )
            db.add(new_data)

    db.commit()
    db.close()
    print("Seeding completed!")

if __name__ == "__main__":
    seed_company()
