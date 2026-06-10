from uuid import UUID

from pydantic import BaseModel


class RolePermissionCreate(BaseModel):
    permission_id: UUID


class RolePermissionActionResult(BaseModel):
    status: str
    role_id: UUID
    permission_id: UUID
    
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_db
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.schemas.role import RoleRead
from app.schemas.permission import PermissionRead

router = APIRouter(prefix="/roles", tags=["Roles"])


@router.get("/", response_model=list[RoleRead])
def get_roles(db: Session = Depends(get_db)):
    stmt = (
        select(Role)
        .options(
            selectinload(Role.role_permissions).selectinload(RolePermission.permission)
        )
        .order_by(Role.code)
    )

    roles = db.execute(stmt).scalars().unique().all()
    return roles


@router.get("/{role_id}", response_model=RoleRead)
def get_role(role_id: UUID, db: Session = Depends(get_db)):
    stmt = (
        select(Role)
        .where(Role.id == role_id)
        .options(
            selectinload(Role.role_permissions).selectinload(RolePermission.permission)
        )
    )

    role = db.execute(stmt).scalar_one_or_none()

    if role is None:
        raise HTTPException(status_code=404, detail="Role not found")

    return role


@router.get("/{role_id}/permissions", response_model=list[PermissionRead])
def get_role_permissions(role_id: UUID, db: Session = Depends(get_db)):
    stmt = (
        select(Role)
        .where(Role.id == role_id)
        .options(
            selectinload(Role.role_permissions).selectinload(RolePermission.permission)
        )
    )

    role = db.execute(stmt).scalar_one_or_none()

    if role is None:
        raise HTTPException(status_code=404, detail="Role not found")

    permissions = [
        item.permission
        for item in role.role_permissions
        if item.permission is not None
    ]

    return permissions