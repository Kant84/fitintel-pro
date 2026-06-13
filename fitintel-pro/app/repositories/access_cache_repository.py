# app/repositories/access_cache_repository.py

from datetime import datetime
from typing import List, Optional
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session
from app.models.access_cache import AccessCache


class AccessCacheRepository:
    """Репозиторий для работы с кэшем доступа (офлайн-режим)"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def add(self, cache_item: AccessCache) -> AccessCache:
        """Добавить элемент в кэш"""
        self.db.add(cache_item)
        self.db.commit()
        self.db.refresh(cache_item)
        return cache_item
    
    def add_bulk(self, items: List[AccessCache]) -> int:
        """Массовое добавление элементов в кэш"""
        self.db.add_all(items)
        self.db.commit()
        return len(items)
    
    def get_by_credential(self, credential_value: str) -> AccessCache | None:
        """Получить кэш по учётным данным"""
        now = datetime.now()
        return self.db.query(AccessCache).filter(
            AccessCache.credential_value == credential_value,
            AccessCache.valid_from <= now,
            AccessCache.valid_until >= now,
        ).first()
    
    def get_all_active(self, device_id: str | None = None) -> List[AccessCache]:
        """Получить все активные элементы кэша"""
        now = datetime.now()
        query = self.db.query(AccessCache).filter(
            AccessCache.valid_from <= now,
            AccessCache.valid_until >= now,
        )
        
        if device_id:
            query = query.filter(AccessCache.device_id == device_id)
        
        return query.all()
    
    def get_max_version(self, device_id: str | None = None) -> int:
        """Получить максимальную версию кэша"""
        query = self.db.query(AccessCache.cache_version)
        
        if device_id:
            query = query.filter(AccessCache.device_id == device_id)
        
        result = query.order_by(AccessCache.cache_version.desc()).first()
        return result[0] if result else 0
    
    def delete_expired(self) -> int:
        """Удалить просроченный кэш"""
        now = datetime.now()
        expired = self.db.query(AccessCache).filter(
            AccessCache.valid_until < now
        ).all()
        
        count = len(expired)
        for item in expired:
            self.db.delete(item)
        
        if count > 0:
            self.db.commit()
        
        return count
    
    def invalidate_by_client(self, client_id: str) -> int:
        """Инвалидировать кэш клиента (при изменении прав)"""
        # Находим все учётные данные клиента
        from app.models.credential import Credential
        credentials = self.db.query(Credential).filter(
            Credential.client_id == client_id
        ).all()
        
        credential_values = [c.credential_value for c in credentials]
        
        if not credential_values:
            return 0
        
        # Удаляем кэш для этих учётных данных
        items = self.db.query(AccessCache).filter(
            AccessCache.credential_value.in_(credential_values)
        ).all()
        
        count = len(items)
        for item in items:
            self.db.delete(item)
        
        if count > 0:
            self.db.commit()
        
        return count