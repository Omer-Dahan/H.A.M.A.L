"""Log color filter panel – embedded inside the main window (replaces the log panel)."""

import re
import customtkinter as ctk

from hamal.core.config import load_settings, save_settings, _DEFAULT_SETTINGS
from hamal.ui.settings_dialog import _patch_scroll_speed

# Catppuccin Mocha palette – shown as color chips
PALETTE = [
    ("#a6e3a1", "Green"),
    ("#89b4fa", "Blue"),
    ("#f9e2af", "Yellow"),
    ("#f38ba8", "Red"),
    ("#cba6f7", "Mauve"),
    ("#89dceb", "Sky"),
    ("#fab387", "Peach"),
    ("#a6adc8", "Subtext"),
]

_COLORS = {
    "base":    "#1e1e2e",
    "mantle":  "#181825",
    "surface": "#313244",
    "overlay": "#45475a",
    "text":    "#cdd6f4",
    "subtext": "#a6adc8",
    "blue":    "#89b4fa",
    "red":     "#f38ba8",
}

_MATCH_OPTIONS = ["contains", "starts with"]
_MAX_FILTERS = 5


class LogFilterPanel(ctk.CTkFrame):
    """In-app log color filter configuration panel.

    Parameters
    ----------
    master:
        Parent widget (MainWindow).
    on_back:
        Callable invoked when the user presses "← Back".
    on_saved:
        Callable invoked after filters are saved (so the caller can apply them).
    """

    def __init__(self, master, on_back=None, on_saved=None, **kwargs):
        super().__init__(master, fg_color=_COLORS["base"], **kwargs)
        self._on_back = on_back
        self._on_saved = on_saved

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._settings = load_settings()
        self._prepare_filters()
        self._rows: list[dict] = []

        self._setup_ui()

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def refresh(self):
        """Reload filters from disk and rebuild rows."""
        self._settings = load_settings()
        self._prepare_filters()
        # Rebuild UI
        for widget in self.winfo_children():
            widget.destroy()
        self._rows.clear()
        self._setup_ui()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _prepare_filters(self):
        stored = self._settings.get("log_filters", [])
        defaults = _DEFAULT_SETTINGS["log_filters"]
        while len(stored) < _MAX_FILTERS:
            stored.append(dict(defaults[len(stored)]))
        self._filters = stored[:_MAX_FILTERS]

    def _setup_ui(self):
        """Build the panel layout."""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)  # Header
        self.grid_rowconfigure(1, weight=1)  # Content

        # ── Page header (3-column: Back │ Title centered │ Esc) ─────────
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=5, pady=(5, 10))
        header.grid_columnconfigure(0, weight=1)
        header.grid_columnconfigure(1, weight=1)
        header.grid_columnconfigure(2, weight=1)

        ctk.CTkButton(
            header,
            text="← Back",
            width=100, height=35,
            fg_color=_COLORS["surface"],
            hover_color=_COLORS["overlay"],
            text_color=_COLORS["blue"],
            font=ctk.CTkFont(size=14, weight="bold"),
            corner_radius=12,
            command=self._go_back,
        ).grid(row=0, column=0, sticky="w", padx=(5, 4))

        ctk.CTkLabel(
            header,
            text="Log Color Filters",
            font=ctk.CTkFont(size=19, weight="bold"),
            text_color=_COLORS["text"],
            anchor="center",
        ).grid(row=0, column=1, sticky="ew")

        ctk.CTkLabel(
            header,
            text="Esc to go back",
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
            row=0, column=0, sticky="ew", padx=16, pady=(0, 8)
        )

        # ── Filter rows ────────────────────────────────────────────────
        for i, flt in enumerate(self._filters):
            self._build_filter_row(scroll, i, flt, base_row=i + 2)

        # ── Save button ────────────────────────────────────────────────
        save_bar = ctk.CTkFrame(scroll, fg_color="transparent")
        save_bar.grid(row=_MAX_FILTERS + 2, column=0, pady=(16, 8), sticky="e", padx=16)

        ctk.CTkButton(
            save_bar,
            text="Save Filters",
            width=130, height=36,
            fg_color=_COLORS["blue"],
            hover_color="#74a8e8",
            text_color="#1e1e2e",
            font=ctk.CTkFont(size=13, weight="bold"),
            corner_radius=8,
            command=self._go_back,   # saves + goes back
        ).pack(side="right")

    def _build_filter_row(self, parent, index: int, flt: dict, base_row: int):
        """Build one filter row inside parent at base_row."""
        row_frame = ctk.CTkFrame(parent, fg_color=_COLORS["surface"], corner_radius=8)
        row_frame.grid(row=base_row, column=0, pady=4, padx=16, sticky="ew")
        row_frame.grid_columnconfigure(1, weight=1)

        # Enable switch
        enabled_var = ctk.BooleanVar(value=flt.get("enabled", False))
        ctk.CTkSwitch(
            row_frame, text="", variable=enabled_var,
            onvalue=True, offvalue=False,
            progress_color=_COLORS["blue"], width=44,
        ).grid(row=0, column=0, padx=(10, 6), pady=10)

        # Pattern entry
        pattern_entry = ctk.CTkEntry(
            row_frame,
            placeholder_text=f"Filter #{index + 1} pattern…",
            font=ctk.CTkFont(family="Consolas", size=12),
            fg_color=_COLORS["mantle"], border_color=_COLORS["overlay"],
            text_color=_COLORS["text"], height=30,
        )
        pattern_entry.grid(row=0, column=1, padx=4, pady=10, sticky="ew")
        if flt.get("prefix"):
            pattern_entry.insert(0, flt["prefix"])

        # Match type dropdown
        match_var = ctk.StringVar(value=flt.get("match_type", "contains"))
        ctk.CTkOptionMenu(
            row_frame, values=_MATCH_OPTIONS, variable=match_var,
            width=110, height=30,
            fg_color=_COLORS["overlay"], button_color=_COLORS["overlay"],
            button_hover_color=_COLORS["surface"],
            text_color=_COLORS["text"], font=ctk.CTkFont(size=11),
        ).grid(row=0, column=2, padx=(4, 8), pady=10)

        # Color chips row
        chips_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
        chips_frame.grid(row=1, column=0, columnspan=3, padx=10, pady=(0, 8), sticky="w")

        color_var = ctk.StringVar(value=flt.get("color", PALETTE[index % len(PALETTE)][0]))

        hex_entry = ctk.CTkEntry(
            chips_frame, textvariable=color_var,
            width=80, height=26,
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color=_COLORS["mantle"], border_color=_COLORS["overlay"],
            text_color=_COLORS["text"],
        )

        ctk.CTkLabel(
            chips_frame, text="Color:",
            font=ctk.CTkFont(size=11), text_color=_COLORS["subtext"],
        ).pack(side="left", padx=(0, 6))

        for hex_c, _ in PALETTE:
            ctk.CTkButton(
                chips_frame, text="", width=22, height=22, corner_radius=11,
                fg_color=hex_c, hover_color=hex_c, border_width=0,
                command=lambda h=hex_c, cv=color_var: cv.set(h),
            ).pack(side="left", padx=2)

        ctk.CTkLabel(
            chips_frame, text=" #hex:",
            font=ctk.CTkFont(size=11), text_color=_COLORS["subtext"],
        ).pack(side="left", padx=(8, 2))
        hex_entry.pack(side="left")

        preview_label = ctk.CTkLabel(
            chips_frame, text="Preview",
            font=ctk.CTkFont(family="Consolas", size=11),
        )
        preview_label.pack(side="left", padx=(10, 0))

        def update_preview(*_):
            raw = color_var.get().strip()
            if re.match(r"^#[0-9a-fA-F]{6}$", raw):
                preview_label.configure(text_color=raw, text="Preview")
        color_var.trace_add("write", update_preview)
        update_preview()

        self._rows.append({
            "enabled": enabled_var,
            "pattern": pattern_entry,
            "match_type": match_var,
            "color": color_var,
        })

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _go_back(self):
        """Save filters, call saved callback, then navigate back."""
        filters = []
        for row in self._rows:
            raw_color = row["color"].get().strip()
            if not re.match(r"^#[0-9a-fA-F]{6}$", raw_color):
                raw_color = "#cdd6f4"
            filters.append({
                "prefix":     row["pattern"].get().strip(),
                "match_type": row["match_type"].get(),
                "color":      raw_color,
                "enabled":    row["enabled"].get(),
            })

        self._settings["log_filters"] = filters
        save_settings(self._settings)

        if self._on_saved:
            self._on_saved()
        if self._on_back:
            self._on_back()


# Keep old name as alias so any stray import still works
LogFilterDialog = LogFilterPanel
