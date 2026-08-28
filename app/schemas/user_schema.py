from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str = "agent"


class UserUpdate(BaseModel):
    role: str | None = None
    password: str | None = None


class UserResponse(BaseModel):
    id: int
    company_id: int
    name: str
    email: str
    role: str

    class Config:
        from_attributes = True
