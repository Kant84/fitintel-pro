# fix_visit_client_id.py
with open('app/services/visit_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_visit = '''        visit = Visit(
            client_id=client_id,
            subscription_id=subscription.id if subscription else None,
            entry_time=entry_time,
            access_method=access_method.value,
            access_device_id=access_device_id,
            access_granted=True,
            status=VisitStatus.ACTIVE.value,
            zone=zone,
            notes=notes,
            processed_by_user_id=actor_user_id,
        )'''

new_visit = '''        visit = Visit(
            client_id=resolved_client_id,
            subscription_id=subscription.id if subscription else None,
            entry_time=entry_time,
            access_method=access_method.value,
            access_device_id=access_device_id,
            access_granted=True,
            status=VisitStatus.ACTIVE.value,
            zone=zone,
            notes=notes,
            processed_by_user_id=actor_user_id,
        )'''

if old_visit in content:
    content = content.replace(old_visit, new_visit)
    with open('app/services/visit_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Visit создан с resolved_client_id!")
else:
    print("ERROR: Не найдено создание Visit")
