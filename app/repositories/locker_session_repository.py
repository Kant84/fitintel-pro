# app/repositories/locker_session_repository.py

from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from app.models.locker_session import LockerSession


class LockerSessionRepository:
    """Репозиторий для работы с сессиями шкафчиков"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def add(self, session: LockerSession) -> LockerSession:
        """Добавить сессию"""
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session
    
    def get_by_id(self, session_id: str) -> LockerSession | None:
        """Получить по ID"""
        return self.db.query(LockerSession).filter(
            LockerSession.id == session_id
        ).first()
    
    def get_by_id_with_details(self, session_id: str) -> LockerSession | None:
        """Получить с подгрузкой связанных данных"""
        return self.db.query(LockerSession).options(
            joinedload(LockerSession.locker),
            joinedload(LockerSession.client),
        ).filter(LockerSession.id == session_id).first()
    
    def get_active_by_client(self, client_id: str) -> LockerSession | None:
        """Получить активную сессию клиента"""
        return self.db.query(LockerSession).filter(
            LockerSession.client_id == client_id,
            LockerSession.status == "ACTIVE",
        ).first()
    
    def get_active_by_locker(self, locker_id: str) -> LockerSession | None:
        """Получить активную сессию шкафчика"""
        return self.db.query(LockerSession).filter(
            LockerSession.locker_id == locker_id,
            LockerSession.status == "ACTIVE",
        ).first()
    
    def get_active_by_credential(self, credential_id: str) -> LockerSession | None:
        """Получить активную сессию по учётным данным"""
        return self.db.query(LockerSession).filter(
            LockerSession.credential_id == credential_id,
            LockerSession.status == "ACTIVE",
        ).first()
    
    def list_active_sessions(self, lock_type: str | None = None) -> List[LockerSession]:
        """Получить все активные сессии"""
        query = self.db.query(LockerSession).filter(LockerSession.status == "ACTIVE")
        
        if lock_type:
            query = query.filter(LockerSession.lock_type == lock_type)
        
        return query.all()
    
    def list_by_client(
        self,
        client_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[LockerSession]:
        """Получить историю сессий клиента"""
        return self.db.query(LockerSession).filter(
            LockerSession.client_id == client_id
        ).order_by(LockerSession.started_at.desc()).offset(offset).limit(limit).all()
    
    def close_session(self, session_id: str) -> LockerSession | None:
        """Закрыть сессию"""
        session = self.get_by_id(session_id)
        if session and session.status == "ACTIVE":
            session.status = "CLOSED"
            session.ended_at = datetime.now()
            self.db.commit()
            self.db.refresh(session)
        return session
    
    def close_by_client(self, client_id: str) -> LockerSession | None:
        """Закрыть активную сессию клиента"""
        session = self.get_active_by_client(client_id)
        if session:
            return self.close_session(session.id)
        return None