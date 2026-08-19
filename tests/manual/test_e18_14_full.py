# tests/manual/test_e18_14_full.py
import requests

login = requests.post("http://localhost:8001/api/v1/auth/login", json={
    "login": "my_new_username",
    "password": "TestPass123!"
})
token = login.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Прогноз на 7 дней
resp = requests.post("http://localhost:8001/api/v1/analytics/forecast", headers=headers, json={
    "metric": "attendance",
    "days_ahead": 7
})
data = resp.json()
print(f"E18.14 Status: {resp.status_code}")
print(f"Metric: {data['metric']}")
print(f"Trend: {data['trend']}")
print(f"Recommendation: {data['recommendation']}")
print(f"History points: {len(data['history'])}")
print(f"Forecast points: {len(data['forecast'])}")
if data.get('ml_features'):
    print(f"ML Features:")
    for key, value in data['ml_features'].items():
        print(f"  {key}: {value}")
