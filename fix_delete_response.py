# fix_delete_response.py
with open('app/api/v1/feature_flags.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_delete = '''@router.delete("/{flag_id}", tags=["Feature Flags"])'''

new_delete = '''@router.delete("/{flag_id}", response_model=dict, tags=["Feature Flags"])'''

if old_delete in content:
    content = content.replace(old_delete, new_delete)
    with open('app/api/v1/feature_flags.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("DELETE response_model исправлен!")
else:
    print("ERROR: Не найден DELETE router")
