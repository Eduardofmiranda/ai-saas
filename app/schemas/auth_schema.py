from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    company_name: str
    name: str
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: str = ""
    user_id: int
    company_id: int
    name: str
    email: str
    role: str
    is_platform_admin: bool = False


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=20, max_length=4096)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=20, max_length=512)
    new_password: str = Field(min_length=8, max_length=128)


class WebhookEvent(BaseModel):
    event: str | None = None
    data: dict | None = None
