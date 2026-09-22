import json, urllib.request
from pathlib import Path

cfg = json.load(open(r"fitintel-desktop\client_settings.json", encoding="utf-8"))
token = cfg.get("token") or cfg.get("access_token")
base = cfg.get("api_base", "http://localhost:8001/api/v1")

r = urllib.request.Request(
    base.rstrip("/") + "/ml/events/recent?limit=5",
    headers={"Authorization": "Bearer " + token})
data = json.load(urllib.request.urlopen(r, timeout=10))

for e in data["events"]:
    print(e["created_at"][:19], "|", e["event_type"], "|", e["payload"])