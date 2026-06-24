# remove_debug_from_time_check.py
with open('app/services/visit_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_debug = '''        print(f"DEBUG _check_time_restriction: type={subscription.time_restriction_type}, start={subscription.allowed_start_time}, end={subscription.allowed_end_time}")
        # Если ограничения не заданы — пропускаем
        if not subscription.time_restriction_type or subscription.time_restriction_type == "FULLDAY":
            print(f"DEBUG: пропускаем (type={subscription.time_restriction_type})")
            return'''

new_debug = '''        # Если ограничения не заданы — пропускаем
        if not subscription.time_restriction_type or subscription.time_restriction_type == "FULLDAY":
            return'''

if old_debug in content:
    content = content.replace(old_debug, new_debug)
    with open('app/services/visit_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("DEBUG убран из _check_time_restriction!")
else:
    print("ERROR: Не найден debug")
