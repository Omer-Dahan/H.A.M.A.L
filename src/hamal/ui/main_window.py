"""Main application window using CustomTkinter."""

from tkinter import messagebox
import customtkinter as ctk

from hamal.core.config import APP_NAME, APP_VERSION, load_settings
from hamal.core.process_manager import ProcessManager
from hamal.ui.dashboard import Dashboard
from hamal.ui.log_panel import LogPanel
from hamal.ui.icons import get_icons_dir
from hamal.ui.about_dialog import AboutDialog
from hamal.ui.settings_dialog import SettingsPanel
from hamal.ui.log_filter_dialog import LogFilterPanel
from hamal.ui.project_form_panel import ProjectFormPanel
from hamal.ui.tray import TrayIcon


# Catppuccin Mocha colors
COLORS = {
    "base": "#1e1e2e",
    "mantle": "#181825",
    "crust": "#11111b",
    "surface": "#313244",
    "overlay": "#45475a",
    "text": "#cdd6f4",
    "subtext": "#a6adc8",
    "blue": "#89b4fa",
    "red": "#f38ba8",
    "green": "#a6e3a1",
    "yellow": "#f9e2af",
    "mauve": "#cba6f7",
}


class MainWindow(ctk.CTk):
    """Main application window with dashboard and log viewer."""
    # pylint: disable=too-many-instance-attributes,attribute-defined-outside-init

    def __init__(self, instance_manager=None):
        super().__init__()

        # Register focus callback so a second launch brings this window up
        if instance_manager is not None:
            instance_manager.set_focus_callback(self.bring_to_front)

        # Load persistent settings
        self._settings = load_settings()

        # Window configuration
        self.title(f"{APP_NAME} v{APP_VERSION}")
        self.geometry("1100x650")
        self.minsize(500, 500)

        # Set window icon
        try:
            icons_dir = get_icons_dir()
            icon_ico = icons_dir / "icon.ico"

            if icon_ico.exists():
                # Windows: iconbitmap uses the .ico file which contains all
                # sizes (16, 32, 48, 256). The OS picks the right one.
                # Do NOT call iconphoto afterwards – it overrides iconbitmap
                # and forces Tkinter to use 16/32 px (the flat, un-shadowed
                # variants) for the title bar and taskbar.
                self.iconbitmap(icon_ico)
            else:
                # Non-Windows fallback: use PNGs via iconphoto
                from PIL import Image, ImageTk  # pylint: disable=import-outside-toplevel
                icon_images = []
                for size in ["256", "48", "32", "16"]:
                    path = icons_dir / f"{size}.png"
                    if path.exists():
                        icon_images.append(ImageTk.PhotoImage(Image.open(path)))
                if icon_images:
                    self.iconphoto(True, *icon_images)

        except Exception as e:  # pylint: disable=broad-exception-caught
            print(f"Failed to set window icon: {e}")

        # Set dark appearance
        self.configure(fg_color=COLORS["base"])

        # Process manager
        self.process_manager = ProcessManager()

        # Right-side panel tracking (log_panel / settings_panel / filter_panel / project_panel)
        self._settings_panel: SettingsPanel | None = None
        self._filter_panel: LogFilterPanel | None = None
        self._project_panel: ProjectFormPanel | None = None
        self._right_panel = "log"  # "log" | "settings" | "filters" | "project"

        # Tray icon (lazy – only shown when minimize_to_tray is active)
        self._tray = TrayIcon(
            on_show=lambda: self.after(0, self._restore_from_tray),
            on_exit=lambda: self.after(0, self._force_quit),
        )

        # Setup callbacks
        self._setup_callbacks()

        # Build UI
        self._setup_menu()
        self._setup_ui()

        # Handle window close
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _setup_callbacks(self):
        """Setup process manager callbacks."""
        self.process_manager.on_status_changed = self._on_status_changed
        self.process_manager.on_log_received = self._on_log_received
        self.process_manager.on_crash_detected = self._on_crash_detected

    def _setup_menu(self):
        """Setup a custom dark-themed menu bar using CTkFrame."""
        # Custom menu bar frame
        self.custom_menu_bar = ctk.CTkFrame(
            self,
            fg_color=COLORS["crust"],
            height=28,
            corner_radius=0
        )
        self.custom_menu_bar.grid(row=0, column=0, columnspan=2, sticky="ew")
        self.custom_menu_bar.grid_propagate(False)

        # Active dropdown tracking
        self._active_menu = None

        # Container frame for menu buttons (grouped on the left)
        self.menu_buttons_container = ctk.CTkFrame(
            self.custom_menu_bar,
            fg_color="transparent"
        )
        self.menu_buttons_container.pack(side="left", padx=0)

        # Menu button style
        menu_btn_style = {
            "fg_color": "transparent",
            "hover_color": COLORS["surface"],
            "text_color": COLORS["text"],
            "font": ctk.CTkFont(size=12),
            "corner_radius": 0,
            "height": 28,
            "anchor": "center"
        }

        # File menu button
        self.file_btn = ctk.CTkButton(
            self.menu_buttons_container,
            text="File",
            width=50,
            command=lambda: self._toggle_dropdown("file"),
            **menu_btn_style
        )
        self.file_btn.pack(side="left", padx=0)

        # Projects menu button
        self.projects_btn = ctk.CTkButton(
            self.menu_buttons_container,
            text="Projects",
            width=70,
            command=lambda: self._toggle_dropdown("projects"),
            **menu_btn_style
        )
        self.projects_btn.pack(side="left", padx=0)

        # Help menu button
        self.help_btn = ctk.CTkButton(
            self.menu_buttons_container,
            text="Help",
            width=50,
            command=lambda: self._toggle_dropdown("help"),
            **menu_btn_style
        )
        self.help_btn.pack(side="left", padx=0)

        # Create dropdown menus (hidden by default)
        self._create_dropdowns()

    def _create_dropdowns(self):
        """Create dropdown menu frames."""
        dropdown_style = {
            "fg_color": COLORS["surface"],
            "corner_radius": 4,
            "border_width": 1,
            "border_color": COLORS["overlay"],
        }

        # Subtle hover - darker instead of bright purple
        item_style = {
            "fg_color": "transparent",
            "hover_color": COLORS["overlay"],
            "text_color": COLORS["text"],
            "font": ctk.CTkFont(size=12),
            "corner_radius": 4,
            "height": 26,
            "anchor": "w"
        }

        # File dropdown
        self.file_dropdown = ctk.CTkFrame(self, **dropdown_style)
        ctk.CTkButton(
            self.file_dropdown,
            text="Settings",
            width=100,
            command=lambda: self._menu_action(self._on_settings),
            **item_style
        ).pack(fill="x", padx=4, pady=(4, 2))

        # Separator
        sep_file = ctk.CTkFrame(self.file_dropdown, fg_color=COLORS["overlay"], height=1)
        sep_file.pack(fill="x", padx=8, pady=2)

        ctk.CTkButton(
            self.file_dropdown,
            text="Exit",
            width=100,
            command=lambda: self._menu_action(self._on_closing),
            **item_style
        ).pack(fill="x", padx=4, pady=(2, 4))

        # Projects dropdown
        self.projects_dropdown = ctk.CTkFrame(self, **dropdown_style)
        ctk.CTkButton(
            self.projects_dropdown,
            text="Add Project...",
            width=130,
            command=lambda: self._menu_action(self._on_add_project),
            **item_style
        ).pack(fill="x", padx=4, pady=(4, 2))

        # Separator
        sep = ctk.CTkFrame(self.projects_dropdown, fg_color=COLORS["overlay"], height=1)
        sep.pack(fill="x", padx=8, pady=2)

        ctk.CTkButton(
            self.projects_dropdown,
            text="Start All",
            width=130,
            command=lambda: self._menu_action(self._on_start_all),
            **item_style
        ).pack(fill="x", padx=4, pady=2)

        ctk.CTkButton(
            self.projects_dropdown,
            text="Stop All",
            width=130,
            command=lambda: self._menu_action(self._on_stop_all),
            **item_style
        ).pack(fill="x", padx=4, pady=(2, 4))

        # Help dropdown
        self.help_dropdown = ctk.CTkFrame(self, **dropdown_style)
        ctk.CTkButton(
            self.help_dropdown,
            text=f"About {APP_NAME}",
            width=130,
            command=lambda: self._menu_action(self._show_about),
            **item_style
        ).pack(fill="x", padx=4, pady=4)

        # Store dropdown references
        self._dropdowns = {
            "file": (self.file_dropdown, self.file_btn),
            "projects": (self.projects_dropdown, self.projects_btn),
            "help": (self.help_dropdown, self.help_btn)
        }

    def _toggle_dropdown(self, menu_name: str):
        """Toggle a dropdown menu visibility."""
        # If clicking the same menu, close it
        if self._active_menu == menu_name:
            self._hide_all_dropdowns()
            return

        # Hide any open dropdown
        self._hide_all_dropdowns()

        # Show the clicked dropdown
        dropdown, btn = self._dropdowns[menu_name]

        dropdown.place(in_=btn, relx=0, rely=1, x=0, y=0)
        dropdown.tkraise()  # Bring to front above all other widgets
        self._active_menu = menu_name

    def _hide_all_dropdowns(self):
        """Hide all dropdown menus."""
        for dropdown, _ in self._dropdowns.values():
            dropdown.place_forget()
        self._active_menu = None

    def _menu_action(self, action_func):
        """Execute a menu action and close dropdown."""
        self._hide_all_dropdowns()
        action_func()

    def _on_add_project(self):
        """Open add project dialog from menu."""
        self.dashboard._on_add_project()  # pylint: disable=protected-access

    def _on_start_all(self):
        """Start all projects from menu."""
        self.dashboard._on_start_all()  # pylint: disable=protected-access

    def _on_stop_all(self):
        """Stop all projects from menu."""
        self.dashboard._on_stop_all()  # pylint: disable=protected-access

    def _show_about(self):
        """Show about dialog with credits and quick guide."""
        AboutDialog(self)

    def _on_settings(self):
        """Show the settings panel on the right side (replaces log panel)."""
        self._show_right_panel("settings")

    def _show_right_panel(self, panel: str):
        """Switch the right-side panel. panel = 'log' | 'settings' | 'filters' | 'project'."""
        current = self._get_right_widget()
        if current:
            current.grid_forget()

        self._right_panel = panel

        # Manage Esc binding
        self.unbind("<Escape>")
        if panel in ("settings", "filters", "project"):
            self.bind("<Escape>", lambda _e: self._esc_from_panel())

        if panel == "settings":
            if self._settings_panel is None:
                self._settings_panel = SettingsPanel(
                    self,
                    on_back=lambda: self._show_right_panel("log"),
                    on_log_filters=lambda: self._show_right_panel("filters"),
                    on_saved=self._on_settings_saved,
                )
            else:
                self._settings_panel.refresh()
        elif panel == "filters":
            if self._filter_panel is None:
                self._filter_panel = LogFilterPanel(
                    self,
                    on_back=lambda: self._show_right_panel("settings"),
                    on_saved=self._on_settings_saved,
                )
            else:
                self._filter_panel.refresh()
        # "project" panel is prepared externally before calling _show_right_panel

        self._place_right_panel(self._get_right_widget())

    def _esc_from_panel(self):
        """Handle Escape key: go back one level in the right panel stack."""
        if self._right_panel == "filters":
            if self._filter_panel:
                self._filter_panel._go_back()  # pylint: disable=protected-access
        elif self._right_panel == "settings":
            if self._settings_panel:
                self._settings_panel._go_back()  # pylint: disable=protected-access
        elif self._right_panel == "project":
            if self._project_panel:
                self._project_panel._cancel()  # pylint: disable=protected-access

    def _on_project_form_requested(self, project=None):
        """Called by Dashboard when Add or Edit is clicked."""
        if self._project_panel is None:
            self._project_panel = ProjectFormPanel(
                self,
                on_back=lambda: self._show_right_panel("log"),
                on_saved=self._on_project_saved,
            )
        if project is None:
            self._project_panel.reset_for_add()
        else:
            self._project_panel.load_project(project)
        self._show_right_panel("project")

    def _on_project_saved(self, _project):
        """Called after a project is added or edited – refresh the dashboard."""
        self.dashboard._refresh_projects()  # pylint: disable=protected-access
    def _get_right_widget(self):
        """Return the widget currently assigned to the right panel slot."""
        if self._right_panel == "settings":
            return self._settings_panel
        if self._right_panel == "filters":
            return self._filter_panel
        if self._right_panel == "project":
            return self._project_panel
        return self.log_panel

    def _place_right_panel(self, widget):
        """Grid a widget into the right panel slot."""
        if widget is None:
            return
        if self._layout_mode == "desktop":
            widget.grid(row=1, column=1, padx=(5, 10), pady=10, sticky="nsew")
        else:
            widget.grid(row=2, column=0, columnspan=2, padx=10, pady=(5, 10), sticky="nsew")

    def _on_settings_saved(self):
        """Reload settings and apply log filters after saving."""
        self._settings = load_settings()
        self.log_panel.reload_filters(self._settings.get("log_filters", []))

    def _setup_ui(self):
        """Setup the main UI layout."""
        # Initialize layout state
        self._layout_mode = "desktop"  # or "mobile"

        # Configure initial grid
        self._configure_grid_desktop()

        # Dashboard (left side)
        self.dashboard = Dashboard(
            self,
            process_manager=self.process_manager,
            on_view_logs=self._show_logs,
            on_project_form=self._on_project_form_requested,
        )
        # Grid position will be set by _update_layout

        # Log panel (right side or bottom)
        self.log_panel = LogPanel(self)

        # Status bar at bottom
        self.status_bar = ctk.CTkFrame(self, fg_color=COLORS["mantle"], height=25, corner_radius=0)

        self.status_label = ctk.CTkLabel(
            self.status_bar,
            text="Ready",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["subtext"],
            anchor="w"
        )
        self.status_label.pack(side="left", padx=10, pady=3)

        # Initial layout update
        self._update_layout()

        # Bind resize event
        self.bind("<Configure>", self._on_resize)

    def _configure_grid_desktop(self):
        """Configure grid for desktop layout (side-by-side)."""
        # Reset mobile settings
        self.grid_rowconfigure(3, weight=0)
        self.grid_columnconfigure(0, weight=3, uniform="group1")
        self.grid_columnconfigure(1, weight=2, uniform="group1")

        # Set desktop rows
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=0)

    def _configure_grid_mobile(self):
        """Configure grid for mobile layout (stacked)."""
        # Reset desktop settings (remove from uniform group)
        self.grid_columnconfigure(0, weight=1, uniform="")
        self.grid_columnconfigure(1, weight=0, uniform="")

        # Set mobile rows
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self.grid_rowconfigure(3, weight=0)

    def _on_resize(self, event):
        """Handle window resize to switch layouts."""
        if event.widget != self:
            return

        width = self.winfo_width()
        height = self.winfo_height()
        aspect_ratio = width / height if height > 0 else 999

        new_mode = "desktop" if aspect_ratio >= 1.3 else "mobile"

        if new_mode != self._layout_mode:
            self._layout_mode = new_mode
            self._update_layout()

    def _update_layout(self):
        """Update widget positions based on current layout mode."""
        right_widget = self._get_right_widget()

        # Clear current grid (dashboard is ALWAYS left – never replaced)
        self.dashboard.grid_forget()
        if right_widget:
            right_widget.grid_forget()
        self.status_bar.grid_forget()

        if self._layout_mode == "desktop":
            self._configure_grid_desktop()

            # Dashboard: always left
            self.dashboard.grid(row=1, column=0, padx=(10, 5), pady=10, sticky="nsew")

            # Right panel
            if right_widget:
                right_widget.grid(row=1, column=1, padx=(5, 10), pady=10, sticky="nsew")

            self.status_bar.grid(row=2, column=0, columnspan=2, sticky="ew")

        else:  # mobile/stacked
            self._configure_grid_mobile()

            self.dashboard.grid(row=1, column=0, columnspan=2, padx=10, pady=(10, 5), sticky="nsew")

            if right_widget:
                right_widget.grid(row=2, column=0, columnspan=2, padx=10, pady=(5, 10), sticky="nsew")

            self.status_bar.grid(row=3, column=0, columnspan=2, sticky="ew")

    def _on_status_changed(self, project_id: int, status: str):
        """Handle project status change."""
        self.after(0, lambda: self.dashboard.update_project_status(project_id, status))
        self.after(0, self._update_status_bar)

    def _on_log_received(self, project_id: int, line: str):
        """Handle new log line."""
        self.after(0, lambda: self.log_panel.add_log(project_id, line))

    def _on_crash_detected(self, project_id: int, name: str, exit_code: int, logs: str):  # pylint: disable=unused-argument
        """Handle process crash."""
        def show_crash():
            self.log_panel.set_project(project_id, name)
            self.log_panel.add_log(project_id, f"\n{'='*50}")
            self.log_panel.add_log(project_id, f"⚠️ CRASHED with exit code {exit_code}")
            self.log_panel.add_log(project_id, f"{'='*50}\n")
            messagebox.showwarning(
                "Process Crashed",
                f"'{name}' crashed with exit code {exit_code}"
            )
        self.after(0, show_crash)

    def _show_logs(self, project_id: int, project_name: str):
        """Show logs for a project (switches back to log panel if needed)."""
        if self._right_panel != "log":
            self._show_right_panel("log")
        self.log_panel.set_project(project_id, project_name)

    def _update_status_bar(self):
        """Update the status bar."""
        total = self.dashboard.get_project_count()
        running = self.dashboard.get_running_count()
        self.status_label.configure(text=f"Projects: {total} | Running: {running}")

    def bring_to_front(self):
        """Restore and raise the window (called when a second instance is launched)."""
        # Schedule on the main thread via after()
        self.after(0, self._do_bring_to_front)

    def _do_bring_to_front(self):
        """Actual window-raise logic (must run on the Tkinter main thread)."""
        self.deiconify()      # Restore if minimised
        self.lift()           # Raise above other windows
        self.focus_force()    # Steal keyboard focus

    def _on_closing(self):
        """Handle window close button.

        If 'minimize_to_tray' is enabled the window is hidden and a tray icon
        appears.  File -> Exit always destroys the window.
        """
        if self._settings.get("minimize_to_tray", False):
            # Hide window and show tray icon
            self.withdraw()
            self._tray.show()
            return

        # Normal exit path
        self._tray.hide()
        running = self.dashboard.get_running_count()
        if running > 0:
            if not messagebox.askyesno(
                "Confirm Exit",
                f"There are {running} running project(s).\nStop them and exit?"
            ):
                return

        self.process_manager.stop_all()
        self.destroy()

    def _restore_from_tray(self):
        """Restore the window when the user clicks 'Show' in the tray menu."""
        self.deiconify()
        self.lift()
        self.focus_force()

    def _force_quit(self):
        """Exit the application from the tray 'Exit' menu item."""
        self.process_manager.stop_all()
        self.destroy()
