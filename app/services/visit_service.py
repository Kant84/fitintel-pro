# app/services/visit_service.py

from datetime import datetime, date, timedelta, timezone
from typing import Optional, List, Dict, Any
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.visit import Visit
from app.models.client import Client
from app.models.subscription import Subscription
from app.repositories.visit_repository import VisitRepository
from app.schemas.visit import (
    VisitResponse,
    VisitListResponse,
    VisitStatsResponse,
    VisitEntryRequest,
    VisitExitRequest,
    ManualVisitRequest,
)
from app.schemas.enums import VisitStatus, AccessMethod
from app.services.audit_service import AuditService


class VisitService:
    """
    Сервис для управления посещениями.
    Включает вход, выход, списание визитов, статистику.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.repository = VisitRepository(db)
        self.audit = AuditService(db)
    
    # ==========================================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # ==========================================================
    
    def _get_client(self, client_id: str) -> Client:
        """Получить клиента или выбросить 404"""
        client = self.db.query(Client).filter(Client.id == client_id).first()
        if not client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Клиент не найден",
            )
        return client
    
    def _get_subscription(self, subscription_id: str) -> Subscription | None:
        """Получить абонемент (опционально)"""
        return self.db.query(Subscription).filter(Subscription.id == subscription_id).first()
    
    def _get_active_subscription(self, client_id: str) -> Subscription | None:
        """Получить активный абонемент клиента"""
        return (
            self.db.query(Subscription)
            .filter(
                Subscription.client_id == client_id,
                Subscription.is_active == True,
                Subscription.status == "ACTIVE",
                Subscription.end_date >= date.today(),
            )
            .first()
        )
    
    def _ensure_timezone_aware(self, dt: datetime) -> datetime:
        """Добавляет UTC часовой пояс, если его нет"""
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt
    
    def _calculate_duration(self, entry_time: datetime, exit_time: datetime) -> int:
        """Рассчитать длительность пребывания в минутах"""
        # Убеждаемся, что оба времени с часовым поясом
        entry_time = self._ensure_timezone_aware(entry_time)
        exit_time = self._ensure_timezone_aware(exit_time)
        
        delta = exit_time - entry_time
        return int(delta.total_seconds() / 60)
    
    def _deduct_visit(self, subscription: Subscription) -> None:
        """Списать один визит из абонемента"""
        if not subscription.is_unlimited:
            subscription.visits_used += 1
            self.db.commit()
    
    def _build_response(self, visit: Visit) -> dict:
        """Построить словарь ответа"""
        return {
            "id": visit.id,
            "client_id": visit.client_id,
            "subscription_id": visit.subscription_id,
            "entry_time": visit.entry_time,
            "exit_time": visit.exit_time,
            "duration_minutes": visit.duration_minutes,
            "access_method": visit.access_method,
            "access_device_id": visit.access_device_id,
            "access_granted": visit.access_granted,
            "access_denied_reason": visit.access_denied_reason,
            "status": visit.status,
            "zone": visit.zone,
            "notes": visit.notes,
            "processed_by_user_id": visit.processed_by_user_id,
            "created_at": visit.created_at,
            "updated_at": visit.updated_at,
        }
    
    # ==========================================================
    # ВХОД
    # ==========================================================
    
    def entry(
        self,
        client_id: str,
        subscription_id: str | None = None,
        access_method: AccessMethod = AccessMethod.QR,
        access_device_id: str | None = None,
        zone: str | None = None,
        entry_time: datetime | None = None,
        notes: str | None = None,
        actor_user_id: str | None = None,
    ) -> Visit:
        """
        Зафиксировать вход клиента.
        
        Args:
            client_id: ID клиента
            subscription_id: ID абонемента (опционально)
            access_method: способ доступа
            access_device_id: ID устройства
            zone: зона клуба
            entry_time: время входа (по умолчанию сейчас)
            notes: заметки
            actor_user_id: кто зафиксировал (для audit)
        
        Returns:
            Созданное посещение
        """
        # Проверяем клиента
        client = self._get_client(client_id)
        
        # Проверяем, нет ли уже активного посещения
        active_visit = self.repository.get_active_visit_by_client(client_id)
        if active_visit:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Клиент уже находится в клубе. Активное посещение: {active_visit.id}",
            )
        
        # Определяем абонемент
        subscription = None
        if subscription_id:
            subscription = self._get_subscription(subscription_id)
            if not subscription:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Абонемент не найден",
                )
        else:
            subscription = self._get_active_subscription(client_id)
        
        # Проверяем лимиты абонемента
        if subscription and not subscription.is_unlimited:
            if subscription.visits_used >= subscription.visit_limit:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Лимит посещений абонемента исчерпан",
                )
        
        # Устанавливаем время входа с часовым поясом UTC
        if entry_time is None:
            entry_time = datetime.now(timezone.utc)
        else:
            entry_time = self._ensure_timezone_aware(entry_time)
        
        # Создаём посещение
        visit = Visit(
            client_id=client_id,
            subscription_id=subscription.id if subscription else None,
            entry_time=entry_time,
            access_method=access_method.value,
            access_device_id=access_device_id,
            access_granted=True,
            status=VisitStatus.ACTIVE.value,
            zone=zone,
            notes=notes,
            processed_by_user_id=actor_user_id,
        )
        
        created_visit = self.repository.add(visit)
        
        # Списываем визит, если есть абонемент
        if subscription:
            self._deduct_visit(subscription)
        
        # Пишем audit
        self.audit.log(
            action="visits.entry",
            status="success",
            actor_user_id=actor_user_id,
            entity_type="visit",
            entity_id=created_visit.id,
            message=f"Client {client.first_name} {client.last_name} entered",
            after_data={
                "client_id": client_id,
                "client_name": f"{client.first_name} {client.last_name}",
                "access_method": access_method.value,
                "zone": zone,
                "subscription_id": subscription.id if subscription else None,
            },
        )
        
        return created_visit
    
    # ==========================================================
    # ВЫХОД
    # ==========================================================
    
    def exit(
        self,
        visit_id: str,
        exit_time: datetime | None = None,
        notes: str | None = None,
        actor_user_id: str | None = None,
    ) -> Visit:
        """
        Зафиксировать выход клиента.
        """
        visit = self.repository.get_by_id(visit_id)
        
        if not visit:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Посещение не найдено",
            )
        
        if visit.status != VisitStatus.ACTIVE.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Посещение уже завершено. Текущий статус: {visit.status}",
            )
        
        # Устанавливаем время выхода с часовым поясом UTC
        if exit_time is None:
            exit_time = datetime.now(timezone.utc)
        else:
            exit_time = self._ensure_timezone_aware(exit_time)
        
        visit.exit_time = exit_time
        
        # Рассчитываем длительность (entry_time уже с UTC)
        visit.duration_minutes = self._calculate_duration(visit.entry_time, exit_time)
        
        # Меняем статус
        visit.status = VisitStatus.COMPLETED.value
        
        if notes:
            visit.notes = notes
        
        updated_visit = self.repository.save(visit)
        
        # Получаем клиента для audit
        client = self._get_client(visit.client_id)
        
        # Пишем audit
        self.audit.log(
            action="visits.exit",
            status="success",
            actor_user_id=actor_user_id,
            entity_type="visit",
            entity_id=updated_visit.id,
            message=f"Client {client.first_name} {client.last_name} exited",
            after_data={
                "client_id": visit.client_id,
                "client_name": f"{client.first_name} {client.last_name}",
                "duration_minutes": visit.duration_minutes,
            },
        )
        
        return updated_visit
    
    # ==========================================================
    # РУЧНОЕ ДОБАВЛЕНИЕ/УДАЛЕНИЕ
    # ==========================================================
    
    def manual_add(
        self,
        data: ManualVisitRequest,
        actor_user_id: str,
    ) -> Visit:
        """
        Ручное добавление посещения (менеджером).
        """
        # Проверяем клиента
        client = self._get_client(str(data.client_id))
        
        # Проверяем, нет ли активного посещения
        active_visit = self.repository.get_active_visit_by_client(str(data.client_id))
        if active_visit:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Клиент уже находится в клубе. Активное посещение: {active_visit.id}",
            )
        
        # Приводим времена к UTC
        entry_time = self._ensure_timezone_aware(data.entry_time)
        exit_time = self._ensure_timezone_aware(data.exit_time) if data.exit_time else None
        
        # Создаём посещение
        visit = Visit(
            client_id=str(data.client_id),
            subscription_id=str(data.subscription_id) if data.subscription_id else None,
            entry_time=entry_time,
            exit_time=exit_time,
            access_method=data.access_method.value,
            access_granted=True,
            status=VisitStatus.COMPLETED.value if exit_time else VisitStatus.ACTIVE.value,
            zone=data.zone,
            notes=data.notes,
            processed_by_user_id=actor_user_id,
        )
        
        # Если есть время выхода — рассчитываем длительность
        if exit_time:
            visit.duration_minutes = self._calculate_duration(entry_time, exit_time)
        
        created_visit = self.repository.add(visit)
        
        # Если есть абонемент и это не выход — списываем визит
        if data.subscription_id and not exit_time:
            subscription = self._get_subscription(str(data.subscription_id))
            if subscription:
                self._deduct_visit(subscription)
        
        # Пишем audit
        self.audit.log(
            action="visits.manual_add",
            status="success",
            actor_user_id=actor_user_id,
            entity_type="visit",
            entity_id=created_visit.id,
            message=f"Manual visit added for client {client.first_name} {client.last_name}",
            after_data={
                "client_id": str(data.client_id),
                "entry_time": str(entry_time),
                "exit_time": str(exit_time) if exit_time else None,
            },
        )
        
        return created_visit
    
    def cancel(
        self,
        visit_id: str,
        reason: str,
        actor_user_id: str | None = None,
    ) -> Visit:
        """
        Отменить посещение.
        """
        visit = self.repository.get_by_id(visit_id)
        
        if not visit:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Посещение не найдено",
            )
        
        if visit.status == VisitStatus.CANCELLED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Посещение уже отменено",
            )
        
        # Сохраняем старый статус
        old_status = visit.status
        
        # Меняем статус
        visit.status = VisitStatus.CANCELLED.value
        visit.notes = f"{visit.notes or ''}\nОтменено: {reason}".strip()
        
        updated_visit = self.repository.save(visit)
        
        # Если было списание визита — возвращаем его (TODO: логика возврата)
        # if old_status == VisitStatus.ACTIVE.value or old_status == VisitStatus.COMPLETED.value:
        #     if visit.subscription_id:
        #         subscription = self._get_subscription(visit.subscription_id)
        #         if subscription:
        #             subscription.visits_used -= 1
        #             self.db.commit()
        
        # Пишем audit
        self.audit.log(
            action="visits.cancel",
            status="success",
            actor_user_id=actor_user_id,
            entity_type="visit",
            entity_id=updated_visit.id,
            message=f"Visit cancelled. Reason: {reason}",
            after_data={
                "visit_id": visit_id,
                "old_status": old_status,
                "reason": reason,
            },
        )
        
        return updated_visit
    
    # ==========================================================
    # ПОЛУЧЕНИЕ ДАННЫХ
    # ==========================================================
    
    def get_visit(self, visit_id: str) -> Visit:
        """Получить посещение по ID"""
        visit = self.repository.get_by_id(visit_id)
        if not visit:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Посещение не найдено",
            )
        return visit
    
    def get_client_visits(
        self,
        client_id: str,
        limit: int = 100,
        offset: int = 0,
        status: str | None = None,
    ) -> VisitListResponse:
        """Получить историю посещений клиента"""
        # Проверяем существование клиента
        self._get_client(client_id)
        
        visits = self.repository.list_by_client(
            client_id=client_id,
            limit=limit,
            offset=offset,
            status=status,
        )
        
        return VisitListResponse(
            items=[self._build_response(v) for v in visits],
            count=len(visits),
        )
    
    def get_active_visits(self, zone: str | None = None) -> VisitListResponse:
        """Получить список активных посещений (клиенты в клубе)"""
        visits = self.repository.get_active_visits(zone=zone)
        
        return VisitListResponse(
            items=[self._build_response(v) for v in visits],
            count=len(visits),
        )
    
    def get_active_count(self, zone: str | None = None) -> int:
        """Получить количество клиентов в клубе"""
        return self.repository.get_active_visits_count(zone=zone)
    
    # ==========================================================
    # СТАТИСТИКА
    # ==========================================================
    
    def get_stats(
        self,
        period: str,
        start_date: date,
        end_date: date | None = None,
        zone: str | None = None,
    ) -> VisitStatsResponse:
        """
        Получить статистику посещений.
        
        Args:
            period: day, week, month, year
            start_date: начальная дата
            end_date: конечная дата (если не указана — start_date)
            zone: фильтр по зоне
        """
        if not end_date:
            end_date = start_date
        
        # Определяем диапазон в зависимости от периода
        if period == "week":
            end_date = start_date + timedelta(days=7)
        elif period == "month":
            end_date = start_date + timedelta(days=30)
        elif period == "year":
            end_date = start_date + timedelta(days=365)
        
        # Получаем базовую статистику
        base_stats = self.repository.get_stats_by_period(start_date, end_date, zone)
        
        # Получаем часы пик
        peak_hours = self.repository.get_peak_hours(start_date, end_date, zone)
        
        # Получаем распределение по дням
        visits_by_day = self.repository.get_visits_by_day(start_date, end_date, zone)
        
        # Получаем распределение по зонам (если не фильтруем по зоне)
        visits_by_zone = None
        if not zone:
            visits_by_zone = self.repository.get_visits_by_zone(start_date, end_date)
        
        return VisitStatsResponse(
            total_visits=base_stats["total_visits"],
            unique_clients=base_stats["unique_clients"],
            avg_duration_minutes=base_stats["avg_duration"],
            peak_hours=peak_hours,
            visits_by_day=visits_by_day,
            visits_by_zone=visits_by_zone,
        )
    
    # ==========================================================
    # ФОНОВЫЕ ЗАДАЧИ
    # ==========================================================
    
    def close_incomplete_visits(self, days_threshold: int = 1) -> int:
        """
        Закрыть незавершённые посещения (вход без выхода).
    
        Args:
            days_threshold: закрывать посещения старше N дней
    
        Returns:
            Количество закрытых посещений
        """
        from datetime import timezone
    
        threshold_date = datetime.now(timezone.utc) - timedelta(days=days_threshold)
    
        # Находим все незавершённые посещения старше порога
        incomplete_visits = (
            self.db.query(Visit)
            .filter(
                Visit.status == VisitStatus.ACTIVE.value,
                Visit.exit_time.is_(None),
                Visit.entry_time < threshold_date,
            )
            .all()
        )
    
        closed_count = 0
        for visit in incomplete_visits:
            # Устанавливаем время выхода = время входа + 1 час (или можно на конец дня)
            visit.exit_time = visit.entry_time + timedelta(hours=1)
            visit.duration_minutes = self._calculate_duration(visit.entry_time, visit.exit_time)
            visit.status = VisitStatus.COMPLETED.value
            closed_count += 1
    
        if closed_count > 0:
            self.db.commit()
        
            self.audit.log(
                action="visits.auto_close",
                status="success",
                actor_user_id=None,
                entity_type="system",
                message=f"Auto-closed {closed_count} incomplete visits",
                after_data={"closed_count": closed_count},
            )
    
        return closed_count