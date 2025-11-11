from datetime import datetime
from re import S
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


class ProvisionalRegistrationCheckResponse(BaseModel):
    detail: str
    valid: bool

class DefinitiveRegistrationRequest(BaseModel):

    prov_reg_id: str
    store_id: str
    store_url: str
    store_name: str
    default_tax_rate: str
    tax_rounding: str
    username: str
    email: EmailStr

class DefinitiveRegistrationResponse(BaseModel):
    detail: str
