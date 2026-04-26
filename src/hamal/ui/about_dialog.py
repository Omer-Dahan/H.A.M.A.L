"""About dialog window."""

import customtkinter as ctk

from hamal.core.config import APP_NAME, APP_VERSION


class AboutDialog(ctk.CTkToplevel):
    """Dialog displaying application information."""
    def __init__(self, parent):
        super().__init__(parent)

        self.title(f"About {APP_NAME}")
        self.geometry("400x450")
        self.resizable(False, False)
        # Center the window
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"+{x}+{y}")
        # Make it modal
        self.transient(parent)
        self.grab_set()
        self.focus_force()
        self._setup_ui()
    def _setup_ui(self):
        # Main container
        self.grid_columnconfigure(0, weight=1)

        # Logo
        from PIL import Image  # pylint: disable=import-outside-toplevel

        from hamal.ui.icons import get_icons_dir  # pylint: disable=import-outside-toplevel

        try:
            # Use specific size icon for best quality
            img_path = get_icons_dir() / "icon_128.png"
            if img_path.exists():
                pil_img = Image.open(img_path)
                large_logo = ctk.CTkImage(
                    light_image=pil_img,
                    dark_image=pil_img,
                    size=(100, 100)
                )

                logo_label = ctk.CTkLabel(
                    self,
                    text="",
                    image=large_logo
                )
                logo_label.grid(row=0, column=0, pady=(30, 10))
        except Exception as e:  # pylint: disable=broad-exception-caught
            print(f"Error loading logo: {e}")

        # App Name & Version
        ctk.CTkLabel(
            self,
            text=APP_NAME,
            font=ctk.CTkFont(size=24, weight="bold")
        ).grid(row=1, column=0, pady=(0, 5))

        ctk.CTkLabel(
            self,
            text=f"v{APP_VERSION}",
            font=ctk.CTkFont(size=14),
            text_color="gray"
        ).grid(row=2, column=0, pady=(0, 20))

        # Description
        desc = "Hybrid Automated Management And Logging"
        ctk.CTkLabel(
            self,
            text=desc,
            font=ctk.CTkFont(size=13)
        ).grid(row=3, column=0, pady=5)

        # Divider
        ctk.CTkFrame(
            self,
            height=2,
            fg_color="gray30"
        ).grid(row=4, column=0, sticky="ew", padx=40, pady=20)

        # Credits
        ctk.CTkLabel(
            self,
            text="Made with ❤️ by Omer Dahan",
            font=ctk.CTkFont(size=13)
        ).grid(row=5, column=0, pady=5)

        # Close button
        ctk.CTkButton(
            self,
            text="Close",
            command=self.destroy,
            width=100
        ).grid(row=6, column=0, pady=(30, 20))
