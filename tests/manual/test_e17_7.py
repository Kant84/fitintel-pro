# tests/manual/test_e17_7.py
import requests
import random
import uuid

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Пытаемся удалить устройство, которое может быть привязано
# Проверяем, есть ли устройства с типом turnstile
resp = requests.get("http://localhost:8001/api/v1/devices", headers=headers)
devices = resp.json().get("items", [])
turnstiles = [d for d in devices if d["device_type"] == "turnstile"]

if turnstiles:
    device_id = turnstiles[0]["id"]
    resp = requests.delete(f"http://localhost:8001/api/v1/devices/{device_id}", headers=headers)
    print(f"E17.7 Status: {resp.status_code}")
    print(f"E17.7 Response: {resp.text[:500]}")
else:
    print("No turnstiles found")
