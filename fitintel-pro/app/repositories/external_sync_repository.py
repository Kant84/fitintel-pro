# app/repositories/external_sync_repository.py

from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.external_sync_log import ExternalSyncLog


class ExternalSyncRepository:
    """Репозиторий для работы с журналом синхронизации внешних систем"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def add(self, log: ExternalSyncLog) -> ExternalSyncLog:
        """Добавить запись синхронизации"""
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log
    
    def update_status(
        self,
        log_id: str,
        status: str,
        response_data: dict | None = None,
        error_message: str | None = None,
    ) -> ExternalSyncLog | None:
        """Обновить статус синхронизации"""
        log = self.db.query(ExternalSyncLog).filter(ExternalSyncLog.id == log_id).first()
        if log:
            log.status = status
            log.processed_at = datetime.now()
            if response_data:
                log.response_data = response_data
            if error_message:
                log.error_message = error_message
            self.db.commit()
            self.db.refresh(log)
        return log
    
    def increment_retry(self, log_id: str) -> ExternalSyncLog | None:
        """Увеличить счётчик попыток"""
        log = self.db.query(ExternalSyncLog).filter(ExternalSyncLog.id == log_id).first()
        if log:
            log.retry_count += 1
            self.db.commit()
            self.db.refresh(log)
        return log
    
    def get_pending(
        self,
        system_type: str | None = None,
        limit: int = 100,
    ) -> List[ExternalSyncLog]:
        """Получить ожидающие синхронизации записи"""
        query = self.db.query(ExternalSyncLog).filter(
            ExternalSyncLog.status == "PENDING"
        )
        
        if system_type:
            query = query.filter(ExternalSyncLog.system_type == system_type)
        
        return query.order_by(ExternalSyncLog.created_at).limit(limit).all()
    
    def get_failed(self, limit: int = 100) -> List[ExternalSyncLog]:
        """Получить неудачные синхронизации"""
        return self.db.query(ExternalSyncLog).filter(
            ExternalSyncLog.status == "FAILED"
        ).order_by(ExternalSyncLog.created_at.desc()).limit(limit).all()
    
    def cleanup_old_logs(self, days_to_keep: int = 30) -> int:
        """Удалить старые записи синхронизации"""
        threshold = datetime.now() - timedelta(days=days_to_keep)
        old_logs = self.db.query(ExternalSyncLog).filter(
            ExternalSyncLog.created_at < threshold
        ).all()
        
        count = len(old_logs)
        for log in old_logs:
            self.db.delete(log)
        
        if count > 0:
            self.db.commit()
        
        return count