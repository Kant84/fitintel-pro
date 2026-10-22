#fitintel-desktop\windows\music_tab.py
# -*- coding: utf-8 -*-
"""Музыка/DJ-пульт (экран 29): зоны, ПЛЕЕР НА ЭТОМ ПК (вкл/выкл, микрофон вкл/выкл),
настройка провайдера и лицензии из окна, деки A/B, файлы/папки с диска,
кроссфейд, мастер, эквалайзер, пады 1-8, энерджи-режим, лицензия фоновой музыки.
Сервер может быть удалённым — плеер на этом ПК общается с ним по HTTP.

v4.6:
- агент запускается ПОТОКОМ внутри GUI (в onefile-сборке нет python.exe);
- панель плейлистов справа от DJ-пульта (выбор трека, →A/→B, ▶A/▶B, двойной клик);
- авто-регистрация агента по machine_id;
- один _agent_running, без дублей.
"""
import json
import os
import subprocess
from pathlib import Path
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QTimer
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QComboBox, QSlider, QSpinBox, QGridLayout, QMessageBox,
    QGroupBox, QTabWidget, QFileDialog, QScrollArea,
    QListWidget, QListWidgetItem)
from . import theme
from .form_dialog import FormDialog


BTN_STYLE = (
    "QPushButton { background: #164e63; color: #a5f3fc; border: 1px solid #0891b2;"
    " border-radius: 6px; padding: 6px 10px; font-weight: 600; }"
    "QPushButton:hover { background: #0e7490; }"
    "QPushButton:pressed { background: #155e75; }"
    "QPushButton:disabled { background: #1e293b; color: #475569; border-color: #334155; }"
)

MUTE_STYLE = (
    "QPushButton { background: #b91c1c; color: white; font-weight: bold;"
    " border: 1px solid #ef4444; border-radius: 6px; padding: 6px 10px; }"
    "QPushButton:hover { background: #dc2626; }"
    "QPushButton:pressed { background: #991b1b; }"
)

AGENT_ON_STYLE = (
    "QPushButton { background: #15803d; color: white; font-weight: bold;"
    " border: 1px solid #22c55e; border-radius: 6px; padding: 6px 10px; }"
    "QPushButton:hover { background: #16a34a; }"
)

MIC_ON_STYLE = (
    "QPushButton { background: #7c3aed; color: white; font-weight: bold;"
    " border: 1px solid #a78bfa; border-radius: 6px; padding: 6px 10px; }"
    "QPushButton:hover { background: #8b5cf6; }"
)

AUDIO_FILTER = "Аудио (*.mp3 *.flac *.ogg *.wav *.m4a);;Все файлы (*)"


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
        self._deck_a = None
        self._deck_b = None
        self._btn_mute = None
        # агент работает как поток внутри GUI
        self._agent_thread = None
        self._agent_obj = None
        self.setStyleSheet(_t("widget_style"))
        outer = QWidget()
        v = QVBoxLayout(outer)

        self.banner = QLabel("")
        self.banner.setWordWrap(True)
        self.banner.hide()
        v.addWidget(self.banner)

        # ---- плеер на этом ПК ----
        pl_box = QGroupBox("Плеер на этом ПК / провайдер")
        plh = QHBoxLayout(pl_box)
        self.lbl_agent = QLabel("—")
        self.btn_agent = QPushButton("⏵ Плеер: ВКЛ")
        self.btn_agent.setToolTip("Запустить/остановить плеер на этом компьютере")
        self.btn_agent.clicked.connect(self.toggle_agent)
        self.btn_mic = QPushButton("")
        self.btn_mic.setToolTip("Микрофон: авто-дакинг музыки во время речи.\n"
                                "Если плеер работает — перезапустит его с новой настройкой.")
        self.btn_mic.clicked.connect(self.toggle_mic)
        b_new_zone = QPushButton("＋ Новая зона…")
        b_new_zone.setToolTip("Создать зону: плеер на этом ПК (local_agent) "
                              "или коробка провайдера (external)")
        b_new_zone.clicked.connect(self.create_zone)
        b_agent_cfg = QPushButton("⚙ Плеер…")
        b_agent_cfg.setToolTip("Папка музыки по умолчанию для плеера на этом ПК")
        b_agent_cfg.clicked.connect(self.agent_settings)
        b_prov = QPushButton("⚙ Провайдер…")
        b_prov.setToolTip("Настройка выбранной зоны external")
        b_prov.clicked.connect(self.provider_settings)
        b_lic = QPushButton("⚙ Лицензия…")
        b_lic.setToolTip("Договор на коммерческий фон (РАО/ВОИС или провайдер)")
        b_lic.clicked.connect(self.license_settings)
        plh.addWidget(self.lbl_agent, 1)
        plh.addWidget(self.btn_agent)
        plh.addWidget(self.btn_mic)
        plh.addWidget(b_new_zone)
        plh.addWidget(b_agent_cfg)
        plh.addWidget(b_prov)
        plh.addWidget(b_lic)
        v.addWidget(pl_box)

        # строка «Сервер: ...»
        self.lbl_server = QLabel("")
        self.lbl_server.setStyleSheet("color: #94a3b8;")
        v.addWidget(self.lbl_server)
        self._update_server_label()

        # ---- верх: зона + фоновый режим ----
        bar = QHBoxLayout()
        bar.addWidget(QLabel("Зона:"))
        self.cmb_zone = QComboBox()
        self.cmb_zone.setMinimumWidth(280)
        self.cmb_zone.setToolTip("local_agent = плеер на ПК; external = коробка провайдера")
        bar.addWidget(self.cmb_zone, 1)
        for text, slot in [("Обновить", self.reload_all),
                           ("Фон (плейлист)", self.bg_play),
                           ("Стоп", self.bg_pause),
                           ("Energize", self.energize)]:
            b = QPushButton(text)
            b.clicked.connect(slot)
            bar.addWidget(b)
        v.addLayout(bar)

        self.lbl_status = QLabel("—")
        v.addWidget(self.lbl_status)

        # ---- DJ-пульт + плейлисты (горизонтально) ----
        dj_row = QHBoxLayout()

        # левая часть: деки
        dj_box = QGroupBox("DJ-пульт (Deck A / Deck B)")
        g = QGridLayout(dj_box)
        self.lbl_deck_a = QLabel("Deck A: пусто")
        self.lbl_deck_b = QLabel("Deck B: пусто")
        self.lbl_onair = QLabel("ЭФИР: —")
        self.lbl_onair.setStyleSheet("font-weight: bold; color: #06b6d4;")
        b_ld_a = QPushButton("Трек на A")
        b_ld_a.clicked.connect(lambda: self.load_track("A"))
        b_ld_b = QPushButton("Трек на B")
        b_ld_b.clicked.connect(lambda: self.load_track("B"))
        b_file_a = QPushButton("Файл на A…")
        b_file_a.setToolTip("Любой аудиофайл с диска/флешки — без плейлиста")
        b_file_a.clicked.connect(lambda: self.load_file("A"))
        b_file_b = QPushButton("Файл на B…")
        b_file_b.setToolTip("Любой аудиофайл с диска/флешки — без плейлиста")
        b_file_b.clicked.connect(lambda: self.load_file("B"))
        b_fold_a = QPushButton("Папка на A…")
        b_fold_a.setToolTip("Вся папка с диска/флешки — треки по очереди, по кругу")
        b_fold_a.clicked.connect(lambda: self.load_folder("A"))
        b_fold_b = QPushButton("Папка на B…")
        b_fold_b.setToolTip("Вся папка с диска/флешки — треки по очереди, по кругу")
        b_fold_b.clicked.connect(lambda: self.load_folder("B"))
        b_air_a = QPushButton("Эфир A")
        b_air_a.clicked.connect(lambda: self.set_active("A"))
        b_air_b = QPushButton("Эфир B")
        b_air_b.clicked.connect(lambda: self.set_active("B"))
        g.addWidget(self.lbl_deck_a, 0, 0)
        g.addWidget(b_ld_a, 0, 1)
        g.addWidget(b_file_a, 0, 2)
        g.addWidget(b_fold_a, 0, 3)
        g.addWidget(b_air_a, 0, 4)
        g.addWidget(self.lbl_deck_b, 1, 0)
        g.addWidget(b_ld_b, 1, 1)
        g.addWidget(b_file_b, 1, 2)
        g.addWidget(b_fold_b, 1, 3)
        g.addWidget(b_air_b, 1, 4)
        g.addWidget(self.lbl_onair, 2, 0, 1, 5)
        g.addWidget(QLabel("Мастер-громкость:"), 3, 0)
        self.sld_master = QSlider(Qt.Orientation.Horizontal)
        self.sld_master.setRange(0, 100)
        self.sld_master.setValue(70)
        g.addWidget(self.sld_master, 3, 1, 1, 3)
        self.lbl_master = QLabel("70")
        g.addWidget(self.lbl_master, 3, 4)
        g.addWidget(QLabel("Кроссфейд, сек:"), 4, 0)
        self.spin_cf = QSpinBox()
        self.spin_cf.setRange(0, 30)
        self.spin_cf.setValue(8)
        g.addWidget(self.spin_cf, 4, 1)
        b_apply = QPushButton("Применить пульт")
        b_apply.clicked.connect(self.apply_dj)
        g.addWidget(b_apply, 4, 2, 1, 3)
        b_mute = QPushButton("MUTE ALL")
        b_mute.setStyleSheet(MUTE_STYLE)
        self._btn_mute = b_mute
        b_mute.clicked.connect(self.mute_all)
        g.addWidget(b_mute, 5, 0, 1, 5)
        self.sld_master.valueChanged.connect(lambda v: self.lbl_master.setText(str(v)))
        dj_row.addWidget(dj_box, 3)

        # правая часть: плейлисты + треки
        pl_box = QGroupBox("Плейлисты")
        pv = QVBoxLayout(pl_box)

        plh = QHBoxLayout()
        plh.addWidget(QLabel("Плейлист:"))
        self.cmb_pl_dj = QComboBox()
        self.cmb_pl_dj.setMinimumWidth(180)
        self.cmb_pl_dj.currentIndexChanged.connect(self._fill_dj_tracks)
        plh.addWidget(self.cmb_pl_dj, 1)
        b_rf_pl = QPushButton("⟳")
        b_rf_pl.setToolTip("Обновить список плейлистов")
        b_rf_pl.setFixedWidth(32)
        b_rf_pl.clicked.connect(self.reload_all)
        plh.addWidget(b_rf_pl)
        pv.addLayout(plh)

        self.list_dj_tracks = QListWidget()
        self.list_dj_tracks.setMinimumHeight(120)
        self.list_dj_tracks.itemDoubleClicked.connect(self._dj_double_click)
        pv.addWidget(self.list_dj_tracks, 1)

        bph = QHBoxLayout()
        b_to_a = QPushButton("→ A")
        b_to_a.setToolTip("Загрузить трек на дек A (без эфира)")
        b_to_a.clicked.connect(lambda: self._dj_to_deck("A", air=False))
        b_to_b = QPushButton("→ B")
        b_to_b.setToolTip("Загрузить трек на дек B (без эфира)")
        b_to_b.clicked.connect(lambda: self._dj_to_deck("B", air=False))
        b_play_a = QPushButton("▶ A")
        b_play_a.setToolTip("Загрузить на A и сразу в эфир")
        b_play_a.clicked.connect(lambda: self._dj_to_deck("A", air=True))
        b_play_b = QPushButton("▶ B")
        b_play_b.setToolTip("Загрузить на B и сразу в эфир")
        b_play_b.clicked.connect(lambda: self._dj_to_deck("B", air=True))
        bph.addWidget(b_to_a)
        bph.addWidget(b_to_b)
        bph.addStretch(1)
        bph.addWidget(b_play_a)
        bph.addWidget(b_play_b)
        pv.addLayout(bph)

        dj_row.addWidget(pl_box, 2)
        v.addLayout(dj_row)

        # ---- эквалайзер ----
        eq_box = QGroupBox("Эквалайзер (дБ, −12…+12)")
        eg = QGridLayout(eq_box)
        self.eq_sliders = {}
        bands = [("bass", "Бас"), ("mid", "Середина"), ("treble", "Верха")]
        for col, (_key, title) in enumerate(bands):
            eg.addWidget(QLabel(title), 0, col + 1)
        for row, deck in enumerate(("A", "B"), start=1):
            eg.addWidget(QLabel("Дек %s" % deck), row, 0)
            for col, (key, _title) in enumerate(bands):
                s = QSlider(Qt.Orientation.Horizontal)
                s.setRange(-12, 12)
                s.setValue(0)
                s.setTickPosition(QSlider.TickPosition.TicksBelow)
                s.valueChanged.connect(lambda _v: self._eq_label_update())
                eg.addWidget(s, row, col + 1)
                self.eq_sliders[(deck, key)] = s
        self.lbl_eq = QLabel("A: 0/0/0 | B: 0/0/0")
        eg.addWidget(self.lbl_eq, 3, 0, 1, 4)
        b_eq = QPushButton("Применить EQ")
        b_eq.clicked.connect(self.apply_dj)
        eg.addWidget(b_eq, 4, 0, 1, 4)
        v.addWidget(eq_box)

        # ---- пады ----
        pads_box = QGroupBox("Сэмплер (пады 1-8)")
        pv = QVBoxLayout(pads_box)
        ph = QHBoxLayout()
        b_add_sfx = QPushButton("Добавить сэмпл")
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
        self._upd_agent_btn()
        self._tmr = QTimer(self)
        self._tmr.timeout.connect(self._upd_agent_btn)
        self._tmr.start(2000)
        for b in self.findChildren(QPushButton):
            if b is self._btn_mute:
                continue
            b.setStyleSheet(BTN_STYLE)
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setWidget(outer)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(scroll)

    # ---------- настройки ----------
    def _settings_rw(self, mutate=None):
        try:
            from paths import SETTINGS as _p
            cfg = json.loads(_p.read_text(encoding="utf-8")) if _p.exists() else {}
        except Exception:
            cfg = {}
        if mutate:
            cfg = mutate(cfg)
            try:
                from paths import SETTINGS as _p
                _p.write_text(json.dumps(cfg, ensure_ascii=False, indent=2),
                              encoding="utf-8")
            except Exception:
                pass
        return cfg

    def _agent_cfg(self):
        return self._settings_rw().get("dj_agent") or {}

    def _agent_token(self):
        return self._agent_cfg().get("token")

    def _mic_on(self):
        return bool(self._agent_cfg().get("mic"))

    def _update_server_label(self):
        server = (getattr(self.api, "base_url", "") or "").rstrip("/")
        self.lbl_server.setText("Сервер: %s" % (server or "—"))

    # ---------- плеер на этом ПК ----------
    def _agent_running(self):
        t = getattr(self, "_agent_thread", None)
        ag = getattr(self, "_agent_obj", None)
        return bool(t and t.is_alive() and ag is not None)

    def _upd_agent_btn(self):
        running = self._agent_running()
        has_token = bool(self._agent_token())
        mic = self._mic_on()
        self.btn_agent.setText("⏹ Плеер: ВЫКЛ" if running else "⏵ Плеер: ВКЛ")
        self.btn_agent.setStyleSheet(AGENT_ON_STYLE if running else BTN_STYLE)
        self.btn_mic.setText("🎤 Микрофон: ВКЛ" if mic else "🎤 Микрофон: ВЫКЛ")
        self.btn_mic.setStyleSheet(MIC_ON_STYLE if mic else BTN_STYLE)
        if running:
            self.lbl_agent.setText("Плеер на этом ПК: РАБОТАЕТ (звук в колонках)")
            self.lbl_agent.setStyleSheet("color: #22c55e; font-weight: 600;")
        elif has_token:
            self.lbl_agent.setText("Плеер на этом ПК: остановлен. Нажмите «Плеер: ВКЛ».")
            self.lbl_agent.setStyleSheet("color: #d97706;")
        else:
            self.lbl_agent.setText("Зона-плеер будет создана автоматически "
                                   "при запуске плеера.")
            self.lbl_agent.setStyleSheet("color: #94a3b8;")

    def toggle_mic(self):
        new_val = not self._mic_on()

        def _mut(cfg):
            dj = cfg.get("dj_agent") or {}
            dj["mic"] = new_val
            cfg["dj_agent"] = dj
            return cfg

        self._settings_rw(mutate=_mut)
        self._upd_agent_btn()
        if self._agent_running():
            self._stop_agent()
            self._start_agent()
            self._show("Микрофон %s — плеер перезапущен."
                       % ("включён" if new_val else "выключен"))
        else:
            self._show("Микрофон %s. Включится при запуске плеера."
                       % ("включён" if new_val else "выключен"))

    def _start_agent(self):
        """Запускает агент как ПОТОК внутри GUI.
        В собранном exe python.exe отсутствует — запускать subprocess'ом нельзя."""
        # Уже запущен?
        t = getattr(self, "_agent_thread", None)
        if t and t.is_alive():
            return True

        cfg = self._agent_cfg()
        lib = cfg.get("lib") or r"E:\music\club"
        server = (getattr(self.api, "base_url", "") or "").rstrip("/")
        token = self._agent_token() or ""
        if not server:
            self._show("Не задан адрес сервера (api_base).", ok=False)
            return False

        # Ищем папку агента: bundle (PyInstaller) или репозиторий
        import sys as _sys
        bundle = getattr(_sys, "_MEIPASS", None)
        if bundle:
            agent_dir = Path(bundle) / "scripts" / "music"
        else:
            agent_dir = Path(__file__).resolve().parents[2] / "scripts" / "music"

        if not (agent_dir / "agent.py").exists():
            self._show("Не найден агент: %s" % (agent_dir / "agent.py"), ok=False)
            return False

        sdir = str(agent_dir)
        if sdir not in _sys.path:
            _sys.path.insert(0, sdir)

        import argparse
        args = argparse.Namespace(
            server=server, token=token, lib=lib,
            dry_run=False, debug=True,
            mic=self._mic_on(), interval=0.5,
            duck_threshold=0.08, duck_factor=0.2, duck_hold=2.0,
        )

        def _run():
            try:
                from agent import Agent as _Agent
                ag = _Agent(args)
                self._agent_obj = ag
                ag.run()
            except Exception as e:
                import traceback
                print("AGENT THREAD ERR:", e)
                traceback.print_exc()

        import threading
        self._agent_thread = threading.Thread(target=_run, daemon=True,
                                              name="FitIntelAgent")
        self._agent_thread.start()
        self._show("Плеер запущен (агент в потоке).")
        return True

    def _stop_agent(self):
        ag = getattr(self, "_agent_obj", None)
        if ag is not None:
            try:
                ag.stop()
            except Exception as e:
                print("stop agent ERR:", e)
            self._agent_obj = None
        try:
            if os.name == "nt":
                subprocess.run(["taskkill", "/F", "/IM", "mpv.exe"],
                               capture_output=True, timeout=5)
        except Exception:
            pass
        t = getattr(self, "_agent_thread", None)
        if t is not None:
            try:
                t.join(timeout=4)
            except Exception:
                pass
            self._agent_thread = None

    def toggle_agent(self):
        if self._agent_running():
            self._stop_agent()
            self._show("Плеер на этом ПК остановлен (и mpv закрыты).")
            self._upd_agent_btn()
            return
        if self._start_agent():
            self._show("Плеер запущен. Управляйте деками ниже.")
        self._upd_agent_btn()

    # ---------- диалоги ----------
    def create_zone(self):
        import socket as _sock
        default_name = "Зал %s" % _sock.gethostname()
        dlg = FormDialog("Новая зона", [
            ("ptype", "Плеер", "combo",
             ["local_agent — плеер на этом ПК (агент сам зарегистрируется)",
              "external — коробка провайдера"]),
            ("name", "Имя зоны", "text", default_name),
            ("lib", "Папка музыки для local_agent (флешка/диск)", "text",
             self._agent_cfg().get("lib") or r"E:\music\club"),
            ("base_url", "Адрес коробки http://IP:порт (для external)", "text", ""),
            ("cmd_path", "Путь команд (обычно /cmd)", "text", "/cmd"),
        ], self)
        if not dlg.exec():
            return
        v = dlg.values()
        ptype_label = v.get("ptype") or ""
        ptype = "local_agent" if ptype_label.startswith("local_agent") else "external"
        name = (v.get("name") or default_name).strip()
        lib = (v.get("lib") or "").strip()

        if ptype == "local_agent":
            # Сохраняем lib — зону агент сам создаст при «Плеер: ВКЛ»
            if lib:
                lib = os.path.normpath(lib)

            def _mut(cfg):
                dj = cfg.get("dj_agent") or {}
                dj["lib"] = lib or r"E:\music\club"
                cfg["dj_agent"] = dj
                return cfg

            self._settings_rw(mutate=_mut)
            self._show("Папка музыки сохранена: %s. Запустите «Плеер: ВКЛ» — "
                       "агент сам зарегистрирует зону." % (lib or r"E:\music\club"))
            return

        # external — через API
        body = {"name": name, "provider_type": "external",
                "provider_config": {
                    "base_url": (v.get("base_url") or "").strip(),
                    "cmd_path": (v.get("cmd_path") or "/cmd").strip()}}

        def _do():
            r = self.api.session.post(self._url("/zones"), json=body, timeout=15)
            r.raise_for_status()
            return r.json()

        def _done(z):
            self._show("Зона «%s» создана (провайдер: %s)."
                       % (name, body["provider_config"].get("base_url")))
            self.reload_all()

        self._run(_do, _done)

    def agent_settings(self):
        cfg = self._agent_cfg()
        dlg = FormDialog("Плеер на этом ПК", [
            ("lib", "Папка музыки по умолчанию", "text",
             cfg.get("lib") or r"E:\music\club"),
        ], self)
        if not dlg.exec():
            return
        lib = (dlg.values().get("lib") or "").strip()
        if lib:
            lib = os.path.normpath(lib)

        def _mut(c):
            dj = c.get("dj_agent") or {}
            dj["lib"] = lib
            c["dj_agent"] = dj
            return c

        self._settings_rw(mutate=_mut)
        if self._agent_running():
            self._stop_agent()
            self._start_agent()
            self._show("Папка музыки: %s — плеер перезапущен." % lib)
        else:
            self._show("Папка музыки: %s" % lib)

    def provider_settings(self):
        zid = self._zid()
        cur = next((z for z in self._zones if z["id"] == zid), None)
        is_ext = bool(cur and cur.get("provider_type") == "external")
        cfg = (cur or {}).get("provider_config") or {}
        dlg = FormDialog("Провайдер (external-зона)", [
            ("name", "Имя зоны", "text",
             (cur or {}).get("name") or "Кардио-зона (провайдер)"),
            ("base_url", "Адрес коробки http://IP:порт", "text",
             cfg.get("base_url") or ""),
            ("cmd_path", "Путь команд (обычно /cmd)", "text",
             cfg.get("cmd_path") or "/cmd"),
        ], self)
        if not dlg.exec():
            return
        v = dlg.values()
        body = {"name": v.get("name"),
                "provider_config": {
                    "base_url": (v.get("base_url") or "").strip(),
                    "cmd_path": (v.get("cmd_path") or "/cmd").strip()}}
        if is_ext:
            def _do():
                r = self.api.session.patch(self._url("/zones/%s" % zid),
                                           json=body, timeout=15)
                r.raise_for_status()
                return r.json()
            self._run(_do, lambda _r: (self._show("Настройки провайдера сохранены."),
                                       self.reload_all()))
        else:
            body["provider_type"] = "external"

            def _do2():
                r = self.api.session.post(self._url("/zones"), json=body, timeout=15)
                r.raise_for_status()
                return r.json()
            self._run(_do2, lambda _r: (self._show("Зона провайдера создана."),
                                        self.reload_all()))

    def license_settings(self):
        dlg = FormDialog("Лицензия фоновой музыки", [
            ("ltype", "Тип договора", "combo", ["provider", "rao_vois"]),
            ("provider", "Провайдер (название)", "text", ""),
            ("contract", "Номер договора", "text", ""),
            ("valid", "Действует до (ГГГГ-ММ-ДД)", "text", "2027-12-31"),
        ], self)
        if not dlg.exec():
            return
        v = dlg.values()
        body = {"license_type": v.get("ltype") or "provider",
                "provider_name": (v.get("provider") or "").strip(),
                "contract_number": (v.get("contract") or "").strip(),
                "valid_until": (v.get("valid") or "").strip() or None}

        def _do():
            r = self.api.session.post(self._url("/license"), json=body, timeout=15)
            r.raise_for_status()
            return r.json()

        self._run(_do, lambda r: (self._show("Лицензия сохранена: %s"
                                             % r.get("status")),
                                  self.load_license()))

    # ---------- infra ----------
    def _url(self, path):
        base = (getattr(self.api, "base_url", "") or "").rstrip("/")
        return base + "/music" + path

    def _run(self, fn, cb):
        w = Worker(fn, self)
        w.done.connect(cb)
        w.fail.connect(lambda e: self._show(_err_text(e), ok=False))
        self._workers.append(w)
        w.finished.connect(lambda: self._workers.remove(w)
                           if w in self._workers else None)
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
        tok = self._agent_token()
        cur = self.cmb_zone.currentData()
        self.cmb_zone.blockSignals(True)
        self.cmb_zone.clear()
        for z in self._zones:
            self.cmb_zone.addItem("%s (%s) · %s"
                                  % (z["name"], z["provider_type"],
                                     str(z["id"])[:8]), z["id"])
        pick = cur
        if tok:
            for z in self._zones:
                if z.get("agent_token") == tok:
                    pick = z["id"]
                    break
        if pick:
            i = self.cmb_zone.findData(pick)
            if i >= 0:
                self.cmb_zone.setCurrentIndex(i)
        self.cmb_zone.blockSignals(False)
        self.refresh_status()

    def _fill_playlists(self, data):
        self._playlists = data if isinstance(data, list) else []
        # синхронизируем комбо в блоке плейлистов DJ
        self.cmb_pl_dj.blockSignals(True)
        cur = self.cmb_pl_dj.currentText()
        self.cmb_pl_dj.clear()
        self.cmb_pl_dj.addItem("— выбери плейлист —", "")
        for p in self._playlists:
            self.cmb_pl_dj.addItem(p.get("name") or p.get("id"), p["id"])
        if cur:
            i = self.cmb_pl_dj.findText(cur)
            if i >= 0:
                self.cmb_pl_dj.setCurrentIndex(i)
        self.cmb_pl_dj.blockSignals(False)
        self._fill_dj_tracks()

    def _fill_dj_tracks(self):
        """Заполняет список треков выбранного плейлиста."""
        self.list_dj_tracks.clear()
        pid = self.cmb_pl_dj.currentData()
        if not pid:
            return
        pl = next((p for p in self._playlists if p["id"] == pid), None)
        if not pl:
            return
        tracks = pl.get("tracks") or []
        for i, t in enumerate(tracks, start=1):
            title = t.get("title") or t.get("path") or "?"
            path = t.get("path") or ""
            it = QListWidgetItem("%2d. %s" % (i, title))
            it.setData(Qt.ItemDataRole.UserRole, {"title": title, "path": path})
            it.setToolTip(path)
            self.list_dj_tracks.addItem(it)

    def _dj_selected_track(self):
        it = self.list_dj_tracks.currentItem()
        if not it:
            self._show("Выбери трек в списке.", ok=False)
            return None
        return it.data(Qt.ItemDataRole.UserRole)

    def _dj_to_deck(self, deck, air=False):
        tr = self._dj_selected_track()
        if not tr:
            return
        self._set_deck(deck, tr)
        if air:
            # ставим этот дек в эфир
            self.apply_dj(active=deck)

    def _dj_double_click(self, item):
        """Двойной клик по треку — на активный дек и в эфир."""
        tr = item.data(Qt.ItemDataRole.UserRole)
        if not tr:
            return
        deck = self._current_active()
        self._set_deck(deck, tr)
        self.apply_dj(active=deck)

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
        if self._btn_mute is not None:
            for b in self.grid_pads.parentWidget().findChildren(QPushButton):
                if b is not self._btn_mute:
                    b.setStyleSheet(BTN_STYLE)

    def load_license(self):
        self._run(lambda: self.api.session.get(self._url("/license"), timeout=15).json(),
                  self._fill_license)

    def _fill_license(self, d):
        if not isinstance(d, dict):
            return
        st = d.get("status")
        text = {
            "ok": " %s, действует до %s (договор %s)" % (
                d.get("license_type"), d.get("valid_until"),
                d.get("contract_number") or "—"),
            "warning": " Лицензия не указана — фон заблокирован (⚙ Лицензия…)",
            "expired": " Лицензия ИСТЕКЛА %s — фоновое воспроизведение заблокировано"
                       % d.get("valid_until"),
        }.get(st, "—")
        color = {"ok": "#16a34a", "warning": "#d97706",
                 "expired": "#dc2626"}.get(st, "#888")
        self.lbl_license.setText("Лицензия фоновой музыки: " + text)
        self.lbl_license.setStyleSheet("color: %s;" % color)

    # ---------- zone ops ----------
    def _zid(self):
        return self.cmb_zone.currentData()

    def refresh_status(self):
        zid = self._zid()
        if not zid:
            return
        self._run(lambda: self.api.session.get(
            self._url("/zones/%s/status" % zid), timeout=15).json(),
            self._fill_status)

    def _fill_status(self, d):
        if not isinstance(d, dict):
            return
        dj = d.get("dj") or {}
        self._deck_a = dj.get("deck_a")
        self._deck_b = dj.get("deck_b")
        self.lbl_deck_a.setText("Deck A: %s"
                                % ((self._deck_a or {}).get("title") or "пусто"))
        self.lbl_deck_b.setText("Deck B: %s"
                                % ((self._deck_b or {}).get("title") or "пусто"))
        self.lbl_onair.setText("ЭФИР: Deck %s | мастер %s | кроссфейд %ss" % (
            dj.get("active_deck", "—"), dj.get("master_volume", "—"),
            dj.get("crossfade_seconds", "—")))
        if dj.get("master_volume") is not None:
            self.sld_master.setValue(int(dj["master_volume"]))
        if dj.get("crossfade_seconds") is not None:
            self.spin_cf.setValue(int(dj["crossfade_seconds"]))
        eq = dj.get("eq") or {}
        for deck in ("A", "B"):
            e = eq.get(deck) or {}
            for key in ("bass", "mid", "treble"):
                s = self.eq_sliders.get((deck, key))
                if s and key in e:
                    s.blockSignals(True)
                    s.setValue(int(e[key]))
                    s.blockSignals(False)
        self._eq_label_update()
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
        if not zid:
            self._show("Не выбрана зона.", ok=False)
            return
        body = {"deck_a": None, "deck_b": None, "active_deck": "A",
                "crossfade_seconds": float(self.spin_cf.value()),
                "master_volume": int(self.sld_master.value()),
                "eq": {"A": {"bass": 0, "mid": 0, "treble": 0},
                       "B": {"bass": 0, "mid": 0, "treble": 0}}}

        def _do():
            self.api.session.post(self._url("/zones/%s/pause" % zid), timeout=15)
            self.api.session.post(self._url("/zones/%s/dj" % zid),
                                  json=body, timeout=15)
            return True

        def _done(_r):
            self._deck_a = None
            self._deck_b = None
            self._show("Стоп: зона остановлена, деки очищены.")
            self.refresh_status()

        self._run(_do, _done)

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
            ("track", "Трек", "combo",
             [t.get("title", t.get("path")) for t in tracks]),
        ], self)
        if not dlg2.exec():
            return
        title = dlg2.values().get("track")
        tr = next((t for t in tracks
                   if t.get("title", t.get("path")) == title), None)
        self._set_deck(deck, tr)

    def load_file(self, deck):
        path, _f = QFileDialog.getOpenFileName(
            self, "Трек на дек %s" % deck, "", AUDIO_FILTER)
        if not path:
            return
        self._set_deck(deck, {"title": os.path.splitext(os.path.basename(path))[0],
                              "path": path})

    def load_folder(self, deck):
        d = QFileDialog.getExistingDirectory(
            self, "Папка на дек %s — все треки по очереди" % deck)
        if not d:
            return
        d = os.path.normpath(d)
        if os.path.dirname(d) == d:
            self._show("Выбран корень диска %s. Выберите папку с музыкой "
                       "(например, G:\\music)." % d, ok=False)
            return
        base = os.path.basename(d) or d
        self._set_deck(deck, {"title": "[папка] " + base, "path": d})

    def _set_deck(self, deck, track):
        if deck == "A":
            self._deck_a = track
        else:
            self._deck_b = track
        self.apply_dj()

    def set_active(self, deck):
        self.apply_dj(active=deck)

    def apply_dj(self, active=None):
        zid = self._zid()
        if not zid:
            self._show("Не выбрана зона.", ok=False)
            return
        body = {"deck_a": self._deck_a, "deck_b": self._deck_b,
                "active_deck": active or self._current_active(),
                "crossfade_seconds": float(self.spin_cf.value()),
                "master_volume": int(self.sld_master.value()),
                "eq": {"A": self._eq_values("A"), "B": self._eq_values("B")}}

        def _do():
            return self.api.session.post(self._url("/zones/%s/dj" % zid),
                                         json=body, timeout=15).json()

        self._run(_do, lambda _r: (self._show("Пульт применён."),
                                   self.refresh_status()))

    def _current_active(self):
        txt = self.lbl_onair.text()
        return "B" if "Deck B" in txt else "A"

    def _eq_values(self, deck):
        return {"bass": self.eq_sliders[(deck, "bass")].value(),
                "mid": self.eq_sliders[(deck, "mid")].value(),
                "treble": self.eq_sliders[(deck, "treble")].value()}

    def _eq_label_update(self):
        a = self._eq_values("A")
        b = self._eq_values("B")
        self.lbl_eq.setText("A: %s/%s/%s | B: %s/%s/%s" % (
            a["bass"], a["mid"], a["treble"], b["bass"], b["mid"], b["treble"]))

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
            lambda r: self._show("Пад: %s (%s)"
                                 % (r.get("sfx"), r.get("mode", "local"))))

    def add_sfx(self):
        dlg = FormDialog("Новый сэмпл", [
            ("name", "Название", "text", None),
            ("path", "Путь к файлу (относ. --lib или абсолютный)", "text", None),
            ("volume", "Громкость 0-100", "text", "80"),
        ], self)
        if not dlg.exec():
            return
        v = dlg.values()
        path = (v.get("path") or "").strip()
        if not path:
            self._show("Путь к сэмплу пуст.", ok=False)
            return
        if os.path.isdir(path):
            self._show("Это папка, а не файл. Укажите конкретный аудиофайл.",
                       ok=False)
            return
        try:
            vol = int(v.get("volume") or 80)
        except ValueError:
            vol = 80
        body = {"name": v.get("name"), "path": path,
                "volume": max(0, min(100, vol)), "sort": len(self._sfx) + 1}
        self._run(lambda: self.api.session.post(self._url("/sfx"),
                                                json=body, timeout=15).json(),
                  lambda _r: (self._show("Сэмпл добавлен."), self.load_sfx()))