"""Local speech-to-text via faster-whisper (CTranslate2). No network, no keys.

Models are downloaded once to ~/.cache/huggingface and then used offline.
Swappable: implement transcribe(audio) -> str with any other backend
(e.g. whisper.cpp via pywhispercpp for AMD Vulkan acceleration).
"""

from __future__ import annotations

import numpy as np


class Transcriber:
    def __init__(self, model_size: str, device: str, compute_type: str,
                 language: str | None):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.language = language
        self._model = None

    def ensure_loaded(self) -> None:
        if self._model is None:
            from faster_whisper import WhisperModel
            self._model = WhisperModel(
                self.model_size, device=self.device,
                compute_type=self.compute_type,
            )

    def transcribe(self, audio: np.ndarray) -> str:
        """audio: float32 mono @ 16 kHz."""
        if audio.size < 1600:  # <0.1 s — ignore accidental taps
            return ""
        self.ensure_loaded()
        segments, _info = self._model.transcribe(
            audio,
            language=self.language,
            beam_size=5,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 400},
            condition_on_previous_text=False,
        )
        return " ".join(s.text.strip() for s in segments).strip()
