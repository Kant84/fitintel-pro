# tests/manual/test_e27_2.py
import requests
import base64

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username", "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

with open("tests/photos/no_face.jpg", "rb") as f:
    photo_b64 = base64.b64encode(f.read()).decode()

resp = requests.post("http://localhost:8001/api/v1/face-id/register",
                     headers=headers,
                     json={"client_id": "473d5de8-3f46-4c95-9950-dd0c49c9a8d3", "photo": photo_b64})
print(f"E27.2 Status: {resp.status_code}")
print(f"E27.2 Response: {resp.text[:300]}")
