# app/api/v1/access_cache.py

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.db.session import get_db
from app.schemas.access_cache import (
    AccessCacheSyncRequest,
    AccessCacheSyncResponse,
)
from app.services.access_cache_service import AccessCacheService


router = APIRouter(prefix="/access/cache", tags=["Access Cache"])


# ==========================================================
# СИНХРОНИЗАЦИЯ КЭША (ДЛЯ ТЕРМИНАЛОВ)
# ==========================================================

@router.post(
    "/sync",
    response_model=AccessCacheSyncResponse,
    status_code=status.HTTP_200_OK,
)
def sync_cache(
    payload: AccessCacheSyncRequest,
    db: Session = Depends(get_db),
):
    """
    Синхронизировать кэш для терминала/турникета.
    
    - Используется для офлайн-режима
    - Возвращает обновления кэша
    - Терминал скачивает кэш и использует при потере интернета
    """
    service = AccessCacheService(db)
    return service.sync_cache(
        device_id=payload.device_id,
        last_cache_version=payload.last_cache_version,
    )


@router.post(
    "/invalidate/client/{client_id}",
    status_code=status.HTTP_200_OK,
)
def invalidate_client_cache(
    client_id: str,
    current_user=Depends(require_permission("access.cache.manage")),
    db: Session = Depends(get_db),
):
    """
    Инвалидировать кэш клиента.
    
    - Используется при изменении прав доступа
    - После этого терминалы обновят кэш
    """
    service = AccessCacheService(db)
    count = service.invalidate_cache_by_client(client_id)
    
    return {
        "success": True,
        "invalidated_count": count,
        "message": f"Cache invalidated for client {client_id}",
    }


@router.post(
    "/refresh-all",
    status_code=status.HTTP_200_OK,
)
def refresh_all_caches(
    current_user=Depends(require_permission("access.cache.manage")),
    db: Session = Depends(get_db),
):
    """
    Принудительно обновить кэш для всех устройств.
    
    - Используется при массовых изменениях
    - Может быть ресурсоёмкой операцией
    """
    service = AccessCacheService(db)
    count = service.refresh_all_caches()
    
    return {
        "success": True,
        "items_count": count,
        "message": f"All caches refreshed, {count} items created",
    }