# tests/manual/test_e19_6.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Удаляем услугу (создаём новую для удаления)
service = {
    "name": "Услуга для удаления",
    "category": "SAUNA",
    "price": 100.00
}
create_resp = requests.post("http://localhost:8001/api/v1/services", headers=headers, json=service)
service_id = create_resp.json()["id"]

# Удаляем
resp = requests.delete(f"http://localhost:8001/api/v1/services/{service_id}", headers=headers)
print(f"E19.6 Status: {resp.status_code}")
print(f"E19.6 Response: {resp.text[:500] if resp.text else 'No content'}")
