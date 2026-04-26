"""Icon resources from hamal."""

import sys
from pathlib import Path

import customtkinter as ctk
from PIL import Image


def get_icons_dir() -> Path:
    """Get the icons directory path, works both in dev and packaged app."""
    # When running as packaged app
    if getattr(sys, 'frozen', False):
        base = Path(sys._MEIPASS)  # pylint: disable=protected-access
        return base / "assets" / "icons"

    # When running in development
    current_file = Path(__file__).resolve()
    return current_file.parent / "assets" / "icons"


class Icons:
    """Manages application icons."""

    _icons: dict = {}
    _loaded: bool = False

    @classmethod
    def load(cls):
        """Load all icons into memory."""
        if cls._loaded:
            return

        icon_names = [
            "play", "stop", "plus", "settings",
            "trash", "logs", "folder", "clear"
        ]

        icons_dir = get_icons_dir()
        print(f"[Icons] Loading from: {icons_dir}")

        for name in icon_names:
            path = icons_dir / f"{name}.png"
            try:
                if path.exists():
                    img = Image.open(path)
                    cls._icons[name] = ctk.CTkImage(
                        light_image=img,
                        dark_image=img,
                        size=(18, 18)
                    )
                    print(f"[Icons] Loaded: {name}")
                else:
                    print(f"[Icons] Not found: {path}")
            except Exception as e:  # pylint: disable=broad-exception-caught
                print(f"[Icons] Error loading {name}: {e}")

        cls._loaded = True

    @classmethod
    def get(cls, name: str) -> ctk.CTkImage | None:
        """Get an icon by name."""
        if not cls._loaded:
            cls.load()
        return cls._icons.get(name)


# Text fallback symbols (used if icons fail to load)
class Symbols:
    """Fallback text symbols."""
    # pylint: disable=too-few-public-methods
    PLAY = "▶"
    STOP = "■"
    PLUS = "+"
    SETTINGS = "⚙"
    TRASH = "✕"
    LOGS = "📋"
    FOLDER = "📂"
    CLEAR = "🗑"
