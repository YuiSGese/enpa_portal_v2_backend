from pydantic import BaseModel, EmailStr
from typing import List, Optional

class StaffCreateRequest(BaseModel):
    username: str
    email: str
    is_admin: bool
    password: str

# Schema con cho user
class UserSchema(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    role_id: Optional[int] = None
    company_id: Optional[int] = None

    class Config:
        from_attributes = True

class StaffCreateResponse(BaseModel):
    message: str
    user: Optional[UserSchema] = None

class StaffListResponse(BaseModel):
    count: int
    list: List[UserSchema]

class StaffDeleteResponse(BaseModel):
    message: str
    user: Optional[UserSchema] = None