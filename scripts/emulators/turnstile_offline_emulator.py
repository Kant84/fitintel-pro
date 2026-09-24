# scripts/emulators/turnstile_offline_emulator.py
"""
Эмулятор контроллера СКУД (турникет), имитирует протокол ITCService.
Шлет POST /skud/check-access на сервер FitIntel Pro и показывает ответ контроллера.

Запуск (один проход):
    python scripts/emulators/turnstile_offline_emulator.py --server http://192.168.101.182/api/v1 --card 04577EAA2A6180

Сценарий (вход -> выход -> неизвестная карта):
    python scripts/emulators/turnstile_offline_emulator.py --server http://192.168.101.182/api/v1 --card 04577EAA2A6180 --scenario
"""
import argparse
import json
import time
import uuid
import urllib.request
import urllib.error
import base64

SKUD_USER = "itc"
SKUD_PASS = "itc_secret_2026"


def check_access(base_url: str, device_id: str, card: str, direction: str = "entry", timeout: int = 10):
    payload = {
        "device_id": device_id,
        "client_card": card,
        "request_id": str(uuid.uuid4()),
        "direction": direction,
    }
    req = urllib.request.Request(
        base_url.rstrip("/") + "/skud/checkaccess",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "Authorization": "Basic " + base64.b64encode(("%s:%s" % (SKUD_USER, SKUD_PASS)).encode()).decode()},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.load(e)
        except Exception:
            return e.code, {"raw": e.read().decode()[:200]}
    except Exception as e:
        return None, {"error": str(e)}


def _print_result(title: str, status, data: dict):
    print()
    print("=== " + title + " ===")
    print("HTTP", status)
    grant = data.get("grant_access")
    if grant == 1 or grant is True:
        print("-> ПРОХОД РАЗРЕШЕН |", data.get("text", ""), "|", data.get("text_full", ""))
    elif grant == 0 or grant is False:
        print("-> ПРОХОД ЗАПРЕЩЕН |", data.get("text", ""), "|", data.get("text_full", ""))
    else:
        print(json.dumps(data, ensure_ascii=False, indent=2))


def main():
    ap = argparse.ArgumentParser(description="Эмулятор турникета СКУД")
    ap.add_argument("--server", required=True, help="Базовый URL API, напр. http://192.168.101.182/api/v1")
    ap.add_argument("--device", default="turnstile_main_entrance", help="ID устройства (из config/devices.yaml)")
    ap.add_argument("--card", required=True, help="UID RFID-карты (hex)")
    ap.add_argument("--scenario", action="store_true", help="Сценарий: вход -> выход -> неизвестная карта")
    args = ap.parse_args()

    st, data = check_access(args.server, args.device, args.card, "entry")
    _print_result("ВХОД: приложена карта " + args.card, st, data)

    if args.scenario:
        time.sleep(1)
        st, data = check_access(args.server, args.device, args.card, "exit")
        _print_result("ВЫХОД: та же карта", st, data)

        time.sleep(1)
        st, data = check_access(args.server, args.device, "FFFFFFFFFFFF", "entry")
        _print_result("ВХОД: НЕИЗВЕСТНАЯ карта FFFFFFFFFFFF", st, data)

    print()
    print("Готово. Проверьте визиты: desktop -> Входы/Выходы.")


if __name__ == "__main__":
    main()
