# tests/manual/test_e20_13.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Групповой QR для двух клиентов
resp = requests.post("http://localhost:8001/api/v1/dynamic-qr/group",
                     headers=headers,
                     json={"client_ids": ["473d5de8-3f46-4c95-9950-dd0c49c9a8d3",
                                          "000041e8-2528-4043-b571-89b2d18cc851"]})
print(f"E20.13 Create Status: {resp.status_code}")
print(f"E20.13 Create Response: {resp.text[:400]}")

if resp.status_code == 201:
    qr_payload = resp.json()["qr_payload"]
    # Проходим 3 раза: 200, 200, потом 410
    for i in range(1, 4):
        v = requests.post("http://localhost:8001/api/v1/dynamic-qr/verify",
                          headers=headers, json={"qr_payload": qr_payload})
        print(f"Verify #{i} Status: {v.status_code}")
