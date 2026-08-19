# tests/manual/test_e20_7.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

client_id = "473d5de8-3f46-4c95-9950-dd0c49c9a8d3"

# Сначала генерируем свежий QR, чтобы точно был активный
gen = requests.post("http://localhost:8001/api/v1/dynamic-qr/generate",
                    headers=headers, json={"client_id": client_id})
print(f"Generate Status: {gen.status_code}")

# Получаем активный QR клиента
resp = requests.get(f"http://localhost:8001/api/v1/dynamic-qr?client_id={client_id}",
                    headers=headers)
print(f"E20.7 Status: {resp.status_code}")
print(f"E20.7 Response: {resp.text[:500]}")
