# tests/manual/test_e14_14.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

subscription_id = "51b59b43-a450-4d37-8b9c-78e6cb2163cd"
update = {
    "notes": "Обновлённая подписка",
    "auto_renew": True
}
resp = requests.patch(f"http://localhost:8001/api/v1/subscriptions/{subscription_id}", headers=headers, json=update)
print(f"E14.14 Status: {resp.status_code}")
print(f"E14.14 Response: {resp.text[:500]}")
