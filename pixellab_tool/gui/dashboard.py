"""Dashboard panel."""

from tkinter import messagebox

import customtkinter as ctk

from .common import BasePanel


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
