from pydantic import BaseModel, EmailStr
from typing import Optional

class LoginRequest(BaseModel):
    username: str
    password: str

# Schema con cho user
class UserSchema(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    role_id: Optional[int] = None
    chatwork_id: str
    company_id: Optional[int] = None

    class Config:
        orm_mode = True  # quan trọng: cho phép chuyển từ SQLAlchemy object sang Pydantic


class LoginResponse(BaseModel):
    access_token: str
    user: Optional[UserSchema] = None