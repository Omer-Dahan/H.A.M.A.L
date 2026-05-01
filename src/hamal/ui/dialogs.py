"""Dialog windows for adding and editing projects."""

from hamal.core.i18n import t
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Optional

import customtkinter as ctk

from hamal.database.crud import create_project, update_project
from hamal.database.models import Project
from hamal.utils.helpers import detect_entry_file, detect_python_interpreter, get_python_files


class AddProjectDialog(ctk.CTkToplevel):
    """Dialog for adding a new project."""

    def __init__(self, master):
        super().__init__(master)

        self.result = None

        # Window config
        self.title("Add Project")
        self.geometry("500x400")
        self.resizable(False, False)

        # Make modal
        self.transient(master)
        self.grab_set()

        self._setup_ui()

        # Center on parent
        self.update_idletasks()
        x = master.winfo_rootx() + (master.winfo_width() - self.winfo_width()) // 2
        y = master.winfo_rooty() + (master.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

        # Wait for dialog to close
        self.wait_window()

    def _setup_ui(self):
        """Setup the dialog UI."""
        self.grid_columnconfigure(0, weight=1)

        # Title
        title = ctk.CTkLabel(
            self,
            text=t("Add New Project"),
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title.grid(row=0, column=0, padx=20, pady=(20, 10))

        # Form frame
        form = ctk.CTkFrame(self, fg_color="transparent")
        form.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        form.grid_columnconfigure(1, weight=1)

        # Project folder
        ctk.CTkLabel(form, text=t("Project Folder:")).grid(
            row=0, column=0, padx=5, pady=10, sticky="e"
        )

        folder_frame = ctk.CTkFrame(form, fg_color="transparent")
        folder_frame.grid(row=0, column=1, padx=5, pady=10, sticky="ew")
        folder_frame.grid_columnconfigure(0, weight=1)

        self.folder_entry = ctk.CTkEntry(folder_frame, placeholder_text=t("Select project folder..."))
        self.folder_entry.grid(row=0, column=0, sticky="ew")

        browse_btn = ctk.CTkButton(
            folder_frame,
            text=t("Browse"),
            width=70,
            command=self._browse_folder
        )
        browse_btn.grid(row=0, column=1, padx=(5, 0))

        # Project name
        ctk.CTkLabel(form, text=t("Project Name:")).grid(row=1, column=0, padx=5, pady=10, sticky="e")
        self.name_entry = ctk.CTkEntry(form, placeholder_text=t("My Project"))
        self.name_entry.grid(row=1, column=1, padx=5, pady=10, sticky="ew")

        # Entry file
        ctk.CTkLabel(form, text=t("Entry File:")).grid(row=2, column=0, padx=5, pady=10, sticky="e")

        entry_frame = ctk.CTkFrame(form, fg_color="transparent")
        entry_frame.grid(row=2, column=1, padx=5, pady=10, sticky="ew")
        entry_frame.grid_columnconfigure(0, weight=1)

        self.entry_entry = ctk.CTkEntry(entry_frame, placeholder_text=t("main.py"))
        self.entry_entry.grid(row=0, column=0, sticky="ew")

        entry_browse_btn = ctk.CTkButton(
            entry_frame,
            text=t("Browse"),
            width=70,
            command=self._browse_entry_file
        )
        entry_browse_btn.grid(row=0, column=1, padx=(5, 0))

        # Python interpreter
        ctk.CTkLabel(form, text=t("Python:")).grid(row=3, column=0, padx=5, pady=10, sticky="e")

        python_frame = ctk.CTkFrame(form, fg_color="transparent")
        python_frame.grid(row=3, column=1, padx=5, pady=10, sticky="ew")
        python_frame.grid_columnconfigure(0, weight=1)

        self.python_entry = ctk.CTkEntry(
            python_frame, placeholder_text=t("Auto-detected or select...")
        )
        self.python_entry.grid(row=0, column=0, sticky="ew")

        python_browse_btn = ctk.CTkButton(
            python_frame,
            text=t("Browse"),
            width=70,
            command=self._browse_python
        )
        python_browse_btn.grid(row=0, column=1, padx=(5, 0))

        # Status label
        self.status_label = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=12),
            text_color=("gray50", "gray50")
        )
        self.status_label.grid(row=2, column=0, padx=20, pady=5)

        # Buttons
        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.grid(row=3, column=0, padx=20, pady=20)

        cancel_btn = ctk.CTkButton(
            buttons,
            text=t("Cancel"),
            width=100,
            fg_color="transparent",
            border_width=1,
            command=self.destroy
        )
        cancel_btn.pack(side="left", padx=10)

        add_btn = ctk.CTkButton(
            buttons,
            text=t("Add Project"),
            width=100,
            command=self._on_add
        )
        add_btn.pack(side="left", padx=10)

    def _browse_folder(self):
        """Browse for project folder."""
        folder = filedialog.askdirectory(title=t("Select Project Folder"))
        if folder:
            self.folder_entry.delete(0, "end")
            self.folder_entry.insert(0, folder)

            # Auto-detect settings
            self._auto_detect(folder)

    def _browse_entry_file(self):
        """Browse for entry Python file."""
        folder = self.folder_entry.get().strip()
        initial_dir = folder if folder and Path(folder).exists() else None

        file = filedialog.askopenfilename(
            title=t("Select Entry Python File"),
            initialdir=initial_dir,
            filetypes=[("Python files", "*.py"), ("All files", "*.*")]
        )
        if file:
            # Store only the filename, not full path
            self.entry_entry.delete(0, "end")
            self.entry_entry.insert(0, Path(file).name)

    def _browse_python(self):
        """Browse for Python interpreter."""
        file = filedialog.askopenfilename(
            title=t("Select Python Executable"),
            filetypes=[("Python", "python.exe"), ("All files", "*.*")]
        )
        if file:
            self.python_entry.delete(0, "end")
            self.python_entry.insert(0, file)

    def _auto_detect(self, folder: str):
        """Auto-detect project settings."""
        # Detect Python
        python = detect_python_interpreter(folder)
        if python:
            self.python_entry.delete(0, "end")
            self.python_entry.insert(0, python)
            self.status_label.configure(text=t("✓ Found virtual environment"))
        else:
            self.status_label.configure(text=t("⚠ No venv found - please select Python manually"))

        # Detect entry file
        entry = detect_entry_file(folder)

        if entry:
            self.entry_entry.delete(0, "end")
            self.entry_entry.insert(0, entry)

        # Auto-set name from folder
        if not self.name_entry.get():
            folder_name = Path(folder).name
            self.name_entry.insert(0, folder_name)

    def _on_add(self):
        """Handle add button click."""
        folder = self.folder_entry.get().strip()
        name = self.name_entry.get().strip()
        entry = self.entry_entry.get().strip()
        python = self.python_entry.get().strip()

        # Validation
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

        # Create project
        try:
            project = create_project(
                name=name,
                folder_path=folder,
                entrypoint=entry,
                interpreter_path=python
            )
            self.result = project
            self.destroy()
        except Exception as e:  # pylint: disable=broad-exception-caught
            messagebox.showerror("Error", f"Failed to create project: {e}")

    def get_result(self) -> Optional[Project]:
        """Get the created project (or None if cancelled)."""
        return self.result


class EditProjectDialog(ctk.CTkToplevel):
    """Dialog for editing an existing project."""

    def __init__(self, master, project: Project):
        super().__init__(master)

        self.project = project
        self.result = None

        # Window config
        self.title("Edit Project")
        self.geometry("500x400")
        self.resizable(False, False)

        # Make modal
        self.transient(master)
        self.grab_set()

        self._setup_ui()

        # Center on parent
        self.update_idletasks()
        x = master.winfo_rootx() + (master.winfo_width() - self.winfo_width()) // 2
        y = master.winfo_rooty() + (master.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

        # Wait for dialog to close
        self.wait_window()

    def _setup_ui(self):
        """Setup the dialog UI."""
        self.grid_columnconfigure(0, weight=1)

        # Title
        title = ctk.CTkLabel(
            self,
            text=t("Edit Project"),
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title.grid(row=0, column=0, padx=20, pady=(20, 10))

        # Form frame
        form = ctk.CTkFrame(self, fg_color="transparent")
        form.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        form.grid_columnconfigure(1, weight=1)

        # Project name
        ctk.CTkLabel(form, text=t("Project Name:")).grid(row=0, column=0, padx=5, pady=10, sticky="e")
        self.name_entry = ctk.CTkEntry(form)
        self.name_entry.insert(0, self.project.name)
        self.name_entry.grid(row=0, column=1, padx=5, pady=10, sticky="ew")

        # Project folder (read-only display)
        ctk.CTkLabel(form, text=t("Folder:")).grid(row=1, column=0, padx=5, pady=10, sticky="e")
        folder_label = ctk.CTkLabel(
            form,
            text=self.project.folder_path,
            anchor="w",
            text_color=("gray50", "gray50")
        )
        folder_label.grid(row=1, column=1, padx=5, pady=10, sticky="w")

        # Entry file
        ctk.CTkLabel(form, text=t("Entry File:")).grid(row=2, column=0, padx=5, pady=10, sticky="e")

        py_files = get_python_files(self.project.folder_path)
        if not py_files:
            py_files = [self.project.entrypoint]

        self.entry_var = ctk.StringVar(value=self.project.entrypoint)
        self.entry_combo = ctk.CTkComboBox(
            form,
            variable=self.entry_var,
            values=py_files,
            state="readonly"
        )
        self.entry_combo.grid(row=2, column=1, padx=5, pady=10, sticky="ew")

        # Python interpreter
        ctk.CTkLabel(form, text=t("Python:")).grid(row=3, column=0, padx=5, pady=10, sticky="e")

        python_frame = ctk.CTkFrame(form, fg_color="transparent")
        python_frame.grid(row=3, column=1, padx=5, pady=10, sticky="ew")
        python_frame.grid_columnconfigure(0, weight=1)

        self.python_entry = ctk.CTkEntry(python_frame)
        self.python_entry.insert(0, self.project.interpreter_path)
        self.python_entry.grid(row=0, column=0, sticky="ew")

        python_browse_btn = ctk.CTkButton(
            python_frame,
            text=t("Browse"),
            width=70,
            command=self._browse_python
        )
        python_browse_btn.grid(row=0, column=1, padx=(5, 0))

        # Buttons
        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.grid(row=3, column=0, padx=20, pady=20)

        cancel_btn = ctk.CTkButton(
            buttons,
            text=t("Cancel"),
            width=100,
            fg_color="transparent",
            border_width=1,
            command=self.destroy
        )
        cancel_btn.pack(side="left", padx=10)

        save_btn = ctk.CTkButton(
            buttons,
            text=t("Save Changes"),
            width=100,
            command=self._on_save
        )
        save_btn.pack(side="left", padx=10)

    def _browse_python(self):
        """Browse for Python interpreter."""
        file = filedialog.askopenfilename(
            title=t("Select Python Executable"),
            filetypes=[("Python", "python.exe"), ("All files", "*.*")]
        )
        if file:
            self.python_entry.delete(0, "end")
            self.python_entry.insert(0, file)

    def _on_save(self):
        """Handle save button click."""
        name = self.name_entry.get().strip()
        entry = self.entry_var.get()
        python = self.python_entry.get().strip()

        # Validation
        if not name:
            messagebox.showerror("Error", "Please enter a project name")
            return

        if not entry:
            messagebox.showerror("Error", "Please select an entry file")
            return

        if not python:
            messagebox.showerror("Error", "Please select a Python interpreter")
            return

        # Update project
        try:
            project = update_project(
                project_id=self.project.id,
                name=name,
                entrypoint=entry,
                interpreter_path=python
            )
            self.result = project
            self.destroy()
        except Exception as e:  # pylint: disable=broad-exception-caught
            messagebox.showerror("Error", f"Failed to update project: {e}")

    def get_result(self) -> Optional[Project]:
        """Get the updated project (or None if cancelled)."""
        return self.result
