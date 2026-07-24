"""Dialog windows for adding and editing projects."""

from hamal.core.i18n import t
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Optional

import customtkinter as ctk

from hamal.core.python_environment import (
    ensure_environment_async,
    find_system_python_async,
    is_winget_available,
    venv_python_path,
)
from hamal.database.crud import create_project, update_project
from hamal.database.models import Project
from hamal.utils.helpers import detect_entry_file, detect_python_interpreter, get_python_files


class AddProjectDialog(ctk.CTkToplevel):
    """Dialog for adding a new project."""

    def __init__(self, master):
        super().__init__(master)

        self.result = None

        # Environment-creation state (see _on_create_env)
        self._venv_btn = None
        self._venv_busy = False
        self._needs_python_install = False

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

        # Status label (left) + environment action button (right)
        status_frame = ctk.CTkFrame(self, fg_color="transparent")
        status_frame.grid(row=2, column=0, padx=20, pady=5, sticky="ew")
        status_frame.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(
            status_frame,
            text="",
            font=ctk.CTkFont(size=12),
            text_color=("gray50", "gray50"),
            anchor="w",
        )
        self.status_label.grid(row=0, column=0, sticky="w")

        self._venv_btn = ctk.CTkButton(
            status_frame,
            text=t("Create venv"),
            width=110,
            height=26,
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self._on_create_env,
        )
        # Placed only when the scan finds no environment (see _auto_detect).

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
            self._hide_venv_button()
        else:
            self.status_label.configure(text=t("⚠ No venv found - please select Python manually"))
            self._show_venv_button()

        # Detect entry file
        entry = detect_entry_file(folder)

        if entry:
            self.entry_entry.delete(0, "end")
            self.entry_entry.insert(0, entry)

        # Auto-set name from folder
        if not self.name_entry.get():
            folder_name = Path(folder).name
            self.name_entry.insert(0, folder_name)

    # ------------------------------------------------------------------
    # Python environment creation
    # ------------------------------------------------------------------

    def _post(self, fn, *args):
        """Hop back to the Tk thread; drops the call if the dialog is already gone."""
        try:
            self.after(0, fn, *args)
        except Exception:  # pylint: disable=broad-exception-caught
            pass

    def _venv_btn_alive(self) -> bool:
        return self._venv_btn is not None and bool(self._venv_btn.winfo_exists())

    def _hide_venv_button(self):
        if self._venv_btn_alive():
            self._venv_btn.grid_forget()

    def _show_venv_button(self):
        """Offer to build the environment, next to the warning."""
        if not self._venv_btn_alive():
            return
        self._needs_python_install = False
        self._venv_btn.configure(text=t("Create venv"), state="normal")
        self._venv_btn.grid(row=0, column=1, padx=(8, 0), sticky="e")
        # Probing `py`/`python` spawns processes - keep it off the UI thread.
        find_system_python_async(lambda p: self._post(self._on_python_probe, p))

    def _on_python_probe(self, python_exe: Optional[str]):
        """Switch the button to `Install Python` when the machine has no Python."""
        if not self._venv_btn_alive() or self._venv_busy:
            return
        self._needs_python_install = python_exe is None
        if python_exe is None:
            self._venv_btn.configure(text=t("Install Python"))
            self.status_label.configure(text=t("⚠ No venv and no Python found on this computer"))
        else:
            self._venv_btn.configure(text=t("Create venv"))

    def _on_create_env(self):
        if self._venv_busy:
            return

        folder = self.folder_entry.get().strip()
        if not folder or not Path(folder).is_dir():
            messagebox.showerror("Error", "Please select a project folder first", parent=self)
            return

        allow_install = False
        if self._needs_python_install:
            if not is_winget_available():
                messagebox.showerror(
                    "Python not found",
                    "Python is not installed and Windows Package Manager (winget) "
                    "is not available.\n\n"
                    "Install Python manually from https://www.python.org/downloads/",
                    parent=self,
                )
                return
            confirmed = messagebox.askyesno(
                "Install Python?",
                "Python was not found on this computer.\n\n"
                "Install Python using Windows Package Manager (winget)?\n\n"
                "This downloads from the internet, may ask for permission, and can "
                "take a few minutes. You may need to restart H.A.M.A.L afterwards.",
                parent=self,
            )
            if not confirmed:
                return
            allow_install = True

        self._venv_busy = True
        self._venv_btn.configure(state="disabled")
        self.status_label.configure(text=t("Creating virtual environment..."))

        ensure_environment_async(
            folder,
            on_done=lambda result: self._post(self._on_env_done, result),
            allow_install=allow_install,
            on_status=lambda text: self._post(self._set_status, text),
        )

    def _set_status(self, text: str):
        if self.status_label.winfo_exists():
            self.status_label.configure(text=text)

    def _on_env_done(self, result):
        self._venv_busy = False
        if not self.winfo_exists():
            return

        if result.success:
            python = result.python_path or str(venv_python_path(self.folder_entry.get().strip()))
            self.python_entry.delete(0, "end")
            self.python_entry.insert(0, python)
            self._set_status(t("✓ Virtual environment ready"))
            self._hide_venv_button()
            return

        # Failure - bring the button back and explain what happened
        self._needs_python_install = result.needs_python_install
        if self._venv_btn_alive():
            self._venv_btn.configure(
                state="normal",
                text=t("Install Python") if result.needs_python_install else t("Create venv"),
            )
        self._set_status(f"✗ {result.message.strip().splitlines()[0]}")
        messagebox.showerror("Environment setup failed", result.message, parent=self)

    def _on_add(self):
        """Handle add button click."""
        if self._venv_busy:
            messagebox.showinfo(
                "Please wait",
                "The virtual environment is still being created.\n"
                "Wait for it to finish before saving the project.",
                parent=self,
            )
            return

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
