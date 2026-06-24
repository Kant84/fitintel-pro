# fix_payment_model.py
with open('app/models/payment.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_payment_method = '''    # Способ оплаты: CASH, CARD, ONLINE, BALANCE
    payment_method: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )'''

new_payment_method = '''    # Способ оплаты: CASH, CARD, ONLINE, BALANCE
    payment_method: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    
    # Направление: INCOME (приход), EXPENSE (расход)
    payment_direction: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="INCOME",
        index=True,
    )
    
    # Категория: SUBSCRIPTION, INVENTORY, SALARY, RENT, UTILITIES, OTHER
    payment_category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="SUBSCRIPTION",
        index=True,
    )'''

if old_payment_method in content:
    content = content.replace(old_payment_method, new_payment_method)
    with open('app/models/payment.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Поля direction и category добавлены в модель!")
else:
    print("Не найден payment_method")

# Добавляем в схему PaymentBase
with open('app/schemas/payment.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_base = '''class PaymentBase(BaseModel):
    """Базовая схема платежа"""
    
    # ID клиента
    client_id: UUID | None = Field(
        default=None,
        description="ID клиента (None для внутренних платежей)",
    )'''

new_base = '''class PaymentBase(BaseModel):
    """Базовая схема платежа"""
    
    # ID клиента
    client_id: UUID | None = Field(
        default=None,
        description="ID клиента (None для внутренних платежей)",
    )
    
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
    print("Поля добавлены в PaymentBase!")
else:
    print("Не найден PaymentBase")
