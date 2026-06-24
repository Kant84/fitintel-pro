# fix_basemodel_import.py
with open('app/api/v1/hardware.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_import = '''from fastapi import APIRouter, Depends, HTTPException'''
new_import = '''from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field'''

if old_import in content:
    content = content.replace(old_import, new_import)
    with open('app/api/v1/hardware.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Импорт BaseModel и status добавлен!")
else:
    print("ERROR: Не найден импорт")
