"""System tray icon for H.A.M.A.L – shown when the window is minimized to tray."""

import threading
from typing import Callable

import pystray
from PIL import Image

from hamal.ui.icons import get_icons_dir
from hamal.core.config import APP_NAME


def _load_tray_image() -> Image.Image:
    """Load the tray icon image (prefers 32px PNG, falls back to 16px or ICO)."""
    icons_dir = get_icons_dir()
    for name in ("32.png", "48.png", "16.png", "icon.ico"):
        path = icons_dir / name
        if path.exists():
            img = Image.open(path)
            # pystray works best with RGBA
            return img.convert("RGBA")
    # Fallback: plain blue square so the tray entry is still visible
    img = Image.new("RGBA", (32, 32), color=(137, 180, 250, 255))
    return img


class TrayIcon:
    """Manages a system-tray icon for the application.

    Parameters
    ----------
    on_show:
        Called (on the Tk thread via `after`) when the user asks to restore
        the window.
    on_exit:
        Called (on the Tk thread via `after`) when the user chooses Exit from
        the tray menu.
    """

    def __init__(self, on_show: Callable, on_exit: Callable) -> None:
        self._on_show = on_show
        self._on_exit = on_exit
        self._icon: pystray.Icon | None = None
        self._thread: threading.Thread | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def show(self) -> None:
        """Start the tray icon in a background thread (idempotent)."""
        if self._icon is not None:
            return  # Already running

        menu = pystray.Menu(
            pystray.MenuItem("Show " + APP_NAME, self._handle_show, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit", self._handle_exit),
        )

        self._icon = pystray.Icon(
            name=APP_NAME,
            icon=_load_tray_image(),
            title=APP_NAME,
            menu=menu,
        )

        self._thread = threading.Thread(target=self._icon.run, daemon=True, name="TrayIcon")
        self._thread.start()

    def hide(self) -> None:
        """Stop and remove the tray icon."""
        if self._icon is not None:
            self._icon.stop()
            self._icon = None

    # ------------------------------------------------------------------
    # Internal handlers (called from the pystray thread)
    # ------------------------------------------------------------------

    def _handle_show(self, icon, item) -> None:  # pylint: disable=unused-argument
        """User clicked 'Show' – hide tray first, then restore window."""
        self.hide()
        self._on_show()

    def _handle_exit(self, icon, item) -> None:  # pylint: disable=unused-argument
        """User clicked 'Exit' – hide tray, then quit the app."""
        self.hide()
        self._on_exit()
