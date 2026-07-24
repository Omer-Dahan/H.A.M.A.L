"""About panel – rendered inside the main window (replaces the log panel)."""

import customtkinter as ctk
from PIL import Image

from hamal.core.config import APP_NAME, APP_VERSION
from hamal.core.i18n import t
from hamal.ui.icons import get_icons_dir

# Catppuccin Mocha theme colors matching main UI
COLORS = {
    "base": "#1e1e2e",
    "mantle": "#181825",
    "surface": "#313244",
    "overlay": "#45475a",
    "text": "#cdd6f4",
    "subtext": "#a6adc8",
    "blue": "#89b4fa",
    "pink": "#f5c2e7",
    "mauve": "#cba6f7",
    "green": "#a6e3a1",
    "red": "#f38ba8",
}


def _patch_scroll_speed(scroll_frame, lines: int = 55):
    """Make CTkScrollableFrame scroll significantly faster and smoother."""
    canvas = scroll_frame._parent_canvas  # pylint: disable=protected-access

    def _fast_scroll(event):
        try:
            if not canvas.winfo_exists():
                return

            widget = event.widget
            is_child = False
            try:
                temp = widget
                while temp:
                    if temp == scroll_frame:
                        is_child = True
                        break
                    temp = temp.master
            except (AttributeError, KeyError):
                pass

            if not is_child:
                return

            if event.delta:
                canvas.yview_scroll(-int(event.delta / 120) * lines, "units")
                return "break"
        except Exception:  # pylint: disable=broad-exception-caught
            pass

    scroll_frame.bind_all("<MouseWheel>", _fast_scroll, add="+")


class AboutPanel(ctk.CTkFrame):
    """About view embedded inside the main window (replaces the log panel)."""

    def __init__(self, master, on_back=None, **kwargs):
        super().__init__(master, fg_color=COLORS["base"], **kwargs)
        self._on_back = on_back

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)  # Header
        self.grid_rowconfigure(1, weight=1)  # Content

        self._setup_ui()

    def _go_back(self):
        """Navigate back to logs."""
        if callable(self._on_back):
            self._on_back()

    def _setup_ui(self):
        """Build the panel layout."""
        # ── Page header (3-column: Back │ Title centered │ Esc) ───────
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=(5, 10))
        header_frame.grid_columnconfigure(0, weight=1)
        header_frame.grid_columnconfigure(1, weight=1)
        header_frame.grid_columnconfigure(2, weight=1)

        ctk.CTkButton(
            header_frame,
            text=t("← Back"),
            width=100,
            height=35,
            fg_color=COLORS["surface"],
            hover_color=COLORS["overlay"],
            text_color=COLORS["blue"],
            font=ctk.CTkFont(size=14, weight="bold"),
            corner_radius=12,
            command=self._go_back,
        ).grid(row=0, column=0, sticky="w", padx=(5, 4))

        ctk.CTkLabel(
            header_frame,
            text=f"{t('About')} {APP_NAME}",
            font=ctk.CTkFont(size=19, weight="bold"),
            text_color=COLORS["text"],
            anchor="center",
        ).grid(row=0, column=1, sticky="ew")

        ctk.CTkLabel(
            header_frame,
            text=t("Esc to go back"),
            font=ctk.CTkFont(size=11),
            text_color=COLORS["subtext"],
            anchor="e",
        ).grid(row=0, column=2, sticky="e", padx=(4, 15))

        # ── Scrollable Content Area ────────────────────────────────────
        content = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            corner_radius=0,
        )
        content.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        content.grid_columnconfigure(0, weight=1)
        _patch_scroll_speed(content)

        # ── 1. Hero Card ──────────────────────────────────────────────
        hero_frame = ctk.CTkFrame(
            content,
            fg_color=COLORS["mantle"],
            corner_radius=14,
            border_width=1,
            border_color=COLORS["surface"]
        )
        hero_frame.grid(row=0, column=0, padx=10, pady=(10, 15), sticky="ew")
        hero_frame.grid_columnconfigure(0, weight=1)

        # Logo
        logo_loaded = False
        icons_dir = get_icons_dir()
        for icon_filename in ["256.png", "128.png", "48.png", "32.png"]:
            img_path = icons_dir / icon_filename
            if img_path.exists():
                try:
                    pil_img = Image.open(img_path)
                    logo_img = ctk.CTkImage(
                        light_image=pil_img,
                        dark_image=pil_img,
                        size=(96, 96)
                    )
                    logo_label = ctk.CTkLabel(
                        hero_frame,
                        text="",
                        image=logo_img
                    )
                    logo_label.grid(row=0, column=0, pady=(24, 12))
                    logo_loaded = True
                    break
                except Exception as e:  # pylint: disable=broad-exception-caught
                    print(f"Error loading logo from {img_path}: {e}")

        if not logo_loaded:
            fallback_label = ctk.CTkLabel(
                hero_frame,
                text="⚡",
                font=ctk.CTkFont(size=56)
            )
            fallback_label.grid(row=0, column=0, pady=(24, 12))

        # Title & Version Badge Container
        title_container = ctk.CTkFrame(hero_frame, fg_color="transparent")
        title_container.grid(row=1, column=0, pady=(0, 6))

        ctk.CTkLabel(
            title_container,
            text=APP_NAME,
            font=ctk.CTkFont(family="Segoe UI", size=26, weight="bold"),
            text_color=COLORS["text"]
        ).pack(side="left", padx=(0, 10))

        # Version Pill Badge
        version_badge = ctk.CTkFrame(
            title_container,
            fg_color=COLORS["surface"],
            corner_radius=8
        )
        version_badge.pack(side="left")

        ctk.CTkLabel(
            version_badge,
            text=f"v{APP_VERSION}",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=COLORS["mauve"]
        ).pack(padx=10, pady=3)

        # Full Name Subtitle
        ctk.CTkLabel(
            hero_frame,
            text="Hybrid Automated Management And Logging",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color=COLORS["subtext"]
        ).grid(row=2, column=0, pady=(0, 20))

        # ── 2. Key Capabilities Card ──────────────────────────────────
        features_frame = ctk.CTkFrame(
            content,
            fg_color=COLORS["mantle"],
            corner_radius=14,
            border_width=1,
            border_color=COLORS["surface"]
        )
        features_frame.grid(row=1, column=0, padx=10, pady=10, sticky="ew")
        features_frame.grid_columnconfigure(0, weight=1)

        # Section Header
        ctk.CTkLabel(
            features_frame,
            text=t("Key Features"),
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color=COLORS["blue"]
        ).grid(row=0, column=0, padx=18, pady=(16, 10), sticky="w")

        features = [
            ("🚀", "Multi-Project Process Orchestration", "Run, manage, and monitor multiple independent Python applications simultaneously."),
            ("📊", "Live Interactive Log Filtering & Colorization", "Real-time log stream viewing with customizable regex/text filters and color coding."),
            ("⚙️", "Automated Environment & Virtualenv Setup", "Automatic virtual environment detection, auto-creation, and dependency management."),
            ("🔔", "Tray Integration & Background Process Control", "Minimize to tray with ongoing background process execution and system control."),
        ]

        for idx, (icon, title_text, desc_text) in enumerate(features, start=1):
            item_frame = ctk.CTkFrame(features_frame, fg_color="transparent")
            item_frame.grid(row=idx, column=0, padx=18, pady=8, sticky="ew")
            item_frame.grid_columnconfigure(1, weight=1)

            ctk.CTkLabel(
                item_frame,
                text=icon,
                font=ctk.CTkFont(size=18),
                width=32
            ).grid(row=0, column=0, rowspan=2, padx=(0, 10), sticky="n")

            ctk.CTkLabel(
                item_frame,
                text=t(title_text),
                font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                text_color=COLORS["text"],
                anchor="w"
            ).grid(row=0, column=1, sticky="w")

            ctk.CTkLabel(
                item_frame,
                text=t(desc_text),
                font=ctk.CTkFont(family="Segoe UI", size=11),
                text_color=COLORS["subtext"],
                anchor="w",
                justify="left"
            ).grid(row=1, column=1, sticky="w")

        # Bottom padding inside features_frame
        ctk.CTkFrame(features_frame, height=8, fg_color="transparent").grid(row=len(features)+1, column=0)

        # ── 3. Developer & Credits Card (Centered) ───────────────────
        credits_card = ctk.CTkFrame(
            content,
            fg_color=COLORS["mantle"],
            corner_radius=14,
            border_width=1,
            border_color=COLORS["surface"]
        )
        credits_card.grid(row=2, column=0, padx=10, pady=(10, 20), sticky="ew")

        # Centered container inside credits_card
        credits_inner = ctk.CTkFrame(credits_card, fg_color="transparent")
        credits_inner.pack(pady=16, anchor="center")

        ctk.CTkLabel(
            credits_inner,
            text=t("Crafted with"),
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color=COLORS["subtext"]
        ).pack(side="left")

        # Styled glowing red/pink heart symbol
        ctk.CTkLabel(
            credits_inner,
            text=" ♥ ",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color=COLORS["red"]
        ).pack(side="left")

        ctk.CTkLabel(
            credits_inner,
            text=t("by Omer Dahan"),
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=COLORS["text"]
        ).pack(side="left")
