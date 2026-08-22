# -*- coding: utf-8 -*-
"""FitIntel Pro theme manager: neon electro-punk (dark) + clean light."""
from PyQt6.QtWidgets import QApplication

DARK = True

# --- dark neon palette ---
N_BG      = "#07070f"
N_PANEL   = "#0e0e1d"
N_ROW     = "#0a0a18"
N_ROW_ALT = "#171732"
N_CYAN    = "#00f0ff"
N_MAGENTA = "#ff2bd6"
N_GREEN   = "#39ff14"
N_RED     = "#ff3860"
N_PURPLE  = "#9d4edd"
N_TEXT    = "#e8e8ff"
N_SUB     = "#9a9ac0"

# --- light palette ---
L_BG      = "#f2f4fa"
L_PANEL   = "#ffffff"
L_ROW     = "#ffffff"
L_ROW_ALT = "#e6eaf6"
L_ACCENT  = "#4338ca"
L_GREEN   = "#15803d"
L_RED     = "#dc2626"
L_TEXT    = "#1a1a2e"
L_SUB     = "#55556e"


def _build(dark):
    if dark:
        bg, panel, row, row_alt = N_BG, N_PANEL, N_ROW, N_ROW_ALT
        text, sub = N_TEXT, N_SUB
        accent, sel_txt = N_MAGENTA, "#050510"
        ok_c, err_c = N_GREEN, N_RED
        hdr_c = N_CYAN
        btn_hover = "#1c1c3a"
    else:
        bg, panel, row, row_alt = L_BG, L_PANEL, L_ROW, L_ROW_ALT
        text, sub = L_TEXT, L_SUB
        accent, sel_txt = L_ACCENT, "#ffffff"
        ok_c, err_c = L_GREEN, L_RED
        hdr_c = L_ACCENT
        btn_hover = "#e0e4f5"
    return "/*FITINTEL_THEME*/\n" + f"""
QWidget {{ background: {bg}; color: {text}; font-family: 'Segoe UI'; font-size: 13px; }}
QMainWindow, QDialog {{ background: {bg}; }}
QMenuBar {{ background: {panel}; color: {text}; border-bottom: 1px solid {accent}; }}
QMenuBar::item:selected {{ background: {accent}; color: {sel_txt}; }}
QMenu {{ background: {panel}; color: {text}; border: 1px solid {accent}; }}
QMenu::item:selected {{ background: {accent}; color: {sel_txt}; }}
QListWidget {{ background: {panel}; color: {text}; border: none; outline: none; }}
QListWidget::item {{ padding: 10px 14px; border-left: 3px solid transparent; }}
QListWidget::item:selected {{ background: {btn_hover}; color: {hdr_c}; border-left: 3px solid {accent}; }}
QListWidget::item:hover {{ background: {btn_hover}; }}
QPushButton {{ background: {panel}; color: {hdr_c}; border: 1px solid {hdr_c}; border-radius: 6px; padding: 7px 14px; }}
QPushButton:hover {{ background: {hdr_c}; color: {sel_txt}; }}
QPushButton:pressed {{ background: {accent}; color: {sel_txt}; }}
QLineEdit, QComboBox, QSpinBox, QDateEdit, QPlainTextEdit, QTextEdit {{
    background: {panel}; color: {text}; border: 1px solid {accent}; border-radius: 4px; padding: 5px;
    selection-background-color: {accent}; selection-color: {sel_txt};
}}
QComboBox QAbstractItemView {{ background: {panel}; color: {text}; selection-background-color: {accent}; selection-color: {sel_txt}; }}
QLabel {{ background: transparent; color: {text}; }}
QTabWidget::pane {{ border: 1px solid {accent}; }}
QTabBar::tab {{ background: {panel}; color: {sub}; padding: 8px 16px; border: 1px solid {accent}; }}
QTabBar::tab:selected {{ background: {accent}; color: {sel_txt}; }}
QTableWidget, QTableView {{
    background: {row}; alternate-background-color: {row_alt};
    color: {text}; gridline-color: {accent}; border: 1px solid {accent};
    selection-background-color: {accent}; selection-color: {sel_txt};
}}
QTableWidget::item, QTableView::item {{ color: {text}; padding: 4px; background: transparent; }}
QTableWidget::item:alternate, QTableView::item:alternate {{ background: {row_alt}; color: {text}; }}
QTableWidget::item:selected, QTableView::item:selected {{ background: {accent}; color: {sel_txt}; }}
QHeaderView::section {{
    background: {panel}; color: {hdr_c}; border: none;
    border-bottom: 2px solid {hdr_c}; padding: 6px; font-weight: bold;
}}
QTableCornerButton::section {{ background: {panel}; border: none; }}
QScrollBar:vertical {{ background: {panel}; width: 10px; }}
QScrollBar::handle:vertical {{ background: {accent}; border-radius: 5px; min-height: 30px; }}
QScrollBar:horizontal {{ background: {panel}; height: 10px; }}
QScrollBar::handle:horizontal {{ background: {accent}; border-radius: 5px; min-width: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QCheckBox {{ color: {text}; background: transparent; }}
QCheckBox::indicator {{ width: 16px; height: 16px; border: 1px solid {accent}; background: {panel}; }}
QCheckBox::indicator:checked {{ background: {ok_c}; border-color: {ok_c}; }}
QGroupBox {{ border: 1px solid {accent}; border-radius: 6px; margin-top: 12px; color: {hdr_c}; }}
QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 4px; }}
QStatusBar {{ background: {panel}; color: {sub}; border-top: 1px solid {accent}; }}
QToolTip {{ background: {panel}; color: {text}; border: 1px solid {accent}; }}
QSplitter::handle {{ background: {accent}; }}
QProgressBar {{ background: {panel}; border: 1px solid {accent}; border-radius: 4px; color: {text}; text-align: center; }}
QProgressBar::chunk {{ background: {accent}; }}
"""


def set_dark(v):
    global DARK
    DARK = bool(v)
    app = QApplication.instance()
    qss = _build(DARK)
    if app is not None:
        app.setStyleSheet(qss)
        for w in app.allWidgets():
            try:
                if "FITINTEL_THEME" in (w.styleSheet() or ""):
                    w.setStyleSheet(qss)
            except Exception:
                pass


def set_theme(name):
    """Alias: accepts 'dark'/'light'/'тёмная'/'светлая'."""
    n = str(name).strip().lower()
    set_dark(n in ("dark", "тёмная", "темная", "1", "true"))


def apply_theme(app=None):
    apply(app)


def is_dark():
    return DARK


def apply(app=None):
    app = app or QApplication.instance()
    if app is not None:
        app.setStyleSheet(_build(DARK))


def widget_style(*a, **kw):
    return _build(DARK)


def table_style(*a, **kw):
    return _build(DARK)


def card_style(*a, **kw):
    panel = N_PANEL if DARK else L_PANEL
    accent = N_CYAN if DARK else L_ACCENT
    return f"QFrame {{ background: {panel}; border: 1px solid {accent}; border-radius: 8px; }}"


def banner_style(ok=True, *a, **kw):
    if DARK:
        c = N_GREEN if ok else N_RED
        txt = "#050510"
    else:
        c = "#dcfce7" if ok else "#fee2e2"
        txt = L_GREEN if ok else L_RED
    return f"QLabel {{ background: {c}; color: {txt}; border-radius: 6px; padding: 8px; font-weight: bold; }}"


def fg(*a, **kw):      return N_TEXT if DARK else L_TEXT
def sub(*a, **kw):     return N_SUB if DARK else L_SUB
def bg(*a, **kw):      return N_BG if DARK else L_BG
def panel(*a, **kw):   return N_PANEL if DARK else L_PANEL
def accent(*a, **kw):  return N_CYAN if DARK else L_ACCENT
def ok_color(*a, **kw):  return N_GREEN if DARK else L_GREEN
def err_color(*a, **kw): return N_RED if DARK else L_RED
