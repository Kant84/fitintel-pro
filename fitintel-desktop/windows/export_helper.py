# -*- coding: utf-8 -*-
"""Экспорт таблиц: XLSX / PDF (DejaVu) / обёртки 1С."""
import windows.theme as theme
from paths import ASSETS
from app_logging import log


def export_table_xlsx(parent, headers, rows, filename, title=""):
    from PyQt6.QtWidgets import QFileDialog, QMessageBox
    from datetime import datetime
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill
    except ImportError:
        QMessageBox.warning(parent, "XLSX", "Не установлен openpyxl")
        return
    path, _ = QFileDialog.getSaveFileName(
        parent, "Сохранить XLSX", f"{filename}_{datetime.now():%Y%m%d}.xlsx", "Excel (*.xlsx)")
    if not path:
        return
    try:
        wb = Workbook()
        ws = wb.active
        ws.title = (title or filename)[:31]
        ws.cell(1, 1, title or filename).font = Font(bold=True, size=14)
        ws.cell(2, 1, f"Дата: {datetime.now():%Y-%m-%d %H:%M}")
        try:
            user = (getattr(parent, "user_data", None) or {}).get("username", "")
            if user:
                ws.cell(3, 1, f"Пользователь: {user}")
        except Exception:
            pass
        header_row = 5
        fill = PatternFill("solid", fgColor=("1E293B" if theme.DARK else "F1F5F9"))
        font = Font(bold=True, color=("FFFFFF" if theme.DARK else "0F172A"))
        for c, h in enumerate(headers, 1):
            cell = ws.cell(header_row, c, h)
            cell.font = font
            cell.fill = fill
        for r, row in enumerate(rows, header_row + 1):
            for c, val in enumerate(row, 1):
                ws.cell(r, c, "" if val is None else str(val))
        for c in range(1, len(headers) + 1):
            max_len = 10
            for r in range(1, ws.max_row + 1):
                v = ws.cell(r, c).value
                if v:
                    max_len = max(max_len, len(str(v)))
            ws.column_dimensions[ws.cell(1, c).column_letter].width = min(max_len + 2, 60)
        wb.save(path)
        QMessageBox.information(parent, "Готово", f"Сохранено: {path}")
        log.info("XLSX сохранён: %s", path)
    except Exception as e:
        QMessageBox.warning(parent, "XLSX", f"Ошибка: {e}")
        log.error("XLSX: %s", e)


def export_table_pdf(parent, headers, rows, filename, title=""):
    from PyQt6.QtWidgets import QFileDialog, QMessageBox
    from datetime import datetime
    ttf_path = ASSETS / "DejaVuSans.ttf"
    if not ttf_path.exists():
        QMessageBox.warning(parent, "PDF",
            f"Не найден {ttf_path}\nПоложите DejaVuSans.ttf в assets/ и перезапустите клиент.")
        return
    try:
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib import colors
        from reportlab.lib.units import mm
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
    except ImportError:
        QMessageBox.warning(parent, "PDF", "Не установлен reportlab")
        return
    pdfmetrics.registerFont(TTFont("DejaVu", str(ttf_path)))
    path, _ = QFileDialog.getSaveFileName(
        parent, "Сохранить PDF", f"{filename}_{datetime.now():%Y%m%d}.pdf", "PDF (*.pdf)")
    if not path:
        return
    try:
        doc = SimpleDocTemplate(path, pagesize=landscape(A4),
                                leftMargin=10*mm, rightMargin=10*mm,
                                topMargin=10*mm, bottomMargin=10*mm)
        story = [
            Paragraph(f"<font name='DejaVu' size='14'><b>{title or filename}</b></font>"),
            Spacer(1, 4*mm),
            Paragraph(f"<font name='DejaVu' size='9'>Дата: {datetime.now():%Y-%m-%d %H:%M}</font>"),
            Spacer(1, 6*mm),
        ]
        data = [headers] + [[str(v or "") for v in row] for row in rows]
        table = Table(data, repeatRows=1)
        table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), "DejaVu"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E293B")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F1F5F9")]),
        ]))
        story.append(table)
        doc.build(story)
        QMessageBox.information(parent, "Готово", f"Сохранено: {path}")
        log.info("PDF сохранён: %s", path)
    except Exception as e:
        QMessageBox.warning(parent, "PDF", f"Ошибка: {e}")
        log.error("PDF: %s", e)


def export_nomenclature_1c(parent, tariffs):
    from windows.accounting_tab import _1c_export_nomenclature
    _1c_export_nomenclature(parent)


def export_counterparties_1c(parent, clients):
    from windows.accounting_tab import _1c_export_counterparties
    _1c_export_counterparties(parent)


def make_export_panel(parent_widget, data_fn):
    """Панель кнопок XLSX/PDF/1С. data_fn() -> (headers, rows, title) или client_list для 1С."""
    from PyQt6.QtWidgets import QHBoxLayout, QPushButton, QMessageBox
    hb = QHBoxLayout()
    hb.addStretch()
    def _do(fmt):
        from windows.export_helper import export_table_xlsx, export_table_pdf, export_counterparties_1c
        try:
            if fmt == "1c":
                clients = data_fn("1c") if data_fn.__code__.co_argcount else []
                export_counterparties_1c(parent_widget, clients or [])
                return
            headers, rows, title = data_fn(fmt)
            if fmt == "xlsx":
                export_table_xlsx(parent_widget, headers, rows, "export", title)
            else:
                export_table_pdf(parent_widget, headers, rows, "export", title)
        except (RuntimeError, Exception) as e:
            QMessageBox.warning(parent_widget, "Экспорт", str(e)[:200])
    for fmt, label in [("xlsx", "XLSX"), ("pdf", "PDF"), ("1c", "1С")]:
        b = QPushButton(label)
        b.setStyleSheet("QPushButton { background: #f1f5f9; color: #475569; "
                        "border: 1px solid #cbd5e1; border-radius: 6px; "
                        "padding: 6px 12px; font-weight: 600; }")
        b.clicked.connect(lambda _, f=fmt: _do(f))
        hb.addWidget(b)
    return hb