"""Application configuration and paths."""

import json
import os
import sys
from pathlib import Path

try:
    import winreg
except ImportError:
    winreg = None


def get_data_dir() -> Path:
    """Get the application data directory. Creates it if it doesn't exist.
    
    Uses %LOCALAPPDATA%\\HAMAL\\ on Windows for installer compatibility.
    This keeps user data separate from Program Files (read-only).
    """
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        data_dir = Path(local_app_data) / "HAMAL"
    else:
        # Fallback for non-Windows or missing env var
        data_dir = Path.home() / ".hamal"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_settings_path() -> Path:
    """Get the path to the JSON settings file."""
    return get_data_dir() / "settings.json"


# Default settings used when no settings file exists yet
_DEFAULT_SETTINGS = {
    "minimize_to_tray": False,
    "run_on_startup": False,
    "log_filters": [
        {"prefix": "", "match_type": "contains", "color": "#a6e3a1", "enabled": False},
        {"prefix": "", "match_type": "contains", "color": "#89b4fa", "enabled": False},
        {"prefix": "", "match_type": "contains", "color": "#f9e2af", "enabled": False},
        {"prefix": "", "match_type": "contains", "color": "#f38ba8", "enabled": False},
        {"prefix": "", "match_type": "contains", "color": "#cba6f7", "enabled": False},
    ],
}


def load_settings() -> dict:
    """Load settings from disk. Returns defaults for missing keys."""
    path = get_settings_path()
    settings = dict(_DEFAULT_SETTINGS)
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Only keep known keys to avoid stale data
            for key in _DEFAULT_SETTINGS:
                if key in data:
                    settings[key] = data[key]
        except (OSError, json.JSONDecodeError):
            pass  # Fall back to defaults on any read error
    return settings


def save_settings(settings: dict) -> None:
    """Persist settings to disk."""
    path = get_settings_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
    except OSError:
        pass  # Best-effort: ignore write errors


def get_database_path() -> Path:
    """Get the SQLite database file path."""
    return get_data_dir() / "hamal.db"


def get_logs_dir() -> Path:
    """Get the logs directory."""
    logs_dir = get_data_dir() / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir


def get_project_logs_dir(project_id: int) -> Path:
    """Get the logs directory for a specific project."""
    project_logs_dir = get_logs_dir() / str(project_id)
    project_logs_dir.mkdir(parents=True, exist_ok=True)
    return project_logs_dir


def set_run_on_startup(enabled: bool) -> bool:
    """Enable or disable 'Run on Startup' via Windows Registry.
    
    Returns True if successful, False otherwise.
    """
    if winreg is None:
        return False

    app_name = "HAMAL"

    # Get the actual path to the executable
    if getattr(sys, 'frozen', False):
        # Running as compiled EXE
        app_path = f'"{sys.executable}"'
    else:
        # Running as script
        exe_path = Path(sys.executable)
        # Try to use pythonw.exe instead of python.exe to hide the console window
        if exe_path.name.lower() == "python.exe":
            pythonw = exe_path.with_name("pythonw.exe")
            if pythonw.exists():
                exe_path = pythonw
                
        app_path = f'"{exe_path}" "{Path(__file__).parents[2] / "hamal" / "main.py"}"'

    try:
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)

        if enabled:
            winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, app_path)
        else:
            try:
                winreg.DeleteValue(key, app_name)
            except FileNotFoundError:
                pass  # Already gone

        winreg.CloseKey(key)
        return True
    except OSError:
        return False


# Application constants
APP_NAME = "H.A.M.A.L"
APP_VERSION = "1.0.0"

# Default entry file patterns to look for when adding a project
# pylint: disable=duplicate-code
DEFAULT_ENTRY_PATTERNS = [
    "main.py",
    "bot.py",
    "app.py",
    "run.py",
    "__main__.py",
]

# Venv detection paths (Windows)
VENV_PYTHON_PATHS = [
    ".venv/Scripts/python.exe",
    "venv/Scripts/python.exe",
]
