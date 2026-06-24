# fix_payment_response_v3.py
with open('app/services/payment_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_return = '''        return {
            "id": payment.id,
            # Данные клиента (как в чеке)
            "client_name": client_name,
            "client_phone": client_phone,
            "client_email": client_email,
            # Данные платежа
            "amount": payment.amount,
            "currency": payment.currency,
            "payment_method": payment.payment_method,
            "payment_type": payment_type,
            "bank_name": bank_name,
            "status": payment.status,
            "external_payment_id": payment.external_payment_id,
            "paid_at": payment.paid_at,
            # Данные чека
            "receipt_number": receipt_number,
            "purpose": purpose,
            "subscription_name": subscription_name,
            # Служебные
            "created_by_user_id": payment.created_by_user_id,
            "notes": payment.notes,
            "created_at": payment.created_at,
            "updated_at": payment.updated_at,
        }'''

new_return = '''        return {
            "id": payment.id,
            "client_id": payment.client_id,
            # Данные клиента (как в чеке)
            "client_name": client_name,
            "client_phone": client_phone,
            "client_email": client_email,
            # Данные платежа
            "amount": payment.amount,
            "currency": payment.currency,
            "payment_method": payment.payment_method,
            "payment_type": payment_type,
            "bank_name": bank_name,
            "status": payment.status,
            "external_payment_id": payment.external_payment_id,
            "paid_at": payment.paid_at,
            # Данные чека
            "receipt_number": receipt_number,
            "purpose": purpose,
            "subscription_name": subscription_name,
            # Служебные
            "created_by_user_id": payment.created_by_user_id,
            "notes": payment.notes,
            "created_at": payment.created_at,
            "updated_at": payment.updated_at,
        }'''

if old_return in content:
    content = content.replace(old_return, new_return)
    with open('app/services/payment_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("client_id возвращён в ответ!")
else:
    print("Не найден return")
