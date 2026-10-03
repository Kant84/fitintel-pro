# rfid_turnstile_test.py — ACR1252 как терминал турникета: браслет -> вход, повтор -> выход
import json, urllib.request, pathlib, time, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent / "fitintel-desktop"))
from rfid.direct_reader import DirectReader

root = pathlib.Path(__file__).parent
cfg = json.loads((root / "fitintel-desktop" / "client_settings.json").read_text(encoding="utf-8"))
B = (cfg.get("api_base") or "http://localhost:8001/api/v1").rstrip("/")
tok = json.load(urllib.request.urlopen(urllib.request.Request(
    B + "/auth/login",
    data=json.dumps({"login": cfg.get("saved_login") or "superadmin",
                     "password": cfg.get("saved_password") or "gfhjkmas"}).encode(),
    headers={"Content-Type": "application/json"})))["access_token"]
H = {"Content-Type": "application/json", "Authorization": "Bearer " + tok}

def call(path, body):
    req = urllib.request.Request(B + path, data=json.dumps(body).encode(), headers=H)
    try:
        return json.load(urllib.request.urlopen(req, timeout=30))
    except urllib.error.HTTPError as e:
        return {"http_error": e.code, "detail": e.read().decode()[:150]}

rd = DirectReader()
print("Поднесите браслет к ACR1252... (Ctrl+C — выход)")
last_uid, last_t = None, 0
while True:
    uid = rd.detect_uid()
    if uid and (uid != last_uid or time.time() - last_t > 5):
        last_uid, last_t = uid, time.time()
        print("UID:", uid)
        print("  вход :", call("/access/open", {"credential": uid, "device_id": "turnstile-1", "zone": "main"}))
        time.sleep(2)
        print("  выход:", call("/access/exit", {"credential": uid, "device_id": "turnstile-1"}))
    time.sleep(0.3)
