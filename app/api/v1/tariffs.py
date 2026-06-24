# app/api/v1/tariffs.py

# импорт UUID
from uuid import UUID

# импорт FastAPI
from fastapi import APIRouter, Depends, Query, status

# импорт Session
from sqlalchemy.orm import Session

# импорт зависимостей
from app.api.dependencies import require_permission

# импорт get_db
from app.db.session import get_db

# импорт схем тарифов
from app.schemas.tariff import (
    TariffCreateRequest,
    TariffListResponse,
    TariffResponse,
    TariffUpdateRequest,
)

# импорт сервиса тарифов
from app.services.tariff_service import TariffService


# создаём роутер tariffs
router = APIRouter(prefix="/tariffs", tags=["Tariffs"])


# список тарифов
@router.get("/", response_model=TariffListResponse)
def list_tariffs(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    current_user=Depends(require_permission("tariffs.read")),
    db: Session = Depends(get_db),
):
    # создаём сервис
    tariff_service = TariffService(db)

    # получаем список
    tariffs = tariff_service.list_tariffs(
        offset=offset,
        limit=limit,
        actor_user_id=current_user.id,
    )

    # возвращаем ответ
    return tariff_service.build_tariff_list_response(tariffs)


# получить тариф по id
@router.get("/{tariff_id}", response_model=TariffResponse)
def get_tariff_by_id(
    tariff_id: UUID,
    current_user=Depends(require_permission("tariffs.read")),
    db: Session = Depends(get_db),
):
    # создаём сервис
    tariff_service = TariffService(db)

    # получаем тариф
    tariff = tariff_service.get_tariff_by_id(str(tariff_id))

    # пишем аудит чтения
    tariff_service.audit.log(
        action="crm.tariff.read",
        status="success",
        actor_user_id=current_user.id,
        entity_type="tariff",
        entity_id=tariff.id,
        message="Tariff card requested",
        after_data={
            "tariff_id": tariff.id,
        },
    )

    # возвращаем ответ
    return tariff_service.build_tariff_response(tariff)


# создать тариф
@router.post("/", response_model=TariffResponse, status_code=status.HTTP_201_CREATED)
def create_tariff(
    payload: TariffCreateRequest,
    current_user=Depends(require_permission("tariffs.create")),
    db: Session = Depends(get_db),
):
    # создаём сервис
    tariff_service = TariffService(db)

    # создаём тариф
    tariff = tariff_service.create_tariff(
        code=payload.code,
        name=payload.name,
        description=payload.description,
        price=payload.price,
        currency=payload.currency,
        duration_days=payload.duration_days,
        visit_limit=payload.visit_limit,
        is_unlimited=payload.is_unlimited,
        is_active=payload.is_active,
        promo_code=payload.promo_code,
        discount_percent=payload.discount_percent,
        time_restriction_type=payload.time_restriction_type,
        allowed_start_time=payload.allowed_start_time,
        allowed_end_time=payload.allowed_end_time,
        actor_user_id=current_user.id,
    )

    # возвращаем ответ
    return tariff_service.build_tariff_response(tariff)


# обновить тариф
@router.patch("/{tariff_id}", response_model=TariffResponse)
def update_tariff(
    tariff_id: UUID,
    payload: TariffUpdateRequest,
    current_user=Depends(require_permission("tariffs.update")),
    db: Session = Depends(get_db),
):
    # создаём сервис
    tariff_service = TariffService(db)

    # обновляем тариф
    tariff = tariff_service.update_tariff(
        tariff_id=str(tariff_id),
        code=payload.code,
        name=payload.name,
        description=payload.description,
        price=payload.price,
        currency=payload.currency,
        duration_days=payload.duration_days,
        visit_limit=payload.visit_limit,
        is_unlimited=payload.is_unlimited,
        is_active=payload.is_active,
        actor_user_id=current_user.id,
    )

    # возвращаем ответ
    return tariff_service.build_tariff_response(tariff)


# ============================================================
# Удаление тарифа
# ============================================================
@router.delete("/{tariff_id}")
def delete_tariff(
    tariff_id: UUID,
    current_user=Depends(require_permission("tariffs.delete")),
    db: Session = Depends(get_db),
):
    """Удаление тарифа"""
    tariff_service = TariffService(db)
    tariff = tariff_service.get_tariff_by_id(str(tariff_id))
    if not tariff:
        raise HTTPException(status_code=404, detail="Тариф не найден")
    tariff_service.delete_tariff(tariff)
    return {"message": "Тариф удалён"}


