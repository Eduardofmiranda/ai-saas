from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.user import User
from app.schemas.user_schema import UserCreate, UserResponse, UserUpdate
from app.services.deps import get_current_user

router = APIRouter(prefix="/users", tags=["Users"])

# Roles: owner > admin > agent. So o owner/admin gerencia a empresa.
_MANAGE_ROLES = ("admin", "owner")


def _require_manager(current_user: User) -> None:
    if current_user.role not in _MANAGE_ROLES:
        raise HTTPException(status_code=403, detail="Apenas administradores podem gerenciar a equipe")


@router.get("/", response_model=list[UserResponse])
def list_users(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lista os membros (users) da empresa do usuario atual."""
    users = (
        db.query(User)
        .filter(User.company_id == current_user.company_id)
        .order_by(User.id)
        .all()
    )
    return users


@router.post("/", response_model=UserResponse)
def create_user(
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
    db.commit()
    db.refresh(user)
    return user


@router.patch("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
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

    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}")
def delete_user(
    user_id: int,
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
    return {"ok": True}
