"""CLI entry point.

  voxflow            run the daemon (tray + overlay)
  voxflow toggle     start/stop dictation   (bind this to your hotkey)
  voxflow cancel     discard current recording
  voxflow quit       stop the daemon
"""

from __future__ import annotations

import sys

from .ipc import VERBS, send_command


def main() -> int:
    args = sys.argv[1:]
    if not args or args[0] == "daemon":
        from .app import run_daemon
        return run_daemon()

    verb = args[0]
    if verb not in VERBS:
        print(__doc__, file=sys.stderr)
        return 2
    if not send_command(verb):
        print("voxflow: daemon not running — start it with "
              "'systemctl --user start voxflow' or just 'voxflow'",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
