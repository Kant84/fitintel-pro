# fix_payment_method_balance.py
with open('app/schemas/enums.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_enum = '''class PaymentMethod(str, Enum):
    CASH = "CASH"
    CARD = "CARD"
    SBP = "SBP"
    TRANSFER = "TRANSFER"
    ONLINE = "ONLINE"
    SUBSCRIPTION = "SUBSCRIPTION"
    QR = "QR"
    CRYPTOCURRENCY = "CRYPTOCURRENCY"
    OTHER = "OTHER"'''

new_enum = '''class PaymentMethod(str, Enum):
    CASH = "CASH"
    CARD = "CARD"
    SBP = "SBP"
    TRANSFER = "TRANSFER"
    ONLINE = "ONLINE"
    SUBSCRIPTION = "SUBSCRIPTION"
    QR = "QR"
    BALANCE = "BALANCE"
    CRYPTOCURRENCY = "CRYPTOCURRENCY"
    OTHER = "OTHER"'''

if old_enum in content:
    content = content.replace(old_enum, new_enum)
    with open('app/schemas/enums.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("BALANCE добавлен!")
else:
    print("Не найден enum")
