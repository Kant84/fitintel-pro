# app/services/qr_service.py

import io
import base64
import secrets
import hashlib
from datetime import datetime, timedelta, date
from typing import Optional, Tuple
from uuid import UUID
import qrcode
from qrcode.constants import ERROR_CORRECT_M
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.credential import Credential
from app.models.client import Client
from app.repositories.credential_repository import CredentialRepository
from app.services.audit_service import AuditService


class QRService:
    """
    Сервис для генерации и управления QR-кодами.
    
    Поддерживает:
    - Генерацию QR-кодов для клиентов
    - Создание JWT-токенов для QR
    - Валидацию QR-кодов при доступе
    - Отображение QR-кода в личном кабинете
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.credential_repo = CredentialRepository(db)
        self.audit = AuditService(db)
    
    # ==========================================================
    # ГЕНЕРАЦИЯ QR-КОДА
    # ==========================================================
    
    def generate_qr_value(self, client_id: str, version: str = "v2") -> str:
        """
        Сгенерировать уникальное значение для QR-кода.
        
        Форматы:
        - v1: UUID (простой)
        - v2: JWT с подписью (безопасный)
        """
        if version == "v1":
            # Простой UUID
            import uuid
            return str(uuid.uuid4())
        
        # v2: JWT-like с подписью
        # Формат: {client_id}:{expires}:{signature}
        expires = (datetime.now() + timedelta(days=365)).timestamp()
        data = f"{client_id}:{int(expires)}"
        signature = hashlib.sha256(
            f"{data}:{settings.SECRET_KEY}".encode()
        ).hexdigest()[:32]
        
        return f"{data}:{signature}"
    
    def create_qr_credential(
        self,
        client_id: str,
        valid_until: date | None = None,
        qr_version: str = "v2",
        issued_by_user_id: str | None = None,
    ) -> Credential:
        """
        Создать QR-код для клиента.
        
        Args:
            client_id: ID клиента
            valid_until: Дата окончания действия (по умолчанию 1 год)
            qr_version: Версия QR-кода (v1, v2)
            issued_by_user_id: Кто выдал
        
        Returns:
            Созданные учётные данные с QR-кодом
        """
        # Проверяем существование клиента
        client = self.db.query(Client).filter(Client.id == client_id).first()
        if not client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Клиент не найден"
            )
        
        # Если не указана дата окончания — 1 год
        if valid_until is None:
            valid_until = date.today() + timedelta(days=365)
        
        # Генерируем значение QR-кода
        qr_value = self.generate_qr_value(client_id, qr_version)
        
        # Создаём учётные данные
        credential = Credential(
            client_id=client_id,
            credential_type="QR",
            credential_value=qr_value,
            status="ACTIVE",
            valid_from=date.today(),
            valid_until=valid_until,
            qr_version=qr_version,
            qr_format="jwt" if qr_version == "v2" else "uuid",
            issued_by_user_id=issued_by_user_id,
            issued_at=datetime.now(),
        )
        
        created = self.credential_repo.add(credential)
        
        # Логируем
        self.audit.log(
            action="qr.created",
            status="success",
            actor_user_id=issued_by_user_id,
            entity_type="credential",
            entity_id=created.id,
            message=f"QR code created for client {client_id}",
            after_data={
                "client_id": client_id,
                "client_name": f"{client.first_name} {client.last_name}",
                "valid_until": str(valid_until),
            },
        )
        
        return created
    
    def generate_qr_image(self, credential_value: str) -> str:
        """
        Сгенерировать QR-код в формате base64 (для отображения).
        
        Returns:
            base64-строка изображения QR-кода
        """
        qr = qrcode.QRCode(
            version=1,
            error_correction=ERROR_CORRECT_M,
            box_size=4,
            border=2,
        )
        qr.add_data(credential_value)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Конвертируем в base64
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        
        return base64.b64encode(buffer.getvalue()).decode()
    
    # ==========================================================
    # ВАЛИДАЦИЯ QR-КОДА
    # ==========================================================
    
    def validate_qr(self, qr_value: str) -> Tuple[bool, str | None, str | None]:
        """
        Проверить валидность QR-кода.
        
        Returns:
            (is_valid, client_id, reason)
        """
        # Ищем в БД
        credential = self.credential_repo.get_by_value(qr_value)
        
        if not credential:
            return False, None, "QR-код не найден"
        
        if credential.credential_type != "QR":
            return False, None, "Неверный тип учётных данных"
        
        if credential.status != "ACTIVE":
            return False, None, f"QR-код {credential.status}"
        
        # Проверяем срок действия
        today = date.today()
        if credential.valid_from > today:
            return False, None, "QR-код ещё не активен"
        
        if credential.valid_until and credential.valid_until < today:
            return False, None, "QR-код просрочен"
        
        # Для v2 проверяем подпись
        if credential.qr_version == "v2":
            try:
                parts = qr_value.split(":")
                if len(parts) == 3:
                    _, expires_str, signature = parts
                    expires = float(expires_str)
                    
                    # Проверяем срок действия токена
                    if expires < datetime.now().timestamp():
                        return False, None, "QR-код просрочен"
                    
                    # Проверяем подпись
                    expected = hashlib.sha256(
                        f"{parts[0]}:{parts[1]}:{settings.SECRET_KEY}".encode()
                    ).hexdigest()[:32]
                    
                    if signature != expected:
                        return False, None, "Неверная подпись QR-кода"
            except Exception:
                return False, None, "Неверный формат QR-кода"
        
        return True, credential.client_id, None
    
    # ==========================================================
    # ОТОБРАЖЕНИЕ QR-КОДА
    # ==========================================================
    
    def get_client_qr(self, client_id: str) -> dict | None:
        """
        Получить активный QR-код клиента.
        
        Returns:
            Словарь с QR-кодом и изображением
        """
        credentials = self.credential_repo.get_active_by_client(client_id)
        
        qr_credentials = [c for c in credentials if c.credential_type == "QR"]
        
        if not qr_credentials:
            return None
        
        qr = qr_credentials[0]
        
        return {
            "id": qr.id,
            "value": qr.credential_value,
            "image_base64": self.generate_qr_image(qr.credential_value),
            "valid_from": qr.valid_from,
            "valid_until": qr.valid_until,
            "created_at": qr.created_at,
        }
    
    def regenerate_qr(self, client_id: str, issued_by_user_id: str | None = None) -> Credential:
        """
        Перевыпустить QR-код (заблокировать старый, создать новый).
        
        Args:
            client_id: ID клиента
            issued_by_user_id: Кто перевыпустил
        
        Returns:
            Новый QR-код
        """
        # Блокируем старые QR-коды
        old_qrs = self.db.query(Credential).filter(
            Credential.client_id == client_id,
            Credential.credential_type == "QR",
            Credential.status == "ACTIVE",
        ).all()
        
        for old in old_qrs:
            old.status = "BLOCKED"
            old.notes = f"Перевыпущен пользователем {issued_by_user_id}"
        
        # Создаём новый
        new_qr = self.create_qr_credential(
            client_id=client_id,
            issued_by_user_id=issued_by_user_id,
        )
        
        self.db.commit()
        
        self.audit.log(
            action="qr.regenerated",
            status="success",
            actor_user_id=issued_by_user_id,
            entity_type="credential",
            entity_id=new_qr.id,
            message=f"QR code regenerated for client {client_id}",
        )
        
        return new_qr
    
    # ==========================================================
    # QR-КОД ДЛЯ ГОСТЯ (ВРЕМЕННЫЙ)
    # ==========================================================
    
    def create_guest_qr(
        self,
        client_id: str,
        valid_hours: int = 24,
        issued_by_user_id: str | None = None,
    ) -> Credential:
        """
        Создать временный QR-код для гостя.
        
        Args:
            client_id: ID клиента (гостя)
            valid_hours: Срок действия в часах
            issued_by_user_id: Кто выдал
        
        Returns:
            Временный QR-код
        """
        valid_until = date.today() + timedelta(hours=valid_hours)
        
        credential = Credential(
            client_id=client_id,
            credential_type="QR",
            credential_value=self.generate_qr_value(client_id, "v2"),
            status="ACTIVE",
            valid_from=date.today(),
            valid_until=valid_until,
            qr_version="v2",
            qr_format="jwt",
            issued_by_user_id=issued_by_user_id,
            issued_at=datetime.now(),
            notes=f"Гостевой доступ на {valid_hours} часов",
        )
        
        created = self.credential_repo.add(credential)
        
        self.audit.log(
            action="qr.guest_created",
            status="success",
            actor_user_id=issued_by_user_id,
            entity_type="credential",
            entity_id=created.id,
            message=f"Guest QR code created for client {client_id}, valid for {valid_hours}h",
        )
        
        return created