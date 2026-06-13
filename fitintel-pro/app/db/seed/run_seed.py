# импорт фабрики сессий базы данных
from app.db.session import SessionLocal

# импорт функций загрузки стартовых ролей, прав и администратора
from app.db.seed.seed_roles import seed_roles
from app.db.seed.seed_permissions import seed_permissions
from app.db.seed.seed_admin import seed_admin


# главная функция запуска seed-данных
def main() -> None:
    # создаём сессию базы данных
    db = SessionLocal()

    try:
        # создаём роли
        seed_roles(db)

        # создаём права и связи прав с ролью admin
        seed_permissions(db)

        # создаём первичного администратора
        seed_admin(db)

        # выводим сообщение об успешном завершении
        print("Seed-данные успешно загружены")
    finally:
        # закрываем сессию базы данных
        db.close()


# если файл запущен напрямую, выполняем main()
if __name__ == "__main__":
    main()