# tests/manual/test_e20_10.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Генерируем QR, привязанный к телефону A
gen = requests.post("http://localhost:8001/api/v1/dynamic-qr/generate",
                    headers=headers,
                    json={"client_id": "473d5de8-3f46-4c95-9950-dd0c49c9a8d3",
                          "device_id": "phone-A-fingerprint-123"})
print(f"Generate Status: {gen.status_code}")
qr_payload = gen.json()["qr_payload"]

# Пытаемся проверить с телефона B — должно быть 403
resp_b = requests.post("http://localhost:8001/api/v1/dynamic-qr/verify",
                       headers=headers,
                       json={"qr_payload": qr_payload, "device_id": "phone-B-fingerprint-999"})
print(f"Verify from Phone B Status: {resp_b.status_code}")
print(f"Verify from Phone B Response: {resp_b.text[:300]}")

# Контроль: проверка с телефона A — должно быть 200
resp_a = requests.post("http://localhost:8001/api/v1/dynamic-qr/verify",
                       headers=headers,
                       json={"qr_payload": qr_payload, "device_id": "phone-A-fingerprint-123"})
print(f"Verify from Phone A Status: {resp_a.status_code}")
print(f"Verify from Phone A Response: {resp_a.text[:300]}")
