# fix_model_validator_import.py
with open('app/schemas/visit.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_import = '''from pydantic import BaseModel, ConfigDict, Field, validator'''

new_import = '''from pydantic import BaseModel, ConfigDict, Field, validator, model_validator'''

if old_import in content:
    content = content.replace(old_import, new_import)
    with open('app/schemas/visit.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Импорт model_validator добавлен!")
else:
    print("ERROR: Не найден импорт")
