# scripts/emulators/qr_turnstile_emulator.py
"""Эмулятор турникета СКУД (ITC-протокол): вход по QR-коду из приложения.
Сценарий: логин -> находит клиента с основаниями входа -> генерирует подписанный QR
-> шлет его в /skud/checkaccess как client_card -> показывает ответ контроллера.

    python scripts/emulators/qr_turnstile_emulator.py --server http://192.168.101.182/api/v1 --login SuperAdmin --password gfhjkmas
"""
import argparse, base64, json, urllib.request, urllib.error

SKUD_USER = "itc"
SKUD_PASS = "itc_secret_2026"


def http(method, url, payload=None, basic=None, bearer=None):
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode() if payload else None,
        headers={"Content-Type": "application/json"}, method=method)
    if basic:
        req.add_header("Authorization", "Basic " + base64.b64encode(basic.encode()).decode())
    if bearer:
        req.add_header("Authorization", "Bearer " + bearer)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            b = r.read().decode()
            return r.status, json.loads(b) if b else {}
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            return e.code, {"raw": "?"}
    except Exception as e:
        return None, {"error": str(e)}


def main():
    ap = argparse.ArgumentParser(description="Эмулятор турникета: вход по QR")
    ap.add_argument("--server", required=True)
    ap.add_argument("--login", required=True)
    ap.add_argument("--password", required=True)
    ap.add_argument("--device", default="turnstile_main_entrance")
    ap.add_argument("--qr", default=None, help="готовый qr_payload; если не задан — сгенерируем для клиента с абонементом")
    args = ap.parse_args()
    base = args.server.rstrip("/")

    st, tok = http("POST", base + "/auth/login", {"login": args.login, "password": args.password})
    jwt = (tok or {}).get("access_token")
    assert jwt, "Вход не удался: %s %s" % (st, tok)
    print("OK: токен получен")

    qr = args.qr
    if not qr:
        st, data = http("GET", base + "/clients?limit=100", bearer=jwt)
        clients = data.get("items", data) if isinstance(data, dict) else data
        for c in clients or []:
            cid = c.get("id")
            st2, g = http("POST", base + "/dynamic-qr/generate",
                          {"client_id": cid, "expires_in_minutes": 2}, bearer=jwt)
            if st2 == 200 and g.get("qr_payload"):
                nm = ((c.get("last_name") or "") + " " + (c.get("first_name") or "")).strip()
                print("OK: QR сгенерирован для клиента:", nm or cid)
                qr = g["qr_payload"]
                break
        if not qr:
            print("Нет клиентов с основаниями входа (нужен активный абонемент/занятие)")
            return

    st, resp = http("POST", base + "/skud/checkaccess",
                    {"device_id": args.device, "client_card": qr,
                     "request_id": "qr-demo-1", "direction": "entry"},
                    basic="%s:%s" % (SKUD_USER, SKUD_PASS))
    print("HTTP", st)
    grant = (resp or {}).get("grant_access")
    if grant == 1 or grant is True:
        print("-> ПРОХОД РАЗРЕШЕН |", resp.get("text", ""), "|", resp.get("text_full", ""))
    elif grant == 0 or grant is False:
        print("-> ПРОХОД ЗАПРЕЩЕН |", resp.get("text", ""), "|", resp.get("text_full", ""))
    else:
        print(json.dumps(resp, ensure_ascii=False, indent=2))
    print("Проверьте визит: desktop -> Входы/Выходы")


if __name__ == "__main__":
    main()
