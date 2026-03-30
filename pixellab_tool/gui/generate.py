"""Generate panel."""

import os
from tkinter import filedialog, messagebox

import customtkinter as ctk

from ..utils import image_to_base64, get_image_size
from .common import BasePanel, ImagePreview


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

        # Style reference (up to 4 images)
        self.style_frame = ctk.CTkFrame(form)
        self.style_frame.pack(fill="x", padx=10, pady=5)
        style_header = ctk.CTkFrame(self.style_frame, fg_color="transparent")
        style_header.pack(fill="x")
        ctk.CTkLabel(style_header, text="스타일 참조 이미지 (최대 4개):").pack(side="left", anchor="w")
        ctk.CTkButton(style_header, text="+ 추가", width=60, command=self.add_style_image).pack(side="right")
        self.style_paths = []
        self.style_list_frame = ctk.CTkFrame(self.style_frame, fg_color="transparent")
        self.style_list_frame.pack(fill="x")

        # Style description (for Style mode)
        self.style_desc_frame = ctk.CTkFrame(form, fg_color="transparent")
        self.style_desc_frame.pack(fill="x", padx=10, pady=(0, 5))
        ctk.CTkLabel(self.style_desc_frame, text="스타일 설명:").pack(anchor="w")
        self.style_desc_entry = ctk.CTkEntry(self.style_desc_frame, placeholder_text="스타일 설명 (선택사항)")
        self.style_desc_entry.pack(fill="x")

        # Advanced options for PixFlux/BitForge
        self.advanced_frame = ctk.CTkFrame(form)
        self.advanced_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(self.advanced_frame, text="고급 옵션 (PixFlux/BitForge):", font=("", 12, "bold")).pack(anchor="w", padx=10, pady=(8, 4))

        # negative_description
        neg_row = ctk.CTkFrame(self.advanced_frame, fg_color="transparent")
        neg_row.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(neg_row, text="부정 설명:").pack(side="left")
        self.negative_desc_entry = ctk.CTkEntry(neg_row, placeholder_text="제외할 요소...")
        self.negative_desc_entry.pack(side="left", fill="x", expand=True, padx=(8, 0))

        # text_guidance_scale
        tgs_row = ctk.CTkFrame(self.advanced_frame, fg_color="transparent")
        tgs_row.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(tgs_row, text="텍스트 가이던스 스케일:").pack(side="left")
        self.text_guidance_scale_entry = ctk.CTkEntry(tgs_row, width=60, placeholder_text="8.0")
        self.text_guidance_scale_entry.pack(side="left", padx=(8, 0))

        # outline
        outline_row = ctk.CTkFrame(self.advanced_frame, fg_color="transparent")
        outline_row.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(outline_row, text="외곽선:").pack(side="left")
        self.outline_var = ctk.StringVar(value="없음")
        ctk.CTkOptionMenu(outline_row, values=["없음", "single color black outline", "single color outline", "selective outline", "lineless"],
                          variable=self.outline_var).pack(side="left", padx=(8, 0))

        # shading
        shading_row = ctk.CTkFrame(self.advanced_frame, fg_color="transparent")
        shading_row.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(shading_row, text="음영:").pack(side="left")
        self.shading_var = ctk.StringVar(value="없음")
        ctk.CTkOptionMenu(shading_row, values=["없음", "flat shading", "low shading", "medium shading", "high shading", "highly detailed shading"],
                          variable=self.shading_var).pack(side="left", padx=(8, 0))

        # detail
        detail_row = ctk.CTkFrame(self.advanced_frame, fg_color="transparent")
        detail_row.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(detail_row, text="디테일:").pack(side="left")
        self.detail_var = ctk.StringVar(value="없음")
        ctk.CTkOptionMenu(detail_row, values=["없음", "low detail", "medium detail", "highly detailed"],
                          variable=self.detail_var).pack(side="left", padx=(8, 0))

        # view
        view_row = ctk.CTkFrame(self.advanced_frame, fg_color="transparent")
        view_row.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(view_row, text="뷰:").pack(side="left")
        self.view_var = ctk.StringVar(value="없음")
        ctk.CTkOptionMenu(view_row, values=["없음", "side", "low top-down", "high top-down"],
                          variable=self.view_var).pack(side="left", padx=(8, 0))

        # direction
        direction_row = ctk.CTkFrame(self.advanced_frame, fg_color="transparent")
        direction_row.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(direction_row, text="방향:").pack(side="left")
        self.direction_var = ctk.StringVar(value="없음")
        ctk.CTkOptionMenu(direction_row, values=["없음", "south", "south-east", "east", "north-east", "north", "north-west", "west", "south-west"],
                          variable=self.direction_var).pack(side="left", padx=(8, 0))

        # isometric
        iso_row = ctk.CTkFrame(self.advanced_frame, fg_color="transparent")
        iso_row.pack(fill="x", padx=10, pady=(2, 8))
        self.isometric_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(iso_row, text="아이소메트릭", variable=self.isometric_var).pack(side="left")

        self.gen_btn = ctk.CTkButton(form, text="생성", command=self.generate, height=40, font=("", 14, "bold"))
        self.gen_btn.pack(pady=15, padx=10, fill="x")

        self.preview = ImagePreview(self, 400, 400)
        self.preview.pack(pady=10)

        self.result_label = ctk.CTkLabel(self, text="")
        self.result_label.pack(pady=5)

    def add_style_image(self):
        if len(self.style_paths) >= 4:
            messagebox.showwarning("제한", "스타일 이미지는 최대 4개까지 추가할 수 있습니다.")
            return
        path = filedialog.askopenfilename(filetypes=[("이미지", "*.png *.jpg *.jpeg *.gif")])
        if path:
            self.style_paths.append(path)
            self._refresh_style_list()

    def _remove_style_image(self, index):
        if 0 <= index < len(self.style_paths):
            self.style_paths.pop(index)
            self._refresh_style_list()

    def _refresh_style_list(self):
        for w in self.style_list_frame.winfo_children():
            w.destroy()
        for i, p in enumerate(self.style_paths):
            row = ctk.CTkFrame(self.style_list_frame, fg_color="transparent")
            row.pack(fill="x", pady=1)
            name = os.path.basename(p)
            ctk.CTkLabel(row, text=f"{i+1}. {name}", anchor="w").pack(side="left", fill="x", expand=True)
            ctk.CTkButton(row, text="\u2715", width=30, fg_color="red", hover_color="darkred",
                          command=lambda idx=i: self._remove_style_image(idx)).pack(side="right")

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

        # Collect style_description for Style mode
        if gen_type == "스타일":
            style_desc_val = self.style_desc_entry.get().strip()
            if style_desc_val:
                kwargs["style_description"] = style_desc_val

        # Collect advanced options for pixflux/bitforge
        if gen_type == "이미지" and model in ("pixflux", "bitforge"):
            neg_val = self.negative_desc_entry.get().strip()
            if neg_val:
                kwargs["negative_description"] = neg_val

            tgs_val = self.text_guidance_scale_entry.get().strip()
            if tgs_val:
                try:
                    kwargs["text_guidance_scale"] = float(tgs_val)
                except ValueError:
                    pass

            outline_val = self.outline_var.get()
            if outline_val and outline_val != "없음":
                kwargs["outline"] = outline_val

            shading_val = self.shading_var.get()
            if shading_val and shading_val != "없음":
                kwargs["shading"] = shading_val

            detail_val = self.detail_var.get()
            if detail_val and detail_val != "없음":
                kwargs["detail"] = detail_val

            view_val = self.view_var.get()
            if view_val and view_val != "없음":
                kwargs["view"] = view_val

            direction_val = self.direction_var.get()
            if direction_val and direction_val != "없음":
                kwargs["direction"] = direction_val

            if self.isometric_var.get():
                kwargs["isometric"] = True

        self.gen_btn.configure(state="disabled", text="생성중...")
        self.app.status_bar.set_status("생성중...")

        def do_generate():
            if gen_type == "스타일":
                if not self.style_paths:
                    raise ValueError("스타일 참조 이미지를 1개 이상 추가해주세요.")
                style_images = []
                for sp in self.style_paths:
                    img = image_to_base64(sp)
                    size = get_image_size(sp)
                    style_images.append({"image": img, "width": size["width"], "height": size["height"]})
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
                self.result_label.configure(text=f"{len(saved)}개 이미지 저장 완료 \u2192 {self.app.output_dir}/")
            self.app.status_bar.set_status("준비")

        self.run_async(do_generate, on_done)
