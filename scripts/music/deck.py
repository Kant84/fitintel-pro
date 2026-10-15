#scripts\music\deck.py
# -*- coding: utf-8 -*-
"""Один дек = один процесс mpv (скрытый, --no-video) со своим IPC-сокетом.
Папка на деке: path → каталог = очередь треков (folder_queue). EQ lavfi."""
import json
import os
import shutil
import socket
import subprocess
import threading
import time

AUDIO_EXTS = (".mp3", ".flac", ".ogg", ".wav", ".m4a")


def _mpv_path():
    """Путь к mpv: PATH → стандартные места установки."""
    p = shutil.which("mpv")
    if p:
        return p
    for cand in (r"C:\mpv\mpv.exe", r"C:\Program Files\MPV Player\mpv.exe",
                 r"C:\Program Files\mpv\mpv.exe"):
        if os.path.exists(cand):
            return cand
    return "mpv"


class Deck:
    def __init__(self, name, ipc, lib, dry_run=False):
        self.name = name
        self.ipc = ipc
        self.lib = lib
        self.dry = dry_run
        self.proc = None
        self.track = None
        self.req = 0
        self.eq = (0, 0, 0)
        self.folder_queue = None
        self.folder_index = 0

    def start(self):
        if self.dry or self.proc:
            return
        self.proc = subprocess.Popen(
            [_mpv_path(), "--no-video", "--idle=yes", "--really-quiet",
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

    def folder_files(self, path):
        """Каталог → отсортированный список аудиофайлов рекурсивно."""
        try:
            if not os.path.isdir(path):
                return None
            found = []
            for root, _dirs, files in os.walk(path):
                for f in sorted(files):
                    if f.lower().endswith(AUDIO_EXTS):
                        found.append(os.path.join(root, f))
            if found:
                return sorted(found)
        except Exception:
            pass
        return None

    def load_paused(self, track):
        self.track = track
        self._loaded_at = time.time()
        target = self.resolve(track)
        q = self.folder_files(target)
        self.folder_queue = q
        self.folder_index = 0
        if q:
            target = q[0]
        if self.dry:
            extra = " (папка: %d файлов)" % len(q) if q else ""
            print("DECK %s | загружен (пауза, vol 0): %s%s" % (self.name,
                                                               track.get("title"), extra))
            return
        self.cmd("loadfile", target, "replace")
        time.sleep(0.2)
        self.cmd("set_property", "pause", True)
        self.cmd("set_property", "volume", 0)

    def load_file_paused(self, path):
        if self.dry:
            print("DECK %s | файл (пауза, vol 0): %s" % (self.name, os.path.basename(path)))
            return
        self.cmd("loadfile", path, "replace")
        time.sleep(0.2)
        self.cmd("set_property", "pause", True)
        self.cmd("set_property", "volume", 0)

    def play(self, volume):
        self._loaded_at = time.time()
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
        cur = self.prop("volume", target)
        if cur is None:
            cur = target
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
        if self.dry:
            print("PAD | ONE-SHOT vol=%s: %s" % (volume, path))
            return
        self.cmd("set_property", "volume", volume)
        self.cmd("loadfile", path, "replace")
        self.cmd("set_property", "pause", False)