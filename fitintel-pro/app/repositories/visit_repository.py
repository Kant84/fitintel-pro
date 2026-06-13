# app/repositories/visit_repository.py

from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID
from sqlalchemy import select, func, and_, or_, between
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.sql import extract
from app.models.visit import Visit
from app.models.client import Client
from app.models.subscription import Subscription


class VisitRepository:
    """
    Репозиторий для работы с посещениями.
    Инкапсулирует все прямые запросы к БД.
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    # ==========================================================
    # БАЗОВЫЕ CRUD ОПЕРАЦИИ
    # ==========================================================
    
    def add(self, visit: Visit) -> Visit:
        """Добавить новое посещение"""
        self.db.add(visit)
        self.db.commit()
        self.db.refresh(visit)
        return visit
    
    def save(self, visit: Visit) -> Visit:
        """Сохранить изменения в посещении"""
        self.db.commit()
        self.db.refresh(visit)
        return visit
    
    def get_by_id(self, visit_id: str) -> Visit | None:
        """Получить посещение по ID"""
        return self.db.query(Visit).filter(Visit.id == visit_id).first()
    
    def get_by_id_with_relations(self, visit_id: str) -> Visit | None:
        """Получить посещение по ID с подгрузкой связанных данных"""
        return (
            self.db.query(Visit)
            .options(
                joinedload(Visit.client),
                joinedload(Visit.subscription),
            )
            .filter(Visit.id == visit_id)
            .first()
        )
    
    def delete(self, visit: Visit) -> None:
        """Удалить посещение"""
        self.db.delete(visit)
        self.db.commit()
    
    # ==========================================================
    # ПОЛУЧЕНИЕ СПИСКОВ
    # ==========================================================
    
    def list_by_client(
        self,
        client_id: str,
        limit: int = 100,
        offset: int = 0,
        status: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> List[Visit]:
        """
        Получить список посещений клиента.
        
        Args:
            client_id: ID клиента
            limit: лимит записей
            offset: смещение
            status: фильтр по статусу (ACTIVE, COMPLETED, CANCELLED)
            start_date: начальная дата
            end_date: конечная дата
        """
        query = self.db.query(Visit).filter(Visit.client_id == client_id)
        
        if status:
            query = query.filter(Visit.status == status)
        
        if start_date:
            query = query.filter(Visit.entry_time >= start_date)
        
        if end_date:
            query = query.filter(Visit.entry_time <= end_date + timedelta(days=1))
        
        return (
            query.order_by(Visit.entry_time.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
    
    def get_active_visits(
        self,
        client_id: str | None = None,
        zone: str | None = None,
    ) -> List[Visit]:
        """
        Получить активные посещения (клиенты в клубе).
        
        Args:
            client_id: опционально — только для конкретного клиента
            zone: опционально — фильтр по зоне
        """
        query = self.db.query(Visit).filter(
            Visit.status == "ACTIVE",
            Visit.exit_time.is_(None),
        )
        
        if client_id:
            query = query.filter(Visit.client_id == client_id)
        
        if zone:
            query = query.filter(Visit.zone == zone)
        
        return query.order_by(Visit.entry_time).all()
    
    def get_active_visits_count(self, zone: str | None = None) -> int:
        """Получить количество активных посещений (клиентов в клубе)"""
        query = self.db.query(Visit).filter(
            Visit.status == "ACTIVE",
            Visit.exit_time.is_(None),
        )
        
        if zone:
            query = query.filter(Visit.zone == zone)
        
        return query.count()
    
    def get_active_visit_by_client(self, client_id: str) -> Visit | None:
        """Получить активное посещение клиента (если есть)"""
        return (
            self.db.query(Visit)
            .filter(
                Visit.client_id == client_id,
                Visit.status == "ACTIVE",
                Visit.exit_time.is_(None),
            )
            .first()
        )
    
    # ==========================================================
    # ОПЕРАЦИИ С ВРЕМЕНЕМ
    # ==========================================================
    
    def get_visits_by_date_range(
        self,
        start_date: date,
        end_date: date,
        client_id: str | None = None,
        zone: str | None = None,
    ) -> List[Visit]:
        """Получить посещения за период"""
        query = self.db.query(Visit).filter(
            between(Visit.entry_time, start_date, end_date + timedelta(days=1))
        )
        
        if client_id:
            query = query.filter(Visit.client_id == client_id)
        
        if zone:
            query = query.filter(Visit.zone == zone)
        
        return query.order_by(Visit.entry_time).all()
    
    def get_today_visits(self, zone: str | None = None) -> List[Visit]:
        """Получить посещения за сегодня"""
        today = date.today()
        return self.get_visits_by_date_range(today, today, zone=zone)
    
    def get_incomplete_visits(self) -> List[Visit]:
        """
        Получить незавершённые посещения (вход есть, выхода нет).
        Для фоновой задачи — закрывать посещения в конце дня.
        """
        return (
            self.db.query(Visit)
            .filter(
                Visit.status == "ACTIVE",
                Visit.exit_time.is_(None),
                Visit.entry_time < date.today() - timedelta(days=1),
            )
            .all()
        )
    
    # ==========================================================
    # СТАТИСТИКА
    # ==========================================================
    
    def get_stats_by_period(
        self,
        start_date: date,
        end_date: date,
        zone: str | None = None,
    ) -> Dict[str, Any]:
        """
        Получить статистику посещений за период.
        
        Returns:
            Dict с ключами:
            - total_visits: общее количество посещений
            - unique_clients: количество уникальных клиентов
            - avg_duration: средняя длительность (в минутах)
            - total_duration: общая длительность (в минутах)
        """
        query = self.db.query(Visit).filter(
            between(Visit.entry_time, start_date, end_date + timedelta(days=1)),
            Visit.status == "COMPLETED",
        )
        
        if zone:
            query = query.filter(Visit.zone == zone)
        
        visits = query.all()
        
        total_visits = len(visits)
        unique_clients = len(set(v.client_id for v in visits))
        
        durations = [v.duration_minutes for v in visits if v.duration_minutes]
        avg_duration = sum(durations) / len(durations) if durations else None
        total_duration = sum(durations) if durations else None
        
        return {
            "total_visits": total_visits,
            "unique_clients": unique_clients,
            "avg_duration": avg_duration,
            "total_duration": total_duration,
        }
    
    def get_peak_hours(
        self,
        start_date: date,
        end_date: date,
        zone: str | None = None,
    ) -> Dict[int, int]:
        """
        Получить распределение посещений по часам.
        
        Returns:
            Dict {час: количество посещений}
        """
        query = self.db.query(
            extract('hour', Visit.entry_time).label('hour'),
            func.count(Visit.id).label('count')
        ).filter(
            between(Visit.entry_time, start_date, end_date + timedelta(days=1))
        )
        
        if zone:
            query = query.filter(Visit.zone == zone)
        
        results = query.group_by('hour').all()
        
        return {int(r.hour): r.count for r in results}
    
    def get_visits_by_day(
        self,
        start_date: date,
        end_date: date,
        zone: str | None = None,
    ) -> Dict[str, int]:
        """
        Получить распределение посещений по дням.
        
        Returns:
            Dict {"YYYY-MM-DD": количество посещений}
        """
        query = self.db.query(
            func.date(Visit.entry_time).label('day'),
            func.count(Visit.id).label('count')
        ).filter(
            between(Visit.entry_time, start_date, end_date + timedelta(days=1))
        )
        
        if zone:
            query = query.filter(Visit.zone == zone)
        
        results = query.group_by('day').order_by('day').all()
        
        return {str(r.day): r.count for r in results}
    
    def get_visits_by_zone(
        self,
        start_date: date,
        end_date: date,
    ) -> Dict[str, int]:
        """
        Получить распределение посещений по зонам.
        
        Returns:
            Dict {зона: количество посещений}
        """
        results = (
            self.db.query(
                Visit.zone,
                func.count(Visit.id).label('count')
            )
            .filter(
                between(Visit.entry_time, start_date, end_date + timedelta(days=1))
            )
            .group_by(Visit.zone)
            .all()
        )
        
        return {r.zone or "unknown": r.count for r in results}
    
    # ==========================================================
    # ОТЧЁТЫ ДЛЯ АДМИНИСТРАТОРА
    # ==========================================================
    
    def get_top_clients(
        self,
        start_date: date,
        end_date: date,
        limit: int = 10,
    ) -> List[Tuple[str, str, int]]:
        """
        Получить топ клиентов по количеству посещений.
        
        Returns:
            List of (client_id, client_name, visits_count)
        """
        results = (
            self.db.query(
                Client.id,
                Client.first_name,
                Client.last_name,
                func.count(Visit.id).label('visits_count')
            )
            .join(Visit, Visit.client_id == Client.id)
            .filter(
                between(Visit.entry_time, start_date, end_date + timedelta(days=1)),
                Visit.status == "COMPLETED",
            )
            .group_by(Client.id)
            .order_by(func.count(Visit.id).desc())
            .limit(limit)
            .all()
        )
        
        return [
            (
                str(r.id),
                f"{r.first_name} {r.last_name}",
                r.visits_count,
            )
            for r in results
        ]
    
    def get_current_occupancy_by_zone(self) -> Dict[str, int]:
        """Получить текущую заполняемость по зонам"""
        results = (
            self.db.query(
                Visit.zone,
                func.count(Visit.id).label('count')
            )
            .filter(
                Visit.status == "ACTIVE",
                Visit.exit_time.is_(None),
            )
            .group_by(Visit.zone)
            .all()
        )
        
        return {r.zone or "unknown": r.count for r in results}
    
    # ==========================================================
    # ОБНОВЛЕНИЕ СТАТУСОВ
    # ==========================================================
    
    def close_incomplete_visits(self, force_date: date | None = None) -> int:
        """
        Закрыть незавершённые посествия (вход без выхода).
        
        Args:
            force_date: дата, до которой закрывать (по умолчанию вчера)
        
        Returns:
            Количество закрытых посещений
        """
        if force_date is None:
            force_date = date.today() - timedelta(days=1)
        
        incomplete_visits = self.get_incomplete_visits()
        
        closed_count = 0
        for visit in incomplete_visits:
            if visit.entry_time.date() <= force_date:
                visit.status = "COMPLETED"
                # Устанавливаем время выхода на 23:59:59 дня входа
                visit.exit_time = datetime.combine(
                    visit.entry_time.date(),
                    datetime.max.time().replace(hour=23, minute=59, second=59)
                )
                if visit.entry_time and visit.exit_time:
                    duration = (visit.exit_time - visit.entry_time).total_seconds() / 60
                    visit.duration_minutes = int(duration)
                closed_count += 1
        
        if closed_count > 0:
            self.db.commit()
        
        return closed_count
    
    # ==========================================================
    # ПРОВЕРКИ
    # ==========================================================
    
    def has_active_visit(self, client_id: str) -> bool:
        """Проверить, есть ли у клиента активное посещение"""
        return (
            self.db.query(Visit)
            .filter(
                Visit.client_id == client_id,
                Visit.status == "ACTIVE",
                Visit.exit_time.is_(None),
            )
            .first() is not None
        )
    
    def get_last_visit(self, client_id: str) -> Visit | None:
        """Получить последнее посещение клиента"""
        return (
            self.db.query(Visit)
            .filter(Visit.client_id == client_id)
            .order_by(Visit.entry_time.desc())
            .first()
        )