# fix_payment_fio_service.py
with open('app/services/payment_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_client = '''        # Получаем данные клиента
        client_name = None
        client_phone = None
        client_email = None
        if payment.client:
            client_name = f"{payment.client.first_name or ''} {payment.client.last_name or ''}".strip()
            client_phone = payment.client.phone
            client_email = payment.client.email'''

new_client = '''        # Получаем данные клиента (раздельные поля ФИО)
        client_first_name = None
        client_last_name = None
        client_middle_name = None
        client_full_name = None
        client_phone = None
        client_email = None
        if payment.client:
            client_first_name = payment.client.first_name
            client_last_name = payment.client.last_name
            client_middle_name = payment.client.middle_name
            parts = [p for p in [client_last_name, client_first_name, client_middle_name] if p]
            client_full_name = " ".join(parts)
            client_phone = payment.client.phone
            client_email = payment.client.email'''

if old_client in content:
    content = content.replace(old_client, new_client)
    
    # Обновляем return
    old_return = '''            # Данные клиента (как в чеке)
            "client_name": client_name,
            "client_phone": client_phone,
            "client_email": client_email,'''
    
    new_return = '''            # Данные клиента (как в чеке)
            "client_first_name": client_first_name,
            "client_last_name": client_last_name,
            "client_middle_name": client_middle_name,
            "client_full_name": client_full_name,
            "client_phone": client_phone,
            "client_email": client_email,'''
    
    content = content.replace(old_return, new_return)
    
    with open('app/services/payment_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Сервис обновлён!")
else:
    print("Не найден блок клиента")
