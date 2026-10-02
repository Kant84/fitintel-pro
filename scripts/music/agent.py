# -*- coding: utf-8 -*-
"""
FitIntel DJ Agent v4 — пакетная версия.
  Деки A/B (mpv IPC), кроссфейд, авто-микс, мастер-громкость.
  Сэмплер: PAD-канал one-shot по очереди /agent/pads.
  Дакинг: микрофон -> музыка вниз (duck.py).
  Без dj-блока — простой плеер (playlist play/stop).

  --dry-run   только лог, без mpv/звука
  --lib DIR   папка с MP3/FLAC/OGG
  --mic       авто-дакинг (pip install sounddevice)

mpv: https://mpv.io | winget install mpv
"""
import argparse
import json
import sys
import time
import urllib.request

from deck import Deck
from duck import VoiceDucker
from pads import Pads


class Agent:
    def __init__(self, args):
        self.a = args
        is_win = sys.platform.startswith("win")
        if is_win:
            base = r"\\.\pipe\fitintel_"
            ia, ib, ip = base + "deck_a", base + "deck_b", base + "pad"
        else:
            base = "/tmp/fitintel_"
            ia, ib, ip = base + "deck_a.sock", base + "deck_b.sock", base + "pad.sock"
        self.decks = {"A": Deck("A", ia, args.lib, args.dry_run),
                      "B": Deck("B", ib, args.lib, args.dry_run),
                      "PAD": Deck("PAD", ip, args.lib, args.dry_run)}
        self.pads = Pads(args.server, args.token, args.lib,
                         self.decks["PAD"], dry=args.dry_run)
        self.active = "A"
        self.master = 70
        self.applied_sig = None
        self.mixing = False
        self.base_key = None
        self.ducker = None
        self.ducked = False
        self.poll = args.interval

    # --- сеть ---
    def fetch(self, path):
        url = self.a.server.rstrip("/") + path
        url += ("&" if "?" in url else "?") + "token=" + self.a.token
        with urllib.request.urlopen(url, timeout=10) as r:
            return json.load(r)

    # --- основной цикл ---
    def run(self):
        print("FitIntel DJ Agent v4 | dry-run=%s | mic=%s | poll %.1fs | lib=%s"
              % (self.a.dry_run, self.a.mic, self.poll, self.a.lib or "—"))
        if not self.a.dry_run:
            for d in self.decks.values():
                d.start()
        if self.a.mic or self.a.dry_run:
            self.ducker = VoiceDucker(
                on_voice=self._duck_on, on_silence=self._duck_off,
                threshold=self.a.duck_threshold, hold_seconds=self.a.duck_hold,
                dry_run=self.a.dry_run).start()
        while True:
            try:
                st = self.fetch("/music/agent/state")
                dj = st.get("dj") or {}
                if dj.get("deck_a") or dj.get("deck_b"):
                    self.handle_dj(st, dj)
                else:
                    self.handle_simple(st)
                self.pads.poll()
            except Exception as e:
                print("ERR:", e)
            time.sleep(self.poll)

    # --- режим 1: простой плеер ---
    def handle_simple(self, st):
        pl = st.get("playlist")
        key = (st["state"], (pl or {}).get("id"), st["volume"])
        if key == self.base_key:
            return
        self.base_key = key
        main = self.decks[self.active]
        if st["state"] == "playing" and pl and pl.get("tracks"):
            t = pl["tracks"][0]
            print("PLAY | зона %s | %s | %s | vol %s" % (st["name"], pl["name"],
                                                         t.get("title"), st["volume"]))
            main.load_paused(t)
            main.play(st["volume"])
        else:
            print("PAUSE | зона %s" % st["name"])
            main.pause()

    # --- режим 2: DJ-пульт ---
    def handle_dj(self, st, dj):
        cf = float(dj.get("crossfade_seconds") or 8.0)
        want_active = dj.get("active_deck", "A")
        self.master = int(dj.get("master_volume") or 70)

        sig = json.dumps(dj, sort_keys=True, ensure_ascii=False)
        if sig != self.applied_sig:
            self.applied_sig = sig
            self.mixing = False
            da = dj.get("deck_a")
            db = dj.get("deck_b")
            if da and (self.decks["A"].track or {}).get("path") != da.get("path"):
                self.decks["A"].load_paused(da)
            if db and (self.decks["B"].track or {}).get("path") != db.get("path"):
                self.decks["B"].load_paused(db)
            if want_active in ("A", "B"):
                self.switch_to(want_active, cf, immediate=True)
            print("DJ | применено: активный дек %s | мастер %s | кроссфейд %.1fs"
                  % (want_active, self.master, cf))

        act = self.decks[self.active]
        if act.eof() and not self.mixing:
            print("DJ | трек на деке %s завершён, тишина (ждём команду пульта)" % self.active)

        rem = act.remaining()
        idle_name = "B" if self.active == "A" else "A"
        idle = self.decks[idle_name]
        if (not self.mixing and rem is not None
                and 0 < rem <= cf + 1.0 and idle.track):
            self.auto_mix(idle_name, cf)

    def switch_to(self, name, cf, immediate=False):
        idle = self.decks[name]
        old = self.decks[self.active]
        if immediate:
            old.pause()
            idle.play(self.master)
        else:
            idle.play(0)
            idle.fade_to(self.master, cf)
            old.fade_to(0, cf)
            time.sleep(cf + 0.3)
            old.pause()
        self.active = name
        print("DJ | эфир: дек %s | %s" % (name, (idle.track or {}).get("title")))

    def auto_mix(self, idle_name, cf):
        self.mixing = True
        idle = self.decks[idle_name]
        nxt = self.next_track(idle.track)
        if nxt and nxt.get("path") != (idle.track or {}).get("path"):
            idle.load_paused(nxt)
        print("DJ | AUTO-MIX: дек %s -> %s | след.: %s | фейд %.1fs"
              % (self.active, idle_name, (nxt or {}).get("title"), cf))
        self.switch_to(idle_name, cf, immediate=False)
        old = self.decks[self.active]
        old.fade_to(0, 0.5)
        self.mixing = False

    def next_track(self, current):
        try:
            st = self.fetch("/music/agent/state")
            pl = st.get("playlist")
            if pl and pl.get("tracks"):
                tracks = pl["tracks"]
                if current:
                    for i, t in enumerate(tracks):
                        if t.get("path") == current.get("path"):
                            return tracks[(i + 1) % len(tracks)]
                return tracks[0]
        except Exception:
            pass
        return current

    # --- дакинг ---
    def _duck_on(self):
        if self.ducked:
            return
        self.ducked = True
        target = int(self.master * self.a.duck_factor)
        print("DUCK | ГОЛОС -> музыка на %s (фактор %s)" % (target, self.a.duck_factor))
        for name in ("A", "B"):
            d = self.decks[name]
            if d.track:
                d.fade_to(target, 0.3)

    def _duck_off(self):
        if not self.ducked:
            return
        self.ducked = False
        print("DUCK | тишина -> музыка на %s" % self.master)
        for name in ("A", "B"):
            d = self.decks[name]
            if d.track:
                d.fade_to(self.master, 1.0)


def main():
    ap = argparse.ArgumentParser(description="FitIntel DJ Agent v4")
    ap.add_argument("--server", required=True, help="http://192.168.101.182/api/v1")
    ap.add_argument("--token", required=True)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--lib", default=None, help="папка с MP3/FLAC/OGG")
    ap.add_argument("--interval", type=float, default=3.0)
    ap.add_argument("--mic", action="store_true", help="включить авто-дакинг микрофона")
    ap.add_argument("--duck-threshold", type=float, default=0.08, help="RMS-порог голоса")
    ap.add_argument("--duck-factor", type=float, default=0.2,
                    help="громкость музыки во время речи (0-1)")
    ap.add_argument("--duck-hold", type=float, default=2.0,
                    help="сек тишины до возврата громкости")
    args = ap.parse_args()
    try:
        Agent(args).run()
    except KeyboardInterrupt:
        print("остановлено")


if __name__ == "__main__":
    main()