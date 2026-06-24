# fix_time_check_with_entry_time.py
with open('app/services/visit_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Обновляем сигнатуру _check_time_restriction чтобы принимать entry_time
old_sig = '''    def _check_time_restriction(self, subscription: Subscription) -> None:'''

new_sig = '''    def _check_time_restriction(self, subscription: Subscription, entry_time: datetime | None = None) -> None:'''

if old_sig in content:
    content = content.replace(old_sig, new_sig)
    print("1. Сигнатура _check_time_restriction обновлена!")
else:
    print("ERROR 1: Не найдена сигнатура")

# Обновляем получение времени
old_time = '''        # Получаем текущее локальное время (для сравнения с локальным временем абонемента)
        now = datetime.now().time()'''

new_time = '''        # Получаем время для проверки (entry_time или текущее)
        if entry_time:
            now = entry_time.time()
        else:
            now = datetime.now().time()'''

if old_time in content:
    content = content.replace(old_time, new_time)
    print("2. Использование entry_time добавлено!")
else:
    print("ERROR 2: Не найдена строка с временем")

# Обновляем вызов _check_time_restriction в entry
old_call = '''        # Проверяем временные ограничения
        self._check_time_restriction(subscription)'''

new_call = '''        # Проверяем временные ограничения
        self._check_time_restriction(subscription, entry_time)'''

if old_call in content:
    content = content.replace(old_call, new_call)
    print("3. Вызов _check_time_restriction обновлён!")
else:
    print("ERROR 3: Не найден вызов")

with open('app/services/visit_service.py', 'w', encoding='utf-8') as f:
    f.write(content)
