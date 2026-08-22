# -*- coding: utf-8 -*-
"""Universal print helper: preview dialog -> printer or PDF."""
from PyQt6.QtPrintSupport import QPrinter, QPrintPreviewDialog
from PyQt6.QtGui import QTextDocument
from PyQt6.QtWidgets import QMessageBox, QPushButton, QTableWidget

def print_html(parent, title, html):
    doc = QTextDocument()
    doc.setHtml("<h2>%s</h2>%s" % (title, html))
    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    dlg = QPrintPreviewDialog(printer, parent)
    dlg.paintRequested.connect(doc.print_)
    dlg.exec()

def table_to_html(tbl):
    heads = []
    for c in range(tbl.columnCount()):
        it = tbl.horizontalHeaderItem(c)
        heads.append(it.text() if it else "")
    rows = ["<tr>" + "".join("<th>%s</th>" % h for h in heads) + "</tr>"]
    for r in range(tbl.rowCount()):
        cells = []
        for c in range(tbl.columnCount()):
            it = tbl.item(r, c)
            cells.append("<td>%s</td>" % (it.text() if it else ""))
        rows.append("<tr>" + "".join(cells) + "</tr>")
    return "<table border=1 cellspacing=0 cellpadding=4 width=100%>%s</table>" % "".join(rows)

def print_table(parent, title, tbl):
    print_html(parent, title, table_to_html(tbl))

def add_print_button(tab, title="FitIntel Pro"):
    btn = QPushButton("🖨 Печать")
    def _p():
        tbls = tab.findChildren(QTableWidget)
        if not tbls:
            QMessageBox.information(tab, "Печать", "На этом экране нет таблицы для печати")
            return
        tbl = max(tbls, key=lambda t: t.rowCount())
        print_table(tab, title, tbl)
    btn.clicked.connect(_p)
    lay = tab.layout()
    if lay is not None:
        lay.addWidget(btn)
