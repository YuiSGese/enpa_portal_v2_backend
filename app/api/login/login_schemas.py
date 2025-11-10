from pydantic import BaseModel, EmailStr
from typing import Optional

class LoginRequest(BaseModel):
    username: str
    password: str

# Schema con cho user
class UserSchema(BaseModel):
    id: str
    username: str
    email: Optional[str] = None
    role_name: Optional[str] = None
    role_id: Optional[str] = None
    company_id: Optional[str] = None
    company_name: Optional[str] = None

    class Config:
        from_attributes = True  # quan trọng: cho phép chuyển từ SQLAlchemy object sang Pydantic


class LoginResponse(BaseModel):
    access_token: str
    user: Optional[UserSchema] = None