# tests/manual/test_e20_4.py
import requests
import json
import base64
import hmac
import hashlib
import time

QR_SECRET = "fitintel-qr-secret-2026"

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Создаём payload с истёкшим временем (10 минут назад, TTL 5 мин)
old_timestamp = int(time.time()) - 600
expires_at = old_timestamp + 300
payload = {
    "client_id": "473d5de8-3f46-4c95-9950-dd0c49c9a8d3",
    "timestamp": old_timestamp,
    "ttl": 300,
    "expires_at": expires_at
}
payload_json = json.dumps(payload, sort_keys=True)
signature = hmac.new(QR_SECRET.encode(), payload_json.encode(), hashlib.sha256).hexdigest()
payload["signature"] = signature
qr_payload = base64.b64encode(json.dumps(payload).encode()).decode()

# Проверяем истёкший QR
resp = requests.post("http://localhost:8001/api/v1/dynamic-qr/verify",
                     headers=headers, json={"qr_payload": qr_payload})
print(f"E20.4 Status: {resp.status_code}")
print(f"E20.4 Response: {resp.text[:500]}")
