#!/usr/bin/env python3
"""Имитация АТОЛ ДТО 10 «почти боевая» (mock v3).

Совместима с контрактом, который ждёт сервер FitIntel (POST {"requests": [...]}).
Эмулирует: смены (openShift/closeShift/getShiftStatus), чеки (sell/sellReturn),
счётчики смены (нал/безнал/возвраты), внесение/выплату, X-отчёт, ФН, очередь ОФД,
сценарии отказов. Управление сценариями: GET /admin?...

Запуск:  python3 tools/mock_atol.py          (порт 18004)
Состояние: файл (по умолчанию ~/mock_atol_state.json, переопределить MOCK_ATOL_STATE).
"""
from http.server import BaseHTTPRequestHandler, HTTPServer
import json, os, threading, time
from pathlib import Path
from urllib.parse import urlparse, parse_qs

STATE_FILE = os.environ.get("MOCK_ATOL_STATE", str(Path.home() / "mock_atol_state.json"))
LOCK = threading.Lock()

DEFAULT = {
    "fd": 0,
    "shift_open": False,
    "shift_opened_at": None,
    "shift_number": 0,
    "cashier": None,
    "cash_in_shift": 0.0,     # наличные за смену
    "card_in_shift": 0.0,     # безнал за смену
    "return_in_shift": 0.0,   # возвраты за смену
    "cash_total": 0.0,        # наличные с начала "жизни" ФН
    "fn": "9999888877776666",
    "fn_valid_until": "2029-12-31",
    "paper": True,            # False -> продажи падают «Нет бумаги»
    "delay": 0,               # секунды задержки ответа (разрыв связи)
    "fail_next": 0,           # 1 -> следующая продажа упадёт с ошибкой печати
    "sent_fd": 0,             # сколько ФД «ушло» в ОФД
}


def _load():
    if os.path.exists(STATE_FILE):
        try:
            return {**DEFAULT, **json.load(open(STATE_FILE))}
        except Exception:
            pass
    return dict(DEFAULT)


def _save(s):
    tmp = STATE_FILE + ".tmp"
    json.dump(s, open(tmp, "w"))
    os.replace(tmp, STATE_FILE)


STATE = _load()


def _fp(s):
    return {"error": 0, "result": True, "fiscalParams": {
        "fiscalDocumentNumber": s["fd"],
        "fiscalDocumentSign": "MOCK%010d" % (1000000000 + s["fd"]),
        "fiscalDriveNumber": "999988887777666655",
        "fiscalReceiptNumber": s["fd"],
        "dateTime": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "fnNumber": s["fn"],
        "shiftNumber": s["shift_number"],
    }}


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _s(self, d, code=200):
        b = json.dumps(d, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        global STATE
        u = urlparse(self.path)
        if u.path == "/status":
            s = STATE
            self._s({"connected": True,
                     "shiftOpen": s["shift_open"],
                     "shiftOpenedAt": s["shift_opened_at"],
                     "shiftNumber": s["shift_number"],
                     "fn": s["fn"], "fnValidUntil": s["fn_valid_until"],
                     "paper": s["paper"],
                     "cashInShift": s["cash_in_shift"],
                     "cardInShift": s["card_in_shift"],
                     "returnInShift": s["return_in_shift"],
                     "cashTotal": s["cash_total"],
                     "fdNumber": s["fd"],
                     "ofdUnsent": s["fd"] - s["sent_fd"]})
            return
        if u.path == "/admin":
            q = {k: v[0] for k, v in parse_qs(u.query).items()}
            with LOCK:
                if "paper" in q:
                    STATE["paper"] = q["paper"] == "in"
                if "delay" in q:
                    STATE["delay"] = int(q["delay"])
                if "fail_next" in q:
                    STATE["fail_next"] = int(q["fail_next"])
                if "cashier" in q:
                    STATE["cashier"] = q["cashier"]
                if "ofd_send" in q:
                    STATE["sent_fd"] = STATE["fd"]
                if "reset" in q:
                    STATE = dict(DEFAULT)
                _save(STATE)
            self._s({"ok": True, "state": STATE})
            return
        self._s({})

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", 0))).decode("utf-8", "replace")
        print(">>> ATOL REQUEST:", body[:300], flush=True)
        try:
            reqs = json.loads(body).get("requests", [])
        except Exception:
            reqs = []
        if STATE["delay"]:
            time.sleep(STATE["delay"])
        results = []
        with LOCK:
            s = STATE
            for r in reqs:
                t = r.get("type")
                err = lambda m: {"error": 1, "description": m}

                if t == "getShiftStatus":
                    results.append({"error": 0, "result": {"shiftStatus": {
                        "state": "opened" if s["shift_open"] else "closed",
                        "number": s["shift_number"],
                        "openedAt": s["shift_opened_at"]}}})
                elif t == "getShiftTotals":
                    results.append({"error": 0, "result": {"shiftTotals": {
                        "cash": s["cash_in_shift"], "card": s["card_in_shift"],
                        "returns": s["return_in_shift"]}}})
                elif t == "getFnInfo":
                    results.append({"error": 0, "result": {"fnInfo": {
                        "fnNumber": s["fn"], "validUntil": s["fn_valid_until"],
                        "fdTotal": s["fd"], "ofdUnsent": s["fd"] - s["sent_fd"]}}})
                elif t == "ofdExchangeStatus":
                    results.append({"error": 0, "result": {
                        "unsentCount": s["fd"] - s["sent_fd"],
                        "lastOkp": time.strftime("%Y-%m-%dT%H:%M:%S")}})
                elif t == "openShift":
                    if s["shift_open"]:
                        results.append(err("Смена уже открыта"))
                    else:
                        s["shift_open"] = True
                        s["shift_number"] += 1
                        s["shift_opened_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
                        s["cash_in_shift"] = s["card_in_shift"] = s["return_in_shift"] = 0.0
                        s["cashier"] = r.get("cashier") or s["cashier"] or "Кассир"
                        s["fd"] += 1
                        results.append(_fp(s))
                elif t == "closeShift":
                    if not s["shift_open"]:
                        results.append(err("Смена уже закрыта"))
                    else:
                        s["shift_open"] = False
                        s["shift_opened_at"] = None
                        s["fd"] += 1
                        results.append({**_fp(s), "result": {
                            "cash": s["cash_in_shift"], "card": s["card_in_shift"],
                            "returns": s["return_in_shift"]}})
                elif t in ("sell", "sellReturn"):
                    if not s["paper"]:
                        results.append(err("Нет бумаги — замените рулон"))
                    elif s["fail_next"]:
                        s["fail_next"] = 0
                        results.append(err("Ошибка печати чека (симуляция)"))
                    elif not s["shift_open"]:
                        results.append(err("Смена закрыта — чек невозможен"))
                    else:
                        cash = float(r.get("cash", 0) or 0)
                        card = float(r.get("card", 0) or 0)
                        amount = float(r.get("amount", cash + card) or 0)
                        if t == "sell":
                            s["cash_in_shift"] += cash
                            s["card_in_shift"] += card
                            s["cash_total"] += cash
                        else:
                            s["return_in_shift"] += amount
                            s["cash_in_shift"] -= amount
                            s["cash_total"] -= amount
                        s["fd"] += 1
                        results.append(_fp(s))
                elif t == "cashIn":
                    amt = float(r.get("amount", 0) or 0)
                    if amt <= 0:
                        results.append(err("Некорректная сумма внесения"))
                    else:
                        if not s["shift_open"]:  # у АТОЛ внесение авто-открывает смену
                            s["shift_open"] = True
                            s["shift_number"] += 1
                            s["shift_opened_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
                        s["cash_in_shift"] += amt
                        s["cash_total"] += amt
                        s["fd"] += 1
                        results.append(_fp(s))
                elif t == "cashOut":
                    amt = float(r.get("amount", 0) or 0)
                    if not s["shift_open"]:
                        results.append(err("Смена закрыта"))
                    elif amt <= 0 or amt > s["cash_in_shift"]:
                        results.append(err("В кассе недостаточно денег для выплаты"))
                    else:
                        s["cash_in_shift"] -= amt
                        s["cash_total"] -= amt
                        s["fd"] += 1
                        results.append(_fp(s))
                elif t == "reportX":
                    if not s["shift_open"]:
                        results.append(err("Смена закрыта"))
                    else:
                        results.append({"error": 0, "result": {
                            "cash": s["cash_in_shift"], "card": s["card_in_shift"],
                            "returns": s["return_in_shift"]}})
                else:
                    results.append({"error": 0, "result": True})
            _save(s)
        self._s({"results": results})


if __name__ == "__main__":
    print("mock АТОЛ v3 на :18004, state =", STATE_FILE, flush=True)
    HTTPServer(("0.0.0.0", 18004), H).serve_forever()