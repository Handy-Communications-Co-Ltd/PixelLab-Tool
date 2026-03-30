"""Common components, constants, and helpers shared across all GUI panels."""

import base64
import io
import json
import os
import threading
import zipfile
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk
import requests
from dotenv import load_dotenv
from PIL import Image, ImageTk

from ..client import PixelLabClient, PixelLabError
from ..utils import image_to_base64, get_image_size, save_images_from_response

load_dotenv()

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ── Constants ──

ANIM_TRACK_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "animations.json")

SIDEBAR_ITEMS = [
    ("대시보드", "Dashboard"),
    ("이미지 생성", "Generate"),
    ("캐릭터", "Character"),
    ("애니메이션", "Animation"),
    ("타일셋", "Tileset"),
    ("편집", "Edit"),
    ("회전", "Rotate"),
    ("설정", "Settings"),
]

CHARACTER_SIZE_PRESETS = [
    "32x32", "48x48", "64x64", "96x96", "128x128", "256x256",
]

ANIMATION_TEMPLATES = [
    "breathing-idle", "walking", "running", "jumping",
    "attack", "slash", "cross-punch", "flying-kick",
    "casting-spell", "fireball", "shooting-arrow",
    "crouching", "crouched-walking", "drinking",
    "falling-back-death", "death", "hurt",
    "fight-stance-idle-8-frames", "backflip",
]

# Approximate costs per operation (credits)
OPERATION_COSTS = {
    "이미지 생성 (Pro)": "~0.02 USD",
    "이미지 생성 (PixFlux)": "~0.01 USD",
    "이미지 생성 (BitForge)": "~0.005 USD",
    "캐릭터 생성 (4방향)": "~0.08 USD",
    "캐릭터 생성 (8방향)": "~0.16 USD",
    "캐릭터 애니메이션": "~0.04 USD",
    "텍스트 애니메이션": "~0.03 USD",
    "타일셋 생성": "~0.04 USD",
    "이미지 편집": "~0.02 USD",
    "인페인팅": "~0.02 USD",
    "8방향 회전": "~0.08 USD",
    "단일 회전": "~0.01 USD",
    "리사이즈": "~0.01 USD",
    "픽셀아트 변환": "~0.01 USD",
}

DEFAULT_OUTPUT_DIR = "output"


# ── Helper functions ──

def download_image_from_url(url: str) -> Image.Image | None:
    """Download an image from a URL and return as PIL Image."""
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            return Image.open(io.BytesIO(resp.content))
    except Exception:
        pass
    return None


def _load_anim_track() -> dict:
    """Load animation tracking data."""
    path = os.path.abspath(ANIM_TRACK_FILE)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_anim_track(data: dict):
    """Save animation tracking data."""
    path = os.path.abspath(ANIM_TRACK_FILE)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _record_animation(character_id: str, template_id: str):
    """Record that an animation was created for a character."""
    data = _load_anim_track()
    if character_id not in data:
        data[character_id] = []
    if template_id not in data[character_id]:
        data[character_id].append(template_id)
    _save_anim_track(data)


def _get_character_animations(character_id: str) -> list[str]:
    """Get list of animations created for a character."""
    data = _load_anim_track()
    return data.get(character_id, [])


def _extract_animations_from_zip(zip_data: bytes) -> list[str]:
    """Extract animation names from a character ZIP file."""
    animations = set()
    try:
        with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
            # Try metadata.json first
            for name in zf.namelist():
                if name.endswith("metadata.json"):
                    try:
                        meta = json.loads(zf.read(name))
                        # Check for animation list in metadata
                        if isinstance(meta, dict):
                            for key in ("animations", "animation_list", "anims"):
                                if key in meta:
                                    anim_data = meta[key]
                                    if isinstance(anim_data, list):
                                        for a in anim_data:
                                            if isinstance(a, str):
                                                animations.add(a)
                                            elif isinstance(a, dict):
                                                aname = a.get("name") or a.get("template_animation_id") or a.get("id", "")
                                                if aname:
                                                    animations.add(aname)
                    except Exception:
                        pass

            # Also scan folder structure for animation names
            # Typical: animations/walking/south/frame_0.png
            for name in zf.namelist():
                parts = name.replace("\\", "/").split("/")
                for i, part in enumerate(parts):
                    if part.lower() in ("animations", "animation", "anims"):
                        if i + 1 < len(parts) and parts[i + 1] and not parts[i + 1].startswith("."):
                            anim_name = parts[i + 1]
                            # Skip direction names and file names
                            if anim_name not in ("south", "north", "east", "west",
                                                  "south-east", "south-west", "north-east", "north-west") \
                               and "." not in anim_name:
                                animations.add(anim_name)
    except Exception:
        pass
    return sorted(animations)


# ── Widgets ──

class StatusBar(ctk.CTkFrame):
    """하단 상태바."""

    def __init__(self, master):
        super().__init__(master, height=30)
        self.label = ctk.CTkLabel(self, text="연결 안됨", anchor="w", font=("", 12))
        self.label.pack(side="left", padx=10)
        self.cost_label = ctk.CTkLabel(self, text="", anchor="center", font=("", 11), text_color="orange")
        self.cost_label.pack(side="left", padx=10)
        self.credit_label = ctk.CTkLabel(self, text="", anchor="e", font=("", 12))
        self.credit_label.pack(side="right", padx=10)

    def set_status(self, text: str):
        self.label.configure(text=text)

    def set_credits(self, text: str):
        self.credit_label.configure(text=text)

    def set_cost(self, text: str):
        self.cost_label.configure(text=text)


class ImagePreview(ctk.CTkFrame):
    """이미지 미리보기 위젯."""

    def __init__(self, master, width=300, height=300):
        super().__init__(master)
        self.preview_size = (width, height)
        self.canvas_label = ctk.CTkLabel(self, text="이미지 없음", width=width, height=height)
        self.canvas_label.pack(padx=5, pady=5)
        self._photo = None

    def show_base64(self, b64_data: str):
        raw = base64.b64decode(b64_data)
        img = Image.open(io.BytesIO(raw))
        img.thumbnail(self.preview_size, Image.NEAREST)
        self._photo = ImageTk.PhotoImage(img)
        self.canvas_label.configure(image=self._photo, text="")

    def show_file(self, path: str):
        img = Image.open(path)
        img.thumbnail(self.preview_size, Image.NEAREST)
        self._photo = ImageTk.PhotoImage(img)
        self.canvas_label.configure(image=self._photo, text="")

    def show_pil(self, img: Image.Image):
        img = img.copy()
        img.thumbnail(self.preview_size, Image.NEAREST)
        self._photo = ImageTk.PhotoImage(img)
        self.canvas_label.configure(image=self._photo, text="")

    def clear(self):
        self._photo = None
        self.canvas_label.configure(image=None, text="이미지 없음")


# ── Panel Base ──

class BasePanel(ctk.CTkScrollableFrame):
    """공통 패널 베이스."""

    def __init__(self, master, app):
        super().__init__(master)
        self.app = app

    @property
    def client(self) -> PixelLabClient | None:
        return self.app.client

    def run_async(self, fn, callback=None):
        def worker():
            try:
                result = fn()
                if callback:
                    self.after(0, lambda r=result: callback(r, None))
            except Exception as e:
                if callback:
                    err = e  # capture before lambda
                    self.after(0, lambda er=err: callback(None, er))
        threading.Thread(target=worker, daemon=True).start()

    def require_client(self) -> bool:
        if not self.client:
            messagebox.showwarning("연결 필요", "설정에서 API 키를 먼저 입력해주세요.")
            return False
        return True

    def handle_job_and_save(self, result: dict, prefix: str, output_dir: str = None) -> list[str]:
        out = output_dir or self.app.output_dir
        # Show usage/cost if available
        usage = result.get("usage") or (result.get("data") or {}).get("usage")
        if usage:
            cost = usage.get("usd", 0)
            if cost:
                self.app.status_bar.set_cost(f"소모: ${cost:.4f}")
        data = result.get("data") or {}
        job_id = result.get("background_job_id") or data.get("background_job_id")
        # API sometimes returns a list of job IDs
        if not job_id:
            job_ids = result.get("background_job_ids") or data.get("background_job_ids", [])
            if job_ids:
                job_id = job_ids[0] if isinstance(job_ids, list) else job_ids
        if job_id:
            self.app.status_bar.set_status(f"작업 {str(job_id)[:12]}... 처리중 (최대 5분)")
            result = self.client.wait_for_job(str(job_id))
            usage = result.get("usage") or (result.get("data") or {}).get("usage")
            if usage:
                cost = usage.get("usd", 0)
                if cost:
                    self.app.status_bar.set_cost(f"소모: ${cost:.4f}")
            self.app.status_bar.set_status("작업 완료")
        saved = save_images_from_response(result, out, prefix)
        # Auto-refresh balance after generation (schedule on main thread)
        try:
            self.app.after(100, lambda: self.app._get_panel("Dashboard").refresh_balance())
        except Exception:
            pass
        return saved
