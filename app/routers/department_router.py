from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.department import Department
from app.models.user import User
from app.models.user_department import UserDepartment
from app.schemas.department_schema import (
    DepartmentCreate,
    DepartmentResponse,
    DepartmentUpdate,
)
from app.services.deps import get_current_user, require_company_manager
from app.services import access_rules

router = APIRouter(
    prefix="/departments",
    tags=["Departments"],
)


@router.get("/")
def get_departments(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Department).filter(Department.company_id == current_user.company_id)
    department_ids = access_rules.user_department_ids(db, current_user)
    if department_ids is not None:
        query = query.filter(Department.id.in_(department_ids))
    departments = query.order_by(Department.name).all()
    return [DepartmentResponse.model_validate(d) for d in departments]


@router.post("/", response_model=DepartmentResponse)
def create_department(
    data: DepartmentCreate,
    current_user: User = Depends(require_company_manager),
    db: Session = Depends(get_db),
):
    existing = (
        db.query(Department)
        .filter(
            Department.company_id == current_user.company_id,
            Department.name == data.name,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Setor com esse nome ja existe")

    dept = Department(
        company_id=current_user.company_id,
        name=data.name,
        description=data.description,
    )
    db.add(dept)
    db.commit()
    db.refresh(dept)
    return dept


@router.patch("/{department_id}", response_model=DepartmentResponse)
def update_department(
    department_id: int,
    data: DepartmentUpdate,
    current_user: User = Depends(require_company_manager),
    db: Session = Depends(get_db),
):
    dept = (
        db.query(Department)
        .filter(
            Department.id == department_id,
            Department.company_id == current_user.company_id,
        )
        .first()
    )
    if not dept:
        raise HTTPException(status_code=404, detail="Setor nao encontrado")

    if data.name is not None:
        dept.name = data.name
    if data.description is not None:
        dept.description = data.description
    if data.is_active is not None:
        dept.is_active = data.is_active
    db.commit()
    db.refresh(dept)
    return dept


@router.delete("/{department_id}")
def delete_department(
    department_id: int,
    current_user: User = Depends(require_company_manager),
    db: Session = Depends(get_db),
):
    dept = (
        db.query(Department)
        .filter(
            Department.id == department_id,
            Department.company_id == current_user.company_id,
        )
        .first()
    )
    if not dept:
        raise HTTPException(status_code=404, detail="Setor nao encontrado")

    db.query(UserDepartment).filter(UserDepartment.department_id == dept.id).delete()
    from app.models.conversation import Conversation
    from app.models.knowledge import Knowledge
    from app.models.workflow import Workflow
    db.query(Conversation).filter(Conversation.department_id == dept.id).update({Conversation.department_id: None})
    db.query(Workflow).filter(Workflow.department_id == dept.id).update(
        {Workflow.department_id: None}, synchronize_session=False
    )
    db.query(Knowledge).filter(Knowledge.department_id == dept.id).update(
        {Knowledge.department_id: None}, synchronize_session=False
    )
    db.delete(dept)
    db.commit()
    return {"message": "Setor removido com sucesso"}
