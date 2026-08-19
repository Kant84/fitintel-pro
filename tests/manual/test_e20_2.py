# tests/manual/test_e20_2.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Клиент БЕЗ активного абонемента
client_id = "000041e8-2528-4043-b571-89b2d18cc851"

resp = requests.post("http://localhost:8001/api/v1/dynamic-qr/generate",
                     headers=headers, json={"client_id": client_id})
print(f"E20.2 Status: {resp.status_code}")
print(f"E20.2 Response: {resp.text[:500]}")
