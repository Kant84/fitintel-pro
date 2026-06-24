# fix_main_pwa.py
with open('app/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Добавляем StaticFiles импорт
if 'from fastapi.staticfiles import StaticFiles' not in content:
    # Находим строку с импортом FastAPI
    old = 'from fastapi import FastAPI'
    new = 'from fastapi import FastAPI\nfrom fastapi.staticfiles import StaticFiles'
    content = content.replace(old, new)
    print("StaticFiles import added!")

# Добавляем mount для PWA
mount_line = 'app.mount("/static/trainer-pwa", StaticFiles(directory="app/static/trainer-pwa"), name="trainer-pwa")'
if mount_line not in content:
    # Находим строку после создания app
    idx = content.find('app = FastAPI(')
    if idx != -1:
        # Находим закрывающую скобку
        end_idx = content.find(')', idx)
        # Находим конец строки
        line_end = content.find('\n', end_idx)
        content = content[:line_end+1] + mount_line + '\n' + content[line_end+1:]
        print("PWA mount added!")

with open('app/main.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("main.py updated for PWA!")
