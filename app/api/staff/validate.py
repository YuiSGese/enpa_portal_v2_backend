from pydantic import BaseModel, EmailStr
from typing import Optional

class StaffCreateRequest(BaseModel):
    username: str
    email: str
    chatwork_id: str
    is_admin: bool
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
        orm_mode = True

class StaffCreateResponse(BaseModel):
    detail: str
    user: Optional[UserSchema] = None