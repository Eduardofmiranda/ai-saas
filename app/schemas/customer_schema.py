from pydantic import BaseModel


class CustomerCreate(BaseModel):
    name: str
    phone: str
    email: str | None = None
    company: str | None = None
    city: str | None = None
    notes: str | None = None


class CustomerResponse(BaseModel):
    id: int
    company_id: int
    name: str | None
    phone: str
    email: str | None = None
    company: str | None = None
    city: str | None = None
    notes: str | None = None

    class Config:
        from_attributes = True
