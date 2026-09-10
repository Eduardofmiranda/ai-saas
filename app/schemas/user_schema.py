from typing import Literal

from pydantic import BaseModel, EmailStr, Field

ACCESS_LEVELS = Literal["view", "attend", "manage"]
USER_ROLES = Literal["owner", "admin", "agent"]


class UserDepartmentIn(BaseModel):
    department_id: int
    level: ACCESS_LEVELS = "attend"


class UserDepartmentOut(BaseModel):
    department_id: int
    level: str


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: USER_ROLES = "agent"
    departments: list[UserDepartmentIn] = []


class UserUpdate(BaseModel):
    role: USER_ROLES | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)
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
