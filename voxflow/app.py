"""VoxFlow daemon: tray icon + overlay + record→transcribe→inject pipeline."""

from __future__ import annotations

import sys
import threading

from PySide6.QtCore import QObject, QTimer, Qt, Signal
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from .config import CONFIG_FILE, load_config
from .injector import InjectionError, check_ydotool, inject
from .ipc import IpcServer
from .overlay import Overlay
from .recorder import Recorder
from .transcriber import Transcriber


def _mic_icon(color: str) -> QIcon:
    pm = QPixmap(64, 64)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor(color), 6, Qt.PenStyle.SolidLine,
               Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    p.setBrush(QColor(color))
    p.drawRoundedRect(24, 8, 16, 28, 8, 8)          # capsule
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawArc(16, 20, 32, 26, 180 * 16, 180 * 16)   # cradle
    p.drawLine(32, 46, 32, 56)                       # stem
    p.end()
    return QIcon(pm)


class VoxFlowApp(QObject):
    transcription_done = Signal(str)
    transcription_failed = Signal(str)

    def __init__(self, app: QApplication):
        super().__init__()
        self.app = app
        self.cfg = load_config()
        self.busy = False  # transcription in flight

        self.recorder = Recorder(self.cfg.sample_rate, self.cfg.audio_device)
        self.transcriber = Transcriber(
            self.cfg.model_size, self.cfg.device,
            self.cfg.compute_type, self.cfg.language,
        )

        self.overlay = Overlay(self.cfg.accent)
        self.overlay.set_level_source(lambda: self.recorder.level)

        self._build_tray()
        self.ipc = IpcServer(self.handle_command)

        self.transcription_done.connect(self._on_transcribed)
        self.transcription_failed.connect(self._on_failed)

        # Warm the model in the background so the first dictation is snappy.
        threading.Thread(target=self._warm_model, daemon=True).start()

        problem = check_ydotool()
        if problem:
            self.tray.showMessage("VoxFlow", problem,
                                  QSystemTrayIcon.MessageIcon.Warning, 8000)

    # ----------------------------------------------------------------- tray

    def _build_tray(self) -> None:
        self.icon_idle = _mic_icon("#b8b8c8")
        self.icon_rec = _mic_icon("#f25c5c")
        self.icon_busy = _mic_icon("#f2a93c")

        self.tray = QSystemTrayIcon(self.icon_idle)
        self.tray.setToolTip("VoxFlow — voice dictation (idle)")
        menu = QMenu()
        act_toggle = QAction("Toggle dictation", menu)
        act_toggle.triggered.connect(self.toggle)
        act_cancel = QAction("Cancel recording", menu)
        act_cancel.triggered.connect(self.cancel)
        act_config = QAction("Open config file", menu)
        act_config.triggered.connect(self._open_config)
        act_quit = QAction("Quit", menu)
        act_quit.triggered.connect(self.quit)
        menu.addAction(act_toggle)
        menu.addAction(act_cancel)
        menu.addSeparator()
        menu.addAction(act_config)
        menu.addAction(act_quit)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(
            lambda reason: self.toggle()
            if reason == QSystemTrayIcon.ActivationReason.Trigger else None)
        self.tray.show()

    def _open_config(self) -> None:
        import subprocess
        subprocess.Popen(["xdg-open", str(CONFIG_FILE)])

    # ------------------------------------------------------------- commands

    def handle_command(self, verb: str) -> None:
        {"toggle": self.toggle, "start": self.start, "stop": self.stop,
         "cancel": self.cancel, "quit": self.quit}[verb]()

    def toggle(self) -> None:
        if self.recorder.recording:
            self.stop()
        elif not self.busy:
            self.start()

    def start(self) -> None:
        if self.recorder.recording or self.busy:
            return
        try:
            self.recorder.start()
        except Exception as e:
            self._flash_error(f"Mic error: {e}")
            return
        self.tray.setIcon(self.icon_rec)
        self.tray.setToolTip("VoxFlow — listening")
        if self.cfg.overlay:
            self.overlay.show_state("listening")

    def stop(self) -> None:
        if not self.recorder.recording:
            return
        audio = self.recorder.stop()
        self.busy = True
        self.tray.setIcon(self.icon_busy)
        self.tray.setToolTip("VoxFlow — transcribing")
        if self.cfg.overlay:
            self.overlay.show_state("transcribing")
        threading.Thread(target=self._transcribe_worker, args=(audio,),
                         daemon=True).start()

    def cancel(self) -> None:
        if self.recorder.recording:
            self.recorder.stop()
        self._reset_ui()

    def quit(self) -> None:
        self.cancel()
        self.app.quit()

    # -------------------------------------------------------------- pipeline

    def _warm_model(self) -> None:
        try:
            self.transcriber.ensure_loaded()
        except Exception as e:
            print(f"voxflow: model load failed: {e}", file=sys.stderr)

    def _transcribe_worker(self, audio) -> None:
        try:
            text = self.transcriber.transcribe(audio)
            self.transcription_done.emit(text)
        except Exception as e:
            self.transcription_failed.emit(str(e))

    def _on_transcribed(self, text: str) -> None:
        self.busy = False
        if not text:
            self._flash_error("No speech detected")
            return
        try:
            inject(text, self.cfg.injection_method, self.cfg.type_delay_ms)
        except InjectionError as e:
            self._flash_error(str(e))
            return
        self._reset_ui()

    def _on_failed(self, msg: str) -> None:
        self.busy = False
        self._flash_error(msg)

    def _flash_error(self, msg: str) -> None:
        print(f"voxflow: {msg}", file=sys.stderr)
        if self.cfg.overlay:
            self.overlay.show_state("error", msg[:60])
            QTimer.singleShot(2500, self._reset_ui)
        else:
            self.tray.showMessage("VoxFlow", msg,
                                  QSystemTrayIcon.MessageIcon.Warning, 4000)
            self._reset_ui()

    def _reset_ui(self) -> None:
        self.busy = False
        self.overlay.hide_overlay()
        self.tray.setIcon(self.icon_idle)
        self.tray.setToolTip("VoxFlow — voice dictation (idle)")


def run_daemon() -> int:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("VoxFlow")
    app.setDesktopFileName("voxflow")
    _vox = VoxFlowApp(app)  # noqa: F841 — keep alive
    return app.exec()
