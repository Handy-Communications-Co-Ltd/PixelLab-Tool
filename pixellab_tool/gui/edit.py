"""Edit panel."""

from tkinter import filedialog, messagebox

import customtkinter as ctk

from ..utils import image_to_base64, get_image_size
from .common import BasePanel, ImagePreview


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

        # Edit extra params
        edit_params_row = ctk.CTkFrame(edit_tab)
        edit_params_row.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(edit_params_row, text="시드:").pack(side="left")
        self.edit_seed = ctk.CTkEntry(edit_params_row, width=80, placeholder_text="랜덤")
        self.edit_seed.pack(side="left", padx=(2, 10))
        ctk.CTkLabel(edit_params_row, text="텍스트 가이던스:").pack(side="left")
        self.edit_text_guidance = ctk.CTkEntry(edit_params_row, width=60, placeholder_text="자동")
        self.edit_text_guidance.pack(side="left", padx=2)

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

        # Shared seed row (used by both v1 and v3)
        inp_seed_row = ctk.CTkFrame(inpaint_tab)
        inp_seed_row.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(inp_seed_row, text="시드:").pack(side="left")
        self.inp_seed = ctk.CTkEntry(inp_seed_row, width=80, placeholder_text="랜덤")
        self.inp_seed.pack(side="left", padx=2)

        # v1-only params
        ctk.CTkLabel(inpaint_tab, text="제외 설명 (v1):").pack(anchor="w", padx=10, pady=(8, 0))
        self.inp_neg_desc = ctk.CTkEntry(inpaint_tab, placeholder_text="제외할 요소...")
        self.inp_neg_desc.pack(fill="x", padx=10, pady=3)

        inp_tg_row = ctk.CTkFrame(inpaint_tab)
        inp_tg_row.pack(fill="x", padx=10, pady=3)
        ctk.CTkLabel(inp_tg_row, text="텍스트 가이던스 (v1):").pack(side="left")
        self.inp_text_guidance = ctk.CTkEntry(inp_tg_row, width=60, placeholder_text="3.0")
        self.inp_text_guidance.pack(side="left", padx=2)

        inp_style_row = ctk.CTkFrame(inpaint_tab)
        inp_style_row.pack(fill="x", padx=10, pady=3)
        ctk.CTkLabel(inp_style_row, text="아웃라인 (v1):").pack(side="left")
        self.inp_outline = ctk.CTkOptionMenu(inp_style_row, values=[
            "없음", "single color black outline", "single color outline",
            "selective outline", "lineless"
        ])
        self.inp_outline.set("없음")
        self.inp_outline.pack(side="left", padx=(2, 10))

        inp_shading_row = ctk.CTkFrame(inpaint_tab)
        inp_shading_row.pack(fill="x", padx=10, pady=3)
        ctk.CTkLabel(inp_shading_row, text="쉐이딩 (v1):").pack(side="left")
        self.inp_shading = ctk.CTkOptionMenu(inp_shading_row, values=[
            "없음", "flat shading", "low shading", "medium shading",
            "high shading", "highly detailed shading"
        ])
        self.inp_shading.set("없음")
        self.inp_shading.pack(side="left", padx=2)

        inp_detail_row = ctk.CTkFrame(inpaint_tab)
        inp_detail_row.pack(fill="x", padx=10, pady=3)
        ctk.CTkLabel(inp_detail_row, text="디테일 (v1):").pack(side="left")
        self.inp_detail = ctk.CTkOptionMenu(inp_detail_row, values=[
            "없음", "low detail", "medium detail", "highly detailed"
        ])
        self.inp_detail.set("없음")
        self.inp_detail.pack(side="left", padx=2)

        # v3-only params
        inp_v3_row = ctk.CTkFrame(inpaint_tab)
        inp_v3_row.pack(fill="x", padx=10, pady=(8, 3))
        self.inp_no_background = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(inp_v3_row, text="배경 제거 (v3)", variable=self.inp_no_background).pack(side="left", padx=(0, 15))
        self.inp_crop_to_mask = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(inp_v3_row, text="마스크에 맞게 자르기 (v3)", variable=self.inp_crop_to_mask).pack(side="left")

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

        ops_seed_row = ctk.CTkFrame(ops_tab)
        ops_seed_row.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(ops_seed_row, text="시드:").pack(side="left")
        self.ops_seed = ctk.CTkEntry(ops_seed_row, width=80, placeholder_text="랜덤")
        self.ops_seed.pack(side="left", padx=2)

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
            kwargs = {}
            seed_val = self.edit_seed.get().strip()
            if seed_val:
                try:
                    kwargs["seed"] = int(seed_val)
                except ValueError:
                    pass
            tg_val = self.edit_text_guidance.get().strip()
            if tg_val:
                try:
                    kwargs["text_guidance_scale"] = float(tg_val)
                except ValueError:
                    pass
            result = self.client.edit_image(img, desc, size["width"], size["height"], **kwargs)
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

            kwargs = {}
            seed_val = self.inp_seed.get().strip()
            if seed_val:
                try:
                    kwargs["seed"] = int(seed_val)
                except ValueError:
                    pass

            if self.inp_pro_var.get():
                # v3 mode
                if self.inp_no_background.get():
                    kwargs["no_background"] = True
                if self.inp_crop_to_mask.get():
                    kwargs["crop_to_mask"] = True
                inp_img = {"image": img, "size": {"width": w, "height": h}}
                mask_img = {"image": mask, "size": {"width": w, "height": h}}
                result = self.client.inpaint_v3(desc, inp_img, mask_img, **kwargs)
            else:
                # v1 mode
                neg_desc = self.inp_neg_desc.get().strip()
                if neg_desc:
                    kwargs["negative_description"] = neg_desc
                tg_val = self.inp_text_guidance.get().strip()
                if tg_val:
                    try:
                        kwargs["text_guidance_scale"] = float(tg_val)
                    except ValueError:
                        pass
                outline_val = self.inp_outline.get()
                if outline_val != "없음":
                    kwargs["outline"] = outline_val
                shading_val = self.inp_shading.get()
                if shading_val != "없음":
                    kwargs["shading"] = shading_val
                detail_val = self.inp_detail.get()
                if detail_val != "없음":
                    kwargs["detail"] = detail_val
                result = self.client.inpaint(desc, img, mask, w, h, **kwargs)
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
            kwargs = {}
            seed_val = self.ops_seed.get().strip()
            if seed_val:
                try:
                    kwargs["seed"] = int(seed_val)
                except ValueError:
                    pass
            if mode == "리사이즈":
                desc = self.ops_desc.get().strip() or "pixel art"
                result = self.client.resize(desc, img, size["width"], size["height"], tw, th, **kwargs)
            else:
                result = self.client.image_to_pixelart(img, size["width"], size["height"], tw, th, **kwargs)
            saved = self.handle_job_and_save(result, mode.replace(" ", "_"))
            return saved

        def on_done(saved, err):
            self.ops_btn.configure(state="normal", text="처리")
            if err:
                messagebox.showerror("오류", str(err))
                return
            self.ops_result.configure(text=f"{len(saved)}개 이미지 저장 완료")

        self.run_async(do_ops, on_done)
