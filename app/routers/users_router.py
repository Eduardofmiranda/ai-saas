from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import or_
from sqlalchemy.orm import Session
from typing import Optional
from collections import defaultdict

from app.database.session import get_db
from app.models.user import User
from app.models.department import Department
from app.models.user_department import UserDepartment
from app.schemas.user_schema import (
    UserCreate,
    UserResponse,
    UserUpdate,
    UserDepartmentIn,
)
from app.services.audit import log_action
from app.services.deps import get_current_user

router = APIRouter(prefix="/users", tags=["Users"])

# Roles: owner > admin > agent. So o owner/admin gerencia a empresa.
_MANAGE_ROLES = ("admin", "owner")


def _require_manager(current_user: User) -> None:
    if current_user.role not in _MANAGE_ROLES:
        raise HTTPException(status_code=403, detail="Apenas administradores podem gerenciar a equipe")


def _set_user_departments(
    db: Session,
    company_id: int,
    user: User,
    departments: list[UserDepartmentIn] | None,
) -> None:
    """Substitui os setores do usuario, validando pertencimento a empresa."""
    targets = departments or []
    ids = {d.department_id for d in targets}
    if ids:
        found = {
            row[0]
            for row in db.query(Department.id).filter(
                Department.company_id == company_id,
                Department.id.in_(ids),
            ).all()
        }
        missing = ids - found
        if missing:
            raise HTTPException(
                status_code=400,
                detail=f"Setor(s) inexistente(s) na empresa: {sorted(missing)}",
            )

    db.query(UserDepartment).filter(UserDepartment.user_id == user.id).delete(
        synchronize_session=False
    )
    for d in targets:
        db.add(UserDepartment(user_id=user.id, department_id=d.department_id, level=d.level))


def _serialize(user: User, departments: list[UserDepartment]) -> dict:
    return {
        "id": user.id,
        "company_id": user.company_id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "is_platform_admin": user.is_platform_admin,
        "departments": [
            {"department_id": row.department_id, "level": row.level}
            for row in departments
        ],
    }


@router.get("/")
def list_users(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    q: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    """Lista os membros (users) da empresa do usuario atual."""
    query = db.query(User).filter(User.company_id == current_user.company_id)
    if q and q.strip():
        ql = f"%{q.strip()}%"
        query = query.filter(or_(User.name.ilike(ql), User.email.ilike(ql)))
    total = query.count()
    users = query.order_by(User.id).offset(offset).limit(limit).all()

    deps_by_user: dict[int, list[UserDepartment]] = defaultdict(list)
    if users:
        rows = (
            db.query(UserDepartment)
            .filter(UserDepartment.user_id.in_([u.id for u in users]))
            .all()
        )
        for row in rows:
            deps_by_user[row.user_id].append(row)

    return {
        "total": total,
        "items": [_serialize(u, deps_by_user.get(u.id, [])) for u in users],
    }


@router.post("/", response_model=UserResponse)
def create_user(
    request: Request,
    data: UserCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Adiciona um novo membro a empresa (apenas admin/owner)."""
    _require_manager(current_user)

    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        # Se o email ja existe em OUTRA empresa, nao permitir
        if existing.company_id != current_user.company_id:
            raise HTTPException(status_code=409, detail="Email ja cadastrado em outra empresa")
        raise HTTPException(status_code=409, detail="Email ja cadastrado nesta empresa")

    user = User(
        company_id=current_user.company_id,
        name=data.name,
        email=data.email,
        role=data.role,
    )
    user.set_password(data.password)
    db.add(user)
    db.flush()
    _set_user_departments(db, current_user.company_id, user, data.departments)
    db.commit()
    db.refresh(user)

    log_action(db, current_user.company_id, current_user.id, "user.create",
               entity="user", entity_id=user.id,
               details={"email": data.email, "role": data.role}, request=request)

    return user


@router.patch("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    request: Request,
    data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Altera role ou senha de um membro (apenas admin/owner)."""
    _require_manager(current_user)

    user = db.query(User).filter(User.id == user_id).first()
    if not user or user.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado na sua empresa")

    # Nao deixar remover/alterar o owner por um admin
    if user.role == "owner" and current_user.role != "owner":
        raise HTTPException(status_code=403, detail="Apenas o dono pode alterar o dono")

    updates = data.model_dump(exclude_unset=True)
    if "role" in updates and updates["role"]:
        user.role = updates["role"]
    if "password" in updates and updates["password"]:
        user.set_password(updates["password"])
    if "departments" in updates:
        _set_user_departments(db, current_user.company_id, user, data.departments)

    db.commit()
    db.refresh(user)

    log_action(db, current_user.company_id, current_user.id, "user.update",
               entity="user", entity_id=user_id,
               details={"fields": list(updates.keys())}, request=request)

    return user


@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Remove um membro da empresa (apenas admin/owner)."""
    _require_manager(current_user)

    user = db.query(User).filter(User.id == user_id).first()
    if not user or user.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado na sua empresa")

    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Voce nao pode remover a si mesmo")

    if user.role == "owner" and current_user.role != "owner":
        raise HTTPException(status_code=403, detail="Apenas o dono pode remover o dono")

    db.delete(user)
    db.commit()

    log_action(db, current_user.company_id, current_user.id, "user.delete",
               entity="user", entity_id=user_id, request=request)

    return {"ok": True}
