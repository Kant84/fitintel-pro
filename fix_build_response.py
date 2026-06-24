# fix_build_response.py
with open('app/services/payment_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_build = '''    def _build_response(self, payment: Payment) -> dict:
        """Построить ответ платежа"""
        return {
            "id": payment.id,
            "client_id": payment.client_id,
            "amount": payment.amount,
            "currency": payment.currency,
            "payment_method": payment.payment_method,
            "status": payment.status,
            "external_payment_id": payment.external_payment_id,
            "payment_system": payment.payment_system,
            "paid_at": payment.paid_at,
            "created_by_user_id": payment.created_by_user_id,
            "notes": payment.notes,
            "created_at": payment.created_at,
            "updated_at": payment.updated_at,
        }'''

new_build = '''    def _build_response(self, payment: Payment) -> dict:
        """Построить ответ платежа (полные данные как в чеке)"""
        # Получаем данные клиента
        client_name = None
        client_phone = None
        if payment.client:
            client_name = f"{payment.client.first_name or ''} {payment.client.last_name or ''}".strip()
            client_phone = payment.client.phone
        
        # Получаем номер чека
        receipt_number = None
        if payment.receipt:
            receipt_number = payment.receipt.receipt_number
        
        # Получаем название абонемента (если есть)
        subscription_name = None
        purpose = payment.notes
        if hasattr(payment, 'subscription') and payment.subscription:
            subscription_name = payment.subscription.name
            purpose = f"Оплата абонемента: {payment.subscription.name}"
        
        # Название банка/платёжной системы
        bank_name = payment.payment_system or "Наличные"
        if payment.payment_method == "CASH":
            bank_name = "Наличные"
        elif payment.payment_method == "SBP":
            bank_name = "СБП (Система быстрых платежей)"
        elif payment.payment_method == "CARD":
            bank_name = payment.payment_system or "Банковская карта"
        
        return {
            "id": payment.id,
            "client_id": payment.client_id,
            "amount": payment.amount,
            "currency": payment.currency,
            "payment_method": payment.payment_method,
            "status": payment.status,
            "external_payment_id": payment.external_payment_id,
            "payment_system": payment.payment_system,
            "paid_at": payment.paid_at,
            "created_by_user_id": payment.created_by_user_id,
            "notes": payment.notes,
            "created_at": payment.created_at,
            "updated_at": payment.updated_at,
            # Данные как в чеке
            "client_name": client_name,
            "client_phone": client_phone,
            "receipt_number": receipt_number,
            "purpose": purpose,
            "subscription_name": subscription_name,
            "bank_name": bank_name,
        }'''

if old_build in content:
    content = content.replace(old_build, new_build)
    with open('app/services/payment_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("_build_response обновлён!")
else:
    print("Не найден _build_response")
