# fix_create_flag.py
with open('app/api/v1/feature_flags.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_create = '''    flag = FeatureFlag(**data.dict(), changed_by=current_user.email)'''

new_create = '''    flag_data = data.dict()
    # Копируем default_value в target_value если target_value не задан
    if flag_data.get("default_value") is not None and flag_data.get("target_value") is None:
        flag_data["target_value"] = flag_data["default_value"]
    flag = FeatureFlag(**flag_data, changed_by=current_user.email)'''

if old_create in content:
    content = content.replace(old_create, new_create)
    with open('app/api/v1/feature_flags.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("create_flag исправлен!")
else:
    print("ERROR: Не найдена строка")
