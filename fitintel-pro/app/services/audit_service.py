# app/services/audit_service.py

# Импорт UUID для типизации идентификаторов.
from uuid import UUID

# Импорт datetime для сериализации дат.
from datetime import datetime, date

# Импорт Any для универсальных словарей.
from typing import Any

# Импорт Session для работы с SQLAlchemy.
from sqlalchemy.orm import Session

# Импорт ORM-модели журнала аудита.
from app.models.audit import AuditLog


class AuditService:
    """
    Сервис аудита.

    Используется для записи событий в таблицу audit_logs.

    Поддерживает:
    - универсальный метод log(...)
    - низкоуровневый метод log_event(...)
    - специальные методы для RBAC-операций
    - безопасную сериализацию UUID / datetime / вложенных структур
      перед записью в JSON-поля before_data / after_data
    """

    def __init__(self, db: Session):
        # Сохраняем текущую сессию БД.
        self.db = db

    # ============================================================
    # ВСПОМОГАТЕЛЬНАЯ СЕРИАЛИЗАЦИЯ ДАННЫХ ДЛЯ JSON
    # ============================================================

    def _make_json_safe(self, value: Any) -> Any:
        """
        Рекурсивно преобразует данные в JSON-совместимый вид.

        Что делает:
        - UUID -> str
        - datetime/date -> isoformat()
        - dict -> рекурсивно обрабатывает ключи и значения
        - list/tuple/set -> рекурсивно обрабатывает элементы
        - остальные JSON-совместимые типы оставляет как есть
        - неизвестные объекты преобразует в str(...)
        """

        # Если значение None, bool, int, float или str — возвращаем как есть.
        if value is None or isinstance(value, (bool, int, float, str)):
            return value

        # UUID преобразуем в строку.
        if isinstance(value, UUID):
            return str(value)

        # datetime и date преобразуем в ISO-строку.
        if isinstance(value, (datetime, date)):
            return value.isoformat()

        # Словарь обрабатываем рекурсивно.
        if isinstance(value, dict):
            return {
                str(self._make_json_safe(key)): self._make_json_safe(item)
                for key, item in value.items()
            }

        # Списки, кортежи и множества обрабатываем рекурсивно.
        if isinstance(value, (list, tuple, set)):
            return [self._make_json_safe(item) for item in value]

        # Всё остальное приводим к строке.
        return str(value)

    # ============================================================
    # БАЗОВОЕ ЛОГИРОВАНИЕ
    # ============================================================

    def log(
        self,
        *,
        action: str,
        status: str,
        message: str | None = None,
        actor_user_id: UUID | None = None,
        entity_type: str | None = None,
        entity_id: UUID | None = None,
        target_user_id: UUID | None = None,
        role_id: UUID | None = None,
        permission_id: UUID | None = None,
        before_data: dict[str, Any] | None = None,
        after_data: dict[str, Any] | None = None,
    ) -> AuditLog:
        """
        Универсальный совместимый метод аудита.

        Этот метод нужен для новых сервисов, где вызывается:
            self.audit.log(...)

        Если entity_type не передан явно, он будет определён автоматически.
        """

        # Если entity_type не передали явно, пытаемся определить его автоматически.
        if entity_type is None:
            # Если операция связана с ролью или передан role_id.
            if role_id is not None or "role" in action:
                entity_type = "role"

            # Если операция связана с permission или передан permission_id.
            elif permission_id is not None or "permission" in action:
                entity_type = "permission"

            # Если операция связана с пользователем или передан target_user_id.
            elif target_user_id is not None or "user" in action:
                entity_type = "user"

            # Иначе ставим общий тип.
            else:
                entity_type = "system"

        # Если entity_id не передан, пробуем подставить наиболее логичный ID.
        if entity_id is None:
            if role_id is not None:
                entity_id = role_id
            elif permission_id is not None:
                entity_id = permission_id
            elif target_user_id is not None:
                entity_id = target_user_id

        # Делаем before_data безопасным для JSON.
        safe_before_data = self._make_json_safe(before_data)

        # Делаем after_data безопасным для JSON.
        safe_after_data = self._make_json_safe(after_data)

        # Передаём всё в базовый метод записи.
        return self.log_event(
            actor_user_id=actor_user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            target_user_id=target_user_id,
            role_id=role_id,
            permission_id=permission_id,
            status=status,
            message=message,
            before_data=safe_before_data,
            after_data=safe_after_data,
        )

    def log_event(
        self,
        *,
        actor_user_id: UUID | None,
        action: str,
        entity_type: str,
        status: str,
        entity_id: UUID | None = None,
        target_user_id: UUID | None = None,
        role_id: UUID | None = None,
        permission_id: UUID | None = None,
        message: str | None = None,
        before_data: dict[str, Any] | None = None,
        after_data: dict[str, Any] | None = None,
    ) -> AuditLog:
        """
        Универсальный метод записи события в аудит.
        """

        # Создаём объект записи аудита.
        audit_log = AuditLog(
            actor_user_id=actor_user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            target_user_id=target_user_id,
            role_id=role_id,
            permission_id=permission_id,
            status=status,
            message=message,
            before_data=before_data,
            after_data=after_data,
        )

        # Добавляем запись в сессию.
        self.db.add(audit_log)

        # Сохраняем запись сразу.
        self.db.commit()

        # Обновляем объект из БД.
        self.db.refresh(audit_log)

        # Возвращаем созданную запись.
        return audit_log

    # ============================================================
    # СПЕЦИАЛЬНЫЕ МЕТОДЫ АУДИТА
    # ============================================================

    def log_rbac_error(
        self,
        *,
        actor_user_id: UUID | None,
        action: str,
        entity_type: str,
        message: str,
        entity_id: UUID | None = None,
        target_user_id: UUID | None = None,
        role_id: UUID | None = None,
        permission_id: UUID | None = None,
        before_data: dict[str, Any] | None = None,
        after_data: dict[str, Any] | None = None,
    ) -> AuditLog:
        """
        Логирует ошибку RBAC-операции.
        """

        return self.log_event(
            actor_user_id=actor_user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            target_user_id=target_user_id,
            role_id=role_id,
            permission_id=permission_id,
            status="error",
            message=message,
            before_data=self._make_json_safe(before_data),
            after_data=self._make_json_safe(after_data),
        )

    def log_rbac_denied_action(
        self,
        *,
        actor_user_id: UUID | None,
        action: str,
        entity_type: str,
        message: str,
        entity_id: UUID | None = None,
        target_user_id: UUID | None = None,
        role_id: UUID | None = None,
        permission_id: UUID | None = None,
        before_data: dict[str, Any] | None = None,
        after_data: dict[str, Any] | None = None,
    ) -> AuditLog:
        """
        Логирует запрещённую RBAC-операцию.
        """

        return self.log_event(
            actor_user_id=actor_user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            target_user_id=target_user_id,
            role_id=role_id,
            permission_id=permission_id,
            status="denied",
            message=message,
            before_data=self._make_json_safe(before_data),
            after_data=self._make_json_safe(after_data),
        )

    def log_rbac_role_assigned(
        self,
        *,
        actor_user_id: UUID,
        target_user_id: UUID,
        role_id: UUID,
        user_role_id: UUID | None = None,
        message: str = "Role assigned successfully",
    ) -> AuditLog:
        """
        Логирует успешное назначение роли пользователю.
        """

        return self.log_event(
            actor_user_id=actor_user_id,
            action="rbac.role.assigned",
            entity_type="user_role",
            entity_id=user_role_id,
            target_user_id=target_user_id,
            role_id=role_id,
            status="success",
            message=message,
            after_data=self._make_json_safe(
                {
                    "target_user_id": target_user_id,
                    "role_id": role_id,
                }
            ),
        )

    def log_rbac_role_revoked(
        self,
        *,
        actor_user_id: UUID,
        target_user_id: UUID,
        role_id: UUID,
        message: str = "Role revoked successfully",
        before_data: dict[str, Any] | None = None,
    ) -> AuditLog:
        """
        Логирует успешное снятие роли у пользователя.
        """

        return self.log_event(
            actor_user_id=actor_user_id,
            action="rbac.role.revoked",
            entity_type="user_role",
            target_user_id=target_user_id,
            role_id=role_id,
            status="success",
            message=message,
            before_data=self._make_json_safe(before_data),
        )

    def log_access_check(
        self,
        *,
        actor_user_id: UUID | None,
        permission_code: str,
        result: dict,
    ) -> AuditLog:
        """
        Логирует проверку доступа.
        """

        return self.log(
            action="access.check",
            status="success" if result["has_access"] else "denied",
            actor_user_id=actor_user_id,
            message=result.get("reason"),
            after_data={
                "permission_code": permission_code,
                **self._make_json_safe(result),
            },
        )