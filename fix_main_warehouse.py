# fix_main_warehouse.py
with open('app/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Добавляем импорт
import_line = "from app.api.v1.warehouse import router as warehouse_router"
if import_line not in content:
    # Находим последний импорт
    last_import = content.rfind('from app.api.v1')
    if last_import != -1:
        line_end = content.find('\n', last_import)
        content = content[:line_end+1] + import_line + '\n' + content[line_end+1:]
        print("Import added!")

# Добавляем include_router
include_line = 'app.include_router(warehouse_router, prefix=settings.API_V1_PREFIX)'
if include_line not in content:
    last_include = content.rfind('app.include_router(')
    if last_include != -1:
        line_end = content.find('\n', last_include)
        content = content[:line_end+1] + include_line + '\n' + content[line_end+1:]
        print("Router included!")

with open('app/main.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("main.py updated!")
