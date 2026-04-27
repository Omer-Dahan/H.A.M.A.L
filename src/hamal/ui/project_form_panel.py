"""In-app project form panel – replaces the log panel when adding or editing a project."""

import os
import subprocess
import threading
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Callable, Optional

import customtkinter as ctk

from hamal.database.crud import create_project, update_project
from hamal.database.models import Project
from hamal.ui.settings_dialog import _patch_scroll_speed
from hamal.utils.helpers import detect_entry_file, detect_python_interpreter, get_python_files

_COLORS = {
    "base":    "#1e1e2e",
    "mantle":  "#181825",
    "surface": "#313244",
    "overlay": "#45475a",
    "text":    "#cdd6f4",
    "subtext": "#a6adc8",
    "blue":    "#89b4fa",
    "green":   "#a6e3a1",
    "red":     "#f38ba8",
}


class ProjectFormPanel(ctk.CTkFrame):
    """In-app form for adding or editing a project.

    Parameters
    ----------
    master: parent widget (MainWindow)
    on_back: called when the user cancels or finishes
    on_saved: called with the resulting Project when saved
    project: if given, we are in Edit mode; otherwise Add mode
    """

    def __init__(
        self,
        master,
        on_back: Optional[Callable] = None,
        on_saved: Optional[Callable[[Project], None]] = None,
        project: Optional[Project] = None,
        **kwargs,
    ):
        super().__init__(master, fg_color=_COLORS["base"], **kwargs)
        self._on_back = on_back
        self._on_saved = on_saved
        self._project = project  # None = Add mode
        self._is_edit = project is not None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_ui()

    # ------------------------------------------------------------------
    # Public helpers (called by main_window when opening the panel)
    # ------------------------------------------------------------------

    def reset_for_add(self):
        """Clear all fields and switch to Add mode."""
        self._project = None
        self._is_edit = False
        for widget in self.winfo_children():
            widget.destroy()
        self._build_ui()

    def load_project(self, project: Project):
        """Populate fields and switch to Edit mode."""
        self._project = project
        self._is_edit = True
        for widget in self.winfo_children():
            widget.destroy()
        self._build_ui()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        # Configure the main panel grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)  # Header
        self.grid_rowconfigure(1, weight=1)  # Content

        # ── 3-column header (Back | Title | Esc) ──────────────────────
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=5, pady=(5, 10))
        header.grid_columnconfigure(0, weight=1)
        header.grid_columnconfigure(1, weight=1)
        header.grid_columnconfigure(2, weight=1)

        ctk.CTkButton(
            header,
            text="← Back",
            width=100, height=35, # Reduced slightly to match depth buttons
            fg_color=_COLORS["surface"],
            hover_color=_COLORS["overlay"],
            text_color=_COLORS["blue"],
            font=ctk.CTkFont(size=14, weight="bold"),
            corner_radius=12,
            command=self._cancel,
        ).grid(row=0, column=0, sticky="w", padx=(5, 4))

        title_text = "Project Settings" if self._is_edit else "Add New Project"
        ctk.CTkLabel(
            header,
            text=title_text,
            font=ctk.CTkFont(size=19, weight="bold"), # Increased slightly
            text_color=_COLORS["text"],
            anchor="center",
        ).grid(row=0, column=1, sticky="ew")

        ctk.CTkLabel(
            header,
            text="Esc to cancel",
            font=ctk.CTkFont(size=11),
            text_color=_COLORS["subtext"],
            anchor="e",
        ).grid(row=0, column=2, sticky="e", padx=(4, 15))

        # ── Scrollable Area ────────────────────────────────────────────
        scroll = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_button_color=_COLORS["overlay"],
            scrollbar_button_hover_color=_COLORS["blue"],
        )
        scroll.grid(row=1, column=0, sticky="nsew")
        scroll.grid_columnconfigure(0, weight=1)
        _patch_scroll_speed(scroll)

        ctk.CTkFrame(scroll, height=1, fg_color=_COLORS["overlay"]).grid(
            row=0, column=0, sticky="ew", padx=16, pady=(0, 12)
        )

        # ── Form card ──────────────────────────────────────────────────
        card = ctk.CTkFrame(scroll, fg_color=_COLORS["surface"], corner_radius=10)
        card.grid(row=2, column=0, padx=16, pady=4, sticky="ew")
        card.grid_columnconfigure(1, weight=1)

        if self._is_edit:
            self._build_edit_form(card)
        else:
            self._build_add_form(card)

        # ── Advanced section ───────────────────────────────────────────
        self._section_label(scroll, "Behavior", row=3)

        auto_row = self._option_row(
            scroll,
            label="Auto-start this project",
            description="Start automatically after 10 seconds when the app runs.",
            row=4,
        )
        self.auto_start_var = ctk.BooleanVar(value=self._project.auto_start if self._is_edit else False)
        ctk.CTkSwitch(
            auto_row,
            text="",
            variable=self.auto_start_var,
            onvalue=True, offvalue=False,
            width=50,
            progress_color=_COLORS["blue"],
            button_color=_COLORS["text"],
            button_hover_color=_COLORS["blue"],
        ).grid(row=0, column=2, padx=(10, 16), pady=14)

        restart_row = self._option_row(
            scroll,
            label="Auto-restart on crash",
            description="If the process exits with an error, restart it automatically after 5 seconds.",
            row=5,
        )
        self.auto_restart_var = ctk.BooleanVar(value=self._project.auto_restart if self._is_edit else False)
        ctk.CTkSwitch(
            restart_row,
            text="",
            variable=self.auto_restart_var,
            onvalue=True, offvalue=False,
            width=50,
            progress_color=_COLORS["red"],
            button_color=_COLORS["text"],
            button_hover_color=_COLORS["red"],
        ).grid(row=0, column=2, padx=(10, 16), pady=14)

        # ── Scheduling section ─────────────────────────────────────────
        self._section_label(scroll, "Scheduling", row=6)

        sched_row = self._option_row(
            scroll,
            label="Scheduled Operation",
            description="Automatically start and stop the script at specific times.",
            row=7,
        )

        # Add time inputs to a NEW row (row 2) to allow text to be full width
        time_frame = ctk.CTkFrame(sched_row, fg_color="transparent")
        time_frame.grid(row=2, column=1, columnspan=3, padx=16, pady=(0, 4), sticky="w")

        # Start Time
        ctk.CTkLabel(time_frame, text="Start:", font=ctk.CTkFont(size=11), text_color=_COLORS["subtext"]).grid(row=0, column=0, padx=4)
        self.sched_start_entry = ctk.CTkEntry(
            time_frame, width=60, height=28, placeholder_text="09:00",
            fg_color=_COLORS["mantle"], border_color=_COLORS["overlay"],
            text_color=_COLORS["text"]
        )
        self.sched_start_entry.grid(row=0, column=1, padx=4)
        if self._is_edit and self._project.schedule_start:
            self.sched_start_entry.insert(0, self._project.schedule_start)

        # Stop Time
        ctk.CTkLabel(time_frame, text="Stop:", font=ctk.CTkFont(size=11), text_color=_COLORS["subtext"]).grid(row=0, column=2, padx=(8, 4))
        self.sched_stop_entry = ctk.CTkEntry(
            time_frame, width=60, height=28, placeholder_text="18:00",
            fg_color=_COLORS["mantle"], border_color=_COLORS["overlay"],
            text_color=_COLORS["text"]
        )
        self.sched_stop_entry.grid(row=0, column=3, padx=4)
        if self._is_edit and self._project.schedule_stop:
            self.sched_stop_entry.insert(0, self._project.schedule_stop)

        # Switch
        self.sched_enabled_var = ctk.BooleanVar(value=self._project.schedule_enabled if self._is_edit else False)
        ctk.CTkSwitch(
            sched_row,
            text="",
            variable=self.sched_enabled_var,
            onvalue=True, offvalue=False,
            width=50,
            progress_color=_COLORS["blue"],
            button_color=_COLORS["text"],
            button_hover_color=_COLORS["blue"],
            command=self._toggle_scheduling_ui
        ).grid(row=0, column=3, padx=(0, 16), pady=(10, 0), sticky="ne")

        # ── Recurrence Days (Hidden by default, shown if enabled) ──────
        self.days_outer_frame = ctk.CTkFrame(sched_row, fg_color="transparent")
        # Initialize the days frame state
        self._setup_days_ui(self.days_outer_frame)

        # Initial visibility - Positioned in row 3 now
        if self.sched_enabled_var.get():
            self.days_outer_frame.grid(row=3, column=1, columnspan=3, sticky="ew", padx=16, pady=(0, 8))

        # ── Dependencies section (Edit mode only — needs a saved folder) ──
        if self._is_edit:
            self._section_label(scroll, "Dependencies", row=8)

            req_row = self._option_row(
                scroll,
                label="Install requirements.txt",
                description="Runs `pip install -r requirements.txt` using this project's Python interpreter.",
                row=9,
            )
            self._req_btn = ctk.CTkButton(
                req_row,
                text="Install",
                width=100, height=32,
                fg_color=_COLORS["blue"],
                hover_color="#74a8e8",
                text_color="#1e1e2e",
                font=ctk.CTkFont(size=13, weight="bold"),
                corner_radius=8,
                command=self._on_install_requirements,
            )
            self._req_btn.grid(row=0, column=3, padx=(8, 16), pady=14, sticky="e")

        # ── Action buttons ─────────────────────────────────────────────
        btn_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        btn_frame.grid(row=10, column=0, padx=16, pady=(16, 24), sticky="e")

        ctk.CTkButton(
            btn_frame,
            text="Cancel",
            width=100, height=36,
            fg_color=_COLORS["surface"],
            hover_color=_COLORS["overlay"],
            text_color=_COLORS["text"],
            corner_radius=8,
            command=self._cancel,
        ).pack(side="left", padx=(0, 8))

        save_text = "Save Changes" if self._is_edit else "Add Project"
        save_color = _COLORS["blue"] if self._is_edit else _COLORS["green"]
        ctk.CTkButton(
            btn_frame,
            text=save_text,
            width=130, height=36,
            fg_color=save_color,
            hover_color="#74a8e8" if self._is_edit else "#8fcf8c",
            text_color="#1e1e2e",
            font=ctk.CTkFont(size=13, weight="bold"),
            corner_radius=8,
            command=self._on_save,
        ).pack(side="left")

    def _field_row(self, parent, label: str, row: int):
        """Render a label in col=0; returns row index for caller to place field in col=1."""
        ctk.CTkLabel(
            parent, text=label,
            font=ctk.CTkFont(size=12),
            text_color=_COLORS["subtext"],
            anchor="e",
        ).grid(row=row, column=0, padx=(16, 8), pady=10, sticky="e")
        return row

    def _section_label(self, parent, text: str, row: int):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.grid(row=row, column=0, sticky="ew", padx=16, pady=(10, 2))
        ctk.CTkLabel(
            frame,
            text=text.upper(),
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=_COLORS["subtext"],
        ).pack(side="left")
        ctk.CTkFrame(frame, height=1, fg_color=_COLORS["overlay"]).pack(
            side="left", fill="x", expand=True, padx=(8, 0)
        )

    def _option_row(self, parent, label: str, description: str, row: int):
        row_frame = ctk.CTkFrame(parent, fg_color=_COLORS["surface"], corner_radius=10)
        row_frame.grid(row=row, column=0, sticky="ew", padx=16, pady=4)

        # Column 1: Labels (Flexible weight, guaranteed minimum width)
        # Column 2 & 3: Controls (Fixed width)
        row_frame.grid_columnconfigure(1, weight=1, minsize=220)
        row_frame.grid_columnconfigure(2, weight=0)
        row_frame.grid_columnconfigure(3, weight=0)

        # Title Label - Spans Title and Time areas to prevent cutoff
        l_label = ctk.CTkLabel(
            row_frame, text=label,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=_COLORS["text"],
            anchor="nw",
            justify="left",
            wraplength=350 # Sufficient room for title
        )
        l_label.grid(row=0, column=1, columnspan=2, padx=(16, 8), pady=(10, 2), sticky="new")

        # Description Label (if exists) - Full width
        if description:
            d_label = ctk.CTkLabel(
                row_frame, text=description,
                font=ctk.CTkFont(size=11),
                text_color=_COLORS["subtext"],
                anchor="nw",
                justify="left",
                wraplength=480 # Full panel width wrap
            )
            d_label.grid(row=1, column=1, columnspan=3, padx=(16, 16), pady=(0, 6), sticky="new")
        else:
            row_frame.grid_rowconfigure(0, weight=1, pad=12)

        return row_frame

    def _setup_days_ui(self, parent):
        """Build the recurrence days selector UI."""
        ctk.CTkLabel(
            parent, text="RECURRENCE DAYS",
            font=ctk.CTkFont(size=9, weight="bold"),
            text_color=_COLORS["subtext"],
            anchor="w"
        ).grid(row=0, column=0, sticky="w", pady=(0, 2))

        days_inner = ctk.CTkFrame(parent, fg_color="transparent")
        days_inner.grid(row=1, column=0, sticky="w")

        self.day_vars = {}
        day_labels = [("Sun", "S"), ("Mon", "M"), ("Tue", "T"), ("Wed", "W"), ("Thu", "T"), ("Fri", "F"), ("Sat", "S")]

        # Default to ALL OFF for new projects
        saved_days = (self._project.schedule_days or "").split(",") if self._is_edit else []

        for i, (_full, short) in enumerate(day_labels):
            is_sel = str(i) in saved_days if saved_days or self._is_edit else False
            btn, var = self._day_pill(days_inner, short, i, is_sel)
            btn.pack(side="left", padx=3)
            self.day_vars[i] = var

    def _day_pill(self, parent, text: str, _day_id: int, selected: bool):
        """Create a rounded square toggle button for a day of the week with glow effect."""
        var = ctk.BooleanVar(value=selected)
        btn = ctk.CTkButton(
            parent, text=text, width=40, height=40,
            fg_color=_COLORS["overlay"] if not selected else _COLORS["blue"],
            hover_color="#585b70" if not selected else "#a6c9ff",
            text_color=_COLORS["text"] if not selected else "#11111b",
            font=ctk.CTkFont(size=14, weight="bold"),
            corner_radius=10,
            border_width=2 if selected else 0,
            border_color="#b4befe" if selected else _COLORS["overlay"],
            command=lambda: self._toggle_day(btn, var)
        )
        return btn, var

    def _toggle_day(self, btn, var):
        val = not var.get()
        var.set(val)
        btn.configure(
            fg_color=_COLORS["blue"] if val else _COLORS["overlay"],
            text_color="#11111b" if val else _COLORS["text"],
            border_width=2 if val else 0,
            border_color="#b4befe" if val else _COLORS["overlay"]
        )

    def _toggle_scheduling_ui(self):
        """Show/hide day selector based on switch state."""
        if self.sched_enabled_var.get():
            self.days_outer_frame.grid(row=3, column=1, columnspan=3, sticky="ew", padx=16, pady=(0, 6))
        else:
            self.days_outer_frame.grid_forget()

    # ------------------------------------------------------------------
    # Add form
    # ------------------------------------------------------------------

    def _build_add_form(self, parent):
        # Folder
        self._field_row(parent, "Project Folder:", 0)
        folder_frame = ctk.CTkFrame(parent, fg_color="transparent")
        folder_frame.grid(row=0, column=1, padx=(0, 12), pady=10, sticky="ew")
        folder_frame.grid_columnconfigure(0, weight=1)

        self.folder_entry = ctk.CTkEntry(
            folder_frame, placeholder_text="Select project folder…",
            fg_color=_COLORS["mantle"], border_color=_COLORS["overlay"],
            text_color=_COLORS["text"],
        )
        self.folder_entry.grid(row=0, column=0, sticky="ew")
        ctk.CTkButton(
            folder_frame, text="Browse", width=80,
            fg_color=_COLORS["blue"], hover_color="#74a8e8", text_color="#1e1e2e",
            command=self._browse_folder,
        ).grid(row=0, column=1, padx=(6, 0))

        # Name
        self._field_row(parent, "Project Name:", 1)
        self.name_entry = ctk.CTkEntry(
            parent, placeholder_text="My Bot",
            fg_color=_COLORS["mantle"], border_color=_COLORS["overlay"],
            text_color=_COLORS["text"],
        )
        self.name_entry.grid(row=1, column=1, padx=(0, 12), pady=10, sticky="ew")

        # Entry file
        self._field_row(parent, "Entry File:", 2)
        entry_frame = ctk.CTkFrame(parent, fg_color="transparent")
        entry_frame.grid(row=2, column=1, padx=(0, 12), pady=10, sticky="ew")
        entry_frame.grid_columnconfigure(0, weight=1)

        self.entry_entry = ctk.CTkEntry(
            entry_frame, placeholder_text="main.py",
            fg_color=_COLORS["mantle"], border_color=_COLORS["overlay"],
            text_color=_COLORS["text"],
        )
        self.entry_entry.grid(row=0, column=0, sticky="ew")
        ctk.CTkButton(
            entry_frame, text="Browse", width=80,
            fg_color=_COLORS["overlay"], hover_color=_COLORS["surface"],
            text_color=_COLORS["text"],
            command=self._browse_entry_file,
        ).grid(row=0, column=1, padx=(6, 0))

        # Python
        self._field_row(parent, "Python:", 3)
        python_frame = ctk.CTkFrame(parent, fg_color="transparent")
        python_frame.grid(row=3, column=1, padx=(0, 12), pady=10, sticky="ew")
        python_frame.grid_columnconfigure(0, weight=1)

        self.python_entry = ctk.CTkEntry(
            python_frame, placeholder_text="Auto-detected…",
            fg_color=_COLORS["mantle"], border_color=_COLORS["overlay"],
            text_color=_COLORS["text"],
        )
        self.python_entry.grid(row=0, column=0, sticky="ew")
        ctk.CTkButton(
            python_frame, text="Browse", width=80,
            fg_color=_COLORS["overlay"], hover_color=_COLORS["surface"],
            text_color=_COLORS["text"],
            command=self._browse_python,
        ).grid(row=0, column=1, padx=(6, 0))

        # Status hint
        self._status_label = ctk.CTkLabel(
            parent, text="",
            font=ctk.CTkFont(size=11), text_color=_COLORS["subtext"],
        )
        self._status_label.grid(row=4, column=0, columnspan=2, padx=16, pady=(0, 8), sticky="w")

    # ------------------------------------------------------------------
    # Edit form
    # ------------------------------------------------------------------

    def _build_edit_form(self, parent):
        p = self._project

        # Name
        self._field_row(parent, "Project Name:", 0)
        self.name_entry = ctk.CTkEntry(
            parent, fg_color=_COLORS["mantle"],
            border_color=_COLORS["overlay"], text_color=_COLORS["text"],
        )
        self.name_entry.insert(0, p.name)
        self.name_entry.grid(row=0, column=1, padx=(0, 12), pady=10, sticky="ew")

        # Folder (read-only)
        self._field_row(parent, "Folder:", 1)
        ctk.CTkLabel(
            parent, text=p.folder_path, anchor="w",
            font=ctk.CTkFont(size=11), text_color=_COLORS["subtext"],
            wraplength=320,
        ).grid(row=1, column=1, padx=(0, 12), pady=10, sticky="w")

        # Entry file dropdown
        self._field_row(parent, "Entry File:", 2)
        py_files = get_python_files(p.folder_path) or [p.entrypoint]
        self.entry_var = ctk.StringVar(value=p.entrypoint)
        ctk.CTkComboBox(
            parent, variable=self.entry_var, values=py_files, state="readonly",
            fg_color=_COLORS["mantle"], border_color=_COLORS["overlay"],
            text_color=_COLORS["text"], button_color=_COLORS["overlay"],
            button_hover_color=_COLORS["surface"],
        ).grid(row=2, column=1, padx=(0, 12), pady=10, sticky="ew")

        # Python
        self._field_row(parent, "Python:", 3)
        python_frame = ctk.CTkFrame(parent, fg_color="transparent")
        python_frame.grid(row=3, column=1, padx=(0, 12), pady=10, sticky="ew")
        python_frame.grid_columnconfigure(0, weight=1)

        self.python_entry = ctk.CTkEntry(
            python_frame, fg_color=_COLORS["mantle"],
            border_color=_COLORS["overlay"], text_color=_COLORS["text"],
        )
        self.python_entry.insert(0, p.interpreter_path)
        self.python_entry.grid(row=0, column=0, sticky="ew")
        ctk.CTkButton(
            python_frame, text="Browse", width=80,
            fg_color=_COLORS["overlay"], hover_color=_COLORS["surface"],
            text_color=_COLORS["text"],
            command=self._browse_python,
        ).grid(row=0, column=1, padx=(6, 0))

        self._status_label = None  # not used in edit mode

    # ------------------------------------------------------------------
    # Browsing helpers
    # ------------------------------------------------------------------

    def _browse_folder(self):
        folder = filedialog.askdirectory(title="Select Project Folder")
        if folder:
            self.folder_entry.delete(0, "end")
            self.folder_entry.insert(0, folder)
            self._auto_detect(folder)

    def _browse_entry_file(self):
        folder = self.folder_entry.get().strip()
        initial_dir = folder if folder and Path(folder).exists() else None
        file = filedialog.askopenfilename(
            title="Select Entry Python File",
            initialdir=initial_dir,
            filetypes=[("Python files", "*.py"), ("All files", "*.*")],
        )
        if file:
            self.entry_entry.delete(0, "end")
            self.entry_entry.insert(0, Path(file).name)

    def _browse_python(self):
        file = filedialog.askopenfilename(
            title="Select Python Executable",
            filetypes=[("Python", "python.exe"), ("All files", "*.*")],
        )
        if file:
            self.python_entry.delete(0, "end")
            self.python_entry.insert(0, file)

    def _auto_detect(self, folder: str):
        python = detect_python_interpreter(folder)
        if python:
            self.python_entry.delete(0, "end")
            self.python_entry.insert(0, python)
            if self._status_label:
                self._status_label.configure(text="✓ Found virtual environment", text_color=_COLORS["green"])
        else:
            if self._status_label:
                self._status_label.configure(
                    text="⚠ No venv found – select Python manually", text_color=_COLORS["red"]
                )
        entry = detect_entry_file(folder)
        if entry:
            self.entry_entry.delete(0, "end")
            self.entry_entry.insert(0, entry)
        if not self.name_entry.get():
            self.name_entry.insert(0, Path(folder).name)

    # ------------------------------------------------------------------
    # Save / Cancel
    # ------------------------------------------------------------------

    def _cancel(self):
        if self._on_back:
            self._on_back()

    def _on_save(self):
        if self._is_edit:
            self._save_edit()
        else:
            self._save_add()

    def _save_add(self):
        folder = self.folder_entry.get().strip()
        name = self.name_entry.get().strip()
        entry = self.entry_entry.get().strip()
        python = self.python_entry.get().strip()
        auto_start = self.auto_start_var.get()
        auto_restart = self.auto_restart_var.get()
        sched_enabled = self.sched_enabled_var.get()
        sched_start = self.sched_start_entry.get().strip() or None
        sched_stop = self.sched_stop_entry.get().strip() or None

        selected_days = [str(i) for i, var in self.day_vars.items() if var.get()]
        sched_days = ",".join(selected_days) if selected_days else None

        if not folder:
            messagebox.showerror("Error", "Please select a project folder")
            return
        if not name:
            messagebox.showerror("Error", "Please enter a project name")
            return
        if not entry:
            messagebox.showerror("Error", "Please select an entry file")
            return
        if not python:
            messagebox.showerror("Error", "Please select a Python interpreter")
            return

        try:
            project = create_project(
                name=name, folder_path=folder,
                entrypoint=entry, interpreter_path=python,
                auto_start=auto_start,
                auto_restart=auto_restart,
                schedule_enabled=sched_enabled,
                schedule_start=sched_start,
                schedule_stop=sched_stop,
                schedule_days=sched_days,
            )
            if self._on_saved:
                self._on_saved(project)
            if self._on_back:
                self._on_back()
        except Exception as e:  # pylint: disable=broad-exception-caught
            messagebox.showerror("Error", f"Failed to create project: {e}")

    def _save_edit(self):
        name = self.name_entry.get().strip()
        entry = self.entry_var.get()
        python = self.python_entry.get().strip()
        auto_start = self.auto_start_var.get()
        auto_restart = self.auto_restart_var.get()
        sched_enabled = self.sched_enabled_var.get()
        sched_start = self.sched_start_entry.get().strip() or None
        sched_stop = self.sched_stop_entry.get().strip() or None

        selected_days = [str(i) for i, var in self.day_vars.items() if var.get()]
        sched_days = ",".join(selected_days) if selected_days else None

        if not name:
            messagebox.showerror("Error", "Please enter a project name")
            return
        if not entry:
            messagebox.showerror("Error", "Please select an entry file")
            return
        if not python:
            messagebox.showerror("Error", "Please select a Python interpreter")
            return

        try:
            project = update_project(
                project_id=self._project.id,
                name=name, entrypoint=entry, interpreter_path=python,
                auto_start=auto_start,
                auto_restart=auto_restart,
                schedule_enabled=sched_enabled,
                schedule_start=sched_start,
                schedule_stop=sched_stop,
                schedule_days=sched_days,
            )
            if self._on_saved:
                self._on_saved(project)
            if self._on_back:
                self._on_back()
        except Exception as e:  # pylint: disable=broad-exception-caught
            messagebox.showerror("Error", f"Failed to update project: {e}")

    # ------------------------------------------------------------------
    # Dependencies
    # ------------------------------------------------------------------

    def _on_install_requirements(self):
        """Run `pip install -r requirements.txt` using the project's interpreter."""
        if not self._is_edit or not self._project:
            return

        python = self.python_entry.get().strip()
        folder = self._project.folder_path
        req_file = Path(folder) / "requirements.txt"

        if not Path(python).exists():
            messagebox.showerror("Error", f"Python interpreter not found:\n{python}")
            return
        if not req_file.exists():
            messagebox.showerror(
                "requirements.txt not found",
                f"No requirements.txt in:\n{folder}",
            )
            return

        PipInstallDialog(
            self.winfo_toplevel(),
            python_path=python,
            requirements_path=str(req_file),
            cwd=folder,
        )


class PipInstallDialog(ctk.CTkToplevel):
    """Modal dialog that streams `pip install -r requirements.txt` output live."""

    def __init__(self, master, python_path: str, requirements_path: str, cwd: str):
        super().__init__(master)
        self.title("Installing requirements")
        self.geometry("720x460")
        self.configure(fg_color=_COLORS["base"])
        self.transient(master)
        self.grab_set()

        self._proc: Optional[subprocess.Popen] = None
        self._done = False

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkLabel(
            self,
            text="pip install -r requirements.txt",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=_COLORS["text"],
        )
        header.grid(row=0, column=0, padx=16, pady=(16, 8), sticky="w")

        self._textbox = ctk.CTkTextbox(
            self,
            fg_color=_COLORS["mantle"],
            text_color=_COLORS["text"],
            font=ctk.CTkFont(family="Consolas", size=11),
            wrap="word",
        )
        self._textbox.grid(row=1, column=0, padx=16, pady=0, sticky="nsew")
        self._textbox.configure(state="disabled")

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=2, column=0, padx=16, pady=12, sticky="e")

        self._cancel_btn = ctk.CTkButton(
            btn_frame, text="Cancel", width=100, height=32,
            fg_color=_COLORS["surface"], hover_color=_COLORS["overlay"],
            text_color=_COLORS["text"],
            command=self._on_cancel,
        )
        self._cancel_btn.pack(side="left", padx=(0, 8))

        self._close_btn = ctk.CTkButton(
            btn_frame, text="Close", width=100, height=32,
            fg_color=_COLORS["blue"], hover_color="#74a8e8",
            text_color="#1e1e2e",
            command=self.destroy,
            state="disabled",
        )
        self._close_btn.pack(side="left")

        self.protocol("WM_DELETE_WINDOW", self._on_cancel)

        threading.Thread(
            target=self._run_pip,
            args=(python_path, requirements_path, cwd),
            daemon=True,
        ).start()

    def _append(self, line: str):
        try:
            self._textbox.configure(state="normal")
            self._textbox.insert("end", line)
            self._textbox.see("end")
            self._textbox.configure(state="disabled")
        except Exception:  # pylint: disable=broad-exception-caught
            pass

    def _run_pip(self, python_path: str, requirements_path: str, cwd: str):
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"

        try:
            # pylint: disable=consider-using-with
            self._proc = subprocess.Popen(
                [python_path, "-m", "pip", "install", "-r", requirements_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=cwd,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                env=env,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        except Exception as e:  # pylint: disable=broad-exception-caught
            self.after(0, self._append, f"[ERROR] Failed to launch pip: {e}\n")
            self.after(0, self._finish, -1)
            return

        for line in iter(self._proc.stdout.readline, ""):
            if not line:
                break
            self.after(0, self._append, line)

        try:
            self._proc.stdout.close()
        except Exception:  # pylint: disable=broad-exception-caught
            pass
        exit_code = self._proc.wait()
        self.after(0, self._finish, exit_code)

    def _finish(self, exit_code: int):
        self._done = True
        if exit_code == 0:
            self._append("\n✓ Done.\n")
        else:
            self._append(f"\n✗ pip exited with code {exit_code}.\n")
        self._cancel_btn.configure(state="disabled")
        self._close_btn.configure(state="normal")

    def _on_cancel(self):
        if self._done:
            self.destroy()
            return
        if self._proc and self._proc.poll() is None:
            try:
                self._proc.terminate()
            except Exception:  # pylint: disable=broad-exception-caught
                pass
        self._append("\n[Cancelled]\n")
        self._cancel_btn.configure(state="disabled")
        self._close_btn.configure(state="normal")
        self._done = True
