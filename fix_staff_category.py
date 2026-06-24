# fix_staff_category.py
with open('app/schemas/enums.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_enum = '''class ClientCategoryEnum(str, Enum):
    ADULT = "ADULT"
    ВЗРОСЛЫЙ = "ADULT"
    CHILD = "CHILD"
    РЕБЁНОК = "CHILD"
    ПЕНСИОНЕР = "ПЕНСИОНЕР"
    ИНВАЛИД = "ИНВАЛИД"
    КОРПОРАТИВНЫЙ = "КОРПОРАТИВНЫЙ"
    VIP = "VIP"
    НЕ_УКАЗАНА = "НЕ_УКАЗАНА"'''

new_enum = '''class ClientCategoryEnum(str, Enum):
    ADULT = "ADULT"
    ВЗРОСЛЫЙ = "ADULT"
    CHILD = "CHILD"
    РЕБЁНОК = "CHILD"
    ПЕНСИОНЕР = "ПЕНСИОНЕР"
    ИНВАЛИД = "ИНВАЛИД"
    КОРПОРАТИВНЫЙ = "КОРПОРАТИВНЫЙ"
    VIP = "VIP"
    STAFF = "STAFF"
    СОТРУДНИК = "STAFF"
    НЕ_УКАЗАНА = "НЕ_УКАЗАНА"'''

if old_enum in content:
    content = content.replace(old_enum, new_enum)
    with open('app/schemas/enums.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Категория STAFF добавлена!")
else:
    print("Не найден enum для замены")
