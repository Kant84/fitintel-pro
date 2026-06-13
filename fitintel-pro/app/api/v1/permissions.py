from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db.session import get_db
from app.models.permission import Permission
from app.schemas.permission import PermissionRead

router = APIRouter(prefix="/permissions", tags=["Permissions"])


@router.get("/", response_model=list[PermissionRead])
def get_permissions(db: Session = Depends(get_db)):
    stmt = select(Permission)

    result = db.execute(stmt).scalars().all()

    return result


@router.get("/{permission_id}", response_model=PermissionRead)
def get_permission(permission_id: str, db: Session = Depends(get_db)):
    stmt = select(Permission).where(Permission.id == permission_id)

    result = db.execute(stmt).scalar_one_or_none()

    return result