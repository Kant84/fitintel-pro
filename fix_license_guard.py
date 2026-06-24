
import re

with open('app/core/license_guard.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Удаляем '/api/v1' из списка исключений
old = '''EXCLUDED_PATHS = [
    "/api/v1/setup",
    "/api/v1/auth",
    "/docs",
    "/openapi.json",
    "/health",
    "/api/v1",
]'''

new = '''EXCLUDED_PATHS = [
    "/api/v1/setup",
    "/api/v1/auth",
    "/docs",
    "/openapi.json",
    "/health",
]'''

if old in content:
    content = content.replace(old, new)
    with open('app/core/license_guard.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('FIXED! Removed /api/v1 from exclusions')
else:
    print('Pattern not found — checking...')
    if 'EXCLUDED_PATHS' in content:
        print('EXCLUDED_PATHS found but pattern mismatch')
    else:
        print('EXCLUDED_PATHS not found')