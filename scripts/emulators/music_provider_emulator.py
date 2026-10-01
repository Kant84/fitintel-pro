# -*- coding: utf-8 -*-
"""
Эмулятор музыкального бокса провайдера.
Принимает пуш-команды от сервера FitIntel (как реальный плеер/усилитель провайдера).
Контракт: POST /cmd {"zone": ..., "action": ..., "payload": {...}}
Позже заменяется реальной коробкой — формат команд подгоним под неё.
"""
import argparse
import json
from http.server import BaseHTTPRequestHandler, HTTPServer


class H(BaseHTTPRequestHandler):
    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(n) or b"{}")
        if self.path == "/cmd":
            zone = body.get("zone")
            action = body.get("action")
            pl = body.get("payload") or {}
            if action == "play":
                print("BOX | zona %-12s | PLAY %s" % (zone, pl.get("playlist_id")), flush=True)
            elif action == "pause":
                print("BOX | zona %-12s | PAUSE" % zone, flush=True)
            elif action == "volume":
                print("BOX | zona %-12s | VOLUME %s" % (zone, pl.get("level")), flush=True)
            elif action == "energize":
                print("BOX | zona %-12s | ENERGIZE !" % zone, flush=True)
            elif action in ("dj_load", "dj_crossfade", "dj_master"):
                print("BOX | zona %-12s | %s %s" % (zone, action.upper(), pl), flush=True)
            else:
                print("BOX | ? ", body, flush=True)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"ok":true}')
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=9101)
    a = ap.parse_args()
    print("Emulyator boksa provaydera: 0.0.0.0:%d (POST /cmd)" % a.port, flush=True)
    HTTPServer(("0.0.0.0", a.port), H).serve_forever()