# tests/manual/test_e15_14.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Проверяем текущую смену
current = requests.get("http://localhost:8001/api/v1/cash-desk/current", headers=headers)
print(f"Current Status: {current.status_code}")
print(f"Current Response: {current.text[:500]}")

# Авто-закрытие — проверяем через verify
verify = requests.post("http://localhost:8001/api/v1/cash-desk/verify", headers=headers, json={})
print(f"Verify Status: {verify.status_code}")
print(f"Verify Response: {verify.text[:500]}")
