from typing import Optional

from pydantic import BaseModel


class DepartmentCreate(BaseModel):
    name: str
    description: str = ""


class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[int] = None


class DepartmentResponse(BaseModel):
    id: int
    company_id: int
    name: str
    description: str
    is_active: int
    created_at: object | None = None
    updated_at: object | None = None

    class Config:
        from_attributes = True
