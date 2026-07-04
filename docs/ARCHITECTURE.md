# VoxFlow architecture

## Overview

VoxFlow is a single long-running Qt daemon plus a thin CLI client that
talks to it over a unix socket. This split exists because global hotkeys
on Wayland belong to the compositor: KDE runs `voxflow toggle` for you,
and that command just pokes the daemon.

```
 Plasma shortcut ──▶ voxflow toggle ──▶ unix socket (QLocalServer)
                                             │
                     ┌───────────────────────▼───────────────────────┐
                     │                VoxFlow daemon                  │
                     │                                                │
                     │  Recorder ──▶ Transcriber ──▶ Injector         │
                     │  (sounddevice) (faster-whisper) (ydotool)      │
                     │                                                │
                     │  Overlay pill (PySide6)     Tray icon          │
                     └────────────────────────────────────────────────┘
```

## Modules

| Module | Responsibility |
|---|---|
| `__main__.py` | CLI dispatch: no args → daemon; verb → IPC client |
| `ipc.py` | `QLocalServer`/`QLocalSocket` on socket `voxflow-ipc`; verbs: toggle, start, stop, cancel, quit |
| `config.py` | TOML config at `~/.config/voxflow/config.toml`, written with commented defaults on first run |
| `recorder.py` | PortAudio input stream (16 kHz mono float32); accumulates chunks; publishes live RMS level for the waveform |
| `transcriber.py` | STT backends behind `make_transcriber(cfg)`: `FasterWhisperTranscriber` (CTranslate2, CPU) and `WhisperCppTranscriber` (pywhispercpp, Vulkan GPU); both expose `transcribe(np.ndarray) -> str` |
| `injector.py` | `type` via `ydotool type`, or `paste` via `wl-copy` + Ctrl+V with clipboard restore; `check_ydotool()` health probe |
| `overlay.py` | Frameless translucent always-on-top pill, QPainter-drawn: live waveform (listening), pulsing dots (transcribing), error flash |
| `app.py` | Wires everything: tray states, state machine (idle → listening → transcribing → inject), background model warm-up |

## Threading model

The Qt event loop owns all UI. Audio arrives on PortAudio's callback
thread (guarded list append + an atomic-enough float for the level).
Transcription runs in a plain `threading.Thread`; results come back to
the main thread via Qt signals (`transcription_done` /
`transcription_failed`), which are queued connections across threads.

## Design decisions

- **ydotool over wtype**: wtype needs the `zwp_virtual_keyboard_v1`
  protocol, which KWin does not expose to arbitrary clients; ydotool
  synthesizes events at the kernel uinput level and works on every
  compositor. Cost: the `ydotoold` daemon and `input` group membership.
- **Two STT backends**: CTranslate2 has no ROCm backend, so
  faster-whisper is CPU int8 (near-realtime for `small` + VAD on modern
  CPUs). The `whisper.cpp` backend (pywhispercpp built with
  `GGML_VULKAN=1`) gives AMD/Intel GPU acceleration through Vulkan
  without ROCm. Both implement one method, selected by
  `make_transcriber(cfg)` from `[model] backend`.
- **Daemon + IPC rather than in-app hotkey**: there is no portable way
  for a Wayland client to grab a global hotkey; delegating to the
  compositor's shortcut system is the reliable path and lets users pick
  any key without VoxFlow caring.
- **Model warm-up at startup**: the first `WhisperModel` construction
  (and one-time download) happens in a background thread at daemon
  start, so the first dictation doesn't stall.

## Extension points

- Alternative STT backend: add a class with `transcribe(np.ndarray) -> str`
  and a branch in `make_transcriber`.
- Streaming/partial results: swap the stop-then-transcribe pipeline for
  chunked transcription fed from the recorder queue.
- Post-processing (punctuation fixes, custom vocabulary, snippets):
  transform the text in `app._on_transcribed` before injection.
