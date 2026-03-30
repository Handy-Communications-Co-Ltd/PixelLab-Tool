"""Animation panel."""

from tkinter import filedialog, messagebox

import customtkinter as ctk

from ..utils import image_to_base64, get_image_size
from .common import BasePanel


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

        # ── v1 parameters ──
        v1_row = ctk.CTkFrame(text_tab)
        v1_row.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(v1_row, text="시드 (v1):").pack(side="left")
        self.v1_seed = ctk.CTkEntry(v1_row, width=80, placeholder_text="랜덤")
        self.v1_seed.pack(side="left", padx=5)

        # ── v2 parameters ──
        v2_frame = ctk.CTkFrame(text_tab)
        v2_frame.pack(fill="x", padx=10, pady=5)

        v2_row1 = ctk.CTkFrame(v2_frame)
        v2_row1.pack(fill="x", pady=2)
        ctk.CTkLabel(v2_row1, text="시드 (v2):").pack(side="left")
        self.v2_seed = ctk.CTkEntry(v2_row1, width=80, placeholder_text="랜덤")
        self.v2_seed.pack(side="left", padx=5)
        self.v2_no_background = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(v2_row1, text="배경 제거", variable=self.v2_no_background).pack(side="left", padx=15)

        v2_row2 = ctk.CTkFrame(v2_frame)
        v2_row2.pack(fill="x", pady=2)
        ctk.CTkLabel(v2_row2, text="뷰:").pack(side="left")
        self.v2_view = ctk.CTkOptionMenu(v2_row2, values=["없음", "none", "side", "low top-down", "high top-down"])
        self.v2_view.pack(side="left", padx=5)
        ctk.CTkLabel(v2_row2, text="방향:").pack(side="left", padx=(15, 0))
        self.v2_direction = ctk.CTkOptionMenu(v2_row2, values=["없음", "none", "south", "south-east", "east", "north-east", "north", "north-west", "west", "south-west"])
        self.v2_direction.pack(side="left", padx=5)

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

        interp_seed_row = ctk.CTkFrame(interp_tab)
        interp_seed_row.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(interp_seed_row, text="시드:").pack(side="left")
        self.interp_seed = ctk.CTkEntry(interp_seed_row, width=80, placeholder_text="랜덤")
        self.interp_seed.pack(side="left", padx=5)

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
                kwargs = {}
                v2_seed_val = self.v2_seed.get().strip()
                if v2_seed_val:
                    kwargs["seed"] = int(v2_seed_val)
                if self.v2_no_background.get():
                    kwargs["no_background"] = True
                view_val = self.v2_view.get()
                if view_val and view_val != "없음":
                    kwargs["view"] = view_val
                dir_val = self.v2_direction.get()
                if dir_val and dir_val != "없음":
                    kwargs["direction"] = dir_val
                result = self.client.animate_with_text_v2(ref_img, action, w, h, description=desc, **kwargs)
            else:
                kwargs = {}
                v1_seed_val = self.v1_seed.get().strip()
                if v1_seed_val:
                    kwargs["seed"] = int(v1_seed_val)
                result = self.client.animate_with_text(ref_img, desc, action, **kwargs)
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
            start_size = get_image_size(start)
            end_img = image_to_base64(end)
            end_size = get_image_size(end)
            start_obj = {"image": start_img, "size": start_size}
            end_obj = {"image": end_img, "size": end_size}
            kwargs = {}
            interp_seed_val = self.interp_seed.get().strip()
            if interp_seed_val:
                kwargs["seed"] = int(interp_seed_val)
            result = self.client.interpolate(start_obj, end_obj, action, **kwargs)
            saved = self.handle_job_and_save(result, "interp")
            return saved

        def on_done(saved, err):
            self.interp_btn.configure(state="normal", text="보간 생성")
            if err:
                messagebox.showerror("오류", str(err))
                return
            self.interp_result.configure(text=f"{len(saved)}개 프레임 저장 완료")

        self.run_async(do_interp, on_done)
