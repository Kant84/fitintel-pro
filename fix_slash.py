import re

with open('app/core/license_guard.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Удаляем строку с "/" из EXCLUDED_PATHS
old = '    "/",'
new = ''

if old in content:
    content = content.replace(old, new)
    with open('app/core/license_guard.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('OK')
else:
    print('Pattern not found')