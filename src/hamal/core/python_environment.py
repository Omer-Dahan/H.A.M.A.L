"""Detection and creation of Python environments for projects.

Two jobs:

* find a real ``python.exe`` on this machine (``py`` launcher first, then ``PATH``);
* create ``<project>\\venv\\Scripts\\python.exe`` with ``<python> -m venv venv``.

If no Python exists at all, :func:`install_python` can install one through the
Windows Package Manager (``winget``) – an explicit, user-confirmed action.

Every long operation has an ``*_async`` twin that runs on a daemon thread so the
Tk main loop keeps breathing. **Callbacks fire on the worker thread** – marshal
back with ``widget.after(0, ...)`` before touching any widget.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

# pylint: disable=logging-fstring-interpolation
logger = logging.getLogger(__name__)


# Environment folder name – matches the scanner's VENV_INTERPRETER_PATHS.
VENV_DIR_NAME = "venv"

# Package installed when no Python is found at all.
WINGET_PYTHON_ID = "Python.Python.3.12"

_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

_PROBE_TIMEOUT = 20      # locating an interpreter
_CREATE_TIMEOUT = 300    # python -m venv
_INSTALL_TIMEOUT = 1800  # winget download + install

_PROBE_CODE = "import sys; print(sys.executable)"

# Cached result of find_system_python(); None means "not probed yet".
_cached_python: Optional[str] = None
_cache_lock = threading.Lock()


@dataclass
class EnvResult:
    """Outcome of an environment operation."""

    success: bool
    message: str
    python_path: Optional[str] = None
    # True when the operation stopped because no Python is installed at all.
    needs_python_install: bool = False


# ----------------------------------------------------------------------
# Process helper
# ----------------------------------------------------------------------

def _run(cmd: list[str], cwd: Optional[str] = None, timeout: int = _PROBE_TIMEOUT):
    """Run a command silently and return the CompletedProcess (never raises on exit code)."""
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    return subprocess.run(  # pylint: disable=subprocess-run-check
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        env=env,
        creationflags=_NO_WINDOW,
        check=False,
    )


# ----------------------------------------------------------------------
# Finding a system interpreter
# ----------------------------------------------------------------------

def _resolve_interpreter(cmd: list[str]) -> Optional[str]:
    """Ask a candidate command for its real ``sys.executable``.

    Returns an absolute path, or None if the command is missing or is the
    Microsoft Store alias stub (which prints nothing and opens the Store).
    """
    try:
        proc = _run([*cmd, "-c", _PROBE_CODE])
    except (OSError, subprocess.SubprocessError) as e:
        logger.debug(f"Interpreter probe failed for {cmd}: {e}")
        return None

    path = (proc.stdout or "").strip().splitlines()
    if proc.returncode != 0 or not path:
        return None

    candidate = Path(path[-1].strip())
    if candidate.is_file():
        return str(candidate)
    return None


def _scan_known_install_dirs() -> Optional[str]:
    """Look for python.exe in the standard installer locations.

    Needed right after a winget install: our own process still has the old
    ``PATH``, so ``py``/``python`` may not be visible until the app restarts.
    """
    roots: list[Path] = []
    local = os.environ.get("LOCALAPPDATA")
    if local:
        roots.append(Path(local) / "Programs" / "Python")
    for var in ("ProgramFiles", "ProgramFiles(x86)"):
        base = os.environ.get(var)
        if base:
            roots.append(Path(base))

    found: list[Path] = []
    for root in roots:
        try:
            if not root.is_dir():
                continue
            for child in root.iterdir():
                if child.is_dir() and child.name.lower().startswith("python"):
                    exe = child / "python.exe"
                    if exe.is_file():
                        found.append(exe)
        except OSError:
            continue

    if not found:
        return None
    # Newest version last alphabetically ("Python312" > "Python39" fails, so sort by digits)
    found.sort(key=lambda p: _version_key(p.parent.name))
    return str(found[-1])


def _version_key(folder_name: str) -> tuple:
    digits = "".join(c for c in folder_name if c.isdigit())
    if not digits:
        return (0, 0)
    # "Python312" -> (3, 12); "Python39" -> (3, 9)
    return (int(digits[0]), int(digits[1:] or 0))


def find_system_python(refresh: bool = False) -> Optional[str]:
    """Return an absolute path to a usable python.exe, or None.

    Priority: the Windows ``py`` launcher, then ``python`` from ``PATH``, then
    the interpreter running this app (dev mode only), then known install dirs.
    Result is cached; pass ``refresh=True`` after installing Python.
    """
    global _cached_python  # pylint: disable=global-statement

    with _cache_lock:
        if _cached_python and not refresh:
            if Path(_cached_python).is_file():
                return _cached_python
            _cached_python = None

    candidates: list[list[str]] = [["py", "-3"], ["py"], ["python"], ["python3"]]

    resolved: Optional[str] = None
    for cmd in candidates:
        resolved = _resolve_interpreter(cmd)
        if resolved:
            break

    if not resolved and not getattr(sys, "frozen", False):
        # Running from source: our own interpreter can build a venv just fine.
        if Path(sys.executable).is_file() and "python" in Path(sys.executable).name.lower():
            resolved = sys.executable

    if not resolved:
        resolved = _scan_known_install_dirs()

    with _cache_lock:
        _cached_python = resolved
    return resolved


def is_winget_available() -> bool:
    """True if the Windows Package Manager is on PATH."""
    return shutil.which("winget") is not None


# ----------------------------------------------------------------------
# venv paths
# ----------------------------------------------------------------------

def venv_python_path(project_folder: str) -> Path:
    """Absolute path of the interpreter inside the project's venv."""
    if os.name == "nt":
        return Path(project_folder) / VENV_DIR_NAME / "Scripts" / "python.exe"
    return Path(project_folder) / VENV_DIR_NAME / "bin" / "python"


def relative_venv_python() -> str:
    """The path we store in the project's Python field, e.g. ``venv\\Scripts\\python.exe``."""
    if os.name == "nt":
        return str(Path(VENV_DIR_NAME) / "Scripts" / "python.exe")
    return str(Path(VENV_DIR_NAME) / "bin" / "python")


# ----------------------------------------------------------------------
# venv creation
# ----------------------------------------------------------------------

def create_venv(project_folder: str, python_exe: Optional[str] = None) -> EnvResult:
    """Create ``<project>/venv`` with ``<python> -m venv venv``.

    An existing, healthy venv is reported as success. An existing but broken
    ``venv`` folder is reported as an error – we never delete it automatically.
    """
    folder = Path(project_folder)
    if not project_folder or not folder.is_dir():
        return EnvResult(False, f"Project folder does not exist:\n{project_folder}")

    target = folder / VENV_DIR_NAME
    interpreter = venv_python_path(project_folder)

    if target.exists():
        if interpreter.is_file():
            return EnvResult(True, "Virtual environment already exists.", str(interpreter))
        return EnvResult(
            False,
            f"A '{VENV_DIR_NAME}' folder already exists but has no interpreter.\n"
            f"Remove or repair it manually:\n{target}",
        )

    python_exe = python_exe or find_system_python()
    if not python_exe:
        return EnvResult(
            False,
            "No Python installation was found on this computer.",
            needs_python_install=True,
        )

    logger.info(f"Creating venv in {folder} using {python_exe}")
    try:
        proc = _run(
            [python_exe, "-m", "venv", VENV_DIR_NAME],
            cwd=str(folder),
            timeout=_CREATE_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return EnvResult(False, "Timed out while creating the virtual environment.")
    except PermissionError:
        return EnvResult(False, f"Permission denied writing to:\n{folder}")
    except (OSError, subprocess.SubprocessError) as e:
        return EnvResult(False, f"Failed to launch Python:\n{e}")

    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()
        detail = detail[-600:] if detail else f"exit code {proc.returncode}"
        return EnvResult(False, f"venv creation failed:\n{detail}")

    if not interpreter.is_file():
        return EnvResult(
            False,
            f"venv reported success but no interpreter was created at:\n{interpreter}",
        )

    logger.info(f"Created venv interpreter at {interpreter}")
    return EnvResult(True, "Virtual environment created.", str(interpreter))


# ----------------------------------------------------------------------
# Python installation (winget)
# ----------------------------------------------------------------------

def install_python() -> EnvResult:
    """Install Python through winget. Requires internet and may need elevation."""
    if not is_winget_available():
        return EnvResult(
            False,
            "Windows Package Manager (winget) is not available.\n"
            "Install Python manually from https://www.python.org/downloads/",
        )

    logger.info(f"Installing {WINGET_PYTHON_ID} via winget")
    try:
        proc = _run(
            [
                "winget", "install",
                "--id", WINGET_PYTHON_ID,
                "--exact",
                "--source", "winget",
                "--accept-package-agreements",
                "--accept-source-agreements",
                "--disable-interactivity",
            ],
            timeout=_INSTALL_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return EnvResult(False, "The Python installation timed out.")
    except (OSError, subprocess.SubprocessError) as e:
        return EnvResult(False, f"Failed to run winget:\n{e}")

    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()
        detail = detail[-600:] if detail else f"exit code {proc.returncode}"
        return EnvResult(False, f"winget could not install Python:\n{detail}")

    python_exe = find_system_python(refresh=True)
    if not python_exe:
        return EnvResult(
            False,
            "Python was installed but could not be located.\n"
            "Restart H.A.M.A.L so it picks up the updated PATH.",
        )
    return EnvResult(True, "Python installed.", python_exe)


# ----------------------------------------------------------------------
# Combined flow + async wrappers
# ----------------------------------------------------------------------

def ensure_environment(
    project_folder: str,
    allow_install: bool = False,
    on_status: Optional[Callable[[str], None]] = None,
) -> EnvResult:
    """Find (or install) Python, then create the project's venv."""

    def status(text: str):
        if on_status:
            on_status(text)

    status("Looking for Python…")
    python_exe = find_system_python()

    if not python_exe:
        if not allow_install:
            return EnvResult(
                False,
                "No Python installation was found on this computer.",
                needs_python_install=True,
            )
        status("Installing Python… this can take a few minutes.")
        install = install_python()
        if not install.success:
            return install
        python_exe = install.python_path

    status("Creating virtual environment…")
    return create_venv(project_folder, python_exe)


def _spawn(fn: Callable[[], EnvResult], on_done: Callable[[EnvResult], None]) -> threading.Thread:
    def worker():
        try:
            result = fn()
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.exception("Environment operation crashed")
            result = EnvResult(False, f"Unexpected error:\n{e}")
        on_done(result)

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    return thread


def ensure_environment_async(
    project_folder: str,
    on_done: Callable[[EnvResult], None],
    allow_install: bool = False,
    on_status: Optional[Callable[[str], None]] = None,
) -> threading.Thread:
    """Background :func:`ensure_environment`. Callbacks run on the worker thread."""
    return _spawn(
        lambda: ensure_environment(project_folder, allow_install, on_status),
        on_done,
    )


def find_system_python_async(
    on_done: Callable[[Optional[str]], None],
    refresh: bool = False,
) -> threading.Thread:
    """Probe for a system Python off the UI thread. Callback runs on the worker thread."""

    def worker():
        try:
            on_done(find_system_python(refresh=refresh))
        except Exception:  # pylint: disable=broad-exception-caught
            logger.exception("Python probe crashed")
            on_done(None)

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    return thread
