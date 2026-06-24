# fix_access_log_device_id.py
with open('app/services/access_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Исправляем device_id в get_logs
old_line = '''                device_id=log.after_data.get("device_id") if log.after_data else None,'''
new_line = '''                device_id=log.after_data.get("device_id") if log.after_data and log.after_data.get("device_id") else "unknown",'''

if old_line in content:
    content = content.replace(old_line, new_line)
    with open('app/services/access_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Исправлено: device_id default = 'unknown'")
else:
    print("ERROR: Не найдена строка")
