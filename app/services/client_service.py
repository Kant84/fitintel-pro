# app/services/client_service.py

# импорт HTTPException и status для возврата API-ошибок
from fastapi import HTTPException, status

# импорт Session для работы с SQLAlchemy
from sqlalchemy.orm import Session

# импорт модели клиента
from app.models.client import Client

# импорт репозитория клиентов
from app.repositories.client_repository import ClientRepository

# импорт сервиса аудита
from app.services.audit_service import AuditService

# импорт сервиса истории клиента
from app.services.client_history_service import ClientHistoryService

from datetime import date

# импорт утилит валидации
from app.utils.validators import (
    normalize_email,
    normalize_text,
    validate_phone,
)


# допустимые статусы клиента
CLIENT_STATUSES = {
    "ACTIVE",
    "INACTIVE",
    "BLOCKED",
}


# сервис клиентов
class ClientService:
    # конструктор принимает сессию БД
    def __init__(self, db: Session) -> None:
        # сохраняем сессию
        self.db = db

        # создаём репозиторий клиентов
        self.client_repository = ClientRepository(db)

        # создаём сервис аудита
        self.audit = AuditService(db)

        # создаём сервис истории клиента
        self.history_service = ClientHistoryService(db)

    # ============================================================
    # ВСПОМОГАТЕЛЬНАЯ ЛОГИКА
    # ============================================================

    # метод нормализует и проверяет статус клиента
    def normalize_status(self, status_value: str | None) -> str:
        # если статус не передан — используем ACTIVE
        if status_value is None:
            return "ACTIVE"

        # убираем пробелы и переводим статус в верхний регистр
        normalized = status_value.strip().upper()

        # если статус пустой — ошибка
        if not normalized:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Статус клиента не может быть пустым",
            )

        # если статус неизвестен — ошибка
        if normalized not in CLIENT_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Недопустимый статус клиента. Допустимые значения: ACTIVE, INACTIVE, BLOCKED",
            )

        # возвращаем нормализованный статус
        return normalized

    # метод вычисляет флаг is_active из статуса
    def status_to_is_active(self, client_status: str) -> bool:
        # только ACTIVE считается активным состоянием
        return client_status == "ACTIVE"

    # метод приводит и проверяет обязательные поля клиента
    def normalize_client_fields(
        self,
        *,
        first_name: str,
        last_name: str,
        phone: str,
        email: str,
    ) -> dict:
        # очищаем имя
        clean_first_name = normalize_text(first_name)

        # очищаем фамилию
        clean_last_name = normalize_text(last_name)

        # нормализуем телефон
        clean_phone = validate_phone(phone)

        # нормализуем email
        clean_email = normalize_email(email)

        # возвращаем готовые значения
        return {
            "first_name": clean_first_name,
            "last_name": clean_last_name,
            "phone": clean_phone,
            "email": clean_email,
        }

    # метод решает итоговую пару status + is_active при создании
    def resolve_create_status_and_activity(
        self,
        *,
        status_value: str | None,
        is_active: bool | None,
    ) -> tuple[str, bool]:
        # если статус явно передан — он главный
        if status_value is not None:
            normalized_status = self.normalize_status(status_value)
            return normalized_status, self.status_to_is_active(normalized_status)

        # если статус не передан, но передан is_active=False,
        # создаём клиента как INACTIVE
        if is_active is False:
            return "INACTIVE", False

        # по умолчанию создаём ACTIVE
        return "ACTIVE", True

    # метод решает итоговую пару status + is_active при обновлении
    def resolve_update_status_and_activity(
        self,
        *,
        current_status: str,
        current_is_active: bool,
        new_status: str | None,
        new_is_active: bool | None,
    ) -> tuple[str, bool]:
        # если статус передан — он главный
        if new_status is not None:
            normalized_status = self.normalize_status(new_status)
            return normalized_status, self.status_to_is_active(normalized_status)

        # если status не передали, но передали is_active
        if new_is_active is not None:
            # активируем клиента
            if new_is_active is True:
                return "ACTIVE", True

            # если клиент уже был BLOCKED — сохраняем BLOCKED
            if current_status == "BLOCKED":
                return "BLOCKED", False

            # иначе ставим INACTIVE
            return "INACTIVE", False

        # если ничего не передали — оставляем как есть
        return current_status, current_is_active

    # ============================================================
    # ЧТЕНИЕ
    # ============================================================

    # метод получает клиента по id
    def get_client_by_id(self, client_id: str) -> Client:
        # ищем клиента
        client = self.client_repository.get_by_id(client_id)

        # если клиент не найден — 404
        if client is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Клиент не найден",
            )

        # возвращаем клиента
        return client

    # метод возвращает список клиентов
    def list_clients(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
        actor_user_id=None,
    ) -> list[Client]:
        # получаем список клиентов
        clients = self.client_repository.list_clients(
            offset=offset,
            limit=limit,
        )

        # пишем audit о чтении списка
        self.audit.log(
            action="crm.client.list",
            status="success",
            actor_user_id=actor_user_id,
            entity_type="client",
            message="Client list requested",
            after_data={
                "offset": offset,
                "limit": limit,
                "count": len(clients),
            },
        )

        # возвращаем список
        return clients

    # ============================================================
    # СОЗДАНИЕ
    # ============================================================

    # метод создаёт клиента
    def create_client(
        self,
        *,
        first_name: str,
        last_name: str,
        phone: str,
        email: str,
        middle_name: str | None = None,
        gender: str | None = None,
        birth_date: date | None = None,
        client_category: str | None = None,
        status_value: str | None = None,
        is_active: bool | None = None,
        actor_user_id=None,
    ) -> Client:
        # нормализуем поля клиента
        normalized_fields = self.normalize_client_fields(
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            email=email,
        )

        # вычисляем финальные status и is_active
        resolved_status, resolved_is_active = self.resolve_create_status_and_activity(
            status_value=status_value,
            is_active=is_active,
        )

        # проверяем уникальность email
        if self.client_repository.email_exists(normalized_fields["email"]):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Клиент с таким email уже существует",
            )

        # проверяем уникальность телефона
        if self.client_repository.phone_exists(normalized_fields["phone"]):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Клиент с таким телефоном уже существует",
            )

        # создаём ORM-объект клиента
        client = Client(
            first_name=normalized_fields["first_name"],
            last_name=normalized_fields["last_name"],
            middle_name=middle_name,
            phone=normalized_fields["phone"],
            email=normalized_fields["email"],
            gender=gender or "НЕ_УКАЗАН",
            birth_date=birth_date,
            client_category=client_category or "НЕ_УКАЗАНА",
            status=resolved_status,
            is_active=resolved_is_active,
        )

        # сохраняем клиента
        created_client = self.client_repository.add(client)

        # ✅ ДОБАВЛЯЕМ СОБЫТИЕ В TIMELINE
        try:
            self.history_service.add_event(
                client_id=str(created_client.id),
                event_type="КЛИЕНТ_СОЗДАН",
                title="Клиент создан",
                description="В CRM создана новая карточка клиента",
                actor_user_id=actor_user_id,
            )
            print(f"[OK] Client history event added for client {created_client.id}")
        except Exception as e:
            print(f"[ERROR] Failed to add client history event: {e}")
            # Не прерываем выполнение, если событие не добавилось

        # пишем audit о создании
        self.audit.log(
            action="crm.client.created",
            status="success",
            actor_user_id=actor_user_id,
            entity_type="client",
            entity_id=created_client.id,
            message="Client created successfully",
            after_data={
                "id": created_client.id,
                "first_name": created_client.first_name,
                "last_name": created_client.last_name,
                "phone": created_client.phone,
                "email": created_client.email,
                "status": created_client.status,
                "is_active": created_client.is_active,
                "gender": created_client.gender,
                "client_category": created_client.client_category,
            },
        )

        # возвращаем созданного клиента
        return created_client

    # ============================================================
    # ОБНОВЛЕНИЕ
    # ============================================================

    # метод обновляет клиента
    def update_client(
        self,
        *,
        client_id: str,
        first_name: str | None = None,
        last_name: str | None = None,
        middle_name: str | None = None,
        phone: str | None = None,
        email: str | None = None,
        gender: str | None = None,
        birth_date: date | None = None,
        client_category: str | None = None,
        status_value: str | None = None,
        is_active: bool | None = None,
        actor_user_id=None,
    ) -> Client:
        # получаем текущего клиента
        client = self.get_client_by_id(client_id)

        # сохраняем снимок состояния до изменения
        before_data = {
            "id": client.id,
            "first_name": client.first_name,
            "last_name": client.last_name,
            "middle_name": client.middle_name,
            "phone": client.phone,
            "email": client.email,
            "gender": client.gender,
            "birth_date": str(client.birth_date) if client.birth_date else None,
            "client_category": client.client_category,
            "status": client.status,
            "is_active": client.is_active,
        }

        # если передали имя — обновляем
        if first_name is not None:
            client.first_name = normalize_text(first_name)

        # если передали фамилию — обновляем
        if last_name is not None:
            client.last_name = normalize_text(last_name)

        # если передали отчество — обновляем
        if middle_name is not None:
            client.middle_name = normalize_text(middle_name) if middle_name else None

        # если передали пол — обновляем
        if gender is not None:
            client.gender = gender

        # если передали дату рождения — обновляем
        if birth_date is not None:
            client.birth_date = birth_date

        # если передали категорию клиента — обновляем
        if client_category is not None:
            client.client_category = client_category

        # если передали телефон — нормализуем и проверяем уникальность
        if phone is not None:
            normalized_phone = validate_phone(phone)

            if self.client_repository.phone_exists(
                normalized_phone,
                exclude_client_id=client_id,
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Клиент с таким телефоном уже существует",
                )

            client.phone = normalized_phone

        # если передали email — нормализуем и проверяем уникальность
        if email is not None:
            normalized_email = normalize_email(email)

            if self.client_repository.email_exists(
                normalized_email,
                exclude_client_id=client_id,
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Клиент с таким email уже существует",
                )

            client.email = normalized_email

        # вычисляем финальные status и is_active
        resolved_status, resolved_is_active = self.resolve_update_status_and_activity(
            current_status=client.status,
            current_is_active=client.is_active,
            new_status=status_value,
            new_is_active=is_active,
        )

        # записываем итоговые значения
        client.status = resolved_status
        client.is_active = resolved_is_active

        # сохраняем клиента
        updated_client = self.client_repository.save(client)

        # ✅ ДОБАВЛЯЕМ СОБЫТИЕ В TIMELINE
        try:
            self.history_service.add_event(
                client_id=client_id,
                event_type="КЛИЕНТ_ОБНОВЛЁН",
                title="Карточка клиента обновлена",
                description="Были изменены данные клиента",
                actor_user_id=actor_user_id,
            )
            print(f"[OK] Client history event added for client {client_id} (update)")
        except Exception as e:
            print(f"[ERROR] Failed to add client history event on update: {e}")

        # пишем audit об обновлении
        self.audit.log(
            action="crm.client.updated",
            status="success",
            actor_user_id=actor_user_id,
            entity_type="client",
            entity_id=updated_client.id,
            message="Client updated successfully",
            before_data=before_data,
            after_data={
                "id": updated_client.id,
                "first_name": updated_client.first_name,
                "last_name": updated_client.last_name,
                "middle_name": updated_client.middle_name,
                "phone": updated_client.phone,
                "email": updated_client.email,
                "gender": updated_client.gender,
                "birth_date": str(updated_client.birth_date) if updated_client.birth_date else None,
                "client_category": updated_client.client_category,
                "status": updated_client.status,
                "is_active": updated_client.is_active,
            },
        )

        # возвращаем обновлённого клиента
        return updated_client

    # ============================================================
    # СБОРКА ОТВЕТА API
    # ============================================================

    # метод строит словарь ответа по одному клиенту
    def build_client_response(self, client: Client) -> dict:
        # возвращаем словарь в формате response schema
        return {
            "id": client.id,
            "first_name": client.first_name,
            "last_name": client.last_name,
            "middle_name": client.middle_name,
            "phone": client.phone,
            "email": client.email,
            "gender": client.gender,
            "birth_date": client.birth_date,
            "client_category": client.client_category,
            "status": client.status,
            "is_active": client.is_active,
            "created_at": client.created_at,
            "updated_at": client.updated_at,
        }

    # метод строит ответ для списка клиентов
    def build_client_list_response(self, clients: list[Client]) -> dict:
        # преобразуем список клиентов в список словарей
        items = [self.build_client_response(client) for client in clients]

        # возвращаем структуру списка
        return {
            "items": items,
            "count": len(items),
        }