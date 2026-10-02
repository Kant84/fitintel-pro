# -*- coding: utf-8 -*-
"""Один дек = один процесс mpv со своим IPC-сокетом (unix-socket / named pipe).
EQ: бас/середина/верха через lavfi equalizer, пересчёт на лету без перерыва."""
import json
import os
import socket
import subprocess
import threading
import time


class Deck:
    def __init__(self, name, ipc, lib, dry_run=False):
        self.name = name
        self.ipc = ipc
        self.lib = lib
        self.dry = dry_run
        self.proc = None
        self.track = None
        self.req = 0
        self.eq = (0, 0, 0)         # (bass, mid, treble) в дБ

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

    def _conn(self):
        if self.ipc.startswith("\\\\.\\pipe\\"):
            return open(self.ipc, "r+b", buffering=0)
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(5)
        s.connect(self.ipc)
        return s.makefile("rwb")

    def cmd(self, *args):
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

    def resolve(self, track):
        p = track.get("path", "")
        if self.lib and not os.path.isabs(p):
            p = os.path.join(self.lib, p)
        return p

    def load_paused(self, track):
        self.track = track
        self._loaded_at = time.time()      # dry-run: имитация длительности трека
        if self.dry:
            print("DECK %s | загружен (пауза, vol 0): %s" % (self.name, track.get("title")))
            return
        self.cmd("loadfile", self.resolve(track), "replace")
        time.sleep(0.2)
        self.cmd("set_property", "pause", True)
        self.cmd("set_property", "volume", 0)

    def play(self, volume):
        self._loaded_at = time.time()      # отсчёт «длительности трека» с момента выхода в эфир
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

    def set_eq(self, bass=0, mid=0, treble=0):
        """Эквалайзер дека: bass/mid/treble в дБ (-12..+12), lavfi equalizer."""
        bass, mid, treble = int(bass), int(mid), int(treble)
        self.eq = (bass, mid, treble)
        if self.dry:
            print("DECK %s | EQ bass=%+d mid=%+d treble=%+d" % (self.name, bass, mid, treble))
            return
        try:
            if bass == 0 and mid == 0 and treble == 0:
                self.cmd("set_property", "af", "")
            else:
                f = ("equalizer=f=80:width_type=h:w=160:g=%d,"
                     "equalizer=f=1200:width_type=h:w=1000:g=%d,"
                     "equalizer=f=6500:width_type=h:w=4500:g=%d" % (bass, mid, treble))
                self.cmd("set_property", "af", f)
        except Exception as e:
            print("DECK %s | EQ FAIL: %s" % (self.name, e))

    def remaining(self):
        if self.dry:
            # dry-run: трек «длится» 45 секунд с момента play() — для проверки AUTO-MIX
            if not self.track:
                return None
            start = getattr(self, "_loaded_at", None) or time.time()
            return max(0.0, 45.0 - (time.time() - start))
        dur = self.prop("duration")
        pos = self.prop("time-pos")
        if dur and pos is not None:
            return float(dur) - float(pos)
        return None

    def eof(self):
        return bool(self.prop("eof-reached", False))

    def play_oneshot(self, path, volume):
        """Сэмплер: проиграть файл один раз, не трогая эфирные деки."""
        if self.dry:
            print("PAD | ONE-SHOT vol=%s: %s" % (volume, path))
            return
        self.cmd("set_property", "volume", volume)
        self.cmd("loadfile", path, "replace")
        self.cmd("set_property", "pause", False)