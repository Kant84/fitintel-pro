# tests/manual/test_e19_9.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Получаем список пользователей (тренеров)
users_resp = requests.get("http://localhost:8001/api/v1/users", headers=headers)
print(f"Users Status: {users_resp.status_code}")

# Получаем список услуг
services_resp = requests.get("http://localhost:8001/api/v1/services", headers=headers)
services = services_resp.json()

# Создаём услугу с тренером
service = {
    "name": "Услуга с тренером",
    "category": "PERSONAL_TRAINER",
    "price": 1000.00,
    "trainer_id": "7db07a4c-0bf9-4a57-bd9f-9f088ba15783"
}
create_resp = requests.post("http://localhost:8001/api/v1/services", headers=headers, json=service)
print(f"Create Status: {create_resp.status_code}")
print(f"Create Response: {create_resp.text[:500]}")

if create_resp.status_code == 201:
    trainer_id = create_resp.json().get("trainer_id")
    if trainer_id:
        # Фильтруем по тренеру
        resp = requests.get(f"http://localhost:8001/api/v1/services?trainer_id={trainer_id}", headers=headers)
        print(f"E19.9 Status: {resp.status_code}")
        print(f"E19.9 Response: {resp.text[:500]}")
    else:
        print("E19.9: trainer_id is null")
else:
    print("E19.9: Failed to create service")
