# fix_main_trainers.py
with open('app/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Добавляем импорт если нет
import_line = "from app.api.v1.trainers import router as trainers_router"
if import_line not in content:
    # Находим последний импорт из app.api.v1
    last_import = content.rfind('from app.api.v1')
    if last_import != -1:
        # Находим конец строки
        line_end = content.find('\n', last_import)
        content = content[:line_end+1] + import_line + '\n' + content[line_end+1:]
        print("Import added!")

# Добавляем include_router если нет
include_line = 'app.include_router(trainers_router, prefix=settings.API_V1_PREFIX)'
if include_line not in content:
    # Находим последний include_router
    last_include = content.rfind('app.include_router(')
    if last_include != -1:
        line_end = content.find('\n', last_include)
        # Ищем конец блока include_router
        next_line = content.find('app.include_router(', line_end+1)
        if next_line == -1:
            # Это последний, добавляем после
            content = content[:line_end+1] + include_line + '\n' + content[line_end+1:]
        else:
            # Добавляем перед последним (чтобы было в алфавитном порядке)
            content = content[:last_include] + include_line + '\n' + content[last_include:]
        print("Router included!")

with open('app/main.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("main.py updated!")
