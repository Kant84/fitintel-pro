import re

with open('app/middleware/license_middleware.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Добавляем print после получения path
old = 'path = request.url.path'
new = '''path = request.url.path
        print(f"[LICENSE] path={path}, excluded={LicenseState.is_path_excluded(path)}, licensed={LicenseState.is_licensed()}")'''

if old in content:
    content = content.replace(old, new)
    with open('app/middleware/license_middleware.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('OK')
else:
    print('Pattern not found')