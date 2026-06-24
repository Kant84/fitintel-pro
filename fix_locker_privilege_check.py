# fix_locker_privilege_check.py
with open('app/services/access_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_check = '''    def _check_locker_on_exit(self, client_id: str) -> dict:
        """
        Проверить, можно ли клиенту выйти с занятым шкафчиком.
        
        VIP и клиенты с индивидуальной арендой шкафчика могут выходить.
        Остальные должны освободить шкафчик перед выходом.
        
        Returns:
            {"can_exit": True} — можно выходить
            {"can_exit": False, "reason": "..."} — нельзя выходить
        """
        from app.models.locker import Locker
        from app.models.locker_session import LockerSession
        from app.models.locker_privilege import LockerPrivilege
        
        # Ищем активную сессию шкафчика клиента
        session = (
            self.db.query(LockerSession)
            .filter(LockerSession.client_id == client_id, LockerSession.status == "ACTIVE")
            .first()
        )
        
        if not session:
            # Нет занятого шкафчика — можно выходить
            return {"can_exit": True}
        
        # Проверяем шкафчик
        locker = self.db.query(Locker).filter(Locker.id == session.locker_id).first()
        if not locker:
            return {"can_exit": True}
        
        # VIP клиенты могут выходить с занятым шкафчиком
        client = self.db.query(Client).filter(Client.id == client_id).first()
        if client and client.client_category == "VIP":
            return {"can_exit": True}
        
        # Проверяем индивидуальную аренду шкафчика
        privilege = (
            self.db.query(LockerPrivilege)
            .filter(LockerPrivilege.client_id == client_id, LockerPrivilege.locker_id == locker.id)
            .first()
        )
        if privilege and privilege.is_active and privilege.end_date and privilege.end_date >= date.today():
            # Индивидуальный шкафчик с оплаченной арендой — можно выходить
            return {"can_exit": True}
        
        # Обычный шкафчик занят — нельзя выходить!
        return {
            "can_exit": False,
            "reason": f"Шкафчик {locker.number} занят. Освободите шкафчик перед выходом.",
        }'''

new_check = '''    def _check_locker_on_exit(self, client_id: str) -> dict:
        """
        Проверить, можно ли клиенту выйти с занятым шкафчиком.
        
        VIP клиенты могут выходить с занятым шкафчиком.
        Остальные должны освободить шкафчик перед выходом.
        
        Returns:
            {"can_exit": True} — можно выходить
            {"can_exit": False, "reason": "..."} — нельзя выходить
        """
        from app.models.locker import Locker
        from app.models.locker_session import LockerSession
        
        # Ищем активную сессию шкафчика клиента
        session = (
            self.db.query(LockerSession)
            .filter(LockerSession.client_id == client_id, LockerSession.status == "ACTIVE")
            .first()
        )
        
        if not session:
            # Нет занятого шкафчика — можно выходить
            return {"can_exit": True}
        
        # Проверяем шкафчик
        locker = self.db.query(Locker).filter(Locker.id == session.locker_id).first()
        if not locker:
            return {"can_exit": True}
        
        # VIP клиенты могут выходить с занятым шкафчиком
        client = self.db.query(Client).filter(Client.id == client_id).first()
        if client and client.client_category == "VIP":
            return {"can_exit": True}
        
        # Обычный шкафчик занят — нельзя выходить!
        return {
            "can_exit": False,
            "reason": f"Шкафчик {locker.number} занят. Освободите шкафчик перед выходом.",
        }'''

if old_check in content:
    content = content.replace(old_check, new_check)
    with open('app/services/access_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Проверка LockerPrivilege исправлена!")
else:
    print("ERROR: Не найден _check_locker_on_exit")
