"""Log handling and persistence for project output."""

from datetime import datetime
from pathlib import Path
from typing import Optional, TextIO

from hamal.core.config import get_project_logs_dir


class LogHandler:
    """
    Handles log capture and persistence for a single project.
    Creates a new log file for each run.
    """

    def __init__(self, project_id: int):
        self.project_id = project_id
        self.log_file: Optional[TextIO] = None
        self.log_path: Optional[Path] = None

    def start_logging(self) -> Path:
        """Start a new log file for this run. Returns the log file path."""
        logs_dir = get_project_logs_dir(self.project_id)

        # Generate timestamp-based filename
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.log_path = logs_dir / f"{timestamp}.log"

        # Open file for writing (will be closed by stop_logging)
        try:
            self.log_file = open(self.log_path, "w", encoding="utf-8", buffering=1)
        except OSError as e:
            self.log_file = None
            raise IOError(f"Failed to open log file {self.log_path}: {e}") from e

        # Write header
        self.log_file.write(f"=== H.A.M.A.L Log Started: {datetime.now().isoformat()} ===\n")
        self.log_file.write(f"=== Project ID: {self.project_id} ===\n\n")

        return self.log_path

    def write_line(self, line: str, stream: str = "stdout"):
        """Write a line to the log file."""
        if self.log_file is None:
            return

        timestamp = datetime.now().strftime("%H:%M:%S")
        prefix = "[ERR]" if stream == "stderr" else "[OUT]"
        self.log_file.write(f"{timestamp} {prefix} {line}\n")

    def stop_logging(self):
        """Close the log file."""
        if self.log_file is not None:
            self.log_file.write(f"\n=== H.A.M.A.L Log Ended: {datetime.now().isoformat()} ===\n")
            self.log_file.close()
            self.log_file = None

    def get_current_log_path(self) -> Optional[Path]:
        """Get the path to the current log file."""
        return self.log_path

    def get_all_log_files(self) -> list[Path]:
        """Get all log files for this project, sorted by date (newest first)."""
        logs_dir = get_project_logs_dir(self.project_id)
        log_files = list(logs_dir.glob("*.log"))
        log_files.sort(reverse=True)  # Newest first
        return log_files
