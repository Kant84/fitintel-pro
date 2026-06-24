# fix_feature_flags_roles.py
with open('app/api/v1/feature_flags.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Заменяем require_roles(["SUPER_ADMIN"]) на require_roles("SUPER_ADMIN")
content = content.replace('require_roles(["SUPER_ADMIN"])', 'require_roles("SUPER_ADMIN")')

with open('app/api/v1/feature_flags.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("feature_flags.py исправлен!")
