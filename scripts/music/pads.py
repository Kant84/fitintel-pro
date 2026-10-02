# -*- coding: utf-8 -*-
"""Очередь сэмплов: забрать pending -> сыграть one-shot -> подтвердить ack."""
import json
import os
import urllib.request


class Pads:
    def __init__(self, server, token, lib, deck, dry=False):
        self.server = server.rstrip("/")
        self.token = token
        self.lib = lib
        self.deck = deck
        self.dry = dry
        self.fired = set()          # event_id, уже сыгранные (защита от повторов)

    def _get(self, path):
        url = self.server + path + ("&" if "?" in path else "?") + "token=" + self.token
        with urllib.request.urlopen(url, timeout=10) as r:
            return json.load(r)

    def _post(self, path, body):
        req = urllib.request.Request(self.server + path,
                                     data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.load(r)

    def poll(self):
        try:
            events = self._get("/music/agent/pads").get("events") or []
        except Exception as e:
            print("PAD | ERR:", e)
            return
        acked = []
        for ev in events:
            eid = ev.get("event_id")
            if not eid or eid in self.fired:
                continue
            self.fired.add(eid)
            path = ev.get("path", "")
            if self.lib and not os.path.isabs(path):
                path = os.path.join(self.lib, path)
            print("PAD | %-20s | %s" % (ev.get("name"), path))
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