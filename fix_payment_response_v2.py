# fix_payment_response_v2.py
with open('app/services/payment_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Находим _build_response и обновляем
old_build = '''    def _build_response(self, payment: Payment) -> dict:
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

new_build = '''    def _build_response(self, payment: Payment) -> dict:
        """Построить ответ платежа (полные данные как в чеке)"""
        # Получаем данные клиента
        client_name = None
        client_phone = None
        client_email = None
        if payment.client:
            client_name = f"{payment.client.first_name or ''} {payment.client.last_name or ''}".strip()
            client_phone = payment.client.phone
            client_email = payment.client.email
        
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
        
        # Вид платежа (Наличные/Безналичные)
        payment_type = "Наличные"
        if payment.payment_method in ["CARD", "SBP", "ONLINE", "TRANSFER"]:
            payment_type = "Безналичные"
        
        # Название банка/платёжной системы (для безналичных)
        bank_name = payment.payment_system
        if not bank_name:
            if payment.payment_method == "SBP":
                bank_name = "Система быстрых платежей (СБП)"
            elif payment.payment_method == "CARD":
                bank_name = "Банковская карта (не указан банк)"
            elif payment.payment_method == "CASH":
                bank_name = None  # Для наличных банк не нужен
            else:
                bank_name = "Не указан"
        
        return {
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

if old_build in content:
    content = content.replace(old_build, new_build)
    with open('app/services/payment_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("_build_response обновлён (v2)!")
else:
    print("Не найден _build_response")

# Обновляем схему PaymentResponse
with open('app/schemas/payment.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_schema = '''    # Данные клиента (как в чеке)
    client_name: str | None = Field(default=None, description="ФИО клиента")
    client_phone: str | None = Field(default=None, description="Телефон клиента")
    
    # Данные чека
    receipt_number: str | None = Field(default=None, description="Номер чека")
    
    # За что оплачено
    purpose: str | None = Field(default=None, description="Назначение платежа (абонемент/услуга)")
    subscription_name: str | None = Field(default=None, description="Название абонемента")
    
    # Банк/платёжная система
    bank_name: str | None = Field(default=None, description="Название банка или платёжной системы")'''

new_schema = '''    # Данные клиента (как в чеке)
    client_name: str | None = Field(default=None, description="ФИО клиента")
    client_phone: str | None = Field(default=None, description="Телефон клиента")
    client_email: str | None = Field(default=None, description="Email клиента")
    
    # Вид платежа
    payment_type: str | None = Field(default=None, description="Вид платежа: Наличные/Безналичные")
    
    # Банк/платёжная система
    bank_name: str | None = Field(default=None, description="Название банка или платёжной системы")
    
    # Данные чека
    receipt_number: str | None = Field(default=None, description="Номер чека")
    
    # За что оплачено
    purpose: str | None = Field(default=None, description="Назначение платежа (абонемент/услуга)")
    subscription_name: str | None = Field(default=None, description="Название абонемента")'''

if old_schema in content:
    content = content.replace(old_schema, new_schema)
    with open('app/schemas/payment.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("PaymentResponse обновлён (v2)!")
else:
    print("Не найден PaymentResponse")
