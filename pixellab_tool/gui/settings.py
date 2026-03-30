"""Settings panel."""

import os
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from ..client import PixelLabClient
from .common import BasePanel, DEFAULT_OUTPUT_DIR


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
