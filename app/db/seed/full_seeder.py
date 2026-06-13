# app/db/seed/full_seeder.py
"""
Полный seeder для FitIntel Pro.
Заполняет БД: роли, права, системный пользователь, демо-тарифы, демо-клиенты.
Использование: python -m app.db.seed.full_seeder
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from uuid import uuid4
from datetime import datetime, timezone, timedelta, date
from passlib.context import CryptContext

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.base import Base
from app.models.user import User
from app.models.client import Client
from app.models.tariff import Tariff
from app.models.role_permission import Role, Permission, role_permission
from app.models.gamification_level import GamificationLevel
from app.models.device import Device

# Создаем engine напрямую
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ============================================================
# РОЛИ
# ============================================================
ROLES = [
    {"id": "role-superadmin", "code": "superadmin", "name": "Супер-администратор", "description": "Полный доступ к системе"},
    {"id": "role-admin", "code": "admin", "name": "Администратор клуба", "description": "Управление клубом"},
    {"id": "role-manager", "code": "manager", "name": "Менеджер", "description": "Управление клиентами и продажи"},
    {"id": "role-trainer", "code": "trainer", "name": "Тренер", "description": "Проведение тренировок"},
    {"id": "role-cashier", "code": "cashier", "name": "Кассир", "description": "Работа с кассой и платежами"},
    {"id": "role-receptionist", "code": "receptionist", "name": "Администратор рецепции", "description": "Регистрация клиентов, доступ"},
    {"id": "role-accountant", "code": "accountant", "name": "Бухгалтер", "description": "Финансы и отчётность"},
    {"id": "role-client", "code": "client", "name": "Клиент", "description": "Self-service доступ"},
    {"id": "role-guest", "code": "guest", "name": "Гость", "description": "Только чтение публичных данных"},
]

# ============================================================
# ПРАВА (51 permission)
# ============================================================
PERMISSIONS = [
    # Users
    {"id": "perm-users-read", "code": "users.read", "name": "Чтение пользователей", "module": "users"},
    {"id": "perm-users-create", "code": "users.create", "name": "Создание пользователей", "module": "users"},
    {"id": "perm-users-update", "code": "users.update", "name": "Обновление пользователей", "module": "users"},
    {"id": "perm-users-delete", "code": "users.delete", "name": "Удаление пользователей", "module": "users"},
    # Clients
    {"id": "perm-clients-read", "code": "clients.read", "name": "Чтение клиентов", "module": "clients"},
    {"id": "perm-clients-create", "code": "clients.create", "name": "Создание клиентов", "module": "clients"},
    {"id": "perm-clients-update", "code": "clients.update", "name": "Обновление клиентов", "module": "clients"},
    {"id": "perm-clients-delete", "code": "clients.delete", "name": "Удаление клиентов", "module": "clients"},
    # Tariffs
    {"id": "perm-tariffs-read", "code": "tariffs.read", "name": "Чтение тарифов", "module": "tariffs"},
    {"id": "perm-tariffs-create", "code": "tariffs.create", "name": "Создание тарифов", "module": "tariffs"},
    {"id": "perm-tariffs-update", "code": "tariffs.update", "name": "Обновление тарифов", "module": "tariffs"},
    {"id": "perm-tariffs-delete", "code": "tariffs.delete", "name": "Удаление тарифов", "module": "tariffs"},
    # Subscriptions
    {"id": "perm-subscriptions-read", "code": "subscriptions.read", "name": "Чтение абонементов", "module": "subscriptions"},
    {"id": "perm-subscriptions-create", "code": "subscriptions.create", "name": "Создание абонементов", "module": "subscriptions"},
    {"id": "perm-subscriptions-update", "code": "subscriptions.update", "name": "Обновление абонементов", "module": "subscriptions"},
    {"id": "perm-subscriptions-delete", "code": "subscriptions.delete", "name": "Удаление абонементов", "module": "subscriptions"},
    # Visits
    {"id": "perm-visits-read", "code": "visits.read", "name": "Чтение посещений", "module": "visits"},
    {"id": "perm-visits-create", "code": "visits.create", "name": "Создание посещений", "module": "visits"},
    {"id": "perm-visits-update", "code": "visits.update", "name": "Обновление посещений", "module": "visits"},
    {"id": "perm-visits-delete", "code": "visits.delete", "name": "Удаление посещений", "module": "visits"},
    # Access
    {"id": "perm-access-read", "code": "access.read", "name": "Чтение доступа", "module": "access"},
    {"id": "perm-access-create", "code": "access.create", "name": "Управление доступом", "module": "access"},
    {"id": "perm-access-update", "code": "access.update", "name": "Обновление доступа", "module": "access"},
    # Payments
    {"id": "perm-payments-read", "code": "payments.read", "name": "Чтение платежей", "module": "payments"},
    {"id": "perm-payments-create", "code": "payments.create", "name": "Создание платежей", "module": "payments"},
    {"id": "perm-payments-update", "code": "payments.update", "name": "Обновление платежей", "module": "payments"},
    {"id": "perm-payments-delete", "code": "payments.delete", "name": "Удаление платежей", "module": "payments"},
    # Cash Desk
    {"id": "perm-cashdesk-read", "code": "cash_desk.read", "name": "Чтение кассы", "module": "cash_desk"},
    {"id": "perm-cashdesk-create", "code": "cash_desk.create", "name": "Операции кассы", "module": "cash_desk"},
    {"id": "perm-cashdesk-close", "code": "cash_desk.close", "name": "Закрытие смены", "module": "cash_desk"},
    # Sales
    {"id": "perm-sales-read", "code": "sales.read", "name": "Чтение продаж", "module": "sales"},
    {"id": "perm-sales-create", "code": "sales.create", "name": "Создание продаж", "module": "sales"},
    # Devices
    {"id": "perm-devices-read", "code": "devices.read", "name": "Чтение устройств", "module": "devices"},
    {"id": "perm-devices-create", "code": "devices.create", "name": "Создание устройств", "module": "devices"},
    {"id": "perm-devices-update", "code": "devices.update", "name": "Обновление устройств", "module": "devices"},
    {"id": "perm-devices-delete", "code": "devices.delete", "name": "Удаление устройств", "module": "devices"},
    # Analytics
    {"id": "perm-analytics-read", "code": "analytics.read", "name": "Чтение аналитики", "module": "analytics"},
    {"id": "perm-analytics-dashboard", "code": "analytics.dashboard", "name": "Дашборд", "module": "analytics"},
    # Marketing
    {"id": "perm-marketing-read", "code": "marketing.read", "name": "Чтение маркетинга", "module": "marketing"},
    {"id": "perm-marketing-create", "code": "marketing.create", "name": "Создание кампаний", "module": "marketing"},
    {"id": "perm-marketing-send", "code": "marketing.send", "name": "Отправка рассылок", "module": "marketing"},
    # Gamification
    {"id": "perm-gamification-read", "code": "gamification.read", "name": "Чтение геймификации", "module": "gamification"},
    # Online Training
    {"id": "perm-online-training-read", "code": "online_training.read", "name": "Чтение тренировок", "module": "online_training"},
    {"id": "perm-online-training-create", "code": "online_training.create", "name": "Создание тренировок", "module": "online_training"},
    {"id": "perm-online-training-update", "code": "online_training.update", "name": "Обновление тренировок", "module": "online_training"},
    {"id": "perm-online-training-delete", "code": "online_training.delete", "name": "Удаление тренировок", "module": "online_training"},
    # Documents
    {"id": "perm-documents-read", "code": "documents.read", "name": "Чтение документов", "module": "documents"},
    {"id": "perm-documents-create", "code": "documents.create", "name": "Создание документов", "module": "documents"},
    {"id": "perm-documents-update", "code": "documents.update", "name": "Обновление документов", "module": "documents"},
    # Hardware
    {"id": "perm-hardware-read", "code": "hardware.read", "name": "Чтение hardware", "module": "hardware"},
    {"id": "perm-hardware-control", "code": "hardware.control", "name": "Управление hardware", "module": "hardware"},
    # Self-Service
    {"id": "perm-selfservice-read", "code": "selfservice.read", "name": "Self-service чтение", "module": "selfservice"},
]

# ============================================================
# ROLE-PERMISSION MAPPING
# ============================================================
ROLE_PERMISSIONS = {
    "superadmin": [p["code"] for p in PERMISSIONS],
    "admin": [
        "users.read", "users.create", "users.update", "clients.read", "clients.create", "clients.update",
        "tariffs.read", "tariffs.create", "tariffs.update", "subscriptions.read", "subscriptions.create",
        "visits.read", "visits.create", "access.read", "access.create", "payments.read", "payments.create",
        "cash_desk.read", "cash_desk.create", "sales.read", "sales.create",
        "devices.read", "devices.create", "devices.update", "analytics.read", "analytics.dashboard",
        "marketing.read", "marketing.create", "marketing.send", "gamification.read",
        "online_training.read", "online_training.create", "online_training.update",
        "documents.read", "documents.create", "hardware.read", "hardware.control",
    ],
    "manager": [
        "clients.read", "clients.create", "clients.update", "subscriptions.read", "subscriptions.create",
        "visits.read", "payments.read", "sales.read", "sales.create", "analytics.read",
        "marketing.read", "marketing.create", "gamification.read",
    ],
    "trainer": [
        "clients.read", "visits.read", "visits.create", "gamification.read",
        "online_training.read", "online_training.create",
    ],
    "cashier": [
        "payments.read", "payments.create", "cash_desk.read", "cash_desk.create", "cash_desk.close",
        "sales.read", "sales.create", "clients.read",
    ],
    "receptionist": [
        "clients.read", "clients.create", "clients.update", "visits.read", "visits.create",
        "access.read", "access.create", "subscriptions.read", "subscriptions.create",
    ],
    "accountant": [
        "payments.read", "analytics.read", "analytics.dashboard",
    ],
    "client": [
        "selfservice.read", "gamification.read",
    ],
    "guest": [],
}


# ============================================================
# DEMO TARIFFS
# ============================================================
DEMO_TARIFFS = [
    {"name": "Разовое посещение", "description": "Одно посещение любой зоны", "price": 800, "duration_days": 1, "type": "single", "is_active": True},
    {"name": "Базовый (1 месяц)", "description": "Тренажёрный зал, безлимит", "price": 3500, "duration_days": 30, "type": "subscription", "is_active": True},
    {"name": "Стандарт (3 месяца)", "description": "Тренажёрный зал + групповые", "price": 9000, "duration_days": 90, "type": "subscription", "is_active": True},
    {"name": "Премиум (6 месяцев)", "description": "Всё включено + бассейн + сауна", "price": 15000, "duration_days": 180, "type": "subscription", "is_active": True},
    {"name": "VIP (12 месяцев)", "description": "Полный доступ + персональный тренер", "price": 25000, "duration_days": 365, "type": "subscription", "is_active": True},
    {"name": "Дневной (6:00-16:00)", "description": "Только дневные часы", "price": 2500, "duration_days": 30, "type": "subscription", "is_active": True},
    {"name": "Студенческий", "description": "Скидка 30% при предъявлении студ. билета", "price": 2100, "duration_days": 30, "type": "subscription", "is_active": True},
    {"name": "Пенсионный", "description": "Скидка 40% для пенсионеров", "price": 1800, "duration_days": 30, "type": "subscription", "is_active": True},
    {"name": "Семейный (2+1)", "description": "Два взрослых + один ребёнок", "price": 5500, "duration_days": 30, "type": "subscription", "is_active": True},
    {"name": "Корпоративный", "description": "Для компаний от 5 человек", "price": 12000, "duration_days": 30, "type": "corporate", "is_active": True},
]


# ============================================================
# DEMO CLIENTS
# ============================================================
DEMO_CLIENTS = [
    {"first_name": "Иван", "last_name": "Петров", "middle_name": "Сергеевич", "phone": "+79161234567", "email": "ivan.petrov@mail.ru", "gender": "МУЖСКОЙ", "birth_date": date(1990, 5, 15)},
    {"first_name": "Мария", "last_name": "Иванова", "middle_name": "Алексеевна", "phone": "+79162345678", "email": "maria.ivanova@mail.ru", "gender": "ЖЕНСКИЙ", "birth_date": date(1988, 3, 22)},
    {"first_name": "Алексей", "last_name": "Смирнов", "middle_name": "Дмитриевич", "phone": "+79163456789", "email": "alexey.smirnov@mail.ru", "gender": "МУЖСКОЙ", "birth_date": date(1995, 8, 10)},
    {"first_name": "Елена", "last_name": "Козлова", "middle_name": "Владимировна", "phone": "+79164567890", "email": "elena.kozlova@mail.ru", "gender": "ЖЕНСКИЙ", "birth_date": date(1992, 11, 5)},
    {"first_name": "Дмитрий", "last_name": "Волков", "middle_name": "Андреевич", "phone": "+79165678901", "email": "dmitry.volkov@mail.ru", "gender": "МУЖСКОЙ", "birth_date": date(1985, 1, 30)},
]


# ============================================================
# DEMO DEVICES
# ============================================================
DEMO_DEVICES = [
    {"code": "turnstile_main", "name": "Турникет главный вход", "device_type": "turnstile", "manufacturer": "ЭРА", "protocol": "tcp", "address": "192.168.1.10:5000", "zone": "Входная группа"},
    {"code": "turnstile_back", "name": "Турникет задний вход", "device_type": "turnstile", "manufacturer": "ЭРА", "protocol": "tcp", "address": "192.168.1.11:5000", "zone": "Задний вход"},
    {"code": "controller_pool", "name": "Контроллер бассейн", "device_type": "controller", "manufacturer": "X1", "protocol": "http_api", "address": "192.168.1.20:8080", "zone": "Бассейн"},
    {"code": "locker_a", "name": "Шкафчики зона A", "device_type": "locker", "manufacturer": "Kerong", "protocol": "modbus_tcp", "address": "192.168.1.30:502", "zone": "Раздевалка A"},
    {"code": "barrier_parking", "name": "Шлагбаум парковка", "device_type": "barrier", "manufacturer": "Generic", "protocol": "http_api", "address": "192.168.1.40:80", "zone": "Парковка"},
]


def seed_all():
    """Запускает полный seed"""
    db = SessionLocal()
    now = datetime.now(timezone.utc)

    try:
        # 1. Проверяем, есть ли уже данные
        existing_roles = db.query(Role).count()
        if existing_roles > 0:
            print(f"  ⚠  Найдено {existing_roles} ролей. Пропускаем seed (уже заполнено).")
            print("  Для принудительного пересоздания: удалите таблицы или используйте --force")
            return

        print("=== FitIntel Pro — Full Seeder ===\n")

        # 2. Роли
        print("1. Создаём роли...")
        role_objs = {}
        for r in ROLES:
            role = Role(id=r["id"], code=r["code"], name=r["name"], description=r["description"])
            db.add(role)
            role_objs[r["code"]] = role
        db.commit()
        print(f"   ✓ {len(ROLES)} ролей создано")

        # 3. Права
        print("2. Создаём права...")
        perm_objs = {}
        for p in PERMISSIONS:
            perm = Permission(id=p["id"], code=p["code"], name=p["name"], module=p["module"])
            db.add(perm)
            perm_objs[p["code"]] = perm
        db.commit()
        print(f"   ✓ {len(PERMISSIONS)} прав создано")

        # 4. Связи role-permission
        print("3. Связываем роли с правами...")
        for role_code, perm_codes in ROLE_PERMISSIONS.items():
            role = role_objs[role_code]
            for perm_code in perm_codes:
                if perm_code in perm_objs:
                    db.execute(role_permission.insert().values(
                        role_id=role.id,
                        permission_id=perm_objs[perm_code].id
                    ))
        db.commit()
        print(f"   ✓ Связи назначены")

        # 5. Системный пользователь (admin)
        print("4. Создаём системного пользователя...")
        admin_id = str(uuid4())
        admin = User(
            id=admin_id,
            username="admin",
            email="admin@fitintel.pro",
            hashed_password=pwd_context.hash("admin123"),
            first_name="Администратор",
            last_name="Системы",
            is_active=True,
            is_superuser=True,
            created_at=now,
            updated_at=now,
        )
        db.add(admin)
        db.commit()
        print(f"   ✓ admin/admin123 создан (ID: {admin_id})")

        # 6. Тарифы
        print("5. Создаём демо-тарифы...")
        for t in DEMO_TARIFFS:
            tariff = Tariff(
                id=str(uuid4()),
                name=t["name"],
                description=t["description"],
                price=t["price"],
                duration_days=t["duration_days"],
                type=t["type"],
                is_active=t["is_active"],
                created_at=now,
                updated_at=now,
            )
            db.add(tariff)
        db.commit()
        print(f"   ✓ {len(DEMO_TARIFFS)} тарифов создано")

        # 7. Демо-клиенты
        print("6. Создаём демо-клиентов...")
        for c in DEMO_CLIENTS:
            client_id = str(uuid4())
            client = Client(
                id=client_id,
                first_name=c["first_name"],
                last_name=c["last_name"],
                middle_name=c.get("middle_name"),
                phone=c["phone"],
                email=c.get("email"),
                gender=c.get("gender", "НЕ_УКАЗАН"),
                birth_date=c.get("birth_date"),
                status="ACTIVE",
                is_active=True,
                created_at=now,
                updated_at=now,
            )
            db.add(client)

            # Gamification level для каждого клиента
            gamification = GamificationLevel(
                id=str(uuid4()),
                client_id=client_id,
                level=1,
                current_xp=0,
                xp_to_next=100,
            )
            db.add(gamification)
        db.commit()
        print(f"   ✓ {len(DEMO_CLIENTS)} клиентов создано")

        # 8. Демо-устройства
        print("7. Создаём демо-устройства СКУД...")
        for d in DEMO_DEVICES:
            device = Device(
                id=str(uuid4()),
                code=d["code"],
                name=d["name"],
                device_type=d["device_type"],
                manufacturer=d.get("manufacturer"),
                protocol=d["protocol"],
                address=d.get("address"),
                is_active=True,
                zone=d.get("zone"),
                created_at=now,
                updated_at=now,
            )
            db.add(device)
        db.commit()
        print(f"   ✓ {len(DEMO_DEVICES)} устройств создано")

        print(f"\n=== SEED ЗАВЕРШЁН ===")
        print(f"Ролей:       {len(ROLES)}")
        print(f"Прав:        {len(PERMISSIONS)}")
        print(f"Тарифов:     {len(DEMO_TARIFFS)}")
        print(f"Клиентов:    {len(DEMO_CLIENTS)}")
        print(f"Устройств:   {len(DEMO_DEVICES)}")
        print(f"\nЛогин: admin / admin123")

    except Exception as e:
        db.rollback()
        print(f"\n✗ Ошибка: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="FitIntel Pro Full Seeder")
    parser.add_argument("--force", action="store_true", help="Принудительно пересоздать")
    args = parser.parse_args()

    if args.force:
        # Удаляем существующие данные
        db = SessionLocal()
        try:
            print("⚠  Принудительный режим — удаляем данные...")
            db.execute(role_permission.delete())
            for model in [User, Client, Tariff, Role, Permission, GamificationLevel, Device]:
                db.query(model).delete(synchronize_session=False)
            db.commit()
            print("   ✓ Данные удалены")
        finally:
            db.close()

    seed_all()
