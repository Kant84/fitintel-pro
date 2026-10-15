#scripts\music\pads.py
# -*- coding: utf-8 -*-
"""Очередь сэмплов: забрать pending -> сыграть one-shot -> подтвердить ack.
Дедуп по event_id и по (name, path) за короткое окно — защита от дублей."""
import json
import os
import time
import urllib.request

AUDIO_EXTS = (".mp3", ".flac", ".ogg", ".wav", ".m4a")


class Pads:
    def __init__(self, server, token, lib, deck, dry=False):
        self.server = server.rstrip("/")
        self.token = token
        self.lib = os.path.normpath(lib) if lib else None
        self.deck = deck
        self.dry = dry
        self.fired = set()
        self._recent = {}
        self._recent_ttl = 2.0

    def _get(self, path):
        url = self.server + path + ("&" if "?" in path else "?") + "token=" + self.token
        with urllib.request.urlopen(url, timeout=10) as r:
            return json.load(r)

    def _post(self, path, body):
        req = urllib.request.Request(
            self.server + path,
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.load(r)

    def _resolve(self, raw):
        p = (raw or "").strip().replace("/", os.sep)
        if self.lib and not os.path.isabs(p):
            p = os.path.join(self.lib, p)
        return os.path.normpath(p)

    def poll(self):
        try:
            events = self._get("/music/agent/pads").get("events") or []
        except Exception as e:
            print("PAD | ERR:", e)
            return

        acked = []
        now = time.time()
        self._recent = {k: v for k, v in self._recent.items()
                        if now - v < self._recent_ttl}

        for ev in events:
            eid = ev.get("event_id")
            if not eid or eid in self.fired:
                continue
            self.fired.add(eid)

            path = self._resolve(ev.get("path"))
            name = ev.get("name") or "(без имени)"

            if not path:
                print("PAD | SKIP empty path (event=%s)" % eid[:8])
                acked.append(eid)
                continue
            if os.path.isdir(path):
                print("PAD | SKIP dir: %s" % path)
                acked.append(eid)
                continue
            if not os.path.isfile(path):
                print("PAD | SKIP not found: %s" % path)
                acked.append(eid)
                continue

            key = (name, path)
            if key in self._recent:
                print("PAD | DEDUP %s | %s" % (name, path))
                acked.append(eid)
                continue
            self._recent[key] = now

            print("PAD | %-20s | %s" % (name, path))
            try:
                self.deck.play_oneshot(path, int(ev.get("volume") or 80))
                acked.append(eid)
            except Exception as e:
                print("PAD | PLAY FAIL:", e)

        if acked:
            try:
                self._post("/music/agent/pads/ack", {"event_ids": acked})
            except Exception as e:
                print("PAD | ACK FAIL:", e)

        if len(self.fired) > 5000:
            self.fired = set(list(self.fired)[-1000:])