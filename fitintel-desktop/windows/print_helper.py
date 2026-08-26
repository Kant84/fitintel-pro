# -*- coding: utf-8 -*-
"""Universal print helper v2: preview -> printer, plus direct PDF export. Errors are visible."""
import traceback
from PyQt6.QtPrintSupport import QPrinter, QPrintPreviewDialog
from PyQt6.QtGui import QTextDocument
from PyQt6.QtWidgets import QMessageBox, QPushButton, QTableWidget, QFileDialog, QHBoxLayout, QWidget






_DLG_STYLE = (
    "QDialog { border: 2px solid #E6007E; background: #0f172a; }"
    " QToolBar { background: #1e293b; border: none; spacing: 4px; }"
    " QToolButton { color: #e2e8f0; background: #1e293b; border: 1px solid #334155; border-radius: 4px; padding: 4px; }"
    " QToolButton:hover { border: 1px solid #E6007E; }"
    " QComboBox, QSpinBox { background: #0f172a; color: #e2e8f0; border: 1px solid #E6007E; padding: 2px; }"
    " QLabel { color: #e2e8f0; }"
)

def _doc_print(doc, printer):
    fn = getattr(doc, "print_", None) or getattr(doc, "print")
    fn(printer)

def _err(parent, where, e):
    traceback.print_exc()
    QMessageBox.critical(parent, "Печать", f"{where}:\n{e}")


def print_html(parent, title, html):
    try:
        doc = QTextDocument(parent)
        doc.setHtml(f"<h2>{title}</h2>{html}")
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        dlg = QPrintPreviewDialog(printer, parent)
        dlg.setStyleSheet(_DLG_STYLE)
        dlg.paintRequested.connect(lambda pr, d=doc: _doc_print(d, pr))
        dlg.exec()
    except Exception as e:
        _err(parent, "Предпросмотр печати", e)


def table_to_html(tbl):
    import html as _html
    heads = []
    for c in range(tbl.columnCount()):
        it = tbl.horizontalHeaderItem(c)
        heads.append(_html.escape(it.text() if it else ""))
    rows = ["<tr>" + "".join(f"<th>{h}</th>" for h in heads) + "</tr>"]
    for r in range(tbl.rowCount()):
        cells = []
        for c in range(tbl.columnCount()):
            it = tbl.item(r, c)
            cells.append(f"<td>{_html.escape(it.text() if it else '')}</td>")
        rows.append("<tr>" + "".join(cells) + "</tr>")
    body = "".join(rows)
    return f"<table border='1' cellspacing='0' cellpadding='4' width='100%'>{body}</table>"


def print_table(parent, title, tbl):
    print_html(parent, title, table_to_html(tbl))


def export_pdf(parent, title, tbl):
    try:
        path, _ = QFileDialog.getSaveFileName(parent, "Сохранить в PDF", f"{title}.pdf", "PDF (*.pdf)")
        if not path:
            return
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(path)
        doc = QTextDocument()
        doc.setHtml(f"<h2>{title}</h2>{table_to_html(tbl)}")
        _doc_print(doc, printer)
        QMessageBox.information(parent, "PDF", "Сохранено:\n" + path)
    except Exception as e:
        _err(parent, "Экспорт PDF", e)


def _find_table(tab):
    tbls = tab.findChildren(QTableWidget)
    if not tbls:
        return None
    return max(tbls, key=lambda t: t.rowCount())


def add_print_button(tab, title="FitIntel Pro"):
    box = QWidget()
    h = QHBoxLayout(box)
    h.setContentsMargins(0, 0, 0, 0)
    btn_p = QPushButton("🖨 Печать")
    btn_pdf = QPushButton("📄 В PDF")

    def _get_tbl():
        tbl = _find_table(tab)
        if tbl is None or tbl.rowCount() == 0:
            QMessageBox.information(tab, "Печать", "На этом экране нет данных для печати")
            return None
        return tbl

    def _p():
        tbl = _get_tbl()
        if tbl is not None:
            print_table(tab, title, tbl)

    def _pdf():
        tbl = _get_tbl()
        if tbl is not None:
            export_pdf(tab, title, tbl)

    btn_p.clicked.connect(_p)
    btn_pdf.clicked.connect(_pdf)
    h.addWidget(btn_p)
    h.addWidget(btn_pdf)
    lay = tab.layout()
    if lay is not None:
        lay.addWidget(box)
