# fix_payment_base.py
with open('app/schemas/payment.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_base = '''class PaymentBase(BaseModel):
    """Базовые поля платежа"""
    
    client_id: UUID = Field(description="ID клиента")
    amount: Decimal = Field(gt=0, decimal_places=2, description="Сумма")
    payment_method: PaymentMethod = Field(description="Способ оплаты")
    payment_system: PaymentSystem | None = Field(None, description="Платёжная система")
    notes: str | None = Field(None, max_length=500, description="Заметки")'''

new_base = '''class PaymentBase(BaseModel):
    """Базовые поля платежа"""
    
    client_id: UUID = Field(description="ID клиента")
    amount: Decimal = Field(gt=0, decimal_places=2, description="Сумма")
    payment_method: PaymentMethod = Field(description="Способ оплаты")
    payment_system: PaymentSystem | None = Field(None, description="Платёжная система")
    notes: str | None = Field(None, max_length=500, description="Заметки")
    
    # Направление платежа
    payment_direction: str = Field(
        default="INCOME",
        description="Направление: INCOME (приход), EXPENSE (расход)",
    )
    
    # Категория платежа
    payment_category: str = Field(
        default="SUBSCRIPTION",
        description="Категория: SUBSCRIPTION, INVENTORY, SALARY, RENT, UTILITIES, OTHER",
    )'''

if old_base in content:
    content = content.replace(old_base, new_base)
    with open('app/schemas/payment.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("PaymentBase обновлён!")
else:
    print("Не найден PaymentBase")
