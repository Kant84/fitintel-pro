# -*- coding: utf-8 -*-
"""
FitIntel DJ Agent v2 — локальный плеер музыкальной зоны.
  Два дека (mpv + JSON IPC): Deck A / Deck B, кроссфейд, авто-микс, мастер-громкость.
  Режим DJ включается, когда сервер отдаёт dj.deck_a / dj.deck_b.
  Без dj-блока работает как простой плеер v1 (playlist play/stop).

  --dry-run      только лог, без mpv и звука (проверка логики)
  --lib DIR      папка с MP3/FLAC/OGG (пути треков резолвятся от неё)
  --interval N   опрос сервера, сек (по умолчанию 3)

mpv (движок): https://mpv.io  |  winget install mpv
IPC: Linux — unix-сокет; Windows — named pipe \\.\pipe\fitintel_deck_*
"""
import argparse
import json
import os
import socket
import subprocess
import sys
import threading
import time
import urllib.request


# --------------------------------------------------------------------------- Deck
class Deck:
    """Один дек = один процесс mpv со своим IPC-сокетом."""

    def __init__(self, name, ipc, lib, dry_run=False):
        self.name = name            # "A" / "B"
        self.ipc = ipc
        self.lib = lib
        self.dry = dry_run
        self.proc = None
        self.track = None           # {"title","path"} — что загружено
        self.req = 0

    # --- процесс ---
    def start(self):
        if self.dry or self.proc:
            return
        self.proc = subprocess.Popen(
            ["mpv", "--no-video", "--idle=yes", "--really-quiet",
             "--volume=0", "--input-ipc-server=%s" % self.ipc])
        self._wait_ipc(10)

    def _wait_ipc(self, timeout):
        t0 = time.time()
        while time.time() - t0 < timeout:
            try:
                self.cmd("get_property", "volume")
                return
            except Exception:
                time.sleep(0.3)
        raise RuntimeError("mpv не ответил по IPC %s" % self.ipc)

    def stop_proc(self):
        if self.proc:
            try:
                self.proc.terminate()
            except Exception:
                pass
            self.proc = None

    # --- IPC ---
    def _conn(self):
        if self.ipc.startswith("\\\\.\\pipe\\"):
            return open(self.ipc, "r+b", buffering=0)
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(5)
        s.connect(self.ipc)
        return s.makefile("rwb")

    def cmd(self, *args):
        """Отправить команду mpv, дождаться ответа по request_id."""
        if self.dry:
            return {}
        self.req += 1
        msg = json.dumps({"command": list(args), "request_id": self.req}).encode() + b"\n"
        f = self._conn()
        try:
            f.write(msg)
            f.flush()
            while True:
                line = f.readline()
                if not line:
                    break
                try:
                    d = json.loads(line)
                except Exception:
                    continue
                if d.get("request_id") == self.req:
                    if d.get("error") not in ("success", None):
                        raise RuntimeError("mpv %s: %s" % (args, d.get("error")))
                    return d
        finally:
            try:
                f.close()
            except Exception:
                pass
        return {}

    def prop(self, name, default=None):
        try:
            return self.cmd("get_property", name).get("data", default)
        except Exception:
            return default

    # --- музыкальные операции ---
    def resolve(self, track):
        p = track.get("path", "")
        if self.lib and not os.path.isabs(p):
            p = os.path.join(self.lib, p)
        return p

    def load_paused(self, track):
        """Загрузить трек на дек и поставить на паузу с нулевой громкостью."""
        self.track = track
        if self.dry:
            print("DECK %s | загружен (пауза, vol 0): %s" % (self.name, track.get("title")))
            return
        self.cmd("loadfile", self.resolve(track), "replace")
        time.sleep(0.2)
        self.cmd("set_property", "pause", True)
        self.cmd("set_property", "volume", 0)

    def play(self, volume):
        self.track = self.track  # unchanged
        if self.dry:
            print("DECK %s | PLAY vol=%s: %s" % (self.name, volume,
                                                 (self.track or {}).get("title")))
            return
        self.cmd("set_property", "volume", volume)
        self.cmd("set_property", "pause", False)

    def pause(self):
        if self.dry:
            print("DECK %s | PAUSE" % self.name)
            return
        self.cmd("set_property", "pause", True)

    def fade_to(self, target, seconds):
        """Плавно изменить громкость (в фоновом потоке)."""
        if self.dry:
            print("DECK %s | FADE -> %s за %.1fs" % (self.name, target, seconds))
            return
        cur = self.prop("volume", target) or target
        steps = max(1, int(seconds / 0.25))
        delta = (target - cur) / steps

        def _ramp():
            v = cur
            for _ in range(steps):
                v += delta
                try:
                    self.cmd("set_property", "volume", max(0, min(130, v)))
                except Exception:
                    return
                time.sleep(0.25)
            try:
                self.cmd("set_property", "volume", target)
            except Exception:
                pass

        threading.Thread(target=_ramp, daemon=True).start()

    def remaining(self):
        """Секунд до конца трека (None если неизвестно)."""
        dur = self.prop("duration")
        pos = self.prop("time-pos")
        if dur and pos is not None:
            return float(dur) - float(pos)
        return None

    def eof(self):
        return bool(self.prop("eof-reached", False))


# --------------------------------------------------------------------------- Agent
class Agent:
    def __init__(self, args):
        self.a = args
        is_win = sys.platform.startswith("win")
        if is_win:
            base = r"\\.\pipe\fitintel_deck_"
            ia, ib = base + "a", base + "b"
        else:
            base = "/tmp/fitintel_deck_"
            ia, ib = base + "a.sock", base + "b.sock"
        self.decks = {"A": Deck("A", ia, args.lib, args.dry_run),
                      "B": Deck("B", ib, args.lib, args.dry_run)}
        self.active = "A"
        self.master = 70
        self.applied_sig = None     # сигнатура dj-состояния, уже применённого сервера
        self.mixing = False
        self.base_key = None        # ключ фонового режима (state+playlist+volume)
        self.poll = args.interval

    # --- сеть ---
    def fetch(self):
        url = self.a.server.rstrip("/") + "/music/agent/state?token=" + self.a.token
        with urllib.request.urlopen(url, timeout=10) as r:
            return json.load(r)

    # --- основной цикл ---
    def run(self):
        print("FitIntel DJ Agent v2 | dry-run=%s | poll %.1fs | lib=%s"
              % (self.a.dry_run, self.poll, self.a.lib or "—"))
        if not self.a.dry_run:
            self.decks["A"].start()
            self.decks["B"].start()
        while True:
            try:
                st = self.fetch()
                dj = st.get("dj") or {}
                if dj.get("deck_a") or dj.get("deck_b"):
                    self.handle_dj(st, dj)
                else:
                    self.handle_simple(st)
            except Exception as e:
                print("ERR:", e)
            time.sleep(self.poll)

    # --- режим 1: простой плеер (как v1) ---
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

        # Применяем серверное состояние только если оно изменилось
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

        # Контроль активного дека: если трек закончился — рестарт (подстраховка)
        act = self.decks[self.active]
        if act.eof() and not self.mixing:
            print("DJ | трек на деке %s завершён, тишина (ждём команду пульта)" % self.active)
            time.sleep(self.poll)

        # Авто-микс: приближается конец трека -> сведение на свободный дек
        rem = act.remaining()
        idle_name = "B" if self.active == "A" else "A"
        idle = self.decks[idle_name]
        if (not self.mixing and rem is not None
                and 0 < rem <= cf + 1.0 and idle.track):
            self.auto_mix(idle_name, cf)

    def switch_to(self, name, cf, immediate=False):
        """Свести эфир на дек name. immediate=True — без фейда (первая подача)."""
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
        """Авто-микс: сводим на свободный дек; следующий трек — из текущего
        плейлиста сервера (или повтор текущего, если плейлиста нет)."""
        self.mixing = True
        idle = self.decks[idle_name]
        nxt = self.next_track(idle.track)
        if nxt and nxt.get("path") != (idle.track or {}).get("path"):
            idle.load_paused(nxt)
        print("DJ | AUTO-MIX: дек %s -> %s | след.: %s | фейд %.1fs"
              % (self.active, idle_name, (nxt or {}).get("title"), cf))
        self.switch_to(idle_name, cf, immediate=False)
        # освободившийся (старый) дек готовим следующим: грузим туда next+1 на паузу
        old = self.decks[self.active]
        old.fade_to(0, 0.5)
        self.mixing = False
        _ = old  # следующий трек подгрузит сервер или повторный auto_mix

    def next_track(self, current):
        """Следующий трек: из последнего известного плейлиста, иначе повтор."""
        try:
            st = self.fetch()
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


def main():
    ap = argparse.ArgumentParser(description="FitIntel DJ Agent v2")
    ap.add_argument("--server", required=True, help="http://192.168.101.182/api/v1")
    ap.add_argument("--token", required=True)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--lib", default=None, help="папка с MP3/FLAC/OGG")
    ap.add_argument("--interval", type=float, default=3.0)
    args = ap.parse_args()
    try:
        Agent(args).run()
    except KeyboardInterrupt:
        print("остановлено")


if __name__ == "__main__":
    main()