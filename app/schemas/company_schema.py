from pydantic import BaseModel


class CompanyCreate(BaseModel):
    name: str


class CompanyUpdate(BaseModel):
    name: str


class CompanyResponse(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True