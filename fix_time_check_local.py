# fix_time_check_local.py
with open('app/services/visit_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_check = '''        # Получаем текущее время
        now = datetime.now(timezone.utc).time()'''

new_check = '''        # Получаем текущее локальное время (для сравнения с локальным временем абонемента)
        now = datetime.now().time()'''

if old_check in content:
    content = content.replace(old_check, new_check)
    with open('app/services/visit_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Исправлено: используем локальное время вместо UTC!")
else:
    print("ERROR: Не найдена строка с UTC временем")
