# add_debug_to_time_check.py
with open('app/services/visit_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_check = '''    def _check_time_restriction(self, subscription: Subscription) -> None:
        """
        Проверить временные ограничения абонемента.
        
        Поддерживает:
        - FULLDAY: полный день (без ограничений)
        - DAYTIME: дневное время (например, 06:00-22:00)
        - NIGHTTIME: ночное время (например, 22:00-06:00)
        """
        # Если ограничения не заданы — пропускаем
        if not subscription.time_restriction_type or subscription.time_restriction_type == "FULLDAY":
            return'''

new_check = '''    def _check_time_restriction(self, subscription: Subscription) -> None:
        """
        Проверить временные ограничения абонемента.
        
        Поддерживает:
        - FULLDAY: полный день (без ограничений)
        - DAYTIME: дневное время (например, 06:00-22:00)
        - NIGHTTIME: ночное время (например, 22:00-06:00)
        """
        print(f"DEBUG _check_time_restriction: type={subscription.time_restriction_type}, start={subscription.allowed_start_time}, end={subscription.allowed_end_time}")
        # Если ограничения не заданы — пропускаем
        if not subscription.time_restriction_type or subscription.time_restriction_type == "FULLDAY":
            print(f"DEBUG: пропускаем (type={subscription.time_restriction_type})")
            return'''

if old_check in content:
    content = content.replace(old_check, new_check)
    with open('app/services/visit_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("DEBUG добавлен в _check_time_restriction!")
else:
    print("ERROR: Не найден _check_time_restriction")
