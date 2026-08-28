from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.company import Company
from app.models.user import User
from app.schemas.auth_schema import LoginResponse, RegisterRequest
from app.services.security import create_access_token, verify_password

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=LoginResponse)
def register(
    data: RegisterRequest,
    db: Session = Depends(get_db),
):
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email ja cadastrado")

    company = Company(name=data.company_name)
    db.add(company)
    db.flush()

    user = User(
        company_id=company.id,
        name=data.name,
        email=data.email,
        role="owner",
    )
    user.set_password(data.password)
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(str(user.id), {"company_id": user.company_id})
    return LoginResponse(
        access_token=token,
        user_id=user.id,
        company_id=user.company_id,
        name=user.name,
        email=user.email,
        role=user.role,
    )


@router.post("/login", response_model=LoginResponse)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email ou senha incorretos")

    token = create_access_token(str(user.id), {"company_id": user.company_id})
    return LoginResponse(
        access_token=token,
        user_id=user.id,
        company_id=user.company_id,
        name=user.name,
        email=user.email,
        role=user.role,
    )
