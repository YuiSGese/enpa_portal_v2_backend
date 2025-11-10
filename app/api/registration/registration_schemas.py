from pydantic import BaseModel, EmailStr
from typing import Optional

class RegistrationRequest(BaseModel):
    aaa: str
    aaaa: str

class RegistrationResponse(BaseModel):
    aaa: str
    aaaa: str
