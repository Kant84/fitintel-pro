# fix_payment_response.py
with open('app/schemas/payment.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_response = '''class PaymentResponse(PaymentBase):
    """Ответ с информацией о платеже"""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    status: str
    external_payment_id: str | None
    paid_at: datetime | None
    created_by_user_id: UUID | None
    created_at: datetime
    updated_at: datetime'''

new_response = '''class PaymentResponse(PaymentBase):
    """Ответ с информацией о платеже (полные данные как в чеке)"""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    status: str
    external_payment_id: str | None
    paid_at: datetime | None
    created_by_user_id: UUID | None
    created_at: datetime
    updated_at: datetime
    
    # Данные клиента (как в чеке)
    client_name: str | None = Field(default=None, description="ФИО клиента")
    client_phone: str | None = Field(default=None, description="Телефон клиента")
    
    # Данные чека
    receipt_number: str | None = Field(default=None, description="Номер чека")
    
    # За что оплачено
    purpose: str | None = Field(default=None, description="Назначение платежа (абонемент/услуга)")
    subscription_name: str | None = Field(default=None, description="Название абонемента")
    
    # Банк/платёжная система
    bank_name: str | None = Field(default=None, description="Название банка или платёжной системы")'''

if old_response in content:
    content = content.replace(old_response, new_response)
    with open('app/schemas/payment.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("PaymentResponse обновлён!")
else:
    print("Не найден PaymentResponse")
