"""Log panel widget using CustomTkinter - Live logs view."""

import os
import re
import tkinter as tk
from typing import Optional

import customtkinter as ctk

from hamal.core.config import get_project_logs_dir


# Catppuccin Mocha colors
# pylint: disable=duplicate-code
COLORS = {
    "base": "#1e1e2e",
    "surface": "#313244",
    "overlay": "#45475a",
    "text": "#cdd6f4",
    "subtext": "#a6adc8",
    "green": "#a6e3a1",
    "red": "#f38ba8",
    "blue": "#89b4fa",
    "yellow": "#f9e2af",
}


class LogPanel(ctk.CTkFrame):
    """Panel for displaying LIVE project logs."""
    # pylint: disable=too-many-ancestors,too-many-instance-attributes

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)

        self.current_project_id: Optional[int] = None
        self.current_project_name: str = ""
        self.logs: dict[int, list[str]] = {}
        self._custom_filters: list[dict] = []  # set by reload_filters()

        self._setup_ui()

    def _setup_ui(self):
        """Setup the log panel UI."""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # === HEADER ===
        self.header = ctk.CTkFrame(self, fg_color="transparent")
        self.header.grid(row=0, column=0, padx=5, pady=(5, 5), sticky="ew")
        self.header.grid_columnconfigure(0, weight=1)

        # Title with project name
        self.title = ctk.CTkLabel(
            self.header,
            text="Logs",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=COLORS["text"]
        )
        self.title.grid(row=0, column=0, sticky="w", padx=5)

        # Buttons frame
        self.buttons_frame = ctk.CTkFrame(self.header, fg_color="transparent")
        self.buttons_frame.grid(row=0, column=1, sticky="e")
        # Live indicator
        self.live_label = ctk.CTkLabel(
            self.buttons_frame,
            text="● LIVE",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=COLORS["green"]
        )
        self.live_label.pack(side="left", padx=10)

        # Open Folder button
        self.open_folder_btn = ctk.CTkButton(
            self.buttons_frame,
            text="Open Folder",
            font=ctk.CTkFont(size=11),
            width=85,
            height=28,
            corner_radius=4,
            fg_color=COLORS["blue"],
            hover_color="#6994d8",
            text_color="#1e1e2e",
            command=self._on_open_folder
        )
        self.open_folder_btn.pack(side="left", padx=3)

        # Clear button
        self.clear_btn = ctk.CTkButton(
            self.buttons_frame,
            text="Clear",
            font=ctk.CTkFont(size=11),
            width=55,
            height=28,
            corner_radius=4,
            fg_color=COLORS["overlay"],
            hover_color=COLORS["red"],
            text_color=COLORS["text"],
            command=self._clear_logs
        )
        self.clear_btn.pack(side="left", padx=3)

        # === LOG TEXT AREA ===
        self.log_container = ctk.CTkFrame(self, fg_color=COLORS["surface"], corner_radius=8)
        self.log_container.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")
        self.log_container.grid_columnconfigure(0, weight=1)
        self.log_container.grid_rowconfigure(0, weight=1)

        self.log_text = ctk.CTkTextbox(
            self.log_container,
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color=COLORS["base"],
            text_color=COLORS["text"],
            scrollbar_button_color=COLORS["overlay"],
            scrollbar_button_hover_color=COLORS["blue"],
            wrap="none",
            corner_radius=6
        )
        self.log_text.grid(row=0, column=0, padx=3, pady=3, sticky="nsew")
        self.log_text.configure(state="disabled")

        # Configure syntax highlighting tags
        self.log_text.tag_config("timestamp", foreground=COLORS["green"])
        self.log_text.tag_config("file", foreground="#cba6f7") # Mauve
        self.log_text.tag_config("info_lvl", foreground=COLORS["blue"])
        self.log_text.tag_config("warn_lvl", foreground=COLORS["yellow"])
        self.log_text.tag_config("err_lvl", foreground=COLORS["red"])
        self.log_text.tag_config("success_lvl", foreground=COLORS["green"])
        
        self.log_text.tag_config("info", foreground=COLORS["text"])
        self.log_text.tag_config("error", foreground=COLORS["red"])
        self.log_text.tag_config("warn", foreground=COLORS["yellow"])
        self.log_text.tag_config("success", foreground=COLORS["green"])
        self.log_text.tag_config("link", foreground="#89dceb", underline=True)  # Sapphire color

        self._setup_context_menu()

        # Initial message
        self._show_initial_message()

        # === STATUS BAR ===
        self.status_bar = ctk.CTkLabel(
            self,
            text="Select a project to view live logs",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["subtext"],
            anchor="w"
        )
        self.status_bar.grid(row=2, column=0, padx=10, pady=(0, 5), sticky="ew")

    def _setup_context_menu(self):
        """Setup right-click context menu and copy shortcuts for logs."""
        # Create standard tkinter Menu for the context menu
        self.context_menu = tk.Menu(self.winfo_toplevel(), tearoff=False,
                                   bg=COLORS["surface"], fg=COLORS["text"],
                                   activebackground=COLORS["overlay"], activeforeground=COLORS["text"],
                                   relief="flat", borderwidth=1)
        
        self.context_menu.add_command(label="Copy (Ctrl+C)", command=self._copy_selection)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Copy All", command=self._copy_all)

        # Bind events to the textbox
        self.log_text.bind("<Button-3>", self._show_context_menu)
        self.log_text.bind("<Control-c>", lambda e: self._copy_selection())
        # Make the textbox focusable even when disabled
        self.log_text.bind("<Button-1>", lambda e: self.log_text.focus_set())

    def _show_context_menu(self, event):
        """Show context menu on right click."""
        try:
            # Only show if there's text
            if self.log_text.get("1.0", "end-1c").strip() != "":
                self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def _copy_selection(self, _event=None):
        """Copy selected text to clipboard."""
        try:
            # Check if there's a selection
            selected_text = self.log_text.get("sel.first", "sel.last")
            if selected_text:
                self.clipboard_clear()
                self.clipboard_append(selected_text)
                self.update() # Keep clipboard contents
        except tk.TclError:
            pass # No selection
        return "break" # Prevent default behavior
            
    def _copy_all(self):
        """Copy all log text to clipboard."""
        all_text = self.log_text.get("1.0", "end-1c")
        if all_text.strip():
            self.clipboard_clear()
            self.clipboard_append(all_text)
            self.update()

    def _show_initial_message(self):
        """Show initial message when no project is selected."""
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.insert("end", "\n\n    Select a project and click LOG to view live output.\n")
        self.log_text.configure(state="disabled")

    def set_project(self, project_id: int, project_name: str):
        """Set the current project to display live logs for."""
        self.current_project_id = project_id
        self.current_project_name = project_name

        # Update title
        self.title.configure(text=f"Logs - {project_name}")

        # Show live indicator
        self.live_label.configure(text="● LIVE", text_color=COLORS["green"])

        # Update status
        self.status_bar.configure(text=f"Viewing live logs for: {project_name}")

        # Display existing live logs for this project
        self._display_logs()

    def _on_open_folder(self):
        """Open the logs folder in file explorer."""
        if not self.current_project_id:
            return

        logs_dir = get_project_logs_dir(self.current_project_id)
        if logs_dir.exists():
            os.startfile(str(logs_dir))

    def reload_filters(self, filters: list[dict]):
        """Update custom color filters and register their tags.

        Each filter dict has: prefix (str), match_type ('contains'|'starts with'),
        color (hex str), enabled (bool).
        """
        self._custom_filters = [
            f for f in filters
            if f.get("enabled") and f.get("prefix")
        ]
        # Register a unique tag for each active filter
        for i, flt in enumerate(self._custom_filters):
            tag_name = f"custom_filter_{i}"
            self.log_text.tag_config(tag_name, foreground=flt["color"])

    def add_log(self, project_id: int, line: str):
        """Add a live log line for a project."""
        if project_id not in self.logs:
            self.logs[project_id] = []

        self.logs[project_id].append(line)

        # Keep only last 1000 lines
        if len(self.logs[project_id]) > 1000:
            self.logs[project_id] = self.logs[project_id][-1000:]

        # If this is the current project, display the new line
        if project_id == self.current_project_id:
            self._append_line(line)

    def _display_logs(self):
        """Display all live logs for the current project."""
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")

        if self.current_project_id and self.current_project_id in self.logs:
            for line in self.logs[self.current_project_id]:
                self._insert_colored_line(line)
        else:
            self.log_text.insert(
                "end", f"\n    Waiting for output from {self.current_project_name}...\n"
            )
            self.log_text.insert("end", "    Start the project to see live logs.\n")

        self.log_text.configure(state="disabled")
        self.log_text.see("end")

    def _insert_message_with_links(self, text: str, base_tag: str = None):
        """Helper to insert text while processing links."""
        link_pattern = r"(https?://[^\s]+|[a-zA-Z]:\\[^\s]+|/[^\s]+)"
        parts = re.split(link_pattern, text)
        for part in parts:
            if not part:
                continue
            if re.match(link_pattern, part):
                self.log_text.insert("end", part, "link")
            else:
                args = ("end", part) if not base_tag else ("end", part, base_tag)
                self.log_text.insert(*args)

    def _insert_colored_line(self, line: str):
        """Parse a line and insert it with appropriate color tags."""
        # Try to match the specific log format: [Date] filename.py:line Level] Message
        match = re.match(r"^(\[\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2}(?:,\d{3})?\])\s+([^ ]+:\d+)\s+([A-Z]\])(.*)", line)
        if match:
            timestamp, file_info, level, message = match.groups()
            
            # Insert Timestamp (green)
            self.log_text.insert("end", timestamp + " ", "timestamp")
            
            # Insert File path/line (mauve)
            self.log_text.insert("end", file_info + " ", "file")
            
            # Insert Level indicator
            lvl_tag = "info_lvl"
            base_msg_tag = None
            if "W]" in level:
                lvl_tag = "warn_lvl"
                base_msg_tag = "warn" if "⚠️" in message else None
            elif "E]" in level or "F]" in level:
                lvl_tag = "err_lvl"
                base_msg_tag = "error"
            elif "I]" in level:
                lvl_tag = "info_lvl"
                if "✅" in message:
                    base_msg_tag = "success"
                
            self.log_text.insert("end", level, lvl_tag)
            
            # Insert the message body natively and handle links
            self._insert_message_with_links(message, base_msg_tag)
            self.log_text.insert("end", "\n")
            return

        # Fallback parsing for lines that aren't matching the standard log structure
        line_lower = line.lower()

        # ── Custom color filters (user-defined) ──────────────────────
        for i, flt in enumerate(self._custom_filters):
            pattern = flt["prefix"]
            match_type = flt.get("match_type", "contains")
            hit = (
                line_lower.startswith(pattern.lower())
                if match_type == "starts with"
                else pattern.lower() in line_lower
            )
            if hit:
                tag_name = f"custom_filter_{i}"
                self._insert_message_with_links(line, tag_name)
                if not line.endswith("\n"):
                    self.log_text.insert("end", "\n")
                return

        # ── Built-in keyword coloring ─────────────────────────────────
        base_tag = None
        if "error" in line_lower or "traceback" in line_lower or "exception" in line_lower or "failed" in line_lower or "❌" in line:
            base_tag = "error"
        elif "warn" in line_lower or "⚠️" in line:
            base_tag = "warn"
        elif "success" in line_lower or "finished" in line_lower or "done" in line_lower or "✅" in line:
            base_tag = "success"

        self._insert_message_with_links(line, base_tag)
        if not line.endswith("\n"):
            self.log_text.insert("end", "\n")

    def _append_line(self, line: str):
        """Append a single line to the log display."""
        self.log_text.configure(state="normal")
        self._insert_colored_line(line)
        self.log_text.configure(state="disabled")
        self.log_text.see("end")

    def _clear_logs(self):
        """Clear logs for the current project."""
        if self.current_project_id:
            self.logs[self.current_project_id] = []
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")
