import uuid
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.domain.entities.ProvisionalRegistrationEntity import ProvisionalRegistrationEntity

class registration_repository:
    def __init__(self, db: Session):
        self.db = db

    def create_provisional_registration(
        self,
        company_name: str,
        person_name: str,
        email: str,
        telephone_number: str,
        note: str | None,
        consulting_flag: str,
        invalid_flag: str = "0",
    ) -> ProvisionalRegistrationEntity:

        expiration_datetime = datetime.now() + timedelta(days=7)

        new_record = ProvisionalRegistrationEntity(
            id=str(uuid.uuid4()),
            company_name=company_name,
            person_name=person_name,
            email=email,
            telephone_number=telephone_number,
            note=note,
            consulting_flag=consulting_flag,
            invalid_flag=invalid_flag,
            expiration_datetime=expiration_datetime,
        )

        self.db.add(new_record)
        self.db.flush()
        self.db.refresh(new_record)

        return new_record