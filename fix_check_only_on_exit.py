# fix_check_only_on_exit.py
with open('app/services/access_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_check = '''        # Проверяем, не пытается ли клиент выйти с занятым шкафчиком
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

new_check = '''        # Проверяем, не пытается ли клиент выйти с занятым шкафчиком
        # (кроме VIP и индивидуальных шкафчиков с оплаченной арендой)
        # Проверяем только на выходе (клиент уже внутри)
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

if old_check in content:
    content = content.replace(old_check, new_check)
    with open('app/services/access_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Проверка исправлена!")
else:
    print("ERROR: Не найден блок")
