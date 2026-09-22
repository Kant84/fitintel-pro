import json, urllib.request
from pathlib import Path

cfg = json.load(open(r"fitintel-desktop\client_settings.json", encoding="utf-8"))
token = cfg.get("token") or cfg.get("access_token")
base = cfg.get("api_base", "http://localhost:8001/api/v1")

CLIENT_ID = "3e86004e-75b1-46ec-9f1e-941c6b7f9b53"

def get(path):
    r = urllib.request.Request(
        base.rstrip("/") + path,
        headers={"Authorization": "Bearer " + token})
    return json.load(urllib.request.urlopen(r, timeout=10))

print("features:  ", get(f"/ml/features/{CLIENT_ID}"))
print("prediction:", get(f"/ml/predict/churn/{CLIENT_ID}"))