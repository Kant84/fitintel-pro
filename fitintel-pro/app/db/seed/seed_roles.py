# app\db\seed\seed_roles.py
# импорт модели роли
from app.models.role import Role


# список системных ролей проекта
SYSTEM_ROLES = [
    {
        "code": "owner",
        "name": "Owner",
        "description": "Владелец системы и главный управляющий.",
        "is_system": True,
    },
    {
        "code": "admin",
        "name": "Admin",
        "description": "Полный административный доступ.",
        "is_system": True,
    },
    {
        "code": "manager",
        "name": "Manager",
        "description": "Работа с клиентами, абонементами и посещениями.",
        "is_system": True,
    },
    {
        "code": "trainer",
        "name": "Trainer",
        "description": "Просмотр клиентов и посещаемости.",
        "is_system": True,
    },
    {
        "code": "cashier",
        "name": "Cashier",
        "description": "Работа с платежами и кассовыми операциями.",
        "is_system": True,
    },
    {
        "code": "accountant",
        "name": "Accountant",
        "description": "Отчёты, документы и выгрузки.",
        "is_system": True,
    },
    {
        "code": "support",
        "name": "Support",
        "description": "Техническая поддержка и диагностика.",
        "is_system": True,
    },
    {
        "code": "client",
        "name": "Client",
        "description": "Роль клиента для личного кабинета.",
        "is_system": True,
    },
    {
        "code": "device",
        "name": "Device",
        "description": "Служебная роль для устройств и терминалов.",
        "is_system": True,
    },
]


# функция создаёт системные роли
def seed_roles(db) -> None:
    # перебираем все роли из списка
    for role_data in SYSTEM_ROLES:
        # ищем роль по коду
        existing_role = db.query(Role).filter(Role.code == role_data["code"]).first()

        # если роль уже существует, пропускаем её
        if existing_role:
            continue

        # создаём новый объект роли
        role = Role(
            code=role_data["code"],
            name=role_data["name"],
            description=role_data["description"],
            is_system=role_data["is_system"],
        )

        # добавляем роль в сессию
        db.add(role)

    # фиксируем изменения в базе
    db.commit()