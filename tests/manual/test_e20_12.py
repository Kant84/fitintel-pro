# tests/manual/test_e20_12.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Создаём гостевой QR по email
resp = requests.post("http://localhost:8001/api/v1/dynamic-qr/guest",
                     headers=headers, json={"email": "guest@example.com"})
print(f"E20.12 Create Status: {resp.status_code}")
print(f"E20.12 Create Response: {resp.text[:400]}")

if resp.status_code == 201:
    qr_payload = resp.json()["qr_payload"]
    # Гость проходит по QR
    v = requests.post("http://localhost:8001/api/v1/dynamic-qr/verify",
                      headers=headers, json={"qr_payload": qr_payload})
    print(f"Guest verify Status: {v.status_code} (ожидаем 200)")
    # Повторно — одноразовый, должен сгореть
    v2 = requests.post("http://localhost:8001/api/v1/dynamic-qr/verify",
                       headers=headers, json={"qr_payload": qr_payload})
    print(f"Guest re-verify Status: {v2.status_code} (ожидаем 410)")
