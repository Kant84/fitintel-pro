# tests/manual/test_e20_8.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Получаем (или создаём) свой QR
my_qr = requests.get("http://localhost:8001/api/v1/dynamic-qr/my", headers=headers)
print(f"My QR Status: {my_qr.status_code}")
qr_id = my_qr.json()["id"]

# Отзываем QR
resp = requests.post(f"http://localhost:8001/api/v1/dynamic-qr/{qr_id}/revoke",
                     headers=headers)
print(f"E20.8 Status: {resp.status_code}")
print(f"E20.8 Response: {resp.text[:500]}")
