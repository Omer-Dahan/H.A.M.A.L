"""Single instance enforcement using a Named Mutex and a local TCP socket.

How it works:
  1. Try to acquire a Windows Named Mutex.
  2. If the mutex is already held, send a FOCUS command to the existing
     instance via a local TCP socket and exit.
  3. If we acquired the mutex successfully, start a listener thread so we
     can receive FOCUS commands from future instances.
"""

import ctypes
import socket
import threading
import logging
import sys

logger = logging.getLogger(__name__)

# Unique identifiers for this application
_IS_FROZEN = getattr(sys, "frozen", False)
_MUTEX_NAME = "Global\\HAMAL_SingleInstance_Mutex" if _IS_FROZEN else "Global\\HAMAL_SingleInstance_Mutex_Dev"
_IPC_PORT = 19847 if _IS_FROZEN else 19848
_IPC_HOST = "127.0.0.1"
_IPC_CMD_FOCUS = b"FOCUS\n"


class SingleInstanceManager:
    """Ensures only one instance of H.A.M.A.L runs at a time."""

    def __init__(self):
        self._mutex_handle = None
        self._listener_thread: threading.Thread | None = None
        self._on_focus_requested = None  # Callback set by MainWindow

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def ensure_single(self) -> bool:
        """Try to become the primary instance.

        Returns:
            True  – we are the primary instance (proceed normally).
            False – another instance is running; we sent FOCUS to it.
        """
        if self._try_acquire_mutex():
            # We are the primary instance – start listening for focus commands
            self._start_listener()
            return True

        # Another instance is running – tell it to focus
        self._send_focus_command()
        return False

    def set_focus_callback(self, callback):
        """Register the function that will bring the window to the front."""
        self._on_focus_requested = callback

    def release(self):
        """Release the mutex (call on application exit)."""
        if self._mutex_handle:
            ctypes.windll.kernel32.ReleaseMutex(self._mutex_handle)
            ctypes.windll.kernel32.CloseHandle(self._mutex_handle)
            self._mutex_handle = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _try_acquire_mutex(self) -> bool:
        """Attempt to create/acquire a Windows Named Mutex.

        Returns True if we successfully became the owner.
        """
        try:
            handle = ctypes.windll.kernel32.CreateMutexW(
                None,   # default security attributes
                True,   # request initial ownership
                _MUTEX_NAME,
            )
            last_error = ctypes.windll.kernel32.GetLastError()
            # ERROR_ALREADY_EXISTS = 183
            if handle and last_error != 183:
                self._mutex_handle = handle
                return True
            # Another instance already owns the mutex
            if handle:
                ctypes.windll.kernel32.CloseHandle(handle)
            return False
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning("Mutex check failed (%s) – proceeding without singleton guard.", exc)
            return True  # Fail-safe: let the app start

    def _send_focus_command(self):
        """Send a FOCUS command to the already-running instance."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(2)
                sock.connect((_IPC_HOST, _IPC_PORT))
                sock.sendall(_IPC_CMD_FOCUS)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning("Could not send FOCUS command: %s", exc)

    def _start_listener(self):
        """Start a background thread that listens for FOCUS commands."""
        self._listener_thread = threading.Thread(
            target=self._listen_loop,
            name="SingleInstanceListener",
            daemon=True,
        )
        self._listener_thread.start()

    def _listen_loop(self):
        """Background loop: accept connections and handle commands."""
        try:
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind((_IPC_HOST, _IPC_PORT))
            server.listen(5)
            server.settimeout(1)  # Allow graceful shutdown checks
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning("IPC listener could not start: %s", exc)
            return

        while True:
            try:
                conn, _ = server.accept()
                with conn:
                    data = conn.recv(64)
                    if _IPC_CMD_FOCUS.strip() in data:
                        self._handle_focus()
            except socket.timeout:
                continue
            except Exception as exc:  # pylint: disable=broad-exception-caught
                logger.debug("IPC listener error: %s", exc)
                break

    def _handle_focus(self):
        """Invoke the registered focus callback (thread-safe via after())."""
        if self._on_focus_requested:
            try:
                self._on_focus_requested()
            except Exception as exc:  # pylint: disable=broad-exception-caught
                logger.warning("Focus callback error: %s", exc)
