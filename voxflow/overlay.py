"""Floating overlay pill — Wispr-Flow-style waveform while dictating."""

from __future__ import annotations

import math
from collections import deque

from PySide6.QtCore import Qt, QTimer, QRectF
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget

PILL_W, PILL_H = 320, 72
N_BARS = 24


class Overlay(QWidget):
    """Frameless, translucent, always-on-top pill.

    States: 'listening' (live waveform), 'transcribing' (pulsing dots),
    'error' (message flash). Hidden when idle.
    """

    def __init__(self, accent: str = "#7c6cf2"):
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setFixedSize(PILL_W, PILL_H)

        self.accent = QColor(accent)
        self.state = "listening"
        self.message = ""
        self._levels: deque[float] = deque([0.05] * N_BARS, maxlen=N_BARS)
        self._phase = 0.0
        self._level_source = lambda: 0.0

        self._timer = QTimer(self)
        self._timer.setInterval(33)  # ~30 fps
        self._timer.timeout.connect(self._tick)

    def set_level_source(self, fn) -> None:
        """fn() -> float in 0..1, polled while listening."""
        self._level_source = fn

    def show_state(self, state: str, message: str = "") -> None:
        self.state = state
        self.message = message
        if state == "listening":
            self._levels.extend([0.05] * N_BARS)
        if not self.isVisible():
            self.show()
        if not self._timer.isActive():
            self._timer.start()

    def hide_overlay(self) -> None:
        self._timer.stop()
        self.hide()

    def _tick(self) -> None:
        self._phase += 0.15
        if self.state == "listening":
            lvl = max(0.05, min(1.0, float(self._level_source())))
            self._levels.append(lvl)
        self.update()

    # ------------------------------------------------------------- painting

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Pill background with subtle border.
        rect = QRectF(1, 1, self.width() - 2, self.height() - 2)
        p.setPen(QPen(QColor(255, 255, 255, 28), 1))
        p.setBrush(QColor(18, 18, 24, 235))
        p.drawRoundedRect(rect, PILL_H / 2 - 1, PILL_H / 2 - 1)

        if self.state == "listening":
            self._paint_waveform(p)
            self._paint_label(p, "Listening")
            self._paint_dot(p, self.accent, pulse=True)
        elif self.state == "transcribing":
            self._paint_dots(p)
            self._paint_label(p, "Transcribing…")
            self._paint_dot(p, QColor("#f2a93c"), pulse=True)
        elif self.state == "error":
            self._paint_label(p, self.message or "Error", big=True,
                              color=QColor("#f26c6c"))
        p.end()

    def _paint_dot(self, p: QPainter, color: QColor, pulse: bool) -> None:
        r = 5 + (1.5 * (0.5 + 0.5 * math.sin(self._phase * 2)) if pulse else 0)
        c = QColor(color)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(c)
        p.drawEllipse(QRectF(26 - r / 2, self.height() / 2 - r / 2, r, r))

    def _paint_label(self, p: QPainter, text: str, big: bool = False,
                     color: QColor | None = None) -> None:
        p.setPen(color or QColor(235, 235, 245, 210))
        f = QFont("Sans Serif", 10 if not big else 11)
        f.setWeight(QFont.Weight.DemiBold)
        p.setFont(f)
        if big:
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, text)
        else:
            p.drawText(QRectF(42, 0, 110, self.height()),
                       Qt.AlignmentFlag.AlignVCenter, text)

    def _paint_waveform(self, p: QPainter) -> None:
        x0, x1 = 140, self.width() - 26
        w = (x1 - x0) / N_BARS
        cy = self.height() / 2
        p.setPen(Qt.PenStyle.NoPen)
        for i, lvl in enumerate(self._levels):
            h = 4 + lvl * (self.height() - 30)
            a = int(90 + 165 * (i / N_BARS))  # fade older bars
            c = QColor(self.accent)
            c.setAlpha(a)
            p.setBrush(c)
            bw = max(2.0, w * 0.55)
            p.drawRoundedRect(QRectF(x0 + i * w, cy - h / 2, bw, h),
                              bw / 2, bw / 2)

    def _paint_dots(self, p: QPainter) -> None:
        cy = self.height() / 2
        cx0 = 175
        p.setPen(Qt.PenStyle.NoPen)
        for i in range(3):
            k = 0.5 + 0.5 * math.sin(self._phase * 2 - i * 0.9)
            r = 4 + 3 * k
            c = QColor(self.accent)
            c.setAlpha(int(120 + 135 * k))
            p.setBrush(c)
            p.drawEllipse(QRectF(cx0 + i * 26 - r, cy - r, 2 * r, 2 * r))
