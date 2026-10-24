#scripts\music\deck.py
# -*- coding: utf-8 -*-
"""Один дек = один процесс mpv (скрытый) со своим IPC-каналом.
Папка на деке: path -> каталог = очередь треков (folder_queue).
EQ через lavfi bridge (mpv v0.41: 'af set <chain>' / 'af clr ""')."""
import json
import os
import shutil
import socket
import subprocess
import threading
import time

AUDIO_EXTS = (".mp3", ".flac", ".ogg", ".wav", ".m4a")


def _mpv_path():
    import sys as _sys

    # 0) явный рабочий путь (WinError 5 при резолве через шимы/PATH в GUI-процессе)
    for cand in (r"C:\mpv\mpv.exe", r"C:\Program Files\MPV Player\mpv.exe"):
        if os.path.exists(cand):
            return cand

    # 1) PyInstaller bundle (--onefile или --onedir)
    if getattr(_sys, "frozen", False) or hasattr(_sys, "_MEIPASS"):
        bundle = getattr(_sys, "_MEIPASS", None) or os.path.dirname(_sys.executable)
        for rel in ("mpv/mpv.exe", "mpv/mpv.com",
                    "_internal/mpv/mpv.exe", "_internal/mpv/mpv.com"):
            cand = os.path.join(bundle, rel)
            if os.path.exists(cand):
                return cand

    # 2) рядом с приложением (корень репо при работе из исходников)
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.abspath(os.path.join(here, "..", ".."))
    for rel in ("mpv/mpv.exe", "mpv/mpv.com"):
        cand = os.path.join(root, rel)
        if os.path.exists(cand):
            return cand

    # 3) рядом с exe (--onedir) — mpv лежит прямо в папке сборки
    if getattr(_sys, "frozen", False):
        base = os.path.dirname(_sys.executable)
        for rel in ("mpv/mpv.exe", "mpv/mpv.com",
                    "_internal/mpv/mpv.exe", "_internal/mpv/mpv.com"):
            cand = os.path.join(base, rel)
            if os.path.exists(cand):
                return cand

    # 4) системный PATH
    p = shutil.which("mpv")
    if p:
        return p

    # 5) старые места
    for cand in (r"C:\mpv\mpv.exe",
                 r"C:\Program Files\MPV Player\mpv.exe",
                 r"C:\Program Files\mpv\mpv.exe"):
        if os.path.exists(cand):
            return cand

    return "mpv"

def _norm(path):
    if not path:
        return path
    return os.path.normpath(path)


class Deck:
    def __init__(self, name, ipc, lib, dry_run=False):
        self.name = name
        self.ipc = ipc
        self.lib = _norm(lib) if lib else None
        self.dry = dry_run
        self.proc = None
        self.track = None
        self.req = 0
        self.eq = (0, 0, 0)
        self.folder_queue = None
        self.folder_index = 0
        self._loaded_at = time.time()
        self._eof_seen = False
        self._last_remaining = None
        self._eq_broken = False
        self._lock = threading.Lock()

    def start(self):
        if self.dry or self.proc:
            return
        try:
            self.proc = subprocess.Popen(
                [_mpv_path(), "--no-video", "--idle=yes", "--really-quiet",
                 "--force-window=no", "--ontop=no", "--no-terminal",
                 "--volume=0", "--input-ipc-server=%s" % self.ipc],
                creationflags=(subprocess.CREATE_NO_WINDOW
                               if os.name == "nt" else 0))
        except Exception as e:
            raise RuntimeError("mpv не стартовал: %s" % e)
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
        """ФИКС: на Windows убиваем всё дерево (mpv.exe + дочерние)."""
        if not self.proc:
            return
        try:
            if os.name == "nt":
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(self.proc.pid)],
                    capture_output=True, timeout=5)
            else:
                self.proc.terminate()
        except Exception as e:
            print("DECK %s | stop_proc ERR: %s" % (self.name, e))
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
        with self._lock:
            self.req += 1
            msg = (json.dumps({"command": list(args), "request_id": self.req})
                   .encode() + b"\n")
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
                            raise RuntimeError("mpv %s: %s"
                                               % (args, d.get("error")))
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
        p = _norm(track.get("path", ""))
        if self.lib and not os.path.isabs(p):
            p = os.path.join(self.lib, p)
        return _norm(p)

    def folder_files(self, path):
        try:
            path = _norm(path)
            if not os.path.isdir(path):
                return None
            found = []
            for root, _dirs, files in os.walk(path):
                for f in sorted(files):
                    if f.lower().endswith(AUDIO_EXTS):
                        found.append(os.path.join(root, f))
            return sorted(found) if found else None
        except Exception as e:
            print("DECK %s | folder_files ERR: %s" % (self.name, e))
            return None

    def _reset_eof(self):
        try:
            self.cmd("set_property", "eof-reached", False)
        except Exception:
            pass

    def load_paused(self, track):
        self.track = track
        self._loaded_at = time.time()
        self._eof_seen = False
        self._last_remaining = None
        target = self.resolve(track)
        q = self.folder_files(target)
        self.folder_queue = q
        self.folder_index = 0
        if q:
            target = q[0]
        if self.dry:
            extra = " (папка: %d файлов)" % len(q) if q else ""
            print("DECK %s | загружен (пауза): %s%s"
                  % (self.name, track.get("title"), extra))
            return
        self.cmd("loadfile", target, "replace")
        time.sleep(0.2)
        self.cmd("set_property", "pause", True)
        self.cmd("set_property", "volume", 0)
        self._reset_eof()
        self._reapply_eq()

    def load_file_paused(self, path):
        self._eof_seen = False
        self._last_remaining = None
        self.track = {"title": os.path.basename(path), "path": path}
        if self.dry:
            print("DECK %s | файл (пауза): %s"
                  % (self.name, os.path.basename(path)))
            return
        self.cmd("loadfile", _norm(path), "replace")
        time.sleep(0.2)
        self.cmd("set_property", "pause", True)
        self.cmd("set_property", "volume", 0)
        self._reset_eof()
        self._reapply_eq()

    def play(self, volume):
        self._loaded_at = time.time()
        self._eof_seen = False
        self._last_remaining = None
        if self.dry:
            print("DECK %s | PLAY vol=%s: %s"
                  % (self.name, volume, (self.track or {}).get("title")))
            return
        self.cmd("set_property", "volume", volume)
        self.cmd("set_property", "pause", False)
        self._reapply_eq()

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
        self.eq = (int(bass), int(mid), int(treble))
        if self.dry:
            print("DECK %s | EQ bass=%+d mid=%+d treble=%+d"
                  % (self.name, self.eq[0], self.eq[1], self.eq[2]))
            return
        self._reapply_eq()

    def _reapply_eq(self):
        if self.dry or self._eq_broken:
            return
        bass, mid, treble = self.eq
        try:
            if bass == 0 and mid == 0 and treble == 0:
                # mpv v0.41: 'af clr ""' — сброс
                try:
                    self.cmd("af", "clr", "")
                except Exception:
                    self.cmd("set_property", "af", "")
            else:
                chain = ("equalizer=f=80:width_type=h:w=160:g=%d,"
                         "equalizer=f=1200:width_type=h:w=1000:g=%d,"
                         "equalizer=f=6500:width_type=h:w=4500:g=%d"
                         % (bass, mid, treble))
                try:
                    self.cmd("af", "set", chain)
                except Exception:
                    self.cmd("set_property", "af", chain)
        except Exception as e:
            err = str(e)
            if "invalid parameter" in err:
                print("DECK %s | EQ: этот mpv не принимает af — EQ выключен"
                      % self.name)
                self._eq_broken = True
            else:
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
            rem = float(dur) - float(pos)
            self._last_remaining = rem
            return rem
        return self._last_remaining

    def eof(self):
        if self.dry:
            return False
        if self._eof_seen:
            return True
        try:
            if bool(self.prop("eof-reached", False)):
                self._eof_seen = True
                return True
        except Exception:
            pass
        try:
            if bool(self.prop("idle-active", False)) and self.track:
                self._eof_seen = True
                return True
        except Exception:
            pass
        if (self._last_remaining is not None and self._last_remaining < 1.5
                and self.prop("duration") is None):
            self._eof_seen = True
            return True
        return False

    def play_oneshot(self, path, volume):
        if self.dry:
            print("PAD | ONE-SHOT vol=%s: %s" % (volume, path))
            return
        path = _norm(path)
        if not path or os.path.isdir(path):
            print("PAD | SKIP: путь не файл (%s)" % path)
            return
        if not os.path.isfile(path):
            print("PAD | SKIP: файл не найден (%s)" % path)
            return
        # ФИКС: один IPC-вызов вместо трёх. Опции loadfile применяются атомарно.
        try:
            self.cmd("loadfile", path, "replace",
                     "volume=%d" % int(volume), "pause=no")
        except Exception:
            # fallback: старый способ, если mpv не поддерживает опции
            self.cmd("set_property", "volume", int(volume))
            self.cmd("loadfile", path, "replace")
            self.cmd("set_property", "pause", False)