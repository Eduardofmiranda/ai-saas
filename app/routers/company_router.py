from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.company import Company
from app.models.user import User
from app.schemas.company_schema import (
    CompanyCreate,
    CompanyResponse,
    CompanyUpdate,
)
from app.services.deps import get_current_user

router = APIRouter(
    prefix="/companies",
    tags=["Companies"],
)


@router.post("/", response_model=CompanyResponse)
def create_company(
    company: CompanyCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    new_company = Company(name=company.name)
    db.add(new_company)
    db.commit()
    db.refresh(new_company)
    return new_company


@router.get("/", response_model=list[CompanyResponse])
def get_companies(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(Company)
        .filter(Company.id == current_user.company_id)
        .all()
    )


@router.get("/{company_id}", response_model=CompanyResponse)
def get_company(
    company_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if company_id != current_user.company_id:
        raise HTTPException(status_code=403, detail="Acesso negado")
    company = (
        db.query(Company)
        .filter(Company.id == company_id)
        .first()
    )
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company


@router.patch("/{company_id}", response_model=CompanyResponse)
def update_company(
    company_id: int,
    data: CompanyUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if company_id != current_user.company_id:
        raise HTTPException(status_code=403, detail="Acesso negado")
    company = (
        db.query(Company)
        .filter(Company.id == company_id)
        .first()
    )
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    company.name = data.name
    db.commit()
    db.refresh(company)
    return company
