from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.user import User
from app.schemas.workflow_schema import WorkflowCreate
from app.services.deps import get_current_user
from app.services.templates import get_template, get_templates

router = APIRouter(prefix="/templates", tags=["templates"])


@router.get("/")
def list_templates() -> list[dict]:
    return get_templates()


@router.get("/{template_id}")
def get_template_detail(template_id: str) -> dict:
    template = get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


@router.post("/{template_id}/use")
def use_template(
    template_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    from app.models.workflow import Workflow

    template = get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    workflow = Workflow(
        company_id=current_user.company_id,
        name=template["name"],
        description=template["description"],
        data=template["data"],
        trigger_type="message",
        active=False,
    )
    db.add(workflow)
    db.commit()
    db.refresh(workflow)

    return {
        "id": workflow.id,
        "name": workflow.name,
        "description": workflow.description,
        "active": workflow.active,
    }
