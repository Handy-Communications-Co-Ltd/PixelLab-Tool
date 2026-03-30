"""PixelLab GUI - 픽셀 아트 생성 도구."""

import os

import customtkinter as ctk

from ..client import PixelLabClient
from .common import (
    BasePanel,
    StatusBar,
    ImagePreview,
    SIDEBAR_ITEMS,
    DEFAULT_OUTPUT_DIR,
    OPERATION_COSTS,
    CHARACTER_SIZE_PRESETS,
    ANIMATION_TEMPLATES,
)
from .dashboard import DashboardPanel
from .generate import GeneratePanel
from .character import CharacterPanel
from .animation import AnimationPanel
from .tileset import TilesetPanel
from .edit import EditPanel
from .rotate import RotatePanel
from .settings import SettingsPanel


class PixelLabApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("PixelLab Tool - 픽셀 아트 생성기")
        self.geometry("1100x750")
        self.minsize(900, 600)

        self.client: PixelLabClient | None = None
        self.output_dir = DEFAULT_OUTPUT_DIR

        api_key = os.environ.get("PIXELLAB_API_KEY")
        if api_key:
            self.client = PixelLabClient(api_key)

        self._build_layout()

        if self.client:
            self.show_panel("Dashboard")
            # Auto-refresh balance on startup
            self.after(500, lambda: self._get_panel("Dashboard").refresh_balance())
        else:
            self.show_panel("Settings")

    def _build_layout(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # Sidebar
        self.sidebar = ctk.CTkFrame(self, width=160, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsw")
        self.sidebar.grid_propagate(False)

        logo_label = ctk.CTkLabel(self.sidebar, text="PixelLab", font=("", 22, "bold"))
        logo_label.pack(pady=(20, 5))
        ctk.CTkLabel(self.sidebar, text="픽셀 아트 도구", font=("", 11), text_color="gray").pack(pady=(0, 20))

        # Nav buttons
        self.nav_buttons: dict[str, ctk.CTkButton] = {}
        for label, key in SIDEBAR_ITEMS:
            btn = ctk.CTkButton(
                self.sidebar,
                text=f"  {label}",
                anchor="w",
                height=36,
                corner_radius=8,
                fg_color="transparent",
                text_color=("gray10", "gray90"),
                hover_color=("gray70", "gray30"),
                command=lambda k=key: self.show_panel(k),
            )
            btn.pack(fill="x", padx=10, pady=2)
            self.nav_buttons[key] = btn

        # Content area
        self.content = ctk.CTkFrame(self, corner_radius=0)
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.grid_rowconfigure(0, weight=1)
        self.content.grid_columnconfigure(0, weight=1)

        # Status bar
        self.status_bar = StatusBar(self)
        self.status_bar.grid(row=1, column=0, columnspan=2, sticky="ew")
        if self.client:
            self.status_bar.set_status("연결됨")
        else:
            self.status_bar.set_status("연결 안됨 - 설정에서 API 키를 입력해주세요")

        self.panels: dict[str, BasePanel] = {}
        self.current_panel: str | None = None

    def _get_panel(self, key: str) -> BasePanel:
        if key not in self.panels:
            panel_map = {
                "Dashboard": DashboardPanel,
                "Generate": GeneratePanel,
                "Character": CharacterPanel,
                "Animation": AnimationPanel,
                "Tileset": TilesetPanel,
                "Edit": EditPanel,
                "Rotate": RotatePanel,
                "Settings": SettingsPanel,
            }
            cls = panel_map[key]
            panel = cls(self.content, self)
            self.panels[key] = panel
        return self.panels[key]

    def show_panel(self, key: str):
        if self.current_panel and self.current_panel in self.panels:
            self.panels[self.current_panel].grid_forget()

        for btn_key, btn in self.nav_buttons.items():
            if btn_key == key:
                btn.configure(fg_color=("gray75", "gray25"))
            else:
                btn.configure(fg_color="transparent")

        panel = self._get_panel(key)
        panel.grid(row=0, column=0, sticky="nsew")
        self.current_panel = key

        # Notify panel it's now visible
        if hasattr(panel, "on_panel_shown"):
            panel.on_panel_shown()


def main():
    app = PixelLabApp()
    app.mainloop()


if __name__ == "__main__":
    main()
