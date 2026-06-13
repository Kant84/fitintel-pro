# app/repositories/device_repository.py

from uuid import UUID
from sqlalchemy import select, desc
from sqlalchemy.orm import Session
from app.models.device import Device


class DeviceRepository:
    """Репозиторий устройств доступа (турникеты, контроллеры, считыватели)"""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, device_id: UUID) -> Device | None:
        """Получить устройство по ID"""
        return self.db.execute(
            select(Device).where(Device.id == device_id)
        ).scalar_one_or_none()

    def get_by_code(self, code: str) -> Device | None:
        """Получить устройство по уникальному коду"""
        return self.db.execute(
            select(Device).where(Device.code == code)
        ).scalar_one_or_none()

    def list_devices(
        self,
        offset: int = 0,
        limit: int = 100,
        device_type: str | None = None,
        is_active: bool | None = None,
        zone: str | None = None,
    ) -> tuple[list[Device], int]:
        """Список устройств с фильтрами и общим количеством"""
        query = select(Device)
        count_query = select(Device)

        if device_type:
            query = query.where(Device.device_type == device_type)
            count_query = count_query.where(Device.device_type == device_type)
        if is_active is not None:
            query = query.where(Device.is_active == is_active)
            count_query = count_query.where(Device.is_active == is_active)
        if zone:
            query = query.where(Device.zone == zone)
            count_query = count_query.where(Device.zone == zone)

        query = query.order_by(desc(Device.created_at)).offset(offset).limit(limit)

        devices = list(self.db.execute(query).scalars().all())
        total = self.db.execute(
            select(count_query.c).select_from(count_query.subquery())
        ).scalar() or 0
        return devices, total

    def create(self, device: Device) -> Device:
        """Создать устройство"""
        self.db.add(device)
        self.db.commit()
        self.db.refresh(device)
        return device

    def update(self, device: Device) -> Device:
        """Обновить устройство"""
        self.db.commit()
        self.db.refresh(device)
        return device

    def delete(self, device: Device) -> None:
        """Удалить устройство"""
        self.db.delete(device)
        self.db.commit()

    def update_heartbeat(self, device_id: UUID) -> None:
        """Обновить timestamp heartbeat"""
        from datetime import datetime, timezone
        device = self.get_by_id(device_id)
        if device:
            device.last_heartbeat_at = datetime.now(timezone.utc)
            self.db.commit()

    def get_active_by_type(self, device_type: str) -> list[Device]:
        """Получить активные устройства по типу"""
        return list(self.db.execute(
            select(Device)
            .where(Device.device_type == device_type)
            .where(Device.is_active == True)
            .order_by(Device.name)
        ).scalars().all())

    def get_all_active(self) -> list[Device]:
        """Все активные устройства"""
        return list(self.db.execute(
            select(Device)
            .where(Device.is_active == True)
            .order_by(Device.name)
        ).scalars().all())

    def count_by_type(self) -> dict[str, int]:
        """Количество устройств по типам"""
        from sqlalchemy import func
        rows = self.db.execute(
            select(Device.device_type, func.count(Device.id))
            .group_by(Device.device_type)
        ).all()
        return {row[0]: row[1] for row in rows}
