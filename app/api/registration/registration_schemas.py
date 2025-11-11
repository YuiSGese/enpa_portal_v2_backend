from datetime import datetime
from pydantic import BaseModel, EmailStr
from typing import Optional

class RegistrationRequest(BaseModel):
    company_name: str
    person_name: str
    email: EmailStr
    telephone_number: str
    note: str
    consulting_flag: bool

class ProvisionalRegistration(BaseModel):
    id: str
    company_name: str
    person_name: str
    email: EmailStr
    telephone_number: Optional[str] = None
    note: Optional[str] = None
    consulting_flag: bool
    invalid_flag: bool
    expiration_datetime: datetime
    create_datetime: datetime
    update_datetime: datetime

    class Config:
        from_attributes = True

    
class RegistrationResponse(BaseModel):
    detail: str
    entity: Optional[ProvisionalRegistration] = None


class VerifyRegistrationResponse(BaseModel):
    detail: str
    entity: Optional[ProvisionalRegistration] = None