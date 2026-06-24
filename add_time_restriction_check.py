# add_time_restriction_check.py
with open('app/services/visit_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Добавляем импорт time
old_import = '''from datetime import datetime, date, timedelta, timezone'''
new_import = '''from datetime import datetime, date, timedelta, timezone, time'''

if old_import in content:
    content = content.replace(old_import, new_import)

# Добавляем метод _check_time_restriction перед _resolve_client_id
old_method = '''    def _resolve_client_id('''

new_method = '''    def _check_time_restriction(self, subscription: Subscription) -> None:
        """
        Проверить временные ограничения абонемента.
        
        Поддерживает:
        - FULLDAY: полный день (без ограничений)
        - DAYTIME: дневное время (например, 06:00-22:00)
        - NIGHTTIME: ночное время (например, 22:00-06:00)
        """
        # Если ограничения не заданы — пропускаем
        if not subscription.time_restriction_type or subscription.time_restriction_type == "FULLDAY":
            return
        
        # Получаем текущее время
        now = datetime.now(timezone.utc).time()
        
        # Если время не задано — пропускаем
        if not subscription.allowed_start_time or not subscription.allowed_end_time:
            return
        
        start_time = subscription.allowed_start_time
        end_time = subscription.allowed_end_time
        
        # Проверяем дневное время (06:00-22:00)
        if subscription.time_restriction_type == "DAYTIME":
            if now < start_time or now > end_time:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Доступ запрещён: дневной абонемент действует с {start_time.strftime('%H:%M')} до {end_time.strftime('%H:%M')}",
                )
        
        # Проверяем ночное время (22:00-06:00)
        elif subscription.time_restriction_type == "NIGHTTIME":
            # Ночной интервал: пересекает полночь
            if start_time > end_time:
                # Например, 22:00-06:00
                if not (now >= start_time or now <= end_time):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Доступ запрещён: ночной абонемент действует с {start_time.strftime('%H:%M')} до {end_time.strftime('%H:%M')}",
                    )
            else:
                # Например, 00:00-06:00
                if now < start_time or now > end_time:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Доступ запрещён: ночной абонемент действует с {start_time.strftime('%H:%M')} до {end_time.strftime('%H:%M')}",
                    )
    
    def _resolve_client_id('''

if old_method in content:
    content = content.replace(old_method, new_method)
    print("Метод _check_time_restriction добавлен!")
else:
    print("ERROR: Не найден метод _resolve_client_id")

# Добавляем вызов проверки времени после проверки лимита
old_check = '''        # Проверяем лимиты абонемента
        if not subscription.is_unlimited:
            if subscription.visits_used >= subscription.visit_limit:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Лимит посещений абонемента исчерпан",
                )
        
        # Устанавливаем время входа с часовым поясом UTC'''

new_check = '''        # Проверяем лимиты абонемента
        if not subscription.is_unlimited:
            if subscription.visits_used >= subscription.visit_limit:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Лимит посещений абонемента исчерпан",
                )
        
        # Проверяем временные ограничения
        self._check_time_restriction(subscription)
        
        # Устанавливаем время входа с часовым поясом UTC'''

if old_check in content:
    content = content.replace(old_check, new_check)
    print("Проверка временных ограничений добавлена в entry!")
else:
    print("ERROR: Не найдена проверка лимита")

with open('app/services/visit_service.py', 'w', encoding='utf-8') as f:
    f.write(content)
