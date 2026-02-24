"""Settings panel – rendered inside the main window (replaces the log panel)."""

import customtkinter as ctk

from hamal.core.config import load_settings, save_settings

# Catppuccin Mocha colors (same palette as MainWindow)
_COLORS = {
    "base":    "#1e1e2e",
    "mantle":  "#181825",
    "surface": "#313244",
    "overlay": "#45475a",
    "text":    "#cdd6f4",
    "subtext": "#a6adc8",
    "blue":    "#89b4fa",
}


def _patch_scroll_speed(scroll_frame, lines: int = 3):
    """Make CTkScrollableFrame scroll faster (Windows default is 1 line per notch)."""
    canvas = scroll_frame._parent_canvas  # pylint: disable=protected-access

    def _fast_scroll(event):
        if event.delta:
            canvas.yview_scroll(-int(event.delta / abs(event.delta)) * lines, "units")

    canvas.bind("<MouseWheel>", _fast_scroll)
    scroll_frame.bind("<MouseWheel>", _fast_scroll)


class SettingsPanel(ctk.CTkFrame):
    """Settings view embedded inside the main window.

    Parameters
    ----------
    master:
        Parent widget (MainWindow).
    on_back:
        Callable invoked when the user presses "← Back".
    on_log_filters:
        Callable invoked when the user clicks "Configure…" for log filters.
    on_saved:
        Callable invoked after the user saves settings.
    """

    def __init__(self, master, on_back=None, on_log_filters=None, on_saved=None, **kwargs):
        super().__init__(master, fg_color=_COLORS["base"], **kwargs)
        self._on_back = on_back
        self._on_log_filters = on_log_filters
        self._on_saved = on_saved

        # Load current settings
        self._settings = load_settings()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._setup_ui()

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def refresh(self):
        """Reload settings from disk before showing the panel."""
        self._settings = load_settings()
        self._tray_var.set(self._settings.get("minimize_to_tray", False))

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _setup_ui(self):
        """Build the panel layout."""
        content = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_button_color=_COLORS["overlay"],
            scrollbar_button_hover_color=_COLORS["blue"],
        )
        content.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        content.grid_columnconfigure(0, weight=1)
        # Speed up mouse-wheel scrolling on Windows
        _patch_scroll_speed(content)

        # ── Page header (3-column: Back │ Title centered │ Esc) ───────
        header_frame = ctk.CTkFrame(content, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=8, pady=(12, 4))
        header_frame.grid_columnconfigure(0, weight=1)
        header_frame.grid_columnconfigure(1, weight=1)
        header_frame.grid_columnconfigure(2, weight=1)

        ctk.CTkButton(
            header_frame,
            text="← Back",
            width=90, height=34,
            fg_color=_COLORS["surface"],
            hover_color=_COLORS["overlay"],
            text_color=_COLORS["blue"],
            font=ctk.CTkFont(size=14, weight="bold"),
            corner_radius=8,
            command=self._go_back,
        ).grid(row=0, column=0, sticky="w", padx=(0, 4))

        ctk.CTkLabel(
            header_frame,
            text="Settings",
            font=ctk.CTkFont(size=17, weight="bold"),
            text_color=_COLORS["text"],
            anchor="center",
        ).grid(row=0, column=1, sticky="ew")

        ctk.CTkLabel(
            header_frame,
            text="Esc to go back",
            font=ctk.CTkFont(size=11),
            text_color=_COLORS["subtext"],
            anchor="e",
        ).grid(row=0, column=2, sticky="e", padx=(4, 8))

        ctk.CTkFrame(content, height=1, fg_color=_COLORS["overlay"]).grid(
            row=1, column=0, sticky="ew", padx=16, pady=(4, 0)
        )

        # ── Section: Window ────────────────────────────────────────────
        self._section_label(content, "Window", row=2)

        tray_row = self._option_row(
            content,
            label="Minimize to tray on close  (X button)",
            description="Hides the window instead of exiting when you press ×.",
            row=3,
        )
        self._tray_var = ctk.BooleanVar(value=self._settings.get("minimize_to_tray", False))
        # Switch on the LEFT (col=0), label stays at col=1
        ctk.CTkSwitch(
            tray_row,
            text="",
            variable=self._tray_var,
            onvalue=True, offvalue=False,
            progress_color=_COLORS["blue"],
        ).grid(row=0, column=0, padx=(14, 4), pady=14)

        # ── Section: Logs ──────────────────────────────────────────────────
        self._section_label(content, "Logs", row=4)

        filter_row = self._option_row(
            content,
            label="Log line color filters",
            description="Highlight lines matching a pattern with a custom color.",
            row=5,
        )
        ctk.CTkButton(
            filter_row,
            text="Configure…",
            width=100, height=28,
            fg_color=_COLORS["blue"],
            hover_color="#74a8e8",
            text_color="#1e1e2e",
            command=self._open_filters,
        ).grid(row=0, column=2, padx=(8, 16), pady=14)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _section_label(self, parent, text: str, row: int):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.grid(row=row, column=0, sticky="ew", padx=16, pady=(14, 2))
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
        row_frame = ctk.CTkFrame(parent, fg_color=_COLORS["surface"], corner_radius=8)
        row_frame.grid(row=row, column=0, sticky="ew", padx=16, pady=3)
        row_frame.grid_columnconfigure(1, weight=1)  # label expands

        # Control widget goes at col=2 (right side) – caller fills it in
        text_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
        text_frame.grid(row=0, column=1, padx=(8, 0), pady=10, sticky="w")

        ctk.CTkLabel(
            text_frame, text=label,
            font=ctk.CTkFont(size=13), text_color=_COLORS["text"], anchor="w",
        ).pack(anchor="w")

        if description:
            ctk.CTkLabel(
                text_frame, text=description,
                font=ctk.CTkFont(size=11), text_color=_COLORS["subtext"], anchor="w",
            ).pack(anchor="w")

        return row_frame

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _open_filters(self):
        """Navigate to the log filter panel (via main_window callback)."""
        if self._on_log_filters:
            self._on_log_filters()

    def _go_back(self):
        """Save settings and return to the log panel."""
        self._settings["minimize_to_tray"] = self._tray_var.get()
        save_settings(self._settings)
        if self._on_saved:
            self._on_saved()
        if self._on_back:
            self._on_back()
