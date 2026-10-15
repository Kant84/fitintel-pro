#scripts\music\agent.py
# -*- coding: utf-8 -*-
"""FitIntel DJ Agent v4.4: деки A/B (mpv IPC, скрытые), кроссфейд, авто-микс
(папка по кругу / плейлист), мастер, EQ, сэмплер, дакинг. Уникальные IPC-каналы
на запуск, при выходе mpv завершаются. Лог UTF-8.

v4.4:
- уважает state='stopped' — паузит оба деки;
- не перезапускает трек при смене мастера/кроссфейда (сравнение по норм.пути);
- switch_to при active==name не трогает играющий дек;
- switch_to при кроссфейде old — строго противоположный дек.
"""
import argparse
import atexit
import json
import os
import sys
import threading
import time
import urllib.request

from deck import Deck
from duck import VoiceDucker
from pads import Pads


class Agent:
    def __init__(self, args):
        self.a = args
        is_win = sys.platform.startswith("win")
        import uuid as _uuid
        suf = _uuid.uuid4().hex[:8]
        if is_win:
            base = r"\\.\pipe\fitintel_%s_" % suf
            ia, ib, ip = base + "deck_a", base + "deck_b", base + "pad"
        else:
            base = "/tmp/fitintel_%s_" % suf
            ia, ib, ip = base + "deck_a.sock", base + "deck_b.sock", base + "pad.sock"
        self.decks = {"A": Deck("A", ia, args.lib, args.dry_run),
                      "B": Deck("B", ib, args.lib, args.dry_run),
                      "PAD": Deck("PAD", ip, args.lib, args.dry_run)}
        self.pads = Pads(args.server, args.token, args.lib,
                         self.decks["PAD"], dry=args.dry_run)
        self.active = "A"
        self.master = 70
        self.applied_sig = None
        self._last_dj = None
        self.mixing = False
        self.base_key = None
        self.ducker = None
        self.ducked = False
        self.poll = args.interval
        # страховка: при выходе агента (в т.ч. по terminate) прибить mpv
        atexit.register(self._kill_all)

    # ---------- сеть ----------
    def fetch(self, path):
        url = self.a.server.rstrip("/") + path
        url += ("&" if "?" in url else "?") + "token=" + self.a.token
        with urllib.request.urlopen(url, timeout=10) as r:
            return json.load(r)

    # ---------- служебное ----------
    def _kill_all(self):
        for d in self.decks.values():
            try:
                d.stop_proc()
            except Exception:
                pass

    def _track_key(self, t):
        """Нормализованный ключ трека для сравнения (норм.путь + normcase)."""
        if not t:
            return None
        p = t.get("path") or ""
        if not p:
            return None
        if self.a.lib and not os.path.isabs(p):
            p = os.path.join(self.a.lib, p)
        return os.path.normcase(os.path.normpath(p))

    # ---------- цикл ----------
    def run(self):
        print("FitIntel DJ Agent v4.4 | dry-run=%s | mic=%s | poll %.1fs | lib=%s"
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
                if self.a.debug:
                    rem = self.decks[self.active].remaining()
                    print("DBG | state=%s active=%s master=%s mixing=%s rem=%.1f"
                          % (st.get("state"), self.active, self.master,
                             self.mixing, rem if rem is not None else -1))
                dj = st.get("dj") or {}
                if dj.get("deck_a") or dj.get("deck_b"):
                    self.handle_dj(st, dj)
                else:
                    self.handle_simple(st)
                self.pads.poll()
            except Exception as e:
                print("ERR:", e)
            time.sleep(self.poll)

    def stop(self):
        if self.ducker:
            try:
                self.ducker.stop()
            except Exception:
                pass
        self._kill_all()

    # ---------- простой режим (плейлист без DJ) ----------
    def handle_simple(self, st):
        # ФИКС: если зона остановлена — паузим ОБА деку и сбрасываем кэш
        if st.get("state") != "playing":
            for d in self.decks.values():
                if d.track:
                    try:
                        d.pause()
                    except Exception:
                        pass
            self.base_key = None
            self.applied_sig = None
            self._last_dj = None
            return

        pl = st.get("playlist")
        key = (st["state"], (pl or {}).get("id"), st["volume"])
        if key == self.base_key:
            return
        self.base_key = key
        main = self.decks[self.active]
        if pl and pl.get("tracks"):
            t = pl["tracks"][0]
            print("PLAY | зона %s | %s | %s | vol %s"
                  % (st["name"], pl["name"], t.get("title"), st["volume"]))
            main.load_paused(t)
            main.play(st["volume"])
        else:
            print("PAUSE | зона %s" % st["name"])
            main.pause()

    # ---------- DJ-режим ----------
    def handle_dj(self, st, dj):
        if self.mixing:
            return

        # ФИКС: state='stopped' — паузим всё, сбрасываем кэш, выходим
        if st.get("state") != "playing":
            for d in self.decks.values():
                if d.track:
                    try:
                        d.pause()
                    except Exception:
                        pass
            self.applied_sig = None
            self._last_dj = None
            return

        cf = float(dj.get("crossfade_seconds") or 8.0)
        want_active = dj.get("active_deck", "A")
        self.master = int(dj.get("master_volume") or 70)

        sig = json.dumps(dj, sort_keys=True, ensure_ascii=False)
        if sig != self.applied_sig:
            prev = self._last_dj or {}
            active_same = prev.get("active_deck") == dj.get("active_deck")
            self.applied_sig = sig
            self._last_dj = dj

            da = dj.get("deck_a")
            db = dj.get("deck_b")

            # ФИКС: сравнение по нормализованному пути — не перезагружаем трек
            # при простой смене мастера/кроссфейда
            if da and self._track_key(self.decks["A"].track) != self._track_key(da):
                self.decks["A"].load_paused(da)
            if db and self._track_key(self.decks["B"].track) != self._track_key(db):
                self.decks["B"].load_paused(db)

            # EQ применяем всегда — дешево и безопасно
            eq = dj.get("eq") or {}
            for nm in ("A", "B"):
                e = eq.get(nm) or {}
                self.decks[nm].set_eq(e.get("bass", 0), e.get("mid", 0),
                                      e.get("treble", 0))

            # ФИКС: switch_to вызываем только если активный дек реально сменился
            if want_active in ("A", "B") and not active_same:
                self.switch_to(want_active, cf, immediate=True)

            # ФИКС: при смене мастера — плавно применить новую громкость
            if active_same and want_active == self.active:
                try:
                    self.decks[self.active].cmd("set_property", "volume",
                                                self.master)
                except Exception:
                    pass

            print("DJ | применено: активный дек %s | мастер %s | кроссфейд %.1fs"
                  % (want_active, self.master, cf))

        act = self.decks[self.active]
        idle_name = "B" if self.active == "A" else "A"
        idle = self.decks[idle_name]

        # Пересобрать очередь, если активный дек — папка, а очередь пуста
        if act.track and not act.folder_queue:
            q = act.folder_files(act.resolve(act.track))
            if q:
                act.folder_queue = q
                act.folder_index = 0
                print("DJ | очередь пересобрана для деку %s: %d файлов"
                      % (self.active, len(q)))

        rem = act.remaining()
        can_mix = bool(idle.track or idle.folder_queue or act.folder_queue)
        need_mix = ((rem is not None and rem <= cf + 1.0) or act.eof())
        if not self.mixing and can_mix and need_mix:
            self.auto_mix(idle_name, cf)
        elif act.eof() and not self.mixing and not can_mix:
            print("DJ | трек завершён, сводить некуда — повтор")
            try:
                act.cmd("seek", 0, "absolute")
                act.play(self.master)
            except Exception as e:
                print("DJ | repeat ERR:", e)

    # ---------- переключение деков ----------
    def switch_to(self, name, cf, immediate=False):
        if name not in ("A", "B"):
            return

        # ФИКС: если уже эфирит этот дек — не трогаем вообще
        if self.active == name:
            if immediate:
                self.mixing = False
            return

        # old — строго противоположный дек
        other = "B" if name == "A" else "A"
        idle = self.decks[name]
        old = self.decks[other]

        if immediate:
            # Просто переключаем: старый на паузу, новый играть с текущей позиции
            try:
                old.pause()
            except Exception as e:
                print("DJ | pause old ERR:", e)
            self.active = name
            try:
                idle.play(self.master)
            except Exception as e:
                print("DJ | play idle ERR:", e)
            print("DJ | эфир: дек %s | %s"
                  % (name, (idle.track or {}).get("title")))
            self.mixing = False
            return

        # Кроссфейд
        if self.mixing:
            return
        self.mixing = True
        self.active = name
        print("DJ | эфир (кроссфейд): дек %s | %s"
              % (name, (idle.track or {}).get("title")))

        def _fade():
            try:
                idle.play(0)
                idle.fade_to(self.master, cf)
                old.fade_to(0, cf)
                time.sleep(cf + 0.3)
                old.pause()
            except Exception as e:
                print("DJ | FADE ERR:", e)
            finally:
                self.mixing = False

        threading.Thread(target=_fade, daemon=True).start()

    # ---------- авто-микс ----------
    def auto_mix(self, idle_name, cf):
        if self.mixing:
            return
        idle = self.decks[idle_name]
        act = self.decks[self.active]
        q = act.folder_queue
        if q:
            act.folder_index = (act.folder_index + 1) % len(q)
            f = q[act.folder_index]
            nxt_title = os.path.basename(f)
            print("DJ | AUTO-MIX (папка): дек %s -> %s | след.: %s | фейд %.1fs"
                  % (self.active, idle_name, nxt_title, cf))
            idle.track = {"title": nxt_title, "path": f}
            idle.folder_queue = q
            idle.folder_index = act.folder_index
            idle._loaded_at = time.time()
            idle.load_file_paused(f)
            self.switch_to(idle_name, cf, immediate=False)
            return
        nxt = self.next_track(idle.track)
        if nxt and self._track_key(nxt) != self._track_key(idle.track):
            idle.load_paused(nxt)
        print("DJ | AUTO-MIX: дек %s -> %s | след.: %s | фейд %.1fs"
              % (self.active, idle_name, (nxt or {}).get("title"), cf))
        self.switch_to(idle_name, cf, immediate=False)

    def next_track(self, current):
        try:
            st = self.fetch("/music/agent/state")
            pl = st.get("playlist")
            if pl and pl.get("tracks"):
                tracks = pl["tracks"]
                if current:
                    cur_key = self._track_key(current)
                    for i, t in enumerate(tracks):
                        if self._track_key(t) == cur_key:
                            return tracks[(i + 1) % len(tracks)]
                return tracks[0]
        except Exception:
            pass
        return current

    # ---------- дакинг ----------
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
    ap = argparse.ArgumentParser(description="FitIntel DJ Agent v4.4")
    ap.add_argument("--server", required=True, help="http://192.168.101.182/api/v1")
    ap.add_argument("--token", required=True)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--debug", action="store_true")
    ap.add_argument("--lib", default=None)
    ap.add_argument("--interval", type=float, default=3.0)
    ap.add_argument("--mic", action="store_true")
    ap.add_argument("--duck-threshold", type=float, default=0.08)
    ap.add_argument("--duck-factor", type=float, default=0.2)
    ap.add_argument("--duck-hold", type=float, default=2.0)
    args = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    agent = None
    try:
        agent = Agent(args)
        agent.run()
    except KeyboardInterrupt:
        print("остановлено")
    finally:
        if agent is not None:
            agent.stop()


if __name__ == "__main__":
    main()