"""Animated button with 3D depth effect using generated images for pixel-perfect rendering."""

from typing import Callable, Optional

import customtkinter as ctk
from PIL import Image, ImageDraw, ImageFont


class DepthButton(ctk.CTkLabel):
    """
    Button that renders itself fully as an image using PIL.
    This bypasses all tkinter/ctk rendering artifacts (black corners, layering issues).
    """
    # pylint: disable=too-many-ancestors,too-many-instance-attributes

    def __init__(
        self,
        master,
        text: str,
        base_color: str,
        hover_color: str,
        shadow_color: str,
        image: Optional[ctk.CTkImage] = None, # Kept for signature, ignored for now
        command: Optional[Callable] = None,
        width: int = 110,
        height: int = 32,
        bg_color: str = "transparent",
        **kwargs
    ):
        # pylint: disable=too-many-locals,too-many-arguments,too-many-positional-arguments,unused-argument
        self._text_str = text
        self._base_color = base_color
        self._hover_color = hover_color
        self._shadow_color = shadow_color
        self._command = command
        self._width = width
        self._height = height
        self._icon = image  # Initialize icon BEFORE generating images

        # State
        self._is_enabled = True

        # Design constants
        self._shadow_offset = 3
        self._corner_radius = 11  # Matches the design

        # Canvas size needs to accommodate the offset
        self._img_width = width + self._shadow_offset
        self._img_height = height + self._shadow_offset

        # Generate images for states
        # Pre-generating ensures smooth performance
        self._img_normal = self._generate_image(base_color, offset_y=0, is_pressed=False)
        self._img_hover = self._generate_image(hover_color, offset_y=0, is_pressed=False)

        # Pressed: darkens color + moves content/face down-right
        pressed_color = self._adjust_brightness(base_color, 0.9)
        self._img_pressed = self._generate_image(pressed_color, offset_y=2, is_pressed=True)

        # Initialize as a Label that displays the image
        super().__init__(
            master,
            text="",  # Text is baked into the image
            image=self._img_normal,
            fg_color="transparent", # Crucial! Lets the parent bg show through transparent pixels
            width=self._img_width,
            height=self._img_height,
            cursor="hand2",
            **kwargs
        )

        # Bind events
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)

    def _generate_image(self, face_color, offset_y=0, is_pressed=False):
        """Generates a high-quality CTkImage for a specific state."""
        # pylint: disable=too-many-locals,too-many-statements
        scale = 3 # 3x scale for super smooth anti-aliasing
        w = self._img_width * scale
        h = self._img_height * scale
        r = self._corner_radius * scale

        shadow_off_x = self._shadow_offset * scale
        shadow_off_y = self._shadow_offset * scale

        # Calculate Face Position
        press_off = (offset_y * scale) if is_pressed else 0
        face_x = press_off
        face_y = press_off

        # Create transparent canvas
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # 1. Draw Shadow
        shadow_rect = [
            shadow_off_x,
            shadow_off_y,
            shadow_off_x + (self._width * scale),
            shadow_off_y + (self._height * scale)
        ]
        draw.rounded_rectangle(shadow_rect, radius=r, fill=self._shadow_color)

        # 2. Draw Face
        face_rect = [
            face_x,
            face_y,
            face_x + (self._width * scale),
            face_y + (self._height * scale)
        ]
        draw.rounded_rectangle(face_rect, radius=r, fill=face_color)

        # 3. Content (Icon + Text)
        # Load font
        font_size = 13 * scale
        try:
            font = ImageFont.truetype("arialbd.ttf", font_size)
        except IOError:
            font = ImageFont.load_default()

        # Measure text (unused text_h removed implicitly by just extracting text_w)
        bbox = draw.textbbox((0, 0), self._text_str, font=font)
        text_w = bbox[2] - bbox[0]

        # Icon dimensions
        icon_size = 0
        gap = 8 * scale  # Gap between icon and text
        icon_img = None

        if self._icon:
            # Extract PIL image from CTkImage (use dark_image as source)
            # CTkImage stores PIL images in _dark_image/_light_image
            original_icon = self._icon._dark_image  # pylint: disable=protected-access
            if original_icon:
                # Resize icon to fit text height roughly (or fixed size 16-20px)
                target_icon_h = font_size + (4 * scale) # Slightly larger than text
                aspect = original_icon.width / original_icon.height
                icon_w = int(target_icon_h * aspect)
                icon_h = int(target_icon_h)

                resample_filter = getattr(Image, 'Resampling', Image).LANCZOS
                icon_img = original_icon.resize((icon_w, icon_h), resample_filter)

                # Recolor icon to text color (#1e1e2e)
                # This assumes icon has transparency. We use alpha as mask for solid color.
                if icon_img.mode != 'RGBA':
                    icon_img = icon_img.convert('RGBA')

                # Create a solid color image
                solid_color = Image.new('RGBA', icon_img.size, "#1e1e2e")
                # Composite: use icon's alpha channel as mask
                icon_img = Image.composite(
                    solid_color,
                    Image.new('RGBA', icon_img.size, (0,0,0,0)),
                    icon_img
                )

                icon_size = icon_w

        # Calculate total content width
        total_w = text_w
        if icon_img:
            total_w += icon_size + gap

        # Center content
        face_w = face_rect[2] - face_rect[0]
        face_h = face_rect[3] - face_rect[1]

        start_x = face_rect[0] + (face_w - total_w) / 2
        center_y = face_rect[1] + (face_h) / 2

        # Draw Icon
        current_x = start_x
        if icon_img:
            icon_y = int(center_y - icon_img.height / 2)
            img.paste(icon_img, (int(current_x), int(icon_y)), icon_img)
            current_x += icon_size + gap

        # Draw Text
        # text anchor 'lm' = left middle
        draw.text((current_x, center_y), self._text_str, fill="#1e1e2e", font=font, anchor="lm")

        # Downscale
        resample_filter = getattr(Image, 'Resampling', Image).LANCZOS
        img = img.resize((self._img_width, self._img_height), resample_filter)

        return ctk.CTkImage(
            light_image=img,
            dark_image=img,
            size=(self._img_width, self._img_height)
        )

    def _adjust_brightness(self, hex_color, factor):
        if hex_color.startswith("#"):
            hex_color = hex_color.lstrip('#')
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        new_rgb = tuple(int(c * factor) for c in rgb)
        return f"#{new_rgb[0]:02x}{new_rgb[1]:02x}{new_rgb[2]:02x}"

    def _on_enter(self, _event):
        if self._is_enabled:
            self.configure(image=self._img_hover)

    def _on_leave(self, _event):
        if self._is_enabled:
            self.configure(image=self._img_normal)

    def _on_press(self, _event):
        if self._is_enabled:
            self.configure(image=self._img_pressed)

    def _on_release(self, _event):
        if self._is_enabled:
            self.configure(image=self._img_hover)
            # Invoke command
            if self._command:
                self._command()

    def configure(self, require_redraw=False, **kwargs):
        # pylint: disable=arguments-differ
        if "state" in kwargs:
            state = kwargs.pop("state")
            self._is_enabled = state != "disabled"
        super().configure(**kwargs)


def create_depth_button(
    master,
    text: str,
    base_color: str,
    hover_color: str,
    shadow_color: Optional[str] = None,
    image: Optional[ctk.CTkImage] = None,
    command: Optional[Callable] = None,
    width: int = 110,
    height: int = 32,
    bg_color: str = "transparent",
    **kwargs
) -> DepthButton:
    """Create a button with 3D depth effect."""
    # pylint: disable=too-many-locals,too-many-arguments,too-many-positional-arguments
    if shadow_color is None:
        hex_color = base_color.lstrip('#')
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        r, g, b = int(r * 0.6), int(g * 0.6), int(b * 0.6)
        shadow_color = f"#{r:02x}{g:02x}{b:02x}"

    return DepthButton(
        master,
        text=text,
        base_color=base_color,
        hover_color=hover_color,
        shadow_color=shadow_color,
        image=image, # Pass the actual image object
        command=command,
        width=width,
        height=height,
        bg_color=bg_color,
        **kwargs
    )
