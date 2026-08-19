# tests/manual/test_e27_7.py
import requests
import base64

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username", "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Создаём временный шаблон для удаления (другой клиент)
with open("tests/photos/face_person_b.jpg", "rb") as f:
    photo_b64 = base64.b64encode(f.read()).decode()
reg = requests.post("http://localhost:8001/api/v1/face-id/register",
                    headers=headers,
                    json={"client_id": "000041e8-2528-4043-b571-89b2d18cc851", "photo": photo_b64})
template_id = reg.json()["face_template_id"]
print(f"Временный шаблон создан: {template_id}")

# Удаляем
resp = requests.delete(f"http://localhost:8001/api/v1/face-id/{template_id}", headers=headers)
print(f"E27.7 Status: {resp.status_code}")
print(f"E27.7 Response: {resp.text[:300] if resp.text else 'No content'}")
