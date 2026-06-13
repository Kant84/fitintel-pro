# app/services/access_cache_service.py 
from datetime import datetime, timedelta, timezone, date  
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.access_cache import AccessCache
from app.models.credential import Credential
from app.models.client import Client
from app.models.subscription import Subscription
from app.repositories.access_cache_repository import AccessCacheRepository
from app.repositories.credential_repository import CredentialRepository
from app.services.audit_service import AuditService

class AccessCacheService:
    """
    Сервис для управления кэшем прав доступа (офлайн-режим).
    
    Кэш позволяет терминалам и турникетам работать без интернета:
    - Предварительно рассчитываются права доступа
    - Кэш скачивается на устройства
    - При отсутствии связи устройства используют локальный кэш
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.cache_repo = AccessCacheRepository(db)
        self.credential_repo = CredentialRepository(db)
        self.audit = AuditService(db)
    
    # ==========================================================
    # ПОСТРОЕНИЕ КЭША
    # ==========================================================
    
    def _get_client_access_info(self, credential: Credential) -> dict:
        """
        Получить информацию о доступе для клиента.
        
        Returns:
            Словарь с данными для кэша
        """
        client = self.db.query(Client).filter(Client.id == credential.client_id).first()
        if not client:
            return {
                "access_granted": False,
                "client_name": None,
                "subscription_status": None,
                "visits_left": None,
                "subscription_end_date": None,
            }
        
        # Проверяем, активен ли клиент
        if not client.is_active or client.status != "ACTIVE":
            return {
                "access_granted": False,
                "client_name": f"{client.first_name} {client.last_name}",
                "subscription_status": "CLIENT_INACTIVE",
                "visits_left": None,
                "subscription_end_date": None,
            }
        
        # Проверяем абонемент
        today = date.today()
        subscription = self.db.query(Subscription).filter(
            Subscription.client_id == client.id,
            Subscription.is_active == True,
            Subscription.status == "ACTIVE",
            Subscription.end_date >= today,
        ).first()
        
        if not subscription:
            return {
                "access_granted": False,
                "client_name": f"{client.first_name} {client.last_name}",
                "subscription_status": "NO_ACTIVE_SUBSCRIPTION",
                "visits_left": None,
                "subscription_end_date": None,
            }
        
        # Проверяем лимит посещений
        if not subscription.is_unlimited:
            if subscription.visits_used >= subscription.visit_limit:
                return {
                    "access_granted": False,
                    "client_name": f"{client.first_name} {client.last_name}",
                    "subscription_status": "LIMIT_EXCEEDED",
                    "visits_left": 0,
                    "subscription_end_date": subscription.end_date,
                }
        
        # Всё хорошо — доступ разрешён
        visits_left = None
        if not subscription.is_unlimited:
            visits_left = subscription.visit_limit - subscription.visits_used
        
        return {
            "access_granted": True,
            "client_name": f"{client.first_name} {client.last_name}",
            "subscription_status": subscription.status,
            "visits_left": visits_left,
            "subscription_end_date": subscription.end_date,
        }
    
    def build_cache_for_credential(
        self,
        credential: Credential,
        cache_duration_hours: int = 24,
        device_id: str | None = None,
    ) -> AccessCache:
        """
        Построить элемент кэша для конкретных учётных данных.
        """
        from datetime import timezone
    
        access_info = self._get_client_access_info(credential)
    
        # ✅ Добавляем часовой пояс UTC
        now = datetime.now(timezone.utc)
        valid_until = now + timedelta(hours=cache_duration_hours)
    
        current_version = self.cache_repo.get_max_version(device_id)
    
        cache_item = AccessCache(
            credential_value=credential.credential_value,
            access_granted=access_info["access_granted"],
            client_name=access_info["client_name"],
            subscription_status=access_info["subscription_status"],
            visits_left=access_info["visits_left"],
            subscription_end_date=access_info["subscription_end_date"],
            valid_from=now,
            valid_until=valid_until,
            cache_version=current_version + 1,
            device_id=device_id,
        )
    
        return cache_item
    
    def build_full_cache(
        self,
        device_id: str | None = None,
        cache_duration_hours: int = 24,
    ) -> List[AccessCache]:
        """
        Построить полный кэш для всех активных учётных данных.
        
        Используется для первоначальной загрузки кэша на устройство.
        
        Args:
            device_id: ID устройства
            cache_duration_hours: Срок действия кэша
        
        Returns:
            Список элементов кэша
        """
        # Получаем все активные учётные данные
        today = date.today()
        active_credentials = self.db.query(Credential).filter(
            Credential.status == "ACTIVE",
            Credential.valid_from <= today,
            Credential.valid_until >= today,
        ).all()
        
        cache_items = []
        for credential in active_credentials:
            cache_item = self.build_cache_for_credential(
                credential=credential,
                cache_duration_hours=cache_duration_hours,
                device_id=device_id,
            )
            cache_items.append(cache_item)
        
        return cache_items
    
    # ==========================================================
    # УПРАВЛЕНИЕ КЭШЕМ
    # ==========================================================
    
    def sync_cache(
        self,
        device_id: str,
        last_cache_version: int = 0,
    ) -> dict:
        """
        Синхронизировать кэш для устройства.
        
        Args:
            device_id: ID устройства
            last_cache_version: Последняя версия кэша на устройстве
        
        Returns:
            Словарь с обновлениями кэша
        """
        current_version = self.cache_repo.get_max_version(device_id)
        
        # Если версия актуальна — обновлений нет
        if last_cache_version >= current_version:
            return {
                "need_update": False,
                "cache_version": current_version,
                "items": [],
            }
        
        # Получаем все активные элементы кэша для устройства
        existing_items = self.cache_repo.get_all_active(device_id)
        
        # Если кэш пуст или устарел — перестраиваем
        if not existing_items or last_cache_version == 0:
            # Удаляем старый кэш для этого устройства
            old_items = self.db.query(AccessCache).filter(
                AccessCache.device_id == device_id
            ).all()
            for item in old_items:
                self.db.delete(item)
            
            # Строим новый кэш
            new_items = self.build_full_cache(device_id)
            
            # Сохраняем
            for item in new_items:
                self.db.add(item)
            
            self.db.commit()
            
            # Формируем ответ
            items_data = [
                {
                    "credential_value": item.credential_value,
                    "access_granted": item.access_granted,
                    "client_name": item.client_name,
                    "subscription_status": item.subscription_status,
                    "visits_left": item.visits_left,
                    "subscription_end_date": item.subscription_end_date,
                }
                for item in new_items
            ]
            
            return {
                "need_update": True,
                "cache_version": current_version + 1,
                "items": items_data,
            }
        
        # Возвращаем существующие элементы
        items_data = [
            {
                "credential_value": item.credential_value,
                "access_granted": item.access_granted,
                "client_name": item.client_name,
                "subscription_status": item.subscription_status,
                "visits_left": item.visits_left,
                "subscription_end_date": item.subscription_end_date,
            }
            for item in existing_items
        ]
        
        return {
            "need_update": True,
            "cache_version": current_version,
            "items": items_data,
        }
    
    def invalidate_cache_by_client(self, client_id: str) -> int:
        """
        Инвалидировать кэш клиента (при изменении прав).
        
        Используется когда:
        - Изменился статус абонемента
        - Изменились права доступа
        - Клиент заблокирован/разблокирован
        
        Returns:
            Количество удалённых элементов кэша
        """
        count = self.cache_repo.invalidate_by_client(client_id)
        
        if count > 0:
            self.audit.log(
                action="access.cache.invalidated",
                status="success",
                actor_user_id=None,
                entity_type="client",
                entity_id=client_id,
                message=f"Access cache invalidated for client {client_id}, {count} items removed",
            )
        
        return count
    
    def invalidate_cache_by_credential(self, credential_value: str) -> bool:
        """
        Инвалидировать кэш для конкретных учётных данных.
        """
        cache_item = self.cache_repo.get_by_credential(credential_value)
        if cache_item:
            self.db.delete(cache_item)
            self.db.commit()
            return True
        return False
    
    # ==========================================================
    # ПРОВЕРКА ДОСТУПА ИЗ КЭША
    # ==========================================================
    
    

    def check_from_cache(
        self,
        credential_value: str,
        device_id: str | None = None,
    ) -> dict:
        """
        Проверить доступ по кэшу (для офлайн-режима).
    
        Returns:
            Словарь с результатом проверки
        """
        from datetime import timezone
    
        cache_item = self.cache_repo.get_by_credential(credential_value)
    
        if not cache_item:
            return {
                "found": False,
                "access_granted": False,
                "reason": "Учётные данные не найдены в кэше",
            }
    
        # ✅ Добавляем часовой пояс к now
        now = datetime.now(timezone.utc)
    
        if cache_item.valid_until < now:
            return {
                "found": True,
                "access_granted": False,
                "reason": "Кэш просрочен",
            }
    
        return {
            "found": True,
            "access_granted": cache_item.access_granted,
            "reason": None if cache_item.access_granted else cache_item.subscription_status,
            "client_name": cache_item.client_name,
            "subscription_status": cache_item.subscription_status,
            "visits_left": cache_item.visits_left,
            "subscription_end_date": cache_item.subscription_end_date,
        }
    
    # ==========================================================
    # ФОНОВЫЕ ЗАДАЧИ
    # ==========================================================
    
    def refresh_all_caches(self) -> int:
        """
        Обновить кэш для всех устройств.
        
        Returns:
            Количество обновлённых элементов
        """
        # Получаем все уникальные device_id
        devices = self.db.query(AccessCache.device_id).distinct().all()
        device_ids = [d[0] for d in devices if d[0]]
        
        total_items = 0
        
        for device_id in device_ids:
            # Удаляем старый кэш
            old_items = self.db.query(AccessCache).filter(
                AccessCache.device_id == device_id
            ).all()
            for item in old_items:
                self.db.delete(item)
            
            # Строим новый кэш
            new_items = self.build_full_cache(device_id)
            for item in new_items:
                self.db.add(item)
            
            total_items += len(new_items)
        
        if total_items > 0:
            self.db.commit()
        
        return total_items
    
    def cleanup_expired_cache(self) -> int:
        """Удалить просроченный кэш"""
        return self.cache_repo.delete_expired()