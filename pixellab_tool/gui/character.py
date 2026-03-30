"""Character panel."""

import os
import re
import zipfile
from tkinter import filedialog, messagebox

import customtkinter as ctk
from PIL import Image, ImageTk

from ..utils import image_to_base64, get_image_size
from .common import (
    BasePanel,
    ImagePreview,
    CHARACTER_SIZE_PRESETS,
    ANIMATION_TEMPLATES,
    download_image_from_url,
    _load_anim_track,
    _save_anim_track,
    _record_animation,
    _get_character_animations,
    _extract_animations_from_zip,
)


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

        row4 = ctk.CTkFrame(create_tab)
        row4.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(row4, text="텍스트 가이던스:").pack(side="left")
        self.text_guidance_entry = ctk.CTkEntry(row4, width=60, placeholder_text="자동")
        self.text_guidance_entry.pack(side="left", padx=5)

        ctk.CTkLabel(row4, text="색상 참조 이미지:").pack(side="left", padx=(20, 0))
        self.color_image_entry = ctk.CTkEntry(row4, width=200, placeholder_text="파일 경로...")
        self.color_image_entry.pack(side="left", padx=5)
        ctk.CTkButton(row4, text="찾아보기", width=70,
                      command=self._browse_color_image).pack(side="left", padx=2)

        self.force_colors_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(row4, text="색상 강제 적용", variable=self.force_colors_var).pack(side="left", padx=20)

        # Character proportions
        prop_frame = ctk.CTkFrame(create_tab)
        prop_frame.pack(fill="x", padx=10, pady=5)

        prop_header = ctk.CTkFrame(prop_frame, fg_color="transparent")
        prop_header.pack(fill="x")
        ctk.CTkLabel(prop_header, text="체형:").pack(side="left")
        self.prop_mode_var = ctk.StringVar(value="없음")
        ctk.CTkOptionMenu(prop_header, values=["없음", "프리셋", "커스텀"],
                          variable=self.prop_mode_var,
                          command=self._on_prop_mode_change).pack(side="left", padx=5)

        # Preset frame
        self.prop_preset_frame = ctk.CTkFrame(prop_frame)
        self.prop_preset_var = ctk.StringVar(value="default")
        ctk.CTkOptionMenu(self.prop_preset_frame,
                          values=["default", "chibi", "cartoon", "stylized",
                                  "realistic_male", "realistic_female", "heroic"],
                          variable=self.prop_preset_var).pack(side="left", padx=10, pady=5)

        # Custom sliders frame
        self.prop_sliders_frame = ctk.CTkFrame(prop_frame)
        self.proportion_vars = {}
        prop_defs = {
            "head_size": ("head_size (머리 크기)", 1.0),
            "arms_length": ("arms_length (팔 길이)", 1.0),
            "legs_length": ("legs_length (다리 길이)", 1.0),
            "shoulder_width": ("shoulder_width (어깨 너비)", 1.0),
            "hip_width": ("hip_width (엉덩이 너비)", 1.0),
        }
        for key, (label, default) in prop_defs.items():
            r = ctk.CTkFrame(self.prop_sliders_frame)
            r.pack(fill="x", pady=1)
            ctk.CTkLabel(r, text=f"{label}:", width=180, anchor="w").pack(side="left")
            var = ctk.DoubleVar(value=default)
            slider = ctk.CTkSlider(r, from_=0.5, to=2.0, variable=var, width=150, number_of_steps=30)
            slider.pack(side="left", padx=5)
            val_label = ctk.CTkLabel(r, text=f"{default:.2f}", width=35)
            val_label.pack(side="left")
            var.trace_add("write", lambda *a, v=var, l=val_label: l.configure(text=f"{v.get():.2f}"))
            self.proportion_vars[key] = var

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

        # Direction navigation
        dir_nav = ctk.CTkFrame(create_tab, fg_color="transparent")
        dir_nav.pack(pady=2)
        self._create_saved_files = []
        self._create_dir_index = 0
        ctk.CTkButton(dir_nav, text="\u25c0", width=40, command=self._prev_direction).pack(side="left", padx=5)
        self._dir_label = ctk.CTkLabel(dir_nav, text="", width=120)
        self._dir_label.pack(side="left", padx=5)
        ctk.CTkButton(dir_nav, text="\u25b6", width=40, command=self._next_direction).pack(side="left", padx=5)

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
        anim_sel_row = ctk.CTkFrame(anim_tab)
        anim_sel_row.pack(fill="x", padx=10, pady=5)
        self.anim_char_thumb = ctk.CTkLabel(anim_sel_row, text="", width=64, height=64)
        self.anim_char_thumb.pack(side="left", padx=(0, 10))
        self._anim_char_photo = None
        self.anim_char_menu = ctk.CTkOptionMenu(anim_sel_row, values=["관리 탭에서 먼저 목록을 새로고침하세요"], width=400, command=self._on_anim_char_changed)
        self.anim_char_menu.pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(anim_tab, text="템플릿 애니메이션:").pack(anchor="w", padx=10, pady=(10, 0))
        self.anim_template = ctk.CTkOptionMenu(anim_tab, values=ANIMATION_TEMPLATES)
        self.anim_template.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(anim_tab, text="커스텀 동작 설명 (선택사항):").pack(anchor="w", padx=10, pady=(10, 0))
        self.anim_action_desc = ctk.CTkEntry(anim_tab, placeholder_text="예: 큰 망치를 세게 휘두르기")
        self.anim_action_desc.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(anim_tab, text="방향 선택 (복수 선택 가능):").pack(anchor="w", padx=10, pady=(10, 0))

        dir_frame = ctk.CTkFrame(anim_tab)
        dir_frame.pack(fill="x", padx=10, pady=5)

        self.anim_dir_vars = {}
        self.anim_all_var = ctk.BooleanVar(value=True)

        dir_row1 = ctk.CTkFrame(dir_frame)
        dir_row1.pack(fill="x", pady=2)
        ctk.CTkCheckBox(dir_row1, text="전체", variable=self.anim_all_var,
                        command=self._toggle_all_dirs).pack(side="left", padx=5)

        dir_row2 = ctk.CTkFrame(dir_frame)
        dir_row2.pack(fill="x", pady=2)
        for d in ["south", "west", "east", "north"]:
            var = ctk.BooleanVar(value=False)
            ctk.CTkCheckBox(dir_row2, text=d, variable=var, width=110,
                            command=self._on_dir_check).pack(side="left", padx=3)
            self.anim_dir_vars[d] = var

        dir_row3 = ctk.CTkFrame(dir_frame)
        dir_row3.pack(fill="x", pady=2)
        for d in ["south-west", "south-east", "north-west", "north-east"]:
            var = ctk.BooleanVar(value=False)
            ctk.CTkCheckBox(dir_row3, text=d, variable=var, width=110,
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

        self.batch_dir_vars = {}
        self.batch_all_dir = ctk.BooleanVar(value=True)

        bdir_row1 = ctk.CTkFrame(batch_dir_frame)
        bdir_row1.pack(fill="x", pady=2)
        ctk.CTkCheckBox(bdir_row1, text="전체", variable=self.batch_all_dir,
                        command=self._batch_toggle_dirs).pack(side="left", padx=5)

        bdir_row2 = ctk.CTkFrame(batch_dir_frame)
        bdir_row2.pack(fill="x", pady=2)
        for d in ["south", "west", "east", "north"]:
            var = ctk.BooleanVar(value=False)
            ctk.CTkCheckBox(bdir_row2, text=d, variable=var, width=110,
                            command=self._batch_on_dir_check).pack(side="left", padx=3)
            self.batch_dir_vars[d] = var

        bdir_row3 = ctk.CTkFrame(batch_dir_frame)
        bdir_row3.pack(fill="x", pady=2)
        for d in ["south-west", "south-east", "north-west", "north-east"]:
            var = ctk.BooleanVar(value=False)
            ctk.CTkCheckBox(bdir_row3, text=d, variable=var, width=110,
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
            # Wait for server to sync new animation data before exporting
            import time
            self.after(0, lambda: self.app.status_bar.set_status("서버 동기화 대기중..."))
            time.sleep(5)
            # Auto-export all characters
            for i, cid in enumerate(selected):
                self.after(0, lambda n=i+1, t=total, c=cid:
                          self.app.status_bar.set_status(f"내보내기중 ({n}/{t}) - {c[:8]}..."))
                self._export_and_extract(cid)
            return all_saved

        def on_done(saved, err):
            self.batch_run_btn.configure(state="normal", text="일괄 애니메이션 생성")
            self.batch_progress.pack_forget()
            if err:
                messagebox.showerror("오류", str(err))
                self.app.status_bar.set_status("일괄 생성 실패")
                return
            self.batch_result.configure(text=f"{total}개 캐릭터에 '{template}' 생성 + 내보내기 완료 ({len(saved)}개 프레임)")
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

    def _on_anim_char_changed(self, selection: str):
        """Show thumbnail preview when animation character selection changes."""
        self._anim_char_photo = None
        self.anim_char_thumb.configure(image=None, text="")
        if "[" not in selection:
            return
        short_id = selection.split("[")[-1].rstrip("]")
        for ch in self.loaded_characters:
            cid = str(ch.get("id", ch.get("character_id", "")))
            if cid.startswith(short_id):
                preview_img = ch.get("_preview_img")
                if preview_img:
                    try:
                        thumb = preview_img.copy()
                        thumb.thumbnail((64, 64), Image.NEAREST)
                        self._anim_char_photo = ImageTk.PhotoImage(thumb)
                        self.anim_char_thumb.configure(image=self._anim_char_photo)
                    except Exception:
                        self.anim_char_thumb.configure(text="[오류]")
                else:
                    self.anim_char_thumb.configure(text="[미리보기\n없음]")
                return

    def _update_anim_dropdown(self):
        """Update the animation tab's character dropdown from loaded characters."""
        if not self.loaded_characters:
            no_char = ["캐릭터 없음"]
            self.anim_char_menu.configure(values=no_char)
            self.anim_char_menu.set(no_char[0])
            self._anim_char_photo = None
            self.anim_char_thumb.configure(image=None, text="")
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
        self._on_anim_char_changed(items[0])
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

    def _get_char_name(self, cid: str) -> str:
        """Get a safe filename-friendly character name from loaded characters."""
        for ch in self.loaded_characters:
            ch_id = str(ch.get("id", ch.get("character_id", "")))
            if ch_id == cid or ch_id.startswith(cid):
                desc = str(ch.get("prompt", ch.get("description", ch.get("name", ""))))[:30]
                # Remove invalid filename characters
                safe = re.sub(r'[\\/:*?"<>|]', '', desc).strip()
                if safe:
                    return safe
        return cid[:12]

    def _export_and_extract(self, cid: str) -> str:
        """Export character ZIP, extract it, delete ZIP, return extracted folder path."""
        import io as _io
        data = self.client.export_character_zip(cid)
        out = self.app.output_dir
        os.makedirs(out, exist_ok=True)
        name = self._get_char_name(cid)
        folder_name = f"{name}_{cid[:8]}"
        extract_dir = os.path.join(out, folder_name)
        os.makedirs(extract_dir, exist_ok=True)
        with zipfile.ZipFile(_io.BytesIO(data)) as zf:
            zf.extractall(extract_dir)
        # Generate sprite sheets for each animation
        self._generate_sprite_sheets(extract_dir)
        return extract_dir

    @staticmethod
    def _generate_sprite_sheets(extract_dir: str):
        """Scan animations/ folder and create a sprite sheet per animation.

        Layout: each row is a direction, each column is a frame.
        Direction order: south, south-east, east, north-east, north, north-west, west, south-west.
        """
        DIRECTION_ORDER = [
            "south", "south-east", "east", "north-east",
            "north", "north-west", "west", "south-west",
        ]
        anim_root = None
        for candidate in ("animations", "animation", "anims"):
            path = os.path.join(extract_dir, candidate)
            if os.path.isdir(path):
                anim_root = path
                break
        if not anim_root:
            return

        sheets_dir = os.path.join(extract_dir, "spritesheets")
        os.makedirs(sheets_dir, exist_ok=True)

        for anim_name in sorted(os.listdir(anim_root)):
            anim_dir = os.path.join(anim_root, anim_name)
            if not os.path.isdir(anim_dir):
                continue

            # Collect directions and their frames
            dir_frames = {}
            for d in os.listdir(anim_dir):
                d_path = os.path.join(anim_dir, d)
                if not os.path.isdir(d_path):
                    continue
                frames = sorted(
                    f for f in os.listdir(d_path)
                    if f.lower().endswith((".png", ".jpg", ".jpeg"))
                )
                if frames:
                    dir_frames[d] = [os.path.join(d_path, f) for f in frames]

            if not dir_frames:
                continue

            # Sort directions by standard order
            sorted_dirs = sorted(
                dir_frames.keys(),
                key=lambda d: DIRECTION_ORDER.index(d) if d in DIRECTION_ORDER else 99,
            )

            # Determine frame size from first image
            first_img = Image.open(dir_frames[sorted_dirs[0]][0])
            fw, fh = first_img.size
            first_img.close()

            n_cols = max(len(dir_frames[d]) for d in sorted_dirs)
            n_rows = len(sorted_dirs)

            sheet = Image.new("RGBA", (fw * n_cols, fh * n_rows), (0, 0, 0, 0))

            for row, d in enumerate(sorted_dirs):
                for col, frame_path in enumerate(dir_frames[d]):
                    frame = Image.open(frame_path)
                    sheet.paste(frame, (col * fw, row * fh))
                    frame.close()

            sheet_path = os.path.join(sheets_dir, f"{anim_name}.png")
            sheet.save(sheet_path, "PNG")
            sheet.close()

    def _prev_direction(self):
        if not self._create_saved_files:
            return
        self._create_dir_index = (self._create_dir_index - 1) % len(self._create_saved_files)
        self._show_direction()

    def _next_direction(self):
        if not self._create_saved_files:
            return
        self._create_dir_index = (self._create_dir_index + 1) % len(self._create_saved_files)
        self._show_direction()

    def _show_direction(self):
        path = self._create_saved_files[self._create_dir_index]
        self.create_preview.show_file(path)
        name = os.path.basename(path)
        idx = self._create_dir_index + 1
        total = len(self._create_saved_files)
        self._dir_label.configure(text=f"{name} ({idx}/{total})")

    def _browse_color_image(self):
        path = filedialog.askopenfilename(
            title="색상 참조 이미지 선택",
            filetypes=[("이미지 파일", "*.png *.jpg *.jpeg *.bmp *.webp"), ("모든 파일", "*.*")]
        )
        if path:
            self.color_image_entry.delete(0, "end")
            self.color_image_entry.insert(0, path)

    def _on_prop_mode_change(self, choice):
        self.prop_preset_frame.pack_forget()
        self.prop_sliders_frame.pack_forget()
        if choice == "프리셋":
            self.prop_preset_frame.pack(fill="x")
        elif choice == "커스텀":
            self.prop_sliders_frame.pack(fill="x", padx=10, pady=5)

    def create_character(self):
        if not self.require_client():
            return
        desc = self.desc_entry.get().strip()
        if not desc:
            messagebox.showwarning("입력 필요", "설명을 입력해주세요.")
            return

        size_parts = self.size_var.get().split("x")
        w, h = int(size_parts[0]), int(size_parts[1])
        dirs_raw = self.dir_var.get()
        dirs = "8" if "8" in dirs_raw else "4"


        kwargs = {}
        prop_mode = self.prop_mode_var.get()
        if prop_mode == "프리셋":
            kwargs["proportions"] = {
                "type": "preset",
                "name": self.prop_preset_var.get(),
            }
        elif prop_mode == "커스텀":
            kwargs["proportions"] = {
                "type": "custom",
                **{k: round(v.get(), 2) for k, v in self.proportion_vars.items()},
            }
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
        tgs = self.text_guidance_entry.get().strip()
        if tgs:
            kwargs["text_guidance_scale"] = float(tgs)
        color_img_path = self.color_image_entry.get().strip()
        if color_img_path:
            kwargs["color_image"] = image_to_base64(color_img_path)
        if self.force_colors_var.get():
            kwargs["force_colors"] = True
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
                    # Debug: log raw response
                    import json as _json
                    print(f"[DEBUG] Character creation response: {_json.dumps(result, indent=2, default=str)[:500]}")
                except Exception as e:
                    err_msg = str(e)
                    if "429" in err_msg or "concurrent" in err_msg.lower() or "job limits" in err_msg.lower():
                        raise Exception(
                            "작업 한도 초과!\n\n"
                            "PixelLab 구독 플랜의 동시 작업 또는 일일 한도에 도달했습니다.\n"
                            "대시보드에서 잔여 크레딧을 확인하거나 잠시 후 다시 시도해주세요."
                        ) from None
                    params = f"size={w}x{h}, dirs={dirs}"
                    if run_kwargs:
                        params += ", " + ", ".join(f"{k}={v}" for k, v in run_kwargs.items() if k != "seed")
                    raise Exception(f"{err_msg}\n\n전송 파라미터: {params}") from None

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
                self._create_saved_files = last_saved
                self._create_dir_index = 0
                self._show_direction()
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
        self.app.status_bar.set_status("내보내기중...")

        def do_export():
            return self._export_and_extract(cid)

        def on_done(path, err):
            if err:
                messagebox.showerror("오류", str(err))
                self.app.status_bar.set_status("실패")
                return
            self.app.status_bar.set_status("준비")
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
            # Wait for server to sync new animation data before exporting
            import time
            self.after(0, lambda: self.app.status_bar.set_status("서버 동기화 대기중..."))
            time.sleep(5)
            self.after(0, lambda: self.app.status_bar.set_status("내보내기중..."))
            export_path = self._export_and_extract(cid)
            return (all_saved, export_path)

        def on_done(result, err):
            self.anim_btn.configure(state="normal", text="애니메이션 생성")
            if err:
                messagebox.showerror("오류", str(err))
                self.app.status_bar.set_status("애니메이션 실패")
                return
            saved, export_path = result
            self.anim_result.configure(text=f"{len(saved)}개 프레임 저장 + 내보내기 완료")
            self.app.status_bar.set_status("준비")

        self.run_async(do_animate, on_done)
