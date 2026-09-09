from typing import Literal

from pydantic import BaseModel, EmailStr

ACCESS_LEVELS = Literal["view", "attend", "manage"]


class UserDepartmentIn(BaseModel):
    department_id: int
    level: ACCESS_LEVELS = "attend"


class UserDepartmentOut(BaseModel):
    department_id: int
    level: str


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str = "agent"
    departments: list[UserDepartmentIn] = []


class UserUpdate(BaseModel):
    role: str | None = None
    password: str | None = None
    departments: list[UserDepartmentIn] | None = None


class UserResponse(BaseModel):
    id: int
    company_id: int
    name: str
    email: str
    role: str
    is_platform_admin: bool = False
    departments: list[UserDepartmentOut] = []

    class Config:
        from_attributes = True
