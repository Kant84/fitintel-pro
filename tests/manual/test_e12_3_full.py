# test_e12_3_full.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

resp = requests.get("http://localhost:8001/api/v1/video-alerts", headers=headers)
print(f"E12.3 Status: {resp.status_code}")
print(f"E12.3 Full Response:\n{resp.text}")
