# tests/manual/test_e27_10.py
import requests
import base64

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username", "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

with open("tests/photos/face_person_a.jpg", "rb") as f:
    photo_b64 = base64.b64encode(f.read()).decode()

# Клиент подходит к турникету, камера снимает лицо
resp = requests.post("http://localhost:8001/api/v1/face-id/turnstile",
                     headers=headers,
                     json={"photo": photo_b64, "device_id": "turnstile_001"})
print(f"E27.10 Status: {resp.status_code}")
print(f"E27.10 Response: {resp.text[:500]}")
