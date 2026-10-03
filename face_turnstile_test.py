# face_turnstile_test.py — виртуальный турникет по лицу.
# ПРОБЕЛ = вход (/face-id/turnstile), E = выход (/face-id/turnstile-exit), q = закрыть.
# Распознавание выполняет СЕРВЕР.
import base64, json, urllib.request, pathlib

root = pathlib.Path(__file__).parent
cfg = json.loads((root / "fitintel-desktop" / "client_settings.json").read_text(encoding="utf-8"))
B = (cfg.get("api_base") or "http://localhost:8001/api/v1").rstrip("/")
login = cfg.get("saved_login") or "superadmin"
password = cfg.get("saved_password") or "gfhjkmas"

tok = json.load(urllib.request.urlopen(urllib.request.Request(
    B + "/auth/login",
    data=json.dumps({"login": login, "password": password}).encode(),
    headers={"Content-Type": "application/json"})))["access_token"]
print("Сервер:", B, "| токен получен")

import cv2

def send(path):
    _, buf = cv2.imencode(".jpg", frame)
    body = {"photo": base64.b64encode(buf).decode(),
            "device_id": "home-cam-1", "zone": "main"}
    req = urllib.request.Request(B + path, data=json.dumps(body).encode(),
          headers={"Content-Type": "application/json",
                   "Authorization": "Bearer " + tok})
    try:
        return json.load(urllib.request.urlopen(req, timeout=90))
    except urllib.error.HTTPError as e:
        return {"http_error": e.code, "detail": e.read().decode()[:200]}

cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
print("Смотрите в камеру... ПРОБЕЛ = вход, E = выход, q = закрыть")
while True:
    ok, frame = cap.read()
    if not ok:
        print("Камера недоступна")
        break
    cv2.imshow("FaceTurnstile", frame)
    key = cv2.waitKey(1) & 0xFF
    if key == ord(" "):
        r = send("/face-id/turnstile")
        print(">>>", "ПРОХОД РАЗРЕШЁН" if r.get("access_granted") else "ОТКАЗ:", r)
    if key == ord("e"):
        r = send("/face-id/turnstile-exit")
        print(">>>", "ВЫХОД" if r.get("exit_granted") else "ОТКАЗ ВЫХОДА:", r)
    if key == ord("q"):
        break
cap.release()
cv2.destroyAllWindows()