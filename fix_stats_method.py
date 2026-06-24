# fix_stats_method.py
with open('app/api/v1/visits.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_call = 'visits = visit_service.list_visits(offset=0, limit=10000, actor_user_id=current_user.id)'
new_call = 'visits = visit_service.list_all(limit=10000, offset=0)'

if old_call in content:
    content = content.replace(old_call, new_call)
    with open('app/api/v1/visits.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Исправлено: list_visits -> list_all!")
else:
    print("Не найден вызов list_visits")
