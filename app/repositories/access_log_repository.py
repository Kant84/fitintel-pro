# app/repositories/access_log_repository.py

from datetime import datetime
from typing import List, Optional
from sqlalchemy import and_, between
from sqlalchemy.orm import Session
from app.models.access_log import AccessLog


class AccessLogRepository:
    """Репозиторий для работы с журналом доступа"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def add(self, log: AccessLog) -> AccessLog:
        """Добавить запись в журнал"""
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log
    
    def add_bulk(self, logs: List[AccessLog]) -> int:
        """Массовое добавление записей (для офлайн-синхронизации)"""
        self.db.add_all(logs)
        self.db.commit()
        return len(logs)
    
    def list_by_device(
        self,
        device_id: str,
        limit: int = 100,
        offset: int = 0,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> List[AccessLog]:
        """Получить записи по устройству"""
        query = self.db.query(AccessLog).filter(AccessLog.device_id == device_id)
        
        if start_date:
            query = query.filter(AccessLog.created_at >= start_date)
        
        if end_date:
            query = query.filter(AccessLog.created_at <= end_date)
        
        return query.order_by(AccessLog.created_at.desc()).offset(offset).limit(limit).all()
    
    def list_by_client(
        self,
        client_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AccessLog]:
        """Получить записи по клиенту"""
        return self.db.query(AccessLog).filter(
            AccessLog.client_id == client_id
        ).order_by(AccessLog.created_at.desc()).offset(offset).limit(limit).all()
    
    def get_denied_by_client(
        self,
        client_id: str,
        limit: int = 50,
    ) -> List[AccessLog]:
        """Получить отказы в доступе для клиента"""
        return self.db.query(AccessLog).filter(
            AccessLog.client_id == client_id,
            AccessLog.decision == "DENY",
        ).order_by(AccessLog.created_at.desc()).limit(limit).all()
    
    def get_stats_by_period(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> dict:
        """Получить статистику по периоду"""
        logs = self.db.query(AccessLog).filter(
            between(AccessLog.created_at, start_date, end_date)
        ).all()
        
        total = len(logs)
        allow = sum(1 for l in logs if l.decision == "ALLOW")
        deny = sum(1 for l in logs if l.decision == "DENY")
        offline = sum(1 for l in logs if l.mode == "offline")
        
        return {
            "total": total,
            "allow": allow,
            "deny": deny,
            "offline_count": offline,
        }
    
    def cleanup_old_logs(self, days_to_keep: int = 90) -> int:
        """Удалить старые записи журнала"""
        threshold = datetime.now() - timedelta(days=days_to_keep)
        old_logs = self.db.query(AccessLog).filter(
            AccessLog.created_at < threshold
        ).all()
        
        count = len(old_logs)
        for log in old_logs:
            self.db.delete(log)
        
        if count > 0:
            self.db.commit()
        
        return count