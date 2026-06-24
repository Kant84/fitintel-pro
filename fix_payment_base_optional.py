# fix_payment_base_optional.py
with open('app/schemas/payment.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_base = '''    client_id: UUID = Field(description="ID клиента")'''

new_base = '''    client_id: UUID | None = Field(default=None, description="ID клиента (None для внутренних платежей)")'''

if old_base in content:
    content = content.replace(old_base, new_base)
    with open('app/schemas/payment.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("client_id теперь необязательный!")
else:
    print("Не найден client_id")

# Обновляем модель
with open('app/models/payment.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_model = '''    client_id: Mapped[str] = mapped_column(
        ForeignKey("clients.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )'''

new_model = '''    client_id: Mapped[str | None] = mapped_column(
        ForeignKey("clients.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )'''

if old_model in content:
    content = content.replace(old_model, new_model)
    with open('app/models/payment.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Модель обновлена!")
else:
    print("Не найдено поле client_id в модели")
