# -*- coding: utf-8 -*-
"""Музыка/DJ-пульт (экран 29): зоны, деки A/B, кроссфейд, мастер, пады 1-8,
энерджи-режим, статус лицензии на фоновую музыку."""
import json
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QComboBox, QSlider, QSpinBox, QGridLayout, QMessageBox,
    QGroupBox, QTabWidget)
from . import theme
from .form_dialog import FormDialog

def _t(name, *args):
    f = getattr(theme, name, None)
    if not callable(f):
        return ""
    for a in (args, ()):
        try:
            return f(*a)
        except TypeError:
            continue
        except Exception:
            return ""
    return ""

class Worker(QThread):
    done = pyqtSignal(object)
    fail = pyqtSignal(object)
    def __init__(self, fn, parent=None):
        super().__init__(parent)
        self._fn = fn
    def run(self):
        try:
            self.done.emit(self._fn())
        except Exception as e:
            self.fail.emit(e)

def _err_text(e):
    resp = getattr(e, "response", None)
    if resp is not None:
        try:
            d = resp.json().get("detail")
            if d:
                return str(d)
        except Exception:
            pass
        return "Ошибка сервера %s" % resp.status_code
    return str(e)

class MusicTab(QWidget):
    def __init__(self, api, parent=None):
        super().__init__(parent)
        self.api = api
        self._workers = []
        self._zones = []
        self._playlists = []
        self._sfx = []
        self._deck_a = None   # {"title","path"}
        self._deck_b = None
        self.setStyleSheet(_t("widget_style"))
        v = QVBoxLayout(self)

        self.banner = QLabel("")
        self.banner.setWordWrap(True)
        self.banner.hide()
        v.addWidget(self.banner)

        # ---- верх: зона + фоновый режим ----
        bar = QHBoxLayout()
        bar.addWidget(QLabel("Зона:"))
        self.cmb_zone = QComboBox()
        self.cmb_zone.setMinimumWidth(280)
        bar.addWidget(self.cmb_zone, 1)
        for text, slot in [("Обновить", self.reload_all),
                           ("▶ Фон (плейлист)", self.bg_play),
                           ("⏸ Стоп", self.bg_pause),
                           ("⚡ Energize", self.energize)]:
            b = QPushButton(text)
            b.clicked.connect(slot)
            bar.addWidget(b)
        v.addLayout(bar)

        self.lbl_status = QLabel("—")
        v.addWidget(self.lbl_status)

        # ---- DJ-пульт ----
        dj_box = QGroupBox("DJ-пульт (Deck A / Deck B)")
        g = QGridLayout(dj_box)
        self.lbl_deck_a = QLabel("Deck A: пусто")
        self.lbl_deck_b = QLabel("Deck B: пусто")
        self.lbl_onair = QLabel("ЭФИР: —")
        self.lbl_onair.setStyleSheet("font-weight: bold; color: #06b6d4;")
        b_ld_a = QPushButton("Загрузить трек на A")
        b_ld_a.clicked.connect(lambda: self.load_track("A"))
        b_ld_b = QPushButton("Загрузить трек на B")
        b_ld_b.clicked.connect(lambda: self.load_track("B"))
        b_air_a = QPushButton("Эфир → A")
        b_air_a.clicked.connect(lambda: self.set_active("A"))
        b_air_b = QPushButton("Эфир → B")
        b_air_b.clicked.connect(lambda: self.set_active("B"))
        g.addWidget(self.lbl_deck_a, 0, 0)
        g.addWidget(b_ld_a, 0, 1)
        g.addWidget(b_air_a, 0, 2)
        g.addWidget(self.lbl_deck_b, 1, 0)
        g.addWidget(b_ld_b, 1, 1)
        g.addWidget(b_air_b, 1, 2)
        g.addWidget(self.lbl_onair, 2, 0, 1, 3)
        # мастер + кроссфейд + mute
        g.addWidget(QLabel("Мастер-громкость:"), 3, 0)
        self.sld_master = QSlider(Qt.Orientation.Horizontal)
        self.sld_master.setRange(0, 100)
        self.sld_master.setValue(70)
        g.addWidget(self.sld_master, 3, 1)
        self.lbl_master = QLabel("70")
        g.addWidget(self.lbl_master, 3, 2)
        g.addWidget(QLabel("Кроссфейд, сек:"), 4, 0)
        self.spin_cf = QSpinBox()
        self.spin_cf.setRange(0, 30)
        self.spin_cf.setValue(8)
        g.addWidget(self.spin_cf, 4, 1)
        b_apply = QPushButton("Применить пульт")
        b_apply.clicked.connect(self.apply_dj)
        g.addWidget(b_apply, 4, 2)
        b_mute = QPushButton("🔇 MUTE ALL")
        b_mute.setStyleSheet("background: #b91c1c; color: white; font-weight: bold;")
        b_mute.clicked.connect(self.mute_all)
        g.addWidget(b_mute, 5, 0, 1, 3)
        self.sld_master.valueChanged.connect(lambda v: self.lbl_master.setText(str(v)))
        v.addWidget(dj_box)

        # ---- пады ----
        pads_box = QGroupBox("Сэмплер (пады 1-8)")
        pv = QVBoxLayout(pads_box)
        ph = QHBoxLayout()
        b_add_sfx = QPushButton("＋ Добавить сэмпл")
        b_add_sfx.clicked.connect(self.add_sfx)
        b_rf_sfx = QPushButton("Обновить сэмплы")
        b_rf_sfx.clicked.connect(self.load_sfx)
        ph.addWidget(b_add_sfx)
        ph.addWidget(b_rf_sfx)
        ph.addStretch(1)
        pv.addLayout(ph)
        self.grid_pads = QGridLayout()
        pv.addLayout(self.grid_pads)
        v.addWidget(pads_box)

        # ---- лицензия ----
        self.lbl_license = QLabel("Лицензия фоновой музыки: —")
        v.addWidget(self.lbl_license)

        self.cmb_zone.currentIndexChanged.connect(lambda _i: self.refresh_status())
        self.reload_all()

    # ---------- infra ----------
    def _url(self, path):
        base = (getattr(self.api, "base_url", "") or "").rstrip("/")
        return base + "/music" + path

    def _run(self, fn, cb):
        w = Worker(fn, self)
        w.done.connect(cb)
        w.fail.connect(lambda e: self._show(_err_text(e), ok=False))
        self._workers.append(w)
        w.finished.connect(lambda: self._workers.remove(w) if w in self._workers else None)
        w.start()

    def _show(self, msg, ok=True):
        self.banner.setText(str(msg))
        self.banner.setStyleSheet(_t("banner_style", ok))
        self.banner.show()

    # ---------- data ----------
    def reload_all(self):
        self._run(lambda: self.api.session.get(self._url("/zones"), timeout=15).json(),
                  self._fill_zones)
        self._run(lambda: self.api.session.get(self._url("/playlists"), timeout=15).json(),
                  self._fill_playlists)
        self.load_sfx()
        self.load_license()

    def _fill_zones(self, data):
        self._zones = data if isinstance(data, list) else []
        cur = self.cmb_zone.currentData()
        self.cmb_zone.blockSignals(True)
        self.cmb_zone.clear()
        for z in self._zones:
            self.cmb_zone.addItem("%s (%s)" % (z["name"], z["provider_type"]), z["id"])
        if cur:
            i = self.cmb_zone.findData(cur)
            if i >= 0:
                self.cmb_zone.setCurrentIndex(i)
        self.cmb_zone.blockSignals(False)
        self.refresh_status()

    def _fill_playlists(self, data):
        self._playlists = data if isinstance(data, list) else []

    def load_sfx(self):
        self._run(lambda: self.api.session.get(self._url("/sfx"), timeout=15).json(),
                  self._fill_sfx)

    def _fill_sfx(self, data):
        self._sfx = data if isinstance(data, list) else []
        while self.grid_pads.count():
            it = self.grid_pads.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        for i in range(8):
            r, c = divmod(i, 4)
            if i < len(self._sfx):
                s = self._sfx[i]
                b = QPushButton("Пад %d\n%s" % (i + 1, s["name"]))
                b.setMinimumHeight(48)
                b.clicked.connect(lambda _c, sid=s["id"]: self.fire_pad(sid))
            else:
                b = QPushButton("Пад %d\n—" % (i + 1))
                b.setMinimumHeight(48)
                b.setEnabled(False)
            self.grid_pads.addWidget(b, r, c)

    def load_license(self):
        self._run(lambda: self.api.session.get(self._url("/license"), timeout=15).json(),
                  self._fill_license)

    def _fill_license(self, d):
        if not isinstance(d, dict):
            return
        st = d.get("status")
        text = {
            "ok": "✅ %s, действует до %s (договор %s)" % (
                d.get("license_type"), d.get("valid_until"), d.get("contract_number") or "—"),
            "warning": "⚠️ Лицензия не указана — для коммерческого зала нужна (РАО/ВОИС или провайдер)",
            "expired": "❌ Лицензия ИСТЕКЛА %s — фоновое воспроизведение заблокировано" % d.get("valid_until"),
        }.get(st, "—")
        color = {"ok": "#16a34a", "warning": "#d97706", "expired": "#dc2626"}.get(st, "#888")
        self.lbl_license.setText("Лицензия фоновой музыки: " + text)
        self.lbl_license.setStyleSheet("color: %s;" % color)

    # ---------- zone ops ----------
    def _zid(self):
        return self.cmb_zone.currentData()

    def refresh_status(self):
        zid = self._zid()
        if not zid:
            return
        self._run(lambda: self.api.session.get(self._url("/zones/%s/status" % zid),
                                               timeout=15).json(),
                  self._fill_status)

    def _fill_status(self, d):
        if not isinstance(d, dict):
            return
        dj = d.get("dj") or {}
        self._deck_a = dj.get("deck_a")
        self._deck_b = dj.get("deck_b")
        self.lbl_deck_a.setText("Deck A: %s" % ((self._deck_a or {}).get("title") or "пусто"))
        self.lbl_deck_b.setText("Deck B: %s" % ((self._deck_b or {}).get("title") or "пусто"))
        self.lbl_onair.setText("ЭФИР: Deck %s | мастер %s | кроссфейд %ss" % (
            dj.get("active_deck", "—"), dj.get("master_volume", "—"),
            dj.get("crossfade_seconds", "—")))
        if dj.get("master_volume") is not None:
            self.sld_master.setValue(int(dj["master_volume"]))
        if dj.get("crossfade_seconds") is not None:
            self.spin_cf.setValue(int(dj["crossfade_seconds"]))
        self.lbl_status.setText("Зона: %s | состояние: %s | громкость: %s" % (
            d.get("zone"), d.get("state"), d.get("volume")))

    def bg_play(self):
        if not self._playlists:
            self._show("Сначала создайте плейлист (кнопка «Обновить»).", ok=False)
            return
        dlg = FormDialog("Фоновый плейлист", [
            ("playlist", "Плейлист", "combo", [p["name"] for p in self._playlists]),
        ], self)
        if not dlg.exec():
            return
        name = dlg.values().get("playlist")
        pid = next((p["id"] for p in self._playlists if p["name"] == name), None)
        zid = self._zid()
        self._run(lambda: self.api.session.post(
            self._url("/zones/%s/play" % zid),
            json={"playlist_id": pid}, timeout=15).json(),
            lambda _r: (self._show("Фоновое воспроизведение запущено."),
                        self.refresh_status()))

    def bg_pause(self):
        zid = self._zid()
        self._run(lambda: self.api.session.post(
            self._url("/zones/%s/pause" % zid), timeout=15).json(),
            lambda _r: (self._show("Остановлено."), self.refresh_status()))

    def energize(self):
        zid = self._zid()
        self._run(lambda: self.api.session.post(
            self._url("/zones/%s/energize" % zid), timeout=15).json(),
            lambda r: (self._show("ENERGIZE: %s, громкость %s" % (
                r.get("playlist"), r.get("volume"))), self.refresh_status()))

    # ---------- DJ ----------
    def load_track(self, deck):
        if not self._playlists:
            self._show("Нет плейлистов.", ok=False)
            return
        names = [p["name"] for p in self._playlists]
        dlg = FormDialog("Трек на дек %s" % deck, [
            ("playlist", "Плейлист", "combo", names),
        ], self)
        if not dlg.exec():
            return
        pl = next((p for p in self._playlists
                   if p["name"] == dlg.values().get("playlist")), None)
        tracks = pl.get("tracks") or []
        if not tracks:
            self._show("В плейлисте нет треков.", ok=False)
            return
        dlg2 = FormDialog("Трек из «%s»" % pl["name"], [
            ("track", "Трек", "combo", [t.get("title", t.get("path")) for t in tracks]),
        ], self)
        if not dlg2.exec():
            return
        title = dlg2.values().get("track")
        tr = next((t for t in tracks
                   if t.get("title", t.get("path")) == title), None)
        if deck == "A":
            self._deck_a = tr
        else:
            self._deck_b = tr
        self.apply_dj()

    def set_active(self, deck):
        self.apply_dj(active=deck)

    def apply_dj(self, active=None):
        zid = self._zid()
        body = {"deck_a": self._deck_a, "deck_b": self._deck_b,
                "active_deck": active or self._current_active(),
                "crossfade_seconds": float(self.spin_cf.value()),
                "master_volume": int(self.sld_master.value())}
        def _do():
            return self.api.session.post(self._url("/zones/%s/dj" % zid),
                                         json=body, timeout=15).json()
        self._run(_do, lambda _r: (self._show("Пульт применён."),
                                   self.refresh_status()))

    def _current_active(self):
        txt = self.lbl_onair.text()
        return "B" if "Deck B" in txt else "A"

    def mute_all(self):
        self.sld_master.setValue(0)
        self.apply_dj()
        self._show("MUTE: мастер-громкость 0. Верните ползунок и «Применить пульт».")

    # ---------- pads ----------
    def fire_pad(self, sfx_id):
        zid = self._zid()
        self._run(lambda: self.api.session.post(
            self._url("/zones/%s/pad-fire" % zid),
            json={"sfx_id": sfx_id}, timeout=15).json(),
            lambda r: self._show("Пад: %s (%s)" % (r.get("sfx"), r.get("mode", "local"))))

    def add_sfx(self):
        dlg = FormDialog("Новый сэмпл", [
            ("name", "Название", "text", None),
            ("path", "Путь к файлу (относ. --lib или абсолютный)", "text", None),
            ("volume", "Громкость 0-100", "text", "80"),
        ], self)
        if not dlg.exec():
            return
        v = dlg.values()
        try:
            vol = int(v.get("volume") or 80)
        except ValueError:
            vol = 80
        body = {"name": v.get("name"), "path": v.get("path"),
                "volume": max(0, min(100, vol)), "sort": len(self._sfx) + 1}
        self._run(lambda: self.api.session.post(self._url("/sfx"),
                                                json=body, timeout=15).json(),
                  lambda _r: (self._show("Сэмпл добавлен."), self.load_sfx()))