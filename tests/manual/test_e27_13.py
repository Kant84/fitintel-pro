# tests/manual/test_e27_13.py
import requests
import base64

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username", "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

frames = []
for name in ["face_person_a.jpg", "face_eyes_closed.jpg"]:
    with open(f"tests/photos/{name}", "rb") as f:
        frames.append(base64.b64encode(f.read()).decode())

resp = requests.post("http://localhost:8001/api/v1/face-id/liveness",
                     headers=headers, json={"frames": frames})
print(f"E27.13 Status: {resp.status_code}")
print(f"E27.13 Response: {resp.text[:400]}")
