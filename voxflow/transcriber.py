"""Local speech-to-text backends. No network after model download, no keys.

Backends (config: [model] backend = ...):
  faster-whisper — CTranslate2, CPU int8. Best accuracy/speed on CPU.
  whisper.cpp    — pywhispercpp. Build with GGML_VULKAN=1 for AMD/Intel
                   GPU acceleration via Vulkan (no ROCm needed).
"""

from __future__ import annotations

import numpy as np

MIN_SAMPLES = 1600  # <0.1 s @ 16 kHz — ignore accidental taps


class FasterWhisperTranscriber:
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
        if audio.size < MIN_SAMPLES:
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


class WhisperCppTranscriber:
    """whisper.cpp via pywhispercpp — GPU on AMD when built with Vulkan.

    Install (Arch):
      sudo pacman -S --needed cmake gcc vulkan-headers vulkan-icd-loader \
                              shaderc glslang
      GGML_VULKAN=1 pip install --no-binary :all: --no-cache-dir pywhispercpp
    Models auto-download to ~/.local/share/pywhispercpp/models.
    """

    def __init__(self, model_size: str, language: str | None):
        self.model_size = model_size
        self.language = language or "auto"
        self._model = None

    def ensure_loaded(self) -> None:
        if self._model is None:
            import os
            from pywhispercpp.model import Model
            self._model = Model(
                self.model_size,
                language=self.language,
                n_threads=max(2, (os.cpu_count() or 4) - 2),
                print_progress=False,
                print_realtime=False,
                redirect_whispercpp_logs_to=None,
            )

    def transcribe(self, audio: np.ndarray) -> str:
        if audio.size < MIN_SAMPLES:
            return ""
        self.ensure_loaded()
        segments = self._model.transcribe(audio)
        return " ".join(s.text.strip() for s in segments).strip()


def make_transcriber(cfg):
    """Factory: pick a backend from the loaded Config."""
    if cfg.backend == "whisper.cpp":
        return WhisperCppTranscriber(cfg.model_size, cfg.language)
    return FasterWhisperTranscriber(
        cfg.model_size, cfg.device, cfg.compute_type, cfg.language)


# Backwards-compatible alias (pre-0.2 name).
Transcriber = FasterWhisperTranscriber
