"""In-app project form panel – replaces the log panel when adding or editing a project."""

from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Optional, Callable

import customtkinter as ctk

from hamal.database.models import Project
from hamal.database.crud import create_project, update_project
from hamal.utils.helpers import detect_python_interpreter, detect_entry_file, get_python_files
from hamal.ui.settings_dialog import _patch_scroll_speed

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
        scroll = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_button_color=_COLORS["overlay"],
            scrollbar_button_hover_color=_COLORS["blue"],
        )
        scroll.grid(row=0, column=0, sticky="nsew")
        scroll.grid_columnconfigure(0, weight=1)
        _patch_scroll_speed(scroll)

        # ── 3-column header (Back | Title | Esc) ──────────────────────
        header = ctk.CTkFrame(scroll, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=8, pady=(12, 4))
        header.grid_columnconfigure(0, weight=1)
        header.grid_columnconfigure(1, weight=1)
        header.grid_columnconfigure(2, weight=1)

        ctk.CTkButton(
            header,
            text="← Back",
            width=90, height=34,
            fg_color=_COLORS["surface"],
            hover_color=_COLORS["overlay"],
            text_color=_COLORS["blue"],
            font=ctk.CTkFont(size=14, weight="bold"),
            corner_radius=8,
            command=self._cancel,
        ).grid(row=0, column=0, sticky="w", padx=(0, 4))

        title_text = "Edit Project" if self._is_edit else "Add New Project"
        ctk.CTkLabel(
            header,
            text=title_text,
            font=ctk.CTkFont(size=17, weight="bold"),
            text_color=_COLORS["text"],
            anchor="center",
        ).grid(row=0, column=1, sticky="ew")

        ctk.CTkLabel(
            header,
            text="Esc to cancel",
            font=ctk.CTkFont(size=11),
            text_color=_COLORS["subtext"],
            anchor="e",
        ).grid(row=0, column=2, sticky="e", padx=(4, 8))

        ctk.CTkFrame(scroll, height=1, fg_color=_COLORS["overlay"]).grid(
            row=1, column=0, sticky="ew", padx=16, pady=(4, 12)
        )

        # ── Form card ──────────────────────────────────────────────────
        card = ctk.CTkFrame(scroll, fg_color=_COLORS["surface"], corner_radius=10)
        card.grid(row=2, column=0, padx=16, pady=4, sticky="ew")
        card.grid_columnconfigure(1, weight=1)

        if self._is_edit:
            self._build_edit_form(card)
        else:
            self._build_add_form(card)

        # ── Action buttons ─────────────────────────────────────────────
        btn_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        btn_frame.grid(row=3, column=0, padx=16, pady=(16, 24), sticky="e")

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
            )
            if self._on_saved:
                self._on_saved(project)
            if self._on_back:
                self._on_back()
        except Exception as e:  # pylint: disable=broad-exception-caught
            messagebox.showerror("Error", f"Failed to update project: {e}")
