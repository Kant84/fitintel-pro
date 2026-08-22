# -*- coding: utf-8 -*-
"""Simple neon line chart (fact + forecast), no external deps."""
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QPen, QColor
from PyQt6.QtCore import Qt

class ChartWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._fact = []
        self._fore = []
        self.setMinimumHeight(280)

    def set_data(self, fact, fore=None):
        self._fact = fact or []
        self._fore = fore or []
        self.update()

    def paintEvent(self, ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        m = 44
        p.fillRect(self.rect(), QColor("#0a0a18"))
        vals = [v for _, v in self._fact] + [v for _, v in self._fore]
        if not vals:
            p.setPen(QColor("#9a9ac0"))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Нет данных — построй прогноз")
            p.end(); return
        vmax = (max(vals) or 1) * 1.15
        n, nf = len(self._fact), len(self._fore)
        total = max(n + nf - 1, 1)
        def pt(i, v):
            x = m + (w - 2 * m) * (i / total)
            y = h - m - (h - 2 * m) * (v / vmax)
            return x, y
        p.setPen(QPen(QColor("#1c1c3a"), 1))
        for i in range(5):
            y = m + (h - 2 * m) * i / 4
            p.drawLine(m, int(y), w - m, int(y))
        if n > 1:
            p.setPen(QPen(QColor("#00f0ff"), 2))
            for i in range(1, n):
                x1, y1 = pt(i - 1, self._fact[i - 1][1]); x2, y2 = pt(i, self._fact[i][1])
                p.drawLine(int(x1), int(y1), int(x2), int(y2))
        if nf:
            p.setPen(QPen(QColor("#ff2bd6"), 2, Qt.PenStyle.DashLine))
            prev = pt(n - 1, self._fact[-1][1]) if n else None
            for i in range(nf):
                cur = pt(n + i, self._fore[i][1])
                if prev:
                    p.drawLine(int(prev[0]), int(prev[1]), int(cur[0]), int(cur[1]))
                prev = cur
        if n and nf:
            x, _ = pt(n - 1, 0)
            p.setPen(QPen(QColor("#39ff14"), 1, Qt.PenStyle.DotLine))
            p.drawLine(int(x), m, int(x), h - m)
            p.setPen(QColor("#39ff14"))
            p.drawText(int(x) + 5, m + 12, "сегодня")
        p.setPen(QColor("#9a9ac0"))
        p.drawText(4, m, str(round(vmax / 1.15, 1)))
        p.drawText(m, h - 8, "голубой = факт, розовый пунктир = прогноз")
        p.end()


class HeatmapWidget(QWidget):
    """Посещения: день недели (Пн..Вс) x час (0..23)."""
    DOWS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._grid = None
        self.setMinimumHeight(240)

    def set_grid(self, grid):
        self._grid = grid
        self.update()

    def paintEvent(self, ev):
        p = QPainter(self)
        w, h = self.width(), self.height()
        p.fillRect(self.rect(), QColor("#0a0a18"))
        if not self._grid:
            p.setPen(QColor("#9a9ac0"))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Нет данных")
            p.end(); return
        mx = max(max(r) for r in self._grid) or 1
        left, top, bottom = 40, 10, 24
        cw_ = (w - left - 10) / 24.0
        ch_ = (h - top - bottom) / 7.0
        for d in range(7):
            pg_row = (d + 1) % 7  # Пн=1..Вс=0 в Postgres DOW
            for hr in range(24):
                v = self._grid[pg_row][hr]
                t = v / mx
                col = QColor(int(10 + 245 * t), int(10 + 20 * t), int(24 + 190 * t))
                p.fillRect(int(left + hr * cw_), int(top + d * ch_), max(int(cw_) - 1, 1), max(int(ch_) - 1, 1), col)
        p.setPen(QColor("#9a9ac0"))
        for d in range(7):
            p.drawText(4, int(top + d * ch_ + ch_ / 2 + 4), self.DOWS[d])
        for hr in range(0, 24, 3):
            p.drawText(int(left + hr * cw_), h - 8, str(hr))
        p.end()
