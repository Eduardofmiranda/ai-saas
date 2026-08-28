from pydantic import BaseModel

class CustomerCreate(BaseModel):
    company_id: int
    name: str
    phone: str

class CustomerResponse(BaseModel):
    id: int
    company_id: int
    name: str
    phone: str

    class Config:
        from_attributes = True