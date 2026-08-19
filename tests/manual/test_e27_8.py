# tests/manual/test_e27_8.py
import requests
import base64

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username", "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

templates = requests.get("http://localhost:8001/api/v1/face-id", headers=headers).json()
template_id = templates[0]["id"]

with open("tests/photos/face_person_a.jpg", "rb") as f:
    photo_b64 = base64.b64encode(f.read()).decode()

resp = requests.put(f"http://localhost:8001/api/v1/face-id/{template_id}",
                    headers=headers, json={"photo": photo_b64})
print(f"E27.8 Status: {resp.status_code}")
print(f"E27.8 Response: {resp.text[:400]}")
