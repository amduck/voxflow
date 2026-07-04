"""Unix-socket IPC so a Plasma global shortcut can toggle the daemon.

The daemon owns a QLocalServer; `voxflow toggle` connects and sends a verb.
"""

from __future__ import annotations

import sys

from PySide6.QtNetwork import QLocalServer, QLocalSocket

SOCKET_NAME = "voxflow-ipc"
VERBS = ("toggle", "start", "stop", "cancel", "quit")


def send_command(verb: str) -> bool:
    """Client side. Returns True if the daemon received the command."""
    sock = QLocalSocket()
    sock.connectToServer(SOCKET_NAME)
    if not sock.waitForConnected(1500):
        return False
    sock.write(verb.encode())
    sock.flush()
    sock.waitForBytesWritten(1000)
    sock.disconnectFromServer()
    return True


class IpcServer:
    """Daemon side. Calls handler(verb) for each received command."""

    def __init__(self, handler):
        self.handler = handler
        QLocalServer.removeServer(SOCKET_NAME)  # clear stale socket
        self.server = QLocalServer()
        if not self.server.listen(SOCKET_NAME):
            print(f"voxflow: cannot listen on {SOCKET_NAME}: "
                  f"{self.server.errorString()}", file=sys.stderr)
            sys.exit(1)
        self.server.newConnection.connect(self._on_connection)

    def _on_connection(self) -> None:
        sock = self.server.nextPendingConnection()
        sock.readyRead.connect(lambda: self._on_ready(sock))

    def _on_ready(self, sock) -> None:
        verb = bytes(sock.readAll()).decode(errors="replace").strip()
        if verb in VERBS:
            self.handler(verb)
