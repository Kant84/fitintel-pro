# fix_feature_flag_schema.py
with open('app/schemas/feature_flag.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_validator = '''    @validator("target_value")
    def validate_target_value(cls, v, values):
        flag_type = values.get("flag_type")
        if flag_type == FlagType.BOOLEAN and v is not None and not isinstance(v, bool):
            raise ValueError("Для boolean-флага target_value должно быть true/false")
        if flag_type == FlagType.INTEGER and v is not None and not isinstance(v, int):
            raise ValueError("Для integer-флага target_value должно быть числом")
        return v'''

new_validator = '''    @validator("target_value", pre=True)
    def validate_target_value(cls, v, values):
        flag_type = values.get("flag_type")
        if flag_type == FlagType.BOOLEAN and v is not None:
            if isinstance(v, str):
                v = v.lower() in ("true", "1", "yes", "on")
            elif not isinstance(v, bool):
                raise ValueError("Для boolean-флага target_value должно быть true/false")
        if flag_type == FlagType.INTEGER and v is not None:
            if isinstance(v, str):
                try:
                    v = int(v)
                except ValueError:
                    raise ValueError("Для integer-флага target_value должно быть числом")
            elif not isinstance(v, int):
                raise ValueError("Для integer-флага target_value должно быть числом")
        return v'''

if old_validator in content:
    content = content.replace(old_validator, new_validator)
    with open('app/schemas/feature_flag.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Валидатор target_value исправлен!")
else:
    print("ERROR: Не найден валидатор")
