# VoxFlow

Local voice dictation for Linux — a Wispr Flow alternative for CachyOS /
KDE Plasma Wayland. Press a hotkey, speak, press again: your words are
typed into whatever app has focus. Fully offline: faster-whisper
(CTranslate2) runs on your CPU, no API keys, no network after the
one-time model download.

## Install

```bash
cd voxflow
chmod +x install.sh
./install.sh
```

Then bind the hotkey: **System Settings → Keyboard → Shortcuts →
Add New → Command or Script** → `~/.local/bin/voxflow toggle` → assign
e.g. `Meta+H`.

If the installer added you to the `input` group, **log out and back in**
once — ydotool can't synthesize keystrokes until then.

## Usage

Press your hotkey (or click the tray mic). A floating pill appears with a
live waveform. Speak. Press the hotkey again — the pill switches to
"Transcribing…" and the text is typed into the focused window. Middle
states are also on the tray icon (grey idle / red recording / amber busy).

CLI verbs: `voxflow toggle | start | stop | cancel | quit`.

## Configuration

`~/.config/voxflow/config.toml` (created on first run, commented):

- `model.size` — `tiny`/`base`/`small`/`medium`/`large-v3`. `small` is the
  CPU sweet spot; drop to `base` on older hardware.
- `model.language` — `"en"` (default), or `"auto"` to detect.
- `injection.method` — `type` (universal, works in terminals) or `paste`
  (Ctrl+V; much faster for long passages, restores your clipboard).
- `ui.accent` — overlay colour.

Restart after editing: `systemctl --user restart voxflow`.

## Notes & troubleshooting

- **AMD GPU**: CTranslate2 has no ROCm backend, so inference is CPU int8 —
  near-realtime for `small` on a modern Ryzen. If you want GPU speed
  later, swap `voxflow/transcriber.py` for whisper.cpp with its Vulkan
  backend (`pywhispercpp`); the interface is one method.
- **Nothing gets typed**: check `ydotool` — `systemctl --user status
  ydotool`, and confirm you're in the `input` group (`groups`).
- **Overlay position**: on Wayland the compositor places windows. If you
  want the pill pinned bottom-centre, add a KWin rule: System Settings →
  Window Management → Window Rules → New → match window class `voxflow`,
  set Position = Force, pick coordinates.
- **Model cache**: `~/.cache/huggingface`. Delete to reclaim space.
- **Logs**: `journalctl --user -u voxflow -f`.

## Documentation

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the design, module
map, threading model, and extension points (alternative STT backends,
streaming, text post-processing).

## Uninstall

```bash
systemctl --user disable --now voxflow ydotool
rm -rf ~/.local/share/voxflow ~/.local/bin/voxflow \
       ~/.config/voxflow ~/.config/systemd/user/voxflow.service
```

## License

MIT — see [LICENSE](LICENSE).
