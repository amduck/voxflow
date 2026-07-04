#!/usr/bin/env bash
# VoxFlow installer for CachyOS / Arch (KDE Plasma Wayland)
set -euo pipefail

APP_DIR="$HOME/.local/share/voxflow"
BIN_DIR="$HOME/.local/bin"
UNIT_DIR="$HOME/.config/systemd/user"
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "==> Installing system packages (pacman)"
sudo pacman -S --needed --noconfirm python ydotool wl-clipboard portaudio

echo "==> Creating virtualenv at $APP_DIR/venv"
mkdir -p "$APP_DIR" "$BIN_DIR" "$UNIT_DIR"
python -m venv "$APP_DIR/venv"
"$APP_DIR/venv/bin/pip" install --upgrade pip -q
"$APP_DIR/venv/bin/pip" install -q faster-whisper sounddevice numpy PySide6

echo "==> Installing VoxFlow package"
cp -r "$SRC_DIR/voxflow" "$APP_DIR/"

echo "==> Creating launcher: $BIN_DIR/voxflow"
cat > "$BIN_DIR/voxflow" <<EOF
#!/usr/bin/env bash
exec "$APP_DIR/venv/bin/python" -m voxflow "\$@"
EOF
chmod +x "$BIN_DIR/voxflow"
# The package must be importable from the venv:
SITE_PKGS="$("$APP_DIR/venv/bin/python" - <<'PY'
import site; print(site.getsitepackages()[0])
PY
)"
ln -sfn "$APP_DIR/voxflow" "$SITE_PKGS/voxflow"

echo "==> Installing systemd user service"
cp "$SRC_DIR/voxflow.service" "$UNIT_DIR/"
systemctl --user daemon-reload
systemctl --user enable --now voxflow.service

echo "==> Enabling ydotool daemon (needed to type into apps on Wayland)"
systemctl --user enable --now ydotool.service || {
  echo "    NOTE: if this failed, check 'systemctl --user status ydotool'"
}

if ! groups | grep -qw input; then
  echo "==> Adding you to the 'input' group (needed by ydotool/uinput)"
  sudo usermod -aG input "$USER"
  NEED_RELOGIN=1
fi

echo
echo "============================================================"
echo " VoxFlow installed."
echo
echo " Final step — bind your hotkey in KDE:"
echo "   System Settings → Keyboard → Shortcuts → Add New → Command:"
echo "     $BIN_DIR/voxflow toggle"
echo "   then assign e.g. Meta+H."
echo
echo " First dictation downloads the Whisper model (~460 MB for"
echo " 'small') to ~/.cache/huggingface — after that it's fully"
echo " offline."
if [ "${NEED_RELOGIN:-0}" = "1" ]; then
  echo
  echo " ⚠ You were added to the 'input' group — LOG OUT AND BACK IN"
  echo "   (or reboot) before dictating, or ydotool cannot type."
fi
echo "============================================================"
