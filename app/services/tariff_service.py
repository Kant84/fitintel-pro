# app/services/tariff_service.py

# импорт Decimal
from decimal import Decimal

# импорт HTTPException и status
from fastapi import HTTPException, status

# импорт Session
from sqlalchemy.orm import Session

# импорт модели тарифа
from app.models.tariff import Tariff

# импорт репозитория тарифа
from app.repositories.tariff_repository import TariffRepository

# импорт сервиса аудита
from app.services.audit_service import AuditService

# импорт нормализации текста
from app.utils.validators import normalize_text


# допустимые валюты на текущем этапе
ALLOWED_CURRENCIES = {"RUB"}


class TariffService:
    # конструктор принимает сессию БД
    def __init__(self, db: Session) -> None:
        # сохраняем сессию
        self.db = db

        # создаём репозиторий тарифов
        self.tariff_repository = TariffRepository(db)

        # создаём сервис аудита
        self.audit = AuditService(db)

    # нормализуем code тарифа
    def normalize_code(self, code: str) -> str:
        # убираем пробелы по краям
        normalized = code.strip().upper()

        # если код пустой — ошибка
        if not normalized:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Код тарифа не может быть пустым",
            )

        # возвращаем код
        return normalized

    # нормализуем name тарифа
    def normalize_name(self, name: str) -> str:
        # используем общую нормализацию текста
        return normalize_text(name)

    # нормализуем валюту
    def normalize_currency(self, currency: str) -> str:
        # убираем пробелы и переводим в верхний регистр
        normalized = currency.strip().upper()

        # если валюта пустая — ошибка
        if not normalized:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Валюта не может быть пустой",
            )

        # если валюта не разрешена — ошибка
        if normalized not in ALLOWED_CURRENCIES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Недопустимая валюта. Разрешено: RUB",
            )

        # возвращаем валюту
        return normalized

    # проверяем цену
    def validate_price(self, price: Decimal) -> Decimal:
        # если цена меньше или равна нулю — ошибка
        if price <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Цена тарифа должна быть больше 0",
            )

        # возвращаем цену
        return price

    # проверяем длительность
    def validate_duration_days(self, duration_days: int) -> int:
        # если длительность меньше или равна нулю — ошибка
        if duration_days <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Срок действия тарифа должен быть больше 0 дней",
            )

        # возвращаем длительность
        return duration_days

    # проверяем связку is_unlimited и visit_limit
    def resolve_visit_logic(
        self,
        *,
        is_unlimited: bool,
        visit_limit: int | None,
    ) -> tuple[bool, int | None]:
        # если тариф безлимитный — visit_limit должен быть None
        if is_unlimited:
            return True, None

        # если тариф не безлимитный, visit_limit обязателен
        if visit_limit is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Для не безлимитного тарифа visit_limit обязателен",
            )

        # если лимит <= 0 — ошибка
        if visit_limit <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="visit_limit должен быть больше 0",
            )

        # возвращаем итоговые значения
        return False, visit_limit

    # получить тариф по id
    def get_tariff_by_id(self, tariff_id: str) -> Tariff:
        # ищем тариф
        tariff = self.tariff_repository.get_by_id(tariff_id)

        # если не найден — 404
        if tariff is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Тариф не найден",
            )

        # возвращаем тариф
        return tariff

    # список тарифов
    def list_tariffs(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
        actor_user_id=None,
    ) -> list[Tariff]:
        # получаем список
        tariffs = self.tariff_repository.list_tariffs(
            offset=offset,
            limit=limit,
        )

        # пишем аудит
        self.audit.log(
            action="crm.tariff.list",
            status="success",
            actor_user_id=actor_user_id,
            entity_type="tariff",
            message="Tariff list requested",
            after_data={
                "offset": offset,
                "limit": limit,
                "count": len(tariffs),
            },
        )

        # возвращаем список
        return tariffs

    # создать тариф
    def create_tariff(
        self,
        *,
        code: str,
        name: str,
        description: str | None,
        price: Decimal,
        currency: str,
        duration_days: int,
        visit_limit: int | None,
        is_unlimited: bool,
        is_active: bool,
        promo_code: str | None = None,
        discount_percent: int | None = 0,
        time_restriction_type: str | None = None,
        allowed_start_time=None,
        allowed_end_time=None,
        actor_user_id=None,
    ) -> Tariff:
        # нормализуем код
        normalized_code = self.normalize_code(code)

        # нормализуем имя
        normalized_name = self.normalize_name(name)

        # нормализуем описание, если оно есть
        normalized_description = normalize_text(description) if description else None

        # валидируем цену
        validated_price = self.validate_price(price)

        # валидируем валюту
        normalized_currency = self.normalize_currency(currency)

        # валидируем длительность
        validated_duration_days = self.validate_duration_days(duration_days)

        # нормализуем логику посещений
        resolved_is_unlimited, resolved_visit_limit = self.resolve_visit_logic(
            is_unlimited=is_unlimited,
            visit_limit=visit_limit,
        )

        # проверяем уникальность code
        if self.tariff_repository.code_exists(normalized_code):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Тариф с таким code уже существует",
            )

        # проверяем уникальность name
        if self.tariff_repository.name_exists(normalized_name):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Тариф с таким name уже существует",
            )

        # создаём ORM-объект тарифа
        tariff = Tariff(
            code=normalized_code,
            name=normalized_name,
            description=normalized_description,
            price=validated_price,
            currency=normalized_currency,
            duration_days=validated_duration_days,
            visit_limit=resolved_visit_limit,
            is_unlimited=resolved_is_unlimited,
            is_active=is_active,
            promo_code=promo_code,
            discount_percent=discount_percent,
            time_restriction_type=time_restriction_type,
            allowed_start_time=allowed_start_time,
            allowed_end_time=allowed_end_time,
        )

        # сохраняем тариф
        created_tariff = self.tariff_repository.add(tariff)

        # пишем аудит
        self.audit.log(
            action="crm.tariff.created",
            status="success",
            actor_user_id=actor_user_id,
            entity_type="tariff",
            entity_id=created_tariff.id,
            message="Tariff created successfully",
            after_data={
                "id": created_tariff.id,
                "code": created_tariff.code,
                "name": created_tariff.name,
                "price": str(created_tariff.price),
                "currency": created_tariff.currency,
                "duration_days": created_tariff.duration_days,
                "visit_limit": created_tariff.visit_limit,
                "is_unlimited": created_tariff.is_unlimited,
                "time_restriction_type": created_tariff.time_restriction_type,
                "allowed_start_time": str(created_tariff.allowed_start_time) if created_tariff.allowed_start_time else None,
                "allowed_end_time": str(created_tariff.allowed_end_time) if created_tariff.allowed_end_time else None,
                "is_active": created_tariff.is_active,
                "promo_code": created_tariff.promo_code,
                "discount_percent": created_tariff.discount_percent,
            },
        )

        # возвращаем тариф
        return created_tariff

    # обновить тариф
    def update_tariff(
        self,
        *,
        tariff_id: str,
        code: str | None = None,
        name: str | None = None,
        description: str | None = None,
        price: Decimal | None = None,
        currency: str | None = None,
        duration_days: int | None = None,
        visit_limit: int | None = None,
        is_unlimited: bool | None = None,
        is_active: bool | None = None,
        actor_user_id=None,
    ) -> Tariff:
        # получаем тариф
        tariff = self.get_tariff_by_id(tariff_id)

        # сохраняем before_data
        before_data = {
            "id": tariff.id,
            "code": tariff.code,
            "name": tariff.name,
            "description": tariff.description,
            "price": str(tariff.price),
            "currency": tariff.currency,
            "duration_days": tariff.duration_days,
            "visit_limit": tariff.visit_limit,
            "is_unlimited": tariff.is_unlimited,
            "is_active": tariff.is_active,
        }

        # обновляем code
        if code is not None:
            normalized_code = self.normalize_code(code)

            if self.tariff_repository.code_exists(
                normalized_code,
                exclude_tariff_id=tariff_id,
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Тариф с таким code уже существует",
                )

            tariff.code = normalized_code

        # обновляем name
        if name is not None:
            normalized_name = self.normalize_name(name)

            if self.tariff_repository.name_exists(
                normalized_name,
                exclude_tariff_id=tariff_id,
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Тариф с таким name уже существует",
                )

            tariff.name = normalized_name

        # обновляем description
        if description is not None:
            tariff.description = normalize_text(description) if description else None

        # обновляем price
        if price is not None:
            tariff.price = self.validate_price(price)

        # обновляем currency
        if currency is not None:
            tariff.currency = self.normalize_currency(currency)

        # обновляем duration_days
        if duration_days is not None:
            tariff.duration_days = self.validate_duration_days(duration_days)

        # пересчитываем связку is_unlimited / visit_limit
        final_is_unlimited = tariff.is_unlimited if is_unlimited is None else is_unlimited
        final_visit_limit = tariff.visit_limit if visit_limit is None else visit_limit

        resolved_is_unlimited, resolved_visit_limit = self.resolve_visit_logic(
            is_unlimited=final_is_unlimited,
            visit_limit=final_visit_limit,
        )

        tariff.is_unlimited = resolved_is_unlimited
        tariff.visit_limit = resolved_visit_limit

        # обновляем is_active
        if is_active is not None:
            tariff.is_active = is_active

        # сохраняем тариф
        updated_tariff = self.tariff_repository.save(tariff)

        # пишем аудит
        self.audit.log(
            action="crm.tariff.updated",
            status="success",
            actor_user_id=actor_user_id,
            entity_type="tariff",
            entity_id=updated_tariff.id,
            message="Tariff updated successfully",
            before_data=before_data,
            after_data={
                "id": updated_tariff.id,
                "code": updated_tariff.code,
                "name": updated_tariff.name,
                "description": updated_tariff.description,
                "price": str(updated_tariff.price),
                "currency": updated_tariff.currency,
                "duration_days": updated_tariff.duration_days,
                "visit_limit": updated_tariff.visit_limit,
                "is_unlimited": updated_tariff.is_unlimited,
                "is_active": updated_tariff.is_active,
            },
        )

        # возвращаем тариф
        return updated_tariff

    # собрать response

    def delete_tariff(self, tariff):
        """Удаление тарифа"""
        self.db.delete(tariff)
        self.db.commit()

    def build_tariff_response(self, tariff: Tariff) -> dict:
        # возвращаем словарь ответа
        return {
            "id": tariff.id,
            "code": tariff.code,
            "name": tariff.name,
            "description": tariff.description,
            "price": tariff.price,
            "currency": tariff.currency,
            "duration_days": tariff.duration_days,
            "visit_limit": tariff.visit_limit,
            "is_unlimited": tariff.is_unlimited,
            "is_active": tariff.is_active,
            "promo_code": tariff.promo_code,
            "discount_percent": tariff.discount_percent,
            "created_at": tariff.created_at,
            "updated_at": tariff.updated_at,
        }

    # собрать response списка
    def build_tariff_list_response(self, tariffs: list[Tariff]) -> dict:
        # собираем элементы
        items = [self.build_tariff_response(tariff) for tariff in tariffs]

        # возвращаем структуру
        return {
            "items": items,
            "count": len(items),
        }