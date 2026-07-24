"""Single-instance guard for PromptBoard.

The first process claims a fixed, per-user local socket and listens for
``activate`` pings. A second start connects to that socket, sends the ping so
the already running window comes to the front, and then exits without spawning a
second window or a second tray icon.

If a previous instance crashed without cleaning up, ``listen()`` fails with
``AddressInUseError``; we then remove the stale name once and retry.

Uses ``QLocalServer``/``QLocalSocket`` (named pipes on Windows) — the same
pattern SoftwareCenter (file-bricks) uses. No third-party dependency.
"""
from __future__ import annotations

import getpass
import logging
from typing import Callable, Optional

from PySide6 import QtCore, QtNetwork

logger = logging.getLogger(__name__)

_PING = b"activate"
_TIMEOUT_MS = 300


def _default_server_name() -> str:
    try:
        user = getpass.getuser()
    except Exception:  # noqa: BLE001
        user = "default"
    return f"PromptBoard-singleton-{user}"


class SingleInstance(QtCore.QObject):
    """Coordinate a single running PromptBoard instance via a local socket."""

    def __init__(
        self,
        server_name: Optional[str] = None,
        parent: Optional[QtCore.QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._server_name = server_name or _default_server_name()
        self._server: Optional[QtNetwork.QLocalServer] = None
        self._on_activate: Optional[Callable[[], None]] = None

    @property
    def server_name(self) -> str:
        return self._server_name

    def is_another_running(self, timeout_ms: int = _TIMEOUT_MS) -> bool:
        """Return True if another instance already listens, and ping it.

        The ping makes the primary instance bring its window to the front.
        """
        socket = QtNetwork.QLocalSocket()
        socket.connectToServer(self._server_name)
        if not socket.waitForConnected(timeout_ms):
            return False
        socket.write(_PING)
        socket.waitForBytesWritten(timeout_ms)
        socket.flush()
        socket.disconnectFromServer()
        if socket.state() != QtNetwork.QLocalSocket.LocalSocketState.UnconnectedState:
            socket.waitForDisconnected(timeout_ms)
        return True

    def start_server(self, on_activate: Callable[[], None]) -> bool:
        """Listen as the primary instance. Returns True on success."""
        self._on_activate = on_activate
        server = QtNetwork.QLocalServer(self)
        if not server.listen(self._server_name):
            if (
                server.serverError()
                == QtNetwork.QAbstractSocket.SocketError.AddressInUseError
            ):
                QtNetwork.QLocalServer.removeServer(self._server_name)
                server.listen(self._server_name)
        if not server.isListening():
            logger.warning(
                "Single-Instance-Server konnte nicht starten: %s", server.errorString()
            )
            return False
        server.newConnection.connect(self._handle_new_connection)
        self._server = server
        return True

    def _handle_new_connection(self) -> None:
        if self._server is None:
            return
        connection = self._server.nextPendingConnection()
        if connection is None:
            return
        # Any connection means "a second start happened" — payload is advisory.
        if connection.waitForReadyRead(_TIMEOUT_MS):
            connection.readAll()
        if self._on_activate is not None:
            try:
                self._on_activate()
            except Exception:  # noqa: BLE001
                logger.exception("Single-Instance-Aktivierungs-Callback fehlgeschlagen")
        connection.disconnectFromServer()
        connection.deleteLater()

    def stop(self) -> None:
        if self._server is not None:
            self._server.close()
            QtNetwork.QLocalServer.removeServer(self._server_name)
            self._server = None
