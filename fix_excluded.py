import re

with open('app/core/license_guard.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Заменяем is_path_excluded
old = '    @staticmethod' + chr(10) + '    def is_path_excluded(path: str) -> bool:' + chr(10) + '        """Check if path is excluded from license check."""' + chr(10) + '        for excluded in EXCLUDED_PATHS:' + chr(10) + '            if path.startswith(excluded):' + chr(10) + '                return True' + chr(10) + '        return False'

new = '    @staticmethod' + chr(10) + '    def is_path_excluded(path: str) -> bool:' + chr(10) + '        """Check if path is excluded from license check."""' + chr(10) + '        for excluded in EXCLUDED_PATHS:' + chr(10) + '            if path == excluded or path.startswith(excluded + "/"):' + chr(10) + '                return True' + chr(10) + '        return False'

if old in content:
    content = content.replace(old, new)
    with open('app/core/license_guard.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('OK')
else:
    print('Pattern not found')