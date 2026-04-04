"""H.A.M.A.L application entry point with CustomTkinter."""

import sys

import customtkinter as ctk

from hamal.core.config import load_settings, set_run_on_startup
from hamal.core.single_instance import SingleInstanceManager
from hamal.database.database import init_database
from hamal.ui.main_window import MainWindow

# Global singleton manager (kept alive for the lifetime of the process)
_instance_manager = SingleInstanceManager()


def main():
    """Main entry point for H.A.M.A.L."""
    # Configure logging to output to console
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        stream=sys.stdout
    )
    logger = logging.getLogger("hamal.main")
    logger.info("Application starting...")

    # Ensure only one instance runs at a time.
    # If another instance is already running, send it a FOCUS command and exit.
    if not _instance_manager.ensure_single():
        sys.exit(0)

    # Load settings and sync startup registration
    settings = load_settings()
    if settings.get("run_on_startup"):
        set_run_on_startup(True)

    # Initialize database
    init_database()

    # Configure CustomTkinter appearance
    ctk.set_appearance_mode("dark")  # Dark mode
    ctk.set_default_color_theme("blue")  # Blue accent color

    # Create and run application
    app = MainWindow(instance_manager=_instance_manager)
    app.mainloop()

    # Release the mutex on clean exit
    _instance_manager.release()


if __name__ == "__main__":
    main()
