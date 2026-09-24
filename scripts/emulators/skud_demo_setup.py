# scripts/emulators/skud_demo_setup.py
"""
Подготовка тестовых данных для эмуляции СКУД на чистой БД:
клиент + тариф + абонемент + привязка RFID-карты.

    python scripts/emulators/skud_demo_setup.py --server http://192.168.101.182/api/v1 --login admin --password Admin123!ChangeMe --card 04577EAA2A6180
"""
import argparse
import json
import urllib.request
import urllib.error
import datetime


def req(method, url, token=None, payload=None):
    r = urllib.request.Request(url, data=json.dumps(payload).encode() if payload else None,
                               headers={"Content-Type": "application/json"}, method=method)
    if token:
        r.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(r, timeout=15) as resp:
            body = resp.read().decode()
            return resp.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:300]
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, {"raw": body}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--server", required=True)
    ap.add_argument("--login", required=True)
    ap.add_argument("--password", required=True)
    ap.add_argument("--card", default="04577EAA2A6180")
    ap.add_argument("--phone", default="+79000000001")
    ap.add_argument("--email", default="skud.test@fitnexus.ru")
    args = ap.parse_args()
    base = args.server.rstrip("/")

    st, tok = req("POST", base + "/auth/login", payload={"login": args.login, "password": args.password})
    token = tok.get("access_token")
    assert token, "Вход не удался: %s %s" % (st, tok)
    print("OK: токен получен")

    st, client = req("POST", base + "/clients/", token,
                     {"first_name": "Тест", "last_name": "СКУДов", "phone": args.phone, "email": args.email})
    if st in (200, 201):
        client_id = client.get("id")
        print("OK: клиент создан:", client_id)
    else:
        st2, clients = req("GET", base + "/clients?phone=" + args.phone, token)
        if isinstance(clients, dict):
            clients = clients.get("items", [])
        client_id = (clients[0].get("id") if isinstance(clients, list) and clients else None)
        print("Клиент уже есть (или ошибка %s), id:" % st, client_id)
    assert client_id, "Не удалось получить client_id"

    st, tariff = req("POST", base + "/tariffs/", token,
                     {"code": "TEST_DAY", "name": "Тестовый день", "price": 500, "duration_days": 30, "is_unlimited": True})
    if st in (200, 201):
        tariff_id = tariff.get("id")
        print("OK: тариф создан:", tariff_id)
    else:
        st2, tariffs = req("GET", base + "/tariffs/", token)
        if isinstance(tariffs, dict):
            tariffs = tariffs.get("items", [])
        tariff_id = (tariffs[0].get("id") if isinstance(tariffs, list) and tariffs else None)
        print("Тариф уже есть (или ошибка %s), id:" % st, tariff_id)
    assert tariff_id, "Не удалось получить tariff_id"

    st, sub = req("POST", base + "/subscriptions/", token,
                  {"client_id": client_id, "tariff_id": tariff_id, "start_date": datetime.date.today().isoformat()})
    print("Абонемент:", st, str(sub)[:150])

    st, cred = req("POST", base + "/credentials/rfid/force-write", token,
                   {"client_id": client_id, "credential_value": args.card,
                    "rfid_manufacturer": "KERONG", "rfid_model": "KR-S50", "sector": 0, "block": 1})
    print("Карта привязана:", st, str(cred)[:150])

    print()
    print("ГОТОВО. Запускайте эмулятор турникета с картой:", args.card)


if __name__ == "__main__":
    main()
