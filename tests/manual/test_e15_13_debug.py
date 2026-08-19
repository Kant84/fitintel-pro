# tests/manual/test_e15_13_debug.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Проверяем ID testuser123
users = requests.get("http://localhost:8001/api/v1/users", headers=headers)
for u in users.json().get("items", []):
    if u["username"] == "testuser123":
        print(f"testuser123 ID: {u['id']}")
        break

# Пытаемся открыть смену
shift = {
    "user_id": "03c4751d-2483-49fa-a4ca-9e2d8c266748",
    "starting_amount": 1000.00
}
print(f"Request user_id: {shift['user_id']}")
resp = requests.post("http://localhost:8001/api/v1/cash-desk/open", headers=headers, json=shift)
print(f"E15.13 Status: {resp.status_code}")
print(f"E15.13 Response: {resp.text[:500]}")
