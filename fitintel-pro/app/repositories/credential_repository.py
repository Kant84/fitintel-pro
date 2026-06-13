# app/repositories/credential_repository.py

from datetime import date, datetime
from typing import Optional, List
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import Session, joinedload
from app.models.credential import Credential
from app.models.client import Client


class CredentialRepository:
    """Репозиторий для работы с учётными данными (QR, RFID)"""
    
    def __init__(self, db: Session):
        self.db = db
    
    # ==========================================================
    # БАЗОВЫЕ CRUD
    # ==========================================================
    
    def add(self, credential: Credential) -> Credential:
        """Добавить учётные данные"""
        self.db.add(credential)
        self.db.commit()
        self.db.refresh(credential)
        return credential
    
    def get_by_id(self, credential_id: str) -> Credential | None:
        """Получить по ID"""
        return self.db.query(Credential).filter(Credential.id == credential_id).first()
    
    def get_by_value(self, credential_value: str) -> Credential | None:
        """Получить по значению (QR-код или UID)"""
        return self.db.query(Credential).filter(
            Credential.credential_value == credential_value
        ).first()
    
    def save(self, credential: Credential) -> Credential:
        """Сохранить изменения"""
        self.db.commit()
        self.db.refresh(credential)
        return credential
    
    def delete(self, credential: Credential) -> None:
        """Удалить учётные данные"""
        self.db.delete(credential)
        self.db.commit()
    
    # ==========================================================
    # ПОЛУЧЕНИЕ СПИСКОВ
    # ==========================================================
    
    def list_by_client(
        self,
        client_id: str,
        credential_type: str | None = None,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Credential]:
        """Получить все учётные данные клиента"""
        query = self.db.query(Credential).filter(Credential.client_id == client_id)
        
        if credential_type:
            query = query.filter(Credential.credential_type == credential_type)
        
        if status:
            query = query.filter(Credential.status == status)
        
        return query.order_by(Credential.created_at.desc()).offset(offset).limit(limit).all()
    
    def get_active_by_client(self, client_id: str) -> List[Credential]:
        """Получить активные учётные данные клиента"""
        today = date.today()
        return self.db.query(Credential).filter(
            Credential.client_id == client_id,
            Credential.status == "ACTIVE",
            Credential.valid_from <= today,
            or_(
                Credential.valid_until.is_(None),
                Credential.valid_until >= today
            )
        ).all()
    
    def get_by_client_and_type(
        self,
        client_id: str,
        credential_type: str,
    ) -> Credential | None:
        """Получить учётные данные клиента по типу"""
        return self.db.query(Credential).filter(
            Credential.client_id == client_id,
            Credential.credential_type == credential_type,
            Credential.status == "ACTIVE",
        ).first()
    
    # ==========================================================
    # ПРОВЕРКИ
    # ==========================================================
    
    def exists_by_value(self, credential_value: str) -> bool:
        """Проверить, существует ли учётные данные с таким значением"""
        return self.db.query(Credential).filter(
            Credential.credential_value == credential_value
        ).first() is not None
    
    def is_active(self, credential_id: str) -> bool:
        """Проверить, активны ли учётные данные"""
        credential = self.get_by_id(credential_id)
        if not credential:
            return False
        
        today = date.today()
        return (
            credential.status == "ACTIVE" and
            credential.valid_from <= today and
            (credential.valid_until is None or credential.valid_until >= today)
        )
    
    # ==========================================================
    # ОБНОВЛЕНИЕ СТАТУСА
    # ==========================================================
    
    def block(self, credential_id: str, reason: str | None = None) -> Credential | None:
        """Заблокировать учётные данные"""
        credential = self.get_by_id(credential_id)
        if credential:
            credential.status = "BLOCKED"
            if reason:
                credential.notes = f"{credential.notes or ''}\nЗаблокировано: {reason}".strip()
            self.db.commit()
            self.db.refresh(credential)
        return credential
    
    def unblock(self, credential_id: str) -> Credential | None:
        """Разблокировать учётные данные"""
        credential = self.get_by_id(credential_id)
        if credential:
            credential.status = "ACTIVE"
            self.db.commit()
            self.db.refresh(credential)
        return credential
    
    def expire_old_credentials(self) -> int:
        """Пометить просроченные учётные данные как EXPIRED"""
        today = date.today()
        expired = self.db.query(Credential).filter(
            Credential.status == "ACTIVE",
            Credential.valid_until < today,
        ).all()
        
        count = 0
        for credential in expired:
            credential.status = "EXPIRED"
            count += 1
        
        if count > 0:
            self.db.commit()
        
        return count