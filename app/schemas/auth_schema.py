from pydantic import BaseModel, EmailStr


class RegisterRequest(BaseModel):
    company_name: str
    name: str
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    company_id: int
    name: str
    email: str
    role: str


class WebhookEvent(BaseModel):
    event: str | None = None
    data: dict | None = None
