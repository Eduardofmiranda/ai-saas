"""Regras de acesso por setor (Fase 8.9).

Niveis por setor (ordem crescente): view < attend < manage.

- Dono/Admin: acesso irrestrito a todas as conversas e setores.
- Atendente com setores: ve conversas dos seus setores + conversas SEM setor;
  responde/altera/assume apenas com nivel >= attend.
  Nivel `manage` hoje tem as mesmas acoes de `attend`, reservado para gestao/
  transferencia entre setores quando houver acao manual de transferencia.
- Atendente SEM setor: comportamento anterior (ve e atende tudo) — compatibilidade.
"""
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.user_department import UserDepartment

_LEVEL_ORDER = {"view": 1, "attend": 2, "manage": 3}
_ATTEND = _LEVEL_ORDER["attend"]


def has_full_access(user: User) -> bool:
    """Gestores da empresa acessam tudo, independente de setor."""
    return user.role in ("owner", "admin")


def _user_levels(db: Session, user: User) -> dict[int, int]:
    """department_id -> nivel numerico do usuario."""
    rows = db.query(UserDepartment).filter(UserDepartment.user_id == user.id).all()
    return {r.department_id: _LEVEL_ORDER.get(r.level, _ATTEND) for r in rows}


def user_department_ids(db: Session, user: User) -> set[int] | None:
    """Setores visiveis; None representa acesso irrestrito legado/gestor."""
    if has_full_access(user):
        return None
    levels = _user_levels(db, user)
    return set(levels) if levels else None


def visible_department_condition(model, db: Session, user: User):
    """Condicao reutilizavel para recursos opcionais vinculados a setor."""
    department_ids = user_department_ids(db, user)
    if department_ids is None:
        return None
    return or_(
        model.department_id.is_(None),
        model.department_id.in_(department_ids),
    )


def can_view_department(db: Session, user: User, department_id: int | None) -> bool:
    """Valida acesso de leitura a um recurso global ou de um setor."""
    if department_id is None:
        return True
    department_ids = user_department_ids(db, user)
    return department_ids is None or department_id in department_ids


def visible_condition(conv_model, db: Session, user: User):
    """Condicao SQL para restringir conversas por setor; None = todas.

    Atendente com setores ve: conversas dos seus setores OU conversas sem setor.
    """
    return visible_department_condition(conv_model, db, user)


def can_view(db: Session, user: User, conversation) -> bool:
    """Pode ler a conversa (qualquer nivel de um setor membro)."""
    if has_full_access(user):
        return True
    if conversation.department_id is None:
        return True
    levels = _user_levels(db, user)
    if not levels:
        return True
    return conversation.department_id in levels


def can_attend(db: Session, user: User, conversation) -> bool:
    """Pode responder/alterar status/assumir a conversa (nivel >= attend)."""
    if has_full_access(user):
        return True
    if conversation.department_id is None:
        return True
    levels = _user_levels(db, user)
    if not levels:
        return True
    return levels.get(conversation.department_id, 0) >= _ATTEND
