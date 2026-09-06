# Вставьте в консоль Python (внутри venv) для теста API:
import requests, json

base = "http://localhost:8001/api/v1"
token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI3ZGIwN2E0Yy0wYmY5LTRhNTctYmQ5Zi05ZjA4OGJhMTU3ODMiLCJleHAiOjE3ODg3MTU2NzMsInRva2VuX3R5cGUiOiJhY2Nlc3MifQ.bhCxEOqwoNtLz1vio5GOR9aHftLxnVTrrmVFxWMsxrE"  # возьмите из client_settings.json

headers = {"Authorization": f"Bearer {token}"}

# 1. Проверить endpoint мастера
r = requests.get(f"{base}/setup/status", headers=headers)
print("Статус:", r.status_code, r.json())

# 2. Проверить лицензию
r = requests.post(f"{base}/license/validate", headers=headers, json={"license_key": "тест"})
print("Лицензия:", r.status_code)

# 3. Проверить создание клуба
r = requests.post(f"{base}/clubs/", headers=headers, json={"name": "Тестовый клуб", "address": "ул. Тестовая"})
print("Клуб:", r.status_code, r.json())