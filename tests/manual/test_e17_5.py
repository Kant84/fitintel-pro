# tests/manual/test_e17_5.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Обновляем устройство
device_id = "a1effed6-357f-49fd-97b0-0e85ed1db91a"
update_data = {
    "name": "Обновлённый турникет"
}
resp = requests.put(f"http://localhost:8001/api/v1/devices/{device_id}", headers=headers, json=update_data)
print(f"E17.5 Status: {resp.status_code}")
print(f"E17.5 Response: {resp.text[:500]}")
