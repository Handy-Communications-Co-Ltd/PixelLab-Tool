"""PixelLab GUI - 픽셀 아트 생성 도구."""

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

from .client import PixelLabClient, PixelLabError
from .utils import image_to_base64, get_image_size, save_images_from_response

load_dotenv()

ANIM_TRACK_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "animations.json")


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


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ── Constants ──

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


def download_image_from_url(url: str) -> Image.Image | None:
    """Download an image from a URL and return as PIL Image."""
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            return Image.open(io.BytesIO(resp.content))
    except Exception:
        pass
    return None


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

    def __init__(self, master, app: "PixelLabApp"):
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
                    self.after(0, lambda: callback(result, None))
            except Exception as e:
                if callback:
                    self.after(0, lambda: callback(None, e))
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
        job_id = result.get("background_job_id") or (result.get("data") or {}).get("background_job_id")
        if job_id:
            self.app.status_bar.set_status(f"작업 {job_id[:12]}... 처리중")
            result = self.client.wait_for_job(job_id)
            usage = result.get("usage") or (result.get("data") or {}).get("usage")
            if usage:
                cost = usage.get("usd", 0)
                if cost:
                    self.app.status_bar.set_cost(f"소모: ${cost:.4f}")
            self.app.status_bar.set_status("작업 완료")
        saved = save_images_from_response(result, out, prefix)
        return saved


# ── Dashboard Panel ──

class DashboardPanel(BasePanel):
    def __init__(self, master, app):
        super().__init__(master, app)

        ctk.CTkLabel(self, text="대시보드", font=("", 24, "bold")).pack(pady=(20, 10), anchor="w", padx=20)

        cards_frame = ctk.CTkFrame(self, fg_color="transparent")
        cards_frame.pack(fill="x", padx=20, pady=10)

        # Credits card
        credit_card = ctk.CTkFrame(cards_frame)
        credit_card.pack(side="left", fill="both", expand=True, padx=(0, 5))
        ctk.CTkLabel(credit_card, text="크레딧 (USD)", font=("", 12), text_color="gray").pack(pady=(15, 0), padx=15, anchor="w")
        self.balance_label = ctk.CTkLabel(credit_card, text="--", font=("", 32, "bold"))
        self.balance_label.pack(pady=(0, 15), padx=15, anchor="w")

        # Generations card
        gen_card = ctk.CTkFrame(cards_frame)
        gen_card.pack(side="left", fill="both", expand=True, padx=(5, 5))
        ctk.CTkLabel(gen_card, text="구독 생성 횟수", font=("", 12), text_color="gray").pack(pady=(15, 0), padx=15, anchor="w")
        self.generations_label = ctk.CTkLabel(gen_card, text="--", font=("", 32, "bold"))
        self.generations_label.pack(pady=(0, 15), padx=15, anchor="w")

        # Refresh
        refresh_card = ctk.CTkFrame(cards_frame)
        refresh_card.pack(side="left", fill="both", expand=True, padx=(5, 0))
        ctk.CTkButton(refresh_card, text="새로고침", command=self.refresh_balance, height=50).pack(pady=15, padx=15, fill="x")

        # Quick actions
        ctk.CTkLabel(self, text="빠른 실행", font=("", 18, "bold")).pack(pady=(20, 10), anchor="w", padx=20)

        quick_frame = ctk.CTkFrame(self)
        quick_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkButton(quick_frame, text="이미지 생성", command=lambda: app.show_panel("Generate")).pack(side="left", padx=10, pady=10)
        ctk.CTkButton(quick_frame, text="캐릭터 생성", command=lambda: app.show_panel("Character")).pack(side="left", padx=10, pady=10)
        ctk.CTkButton(quick_frame, text="타일셋 생성", command=lambda: app.show_panel("Tileset")).pack(side="left", padx=10, pady=10)


    def refresh_balance(self):
        if not self.require_client():
            return
        self.app.status_bar.set_status("잔액 조회중...")

        def fetch():
            return self.client.get_balance()

        def on_done(result, err):
            if err:
                messagebox.showerror("오류", str(err))
                self.app.status_bar.set_status("잔액 조회 실패")
                return
            data = result.get("data", result)
            # Parse nested balance structure
            credits_obj = data.get("credits", data.get("remaining_credits", data))
            if isinstance(credits_obj, dict):
                credits_val = credits_obj.get("usd", credits_obj.get("amount", "N/A"))
            else:
                credits_val = credits_obj

            sub_obj = data.get("subscription", {})
            if isinstance(sub_obj, dict):
                gens_val = sub_obj.get("generations", sub_obj.get("remaining", "N/A"))
            else:
                gens_val = data.get("remaining_generations", data.get("generations", "N/A"))

            # Format nicely
            if isinstance(credits_val, (int, float)):
                display_credits = f"${credits_val:.2f}"
            else:
                display_credits = str(credits_val)

            self.balance_label.configure(text=display_credits)
            self.generations_label.configure(text=str(gens_val))
            self.app.status_bar.set_credits(f"크레딧: {display_credits}")
            self.app.status_bar.set_status("준비")

        self.run_async(fetch, on_done)


# ── Generate Panel ──

class GeneratePanel(BasePanel):
    def __init__(self, master, app):
        super().__init__(master, app)

        ctk.CTkLabel(self, text="이미지 생성", font=("", 24, "bold")).pack(pady=(20, 10), anchor="w", padx=20)

        cost_info = ctk.CTkFrame(self)
        cost_info.pack(fill="x", padx=20, pady=(0, 5))
        ctk.CTkLabel(cost_info, text="예상 비용  |  Pro: ~$0.02  |  PixFlux: ~$0.01  |  BitForge: ~$0.005  |  UI/Style: ~$0.02",
                     font=("", 11), text_color="orange").pack(padx=10, pady=5)

        form = ctk.CTkFrame(self)
        form.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(form, text="설명:").pack(anchor="w", padx=10, pady=(10, 0))
        self.desc_entry = ctk.CTkTextbox(form, height=80)
        self.desc_entry.pack(fill="x", padx=10, pady=5)

        row1 = ctk.CTkFrame(form)
        row1.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(row1, text="모델:").pack(side="left")
        self.model_var = ctk.StringVar(value="pro")
        ctk.CTkOptionMenu(row1, values=["pro", "pixflux", "bitforge"], variable=self.model_var).pack(side="left", padx=10)

        ctk.CTkLabel(row1, text="너비:").pack(side="left", padx=(20, 0))
        self.width_entry = ctk.CTkEntry(row1, width=60, placeholder_text="128")
        self.width_entry.pack(side="left", padx=5)
        self.width_entry.insert(0, "128")

        ctk.CTkLabel(row1, text="높이:").pack(side="left", padx=(10, 0))
        self.height_entry = ctk.CTkEntry(row1, width=60, placeholder_text="128")
        self.height_entry.pack(side="left", padx=5)
        self.height_entry.insert(0, "128")

        row2 = ctk.CTkFrame(form)
        row2.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(row2, text="시드:").pack(side="left")
        self.seed_entry = ctk.CTkEntry(row2, width=80, placeholder_text="랜덤")
        self.seed_entry.pack(side="left", padx=10)

        self.no_bg_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(row2, text="배경 제거", variable=self.no_bg_var).pack(side="left", padx=20)

        self.gen_type = ctk.CTkSegmentedButton(form, values=["이미지", "UI", "스타일"])
        self.gen_type.set("이미지")
        self.gen_type.pack(fill="x", padx=10, pady=10)

        # Style reference
        self.style_frame = ctk.CTkFrame(form)
        self.style_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(self.style_frame, text="스타일 참조 이미지 (스타일 모드용):").pack(anchor="w")
        style_row = ctk.CTkFrame(self.style_frame)
        style_row.pack(fill="x")
        self.style_path_var = ctk.StringVar()
        ctk.CTkEntry(style_row, textvariable=self.style_path_var).pack(side="left", fill="x", expand=True, padx=(0, 5))
        ctk.CTkButton(style_row, text="찾아보기", width=80, command=self.browse_style).pack(side="right")

        self.gen_btn = ctk.CTkButton(form, text="생성", command=self.generate, height=40, font=("", 14, "bold"))
        self.gen_btn.pack(pady=15, padx=10, fill="x")

        self.preview = ImagePreview(self, 400, 400)
        self.preview.pack(pady=10)

        self.result_label = ctk.CTkLabel(self, text="")
        self.result_label.pack(pady=5)

    def browse_style(self):
        path = filedialog.askopenfilename(filetypes=[("이미지", "*.png *.jpg *.jpeg *.gif")])
        if path:
            self.style_path_var.set(path)

    def generate(self):
        if not self.require_client():
            return
        desc = self.desc_entry.get("1.0", "end").strip()
        if not desc:
            messagebox.showwarning("입력 필요", "설명을 입력해주세요.")
            return

        w = int(self.width_entry.get() or 128)
        h = int(self.height_entry.get() or 128)
        seed_text = self.seed_entry.get().strip()
        kwargs = {}
        if seed_text:
            kwargs["seed"] = int(seed_text)
        if self.no_bg_var.get():
            kwargs["no_background"] = True

        gen_type = self.gen_type.get()
        model = self.model_var.get()

        self.gen_btn.configure(state="disabled", text="생성중...")
        self.app.status_bar.set_status("생성중...")

        def do_generate():
            if gen_type == "스타일":
                style_path = self.style_path_var.get()
                if not style_path:
                    raise ValueError("스타일 참조 이미지를 선택해주세요.")
                img = image_to_base64(style_path)
                size = get_image_size(style_path)
                style_images = [{"image": img, "size": size}]
                result = self.client.generate_with_style(desc, style_images, w, h, **kwargs)
            elif gen_type == "UI":
                result = self.client.generate_ui(desc, w, h, **kwargs)
            else:
                if model == "pixflux":
                    result = self.client.generate_image_pixflux(desc, w, h, **kwargs)
                elif model == "bitforge":
                    result = self.client.generate_image_bitforge(desc, w, h, **kwargs)
                else:
                    result = self.client.generate_image(desc, w, h, **kwargs)
            saved = self.handle_job_and_save(result, f"gen_{gen_type.lower()}")
            return saved

        def on_done(saved, err):
            self.gen_btn.configure(state="normal", text="생성")
            if err:
                messagebox.showerror("오류", str(err))
                self.app.status_bar.set_status("생성 실패")
                return
            if saved:
                self.preview.show_file(saved[0])
                self.result_label.configure(text=f"{len(saved)}개 이미지 저장 완료 → {self.app.output_dir}/")
            self.app.status_bar.set_status("준비")

        self.run_async(do_generate, on_done)


# ── Character Panel ──

class CharacterPanel(BasePanel):
    def __init__(self, master, app):
        super().__init__(master, app)

        ctk.CTkLabel(self, text="캐릭터", font=("", 24, "bold")).pack(pady=(20, 10), anchor="w", padx=20)

        cost_info = ctk.CTkFrame(self)
        cost_info.pack(fill="x", padx=20, pady=(0, 5))
        ctk.CTkLabel(cost_info, text="예상 비용  |  4방향: ~$0.08  |  8방향: ~$0.16  |  애니메이션: ~$0.04",
                     font=("", 11), text_color="orange").pack(padx=10, pady=5)

        self._manage_loaded = False

        tabs = ctk.CTkTabview(self, command=self._on_tab_change)
        tabs.pack(fill="both", expand=True, padx=20, pady=10)

        # ── Create Tab ──
        create_tab = tabs.add("생성")

        ctk.CTkLabel(create_tab, text="설명:").pack(anchor="w", padx=10, pady=(10, 0))
        self.desc_entry = ctk.CTkEntry(create_tab, placeholder_text="빛나는 갑옷을 입은 용감한 기사")
        self.desc_entry.pack(fill="x", padx=10, pady=5)

        row = ctk.CTkFrame(create_tab)
        row.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(row, text="방향:").pack(side="left")
        self.dir_var = ctk.StringVar(value="4")
        ctk.CTkOptionMenu(row, values=["4", "8"], variable=self.dir_var).pack(side="left", padx=10)

        ctk.CTkLabel(row, text="크기:").pack(side="left", padx=(20, 0))
        self.size_var = ctk.StringVar(value="64x64")
        ctk.CTkOptionMenu(row, values=CHARACTER_SIZE_PRESETS, variable=self.size_var).pack(side="left", padx=10)

        ctk.CTkLabel(row, text="시점:").pack(side="left", padx=(20, 0))
        self.view_var = ctk.StringVar(value="side")
        ctk.CTkOptionMenu(row, values=["side", "low top-down", "high top-down", "perspective"], variable=self.view_var).pack(side="left", padx=10)

        row2 = ctk.CTkFrame(create_tab)
        row2.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(row2, text="템플릿:").pack(side="left")
        self.template_var = ctk.StringVar(value="mannequin")
        ctk.CTkOptionMenu(row2, values=["mannequin", "bear", "cat", "dog", "horse", "lion"], variable=self.template_var).pack(side="left", padx=10)

        ctk.CTkLabel(row2, text="디테일:").pack(side="left", padx=(20, 0))
        self.detail_var = ctk.StringVar(value="medium")
        ctk.CTkOptionMenu(row2, values=["low", "medium", "high"], variable=self.detail_var).pack(side="left", padx=10)

        row3 = ctk.CTkFrame(create_tab)
        row3.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(row3, text="외곽선:").pack(side="left")
        self.outline_var = ctk.StringVar(value="none")
        ctk.CTkOptionMenu(row3, values=["none", "thin", "medium", "thick"], variable=self.outline_var).pack(side="left", padx=10)

        ctk.CTkLabel(row3, text="셰이딩:").pack(side="left", padx=(20, 0))
        self.shading_var = ctk.StringVar(value="none")
        ctk.CTkOptionMenu(row3, values=["none", "soft", "hard", "flat"], variable=self.shading_var).pack(side="left", padx=10)

        ctk.CTkLabel(row3, text="시드:").pack(side="left", padx=(20, 0))
        self.seed_entry = ctk.CTkEntry(row3, width=80, placeholder_text="랜덤")
        self.seed_entry.pack(side="left", padx=5)

        self.isometric_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(row3, text="아이소메트릭", variable=self.isometric_var).pack(side="left", padx=20)

        # Batch generation row
        batch_row = ctk.CTkFrame(create_tab)
        batch_row.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(batch_row, text="반복 생성 횟수:").pack(side="left")
        self.batch_count = ctk.CTkEntry(batch_row, width=60)
        self.batch_count.pack(side="left", padx=5)
        self.batch_count.insert(0, "1")
        ctk.CTkLabel(batch_row, text="(서로 다른 시드로 여러 캐릭터를 한번에 생성)", font=("", 10), text_color="gray").pack(side="left", padx=10)

        self.create_btn = ctk.CTkButton(create_tab, text="캐릭터 생성", command=self.create_character, height=40, font=("", 14, "bold"))
        self.create_btn.pack(fill="x", padx=10, pady=15)

        self.batch_progress = ctk.CTkProgressBar(create_tab)
        self.batch_progress.pack(fill="x", padx=10, pady=(0, 5))
        self.batch_progress.set(0)
        self.batch_progress.pack_forget()  # hidden by default

        self.create_preview = ImagePreview(create_tab, 300, 300)
        self.create_preview.pack(pady=5)

        self.create_result = ctk.CTkLabel(create_tab, text="")
        self.create_result.pack(pady=5)

        # ── Manage Tab ──
        manage_tab = tabs.add("관리")

        btn_row = ctk.CTkFrame(manage_tab)
        btn_row.pack(fill="x", padx=10, pady=10)
        ctk.CTkButton(btn_row, text="목록 새로고침", command=self.refresh_list).pack(side="left", padx=5)
        ctk.CTkButton(btn_row, text="선택 내보내기", command=self.export_selected).pack(side="left", padx=5)
        ctk.CTkButton(btn_row, text="선택 삭제", command=self.delete_selected, fg_color="red", hover_color="darkred").pack(side="left", padx=5)

        self.char_list_frame = ctk.CTkScrollableFrame(manage_tab, height=400)
        self.char_list_frame.pack(fill="both", expand=True, padx=10, pady=5)
        self.selected_char_id = ctk.StringVar()
        self.selected_char_name = ctk.StringVar()
        self.char_widgets = []
        self.char_photos = []
        self.loaded_characters = []  # Store loaded character data for animate dropdown

        # ── Animate Tab ──
        anim_tab = tabs.add("애니메이션")

        ctk.CTkLabel(anim_tab, text="캐릭터 선택:").pack(anchor="w", padx=10, pady=(10, 0))
        self.anim_char_menu = ctk.CTkOptionMenu(anim_tab, values=["관리 탭에서 먼저 목록을 새로고침하세요"], width=400)
        self.anim_char_menu.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(anim_tab, text="템플릿 애니메이션:").pack(anchor="w", padx=10, pady=(10, 0))
        self.anim_template = ctk.CTkOptionMenu(anim_tab, values=ANIMATION_TEMPLATES)
        self.anim_template.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(anim_tab, text="커스텀 동작 설명 (선택사항):").pack(anchor="w", padx=10, pady=(10, 0))
        self.anim_action_desc = ctk.CTkEntry(anim_tab, placeholder_text="예: 큰 망치를 세게 휘두르기")
        self.anim_action_desc.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(anim_tab, text="방향 선택 (복수 선택 가능):").pack(anchor="w", padx=10, pady=(10, 0))

        dir_frame = ctk.CTkFrame(anim_tab)
        dir_frame.pack(fill="x", padx=10, pady=5)

        all_dirs = ["south", "west", "east", "north", "south-west", "south-east", "north-west", "north-east"]
        self.anim_dir_vars = {}
        self.anim_all_var = ctk.BooleanVar(value=True)

        ctk.CTkCheckBox(dir_frame, text="전체", variable=self.anim_all_var,
                        command=self._toggle_all_dirs).pack(side="left", padx=5)

        for d in all_dirs:
            var = ctk.BooleanVar(value=False)
            ctk.CTkCheckBox(dir_frame, text=d, variable=var, width=90,
                            command=self._on_dir_check).pack(side="left", padx=3)
            self.anim_dir_vars[d] = var

        anim_opts = ctk.CTkFrame(anim_tab)
        anim_opts.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(anim_opts, text="시드:").pack(side="left")
        self.anim_seed = ctk.CTkEntry(anim_opts, width=80, placeholder_text="랜덤")
        self.anim_seed.pack(side="left", padx=5)

        self.anim_btn = ctk.CTkButton(anim_tab, text="애니메이션 생성", command=self.animate_character, height=40, font=("", 14, "bold"))
        self.anim_btn.pack(fill="x", padx=10, pady=15)

        self.anim_result = ctk.CTkLabel(anim_tab, text="")
        self.anim_result.pack(pady=5)

        # ── Copy animations section ──
        ctk.CTkLabel(anim_tab, text="", height=1).pack()  # spacer
        copy_frame = ctk.CTkFrame(anim_tab)
        copy_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(copy_frame, text="애니메이션 복사", font=("", 14, "bold")).pack(anchor="w", padx=10, pady=(10, 5))
        ctk.CTkLabel(copy_frame, text="원본 캐릭터의 애니메이션을 대상 캐릭터에 복사합니다.", font=("", 10), text_color="gray").pack(anchor="w", padx=10)

        # Source character
        src_row = ctk.CTkFrame(copy_frame)
        src_row.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(src_row, text="원본:").pack(side="left")
        self.copy_source_menu = ctk.CTkOptionMenu(src_row, values=["목록을 먼저 새로고침하세요"], width=300)
        self.copy_source_menu.pack(side="left", padx=10)
        ctk.CTkButton(src_row, text="확인", width=50, command=self._show_source_anims).pack(side="left")

        self.copy_source_anims = ctk.CTkLabel(copy_frame, text="원본 애니메이션: -", font=("", 12), text_color="#90EE90", justify="left", anchor="w")
        self.copy_source_anims.pack(anchor="w", padx=10, pady=3)

        # Target character
        tgt_row = ctk.CTkFrame(copy_frame)
        tgt_row.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(tgt_row, text="대상:").pack(side="left")
        self.copy_target_menu = ctk.CTkOptionMenu(tgt_row, values=["목록을 먼저 새로고침하세요"], width=300)
        self.copy_target_menu.pack(side="left", padx=10)

        self.copy_btn = ctk.CTkButton(copy_frame, text="애니메이션 복사 실행", command=self.copy_animations,
                                       height=40, fg_color="green", hover_color="darkgreen")
        self.copy_btn.pack(fill="x", padx=10, pady=10)

        self.copy_result = ctk.CTkLabel(copy_frame, text="")
        self.copy_result.pack(pady=(0, 10))

        # ── Batch Animation Tab ──
        batch_tab = tabs.add("일괄 애니메이션")

        ctk.CTkLabel(batch_tab, text="여러 캐릭터에 동일한 애니메이션을 한번에 추가합니다.",
                     font=("", 11), text_color="gray").pack(anchor="w", padx=10, pady=(10, 5))

        # Animation selection
        ctk.CTkLabel(batch_tab, text="애니메이션 선택:").pack(anchor="w", padx=10, pady=(5, 0))
        self.batch_anim_menu = ctk.CTkOptionMenu(batch_tab, values=ANIMATION_TEMPLATES)
        self.batch_anim_menu.pack(fill="x", padx=10, pady=5)

        # Custom action description
        ctk.CTkLabel(batch_tab, text="커스텀 동작 설명 (선택사항):").pack(anchor="w", padx=10, pady=(5, 0))
        self.batch_action_desc = ctk.CTkEntry(batch_tab, placeholder_text="예: 큰 망치를 세게 휘두르기")
        self.batch_action_desc.pack(fill="x", padx=10, pady=5)

        # Direction selection
        ctk.CTkLabel(batch_tab, text="방향 선택:").pack(anchor="w", padx=10, pady=(5, 0))
        batch_dir_frame = ctk.CTkFrame(batch_tab)
        batch_dir_frame.pack(fill="x", padx=10, pady=5)

        all_dirs = ["south", "west", "east", "north", "south-west", "south-east", "north-west", "north-east"]
        self.batch_dir_vars = {}
        self.batch_all_dir = ctk.BooleanVar(value=True)

        ctk.CTkCheckBox(batch_dir_frame, text="전체", variable=self.batch_all_dir,
                        command=self._batch_toggle_dirs).pack(side="left", padx=5)
        for d in all_dirs:
            var = ctk.BooleanVar(value=False)
            ctk.CTkCheckBox(batch_dir_frame, text=d, variable=var, width=90,
                            command=self._batch_on_dir_check).pack(side="left", padx=3)
            self.batch_dir_vars[d] = var

        # Character multi-select
        ctk.CTkLabel(batch_tab, text="적용할 캐릭터 선택:").pack(anchor="w", padx=10, pady=(10, 0))

        batch_btn_row = ctk.CTkFrame(batch_tab)
        batch_btn_row.pack(fill="x", padx=10, pady=5)
        ctk.CTkButton(batch_btn_row, text="전체 선택", width=80, command=self._batch_select_all).pack(side="left", padx=5)
        ctk.CTkButton(batch_btn_row, text="전체 해제", width=80, command=self._batch_deselect_all).pack(side="left", padx=5)

        self.batch_char_frame = ctk.CTkScrollableFrame(batch_tab, height=200)
        self.batch_char_frame.pack(fill="both", expand=True, padx=10, pady=5)
        self.batch_char_vars: dict[str, ctk.BooleanVar] = {}

        self.batch_run_btn = ctk.CTkButton(batch_tab, text="일괄 애니메이션 생성", command=self.run_batch_animation,
                                            height=40, font=("", 14, "bold"))
        self.batch_run_btn.pack(fill="x", padx=10, pady=10)

        self.batch_progress = ctk.CTkProgressBar(batch_tab)
        self.batch_progress.pack(fill="x", padx=10, pady=(0, 5))
        self.batch_progress.set(0)
        self.batch_progress.pack_forget()

        self.batch_result = ctk.CTkLabel(batch_tab, text="")
        self.batch_result.pack(pady=5)

    def on_panel_shown(self):
        """Called when the Character panel becomes visible."""
        if not self._manage_loaded and self.client:
            self._manage_loaded = True
            self.after(100, self.refresh_list)

    def _on_tab_change(self, tab_name):
        pass

    def _toggle_all_dirs(self):
        if self.anim_all_var.get():
            for var in self.anim_dir_vars.values():
                var.set(False)

    def _on_dir_check(self):
        any_checked = any(v.get() for v in self.anim_dir_vars.values())
        if any_checked:
            self.anim_all_var.set(False)
        else:
            self.anim_all_var.set(True)

    def _update_batch_char_list(self):
        """Update batch tab character checkboxes."""
        for w in self.batch_char_frame.winfo_children():
            w.destroy()
        self.batch_char_vars.clear()
        for ch in self.loaded_characters:
            cid = str(ch.get("id", ch.get("character_id", "")))
            desc = str(ch.get("prompt", ch.get("description", ch.get("name", ""))))[:35]
            var = ctk.BooleanVar(value=False)
            ctk.CTkCheckBox(self.batch_char_frame, text=f"{desc} [{cid[:8]}]",
                            variable=var).pack(anchor="w", pady=2)
            self.batch_char_vars[cid] = var

    def _batch_toggle_dirs(self):
        if self.batch_all_dir.get():
            for var in self.batch_dir_vars.values():
                var.set(False)

    def _batch_on_dir_check(self):
        if any(v.get() for v in self.batch_dir_vars.values()):
            self.batch_all_dir.set(False)
        else:
            self.batch_all_dir.set(True)

    def _batch_select_all(self):
        for var in self.batch_char_vars.values():
            var.set(True)

    def _batch_deselect_all(self):
        for var in self.batch_char_vars.values():
            var.set(False)

    def run_batch_animation(self):
        if not self.require_client():
            return
        selected = [cid for cid, var in self.batch_char_vars.items() if var.get()]
        if not selected:
            messagebox.showwarning("선택 필요", "캐릭터를 하나 이상 선택해주세요.")
            return
        template = self.batch_anim_menu.get()
        total = len(selected)

        if not messagebox.askyesno("확인",
                f"{total}개 캐릭터에 '{template}' 애니메이션을 생성하시겠습니까?\n"
                f"예상 비용: ~${total * 0.04:.2f}"):
            return

        self.batch_run_btn.configure(state="disabled", text="생성중...")
        self.batch_progress.pack(fill="x", padx=10, pady=(0, 5))
        self.batch_progress.set(0)

        def do_batch():
            kwargs = {}
            action_desc = self.batch_action_desc.get().strip()
            if action_desc:
                kwargs["action_description"] = action_desc
            sel_dirs = [d for d, v in self.batch_dir_vars.items() if v.get()]
            if sel_dirs and not self.batch_all_dir.get():
                kwargs["directions"] = sel_dirs

            all_saved = []
            for i, cid in enumerate(selected):
                self.after(0, lambda n=i+1, t=total, c=cid:
                          (self.app.status_bar.set_status(f"일괄 애니메이션 ({n}/{t}) - {c[:8]}..."),
                           self.batch_progress.set(n / t)))
                result = self.client.animate_character(cid, template, **kwargs)
                saved = self.handle_job_and_save(result, f"batch_{template}_{cid[:8]}")
                all_saved.extend(saved)
                _record_animation(cid, template)
            return all_saved

        def on_done(saved, err):
            self.batch_run_btn.configure(state="normal", text="일괄 애니메이션 생성")
            self.batch_progress.pack_forget()
            if err:
                messagebox.showerror("오류", str(err))
                self.app.status_bar.set_status("일괄 생성 실패")
                return
            self.batch_result.configure(text=f"{total}개 캐릭터에 '{template}' 생성 완료 ({len(saved)}개 프레임)")
            self.app.status_bar.set_status("준비")

        self.run_async(do_batch, on_done)

    def _show_source_anims(self):
        """Show what animations the source character has."""
        source_id = self._get_char_id_from_menu(self.copy_source_menu.get())
        if not source_id:
            self.copy_source_anims.configure(text="원본 애니메이션: 캐릭터를 선택해주세요")
            return
        anims = _get_character_animations(source_id)
        if anims:
            anim_list = "\n   ".join(anims)
            self.copy_source_anims.configure(text=f"원본 애니메이션 ({len(anims)}개):\n   {anim_list}")
        else:
            self.copy_source_anims.configure(text="원본 애니메이션: 추적된 애니메이션 없음")

    def _get_char_id_from_menu(self, menu_text: str) -> str | None:
        """Extract character ID from menu selection text."""
        if "[" in menu_text and "]" in menu_text:
            short_id = menu_text.split("[")[-1].rstrip("]")
            for ch in self.loaded_characters:
                cid = str(ch.get("id", ch.get("character_id", "")))
                if cid.startswith(short_id):
                    return cid
        return None

    def copy_animations(self):
        """Copy animations from source character to target character."""
        if not self.require_client():
            return

        target_id = self._get_char_id_from_menu(self.copy_target_menu.get())
        source_id = self._get_char_id_from_menu(self.copy_source_menu.get())

        if not target_id:
            messagebox.showwarning("선택 필요", "대상 캐릭터를 선택해주세요.")
            return
        if not source_id:
            messagebox.showwarning("선택 필요", "원본 캐릭터를 선택해주세요.")
            return
        if target_id == source_id:
            messagebox.showwarning("오류", "원본과 대상 캐릭터가 같습니다.")
            return

        source_anims = _get_character_animations(source_id)
        if not source_anims:
            messagebox.showwarning("애니메이션 없음", "원본 캐릭터에 추적된 애니메이션이 없습니다.")
            return

        target_anims = _get_character_animations(target_id)
        duplicates = [a for a in source_anims if a in target_anims]
        new_anims = [a for a in source_anims if a not in target_anims]

        # Show conflict resolution dialog
        self._show_copy_conflict_dialog(target_id, source_anims, new_anims, duplicates)

    def _show_copy_conflict_dialog(self, target_id, all_anims, new_anims, duplicates):
        """Show dialog for selecting which animations to copy with conflict resolution."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("애니메이션 복사 확인")
        dialog.geometry("500x550")
        dialog.grab_set()

        ctk.CTkLabel(dialog, text="복사할 애니메이션 선택", font=("", 16, "bold")).pack(pady=(15, 5), padx=15, anchor="w")

        # New animations section
        if new_anims:
            ctk.CTkLabel(dialog, text=f"새로 추가 ({len(new_anims)}개)", font=("", 13, "bold"),
                         text_color="#90EE90").pack(anchor="w", padx=15, pady=(10, 3))

        check_vars = {}
        scroll = ctk.CTkScrollableFrame(dialog, height=300)
        scroll.pack(fill="both", expand=True, padx=15, pady=5)

        for anim in new_anims:
            var = ctk.BooleanVar(value=True)
            ctk.CTkCheckBox(scroll, text=f"{anim}", variable=var,
                            text_color="#90EE90").pack(anchor="w", pady=2)
            check_vars[anim] = var

        # Duplicate animations section
        if duplicates:
            dup_label = ctk.CTkLabel(scroll, text=f"\n이미 존재하는 애니메이션 ({len(duplicates)}개)",
                                     font=("", 13, "bold"), text_color="orange")
            dup_label.pack(anchor="w", pady=(10, 3))

            ctk.CTkLabel(scroll, text="체크하면 덮어씌우기, 해제하면 건너뛰기",
                         font=("", 10), text_color="gray").pack(anchor="w", pady=(0, 5))

            for anim in duplicates:
                var = ctk.BooleanVar(value=False)  # Default: skip
                row = ctk.CTkFrame(scroll, fg_color="transparent")
                row.pack(anchor="w", fill="x", pady=2)
                ctk.CTkCheckBox(row, text=f"{anim}", variable=var,
                                text_color="orange").pack(side="left")
                ctk.CTkLabel(row, text="(덮어씌우기)", font=("", 10), text_color="gray").pack(side="left", padx=5)
                check_vars[anim] = var

        if not new_anims and not duplicates:
            ctk.CTkLabel(scroll, text="복사할 애니메이션이 없습니다.").pack(pady=10)

        # Summary and buttons
        summary_frame = ctk.CTkFrame(dialog)
        summary_frame.pack(fill="x", padx=15, pady=10)

        def update_summary(*_):
            selected = [a for a, v in check_vars.items() if v.get()]
            cost = len(selected) * 0.04
            summary_label.configure(text=f"선택: {len(selected)}개  |  예상 비용: ~${cost:.2f}")

        summary_label = ctk.CTkLabel(summary_frame, text="", font=("", 12))
        summary_label.pack(pady=5)
        update_summary()

        # Bind checkbox changes to update summary
        for var in check_vars.values():
            var.trace_add("write", update_summary)

        btn_row = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_row.pack(fill="x", padx=15, pady=(0, 15))

        def do_copy():
            selected = [a for a, v in check_vars.items() if v.get()]
            if not selected:
                messagebox.showinfo("알림", "선택된 애니메이션이 없습니다.")
                return
            dialog.destroy()
            self._execute_copy(target_id, selected)

        ctk.CTkButton(btn_row, text="복사 실행", command=do_copy,
                      height=40, fg_color="green", hover_color="darkgreen").pack(side="left", fill="x", expand=True, padx=(0, 5))
        ctk.CTkButton(btn_row, text="취소", command=dialog.destroy,
                      height=40, fg_color="gray", hover_color="darkgray").pack(side="right", width=100)

    def _execute_copy(self, target_id, anims_to_copy):
        """Execute the animation copy with selected animations."""
        self.copy_btn.configure(state="disabled", text="복사중...")
        self.app.status_bar.set_status(f"애니메이션 복사중... (0/{len(anims_to_copy)})")
        total = len(anims_to_copy)

        def do_copy():
            all_saved = []
            for i, template in enumerate(anims_to_copy):
                self.after(0, lambda n=i+1, t=total, a=template:
                          self.app.status_bar.set_status(f"애니메이션 복사중... ({n}/{t}) - {a}"))
                result = self.client.animate_character(target_id, template)
                saved = self.handle_job_and_save(result, f"copy_{template}")
                all_saved.extend(saved)
                _record_animation(target_id, template)
            return all_saved

        def on_done(saved, err):
            self.copy_btn.configure(state="normal", text="애니메이션 복사 실행")
            if err:
                messagebox.showerror("오류", str(err))
                self.app.status_bar.set_status("복사 실패")
                return
            self.copy_result.configure(text=f"{total}개 애니메이션 복사 완료 ({len(saved)}개 프레임)")
            self.app.status_bar.set_status("준비")

        self.run_async(do_copy, on_done)

    def _update_anim_dropdown(self):
        """Update the animation tab's character dropdown from loaded characters."""
        if not self.loaded_characters:
            no_char = ["캐릭터 없음"]
            self.anim_char_menu.configure(values=no_char)
            self.anim_char_menu.set(no_char[0])
            self.copy_source_menu.configure(values=no_char)
            self.copy_source_menu.set(no_char[0])
            self.copy_target_menu.configure(values=no_char)
            self.copy_target_menu.set(no_char[0])
            return
        items = []
        for ch in self.loaded_characters:
            cid = str(ch.get("id", ch.get("character_id", "")))
            desc = str(ch.get("prompt", ch.get("description", ch.get("name", ""))))[:30]
            items.append(f"{desc} [{cid[:8]}]")
        self.anim_char_menu.configure(values=items)
        self.anim_char_menu.set(items[0])
        self.copy_source_menu.configure(values=items)
        self.copy_source_menu.set(items[0])
        self.copy_target_menu.configure(values=items)
        self.copy_target_menu.set(items[-1] if len(items) > 1 else items[0])
        # Update batch character checkboxes
        self._update_batch_char_list()

    def _get_selected_anim_char_id(self) -> str | None:
        """Extract character ID from the animation dropdown selection."""
        sel = self.anim_char_menu.get()
        if "[" in sel and "]" in sel:
            short_id = sel.split("[")[-1].rstrip("]")
            for ch in self.loaded_characters:
                cid = str(ch.get("id", ch.get("character_id", "")))
                if cid.startswith(short_id):
                    return cid
        return None

    def create_character(self):
        if not self.require_client():
            return
        desc = self.desc_entry.get().strip()
        if not desc:
            messagebox.showwarning("입력 필요", "설명을 입력해주세요.")
            return

        size_parts = self.size_var.get().split("x")
        w, h = int(size_parts[0]), int(size_parts[1])
        dirs = self.dir_var.get()
        kwargs = {}
        view = self.view_var.get()
        if view != "side":
            kwargs["view"] = view
        template = self.template_var.get()
        if template != "mannequin":
            kwargs["template_id"] = template
        detail = self.detail_var.get()
        if detail != "medium":
            kwargs["detail"] = detail
        if self.isometric_var.get():
            kwargs["isometric"] = True
        outline = self.outline_var.get()
        if outline != "none":
            kwargs["outline"] = outline
        shading = self.shading_var.get()
        if shading != "none":
            kwargs["shading"] = shading
        seed_text = self.seed_entry.get().strip()
        base_seed = int(seed_text) if seed_text else None

        batch = max(1, int(self.batch_count.get() or 1))

        self.create_btn.configure(state="disabled", text="생성중...")
        self.app.status_bar.set_status(f"캐릭터 생성중... (0/{batch})")

        if batch > 1:
            self.batch_progress.pack(fill="x", padx=10, pady=(0, 5))
            self.batch_progress.set(0)

        def do_create():
            import random
            results = []
            for i in range(batch):
                run_kwargs = dict(kwargs)
                if base_seed is not None:
                    run_kwargs["seed"] = base_seed + i
                else:
                    run_kwargs["seed"] = random.randint(1, 999999)

                try:
                    if dirs == "4":
                        result = self.client.create_character_4dir(desc, w, h, **run_kwargs)
                    else:
                        result = self.client.create_character_8dir(desc, w, h, **run_kwargs)
                except Exception as e:
                    err_msg = str(e)
                    # Show what was sent for debugging
                    params = f"size={w}x{h}, dirs={dirs}"
                    if run_kwargs:
                        params += ", " + ", ".join(f"{k}={v}" for k, v in run_kwargs.items() if k != "seed")
                    raise Exception(f"{err_msg}\n\n전송 파라미터: {params}\n\n서버 내부 오류일 수 있습니다. 다른 옵션 조합으로 시도해보세요.") from None

                char_id = result.get("character_id", result.get("data", {}).get("character_id", "N/A"))
                saved = self.handle_job_and_save(result, f"character_{i}")
                results.append((char_id, saved))

                progress = (i + 1) / batch
                self.after(0, lambda p=progress, n=i+1: self._update_batch_progress(p, n, batch))

            return results

        def on_done(results, err):
            self.create_btn.configure(state="normal", text="캐릭터 생성")
            self.batch_progress.pack_forget()
            if err:
                messagebox.showerror("오류", str(err))
                self.app.status_bar.set_status("생성 실패")
                return
            if not results:
                return
            last_id, last_saved = results[-1]
            if batch == 1:
                self.create_result.configure(text=f"캐릭터 ID: {last_id}")
            else:
                ids = [r[0] for r in results]
                self.create_result.configure(text=f"{batch}개 캐릭터 생성 완료\nIDs: {', '.join(str(i)[:12] for i in ids)}")
            if last_saved:
                self.create_preview.show_file(last_saved[0])
            self.app.status_bar.set_status("준비")

        self.run_async(do_create, on_done)

    def _update_batch_progress(self, progress, current, total):
        self.batch_progress.set(progress)
        self.app.status_bar.set_status(f"캐릭터 생성중... ({current}/{total})")

    def refresh_list(self):
        if not self.require_client():
            return
        self.app.status_bar.set_status("캐릭터 목록 로딩중...")

        def fetch():
            result = self.client.list_characters(limit=50)
            data = result.get("data", result)
            characters = data if isinstance(data, list) else data.get("characters", [])
            # Fetch details to get rotation_urls
            detailed = []
            for ch in characters:
                cid = str(ch.get("id", ""))
                try:
                    detail = self.client.get_character(cid)
                    detail_data = detail.get("data", detail)
                    detailed.append(detail_data)
                except Exception:
                    detailed.append(ch)
            # Download preview images and extract animations from ZIP
            for i, ch in enumerate(detailed):
                cid = str(ch.get("id", ch.get("character_id", "")))
                self.after(0, lambda n=i+1, t=len(detailed):
                          self.app.status_bar.set_status(f"캐릭터 정보 로딩중... ({n}/{t})"))
                # Preview image
                preview_url = ch.get("preview_url")
                rotation_urls = ch.get("rotation_urls", {})
                if not preview_url and rotation_urls:
                    preview_url = rotation_urls.get("south") or next(iter(rotation_urls.values()), None)
                if preview_url:
                    img = download_image_from_url(preview_url)
                    if img:
                        ch["_preview_img"] = img
                # Extract animations from ZIP if not already tracked
                anim_count = ch.get("animation_count", 0)
                existing_anims = _get_character_animations(cid)
                if anim_count > 0 and not existing_anims:
                    try:
                        zip_data = self.client.export_character_zip(cid)
                        anims = _extract_animations_from_zip(zip_data)
                        if anims:
                            track = _load_anim_track()
                            track[cid] = anims
                            _save_anim_track(track)
                    except Exception:
                        pass
            return detailed

        def on_done(characters, err):
            if err:
                messagebox.showerror("오류", str(err))
                self.app.status_bar.set_status("캐릭터 로딩 실패")
                return
            for w in self.char_list_frame.winfo_children():
                w.destroy()
            self.char_widgets.clear()
            self.char_photos.clear()
            self.loaded_characters = characters

            if not characters:
                ctk.CTkLabel(self.char_list_frame, text="캐릭터가 없습니다.").pack(pady=10)
                self.app.status_bar.set_status("준비")
                self._update_anim_dropdown()
                return

            for ch in characters:
                cid = str(ch.get("id", ch.get("character_id", "")))
                desc = str(ch.get("prompt", ch.get("description", ch.get("name", ""))))[:40]
                dirs = ch.get("directions", "?")
                size = ch.get("size", {})
                size_str = f"{size.get('width', '?')}x{size.get('height', '?')}" if isinstance(size, dict) else ""

                card = ctk.CTkFrame(self.char_list_frame)
                card.pack(fill="x", padx=5, pady=3)

                # Thumbnail from downloaded image
                thumb_label = ctk.CTkLabel(card, text="", width=64, height=64)
                thumb_label.pack(side="left", padx=5, pady=5)

                preview_img = ch.get("_preview_img")
                if preview_img:
                    try:
                        thumb = preview_img.copy()
                        thumb.thumbnail((64, 64), Image.NEAREST)
                        photo = ImageTk.PhotoImage(thumb)
                        thumb_label.configure(image=photo)
                        self.char_photos.append(photo)
                    except Exception:
                        thumb_label.configure(text="[오류]")
                else:
                    thumb_label.configure(text="[미리보기\n없음]")

                info_frame = ctk.CTkFrame(card, fg_color="transparent")
                info_frame.pack(side="left", fill="x", expand=True, padx=5)

                ctk.CTkLabel(info_frame, text=desc or "설명 없음", font=("", 13, "bold"), anchor="w").pack(anchor="w")
                ctk.CTkLabel(info_frame, text=f"{dirs}방향 | {size_str} | ID: {cid[:16]}", font=("", 10), text_color="gray", anchor="w").pack(anchor="w")

                # Show animations
                anims = _get_character_animations(cid)
                anim_count = ch.get("animation_count", len(anims))

                anim_header = ctk.CTkFrame(info_frame, fg_color="transparent")
                anim_header.pack(anchor="w", fill="x")

                if anims:
                    ctk.CTkLabel(anim_header, text=f"애니메이션 ({len(anims)}개)", font=("", 12, "bold"), text_color="#90EE90", anchor="w").pack(side="left")
                    for anim_name in anims:
                        ctk.CTkLabel(info_frame, text=f"  {anim_name}", font=("", 12), text_color="#90EE90",
                                     anchor="w").pack(anchor="w", pady=1)
                elif anim_count > 0:
                    ctk.CTkLabel(anim_header, text=f"애니메이션: {anim_count}개 (미등록)", font=("", 12), text_color="yellow", anchor="w").pack(side="left")
                else:
                    ctk.CTkLabel(anim_header, text="애니메이션: 없음", font=("", 12), text_color="gray", anchor="w").pack(side="left")

                # Manual register button for untracked animations
                if anim_count > 0 and len(anims) < anim_count:
                    ctk.CTkButton(anim_header, text="등록", width=50, height=20, font=("", 10),
                                  command=lambda c=cid: self._manual_register_anims(c)).pack(side="left", padx=5)

                right_frame = ctk.CTkFrame(card, fg_color="transparent")
                right_frame.pack(side="right", padx=10)
                rb = ctk.CTkRadioButton(right_frame, text="선택", variable=self.selected_char_id, value=cid, width=70)
                rb.pack()
                self.char_widgets.append(card)

            self._update_anim_dropdown()
            self.app.status_bar.set_status(f"{len(characters)}개 캐릭터 로딩 완료")

        self.run_async(fetch, on_done)

    def export_selected(self):
        cid = self.selected_char_id.get()
        if not cid or not self.require_client():
            messagebox.showwarning("선택 필요", "먼저 캐릭터를 선택해주세요.")
            return

        def do_export():
            data = self.client.export_character_zip(cid)
            out = self.app.output_dir
            os.makedirs(out, exist_ok=True)
            path = os.path.join(out, f"character_{cid}.zip")
            with open(path, "wb") as f:
                f.write(data)
            return path

        def on_done(path, err):
            if err:
                messagebox.showerror("오류", str(err))
                return
            messagebox.showinfo("내보내기 완료", f"저장 위치: {path}")

        self.run_async(do_export, on_done)

    def _manual_register_anims(self, character_id: str):
        """Open dialog to manually register animations for a character."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("애니메이션 수동 등록")
        dialog.geometry("400x500")
        dialog.grab_set()

        ctk.CTkLabel(dialog, text=f"캐릭터: {character_id[:16]}...", font=("", 12)).pack(pady=(15, 5), padx=15, anchor="w")
        ctk.CTkLabel(dialog, text="이 캐릭터에 있는 애니메이션을 선택하세요:", font=("", 11)).pack(pady=5, padx=15, anchor="w")

        existing = _get_character_animations(character_id)
        check_vars = {}

        scroll = ctk.CTkScrollableFrame(dialog, height=300)
        scroll.pack(fill="both", expand=True, padx=15, pady=5)

        for template in ANIMATION_TEMPLATES:
            var = ctk.BooleanVar(value=template in existing)
            ctk.CTkCheckBox(scroll, text=template, variable=var).pack(anchor="w", pady=2)
            check_vars[template] = var

        def save():
            data = _load_anim_track()
            selected = [t for t, v in check_vars.items() if v.get()]
            data[character_id] = selected
            _save_anim_track(data)
            dialog.destroy()
            self.refresh_list()

        ctk.CTkButton(dialog, text="저장", command=save, height=40, font=("", 14, "bold")).pack(fill="x", padx=15, pady=15)

    def delete_selected(self):
        cid = self.selected_char_id.get()
        if not cid or not self.require_client():
            return
        if not messagebox.askyesno("확인", f"캐릭터 {cid[:12]}...를 삭제하시겠습니까?"):
            return

        def do_delete():
            self.client.delete_character(cid)

        def on_done(_, err):
            if err:
                messagebox.showerror("오류", str(err))
                return
            messagebox.showinfo("삭제 완료", "캐릭터가 삭제되었습니다.")
            self.refresh_list()

        self.run_async(do_delete, on_done)

    def animate_character(self):
        if not self.require_client():
            return
        cid = self._get_selected_anim_char_id()
        if not cid:
            messagebox.showwarning("선택 필요", "애니메이션할 캐릭터를 선택해주세요.")
            return

        template = self.anim_template.get()
        self.anim_btn.configure(state="disabled", text="생성중...")
        self.app.status_bar.set_status("애니메이션 생성중...")

        def do_animate():
            base_kwargs = {}
            action_desc = self.anim_action_desc.get().strip()
            if action_desc:
                base_kwargs["action_description"] = action_desc
            seed_text = self.anim_seed.get().strip()
            if seed_text:
                base_kwargs["seed"] = int(seed_text)

            # Determine selected directions
            selected_dirs = [d for d, v in self.anim_dir_vars.items() if v.get()]
            use_all = self.anim_all_var.get() or not selected_dirs

            all_saved = []
            if use_all:
                # Single call with all directions
                result = self.client.animate_character(cid, template, **base_kwargs)
                all_saved.extend(self.handle_job_and_save(result, "anim"))
            else:
                # One call per selected direction
                for i, d in enumerate(selected_dirs):
                    self.after(0, lambda n=i+1, t=len(selected_dirs):
                              self.app.status_bar.set_status(f"애니메이션 생성중... ({n}/{t}) - {d}"))
                    kwargs = dict(base_kwargs)
                    kwargs["directions"] = [d]
                    result = self.client.animate_character(cid, template, **kwargs)
                    saved = self.handle_job_and_save(result, f"anim_{d}")
                    all_saved.extend(saved)
            # Record animation
            _record_animation(cid, template)
            return all_saved

        def on_done(saved, err):
            self.anim_btn.configure(state="normal", text="애니메이션 생성")
            if err:
                messagebox.showerror("오류", str(err))
                self.app.status_bar.set_status("애니메이션 실패")
                return
            self.anim_result.configure(text=f"{len(saved)}개 프레임 저장 완료")
            self.app.status_bar.set_status("준비")

        self.run_async(do_animate, on_done)


# ── Animation Panel ──

class AnimationPanel(BasePanel):
    def __init__(self, master, app):
        super().__init__(master, app)

        ctk.CTkLabel(self, text="애니메이션", font=("", 24, "bold")).pack(pady=(20, 10), anchor="w", padx=20)

        cost_info = ctk.CTkFrame(self)
        cost_info.pack(fill="x", padx=20, pady=(0, 5))
        ctk.CTkLabel(cost_info, text="예상 비용  |  텍스트 애니메이션: ~$0.03  |  보간: ~$0.03",
                     font=("", 11), text_color="orange").pack(padx=10, pady=5)

        tabs = ctk.CTkTabview(self)
        tabs.pack(fill="both", expand=True, padx=20, pady=10)

        # ── Text Animation ──
        text_tab = tabs.add("텍스트 애니메이션")

        ctk.CTkLabel(text_tab, text="참조 이미지:").pack(anchor="w", padx=10, pady=(10, 0))
        ref_row = ctk.CTkFrame(text_tab)
        ref_row.pack(fill="x", padx=10, pady=5)
        self.ref_path = ctk.StringVar()
        ctk.CTkEntry(ref_row, textvariable=self.ref_path).pack(side="left", fill="x", expand=True, padx=(0, 5))
        ctk.CTkButton(ref_row, text="찾아보기", width=80, command=lambda: self._browse(self.ref_path)).pack(side="right")

        ctk.CTkLabel(text_tab, text="설명:").pack(anchor="w", padx=10, pady=(10, 0))
        self.anim_desc = ctk.CTkEntry(text_tab, placeholder_text="기사 캐릭터")
        self.anim_desc.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(text_tab, text="동작:").pack(anchor="w", padx=10, pady=(10, 0))
        self.anim_action = ctk.CTkEntry(text_tab, placeholder_text="앞으로 걷기")
        self.anim_action.pack(fill="x", padx=10, pady=5)

        row = ctk.CTkFrame(text_tab)
        row.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(row, text="너비:").pack(side="left")
        self.w_entry = ctk.CTkEntry(row, width=60)
        self.w_entry.pack(side="left", padx=5)
        self.w_entry.insert(0, "64")
        ctk.CTkLabel(row, text="높이:").pack(side="left", padx=(10, 0))
        self.h_entry = ctk.CTkEntry(row, width=60)
        self.h_entry.pack(side="left", padx=5)
        self.h_entry.insert(0, "64")

        self.pro_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(row, text="Pro (v2)", variable=self.pro_var).pack(side="left", padx=20)

        self.text_anim_btn = ctk.CTkButton(text_tab, text="애니메이션 생성", command=self.animate_text, height=40)
        self.text_anim_btn.pack(fill="x", padx=10, pady=15)

        self.text_result = ctk.CTkLabel(text_tab, text="")
        self.text_result.pack(pady=5)

        # ── Interpolation ──
        interp_tab = tabs.add("보간")

        ctk.CTkLabel(interp_tab, text="시작 이미지:").pack(anchor="w", padx=10, pady=(10, 0))
        s_row = ctk.CTkFrame(interp_tab)
        s_row.pack(fill="x", padx=10, pady=5)
        self.start_path = ctk.StringVar()
        ctk.CTkEntry(s_row, textvariable=self.start_path).pack(side="left", fill="x", expand=True, padx=(0, 5))
        ctk.CTkButton(s_row, text="찾아보기", width=80, command=lambda: self._browse(self.start_path)).pack(side="right")

        ctk.CTkLabel(interp_tab, text="끝 이미지:").pack(anchor="w", padx=10, pady=(10, 0))
        e_row = ctk.CTkFrame(interp_tab)
        e_row.pack(fill="x", padx=10, pady=5)
        self.end_path = ctk.StringVar()
        ctk.CTkEntry(e_row, textvariable=self.end_path).pack(side="left", fill="x", expand=True, padx=(0, 5))
        ctk.CTkButton(e_row, text="찾아보기", width=80, command=lambda: self._browse(self.end_path)).pack(side="right")

        ctk.CTkLabel(interp_tab, text="동작:").pack(anchor="w", padx=10, pady=(10, 0))
        self.interp_action = ctk.CTkEntry(interp_tab, placeholder_text="검 휘두르기")
        self.interp_action.pack(fill="x", padx=10, pady=5)

        self.interp_btn = ctk.CTkButton(interp_tab, text="보간 생성", command=self.interpolate, height=40)
        self.interp_btn.pack(fill="x", padx=10, pady=15)

        self.interp_result = ctk.CTkLabel(interp_tab, text="")
        self.interp_result.pack(pady=5)

    def _browse(self, var):
        path = filedialog.askopenfilename(filetypes=[("이미지", "*.png *.jpg *.jpeg *.gif")])
        if path:
            var.set(path)

    def animate_text(self):
        if not self.require_client():
            return
        ref = self.ref_path.get()
        if not ref:
            messagebox.showwarning("입력 필요", "참조 이미지를 선택해주세요.")
            return
        action = self.anim_action.get().strip()
        desc = self.anim_desc.get().strip()
        if not action:
            messagebox.showwarning("입력 필요", "동작을 입력해주세요.")
            return

        w = int(self.w_entry.get() or 64)
        h = int(self.h_entry.get() or 64)
        use_pro = self.pro_var.get()

        self.text_anim_btn.configure(state="disabled", text="생성중...")
        self.app.status_bar.set_status("애니메이션 생성중...")

        def do_animate():
            ref_img = image_to_base64(ref)
            if use_pro:
                result = self.client.animate_with_text_v2(ref_img, action, w, h, description=desc)
            else:
                result = self.client.animate_with_text(ref_img, desc, action)
            saved = self.handle_job_and_save(result, "anim")
            return saved

        def on_done(saved, err):
            self.text_anim_btn.configure(state="normal", text="애니메이션 생성")
            if err:
                messagebox.showerror("오류", str(err))
                self.app.status_bar.set_status("애니메이션 실패")
                return
            self.text_result.configure(text=f"{len(saved)}개 프레임 저장 완료")
            self.app.status_bar.set_status("준비")

        self.run_async(do_animate, on_done)

    def interpolate(self):
        if not self.require_client():
            return
        start = self.start_path.get()
        end = self.end_path.get()
        action = self.interp_action.get().strip()
        if not start or not end or not action:
            messagebox.showwarning("입력 필요", "모든 항목을 입력해주세요.")
            return

        self.interp_btn.configure(state="disabled", text="보간중...")

        def do_interp():
            start_img = image_to_base64(start)
            end_img = image_to_base64(end)
            result = self.client.interpolate(start_img, end_img, action)
            saved = self.handle_job_and_save(result, "interp")
            return saved

        def on_done(saved, err):
            self.interp_btn.configure(state="normal", text="보간 생성")
            if err:
                messagebox.showerror("오류", str(err))
                return
            self.interp_result.configure(text=f"{len(saved)}개 프레임 저장 완료")

        self.run_async(do_interp, on_done)


# ── Tileset Panel ──

class TilesetPanel(BasePanel):
    def __init__(self, master, app):
        super().__init__(master, app)

        ctk.CTkLabel(self, text="타일셋", font=("", 24, "bold")).pack(pady=(20, 10), anchor="w", padx=20)

        cost_info = ctk.CTkFrame(self)
        cost_info.pack(fill="x", padx=20, pady=(0, 5))
        ctk.CTkLabel(cost_info, text="예상 비용  |  탑다운/횡스크롤: ~$0.04  |  아이소메트릭: ~$0.02  |  프로 타일: ~$0.04",
                     font=("", 11), text_color="orange").pack(padx=10, pady=5)

        tabs = ctk.CTkTabview(self)
        tabs.pack(fill="both", expand=True, padx=20, pady=10)

        # ── Top-down ──
        td_tab = tabs.add("탑다운")

        ctk.CTkLabel(td_tab, text="하단 지형:").pack(anchor="w", padx=10, pady=(10, 0))
        self.td_lower = ctk.CTkEntry(td_tab, placeholder_text="바다, 잔디, 모래...")
        self.td_lower.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(td_tab, text="상단 지형:").pack(anchor="w", padx=10, pady=(10, 0))
        self.td_upper = ctk.CTkEntry(td_tab, placeholder_text="모래, 돌, 흙...")
        self.td_upper.pack(fill="x", padx=10, pady=5)

        row = ctk.CTkFrame(td_tab)
        row.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(row, text="타일 크기:").pack(side="left")
        self.td_size = ctk.CTkOptionMenu(row, values=["16", "32"])
        self.td_size.pack(side="left", padx=10)
        ctk.CTkLabel(row, text="시점:").pack(side="left", padx=(20, 0))
        self.td_view = ctk.CTkOptionMenu(row, values=["low top-down", "high top-down"])
        self.td_view.pack(side="left", padx=10)

        self.td_btn = ctk.CTkButton(td_tab, text="타일셋 생성", command=self.create_topdown, height=40)
        self.td_btn.pack(fill="x", padx=10, pady=15)
        self.td_result = ctk.CTkLabel(td_tab, text="")
        self.td_result.pack(pady=5)

        # ── Sidescroller ──
        ss_tab = tabs.add("횡스크롤")

        ctk.CTkLabel(ss_tab, text="설명:").pack(anchor="w", padx=10, pady=(10, 0))
        self.ss_desc = ctk.CTkEntry(ss_tab, placeholder_text="돌 벽돌")
        self.ss_desc.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(ss_tab, text="전환 효과:").pack(anchor="w", padx=10, pady=(10, 0))
        self.ss_trans = ctk.CTkEntry(ss_tab, placeholder_text="이끼 (선택사항)")
        self.ss_trans.pack(fill="x", padx=10, pady=5)

        self.ss_btn = ctk.CTkButton(ss_tab, text="횡스크롤 타일 생성", command=self.create_sidescroller, height=40)
        self.ss_btn.pack(fill="x", padx=10, pady=15)
        self.ss_result = ctk.CTkLabel(ss_tab, text="")
        self.ss_result.pack(pady=5)

        # ── Isometric ──
        iso_tab = tabs.add("아이소메트릭")

        ctk.CTkLabel(iso_tab, text="설명:").pack(anchor="w", padx=10, pady=(10, 0))
        self.iso_desc = ctk.CTkEntry(iso_tab, placeholder_text="잔디밭")
        self.iso_desc.pack(fill="x", padx=10, pady=5)

        row = ctk.CTkFrame(iso_tab)
        row.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(row, text="형태:").pack(side="left")
        self.iso_shape = ctk.CTkOptionMenu(row, values=["thin tile", "thick tile", "block"])
        self.iso_shape.set("block")
        self.iso_shape.pack(side="left", padx=10)

        self.iso_btn = ctk.CTkButton(iso_tab, text="아이소메트릭 생성", command=self.create_isometric, height=40)
        self.iso_btn.pack(fill="x", padx=10, pady=15)
        self.iso_result = ctk.CTkLabel(iso_tab, text="")
        self.iso_result.pack(pady=5)

        # ── Pro Tiles ──
        pro_tab = tabs.add("프로 타일")

        ctk.CTkLabel(pro_tab, text="설명:").pack(anchor="w", padx=10, pady=(10, 0))
        self.pro_desc = ctk.CTkEntry(pro_tab, placeholder_text="1). 잔디 2). 돌 3). 용암")
        self.pro_desc.pack(fill="x", padx=10, pady=5)

        row = ctk.CTkFrame(pro_tab)
        row.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(row, text="타입:").pack(side="left")
        self.pro_type = ctk.CTkOptionMenu(row, values=["hex", "hex_pointy", "isometric", "octagon", "square_topdown"])
        self.pro_type.set("isometric")
        self.pro_type.pack(side="left", padx=10)
        ctk.CTkLabel(row, text="타일 수:").pack(side="left", padx=(20, 0))
        self.pro_n = ctk.CTkEntry(row, width=60, placeholder_text="3")
        self.pro_n.pack(side="left", padx=5)

        self.pro_btn = ctk.CTkButton(pro_tab, text="프로 타일 생성", command=self.create_pro_tiles, height=40)
        self.pro_btn.pack(fill="x", padx=10, pady=15)
        self.pro_result = ctk.CTkLabel(pro_tab, text="")
        self.pro_result.pack(pady=5)

    def _generate(self, btn, label, fn, btn_text):
        if not self.require_client():
            return
        btn.configure(state="disabled", text="생성중...")
        self.app.status_bar.set_status("타일셋 생성중...")

        def on_done(saved, err):
            btn.configure(state="normal", text=btn_text)
            if err:
                messagebox.showerror("오류", str(err))
                self.app.status_bar.set_status("실패")
                return
            label.configure(text=f"{len(saved)}개 타일 저장 완료")
            self.app.status_bar.set_status("준비")

        self.run_async(fn, on_done)

    def create_topdown(self):
        lower = self.td_lower.get().strip()
        upper = self.td_upper.get().strip()
        if not lower or not upper:
            messagebox.showwarning("입력 필요", "하단/상단 지형을 모두 입력해주세요.")
            return
        size = int(self.td_size.get())
        view = self.td_view.get()

        def fn():
            result = self.client.create_tileset(lower, upper, tile_size={"width": size, "height": size}, view=view)
            return self.handle_job_and_save(result, "tileset")

        self._generate(self.td_btn, self.td_result, fn, "타일셋 생성")

    def create_sidescroller(self):
        desc = self.ss_desc.get().strip()
        if not desc:
            messagebox.showwarning("입력 필요", "설명을 입력해주세요.")
            return
        kwargs = {}
        trans = self.ss_trans.get().strip()
        if trans:
            kwargs["transition_description"] = trans

        def fn():
            result = self.client.create_tileset_sidescroller(desc, **kwargs)
            return self.handle_job_and_save(result, "sidescroller")

        self._generate(self.ss_btn, self.ss_result, fn, "횡스크롤 타일 생성")

    def create_isometric(self):
        desc = self.iso_desc.get().strip()
        if not desc:
            messagebox.showwarning("입력 필요", "설명을 입력해주세요.")
            return

        def fn():
            result = self.client.create_isometric_tile(desc, isometric_tile_shape=self.iso_shape.get())
            return self.handle_job_and_save(result, "iso")

        self._generate(self.iso_btn, self.iso_result, fn, "아이소메트릭 생성")

    def create_pro_tiles(self):
        desc = self.pro_desc.get().strip()
        if not desc:
            messagebox.showwarning("입력 필요", "설명을 입력해주세요.")
            return
        kwargs = {"tile_type": self.pro_type.get()}
        n = self.pro_n.get().strip()
        if n:
            kwargs["n_tiles"] = int(n)

        def fn():
            result = self.client.create_tiles_pro(desc, **kwargs)
            return self.handle_job_and_save(result, "tiles_pro")

        self._generate(self.pro_btn, self.pro_result, fn, "프로 타일 생성")


# ── Edit Panel ──

class EditPanel(BasePanel):
    def __init__(self, master, app):
        super().__init__(master, app)

        ctk.CTkLabel(self, text="편집 / 인페인팅", font=("", 24, "bold")).pack(pady=(20, 10), anchor="w", padx=20)

        cost_info = ctk.CTkFrame(self)
        cost_info.pack(fill="x", padx=20, pady=(0, 5))
        ctk.CTkLabel(cost_info, text="예상 비용  |  편집: ~$0.02  |  인페인팅: ~$0.02  |  리사이즈: ~$0.01  |  픽셀아트 변환: ~$0.01",
                     font=("", 11), text_color="orange").pack(padx=10, pady=5)

        tabs = ctk.CTkTabview(self)
        tabs.pack(fill="both", expand=True, padx=20, pady=10)

        # ── Edit ──
        edit_tab = tabs.add("이미지 편집")

        ctk.CTkLabel(edit_tab, text="이미지:").pack(anchor="w", padx=10, pady=(10, 0))
        row = ctk.CTkFrame(edit_tab)
        row.pack(fill="x", padx=10, pady=5)
        self.edit_path = ctk.StringVar()
        ctk.CTkEntry(row, textvariable=self.edit_path).pack(side="left", fill="x", expand=True, padx=(0, 5))
        ctk.CTkButton(row, text="찾아보기", width=80, command=lambda: self._browse(self.edit_path)).pack(side="right")

        ctk.CTkLabel(edit_tab, text="편집 설명:").pack(anchor="w", padx=10, pady=(10, 0))
        self.edit_desc = ctk.CTkEntry(edit_tab, placeholder_text="빨간 망토 추가")
        self.edit_desc.pack(fill="x", padx=10, pady=5)

        self.edit_btn = ctk.CTkButton(edit_tab, text="이미지 편집", command=self.edit_image, height=40)
        self.edit_btn.pack(fill="x", padx=10, pady=15)

        self.edit_preview = ImagePreview(edit_tab, 300, 300)
        self.edit_preview.pack(pady=5)

        # ── Inpaint ──
        inpaint_tab = tabs.add("인페인팅")

        ctk.CTkLabel(inpaint_tab, text="이미지:").pack(anchor="w", padx=10, pady=(10, 0))
        row = ctk.CTkFrame(inpaint_tab)
        row.pack(fill="x", padx=10, pady=5)
        self.inp_path = ctk.StringVar()
        ctk.CTkEntry(row, textvariable=self.inp_path).pack(side="left", fill="x", expand=True, padx=(0, 5))
        ctk.CTkButton(row, text="찾아보기", width=80, command=lambda: self._browse(self.inp_path)).pack(side="right")

        ctk.CTkLabel(inpaint_tab, text="마스크:").pack(anchor="w", padx=10, pady=(10, 0))
        row = ctk.CTkFrame(inpaint_tab)
        row.pack(fill="x", padx=10, pady=5)
        self.mask_path = ctk.StringVar()
        ctk.CTkEntry(row, textvariable=self.mask_path).pack(side="left", fill="x", expand=True, padx=(0, 5))
        ctk.CTkButton(row, text="찾아보기", width=80, command=lambda: self._browse(self.mask_path)).pack(side="right")

        ctk.CTkLabel(inpaint_tab, text="설명:").pack(anchor="w", padx=10, pady=(10, 0))
        self.inp_desc = ctk.CTkEntry(inpaint_tab, placeholder_text="돌 벽")
        self.inp_desc.pack(fill="x", padx=10, pady=5)

        self.inp_pro_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(inpaint_tab, text="Pro (v3)", variable=self.inp_pro_var).pack(anchor="w", padx=10, pady=5)

        self.inp_btn = ctk.CTkButton(inpaint_tab, text="인페인팅", command=self.do_inpaint, height=40)
        self.inp_btn.pack(fill="x", padx=10, pady=15)

        self.inp_preview = ImagePreview(inpaint_tab, 300, 300)
        self.inp_preview.pack(pady=5)

        # ── Resize & Convert ──
        ops_tab = tabs.add("리사이즈 / 변환")

        ctk.CTkLabel(ops_tab, text="이미지:").pack(anchor="w", padx=10, pady=(10, 0))
        row = ctk.CTkFrame(ops_tab)
        row.pack(fill="x", padx=10, pady=5)
        self.ops_path = ctk.StringVar()
        ctk.CTkEntry(row, textvariable=self.ops_path).pack(side="left", fill="x", expand=True, padx=(0, 5))
        ctk.CTkButton(row, text="찾아보기", width=80, command=lambda: self._browse(self.ops_path)).pack(side="right")

        self.ops_mode = ctk.CTkSegmentedButton(ops_tab, values=["리사이즈", "픽셀아트 변환"])
        self.ops_mode.set("리사이즈")
        self.ops_mode.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(ops_tab, text="설명 (리사이즈용):").pack(anchor="w", padx=10)
        self.ops_desc = ctk.CTkEntry(ops_tab, placeholder_text="기사 캐릭터")
        self.ops_desc.pack(fill="x", padx=10, pady=5)

        row = ctk.CTkFrame(ops_tab)
        row.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(row, text="목표 너비:").pack(side="left")
        self.ops_tw = ctk.CTkEntry(row, width=60)
        self.ops_tw.pack(side="left", padx=5)
        self.ops_tw.insert(0, "128")
        ctk.CTkLabel(row, text="목표 높이:").pack(side="left", padx=(10, 0))
        self.ops_th = ctk.CTkEntry(row, width=60)
        self.ops_th.pack(side="left", padx=5)
        self.ops_th.insert(0, "128")

        self.ops_btn = ctk.CTkButton(ops_tab, text="처리", command=self.process_ops, height=40)
        self.ops_btn.pack(fill="x", padx=10, pady=15)

        self.ops_result = ctk.CTkLabel(ops_tab, text="")
        self.ops_result.pack(pady=5)

    def _browse(self, var):
        path = filedialog.askopenfilename(filetypes=[("이미지", "*.png *.jpg *.jpeg *.gif")])
        if path:
            var.set(path)

    def edit_image(self):
        if not self.require_client():
            return
        path = self.edit_path.get()
        desc = self.edit_desc.get().strip()
        if not path or not desc:
            messagebox.showwarning("입력 필요", "이미지와 설명을 모두 입력해주세요.")
            return

        self.edit_btn.configure(state="disabled", text="편집중...")

        def do_edit():
            img = image_to_base64(path)
            size = get_image_size(path)
            result = self.client.edit_image(img, desc, size["width"], size["height"])
            saved = self.handle_job_and_save(result, "edit")
            return saved

        def on_done(saved, err):
            self.edit_btn.configure(state="normal", text="이미지 편집")
            if err:
                messagebox.showerror("오류", str(err))
                return
            if saved:
                self.edit_preview.show_file(saved[0])

        self.run_async(do_edit, on_done)

    def do_inpaint(self):
        if not self.require_client():
            return
        img_path = self.inp_path.get()
        mask_path = self.mask_path.get()
        desc = self.inp_desc.get().strip()
        if not img_path or not mask_path or not desc:
            messagebox.showwarning("입력 필요", "모든 항목을 입력해주세요.")
            return

        self.inp_btn.configure(state="disabled", text="인페인팅중...")

        def do_inp():
            img = image_to_base64(img_path)
            mask = image_to_base64(mask_path)
            size = get_image_size(img_path)
            w, h = size["width"], size["height"]
            if self.inp_pro_var.get():
                inp_img = {"image": img, "size": {"width": w, "height": h}}
                mask_img = {"image": mask, "size": {"width": w, "height": h}}
                result = self.client.inpaint_v3(desc, inp_img, mask_img)
            else:
                result = self.client.inpaint(desc, img, mask, w, h)
            saved = self.handle_job_and_save(result, "inpaint")
            return saved

        def on_done(saved, err):
            self.inp_btn.configure(state="normal", text="인페인팅")
            if err:
                messagebox.showerror("오류", str(err))
                return
            if saved:
                self.inp_preview.show_file(saved[0])

        self.run_async(do_inp, on_done)

    def process_ops(self):
        if not self.require_client():
            return
        path = self.ops_path.get()
        if not path:
            messagebox.showwarning("입력 필요", "이미지를 선택해주세요.")
            return

        tw = int(self.ops_tw.get() or 128)
        th = int(self.ops_th.get() or 128)
        mode = self.ops_mode.get()

        self.ops_btn.configure(state="disabled", text="처리중...")

        def do_ops():
            img = image_to_base64(path)
            size = get_image_size(path)
            if mode == "리사이즈":
                desc = self.ops_desc.get().strip() or "pixel art"
                result = self.client.resize(desc, img, size["width"], size["height"], tw, th)
            else:
                result = self.client.image_to_pixelart(img, size["width"], size["height"], tw, th)
            saved = self.handle_job_and_save(result, mode.replace(" ", "_"))
            return saved

        def on_done(saved, err):
            self.ops_btn.configure(state="normal", text="처리")
            if err:
                messagebox.showerror("오류", str(err))
                return
            self.ops_result.configure(text=f"{len(saved)}개 이미지 저장 완료")

        self.run_async(do_ops, on_done)


# ── Rotate Panel ──

class RotatePanel(BasePanel):
    def __init__(self, master, app):
        super().__init__(master, app)

        ctk.CTkLabel(self, text="회전", font=("", 24, "bold")).pack(pady=(20, 10), anchor="w", padx=20)

        cost_info = ctk.CTkFrame(self)
        cost_info.pack(fill="x", padx=20, pady=(0, 5))
        ctk.CTkLabel(cost_info, text="예상 비용  |  8방향 회전: ~$0.08  |  단일 회전: ~$0.01",
                     font=("", 11), text_color="orange").pack(padx=10, pady=5)

        tabs = ctk.CTkTabview(self)
        tabs.pack(fill="both", expand=True, padx=20, pady=10)

        # ── 8 Rotations ──
        rot8_tab = tabs.add("8방향 회전")

        ctk.CTkLabel(rot8_tab, text="참조 이미지:").pack(anchor="w", padx=10, pady=(10, 0))
        row = ctk.CTkFrame(rot8_tab)
        row.pack(fill="x", padx=10, pady=5)
        self.rot8_path = ctk.StringVar()
        ctk.CTkEntry(row, textvariable=self.rot8_path).pack(side="left", fill="x", expand=True, padx=(0, 5))
        ctk.CTkButton(row, text="찾아보기", width=80, command=lambda: self._browse(self.rot8_path)).pack(side="right")

        row2 = ctk.CTkFrame(rot8_tab)
        row2.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(row2, text="너비:").pack(side="left")
        self.rot8_w = ctk.CTkEntry(row2, width=60)
        self.rot8_w.pack(side="left", padx=5)
        self.rot8_w.insert(0, "64")
        ctk.CTkLabel(row2, text="높이:").pack(side="left", padx=(10, 0))
        self.rot8_h = ctk.CTkEntry(row2, width=60)
        self.rot8_h.pack(side="left", padx=5)
        self.rot8_h.insert(0, "64")
        ctk.CTkLabel(row2, text="시점:").pack(side="left", padx=(20, 0))
        self.rot8_view = ctk.CTkOptionMenu(row2, values=["low top-down", "high top-down", "side"])
        self.rot8_view.pack(side="left", padx=10)

        self.rot8_nobg = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(rot8_tab, text="배경 제거", variable=self.rot8_nobg).pack(anchor="w", padx=10, pady=5)

        self.rot8_btn = ctk.CTkButton(rot8_tab, text="8방향 회전 생성", command=self.gen_8rot, height=40)
        self.rot8_btn.pack(fill="x", padx=10, pady=15)
        self.rot8_result = ctk.CTkLabel(rot8_tab, text="")
        self.rot8_result.pack(pady=5)

        # ── Single Rotation ──
        single_tab = tabs.add("단일 회전")

        ctk.CTkLabel(single_tab, text="이미지:").pack(anchor="w", padx=10, pady=(10, 0))
        row = ctk.CTkFrame(single_tab)
        row.pack(fill="x", padx=10, pady=5)
        self.single_path = ctk.StringVar()
        ctk.CTkEntry(row, textvariable=self.single_path).pack(side="left", fill="x", expand=True, padx=(0, 5))
        ctk.CTkButton(row, text="찾아보기", width=80, command=lambda: self._browse(self.single_path)).pack(side="right")

        ctk.CTkLabel(single_tab, text="목표 방향:").pack(anchor="w", padx=10, pady=(10, 0))
        self.single_dir = ctk.CTkOptionMenu(single_tab, values=[
            "north", "north-east", "east", "south-east",
            "south", "south-west", "west", "north-west",
        ])
        self.single_dir.pack(fill="x", padx=10, pady=5)

        self.single_btn = ctk.CTkButton(single_tab, text="회전", command=self.rotate_single, height=40)
        self.single_btn.pack(fill="x", padx=10, pady=15)

        self.single_preview = ImagePreview(single_tab, 300, 300)
        self.single_preview.pack(pady=5)

    def _browse(self, var):
        path = filedialog.askopenfilename(filetypes=[("이미지", "*.png *.jpg *.jpeg *.gif")])
        if path:
            var.set(path)

    def gen_8rot(self):
        if not self.require_client():
            return
        ref = self.rot8_path.get()
        if not ref:
            messagebox.showwarning("입력 필요", "참조 이미지를 선택해주세요.")
            return

        w = int(self.rot8_w.get() or 64)
        h = int(self.rot8_h.get() or 64)

        self.rot8_btn.configure(state="disabled", text="생성중...")

        def do_rot():
            ref_img = image_to_base64(ref)
            ref_size = get_image_size(ref)
            kwargs = {
                "reference_image": {"image": ref_img, "size": ref_size},
                "view": self.rot8_view.get(),
            }
            if self.rot8_nobg.get():
                kwargs["no_background"] = True
            result = self.client.generate_8_rotations(w, h, **kwargs)
            saved = self.handle_job_and_save(result, "rot8")
            return saved

        def on_done(saved, err):
            self.rot8_btn.configure(state="normal", text="8방향 회전 생성")
            if err:
                messagebox.showerror("오류", str(err))
                return
            self.rot8_result.configure(text=f"{len(saved)}개 회전 저장 완료")

        self.run_async(do_rot, on_done)

    def rotate_single(self):
        if not self.require_client():
            return
        path = self.single_path.get()
        if not path:
            messagebox.showwarning("입력 필요", "이미지를 선택해주세요.")
            return

        self.single_btn.configure(state="disabled", text="회전중...")

        def do_rot():
            img = image_to_base64(path)
            size = get_image_size(path)
            result = self.client.rotate(img, size["width"], size["height"], to_direction=self.single_dir.get())
            saved = self.handle_job_and_save(result, "rotated")
            return saved

        def on_done(saved, err):
            self.single_btn.configure(state="normal", text="회전")
            if err:
                messagebox.showerror("오류", str(err))
                return
            if saved:
                self.single_preview.show_file(saved[0])

        self.run_async(do_rot, on_done)


# ── Settings Panel ──

class SettingsPanel(BasePanel):
    def __init__(self, master, app):
        super().__init__(master, app)

        ctk.CTkLabel(self, text="설정", font=("", 24, "bold")).pack(pady=(20, 10), anchor="w", padx=20)

        form = ctk.CTkFrame(self)
        form.pack(fill="x", padx=20, pady=10)

        # API Key
        ctk.CTkLabel(form, text="API 키:").pack(anchor="w", padx=10, pady=(15, 0))
        key_row = ctk.CTkFrame(form)
        key_row.pack(fill="x", padx=10, pady=5)
        self.key_entry = ctk.CTkEntry(key_row, show="*", placeholder_text="PixelLab API 키를 입력하세요")
        self.key_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))

        self.show_key_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(key_row, text="표시", variable=self.show_key_var, command=self.toggle_key_visibility, width=60).pack(side="right")

        existing_key = os.environ.get("PIXELLAB_API_KEY", "")
        if existing_key:
            self.key_entry.insert(0, existing_key)

        # Output dir
        ctk.CTkLabel(form, text="출력 디렉토리:").pack(anchor="w", padx=10, pady=(15, 0))
        out_row = ctk.CTkFrame(form)
        out_row.pack(fill="x", padx=10, pady=5)
        self.out_entry = ctk.CTkEntry(out_row)
        self.out_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.out_entry.insert(0, app.output_dir)
        ctk.CTkButton(out_row, text="찾아보기", width=80, command=self.browse_output).pack(side="right")

        # Appearance
        ctk.CTkLabel(form, text="테마:").pack(anchor="w", padx=10, pady=(15, 0))
        self.appearance_var = ctk.StringVar(value="dark")
        ctk.CTkOptionMenu(form, values=["dark", "light", "system"], variable=self.appearance_var,
                          command=lambda v: ctk.set_appearance_mode(v)).pack(anchor="w", padx=10, pady=5)

        # Save
        ctk.CTkButton(form, text="저장 및 연결", command=self.save_settings, height=40,
                      font=("", 14, "bold")).pack(fill="x", padx=10, pady=20)

        # Info
        info = ctk.CTkFrame(self)
        info.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(info, text="API 키 발급: https://pixellab.ai/account",
                     text_color="gray").pack(padx=10, pady=10)
        ctk.CTkLabel(info, text="API 문서: https://api.pixellab.ai/v2/docs",
                     text_color="gray").pack(padx=10, pady=(0, 10))

    def toggle_key_visibility(self):
        self.key_entry.configure(show="" if self.show_key_var.get() else "*")

    def browse_output(self):
        path = filedialog.askdirectory()
        if path:
            self.out_entry.delete(0, "end")
            self.out_entry.insert(0, path)

    def save_settings(self):
        key = self.key_entry.get().strip()
        out_dir = self.out_entry.get().strip()

        if not key:
            messagebox.showwarning("API 키 필요", "API 키를 입력해주세요.")
            return

        self.app.output_dir = out_dir or DEFAULT_OUTPUT_DIR

        env_path = Path(".env")
        env_path.write_text(f"PIXELLAB_API_KEY={key}\n")
        os.environ["PIXELLAB_API_KEY"] = key

        self.app.client = PixelLabClient(key)
        self.app.status_bar.set_status("연결됨")
        messagebox.showinfo("저장 완료", "설정이 저장되고 API에 연결되었습니다.")


# ── Main Application ──

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
