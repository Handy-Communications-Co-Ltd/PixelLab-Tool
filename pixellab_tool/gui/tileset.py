"""Tileset panel."""

from tkinter import filedialog, messagebox

import customtkinter as ctk

from .common import BasePanel, ImagePreview


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

        ctk.CTkLabel(td_tab, text="전환 지형 설명:").pack(anchor="w", padx=10, pady=(10, 0))
        self.td_transition_desc = ctk.CTkEntry(td_tab, placeholder_text="전환 지형 설명 (선택사항)")
        self.td_transition_desc.pack(fill="x", padx=10, pady=5)

        row = ctk.CTkFrame(td_tab)
        row.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(row, text="텍스트 가이던스:").pack(side="left")
        self.td_guidance = ctk.CTkEntry(row, width=60, placeholder_text="8.0")
        self.td_guidance.pack(side="left", padx=5)

        row = ctk.CTkFrame(td_tab)
        row.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(row, text="외곽선:").pack(side="left")
        self.td_outline = ctk.CTkOptionMenu(row, values=["single color black outline", "single color outline", "selective outline", "lineless", "없음"])
        self.td_outline.set("없음")
        self.td_outline.pack(side="left", padx=5)
        ctk.CTkLabel(row, text="셰이딩:").pack(side="left", padx=(10, 0))
        self.td_shading = ctk.CTkOptionMenu(row, values=["flat shading", "low shading", "medium shading", "high shading", "highly detailed shading", "없음"])
        self.td_shading.set("없음")
        self.td_shading.pack(side="left", padx=5)
        ctk.CTkLabel(row, text="디테일:").pack(side="left", padx=(10, 0))
        self.td_detail = ctk.CTkOptionMenu(row, values=["low detail", "medium detail", "highly detailed", "없음"])
        self.td_detail.set("없음")
        self.td_detail.pack(side="left", padx=5)

        row = ctk.CTkFrame(td_tab)
        row.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(row, text="타일 강도:").pack(side="left")
        self.td_tile_strength = ctk.CTkEntry(row, width=60, placeholder_text="1.0")
        self.td_tile_strength.pack(side="left", padx=5)
        ctk.CTkLabel(row, text="준수 자유도:").pack(side="left", padx=(10, 0))
        self.td_adherence_freedom = ctk.CTkEntry(row, width=60, placeholder_text="500.0")
        self.td_adherence_freedom.pack(side="left", padx=5)
        ctk.CTkLabel(row, text="준수:").pack(side="left", padx=(10, 0))
        self.td_adherence = ctk.CTkEntry(row, width=60, placeholder_text="100.0")
        self.td_adherence.pack(side="left", padx=5)

        row = ctk.CTkFrame(td_tab)
        row.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(row, text="전환 크기:").pack(side="left")
        self.td_transition_size = ctk.CTkOptionMenu(row, values=["0.0", "0.25", "0.5", "1.0"])
        self.td_transition_size.set("0.0")
        self.td_transition_size.pack(side="left", padx=5)
        ctk.CTkLabel(row, text="시드:").pack(side="left", padx=(20, 0))
        self.td_seed = ctk.CTkEntry(row, width=80, placeholder_text="랜덤")
        self.td_seed.pack(side="left", padx=5)

        self.td_btn = ctk.CTkButton(td_tab, text="타일셋 생성", command=self.create_topdown, height=40)
        self.td_btn.pack(fill="x", padx=10, pady=15)
        self.td_result = ctk.CTkLabel(td_tab, text="")
        self.td_result.pack(pady=5)
        self.td_preview = ImagePreview(td_tab, 300, 300)
        self.td_preview.pack(pady=5)

        # ── Sidescroller ──
        ss_tab = tabs.add("횡스크롤")

        ctk.CTkLabel(ss_tab, text="설명:").pack(anchor="w", padx=10, pady=(10, 0))
        self.ss_desc = ctk.CTkEntry(ss_tab, placeholder_text="돌 벽돌")
        self.ss_desc.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(ss_tab, text="전환 효과:").pack(anchor="w", padx=10, pady=(10, 0))
        self.ss_trans = ctk.CTkEntry(ss_tab, placeholder_text="이끼 (선택사항)")
        self.ss_trans.pack(fill="x", padx=10, pady=5)

        row = ctk.CTkFrame(ss_tab)
        row.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(row, text="타일 크기:").pack(side="left")
        self.ss_size = ctk.CTkOptionMenu(row, values=["16", "32"])
        self.ss_size.set("16")
        self.ss_size.pack(side="left", padx=5)
        ctk.CTkLabel(row, text="텍스트 가이던스:").pack(side="left", padx=(10, 0))
        self.ss_guidance = ctk.CTkEntry(row, width=60, placeholder_text="8.0")
        self.ss_guidance.pack(side="left", padx=5)

        row = ctk.CTkFrame(ss_tab)
        row.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(row, text="외곽선:").pack(side="left")
        self.ss_outline = ctk.CTkOptionMenu(row, values=["single color black outline", "single color outline", "selective outline", "lineless", "없음"])
        self.ss_outline.set("없음")
        self.ss_outline.pack(side="left", padx=5)
        ctk.CTkLabel(row, text="셰이딩:").pack(side="left", padx=(10, 0))
        self.ss_shading = ctk.CTkOptionMenu(row, values=["flat shading", "low shading", "medium shading", "high shading", "highly detailed shading", "없음"])
        self.ss_shading.set("없음")
        self.ss_shading.pack(side="left", padx=5)
        ctk.CTkLabel(row, text="디테일:").pack(side="left", padx=(10, 0))
        self.ss_detail = ctk.CTkOptionMenu(row, values=["low detail", "medium detail", "highly detailed", "없음"])
        self.ss_detail.set("없음")
        self.ss_detail.pack(side="left", padx=5)

        row = ctk.CTkFrame(ss_tab)
        row.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(row, text="타일 강도:").pack(side="left")
        self.ss_tile_strength = ctk.CTkEntry(row, width=60, placeholder_text="1.0")
        self.ss_tile_strength.pack(side="left", padx=5)
        ctk.CTkLabel(row, text="준수 자유도:").pack(side="left", padx=(10, 0))
        self.ss_adherence_freedom = ctk.CTkEntry(row, width=60, placeholder_text="500.0")
        self.ss_adherence_freedom.pack(side="left", padx=5)
        ctk.CTkLabel(row, text="준수:").pack(side="left", padx=(10, 0))
        self.ss_adherence = ctk.CTkEntry(row, width=60, placeholder_text="100.0")
        self.ss_adherence.pack(side="left", padx=5)

        row = ctk.CTkFrame(ss_tab)
        row.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(row, text="전환 크기:").pack(side="left")
        self.ss_transition_size = ctk.CTkOptionMenu(row, values=["0.0", "0.25", "0.5", "1.0"])
        self.ss_transition_size.set("0.0")
        self.ss_transition_size.pack(side="left", padx=5)
        ctk.CTkLabel(row, text="시드:").pack(side="left", padx=(20, 0))
        self.ss_seed = ctk.CTkEntry(row, width=80, placeholder_text="랜덤")
        self.ss_seed.pack(side="left", padx=5)

        self.ss_btn = ctk.CTkButton(ss_tab, text="횡스크롤 타일 생성", command=self.create_sidescroller, height=40)
        self.ss_btn.pack(fill="x", padx=10, pady=15)
        self.ss_result = ctk.CTkLabel(ss_tab, text="")
        self.ss_result.pack(pady=5)
        self.ss_preview = ImagePreview(ss_tab, 300, 300)
        self.ss_preview.pack(pady=5)

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

        row = ctk.CTkFrame(iso_tab)
        row.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(row, text="이미지 너비:").pack(side="left")
        self.iso_img_w = ctk.CTkEntry(row, width=60, placeholder_text="32")
        self.iso_img_w.pack(side="left", padx=5)
        ctk.CTkLabel(row, text="이미지 높이:").pack(side="left", padx=(10, 0))
        self.iso_img_h = ctk.CTkEntry(row, width=60, placeholder_text="32")
        self.iso_img_h.pack(side="left", padx=5)

        row = ctk.CTkFrame(iso_tab)
        row.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(row, text="텍스트 가이던스:").pack(side="left")
        self.iso_guidance = ctk.CTkEntry(row, width=60, placeholder_text="8.0")
        self.iso_guidance.pack(side="left", padx=5)

        row = ctk.CTkFrame(iso_tab)
        row.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(row, text="외곽선:").pack(side="left")
        self.iso_outline = ctk.CTkOptionMenu(row, values=["single color black outline", "single color outline", "selective outline", "lineless", "없음"])
        self.iso_outline.set("없음")
        self.iso_outline.pack(side="left", padx=5)
        ctk.CTkLabel(row, text="셰이딩:").pack(side="left", padx=(10, 0))
        self.iso_shading = ctk.CTkOptionMenu(row, values=["flat shading", "low shading", "medium shading", "high shading", "highly detailed shading", "없음"])
        self.iso_shading.set("없음")
        self.iso_shading.pack(side="left", padx=5)
        ctk.CTkLabel(row, text="디테일:").pack(side="left", padx=(10, 0))
        self.iso_detail = ctk.CTkOptionMenu(row, values=["low detail", "medium detail", "highly detailed", "없음"])
        self.iso_detail.set("없음")
        self.iso_detail.pack(side="left", padx=5)

        row = ctk.CTkFrame(iso_tab)
        row.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(row, text="아이소 타일 크기:").pack(side="left")
        self.iso_tile_size = ctk.CTkEntry(row, width=60, placeholder_text="자동")
        self.iso_tile_size.pack(side="left", padx=5)
        ctk.CTkLabel(row, text="시드:").pack(side="left", padx=(20, 0))
        self.iso_seed = ctk.CTkEntry(row, width=80, placeholder_text="랜덤")
        self.iso_seed.pack(side="left", padx=5)

        self.iso_btn = ctk.CTkButton(iso_tab, text="아이소메트릭 생성", command=self.create_isometric, height=40)
        self.iso_btn.pack(fill="x", padx=10, pady=15)
        self.iso_result = ctk.CTkLabel(iso_tab, text="")
        self.iso_result.pack(pady=5)
        self.iso_preview = ImagePreview(iso_tab, 300, 300)
        self.iso_preview.pack(pady=5)

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

        row = ctk.CTkFrame(pro_tab)
        row.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(row, text="타일 크기:").pack(side="left")
        self.pro_tile_size = ctk.CTkEntry(row, width=60, placeholder_text="32")
        self.pro_tile_size.pack(side="left", padx=5)
        ctk.CTkLabel(row, text="타일 높이:").pack(side="left", padx=(10, 0))
        self.pro_tile_height = ctk.CTkEntry(row, width=60, placeholder_text="자동")
        self.pro_tile_height.pack(side="left", padx=5)

        row = ctk.CTkFrame(pro_tab)
        row.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(row, text="타일 시점:").pack(side="left")
        self.pro_tile_view = ctk.CTkOptionMenu(row, values=["top-down", "high top-down", "low top-down", "side"])
        self.pro_tile_view.set("low top-down")
        self.pro_tile_view.pack(side="left", padx=5)
        ctk.CTkLabel(row, text="시점 각도:").pack(side="left", padx=(10, 0))
        self.pro_tile_view_angle = ctk.CTkEntry(row, width=60, placeholder_text="자동")
        self.pro_tile_view_angle.pack(side="left", padx=5)
        ctk.CTkLabel(row, text="깊이 비율:").pack(side="left", padx=(10, 0))
        self.pro_tile_depth_ratio = ctk.CTkEntry(row, width=60, placeholder_text="자동")
        self.pro_tile_depth_ratio.pack(side="left", padx=5)

        row = ctk.CTkFrame(pro_tab)
        row.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(row, text="텍스트 가이던스:").pack(side="left")
        self.pro_guidance = ctk.CTkEntry(row, width=60, placeholder_text="8.0")
        self.pro_guidance.pack(side="left", padx=5)

        row = ctk.CTkFrame(pro_tab)
        row.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(row, text="스타일 이미지:").pack(side="left")
        self.pro_style_path = ctk.CTkEntry(row, placeholder_text="스타일 참조 이미지 경로 (선택)")
        self.pro_style_path.pack(side="left", fill="x", expand=True, padx=5)
        ctk.CTkButton(row, text="찾기", width=50, command=self._browse_pro_style).pack(side="left", padx=(0, 5))

        row = ctk.CTkFrame(pro_tab)
        row.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(row, text="시드:").pack(side="left")
        self.pro_seed = ctk.CTkEntry(row, width=80, placeholder_text="랜덤")
        self.pro_seed.pack(side="left", padx=5)

        self.pro_btn = ctk.CTkButton(pro_tab, text="프로 타일 생성", command=self.create_pro_tiles, height=40)
        self.pro_btn.pack(fill="x", padx=10, pady=15)
        self.pro_result = ctk.CTkLabel(pro_tab, text="")
        self.pro_result.pack(pady=5)
        self.pro_preview = ImagePreview(pro_tab, 300, 300)
        self.pro_preview.pack(pady=5)

    def _generate(self, btn, label, fn, btn_text, preview=None):
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
            if preview and saved:
                preview.show_file(saved[0])
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

        kwargs = {}
        val = self.td_transition_desc.get().strip()
        if val:
            kwargs["transition_description"] = val
        val = self.td_guidance.get().strip()
        if val:
            kwargs["text_guidance_scale"] = float(val)
        outline = self.td_outline.get()
        if outline != "없음":
            kwargs["outline"] = outline
        shading = self.td_shading.get()
        if shading != "없음":
            kwargs["shading"] = shading
        detail = self.td_detail.get()
        if detail != "없음":
            kwargs["detail"] = detail
        val = self.td_tile_strength.get().strip()
        if val:
            kwargs["tile_strength"] = float(val)
        val = self.td_adherence_freedom.get().strip()
        if val:
            kwargs["tileset_adherence_freedom"] = float(val)
        val = self.td_adherence.get().strip()
        if val:
            kwargs["tileset_adherence"] = float(val)
        ts = self.td_transition_size.get()
        if ts != "0.0":
            kwargs["transition_size"] = float(ts)
        val = self.td_seed.get().strip()
        if val:
            kwargs["seed"] = int(val)

        def fn():
            result = self.client.create_tileset(lower, upper, tile_size={"width": size, "height": size}, view=view, **kwargs)
            return self.handle_job_and_save(result, "tileset")

        self._generate(self.td_btn, self.td_result, fn, "타일셋 생성", self.td_preview)

    def create_sidescroller(self):
        desc = self.ss_desc.get().strip()
        if not desc:
            messagebox.showwarning("입력 필요", "설명을 입력해주세요.")
            return
        kwargs = {}
        trans = self.ss_trans.get().strip()
        if trans:
            kwargs["transition_description"] = trans
        kwargs["tile_size"] = int(self.ss_size.get())
        val = self.ss_guidance.get().strip()
        if val:
            kwargs["text_guidance_scale"] = float(val)
        outline = self.ss_outline.get()
        if outline != "없음":
            kwargs["outline"] = outline
        shading = self.ss_shading.get()
        if shading != "없음":
            kwargs["shading"] = shading
        detail = self.ss_detail.get()
        if detail != "없음":
            kwargs["detail"] = detail
        val = self.ss_tile_strength.get().strip()
        if val:
            kwargs["tile_strength"] = float(val)
        val = self.ss_adherence_freedom.get().strip()
        if val:
            kwargs["tileset_adherence_freedom"] = float(val)
        val = self.ss_adherence.get().strip()
        if val:
            kwargs["tileset_adherence"] = float(val)
        ts = self.ss_transition_size.get()
        if ts != "0.0":
            kwargs["transition_size"] = float(ts)
        val = self.ss_seed.get().strip()
        if val:
            kwargs["seed"] = int(val)

        def fn():
            result = self.client.create_tileset_sidescroller(desc, **kwargs)
            return self.handle_job_and_save(result, "sidescroller")

        self._generate(self.ss_btn, self.ss_result, fn, "횡스크롤 타일 생성", self.ss_preview)

    def create_isometric(self):
        desc = self.iso_desc.get().strip()
        if not desc:
            messagebox.showwarning("입력 필요", "설명을 입력해주세요.")
            return

        kwargs = {"isometric_tile_shape": self.iso_shape.get()}
        iw = self.iso_img_w.get().strip()
        ih = self.iso_img_h.get().strip()
        if iw and ih:
            kwargs["image_size"] = {"width": int(iw), "height": int(ih)}
        val = self.iso_guidance.get().strip()
        if val:
            kwargs["text_guidance_scale"] = float(val)
        outline = self.iso_outline.get()
        if outline != "없음":
            kwargs["outline"] = outline
        shading = self.iso_shading.get()
        if shading != "없음":
            kwargs["shading"] = shading
        detail = self.iso_detail.get()
        if detail != "없음":
            kwargs["detail"] = detail
        val = self.iso_tile_size.get().strip()
        if val:
            kwargs["isometric_tile_size"] = int(val)
        val = self.iso_seed.get().strip()
        if val:
            kwargs["seed"] = int(val)

        def fn():
            result = self.client.create_isometric_tile(desc, **kwargs)
            return self.handle_job_and_save(result, "iso")

        self._generate(self.iso_btn, self.iso_result, fn, "아이소메트릭 생성", self.iso_preview)

    def _browse_pro_style(self):
        path = filedialog.askopenfilename(filetypes=[("이미지", "*.png *.jpg *.jpeg *.webp")])
        if path:
            self.pro_style_path.delete(0, "end")
            self.pro_style_path.insert(0, path)

    def create_pro_tiles(self):
        desc = self.pro_desc.get().strip()
        if not desc:
            messagebox.showwarning("입력 필요", "설명을 입력해주세요.")
            return
        kwargs = {"tile_type": self.pro_type.get()}
        n = self.pro_n.get().strip()
        if n:
            kwargs["n_tiles"] = int(n)
        val = self.pro_tile_size.get().strip()
        if val:
            kwargs["tile_size"] = int(val)
        val = self.pro_tile_height.get().strip()
        if val:
            kwargs["tile_height"] = int(val)
        kwargs["tile_view"] = self.pro_tile_view.get()
        val = self.pro_tile_view_angle.get().strip()
        if val:
            kwargs["tile_view_angle"] = float(val)
        val = self.pro_tile_depth_ratio.get().strip()
        if val:
            kwargs["tile_depth_ratio"] = float(val)
        val = self.pro_guidance.get().strip()
        if val:
            kwargs["text_guidance_scale"] = float(val)
        style_path = self.pro_style_path.get().strip()
        if style_path:
            from ..utils import image_to_base64
            kwargs["style_images"] = [image_to_base64(style_path)]
        val = self.pro_seed.get().strip()
        if val:
            kwargs["seed"] = int(val)

        def fn():
            result = self.client.create_tiles_pro(desc, **kwargs)
            return self.handle_job_and_save(result, "tiles_pro")

        self._generate(self.pro_btn, self.pro_result, fn, "프로 타일 생성", self.pro_preview)
