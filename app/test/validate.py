from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str

class TestFincodeRequest(BaseModel):
    email: EmailStr
    customer_name: str