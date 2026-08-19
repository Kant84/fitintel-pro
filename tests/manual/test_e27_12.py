# tests/manual/test_e27_12.py
import requests
import base64

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username", "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

for name, expect in [("face_on_screen.jpg", 403), ("face_person_a.jpg", 200)]:
    with open(f"tests/photos/{name}", "rb") as f:
        photo_b64 = base64.b64encode(f.read()).decode()
    resp = requests.post("http://localhost:8001/api/v1/face-id/anti-spoofing",
                         headers=headers, json={"photo": photo_b64})
    print(f"{name}: Status {resp.status_code} (ожидаем {expect}) — {resp.text[:200]}")
