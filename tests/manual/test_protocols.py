# tests/manual/test_protocols.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

resp = requests.get("http://localhost:8001/api/v1/devices", headers=headers)
devices = resp.json().get("items", [])
if not devices:
    print("No devices found")
    exit()

device_id = devices[0]["id"]

# Тестируем разные протоколы
protocols = [
    {"protocol": "http_api", "command": "open", "params": {"duration": 5}},
    {"protocol": "mqtt", "command": "set_mode", "params": {"mode": "auto", "qos": 2}},
    {"protocol": "websocket", "command": "get_status", "params": {}},
    {"protocol": "serial", "command": "reset", "params": {"port": "COM3", "baudrate": 115200}},
    {"protocol": "tcp_raw", "command": "ping", "params": {"host": "192.168.1.100", "port": 8080}},
    {"protocol": "modbus_tcp", "command": "read", "params": {"register": 100, "count": 3}},
]

for proto in protocols:
    resp = requests.post(f"http://localhost:8001/api/v1/devices/{device_id}/protocol", headers=headers, json=proto)
    print(f"Protocol {proto['protocol']}: Status {resp.status_code}")
    print(f"Response: {resp.text[:200]}")
    print("---")
