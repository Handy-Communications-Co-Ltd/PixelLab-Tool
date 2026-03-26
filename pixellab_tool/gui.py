"""PixelLab GUI - Modern pixel art generation tool."""

import base64
import io
import json
import os
import threading
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk
from dotenv import load_dotenv
from PIL import Image, ImageTk

from .client import PixelLabClient, PixelLabError
from .utils import image_to_base64, get_image_size, save_images_from_response

load_dotenv()

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ── Constants ──

SIDEBAR_ITEMS = [
    ("Dashboard", "D"),
    ("Generate", "G"),
    ("Character", "C"),
    ("Animation", "A"),
    ("Tileset", "T"),
    ("Edit", "E"),
    ("Rotate", "R"),
    ("Settings", "S"),
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

DEFAULT_OUTPUT_DIR = "output"


class StatusBar(ctk.CTkFrame):
    """Bottom status bar showing connection and credit info."""

    def __init__(self, master):
        super().__init__(master, height=30)
        self.label = ctk.CTkLabel(self, text="Not connected", anchor="w", font=("", 12))
        self.label.pack(side="left", padx=10)
        self.credit_label = ctk.CTkLabel(self, text="", anchor="e", font=("", 12))
        self.credit_label.pack(side="right", padx=10)

    def set_status(self, text: str):
        self.label.configure(text=text)

    def set_credits(self, text: str):
        self.credit_label.configure(text=text)


class ImagePreview(ctk.CTkFrame):
    """Reusable image preview widget."""

    def __init__(self, master, width=300, height=300):
        super().__init__(master)
        self.preview_size = (width, height)
        self.canvas_label = ctk.CTkLabel(self, text="No image", width=width, height=height)
        self.canvas_label.pack(padx=5, pady=5)
        self._photo = None  # prevent GC

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

    def clear(self):
        self._photo = None
        self.canvas_label.configure(image=None, text="No image")


# ── Panel Base ──

class BasePanel(ctk.CTkScrollableFrame):
    """Base panel with common utilities."""

    def __init__(self, master, app: "PixelLabApp"):
        super().__init__(master)
        self.app = app

    @property
    def client(self) -> PixelLabClient | None:
        return self.app.client

    def run_async(self, fn, callback=None):
        """Run a function in a background thread, call callback with result on main thread."""
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
            messagebox.showwarning("Not Connected", "Please set your API key in Settings first.")
            return False
        return True

    def handle_job_and_save(self, result: dict, prefix: str, output_dir: str = None) -> list[str]:
        """Handle async job polling and save images."""
        out = output_dir or self.app.output_dir
        job_id = result.get("background_job_id") or (result.get("data") or {}).get("background_job_id")
        if job_id:
            self.app.status_bar.set_status(f"Job {job_id[:12]}... processing")
            result = self.client.wait_for_job(job_id)
            self.app.status_bar.set_status("Job completed")
        saved = save_images_from_response(result, out, prefix)
        return saved


# ── Dashboard Panel ──

class DashboardPanel(BasePanel):
    def __init__(self, master, app):
        super().__init__(master, app)

        ctk.CTkLabel(self, text="Dashboard", font=("", 24, "bold")).pack(pady=(20, 10), anchor="w", padx=20)

        cards_frame = ctk.CTkFrame(self, fg_color="transparent")
        cards_frame.pack(fill="x", padx=20, pady=10)

        # Credits card
        credit_card = ctk.CTkFrame(cards_frame)
        credit_card.pack(side="left", fill="both", expand=True, padx=(0, 5))
        ctk.CTkLabel(credit_card, text="Credits", font=("", 12), text_color="gray").pack(pady=(15, 0), padx=15, anchor="w")
        self.balance_label = ctk.CTkLabel(credit_card, text="--", font=("", 32, "bold"))
        self.balance_label.pack(pady=(0, 15), padx=15, anchor="w")

        # Generations card
        gen_card = ctk.CTkFrame(cards_frame)
        gen_card.pack(side="left", fill="both", expand=True, padx=(5, 5))
        ctk.CTkLabel(gen_card, text="Generations", font=("", 12), text_color="gray").pack(pady=(15, 0), padx=15, anchor="w")
        self.generations_label = ctk.CTkLabel(gen_card, text="--", font=("", 32, "bold"))
        self.generations_label.pack(pady=(0, 15), padx=15, anchor="w")

        # Refresh card
        refresh_card = ctk.CTkFrame(cards_frame)
        refresh_card.pack(side="left", fill="both", expand=True, padx=(5, 0))
        ctk.CTkButton(refresh_card, text="Refresh", command=self.refresh_balance, height=50).pack(pady=15, padx=15, fill="x")

        # Quick actions
        ctk.CTkLabel(self, text="Quick Actions", font=("", 18, "bold")).pack(pady=(20, 10), anchor="w", padx=20)

        quick_frame = ctk.CTkFrame(self)
        quick_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkButton(quick_frame, text="Generate Image", command=lambda: app.show_panel("Generate")).pack(side="left", padx=10, pady=10)
        ctk.CTkButton(quick_frame, text="Create Character", command=lambda: app.show_panel("Character")).pack(side="left", padx=10, pady=10)
        ctk.CTkButton(quick_frame, text="Create Tileset", command=lambda: app.show_panel("Tileset")).pack(side="left", padx=10, pady=10)

    def refresh_balance(self):
        if not self.require_client():
            return
        self.app.status_bar.set_status("Fetching balance...")

        def fetch():
            return self.client.get_balance()

        def on_done(result, err):
            if err:
                messagebox.showerror("Error", str(err))
                self.app.status_bar.set_status("Error fetching balance")
                return
            data = result.get("data", result)
            credits = data.get("remaining_credits", data.get("credits", "N/A"))
            gens = data.get("remaining_generations", data.get("generations", "N/A"))
            self.balance_label.configure(text=str(credits))
            self.generations_label.configure(text=str(gens))
            self.app.status_bar.set_credits(f"Credits: {credits}")
            self.app.status_bar.set_status("Ready")

        self.run_async(fetch, on_done)


# ── Generate Panel ──

class GeneratePanel(BasePanel):
    def __init__(self, master, app):
        super().__init__(master, app)

        ctk.CTkLabel(self, text="Generate Pixel Art", font=("", 24, "bold")).pack(pady=(20, 10), anchor="w", padx=20)

        # Form
        form = ctk.CTkFrame(self)
        form.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(form, text="Description:").pack(anchor="w", padx=10, pady=(10, 0))
        self.desc_entry = ctk.CTkTextbox(form, height=80)
        self.desc_entry.pack(fill="x", padx=10, pady=5)

        row1 = ctk.CTkFrame(form)
        row1.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(row1, text="Model:").pack(side="left")
        self.model_var = ctk.StringVar(value="pro")
        ctk.CTkOptionMenu(row1, values=["pro", "pixflux", "bitforge"], variable=self.model_var).pack(side="left", padx=10)

        ctk.CTkLabel(row1, text="Width:").pack(side="left", padx=(20, 0))
        self.width_entry = ctk.CTkEntry(row1, width=60, placeholder_text="128")
        self.width_entry.pack(side="left", padx=5)
        self.width_entry.insert(0, "128")

        ctk.CTkLabel(row1, text="Height:").pack(side="left", padx=(10, 0))
        self.height_entry = ctk.CTkEntry(row1, width=60, placeholder_text="128")
        self.height_entry.pack(side="left", padx=5)
        self.height_entry.insert(0, "128")

        row2 = ctk.CTkFrame(form)
        row2.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(row2, text="Seed:").pack(side="left")
        self.seed_entry = ctk.CTkEntry(row2, width=80, placeholder_text="Random")
        self.seed_entry.pack(side="left", padx=10)

        self.no_bg_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(row2, text="No Background", variable=self.no_bg_var).pack(side="left", padx=20)

        # Generate type tabs
        self.gen_type = ctk.CTkSegmentedButton(form, values=["Image", "UI", "Style"])
        self.gen_type.set("Image")
        self.gen_type.pack(fill="x", padx=10, pady=10)

        # Style reference
        self.style_frame = ctk.CTkFrame(form)
        self.style_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(self.style_frame, text="Style Reference (for Style mode):").pack(anchor="w")
        style_row = ctk.CTkFrame(self.style_frame)
        style_row.pack(fill="x")
        self.style_path_var = ctk.StringVar()
        ctk.CTkEntry(style_row, textvariable=self.style_path_var).pack(side="left", fill="x", expand=True, padx=(0, 5))
        ctk.CTkButton(style_row, text="Browse", width=80, command=self.browse_style).pack(side="right")

        # Generate button
        self.gen_btn = ctk.CTkButton(form, text="Generate", command=self.generate, height=40, font=("", 14, "bold"))
        self.gen_btn.pack(pady=15, padx=10, fill="x")

        # Preview
        self.preview = ImagePreview(self, 400, 400)
        self.preview.pack(pady=10)

        self.result_label = ctk.CTkLabel(self, text="")
        self.result_label.pack(pady=5)

    def browse_style(self):
        path = filedialog.askopenfilename(filetypes=[("Images", "*.png *.jpg *.jpeg *.gif")])
        if path:
            self.style_path_var.set(path)

    def generate(self):
        if not self.require_client():
            return
        desc = self.desc_entry.get("1.0", "end").strip()
        if not desc:
            messagebox.showwarning("Input Required", "Please enter a description.")
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

        self.gen_btn.configure(state="disabled", text="Generating...")
        self.app.status_bar.set_status("Generating...")

        def do_generate():
            if gen_type == "Style":
                style_path = self.style_path_var.get()
                if not style_path:
                    raise ValueError("Please select a style reference image.")
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
            self.gen_btn.configure(state="normal", text="Generate")
            if err:
                messagebox.showerror("Error", str(err))
                self.app.status_bar.set_status("Generation failed")
                return
            if saved:
                self.preview.show_file(saved[0])
                self.result_label.configure(text=f"Saved {len(saved)} image(s) to {self.app.output_dir}/")
            self.app.status_bar.set_status("Ready")

        self.run_async(do_generate, on_done)


# ── Character Panel ──

class CharacterPanel(BasePanel):
    def __init__(self, master, app):
        super().__init__(master, app)

        ctk.CTkLabel(self, text="Characters", font=("", 24, "bold")).pack(pady=(20, 10), anchor="w", padx=20)

        # Create tab
        tabs = ctk.CTkTabview(self)
        tabs.pack(fill="both", expand=True, padx=20, pady=10)

        # ── Create Tab ──
        create_tab = tabs.add("Create")

        ctk.CTkLabel(create_tab, text="Description:").pack(anchor="w", padx=10, pady=(10, 0))
        self.desc_entry = ctk.CTkEntry(create_tab, placeholder_text="brave knight with shining armor")
        self.desc_entry.pack(fill="x", padx=10, pady=5)

        row = ctk.CTkFrame(create_tab)
        row.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(row, text="Directions:").pack(side="left")
        self.dir_var = ctk.StringVar(value="4")
        ctk.CTkOptionMenu(row, values=["4", "8"], variable=self.dir_var).pack(side="left", padx=10)

        ctk.CTkLabel(row, text="Size:").pack(side="left", padx=(20, 0))
        self.size_var = ctk.StringVar(value="64x64")
        ctk.CTkOptionMenu(row, values=CHARACTER_SIZE_PRESETS, variable=self.size_var).pack(side="left", padx=10)

        ctk.CTkLabel(row, text="View:").pack(side="left", padx=(20, 0))
        self.view_var = ctk.StringVar(value="side")
        ctk.CTkOptionMenu(row, values=["side", "low top-down", "high top-down", "perspective"], variable=self.view_var).pack(side="left", padx=10)

        row2 = ctk.CTkFrame(create_tab)
        row2.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(row2, text="Template:").pack(side="left")
        self.template_var = ctk.StringVar(value="mannequin")
        ctk.CTkOptionMenu(row2, values=["mannequin", "bear", "cat", "dog", "horse", "lion"], variable=self.template_var).pack(side="left", padx=10)

        ctk.CTkLabel(row2, text="Detail:").pack(side="left", padx=(20, 0))
        self.detail_var = ctk.StringVar(value="medium")
        ctk.CTkOptionMenu(row2, values=["low", "medium", "high"], variable=self.detail_var).pack(side="left", padx=10)

        row3 = ctk.CTkFrame(create_tab)
        row3.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(row3, text="Outline:").pack(side="left")
        self.outline_var = ctk.StringVar(value="none")
        ctk.CTkOptionMenu(row3, values=["none", "thin", "medium", "thick"], variable=self.outline_var).pack(side="left", padx=10)

        ctk.CTkLabel(row3, text="Shading:").pack(side="left", padx=(20, 0))
        self.shading_var = ctk.StringVar(value="none")
        ctk.CTkOptionMenu(row3, values=["none", "soft", "hard", "flat"], variable=self.shading_var).pack(side="left", padx=10)

        ctk.CTkLabel(row3, text="Seed:").pack(side="left", padx=(20, 0))
        self.seed_entry = ctk.CTkEntry(row3, width=80, placeholder_text="Random")
        self.seed_entry.pack(side="left", padx=5)

        self.isometric_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(row3, text="Isometric", variable=self.isometric_var).pack(side="left", padx=20)

        self.create_btn = ctk.CTkButton(create_tab, text="Create Character", command=self.create_character, height=40, font=("", 14, "bold"))
        self.create_btn.pack(fill="x", padx=10, pady=15)

        self.create_preview = ImagePreview(create_tab, 300, 300)
        self.create_preview.pack(pady=5)

        self.create_result = ctk.CTkLabel(create_tab, text="")
        self.create_result.pack(pady=5)

        # ── Manage Tab ──
        manage_tab = tabs.add("Manage")

        btn_row = ctk.CTkFrame(manage_tab)
        btn_row.pack(fill="x", padx=10, pady=10)
        ctk.CTkButton(btn_row, text="Refresh List", command=self.refresh_list).pack(side="left", padx=5)
        ctk.CTkButton(btn_row, text="Export Selected", command=self.export_selected).pack(side="left", padx=5)
        ctk.CTkButton(btn_row, text="Delete Selected", command=self.delete_selected, fg_color="red", hover_color="darkred").pack(side="left", padx=5)

        self.char_list_frame = ctk.CTkScrollableFrame(manage_tab, height=400)
        self.char_list_frame.pack(fill="both", expand=True, padx=10, pady=5)
        self.selected_char_id = ctk.StringVar()
        self.char_widgets = []
        self.char_photos = []  # prevent GC

        # ── Animate Tab ──
        anim_tab = tabs.add("Animate")

        ctk.CTkLabel(anim_tab, text="Character ID:").pack(anchor="w", padx=10, pady=(10, 0))
        self.anim_char_id = ctk.CTkEntry(anim_tab, placeholder_text="Paste character ID or select from Manage tab")
        self.anim_char_id.pack(fill="x", padx=10, pady=5)

        ctk.CTkButton(anim_tab, text="Use Selected Character", width=180,
                      command=lambda: self.anim_char_id.insert(0, self.selected_char_id.get()) if self.selected_char_id.get() else None
                      ).pack(anchor="w", padx=10, pady=2)

        ctk.CTkLabel(anim_tab, text="Template Animation:").pack(anchor="w", padx=10, pady=(10, 0))
        self.anim_template = ctk.CTkOptionMenu(anim_tab, values=ANIMATION_TEMPLATES)
        self.anim_template.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(anim_tab, text="Custom Action (optional - overrides template description):").pack(anchor="w", padx=10, pady=(10, 0))
        self.anim_action_desc = ctk.CTkEntry(anim_tab, placeholder_text="e.g. swinging a large hammer aggressively")
        self.anim_action_desc.pack(fill="x", padx=10, pady=5)

        anim_opts = ctk.CTkFrame(anim_tab)
        anim_opts.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(anim_opts, text="Directions:").pack(side="left")
        self.anim_dirs_var = ctk.StringVar(value="all")
        ctk.CTkOptionMenu(anim_opts, values=["all", "south", "west", "east", "north",
                                              "south-west", "south-east", "north-west", "north-east"],
                          variable=self.anim_dirs_var).pack(side="left", padx=10)

        ctk.CTkLabel(anim_opts, text="Seed:").pack(side="left", padx=(20, 0))
        self.anim_seed = ctk.CTkEntry(anim_opts, width=80, placeholder_text="Random")
        self.anim_seed.pack(side="left", padx=5)

        self.anim_btn = ctk.CTkButton(anim_tab, text="Animate", command=self.animate_character, height=40, font=("", 14, "bold"))
        self.anim_btn.pack(fill="x", padx=10, pady=15)

        self.anim_result = ctk.CTkLabel(anim_tab, text="")
        self.anim_result.pack(pady=5)

    def create_character(self):
        if not self.require_client():
            return
        desc = self.desc_entry.get().strip()
        if not desc:
            messagebox.showwarning("Input Required", "Please enter a description.")
            return

        size_parts = self.size_var.get().split("x")
        w, h = int(size_parts[0]), int(size_parts[1])
        dirs = self.dir_var.get()
        kwargs = {}
        kwargs["view"] = self.view_var.get()
        kwargs["template_id"] = self.template_var.get()
        kwargs["detail"] = self.detail_var.get()
        if self.isometric_var.get():
            kwargs["isometric"] = True
        outline = self.outline_var.get()
        if outline != "none":
            kwargs["outline"] = outline
        shading = self.shading_var.get()
        if shading != "none":
            kwargs["shading"] = shading
        seed_text = self.seed_entry.get().strip()
        if seed_text:
            kwargs["seed"] = int(seed_text)

        self.create_btn.configure(state="disabled", text="Creating...")
        self.app.status_bar.set_status("Creating character...")

        def do_create():
            if dirs == "4":
                result = self.client.create_character_4dir(desc, w, h, **kwargs)
            else:
                result = self.client.create_character_8dir(desc, w, h, **kwargs)
            char_id = result.get("character_id", "N/A")
            saved = self.handle_job_and_save(result, "character")
            return char_id, saved

        def on_done(res, err):
            self.create_btn.configure(state="normal", text="Create Character")
            if err:
                messagebox.showerror("Error", str(err))
                self.app.status_bar.set_status("Creation failed")
                return
            char_id, saved = res
            self.create_result.configure(text=f"Character ID: {char_id}")
            if saved:
                self.create_preview.show_file(saved[0])
            self.app.status_bar.set_status("Ready")

        self.run_async(do_create, on_done)

    def refresh_list(self):
        if not self.require_client():
            return
        self.app.status_bar.set_status("Loading characters...")

        def fetch():
            result = self.client.list_characters(limit=50)
            data = result.get("data", result)
            characters = data if isinstance(data, list) else data.get("characters", [])
            # Fetch details for each character to get images
            detailed = []
            for ch in characters:
                cid = str(ch.get("id", ""))
                try:
                    detail = self.client.get_character(cid)
                    detail_data = detail.get("data", detail)
                    detailed.append(detail_data)
                except Exception:
                    detailed.append(ch)
            return detailed

        def on_done(characters, err):
            if err:
                messagebox.showerror("Error", str(err))
                self.app.status_bar.set_status("Error loading characters")
                return
            for w in self.char_list_frame.winfo_children():
                w.destroy()
            self.char_widgets.clear()
            self.char_photos.clear()

            if not characters:
                ctk.CTkLabel(self.char_list_frame, text="No characters found.").pack(pady=10)
                self.app.status_bar.set_status("Ready")
                return

            for ch in characters:
                cid = str(ch.get("id", ch.get("character_id", "")))
                desc = str(ch.get("description", ""))[:40]

                card = ctk.CTkFrame(self.char_list_frame)
                card.pack(fill="x", padx=5, pady=3)

                # Try to show thumbnail
                thumb_label = ctk.CTkLabel(card, text="", width=64, height=64)
                thumb_label.pack(side="left", padx=5, pady=5)

                images = ch.get("images", ch.get("sprites", []))
                if isinstance(images, dict):
                    # Sometimes images is a dict with direction keys
                    first_img = next(iter(images.values()), None)
                elif isinstance(images, list) and images:
                    first_img = images[0]
                else:
                    first_img = None

                b64_data = None
                if isinstance(first_img, dict):
                    b64_data = first_img.get("base64")
                elif isinstance(first_img, str):
                    b64_data = first_img

                if b64_data:
                    try:
                        raw = base64.b64decode(b64_data)
                        img = Image.open(io.BytesIO(raw))
                        img.thumbnail((64, 64), Image.NEAREST)
                        photo = ImageTk.PhotoImage(img)
                        thumb_label.configure(image=photo)
                        self.char_photos.append(photo)
                    except Exception:
                        thumb_label.configure(text="[img]")
                else:
                    thumb_label.configure(text="[no img]")

                info_frame = ctk.CTkFrame(card, fg_color="transparent")
                info_frame.pack(side="left", fill="x", expand=True, padx=5)

                ctk.CTkLabel(info_frame, text=desc or "No description", font=("", 13, "bold"), anchor="w").pack(anchor="w")
                ctk.CTkLabel(info_frame, text=f"ID: {cid[:20]}", font=("", 10), text_color="gray", anchor="w").pack(anchor="w")

                rb = ctk.CTkRadioButton(card, text="Select", variable=self.selected_char_id, value=cid, width=70)
                rb.pack(side="right", padx=10)
                self.char_widgets.append(card)

            self.app.status_bar.set_status(f"Loaded {len(characters)} characters")

        self.run_async(fetch, on_done)

    def export_selected(self):
        cid = self.selected_char_id.get()
        if not cid or not self.require_client():
            messagebox.showwarning("Select Character", "Please select a character first.")
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
                messagebox.showerror("Error", str(err))
                return
            messagebox.showinfo("Exported", f"Saved to: {path}")

        self.run_async(do_export, on_done)

    def delete_selected(self):
        cid = self.selected_char_id.get()
        if not cid or not self.require_client():
            return
        if not messagebox.askyesno("Confirm", f"Delete character {cid[:12]}...?"):
            return

        def do_delete():
            self.client.delete_character(cid)

        def on_done(_, err):
            if err:
                messagebox.showerror("Error", str(err))
                return
            messagebox.showinfo("Deleted", "Character deleted.")
            self.refresh_list()

        self.run_async(do_delete, on_done)

    def animate_character(self):
        if not self.require_client():
            return
        cid = self.anim_char_id.get().strip()
        if not cid:
            messagebox.showwarning("Input Required", "Please enter a character ID.")
            return

        template = self.anim_template.get()
        self.anim_btn.configure(state="disabled", text="Animating...")
        self.app.status_bar.set_status("Animating...")

        def do_animate():
            kwargs = {}
            action_desc = self.anim_action_desc.get().strip()
            if action_desc:
                kwargs["action_description"] = action_desc
            dirs = self.anim_dirs_var.get()
            if dirs != "all":
                kwargs["directions"] = [dirs]
            seed_text = self.anim_seed.get().strip()
            if seed_text:
                kwargs["seed"] = int(seed_text)
            result = self.client.animate_character(cid, template, **kwargs)
            saved = self.handle_job_and_save(result, "anim")
            return saved

        def on_done(saved, err):
            self.anim_btn.configure(state="normal", text="Animate")
            if err:
                messagebox.showerror("Error", str(err))
                self.app.status_bar.set_status("Animation failed")
                return
            self.anim_result.configure(text=f"Saved {len(saved)} frame(s)")
            self.app.status_bar.set_status("Ready")

        self.run_async(do_animate, on_done)


# ── Animation Panel ──

class AnimationPanel(BasePanel):
    def __init__(self, master, app):
        super().__init__(master, app)

        ctk.CTkLabel(self, text="Animation", font=("", 24, "bold")).pack(pady=(20, 10), anchor="w", padx=20)

        tabs = ctk.CTkTabview(self)
        tabs.pack(fill="both", expand=True, padx=20, pady=10)

        # ── Text Animation ──
        text_tab = tabs.add("Text Animation")

        ctk.CTkLabel(text_tab, text="Reference Image:").pack(anchor="w", padx=10, pady=(10, 0))
        ref_row = ctk.CTkFrame(text_tab)
        ref_row.pack(fill="x", padx=10, pady=5)
        self.ref_path = ctk.StringVar()
        ctk.CTkEntry(ref_row, textvariable=self.ref_path).pack(side="left", fill="x", expand=True, padx=(0, 5))
        ctk.CTkButton(ref_row, text="Browse", width=80, command=lambda: self._browse(self.ref_path)).pack(side="right")

        ctk.CTkLabel(text_tab, text="Description:").pack(anchor="w", padx=10, pady=(10, 0))
        self.anim_desc = ctk.CTkEntry(text_tab, placeholder_text="knight character")
        self.anim_desc.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(text_tab, text="Action:").pack(anchor="w", padx=10, pady=(10, 0))
        self.anim_action = ctk.CTkEntry(text_tab, placeholder_text="walking forward")
        self.anim_action.pack(fill="x", padx=10, pady=5)

        row = ctk.CTkFrame(text_tab)
        row.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(row, text="Width:").pack(side="left")
        self.w_entry = ctk.CTkEntry(row, width=60)
        self.w_entry.pack(side="left", padx=5)
        self.w_entry.insert(0, "64")
        ctk.CTkLabel(row, text="Height:").pack(side="left", padx=(10, 0))
        self.h_entry = ctk.CTkEntry(row, width=60)
        self.h_entry.pack(side="left", padx=5)
        self.h_entry.insert(0, "64")

        self.pro_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(row, text="Pro (v2)", variable=self.pro_var).pack(side="left", padx=20)

        self.text_anim_btn = ctk.CTkButton(text_tab, text="Animate", command=self.animate_text, height=40)
        self.text_anim_btn.pack(fill="x", padx=10, pady=15)

        self.text_result = ctk.CTkLabel(text_tab, text="")
        self.text_result.pack(pady=5)

        # ── Interpolation ──
        interp_tab = tabs.add("Interpolation")

        ctk.CTkLabel(interp_tab, text="Start Image:").pack(anchor="w", padx=10, pady=(10, 0))
        s_row = ctk.CTkFrame(interp_tab)
        s_row.pack(fill="x", padx=10, pady=5)
        self.start_path = ctk.StringVar()
        ctk.CTkEntry(s_row, textvariable=self.start_path).pack(side="left", fill="x", expand=True, padx=(0, 5))
        ctk.CTkButton(s_row, text="Browse", width=80, command=lambda: self._browse(self.start_path)).pack(side="right")

        ctk.CTkLabel(interp_tab, text="End Image:").pack(anchor="w", padx=10, pady=(10, 0))
        e_row = ctk.CTkFrame(interp_tab)
        e_row.pack(fill="x", padx=10, pady=5)
        self.end_path = ctk.StringVar()
        ctk.CTkEntry(e_row, textvariable=self.end_path).pack(side="left", fill="x", expand=True, padx=(0, 5))
        ctk.CTkButton(e_row, text="Browse", width=80, command=lambda: self._browse(self.end_path)).pack(side="right")

        ctk.CTkLabel(interp_tab, text="Action:").pack(anchor="w", padx=10, pady=(10, 0))
        self.interp_action = ctk.CTkEntry(interp_tab, placeholder_text="swinging sword")
        self.interp_action.pack(fill="x", padx=10, pady=5)

        self.interp_btn = ctk.CTkButton(interp_tab, text="Interpolate", command=self.interpolate, height=40)
        self.interp_btn.pack(fill="x", padx=10, pady=15)

        self.interp_result = ctk.CTkLabel(interp_tab, text="")
        self.interp_result.pack(pady=5)

    def _browse(self, var):
        path = filedialog.askopenfilename(filetypes=[("Images", "*.png *.jpg *.jpeg *.gif")])
        if path:
            var.set(path)

    def animate_text(self):
        if not self.require_client():
            return
        ref = self.ref_path.get()
        if not ref:
            messagebox.showwarning("Input Required", "Please select a reference image.")
            return
        action = self.anim_action.get().strip()
        desc = self.anim_desc.get().strip()
        if not action:
            messagebox.showwarning("Input Required", "Please enter an action.")
            return

        w = int(self.w_entry.get() or 64)
        h = int(self.h_entry.get() or 64)
        use_pro = self.pro_var.get()

        self.text_anim_btn.configure(state="disabled", text="Animating...")
        self.app.status_bar.set_status("Animating...")

        def do_animate():
            ref_img = image_to_base64(ref)
            if use_pro:
                result = self.client.animate_with_text_v2(ref_img, action, w, h, description=desc)
            else:
                result = self.client.animate_with_text(ref_img, desc, action)
            saved = self.handle_job_and_save(result, "anim")
            return saved

        def on_done(saved, err):
            self.text_anim_btn.configure(state="normal", text="Animate")
            if err:
                messagebox.showerror("Error", str(err))
                self.app.status_bar.set_status("Animation failed")
                return
            self.text_result.configure(text=f"Saved {len(saved)} frame(s)")
            self.app.status_bar.set_status("Ready")

        self.run_async(do_animate, on_done)

    def interpolate(self):
        if not self.require_client():
            return
        start = self.start_path.get()
        end = self.end_path.get()
        action = self.interp_action.get().strip()
        if not start or not end or not action:
            messagebox.showwarning("Input Required", "Please fill all fields.")
            return

        self.interp_btn.configure(state="disabled", text="Interpolating...")

        def do_interp():
            start_img = image_to_base64(start)
            end_img = image_to_base64(end)
            result = self.client.interpolate(start_img, end_img, action)
            saved = self.handle_job_and_save(result, "interp")
            return saved

        def on_done(saved, err):
            self.interp_btn.configure(state="normal", text="Interpolate")
            if err:
                messagebox.showerror("Error", str(err))
                return
            self.interp_result.configure(text=f"Saved {len(saved)} frame(s)")

        self.run_async(do_interp, on_done)


# ── Tileset Panel ──

class TilesetPanel(BasePanel):
    def __init__(self, master, app):
        super().__init__(master, app)

        ctk.CTkLabel(self, text="Tilesets", font=("", 24, "bold")).pack(pady=(20, 10), anchor="w", padx=20)

        tabs = ctk.CTkTabview(self)
        tabs.pack(fill="both", expand=True, padx=20, pady=10)

        # ── Top-down ──
        td_tab = tabs.add("Top-Down")

        ctk.CTkLabel(td_tab, text="Lower Terrain:").pack(anchor="w", padx=10, pady=(10, 0))
        self.td_lower = ctk.CTkEntry(td_tab, placeholder_text="ocean, grass, sand...")
        self.td_lower.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(td_tab, text="Upper Terrain:").pack(anchor="w", padx=10, pady=(10, 0))
        self.td_upper = ctk.CTkEntry(td_tab, placeholder_text="sand, stone, dirt...")
        self.td_upper.pack(fill="x", padx=10, pady=5)

        row = ctk.CTkFrame(td_tab)
        row.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(row, text="Tile Size:").pack(side="left")
        self.td_size = ctk.CTkOptionMenu(row, values=["16", "32"])
        self.td_size.pack(side="left", padx=10)
        ctk.CTkLabel(row, text="View:").pack(side="left", padx=(20, 0))
        self.td_view = ctk.CTkOptionMenu(row, values=["low top-down", "high top-down"])
        self.td_view.pack(side="left", padx=10)

        self.td_btn = ctk.CTkButton(td_tab, text="Create Tileset", command=self.create_topdown, height=40)
        self.td_btn.pack(fill="x", padx=10, pady=15)
        self.td_result = ctk.CTkLabel(td_tab, text="")
        self.td_result.pack(pady=5)

        # ── Sidescroller ──
        ss_tab = tabs.add("Sidescroller")

        ctk.CTkLabel(ss_tab, text="Description:").pack(anchor="w", padx=10, pady=(10, 0))
        self.ss_desc = ctk.CTkEntry(ss_tab, placeholder_text="stone bricks")
        self.ss_desc.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(ss_tab, text="Transition:").pack(anchor="w", padx=10, pady=(10, 0))
        self.ss_trans = ctk.CTkEntry(ss_tab, placeholder_text="moss (optional)")
        self.ss_trans.pack(fill="x", padx=10, pady=5)

        self.ss_btn = ctk.CTkButton(ss_tab, text="Create Sidescroller", command=self.create_sidescroller, height=40)
        self.ss_btn.pack(fill="x", padx=10, pady=15)
        self.ss_result = ctk.CTkLabel(ss_tab, text="")
        self.ss_result.pack(pady=5)

        # ── Isometric ──
        iso_tab = tabs.add("Isometric")

        ctk.CTkLabel(iso_tab, text="Description:").pack(anchor="w", padx=10, pady=(10, 0))
        self.iso_desc = ctk.CTkEntry(iso_tab, placeholder_text="grass field")
        self.iso_desc.pack(fill="x", padx=10, pady=5)

        row = ctk.CTkFrame(iso_tab)
        row.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(row, text="Shape:").pack(side="left")
        self.iso_shape = ctk.CTkOptionMenu(row, values=["thin tile", "thick tile", "block"])
        self.iso_shape.set("block")
        self.iso_shape.pack(side="left", padx=10)

        self.iso_btn = ctk.CTkButton(iso_tab, text="Create Isometric", command=self.create_isometric, height=40)
        self.iso_btn.pack(fill="x", padx=10, pady=15)
        self.iso_result = ctk.CTkLabel(iso_tab, text="")
        self.iso_result.pack(pady=5)

        # ── Pro Tiles ──
        pro_tab = tabs.add("Pro Tiles")

        ctk.CTkLabel(pro_tab, text="Description:").pack(anchor="w", padx=10, pady=(10, 0))
        self.pro_desc = ctk.CTkEntry(pro_tab, placeholder_text="1). grass 2). stone 3). lava")
        self.pro_desc.pack(fill="x", padx=10, pady=5)

        row = ctk.CTkFrame(pro_tab)
        row.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(row, text="Type:").pack(side="left")
        self.pro_type = ctk.CTkOptionMenu(row, values=["hex", "hex_pointy", "isometric", "octagon", "square_topdown"])
        self.pro_type.set("isometric")
        self.pro_type.pack(side="left", padx=10)
        ctk.CTkLabel(row, text="N Tiles:").pack(side="left", padx=(20, 0))
        self.pro_n = ctk.CTkEntry(row, width=60, placeholder_text="3")
        self.pro_n.pack(side="left", padx=5)

        self.pro_btn = ctk.CTkButton(pro_tab, text="Create Pro Tiles", command=self.create_pro_tiles, height=40)
        self.pro_btn.pack(fill="x", padx=10, pady=15)
        self.pro_result = ctk.CTkLabel(pro_tab, text="")
        self.pro_result.pack(pady=5)

    def _generate(self, btn, label, fn):
        if not self.require_client():
            return
        btn.configure(state="disabled", text="Creating...")
        self.app.status_bar.set_status("Creating tileset...")

        def on_done(saved, err):
            btn.configure(state="normal", text=btn._text)
            if err:
                messagebox.showerror("Error", str(err))
                self.app.status_bar.set_status("Failed")
                return
            label.configure(text=f"Saved {len(saved)} tile(s)")
            self.app.status_bar.set_status("Ready")

        self.run_async(fn, on_done)

    def create_topdown(self):
        lower = self.td_lower.get().strip()
        upper = self.td_upper.get().strip()
        if not lower or not upper:
            messagebox.showwarning("Input Required", "Please fill lower and upper terrain.")
            return
        size = int(self.td_size.get())
        view = self.td_view.get()

        def fn():
            result = self.client.create_tileset(lower, upper, tile_size={"width": size, "height": size}, view=view)
            return self.handle_job_and_save(result, "tileset")

        self._generate(self.td_btn, self.td_result, fn)

    def create_sidescroller(self):
        desc = self.ss_desc.get().strip()
        if not desc:
            messagebox.showwarning("Input Required", "Please enter a description.")
            return
        kwargs = {}
        trans = self.ss_trans.get().strip()
        if trans:
            kwargs["transition_description"] = trans

        def fn():
            result = self.client.create_tileset_sidescroller(desc, **kwargs)
            return self.handle_job_and_save(result, "sidescroller")

        self._generate(self.ss_btn, self.ss_result, fn)

    def create_isometric(self):
        desc = self.iso_desc.get().strip()
        if not desc:
            messagebox.showwarning("Input Required", "Please enter a description.")
            return

        def fn():
            result = self.client.create_isometric_tile(desc, isometric_tile_shape=self.iso_shape.get())
            return self.handle_job_and_save(result, "iso")

        self._generate(self.iso_btn, self.iso_result, fn)

    def create_pro_tiles(self):
        desc = self.pro_desc.get().strip()
        if not desc:
            messagebox.showwarning("Input Required", "Please enter a description.")
            return
        kwargs = {"tile_type": self.pro_type.get()}
        n = self.pro_n.get().strip()
        if n:
            kwargs["n_tiles"] = int(n)

        def fn():
            result = self.client.create_tiles_pro(desc, **kwargs)
            return self.handle_job_and_save(result, "tiles_pro")

        self._generate(self.pro_btn, self.pro_result, fn)


# ── Edit Panel ──

class EditPanel(BasePanel):
    def __init__(self, master, app):
        super().__init__(master, app)

        ctk.CTkLabel(self, text="Edit & Inpaint", font=("", 24, "bold")).pack(pady=(20, 10), anchor="w", padx=20)

        tabs = ctk.CTkTabview(self)
        tabs.pack(fill="both", expand=True, padx=20, pady=10)

        # ── Edit ──
        edit_tab = tabs.add("Edit Image")

        ctk.CTkLabel(edit_tab, text="Image:").pack(anchor="w", padx=10, pady=(10, 0))
        row = ctk.CTkFrame(edit_tab)
        row.pack(fill="x", padx=10, pady=5)
        self.edit_path = ctk.StringVar()
        ctk.CTkEntry(row, textvariable=self.edit_path).pack(side="left", fill="x", expand=True, padx=(0, 5))
        ctk.CTkButton(row, text="Browse", width=80, command=lambda: self._browse(self.edit_path)).pack(side="right")

        ctk.CTkLabel(edit_tab, text="Edit Description:").pack(anchor="w", padx=10, pady=(10, 0))
        self.edit_desc = ctk.CTkEntry(edit_tab, placeholder_text="add a red cape")
        self.edit_desc.pack(fill="x", padx=10, pady=5)

        self.edit_btn = ctk.CTkButton(edit_tab, text="Edit Image", command=self.edit_image, height=40)
        self.edit_btn.pack(fill="x", padx=10, pady=15)

        self.edit_preview = ImagePreview(edit_tab, 300, 300)
        self.edit_preview.pack(pady=5)

        # ── Inpaint ──
        inpaint_tab = tabs.add("Inpaint")

        ctk.CTkLabel(inpaint_tab, text="Image:").pack(anchor="w", padx=10, pady=(10, 0))
        row = ctk.CTkFrame(inpaint_tab)
        row.pack(fill="x", padx=10, pady=5)
        self.inp_path = ctk.StringVar()
        ctk.CTkEntry(row, textvariable=self.inp_path).pack(side="left", fill="x", expand=True, padx=(0, 5))
        ctk.CTkButton(row, text="Browse", width=80, command=lambda: self._browse(self.inp_path)).pack(side="right")

        ctk.CTkLabel(inpaint_tab, text="Mask:").pack(anchor="w", padx=10, pady=(10, 0))
        row = ctk.CTkFrame(inpaint_tab)
        row.pack(fill="x", padx=10, pady=5)
        self.mask_path = ctk.StringVar()
        ctk.CTkEntry(row, textvariable=self.mask_path).pack(side="left", fill="x", expand=True, padx=(0, 5))
        ctk.CTkButton(row, text="Browse", width=80, command=lambda: self._browse(self.mask_path)).pack(side="right")

        ctk.CTkLabel(inpaint_tab, text="Description:").pack(anchor="w", padx=10, pady=(10, 0))
        self.inp_desc = ctk.CTkEntry(inpaint_tab, placeholder_text="stone wall")
        self.inp_desc.pack(fill="x", padx=10, pady=5)

        self.inp_pro_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(inpaint_tab, text="Pro (v3)", variable=self.inp_pro_var).pack(anchor="w", padx=10, pady=5)

        self.inp_btn = ctk.CTkButton(inpaint_tab, text="Inpaint", command=self.do_inpaint, height=40)
        self.inp_btn.pack(fill="x", padx=10, pady=15)

        self.inp_preview = ImagePreview(inpaint_tab, 300, 300)
        self.inp_preview.pack(pady=5)

        # ── Resize & Convert ──
        ops_tab = tabs.add("Resize / Convert")

        ctk.CTkLabel(ops_tab, text="Image:").pack(anchor="w", padx=10, pady=(10, 0))
        row = ctk.CTkFrame(ops_tab)
        row.pack(fill="x", padx=10, pady=5)
        self.ops_path = ctk.StringVar()
        ctk.CTkEntry(row, textvariable=self.ops_path).pack(side="left", fill="x", expand=True, padx=(0, 5))
        ctk.CTkButton(row, text="Browse", width=80, command=lambda: self._browse(self.ops_path)).pack(side="right")

        self.ops_mode = ctk.CTkSegmentedButton(ops_tab, values=["Resize", "To Pixel Art"])
        self.ops_mode.set("Resize")
        self.ops_mode.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(ops_tab, text="Description (for resize):").pack(anchor="w", padx=10)
        self.ops_desc = ctk.CTkEntry(ops_tab, placeholder_text="knight character")
        self.ops_desc.pack(fill="x", padx=10, pady=5)

        row = ctk.CTkFrame(ops_tab)
        row.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(row, text="Target W:").pack(side="left")
        self.ops_tw = ctk.CTkEntry(row, width=60)
        self.ops_tw.pack(side="left", padx=5)
        self.ops_tw.insert(0, "128")
        ctk.CTkLabel(row, text="Target H:").pack(side="left", padx=(10, 0))
        self.ops_th = ctk.CTkEntry(row, width=60)
        self.ops_th.pack(side="left", padx=5)
        self.ops_th.insert(0, "128")

        self.ops_btn = ctk.CTkButton(ops_tab, text="Process", command=self.process_ops, height=40)
        self.ops_btn.pack(fill="x", padx=10, pady=15)

        self.ops_result = ctk.CTkLabel(ops_tab, text="")
        self.ops_result.pack(pady=5)

    def _browse(self, var):
        path = filedialog.askopenfilename(filetypes=[("Images", "*.png *.jpg *.jpeg *.gif")])
        if path:
            var.set(path)

    def edit_image(self):
        if not self.require_client():
            return
        path = self.edit_path.get()
        desc = self.edit_desc.get().strip()
        if not path or not desc:
            messagebox.showwarning("Input Required", "Please provide image and description.")
            return

        self.edit_btn.configure(state="disabled", text="Editing...")

        def do_edit():
            img = image_to_base64(path)
            size = get_image_size(path)
            result = self.client.edit_image(img, desc, size["width"], size["height"])
            saved = self.handle_job_and_save(result, "edit")
            return saved

        def on_done(saved, err):
            self.edit_btn.configure(state="normal", text="Edit Image")
            if err:
                messagebox.showerror("Error", str(err))
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
            messagebox.showwarning("Input Required", "Please fill all fields.")
            return

        self.inp_btn.configure(state="disabled", text="Inpainting...")

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
            self.inp_btn.configure(state="normal", text="Inpaint")
            if err:
                messagebox.showerror("Error", str(err))
                return
            if saved:
                self.inp_preview.show_file(saved[0])

        self.run_async(do_inp, on_done)

    def process_ops(self):
        if not self.require_client():
            return
        path = self.ops_path.get()
        if not path:
            messagebox.showwarning("Input Required", "Please select an image.")
            return

        tw = int(self.ops_tw.get() or 128)
        th = int(self.ops_th.get() or 128)
        mode = self.ops_mode.get()

        self.ops_btn.configure(state="disabled", text="Processing...")

        def do_ops():
            img = image_to_base64(path)
            size = get_image_size(path)
            if mode == "Resize":
                desc = self.ops_desc.get().strip() or "pixel art"
                result = self.client.resize(desc, img, size["width"], size["height"], tw, th)
            else:
                result = self.client.image_to_pixelart(img, size["width"], size["height"], tw, th)
            saved = self.handle_job_and_save(result, mode.lower().replace(" ", "_"))
            return saved

        def on_done(saved, err):
            self.ops_btn.configure(state="normal", text="Process")
            if err:
                messagebox.showerror("Error", str(err))
                return
            self.ops_result.configure(text=f"Saved {len(saved)} image(s)")

        self.run_async(do_ops, on_done)


# ── Rotate Panel ──

class RotatePanel(BasePanel):
    def __init__(self, master, app):
        super().__init__(master, app)

        ctk.CTkLabel(self, text="Rotation", font=("", 24, "bold")).pack(pady=(20, 10), anchor="w", padx=20)

        tabs = ctk.CTkTabview(self)
        tabs.pack(fill="both", expand=True, padx=20, pady=10)

        # ── 8 Rotations ──
        rot8_tab = tabs.add("8 Rotations")

        ctk.CTkLabel(rot8_tab, text="Reference Image:").pack(anchor="w", padx=10, pady=(10, 0))
        row = ctk.CTkFrame(rot8_tab)
        row.pack(fill="x", padx=10, pady=5)
        self.rot8_path = ctk.StringVar()
        ctk.CTkEntry(row, textvariable=self.rot8_path).pack(side="left", fill="x", expand=True, padx=(0, 5))
        ctk.CTkButton(row, text="Browse", width=80, command=lambda: self._browse(self.rot8_path)).pack(side="right")

        row2 = ctk.CTkFrame(rot8_tab)
        row2.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(row2, text="Width:").pack(side="left")
        self.rot8_w = ctk.CTkEntry(row2, width=60)
        self.rot8_w.pack(side="left", padx=5)
        self.rot8_w.insert(0, "64")
        ctk.CTkLabel(row2, text="Height:").pack(side="left", padx=(10, 0))
        self.rot8_h = ctk.CTkEntry(row2, width=60)
        self.rot8_h.pack(side="left", padx=5)
        self.rot8_h.insert(0, "64")
        ctk.CTkLabel(row2, text="View:").pack(side="left", padx=(20, 0))
        self.rot8_view = ctk.CTkOptionMenu(row2, values=["low top-down", "high top-down", "side"])
        self.rot8_view.pack(side="left", padx=10)

        self.rot8_nobg = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(rot8_tab, text="No Background", variable=self.rot8_nobg).pack(anchor="w", padx=10, pady=5)

        self.rot8_btn = ctk.CTkButton(rot8_tab, text="Generate 8 Rotations", command=self.gen_8rot, height=40)
        self.rot8_btn.pack(fill="x", padx=10, pady=15)
        self.rot8_result = ctk.CTkLabel(rot8_tab, text="")
        self.rot8_result.pack(pady=5)

        # ── Single Rotation ──
        single_tab = tabs.add("Single Rotation")

        ctk.CTkLabel(single_tab, text="Image:").pack(anchor="w", padx=10, pady=(10, 0))
        row = ctk.CTkFrame(single_tab)
        row.pack(fill="x", padx=10, pady=5)
        self.single_path = ctk.StringVar()
        ctk.CTkEntry(row, textvariable=self.single_path).pack(side="left", fill="x", expand=True, padx=(0, 5))
        ctk.CTkButton(row, text="Browse", width=80, command=lambda: self._browse(self.single_path)).pack(side="right")

        ctk.CTkLabel(single_tab, text="Target Direction:").pack(anchor="w", padx=10, pady=(10, 0))
        self.single_dir = ctk.CTkOptionMenu(single_tab, values=[
            "north", "north-east", "east", "south-east",
            "south", "south-west", "west", "north-west",
        ])
        self.single_dir.pack(fill="x", padx=10, pady=5)

        self.single_btn = ctk.CTkButton(single_tab, text="Rotate", command=self.rotate_single, height=40)
        self.single_btn.pack(fill="x", padx=10, pady=15)

        self.single_preview = ImagePreview(single_tab, 300, 300)
        self.single_preview.pack(pady=5)

    def _browse(self, var):
        path = filedialog.askopenfilename(filetypes=[("Images", "*.png *.jpg *.jpeg *.gif")])
        if path:
            var.set(path)

    def gen_8rot(self):
        if not self.require_client():
            return
        ref = self.rot8_path.get()
        if not ref:
            messagebox.showwarning("Input Required", "Please select a reference image.")
            return

        w = int(self.rot8_w.get() or 64)
        h = int(self.rot8_h.get() or 64)

        self.rot8_btn.configure(state="disabled", text="Generating...")

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
            self.rot8_btn.configure(state="normal", text="Generate 8 Rotations")
            if err:
                messagebox.showerror("Error", str(err))
                return
            self.rot8_result.configure(text=f"Saved {len(saved)} rotation(s)")

        self.run_async(do_rot, on_done)

    def rotate_single(self):
        if not self.require_client():
            return
        path = self.single_path.get()
        if not path:
            messagebox.showwarning("Input Required", "Please select an image.")
            return

        self.single_btn.configure(state="disabled", text="Rotating...")

        def do_rot():
            img = image_to_base64(path)
            size = get_image_size(path)
            result = self.client.rotate(img, size["width"], size["height"], to_direction=self.single_dir.get())
            saved = self.handle_job_and_save(result, "rotated")
            return saved

        def on_done(saved, err):
            self.single_btn.configure(state="normal", text="Rotate")
            if err:
                messagebox.showerror("Error", str(err))
                return
            if saved:
                self.single_preview.show_file(saved[0])

        self.run_async(do_rot, on_done)


# ── Settings Panel ──

class SettingsPanel(BasePanel):
    def __init__(self, master, app):
        super().__init__(master, app)

        ctk.CTkLabel(self, text="Settings", font=("", 24, "bold")).pack(pady=(20, 10), anchor="w", padx=20)

        form = ctk.CTkFrame(self)
        form.pack(fill="x", padx=20, pady=10)

        # API Key
        ctk.CTkLabel(form, text="API Key:").pack(anchor="w", padx=10, pady=(15, 0))
        key_row = ctk.CTkFrame(form)
        key_row.pack(fill="x", padx=10, pady=5)
        self.key_entry = ctk.CTkEntry(key_row, show="*", placeholder_text="Enter your PixelLab API key")
        self.key_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))

        self.show_key_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(key_row, text="Show", variable=self.show_key_var, command=self.toggle_key_visibility, width=60).pack(side="right")

        # Load existing key
        existing_key = os.environ.get("PIXELLAB_API_KEY", "")
        if existing_key:
            self.key_entry.insert(0, existing_key)

        # Output dir
        ctk.CTkLabel(form, text="Output Directory:").pack(anchor="w", padx=10, pady=(15, 0))
        out_row = ctk.CTkFrame(form)
        out_row.pack(fill="x", padx=10, pady=5)
        self.out_entry = ctk.CTkEntry(out_row)
        self.out_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.out_entry.insert(0, app.output_dir)
        ctk.CTkButton(out_row, text="Browse", width=80, command=self.browse_output).pack(side="right")

        # Appearance
        ctk.CTkLabel(form, text="Appearance:").pack(anchor="w", padx=10, pady=(15, 0))
        self.appearance_var = ctk.StringVar(value="dark")
        ctk.CTkOptionMenu(form, values=["dark", "light", "system"], variable=self.appearance_var,
                          command=lambda v: ctk.set_appearance_mode(v)).pack(anchor="w", padx=10, pady=5)

        # Save
        ctk.CTkButton(form, text="Save & Connect", command=self.save_settings, height=40,
                      font=("", 14, "bold")).pack(fill="x", padx=10, pady=20)

        # Info
        info = ctk.CTkFrame(self)
        info.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(info, text="Get your API key at: https://pixellab.ai/account",
                     text_color="gray").pack(padx=10, pady=10)
        ctk.CTkLabel(info, text="API Docs: https://api.pixellab.ai/v2/docs",
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
            messagebox.showwarning("API Key Required", "Please enter your API key.")
            return

        self.app.output_dir = out_dir or DEFAULT_OUTPUT_DIR

        # Save to .env
        env_path = Path(".env")
        env_path.write_text(f"PIXELLAB_API_KEY={key}\n")
        os.environ["PIXELLAB_API_KEY"] = key

        # Connect
        self.app.client = PixelLabClient(key)
        self.app.status_bar.set_status("Connected")
        messagebox.showinfo("Saved", "Settings saved and connected to PixelLab API.")


# ── Main Application ──

class PixelLabApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("PixelLab Tool")
        self.geometry("1100x750")
        self.minsize(900, 600)

        self.client: PixelLabClient | None = None
        self.output_dir = DEFAULT_OUTPUT_DIR

        # Try to connect with existing key
        api_key = os.environ.get("PIXELLAB_API_KEY")
        if api_key:
            self.client = PixelLabClient(api_key)

        self._build_layout()

        # Show dashboard or settings
        if self.client:
            self.show_panel("Dashboard")
        else:
            self.show_panel("Settings")

    def _build_layout(self):
        # Grid layout
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # Sidebar
        self.sidebar = ctk.CTkFrame(self, width=180, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsw")
        self.sidebar.grid_propagate(False)

        # Logo
        logo_label = ctk.CTkLabel(self.sidebar, text="PixelLab", font=("", 22, "bold"))
        logo_label.pack(pady=(20, 5))
        ctk.CTkLabel(self.sidebar, text="Pixel Art Tool", font=("", 12), text_color="gray").pack(pady=(0, 20))

        # Nav buttons
        self.nav_buttons: dict[str, ctk.CTkButton] = {}
        for name, shortcut in SIDEBAR_ITEMS:
            btn = ctk.CTkButton(
                self.sidebar,
                text=f"  {name}",
                anchor="w",
                height=36,
                corner_radius=8,
                fg_color="transparent",
                text_color=("gray10", "gray90"),
                hover_color=("gray70", "gray30"),
                command=lambda n=name: self.show_panel(n),
            )
            btn.pack(fill="x", padx=10, pady=2)
            self.nav_buttons[name] = btn

        # Content area
        self.content = ctk.CTkFrame(self, corner_radius=0)
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.grid_rowconfigure(0, weight=1)
        self.content.grid_columnconfigure(0, weight=1)

        # Status bar
        self.status_bar = StatusBar(self)
        self.status_bar.grid(row=1, column=0, columnspan=2, sticky="ew")
        if self.client:
            self.status_bar.set_status("Connected")
        else:
            self.status_bar.set_status("Not connected - set API key in Settings")

        # Panels (lazy init)
        self.panels: dict[str, BasePanel] = {}
        self.current_panel: str | None = None

    def _get_panel(self, name: str) -> BasePanel:
        if name not in self.panels:
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
            cls = panel_map[name]
            panel = cls(self.content, self)
            self.panels[name] = panel
        return self.panels[name]

    def show_panel(self, name: str):
        # Hide current
        if self.current_panel and self.current_panel in self.panels:
            self.panels[self.current_panel].grid_forget()

        # Update nav button styles
        for btn_name, btn in self.nav_buttons.items():
            if btn_name == name:
                btn.configure(fg_color=("gray75", "gray25"))
            else:
                btn.configure(fg_color="transparent")

        # Show panel
        panel = self._get_panel(name)
        panel.grid(row=0, column=0, sticky="nsew")
        self.current_panel = name


def main():
    app = PixelLabApp()
    app.mainloop()


if __name__ == "__main__":
    main()
