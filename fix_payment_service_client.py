# fix_payment_service_client.py
with open('app/services/payment_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_check = '''        client = self._get_client(client_id)
        
        if amount <= 0:'''

new_check = '''        # Проверяем клиента только если указан
        client = None
        if client_id:
            client = self._get_client(client_id)
        
        if amount <= 0:'''

if old_check in content:
    content = content.replace(old_check, new_check)
    with open('app/services/payment_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Проверка клиента исправлена!")
else:
    print("Не найдена проверка клиента")
