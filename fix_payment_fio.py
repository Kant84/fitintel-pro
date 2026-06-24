# fix_payment_fio.py
with open('app/schemas/payment.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_fields = '''    # Данные клиента (как в чеке)
    client_name: str | None = Field(default=None, description="ФИО клиента")
    client_phone: str | None = Field(default=None, description="Телефон клиента")
    client_email: str | None = Field(default=None, description="Email клиента")'''

new_fields = '''    # Данные клиента (как в чеке)
    client_first_name: str | None = Field(default=None, description="Имя клиента")
    client_last_name: str | None = Field(default=None, description="Фамилия клиента")
    client_middle_name: str | None = Field(default=None, description="Отчество клиента")
    client_full_name: str | None = Field(default=None, description="Полное ФИО клиента")
    client_phone: str | None = Field(default=None, description="Телефон клиента")
    client_email: str | None = Field(default=None, description="Email клиента")'''

if old_fields in content:
    content = content.replace(old_fields, new_fields)
    with open('app/schemas/payment.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Поля ФИО обновлены!")
else:
    print("Не найдены поля клиента")
