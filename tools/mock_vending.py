#!/usr/bin/env python3
"""Эмулятор вендинг-автомата (v1).

Примеры:
  python tools/mock_vending.py purchase --token vend-test-01 --client-id <id> --product "Вода" --price 50
  python tools/mock_vending.py confirm --token vend-test-01 --sale <sale_id> --status dispensed
  python tools/mock_vending.py sales --token vend-test-01
"""
import argparse, json, urllib.request

BASE = "http://127.0.0.1/api/v1/vending"


def call(method, path, token, payload=None):
    req = urllib.request.Request(BASE + path, method=method)
    req.add_header("X-Device-Token", token)
    data = None
    if payload is not None:
        req.add_header("Content-Type", "application/json")
        data = json.dumps(payload).encode()
    with urllib.request.urlopen(req, data=data, timeout=15) as r:
        return json.loads(r.read().decode())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["purchase", "confirm", "sales"])
    ap.add_argument("--token", required=True)
    ap.add_argument("--client-id")
    ap.add_argument("--uid")
    ap.add_argument("--client-label", default="")
    ap.add_argument("--product", default="Товар")
    ap.add_argument("--price", default="0")
    ap.add_argument("--sale")
    ap.add_argument("--status", default="dispensed", choices=["dispensed", "failed"])
    a = ap.parse_args()

    if a.cmd == "purchase":
        out = call("POST", "/purchase", a.token, {
            "client_id": a.client_id, "uid": a.uid,
            "client_label": a.client_label,
            "product_name": a.product, "price": a.price})
    elif a.cmd == "confirm":
        out = call("POST", "/confirm", a.token, {"sale_id": a.sale, "status": a.status})
    else:
        out = call("GET", "/sales?limit=20", a.token)
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
