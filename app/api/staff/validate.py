from pydantic import BaseModel, EmailStr

class StaffCreateRequest(BaseModel):
    username: str
    email: str
    chatwork_id: str
    is_admin: bool
    password: str

class StaffCreateResponse(BaseModel):
    access_token: str
    user_name: str