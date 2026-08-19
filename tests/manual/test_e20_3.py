# tests/manual/test_e20_3.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Генерируем QR
gen = requests.post("http://localhost:8001/api/v1/dynamic-qr/generate",
                    headers=headers, json={"client_id": "473d5de8-3f46-4c95-9950-dd0c49c9a8d3"})
qr_payload = gen.json()["qr_payload"]

# Проверяем QR
resp = requests.post("http://localhost:8001/api/v1/dynamic-qr/verify",
                     headers=headers, json={"qr_payload": qr_payload})
print(f"E20.3 Status: {resp.status_code}")
print(f"E20.3 Response: {resp.text[:500]}")
