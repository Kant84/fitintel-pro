# fix_dashboard_import.py
with open('app/api/v1/analytics_dashboard.py', 'r', encoding='utf-8') as f:
    content = f.read()

old = '''import json
from datetime import date
from fastapi import APIRouter, Depends'''

new = '''import json
from datetime import date, timedelta
from fastapi import APIRouter, Depends'''

if old in content:
    content = content.replace(old, new)
    with open('app/api/v1/analytics_dashboard.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("timedelta import added!")
else:
    print("ERROR")
