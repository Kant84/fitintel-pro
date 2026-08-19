# tests/manual/test_e27_4.py
import requests
import base64

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username", "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

with open("tests/photos/face_person_a.jpg", "rb") as f:
    photo_b64 = base64.b64encode(f.read()).decode()

resp = requests.post("http://localhost:8001/api/v1/face-id/verify",
                     headers=headers, json={"photo": photo_b64})
print(f"E27.4 Status: {resp.status_code}")
print(f"E27.4 Response: {resp.text[:400]}")
