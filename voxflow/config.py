"""Configuration handling: ~/.config/voxflow/config.toml"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "voxflow"
CONFIG_FILE = CONFIG_DIR / "config.toml"

DEFAULT_CONFIG = """\
# VoxFlow configuration

[model]
# tiny, base, small, medium, large-v3, or distil-* variants.
# 'small' is a good CPU sweet spot; 'base' if your CPU is older.
size = "small"
# "auto" detects language; or force e.g. "en" for better speed/accuracy.
language = "en"
# cpu (CTranslate2 has no ROCm support; keep cpu on AMD GPUs)
device = "cpu"
# int8 is fastest on CPU with negligible accuracy loss.
compute_type = "int8"

[injection]
# "type"  : ydotool types each character (works everywhere, incl. terminals)
# "paste" : copies to clipboard and sends Ctrl+V (much faster for long text,
#           but terminals need Ctrl+Shift+V — use "type" if you dictate into
#           terminals a lot). Original clipboard is restored afterwards.
method = "type"
# Delay in ms between ydotool keystrokes when method = "type" (0 = fastest).
type_delay_ms = 2

[audio]
sample_rate = 16000
# Input device name substring, or "" for system default.
device = ""

[ui]
# Show the floating overlay pill while recording/transcribing.
overlay = true
# Accent colour of the overlay (any hex colour).
accent = "#7c6cf2"
"""


@dataclass
class Config:
    model_size: str = "small"
    language: str = "en"
    device: str = "cpu"
    compute_type: str = "int8"
    injection_method: str = "type"
    type_delay_ms: int = 2
    sample_rate: int = 16000
    audio_device: str = ""
    overlay: bool = True
    accent: str = "#7c6cf2"
    raw: dict = field(default_factory=dict)


def load_config() -> Config:
    if not CONFIG_FILE.exists():
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(DEFAULT_CONFIG)
    with open(CONFIG_FILE, "rb") as f:
        data = tomllib.load(f)

    model = data.get("model", {})
    inj = data.get("injection", {})
    audio = data.get("audio", {})
    ui = data.get("ui", {})

    lang = model.get("language", "en")
    return Config(
        model_size=model.get("size", "small"),
        language=None if lang in ("auto", "") else lang,
        device=model.get("device", "cpu"),
        compute_type=model.get("compute_type", "int8"),
        injection_method=inj.get("method", "type"),
        type_delay_ms=int(inj.get("type_delay_ms", 2)),
        sample_rate=int(audio.get("sample_rate", 16000)),
        audio_device=audio.get("device", ""),
        overlay=bool(ui.get("overlay", True)),
        accent=ui.get("accent", "#7c6cf2"),
        raw=data,
    )
