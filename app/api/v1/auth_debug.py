from fastapi import APIRouter, Depends, Query
from app.api.dependencies import get_current_user
from app.services.rbac_service import RBACService
from app.db.session import get_db
from sqlalchemy.orm import Session
from app.schemas.rbac import DebugAccessRead

router = APIRouter(prefix="/auth", tags=["Auth Debug"])


@router.get("/debug-access", response_model=DebugAccessRead)
def debug_access(
    required_permission: str | None = Query(None),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    rbac = RBACService(db)

    roles = [role.code for role in current_user.roles]
    permissions = rbac.get_user_permissions(current_user)

    missing = []
    if required_permission:
        missing = rbac.get_missing_permissions(current_user, required_permission)

    return {
        "user_id": str(current_user.id),
        "roles": roles,
        "permissions": permissions,
        "missing_permissions": missing
    }
