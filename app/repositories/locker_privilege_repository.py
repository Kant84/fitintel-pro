# app/repositories/locker_privilege_repository.py

from datetime import date
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.locker_privilege import LockerPrivilege


class LockerPrivilegeRepository:
    """Репозиторий для работы с привилегиями на шкафчики"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def add(self, privilege: LockerPrivilege) -> LockerPrivilege:
        """Добавить привилегию"""
        self.db.add(privilege)
        self.db.commit()
        self.db.refresh(privilege)
        return privilege
    
    def get_by_id(self, privilege_id: str) -> LockerPrivilege | None:
        """Получить по ID"""
        return self.db.query(LockerPrivilege).filter(
            LockerPrivilege.id == privilege_id
        ).first()
    
    def get_by_client(
        self,
        client_id: str,
        locker_type: str | None = None,
    ) -> List[LockerPrivilege]:
        """Получить привилегии клиента"""
        query = self.db.query(LockerPrivilege).filter(
            LockerPrivilege.client_id == client_id
        )
        
        if locker_type:
            query = query.filter(LockerPrivilege.locker_type == locker_type)
        
        return query.all()
    
    def has_privilege(
        self,
        client_id: str,
        locker_type: str,
    ) -> bool:
        """Проверить, есть ли у клиента привилегия"""
        today = date.today()
        privilege = self.db.query(LockerPrivilege).filter(
            LockerPrivilege.client_id == client_id,
            LockerPrivilege.locker_type == locker_type,
            LockerPrivilege.valid_from <= today,
            LockerPrivilege.valid_until >= today,
        ).first()
        return privilege is not None
    
    def revoke(self, privilege_id: str) -> bool:
        """Отозвать привилегию"""
        privilege = self.get_by_id(privilege_id)
        if privilege:
            self.db.delete(privilege)
            self.db.commit()
            return True
        return False
    
    def revoke_by_client(self, client_id: str, locker_type: str) -> int:
        """Отозвать все привилегии клиента указанного типа"""
        privileges = self.db.query(LockerPrivilege).filter(
            LockerPrivilege.client_id == client_id,
            LockerPrivilege.locker_type == locker_type,
        ).all()
        
        count = len(privileges)
        for privilege in privileges:
            self.db.delete(privilege)
        
        if count > 0:
            self.db.commit()
        
        return count