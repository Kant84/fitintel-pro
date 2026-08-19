# tests/manual/test_e27_14.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username", "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

resp = requests.get("http://localhost:8001/api/v1/face-id/engine/info", headers=headers)
print(f"E27.14 Status: {resp.status_code}")
print(f"E27.14 Response: {resp.text[:400]}")
