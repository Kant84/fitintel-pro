"""FitIntel Pro — Theme manager (light/dark)"""

DARK = False


def set_dark(value: bool):
    global DARK
    DARK = bool(value)


def is_dark() -> bool:
    return DARK


def fg() -> str:
    return "#f1f5f9" if DARK else "#0f172a"


def sub() -> str:
    return "#94a3b8" if DARK else "#64748b"


def table_style() -> str:
    if DARK:
        return ("QTableWidget { background: #1e293b; color: #e2e8f0; border: 1px solid #334155; "
                "border-radius: 8px; gridline-color: #334155; alternate-background-color: #24304a; } "
                "QHeaderView::section { background: #0f172a; color: #cbd5e1; padding: 10px; "
                "font-weight: 600; border: none; border-bottom: 1px solid #334155; } "
                "QTableCornerButton::section { background: #0f172a; } "
                "QTableWidget::item:selected { background: #065f46; }")
    return ("QTableWidget { background: #ffffff; color: #0f172a; border: 1px solid #e2e8f0; "
            "border-radius: 8px; gridline-color: #f1f5f9; } "
            "QHeaderView::section { background: #f8fafc; padding: 10px; font-weight: 600; "
            "border: none; border-bottom: 1px solid #e2e8f0; }")


def card_style() -> str:
    if DARK:
        return ("background: #1e293b; color: #f1f5f9; border: 1px solid #334155; "
                "border-radius: 8px; padding: 14px; min-width: 140px;")
    return ("background: #ffffff; border: 1px solid #e2e8f0; "
            "border-radius: 8px; padding: 14px; min-width: 140px;")


def banner_style() -> str:
    if DARK:
        return ("background: #3b2f0b; color: #fcd34d; border: 1px solid #a16207; "
                "border-radius: 8px; padding: 10px; font-size: 13px;")
    return ("background: #fffbeb; border: 1px solid #fde68a; "
            "border-radius: 8px; padding: 10px; font-size: 13px;")


def widget_style() -> str:
    """Общий стиль контейнера вкладки."""
    if DARK:
        return ("QWidget { background: #0f172a; color: #e2e8f0; } "
                "QGroupBox { color: #e2e8f0; border: 1px solid #334155; border-radius: 8px; "
                "margin-top: 12px; padding-top: 10px; } "
                "QGroupBox::title { subcontrol-origin: margin; left: 10px; } "
                "QLabel { color: #e2e8f0; } "
                "QLineEdit, QComboBox { background: #1e293b; color: #e2e8f0; "
                "border: 1px solid #475569; border-radius: 6px; padding: 6px; }")
    return ""
