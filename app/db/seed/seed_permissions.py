# app/db/seed/seed_permissions.py

# импорт модели права
from app.models.permission import Permission

# импорт модели роли
from app.models.role import Role

# импорт модели связи роль-право
from app.models.role_permission import RolePermission


# список системных прав
SYSTEM_PERMISSIONS = [
    {
        "code": "users.read",
        "name": "Read users",
        "module": "users",
        "description": "Просмотр пользователей.",
    },
    {
        "code": "users.create",
        "name": "Create users",
        "module": "users",
        "description": "Создание пользователей.",
    },
    {
        "code": "users.update",
        "name": "Update users",
        "module": "users",
        "description": "Изменение пользователей.",
    },
    {
        "code": "roles.read",
        "name": "Read roles",
        "module": "roles",
        "description": "Просмотр ролей.",
    },
    {
        "code": "roles.manage",
        "name": "Manage roles",
        "module": "roles",
        "description": "Управление ролями.",
    },
    {
        "code": "permissions.read",
        "name": "Read permissions",
        "module": "permissions",
        "description": "Просмотр прав.",
    },
    {
        "code": "club_settings.read",
        "name": "Read club settings",
        "module": "club_settings",
        "description": "Просмотр настроек клуба.",
    },
    {
        "code": "club_settings.update",
        "name": "Update club settings",
        "module": "club_settings",
        "description": "Изменение настроек клуба.",
    },
    {
        "code": "audit.read",
        "name": "Read audit logs",
        "module": "audit",
        "description": "Просмотр журнала аудита.",
    },
    {
        "code": "system.admin",
        "name": "System administration",
        "module": "system",
        "description": "Полное системное администрирование.",
    },
    {
        "code": "clients.read",
        "name": "Read clients",
        "module": "clients",
        "description": "Просмотр клиентов.",
    },
    {
        "code": "clients.create",
        "name": "Create clients",
        "module": "clients",
        "description": "Создание клиентов.",
    },
    {
        "code": "clients.update",
        "name": "Update clients",
        "module": "clients",
        "description": "Изменение клиентов.",
    },
    {
        "code": "tariffs.read",
        "name": "Read tariffs",
        "module": "tariffs",
        "description": "Просмотр тарифов.",
    },
    {
        "code": "tariffs.create",
        "name": "Create tariffs",
        "module": "tariffs",
        "description": "Создание тарифов.",
    },
    {
        "code": "tariffs.update",
        "name": "Update tariffs",
        "module": "tariffs",
        "description": "Изменение тарифов.",
    },
    {
        "code": "subscriptions.read",
        "name": "Read subscriptions",
        "module": "subscriptions",
        "description": "Просмотр абонементов.",
    },
    {
        "code": "subscriptions.create",
        "name": "Create subscriptions",
        "module": "subscriptions",
        "description": "Создание абонементов.",
    },
    {
        "code": "subscriptions.update",
        "name": "Update subscriptions",
        "module": "subscriptions",
        "description": "Изменение абонементов.",
    },
    {
        "code": "subscriptions.freeze",
        "name": "Freeze subscriptions",
        "module": "subscriptions",
        "description": "Право на заморозку абонемента",
    },
    {
        "code": "subscriptions.renew",
        "name": "Renew subscriptions",
        "module": "subscriptions",
        "description": "Право на продление абонемента",
    },
    {
        "code": "subscriptions.cancel",
        "name": "Cancel subscriptions",
        "module": "subscriptions",
        "description": "Право на отмену абонемента",
    },
    {
        "code": "subscriptions.history",
        "name": "View subscription history",
        "module": "subscriptions",
        "description": "Право на просмотр истории абонемента",
    },

    # ==========================================================
    # НАСТРОЙКИ (SETTINGS) — требуются роутером /setup
    # ==========================================================

    {"code": "settings.read", "name": "Read settings", "module": "settings",
     "description": "Просмотр настроек системы"},

    {"code": "settings.update", "name": "Update settings", "module": "settings",
     "description": "Изменение настроек системы"},

    # ==========================================================
    # УСТРОЙСТВА (DEVICES)
    # ==========================================================

    {"code": "devices.read", "name": "Read devices", "module": "devices",
     "description": "Просмотр устройств"},

    {"code": "devices.create", "name": "Create devices", "module": "devices",
     "description": "Добавление устройств"},

    {"code": "devices.update", "name": "Update devices", "module": "devices",
     "description": "Изменение устройств"},

    {"code": "devices.delete", "name": "Delete devices", "module": "devices",
     "description": "Удаление устройств"},

    # ==========================================================
    # МАСТЕР УСТАНОВКИ (SETUP)
    # ==========================================================

    {"code": "setup.read", "name": "Read setup", "module": "setup",
     "description": "Просмотр шагов мастера установки"},

    {"code": "setup.write", "name": "Write setup", "module": "setup",
     "description": "Выполнение шагов мастера установки"},

    # ==========================================================
    # УСЛУГИ (SERVICES)
    # ==========================================================
    {"code": "services.read", "name": "Read services", "module": "services",
     "description": "Просмотр услуг"},

    {"code": "services.create", "name": "Create services", "module": "services",
     "description": "Создание услуг"},

    {"code": "services.update", "name": "Update services", "module": "services",
     "description": "Изменение услуг"},

    {"code": "services.delete", "name": "Delete services", "module": "services",
     "description": "Удаление услуг"},

    # ==========================================================
    # ДОКУМЕНТЫ (DOCUMENTS)
    # ==========================================================

    {"code": "documents.read", "name": "Read documents", "module": "documents",
     "description": "Просмотр документов"},

    {"code": "documents.create", "name": "Create documents", "module": "documents",
     "description": "Генерация документов"},

    {"code": "documents.delete", "name": "Delete documents", "module": "documents",
     "description": "Удаление документов"},

    # ==========================================================
    # FACE ID
    # ==========================================================

    {"code": "face.read", "name": "Read face templates", "module": "face_id",
     "description": "Просмотр шаблонов лиц"},

    {"code": "face.manage", "name": "Manage face templates", "module": "face_id",
     "description": "Управление шаблонами лиц"},

    # ==========================================================
    # UI-КОНФИГ (ЭКРАНЫ РОЛЕЙ)
    # ==========================================================
    {"code": "ui-config.read", "name": "Read UI config", "module": "ui_config",
     "description": "Просмотр настройки экранов ролей"},

    {"code": "ui-config.update", "name": "Update UI config", "module": "ui_config",
     "description": "Настройка экранов ролей"},

    # ==========================================================
    # ПРАВА ДЛЯ ПОСЕЩЕНИЙ (VISITS)
    # ==========================================================
    {
        "code": "visits.read",
        "name": "Read visits",
        "module": "visits",
        "description": "Просмотр посещений",
    },
    {
        "code": "visits.create",
        "name": "Create visits",
        "module": "visits",
        "description": "Создание посещений (вход)",
    },
    {
        "code": "visits.update",
        "name": "Update visits",
        "module": "visits",
        "description": "Обновление посещений (выход, ручное редактирование)",
    },
    {
        "code": "visits.delete",
        "name": "Delete visits",
        "module": "visits",
        "description": "Отмена посещений",
    },
    {
        "code": "access.override",
        "name": "Override access",
        "module": "access",
        "description": "Принудительное открытие турникета",
    },

    # ==========================================================
    # ПРАВА ДЛЯ УЧЁТНЫХ ДАННЫХ (CREDENTIALS)
    # ==========================================================
    {
        "code": "credentials.read",
        "name": "Read credentials",
        "module": "credentials",
        "description": "Просмотр учётных данных",
    },
    {
        "code": "credentials.create",
        "name": "Create credentials",
        "module": "credentials",
        "description": "Создание учётных данных (QR, RFID)",
    },
    {
        "code": "credentials.update",
        "name": "Update credentials",
        "module": "credentials",
        "description": "Изменение учётных данных",
    },
    {
        "code": "credentials.delete",
        "name": "Delete credentials",
        "module": "credentials",
        "description": "Удаление учётных данных",
    },

    # ==========================================================
    # ПРАВА ДЛЯ КЭША ДОСТУПА
    # ==========================================================
    {
        "code": "access.cache.manage",
        "name": "Manage access cache",
        "module": "access",
        "description": "Управление кэшем доступа (офлайн-режим)",
    },

    # ==========================================================
    # ПРАВА ДЛЯ ШКАФЧИКОВ
    # ==========================================================
    {
        "code": "lockers.read",
        "name": "Read lockers",
        "module": "lockers",
        "description": "Просмотр шкафчиков",
    },
    {
        "code": "lockers.assign",
        "name": "Assign lockers",
        "module": "lockers",
        "description": "Выбор и закрытие шкафчиков",
    },
    {
        "code": "lockers.update",
        "name": "Update lockers",
        "module": "lockers",
        "description": "Обновление статуса шкафчиков",
    },
    {
        "code": "lockers.manage",
        "name": "Manage lockers",
        "module": "lockers",
        "description": "Полное управление шкафчиками (админ)",
    },
    
    # ==========================================================
    # ПРАВА ДЛЯ ФИНАНСОВОГО МОДУЛЯ
    # ==========================================================

    # Кошелёк
    {
        "code": "wallet.read",
        "name": "Read wallet",
        "module": "wallet",
        "description": "Просмотр кошелька клиента",
    },
    {
        "code": "wallet.deposit",
        "name": "Deposit to wallet",
        "module": "wallet",
        "description": "Пополнение баланса клиента",
    },

    # Платежи
    {
        "code": "payments.read",
        "name": "Read payments",
        "module": "payments",
        "description": "Просмотр платежей",
    },
    {
        "code": "payments.create",
        "name": "Create payments",
        "module": "payments",
        "description": "Создание платежей",
    },
    {
        "code": "payments.update",
        "name": "Update payments",
        "module": "payments",
        "description": "Изменение платежей",
    },
    {
        "code": "payments.refund",
        "name": "Refund payments",
        "module": "payments",
        "description": "Возврат платежей",
    },

    # Чеки
    {
        "code": "receipts.read",
        "name": "Read receipts",
        "module": "receipts",
        "description": "Просмотр чеков",
    },
    {
        "code": "receipts.send",
        "name": "Send receipts",
        "module": "receipts",
        "description": "Отправка чеков клиентам",
    },

    # Касса
    {
        "code": "cash_desk.read",
        "name": "Read cash desk",
        "module": "cash_desk",
        "description": "Просмотр кассовых смен",
    },
    {
        "code": "cash_desk.open",
        "name": "Open cash desk session",
        "module": "cash_desk",
        "description": "Открытие кассовой смены",
    },
    {
        "code": "cash_desk.close",
        "name": "Close cash desk session",
        "module": "cash_desk",
        "description": "Закрытие кассовой смены",
    },
    {
        "code": "cash_desk.manage",
        "name": "Manage cash desk",
        "module": "cash_desk",
        "description": "Управление кассовыми операциями",
    },

    # Продажи
    {
        "code": "sales.read",
        "name": "Read sales",
        "module": "sales",
        "description": "Просмотр продаж",
    },
    {
        "code": "sales.create",
        "name": "Create sales",
        "module": "sales",
        "description": "Создание продаж",
    },
]

# вспомогательная функция:
# находит роль и привязывает к ней список прав по code
def bind_permissions_to_role(db, role_code: str, permission_codes: list[str]) -> None:
    # ищем роль
    role = db.query(Role).filter(Role.code == role_code).first()

    # если роль не найдена — ничего не делаем
    if not role:
        return

    # перебираем коды прав
    for permission_code in permission_codes:
        # ищем право
        permission = (
            db.query(Permission)
            .filter(Permission.code == permission_code)
            .first()
        )

        # если право не найдено — пропускаем
        if not permission:
            continue

        # проверяем, есть ли уже связь роль -> право
        existing_link = (
            db.query(RolePermission)
            .filter(
                RolePermission.role_id == role.id,
                RolePermission.permission_id == permission.id,
            )
            .first()
        )

        # если связь уже существует — пропускаем
        if existing_link:
            continue

        # создаём новую связь
        role_permission = RolePermission(
            role_id=role.id,
            permission_id=permission.id,
        )

        # добавляем связь в сессию
        db.add(role_permission)

    # фиксируем изменения
    db.commit()


# функция создаёт права и привязывает их к ролям
def seed_permissions(db) -> None:
    # сначала создаём сами права
    for permission_data in SYSTEM_PERMISSIONS:
        # ищем право по коду
        existing_permission = (
            db.query(Permission)
            .filter(Permission.code == permission_data["code"])
            .first()
        )

        # если право уже существует — пропускаем
        if existing_permission:
            continue

        # создаём новый объект права
        permission = Permission(
            code=permission_data["code"],
            name=permission_data["name"],
            module=permission_data["module"],
            description=permission_data["description"],
        )

        # добавляем право в сессию
        db.add(permission)

    # фиксируем создание прав
    db.commit()

    # admin получает все права
    admin_role = db.query(Role).filter(Role.code == "admin").first()

    # если роль admin существует — связываем её со всеми правами
    if admin_role:
        permissions = db.query(Permission).all()

        for permission in permissions:
            # проверяем, есть ли уже связь admin -> permission
            existing_link = (
                db.query(RolePermission)
                .filter(
                    RolePermission.role_id == admin_role.id,
                    RolePermission.permission_id == permission.id,
                )
                .first()
            )

            # если связь уже есть — пропускаем
            if existing_link:
                continue

            # создаём связь
            role_permission = RolePermission(
                role_id=admin_role.id,
                permission_id=permission.id,
            )

            # добавляем связь в сессию
            db.add(role_permission)

        # фиксируем admin -> all permissions
        db.commit()

    # manager получает полный рабочий CRM-доступ
    bind_permissions_to_role(
        db,
        role_code="manager",
        permission_codes=[
            "clients.read",
            "clients.create",
            "clients.update",
            "tariffs.read",
            "tariffs.create",
            "tariffs.update",
            "subscriptions.read",
            "subscriptions.create",
            "subscriptions.update",
            "visits.read",
            "visits.create",
            "visits.update",
            "payments.read",
            "payments.create",
            "payments.update",
        ],
    )

    # trainer читает клиентов и посещения
    bind_permissions_to_role(
        db,
        role_code="trainer",
        permission_codes=["clients.read", "visits.read"],
    )

    # cashier: продажа, оплата, чеки
    bind_permissions_to_role(
        db,
        role_code="cashier",
        permission_codes=[
            "clients.read",
            "tariffs.read",
            "subscriptions.read",
            "payments.read",
            "payments.create",
            "visits.read",
            "receipts.read",
            "receipts.send",
        ],
    )

    # accountant: финансы, документы, касса
    bind_permissions_to_role(
        db,
        role_code="accountant",
        permission_codes=[
            "clients.read",
            "tariffs.read",
            "subscriptions.read",
            "payments.read",
            "payments.update",
            "visits.read",
            "documents.read",
            "cash_desk.read",
        ],
    )

    # owner: полный рабочий набор manager + сотрудники и возвраты
    bind_permissions_to_role(
        db,
        role_code="owner",
        permission_codes=[
            "clients.read", "clients.create", "clients.update",
            "tariffs.read", "tariffs.create", "tariffs.update",
            "subscriptions.read", "subscriptions.create", "subscriptions.update",
            "visits.read", "visits.create", "visits.update",
            "payments.read", "payments.create", "payments.update",
            "users.read", "payments.refund",
        ],
    )

    # support: минимальный доступ
    bind_permissions_to_role(
        db,
        role_code="support",
        permission_codes=["clients.read", "settings.read"],
    )

    # security (Охрана/СКУД): доступ и шкафчики
    bind_permissions_to_role(
        db,
        role_code="security",
        permission_codes=["clients.read", "visits.read", "lockers.read"],
    )

    # reception (Ресепшен): продажа и приём оплаты
    bind_permissions_to_role(
        db,
        role_code="reception",
        permission_codes=[
            "clients.read",
            "tariffs.read",
            "subscriptions.read", "subscriptions.create", "subscriptions.update",
            "payments.read", "payments.create",
            "visits.read", "visits.create",
        ],
    )

    # cashier работает с продажей и абонементами, но не меняет тарифы
    bind_permissions_to_role(
        db,
        role_code="cashier",
        permission_codes=[
            "clients.read",
            "clients.create",
            "tariffs.read",
            "subscriptions.read",
            "subscriptions.create",
            "subscriptions.update",
        ],
    )

    # support имеет ограниченный read-only доступ
    bind_permissions_to_role(
        db,
        role_code="support",
        permission_codes=[
            "clients.read",
            "subscriptions.read",
        ],
    )