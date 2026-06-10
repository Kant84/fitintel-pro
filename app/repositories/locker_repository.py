# app/repositories/locker_repository.py

from typing import List, Optional
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.models.locker import Locker


class LockerRepository:
    """Репозиторий для работы со шкафчиками"""
    
    def __init__(self, db: Session):
        self.db = db
    
    # ==========================================================
    # БАЗОВЫЕ CRUD
    # ==========================================================
    
    def add(self, locker: Locker) -> Locker:
        """Добавить шкафчик"""
        self.db.add(locker)
        self.db.commit()
        self.db.refresh(locker)
        return locker
    
    def get_by_id(self, locker_id: str) -> Locker | None:
        """Получить по ID"""
        return self.db.query(Locker).filter(Locker.id == locker_id).first()
    
    def get_by_number(self, number: str) -> Locker | None:
        """Получить по номеру"""
        return self.db.query(Locker).filter(Locker.number == number).first()
    
    def save(self, locker: Locker) -> Locker:
        """Сохранить изменения"""
        self.db.commit()
        self.db.refresh(locker)
        return locker
    
    # ==========================================================
    # ПОЛУЧЕНИЕ СПИСКОВ
    # ==========================================================
    
    def list_all(
        self,
        zone: str | None = None,
        lock_type: str | None = None,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Locker]:
        """Получить список шкафчиков с фильтрацией"""
        query = self.db.query(Locker)
        
        if zone:
            query = query.filter(Locker.zone == zone)
        
        if lock_type:
            query = query.filter(Locker.lock_type == lock_type)
        
        if status:
            query = query.filter(Locker.status == status)
        
        return query.order_by(Locker.number).offset(offset).limit(limit).all()
    
    def get_free_lockers(
        self,
        lock_type: str | None = None,
        zone: str | None = None,
    ) -> List[Locker]:
        """Получить свободные шкафчики"""
        query = self.db.query(Locker).filter(Locker.status == "FREE")
        
        if lock_type:
            query = query.filter(Locker.lock_type == lock_type)
        
        if zone:
            query = query.filter(Locker.zone == zone)
        
        return query.order_by(Locker.number).all()
    
    def get_occupied_lockers(self) -> List[Locker]:
        """Получить занятые шкафчики"""
        return self.db.query(Locker).filter(Locker.status == "OCCUPIED").all()
    
    def get_by_device_id(self, device_id: str) -> Locker | None:
        """Получить шкафчик по ID устройства замка"""
        return self.db.query(Locker).filter(Locker.device_id == device_id).first()
    
    # ==========================================================
    # СТАТУСЫ
    # ==========================================================
    
    def update_status(self, locker_id: str, status: str) -> Locker | None:
        """Обновить статус шкафчика"""
        locker = self.get_by_id(locker_id)
        if locker:
            locker.status = status
            self.db.commit()
            self.db.refresh(locker)
        return locker
    
    def get_stats(self) -> dict:
        """Получить статистику по шкафчикам"""
        total = self.db.query(Locker).count()
        free = self.db.query(Locker).filter(Locker.status == "FREE").count()
        occupied = self.db.query(Locker).filter(Locker.status == "OCCUPIED").count()
        broken = self.db.query(Locker).filter(Locker.status == "BROKEN").count()
        
        return {
            "total": total,
            "free": free,
            "occupied": occupied,
            "broken": broken,
        }