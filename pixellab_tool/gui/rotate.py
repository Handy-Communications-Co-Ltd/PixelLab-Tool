"""Rotate panel."""

from tkinter import filedialog, messagebox

import customtkinter as ctk

from ..utils import image_to_base64, get_image_size
from .common import BasePanel, ImagePreview


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

        ctk.CTkLabel(rot8_tab, text="방법:").pack(anchor="w", padx=10, pady=(5, 0))
        self.rot8_method = ctk.CTkOptionMenu(rot8_tab, values=["rotate_character", "create_with_style", "create_from_concept"])
        self.rot8_method.pack(fill="x", padx=10, pady=5)

        self.rot8_desc = ctk.CTkEntry(rot8_tab, placeholder_text="설명 (선택사항)")
        self.rot8_desc.pack(fill="x", padx=10, pady=5)

        self.rot8_style_desc = ctk.CTkEntry(rot8_tab, placeholder_text="스타일 설명 (선택사항)")
        self.rot8_style_desc.pack(fill="x", padx=10, pady=5)

        row3 = ctk.CTkFrame(rot8_tab)
        row3.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(row3, text="시드:").pack(side="left")
        self.rot8_seed = ctk.CTkEntry(row3, width=80, placeholder_text="랜덤")
        self.rot8_seed.pack(side="left", padx=5)

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

        single_row = ctk.CTkFrame(single_tab)
        single_row.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(single_row, text="시드:").pack(side="left")
        self.single_seed = ctk.CTkEntry(single_row, width=80, placeholder_text="랜덤")
        self.single_seed.pack(side="left", padx=5)
        ctk.CTkLabel(single_row, text="이미지 가이던스:").pack(side="left", padx=(15, 0))
        self.single_guidance = ctk.CTkEntry(single_row, width=60, placeholder_text="3.0")
        self.single_guidance.pack(side="left", padx=5)

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
                "reference_image": {"image": ref_img, "width": ref_size["width"], "height": ref_size["height"]},
                "view": self.rot8_view.get(),
            }
            if self.rot8_nobg.get():
                kwargs["no_background"] = True
            method_val = self.rot8_method.get()
            if method_val != "rotate_character":
                kwargs["method"] = method_val
            desc_val = self.rot8_desc.get().strip()
            if desc_val:
                kwargs["description"] = desc_val
            style_desc_val = self.rot8_style_desc.get().strip()
            if style_desc_val:
                kwargs["style_description"] = style_desc_val
            seed_val = self.rot8_seed.get().strip()
            if seed_val:
                kwargs["seed"] = int(seed_val)
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
            kwargs = {}
            seed_val = self.single_seed.get().strip()
            if seed_val:
                kwargs["seed"] = int(seed_val)
            guidance_val = self.single_guidance.get().strip()
            if guidance_val:
                kwargs["image_guidance_scale"] = float(guidance_val)
            result = self.client.rotate(img, size["width"], size["height"], to_direction=self.single_dir.get(), **kwargs)
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
