"""Microphone capture via sounddevice (PortAudio → PipeWire)."""

from __future__ import annotations

import threading

import numpy as np
import sounddevice as sd


class Recorder:
    """Collects mono float32 audio; exposes a live RMS level for the UI."""

    def __init__(self, sample_rate: int = 16000, device: str = ""):
        self.sample_rate = sample_rate
        self.device = device or None
        self._chunks: list[np.ndarray] = []
        self._stream: sd.InputStream | None = None
        self._lock = threading.Lock()
        self.level: float = 0.0  # 0..1-ish live RMS, read by the overlay

    @property
    def recording(self) -> bool:
        return self._stream is not None

    def start(self) -> None:
        if self._stream is not None:
            return
        self._chunks = []
        self.level = 0.0

        def callback(indata, frames, time_info, status):
            mono = indata[:, 0].copy()
            with self._lock:
                self._chunks.append(mono)
            # Perceptual-ish level for the waveform animation.
            rms = float(np.sqrt(np.mean(mono**2)))
            self.level = min(1.0, rms * 18.0)

        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32",
            device=self.device,
            callback=callback,
        )
        self._stream.start()

    def stop(self) -> np.ndarray:
        """Stop and return the captured audio as float32 mono."""
        if self._stream is None:
            return np.empty(0, dtype=np.float32)
        self._stream.stop()
        self._stream.close()
        self._stream = None
        self.level = 0.0
        with self._lock:
            if not self._chunks:
                return np.empty(0, dtype=np.float32)
            audio = np.concatenate(self._chunks)
            self._chunks = []
        return audio
