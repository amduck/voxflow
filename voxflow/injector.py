"""Type transcribed text into the focused window on KDE Plasma Wayland.

Uses ydotool (kernel uinput — works on every Wayland compositor).
Requires ydotoold running: `systemctl --user enable --now ydotool.service`.

Methods:
  type  — ydotool types the text (universal, incl. terminals)
  paste — wl-copy + Ctrl+V, original clipboard restored (fast for long text)
"""

from __future__ import annotations

import shutil
import subprocess
import time

CTRL_V = ["29:1", "47:1", "47:0", "29:0"]  # KEY_LEFTCTRL, KEY_V press/release


class InjectionError(RuntimeError):
    pass


def _run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(cmd, check=True, capture_output=True, **kw)
    except FileNotFoundError:
        raise InjectionError(f"'{cmd[0]}' not found — is it installed?")
    except subprocess.CalledProcessError as e:
        err = e.stderr.decode(errors="replace").strip()
        raise InjectionError(f"{cmd[0]} failed: {err}")


def inject(text: str, method: str = "type", type_delay_ms: int = 2) -> None:
    if not text:
        return
    if method == "paste":
        _inject_paste(text)
    else:
        _inject_type(text, type_delay_ms)


def _inject_type(text: str, delay_ms: int) -> None:
    _run(["ydotool", "type", "--key-delay", str(delay_ms), "--", text])


def _inject_paste(text: str) -> None:
    if shutil.which("wl-copy") is None:
        raise InjectionError("wl-clipboard not installed")
    # Save current clipboard (best effort).
    old = None
    try:
        old = subprocess.run(["wl-paste", "--no-newline"],
                             capture_output=True, timeout=2).stdout
    except Exception:
        pass
    _run(["wl-copy", "--", text])
    time.sleep(0.15)  # let the clipboard settle
    _run(["ydotool", "key", *CTRL_V])
    if old is not None:
        time.sleep(0.3)
        try:
            subprocess.run(["wl-copy", "--"], input=old, timeout=2)
        except Exception:
            pass


def check_ydotool() -> str | None:
    """Return a human-readable problem description, or None if OK."""
    if shutil.which("ydotool") is None:
        return "ydotool is not installed (pacman -S ydotool)"
    probe = subprocess.run(["ydotool", "key", "0:0"], capture_output=True)
    if probe.returncode != 0:
        return ("ydotoold daemon not reachable — run "
                "'systemctl --user enable --now ydotool.service'")
    return None
