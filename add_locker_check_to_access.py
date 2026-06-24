# add_locker_check_to_access.py
with open('app/services/access_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Добавляем метод _check_locker_on_exit перед check_access
old_check_access = '''    def check_access(
        self,
        credential: str,
        device_id: str,
        zone: str | None = None,
    ) -> AccessCheckResponse:
        """Проверить, может ли клиент пройти (без создания посещения)"""
        device = self._get_device(device_id)
        client = self._find_client_by_credential(credential)
        
        if not client:
            return AccessCheckResponse(
                decision=AccessDecision.DENIED,
                reason="Клиент не найден",
            )'''

new_check_access = '''    def _check_locker_on_exit(self, client_id: str) -> dict:
        """
        Проверить, можно ли клиенту выйти с занятым шкафчиком.
        
        VIP и клиенты с индивидуальной арендой шкафчика могут выходить.
        Остальные должны освободить шкафчик перед выходом.
        
        Returns:
            {"can_exit": True} — можно выходить
            {"can_exit": False, "reason": "..."} — нельзя выходить
        """
        from app.models.locker import Locker, LockerSession
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
        }
    
    def _get_active_visit(self, client_id: str):
        """Получить активное посещение клиента"""
        from app.models.visit import Visit
        return (
            self.db.query(Visit)
            .filter(Visit.client_id == client_id, Visit.status == "ACTIVE")
            .first()
        )
    
    def check_access(
        self,
        credential: str,
        device_id: str,
        zone: str | None = None,
    ) -> AccessCheckResponse:
        """Проверить, может ли клиент пройти (без создания посещения)"""
        device = self._get_device(device_id)
        client = self._find_client_by_credential(credential)
        
        if not client:
            return AccessCheckResponse(
                decision=AccessDecision.DENIED,
                reason="Клиент не найден",
            )
        
        # Проверяем, не пытается ли клиент выйти с занятым шкафчиком
        # (кроме VIP и индивидуальных шкафчиков с оплаченной арендой)
        if device and device.device_type == "turnstile":
            # Проверяем активное посещение
            active_visit = self._get_active_visit(client.id)
            if active_visit:
                # Клиент внутри — значит это выход
                # Проверяем шкафчик
                locker_check = self._check_locker_on_exit(client.id)
                if not locker_check["can_exit"]:
                    return AccessCheckResponse(
                        decision=AccessDecision.DENIED,
                        reason=locker_check["reason"],
                    )'''

if old_check_access in content:
    content = content.replace(old_check_access, new_check_access)
    with open('app/services/access_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Проверка шкафчика перед выходом добавлена!")
else:
    print("ERROR: Не найден check_access")
