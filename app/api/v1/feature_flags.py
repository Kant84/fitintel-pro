# app/api/v1/feature_flags.py
import time
import hashlib
import json
from typing import Optional, Any, List
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from redis import Redis

from app.db.base import get_db
from app.core.config import settings
from app.api.dependencies import get_current_user, require_roles
from app.models.feature_flag import (
    FeatureFlag, FeatureFlagTenantOverride, FeatureFlagUserOverride,
    FeatureFlagAudit, FeatureFlagDependency, FlagScope, FlagType
)
from app.schemas.feature_flag import (
    FeatureFlagCreate, FeatureFlagUpdate, FeatureFlagResponse,
    FeatureFlagCheckRequest, FeatureFlagCheckResponse,
    FeatureFlagBulkUpdate, FeatureFlagAuditResponse, FlagConditions
)

router = APIRouter()

# Redis-клиент (инициализируется при старте приложения)
redis_client: Optional[Redis] = None

def get_redis() -> Redis:
    global redis_client
    if redis_client is None:
        redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    else:
        # Проверяем, живо ли соединение
        try:
            redis_client.ping()
        except:
            redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    return redis_client

def _cache_key(flag_key: str, tenant_id: Optional[int] = None, user_id: Optional[int] = None) -> str:
    return f"ff:{flag_key}:t:{tenant_id}:u:{user_id}"

def _log_audit(db: Session, flag_id: int, action: str, old_value: Any, new_value: Any, changed_by: str, reason: Optional[str] = None):
    audit = FeatureFlagAudit(
        flag_id=flag_id,
        action=action,
        old_value=old_value,
        new_value=new_value,
        changed_by=changed_by,
        reason=reason
    )
    db.add(audit)
    db.commit()

def _check_dependencies(db: Session, flag: FeatureFlag, desired_value: Any) -> bool:
    """Проверяет, что все зависимые флаги включены, если пытаемся включить текущий."""
    if not desired_value or flag.flag_type != FlagType.BOOLEAN:
        return True

    deps = db.query(FeatureFlagDependency).filter(FeatureFlagDependency.flag_id == flag.id).all()
    for dep in deps:
        required = db.query(FeatureFlag).filter(FeatureFlag.id == dep.requires_flag_id).first()
        if not required or not required.target_value:
            return False
    return True

def _evaluate_conditions(conditions: Optional[FlagConditions], user_role: Optional[str], desktop_version: Optional[str]) -> bool:
    """Проверяет условные ограничения флага."""
    if not conditions:
        return True

    import datetime
    now = datetime.datetime.now(datetime.timezone.utc)

    if conditions.start_date and now < conditions.start_date:
        return False
    if conditions.end_date and now > conditions.end_date:
        return False

    if conditions.allowed_roles and user_role and user_role not in conditions.allowed_roles:
        return False

    if conditions.min_desktop_version and desktop_version:
        # Простое сравнение версий
        if desktop_version < conditions.min_desktop_version:
            return False

    # Percentage rollout — проверяем по хешу user_id или случайно
    if conditions.percentage_rollout is not None and conditions.percentage_rollout < 100:
        # Для детерминированности используем хеш флага + текущий час
        hash_input = f"{conditions.percentage_rollout}:{now.hour}"
        hash_val = int(hashlib.md5(hash_input.encode()).hexdigest(), 16) % 100
        if hash_val >= conditions.percentage_rollout:
            return False

    return True

@router.post("", response_model=FeatureFlagResponse, tags=["Feature Flags"])
def create_flag(
    data: FeatureFlagCreate,
    db: Session = Depends(get_db),
    current_user = Depends(require_roles("SUPER_ADMIN"))
):
    """Создание нового флага (только SuperAdmin)."""
    existing = db.query(FeatureFlag).filter(FeatureFlag.flag_key == data.flag_key).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Флаг {data.flag_key} уже существует")

    flag_data = data.dict()
    # Копируем default_value в target_value если target_value не задан
    if flag_data.get("default_value") is not None and flag_data.get("target_value") is None:
        flag_data["target_value"] = flag_data["default_value"]
    flag = FeatureFlag(**flag_data, changed_by=current_user.email)
    db.add(flag)
    db.commit()
    db.refresh(flag)

    _log_audit(db, flag.id, "CREATE", None, flag.target_value, current_user.email)

    # Инвалидируем кэш
    r = get_redis()
    r.delete(_cache_key(flag.flag_key))

    return flag

@router.get("", response_model=List[FeatureFlagResponse], tags=["Feature Flags"])
def list_flags(
    scope: Optional[FlagScope] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Список флагов с фильтрацией."""
    query = db.query(FeatureFlag)
    if scope:
        query = query.filter(FeatureFlag.scope == scope)
    if is_active is not None:
        query = query.filter(FeatureFlag.is_active == is_active)
    return query.all()

@router.get("/{flag_id}", response_model=FeatureFlagResponse, tags=["Feature Flags"])
def get_flag(flag_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """Получение флага по ID."""
    flag = db.query(FeatureFlag).filter(FeatureFlag.id == flag_id).first()
    if not flag:
        raise HTTPException(status_code=404, detail="Флаг не найден")
    return flag

@router.put("/{flag_id}", response_model=FeatureFlagResponse, tags=["Feature Flags"])
def update_flag(
    flag_id: int,
    data: FeatureFlagUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(require_roles("SUPER_ADMIN"))
):
    """Обновление флага (только SuperAdmin)."""
    flag = db.query(FeatureFlag).filter(FeatureFlag.id == flag_id).first()
    if not flag:
        raise HTTPException(status_code=404, detail="Флаг не найден")

    old_value = flag.target_value

    # Проверка зависимостей
    if data.target_value and not _check_dependencies(db, flag, data.target_value):
        raise HTTPException(status_code=400, detail="Нельзя включить флаг: требуемые зависимости выключены")

    # Нельзя отключить MODULE_CORE_PLATFORM если есть зависимые
    if flag.flag_key == "MODULE_CORE_PLATFORM" and data.target_value == False:
        dependent_count = db.query(FeatureFlagDependency).filter(
            FeatureFlagDependency.requires_flag_id == flag.id
        ).count()
        if dependent_count > 0:
            raise HTTPException(status_code=400, detail="Нельзя отключить MODULE_CORE_PLATFORM: есть зависимые модули")

    update_data = data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(flag, field, value)

    flag.changed_by = current_user.email
    db.commit()
    db.refresh(flag)

    _log_audit(db, flag.id, "UPDATE", old_value, flag.target_value, current_user.email)

    # Инвалидируем кэш
    r = get_redis()
    r.delete(_cache_key(flag.flag_key))

    return flag

@router.delete("/{flag_id}", response_model=dict, tags=["Feature Flags"])
def delete_flag(
    flag_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(require_roles("SUPER_ADMIN"))
):
    """Удаление флага (только SuperAdmin)."""
    flag = db.query(FeatureFlag).filter(FeatureFlag.id == flag_id).first()
    if not flag:
        raise HTTPException(status_code=404, detail="Флаг не найден")

    _log_audit(db, flag.id, "DELETE", flag.target_value, None, current_user.email)

    r = get_redis()
    r.delete(_cache_key(flag.flag_key))

    db.delete(flag)
    db.commit()
    return {"detail": "Флаг удалён"}

@router.post("/check", response_model=FeatureFlagCheckResponse, tags=["Feature Flags"])
def check_flag(
    request: FeatureFlagCheckRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Проверка значения флага (основной endpoint для клиентов)."""
    start_time = time.time()
    r = get_redis()

    cache_key = _cache_key(request.flag_key, request.tenant_id, request.user_id)

    # 1. Проверка Redis-кэша
    cached = r.get(cache_key)
    if cached:
        data = json.loads(cached)
        data["latency_ms"] = (time.time() - start_time) * 1000
        return FeatureFlagCheckResponse(**data)

    # 2. Проверка из БД
    flag = db.query(FeatureFlag).filter(FeatureFlag.flag_key == request.flag_key).first()

    if not flag or not flag.is_active:
        # Fallback на default
        result = FeatureFlagCheckResponse(
            flag_key=request.flag_key,
            value=False,
            source="default",
            is_active=False,
            latency_ms=(time.time() - start_time) * 1000
        )
        r.setex(cache_key, 60, result.json())
        return result

    # Определяем значение по иерархии
    value = flag.default_value
    source = "default"

    # Системный/модульный уровень
    if flag.target_value is not None:
        value = flag.target_value
        source = flag.scope.value

    # Клиентский уровень (tenant)
    if request.tenant_id and flag.scope in [FlagScope.TENANT, FlagScope.CANARY]:
        tenant_override = db.query(FeatureFlagTenantOverride).filter(
            and_(
                FeatureFlagTenantOverride.flag_id == flag.id,
                FeatureFlagTenantOverride.tenant_id == request.tenant_id,
                FeatureFlagTenantOverride.is_active == True
            )
        ).first()
        if tenant_override:
            value = tenant_override.target_value
            source = "tenant"

    # Пользовательский уровень
    if request.user_id and flag.scope in [FlagScope.USER, FlagScope.CANARY]:
        user_override = db.query(FeatureFlagUserOverride).filter(
            and_(
                FeatureFlagUserOverride.flag_id == flag.id,
                FeatureFlagUserOverride.user_id == request.user_id,
                FeatureFlagUserOverride.is_active == True
            )
        ).first()
        if user_override:
            value = user_override.target_value
            source = "user"

    # Проверка условий
    conditions = flag.conditions
    if conditions and not _evaluate_conditions(conditions, request.user_role, request.desktop_version):
        value = flag.default_value
        source = "default (conditions not met)"

    latency = (time.time() - start_time) * 1000

    result = FeatureFlagCheckResponse(
        flag_key=request.flag_key,
        value=value,
        source=source,
        is_active=flag.is_active,
        latency_ms=round(latency, 2)
    )

    # Кэшируем на 60 секунд
    r.setex(cache_key, 60, result.json())

    return result

@router.post("/bulk", tags=["Feature Flags"])
def bulk_update(
    data: FeatureFlagBulkUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(require_roles("SUPER_ADMIN"))
):
    """Массовое обновление флагов (только SuperAdmin)."""
    updated = 0
    errors = []

    for item in data.flags:
        flag_key = item.get("flag_key")
        flag = db.query(FeatureFlag).filter(FeatureFlag.flag_key == flag_key).first()
        if not flag:
            errors.append(f"Флаг {flag_key} не найден")
            continue

        old_value = flag.target_value
        new_value = item.get("target_value")

        if not _check_dependencies(db, flag, new_value):
            errors.append(f"Нельзя включить {flag_key}: зависимости не выполнены")
            continue

        flag.target_value = new_value
        flag.changed_by = data.changed_by
        updated += 1

        _log_audit(db, flag.id, "BULK_UPDATE", old_value, new_value, data.changed_by)

        # Инвалидируем кэш
        r = get_redis()
        r.delete(_cache_key(flag.flag_key))

    db.commit()
    return {"updated": updated, "errors": errors}

@router.get("/{flag_id}/audit", response_model=List[FeatureFlagAuditResponse], tags=["Feature Flags"])
def get_audit(flag_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """История изменений флага."""
    return db.query(FeatureFlagAudit).filter(FeatureFlagAudit.flag_id == flag_id).order_by(FeatureFlagAudit.created_at.desc()).all()

@router.get("/{flag_id}/dependencies", tags=["Feature Flags"])
def get_dependencies(flag_id: int, db: Session = Depends(get_db)):
    """Получение зависимостей флага."""
    flag = db.query(FeatureFlag).filter(FeatureFlag.id == flag_id).first()
    if not flag:
        raise HTTPException(status_code=404, detail="Флаг не найден")

    deps = db.query(FeatureFlagDependency).filter(FeatureFlagDependency.flag_id == flag_id).all()
    return {
        "flag": flag.flag_key,
        "requires": [
            {
                "flag_id": d.requires_flag_id,
                "flag_key": db.query(FeatureFlag).filter(FeatureFlag.id == d.requires_flag_id).first().flag_key
            }
            for d in deps
        ]
    }

@router.post("/{flag_id}/dependencies", tags=["Feature Flags"])
def add_dependency(
    flag_id: int,
    requires_flag_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(require_roles("SUPER_ADMIN"))
):
    """Добавление зависимости (только SuperAdmin)."""
    flag = db.query(FeatureFlag).filter(FeatureFlag.id == flag_id).first()
    required = db.query(FeatureFlag).filter(FeatureFlag.id == requires_flag_id).first()

    if not flag or not required:
        raise HTTPException(status_code=404, detail="Флаг не найден")

    # Проверка циклических зависимостей
    existing = db.query(FeatureFlagDependency).filter(
        FeatureFlagDependency.flag_id == requires_flag_id,
        FeatureFlagDependency.requires_flag_id == flag_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Циклическая зависимость обнаружена")

    dep = FeatureFlagDependency(flag_id=flag_id, requires_flag_id=requires_flag_id)
    db.add(dep)
    db.commit()

    return {"detail": f"Флаг {flag.flag_key} теперь требует {required.flag_key}"}
