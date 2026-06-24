# fix_setup_hashlib.py
with open('app/api/v1/setup.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Добавляем hashlib после logging
old = 'import logging'
new = 'import logging\nimport hashlib'

if old in content and 'import hashlib' not in content:
    content = content.replace(old, new)
    with open('app/api/v1/setup.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("hashlib import added!")
else:
    print("hashlib already imported or pattern not found")
