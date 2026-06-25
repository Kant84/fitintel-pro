# fix_quick_export.py
with open('app/api/v1/exports.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Исправляем regex для quick_export
old = '    format: str = Query("csv", regex="^(csv|json)$")'
new = '    format: str = Query("csv", regex="^(xlsx|csv|json|xml)$")'

if old in content:
    content = content.replace(old, new)
    print("Quick export regex fixed!")
else:
    print("Pattern not found")

with open('app/api/v1/exports.py', 'w', encoding='utf-8') as f:
    f.write(content)
