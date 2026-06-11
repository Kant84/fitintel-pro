# app/services/device_service.py

from uuid import UUID, uuid4
from datetime import datetime, timezone
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.device import Device
from app.repositories.device_repository import DeviceRepository
from app.services.audit_service import AuditService


VALID_DEVICE_TYPES = {"turnstile", "terminal", "controller", "reader", "locker", "barrier", "gate"}
VALID_PROTOCOLS = {"http", "mqtt", "modbus", "serial", "gpio", "tcp", "websocket", "none"}


class DeviceService:
    """Сервис управления устройствами доступа (турникеты, контроллеры, считыватели)"""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = DeviceRepository(db)
        self.audit = AuditService(db)

    # ============================================================
    # ВАЛИДАЦИЯ
    # ============================================================

    def _validate_type(self, device_type: str) -> None:
        if device_type not in VALID_DEVICE_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Недопустимый тип устройства: '{device_type}'. Допустимые: {', '.join(sorted(VALID_DEVICE_TYPES))}"
            )

    def _validate_protocol(self, protocol: str) -> None:
        if protocol not in VALID_PROTOCOLS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Недопустимый протокол: '{protocol}'. Допустимые: {', '.join(sorted(VALID_PROTOCOLS))}"
            )

    def _normalize_code(self, code: str) -> str:
        """Нормализовать код устройства"""
        code = code.strip().lower()
        code = code.replace(" ", "_").replace("-", "_")
        if len(code) < 3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Код устройства должен быть не менее 3 символов"
            )
        return code

    # ============================================================
    # CRUD
    # ============================================================

    def create(self, data: dict, actor_user_id: UUID | None = None) -> Device:
        """Создать новое устройство"""
        code = self._normalize_code(data["code"])

        # Проверка уникальности кода
        if self.repo.get_by_code(code):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Устройство с кодом '{code}' уже существует"
            )

        device_type = data.get("device_type", "turnstile")
        self._validate_type(device_type)

        protocol = data.get("protocol", "none")
        self._validate_protocol(protocol)

        device = Device(
            id=uuid4(),
            code=code,
            name=data["name"].strip(),
            device_type=device_type,
            manufacturer=data.get("manufacturer"),
            protocol=protocol,
            address=data.get("address"),
            config=data.get("config", {}),
            is_active=data.get("is_active", True),
            zone=data.get("zone"),
            notes=data.get("notes"),
            last_heartbeat_at=None,
        )

        self.repo.create(device)

        self.audit.log(
            action="device.create",
            status="success",
            actor_user_id=actor_user_id,
            target_device_id=device.id,
            message=f"Создано устройство {device.name} ({device.code})",
            after_data={
                "code": device.code,
                "name": device.name,
                "device_type": device.device_type,
                "protocol": device.protocol,
                "address": device.address,
                "zone": device.zone,
                "is_active": device.is_active,
            },
        )

        return device

    def get_by_id(self, device_id: UUID) -> Device:
        """Получить устройство по ID"""
        device = self.repo.get_by_id(device_id)
        if not device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Устройство не найдено"
            )
        return device

    def list_devices(
        self,
        offset: int = 0,
        limit: int = 100,
        device_type: str | None = None,
        is_active: bool | None = None,
        zone: str | None = None,
    ) -> dict:
        """Список устройств с пагинацией"""
        devices, total = self.repo.list_devices(offset, limit, device_type, is_active, zone)
        return {
            "items": [self._serialize(d) for d in devices],
            "total": total,
            "offset": offset,
            "limit": limit,
        }

    def update(self, device_id: UUID, data: dict, actor_user_id: UUID | None = None) -> Device:
        """Обновить устройство"""
        device = self.get_by_id(device_id)

        before = self._serialize(device)
        changed_fields = []

        # Обновляемые поля
        field_map = {
            "name": "name",
            "manufacturer": "manufacturer",
            "address": "address",
            "config": "config",
            "is_active": "is_active",
            "zone": "zone",
            "notes": "notes",
        }

        for json_key, attr_name in field_map.items():
            if json_key in data:
                old_val = getattr(device, attr_name)
                new_val = data[json_key]
                if old_val != new_val:
                    setattr(device, attr_name, new_val)
                    changed_fields.append(json_key)

        # Специальная валидация для type/protocol
        if "device_type" in data:
            self._validate_type(data["device_type"])
            if device.device_type != data["device_type"]:
                changed_fields.append("device_type")
                device.device_type = data["device_type"]

        if "protocol" in data:
            self._validate_protocol(data["protocol"])
            if device.protocol != data["protocol"]:
                changed_fields.append("protocol")
                device.protocol = data["protocol"]

        if "code" in data:
            new_code = self._normalize_code(data["code"])
            if new_code != device.code:
                existing = self.repo.get_by_code(new_code)
                if existing and existing.id != device.id:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Код '{new_code}' уже занят"
                    )
                changed_fields.append("code")
                device.code = new_code

        if changed_fields:
            device.updated_at = datetime.now(timezone.utc)
            self.repo.update(device)

            self.audit.log(
                action="device.update",
                status="success",
                actor_user_id=actor_user_id,
                target_device_id=device.id,
                message=f"Обновлено устройство {device.name}",
                before_data=before,
                after_data=self._serialize(device),
                changed_fields=changed_fields,
            )

        return device

    def delete(self, device_id: UUID, actor_user_id: UUID | None = None) -> None:
        """Удалить устройство"""
        device = self.get_by_id(device_id)
        name = device.name

        self.audit.log(
            action="device.delete",
            status="success",
            actor_user_id=actor_user_id,
            target_device_id=device.id,
            message=f"Удалено устройство {name}",
            before_data=self._serialize(device),
        )

        self.repo.delete(device)

    # ============================================================
    # HEARTBEAT / HEALTH
    # ============================================================

    def heartbeat(self, device_id: UUID) -> dict:
        """Обработать heartbeat от устройства"""
        device = self.get_by_id(device_id)
        now = datetime.now(timezone.utc)
        device.last_heartbeat_at = now
        self.repo.update(device)

        return {
            "device_id": str(device.id),
            "status": "ok",
            "timestamp": now.isoformat(),
            "device_name": device.name,
        }

    def check_health(self, device_id: UUID) -> dict:
        """Проверить здоровье устройства"""
        device = self.get_by_id(device_id)

        now = datetime.now(timezone.utc)
        last_hb = device.last_heartbeat_at

        if not last_hb:
            status_code = "unknown"
            seconds_since_hb = None
        else:
            seconds_since_hb = int((now - last_hb).total_seconds())
            if seconds_since_hb < 60:
                status_code = "online"
            elif seconds_since_hb < 300:
                status_code = "warning"
            else:
                status_code = "offline"

        return {
            "device_id": str(device.id),
            "name": device.name,
            "status": status_code,
            "is_active": device.is_active,
            "last_heartbeat_at": last_hb.isoformat() if last_hb else None,
            "seconds_since_heartbeat": seconds_since_hb,
            "device_type": device.device_type,
            "protocol": device.protocol,
            "address": device.address,
        }

    def get_health_all(self) -> dict:
        """Здоровье всех устройств"""
        devices = self.repo.get_all_active()
        now = datetime.now(timezone.utc)
        online = warning = offline = 0

        items = []
        for d in devices:
            if not d.last_heartbeat_at:
                st = "unknown"
                offline += 1
            else:
                sec = (now - d.last_heartbeat_at).total_seconds()
                if sec < 60:
                    st = "online"
                    online += 1
                elif sec < 300:
                    st = "warning"
                    warning += 1
                else:
                    st = "offline"
                    offline += 1

            items.append({
                "id": str(d.id),
                "name": d.name,
                "code": d.code,
                "status": st,
                "type": d.device_type,
            })

        total = len(devices)
        return {
            "total": total,
            "online": online,
            "warning": warning,
            "offline": offline,
            "unknown": total - online - warning - offline,
            "items": items,
        }

    # ============================================================
    # СТАТИСТИКА
    # ============================================================

    def get_stats(self) -> dict:
        """Статистика по устройствам"""
        by_type = self.repo.count_by_type()
        all_devices, total = self.repo.list_devices(limit=9999)
        active_count = sum(1 for d in all_devices if d.is_active)

        return {
            "total": total,
            "active": active_count,
            "inactive": total - active_count,
            "by_type": by_type,
            "by_protocol": self._count_by_field(all_devices, "protocol"),
            "by_zone": self._count_by_field(all_devices, "zone"),
        }

    # ============================================================
    # ВСПОМОГАТЕЛЬНЫЕ
    # ============================================================

    @staticmethod
    def _serialize(device: Device) -> dict:
        return {
            "id": str(device.id),
            "code": device.code,
            "name": device.name,
            "device_type": device.device_type,
            "manufacturer": device.manufacturer,
            "protocol": device.protocol,
            "address": device.address,
            "config": device.config or {},
            "is_active": device.is_active,
            "zone": device.zone,
            "notes": device.notes,
            "last_heartbeat_at": device.last_heartbeat_at.isoformat() if device.last_heartbeat_at else None,
            "created_at": device.created_at.isoformat() if device.created_at else None,
            "updated_at": device.updated_at.isoformat() if device.updated_at else None,
        }

    @staticmethod
    def _count_by_field(devices: list[Device], field: str) -> dict[str, int]:
        counts: dict[str, int] = {}
        for d in devices:
            val = getattr(d, field, None) or "unspecified"
            counts[val] = counts.get(val, 0) + 1
        return counts
