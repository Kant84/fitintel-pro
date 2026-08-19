# tests/manual/test_e17_7_full.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Пытаемся удалить устройство (первое в списке)
resp = requests.get("http://localhost:8001/api/v1/devices", headers=headers)
devices = resp.json().get("items", [])
if devices:
    device_id = devices[0]["id"]
    resp = requests.delete(f"http://localhost:8001/api/v1/devices/{device_id}", headers=headers)
    print(f"E17.7 Status: {resp.status_code}")
    print(f"E17.7 Full Response:\n{resp.text}")
else:
    print("No devices found")
