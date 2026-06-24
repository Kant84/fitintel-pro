# fix_flag_key_upper.py
with open('app/schemas/feature_flag.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_validator = '''    @validator("flag_key")
    def validate_flag_key(cls, v):
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Ключ флага должен содержать только буквы, цифры, _ и -")
        return v.upper()'''

new_validator = '''    @validator("flag_key")
    def validate_flag_key(cls, v):
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Ключ флага должен содержать только буквы, цифры, _ и -")
        return v'''

if old_validator in content:
    content = content.replace(old_validator, new_validator)
    with open('app/schemas/feature_flag.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Валидатор flag_key исправлен — убран .upper()!")
else:
    print("ERROR: Не найден валидатор")
