# -*- coding: utf-8 -*-
"""
شاشة System Overview (غير مربوطة بالسايد بار — كانت موجودة بدون ربط).

مُرحّلة حرفياً من gui.py الأصلي — منطق البحث والعرض كما هو دون تغيير.
"""
import logging
import re
import threading
from datetime import datetime

import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
import pandas as pd
from tkinter import ttk

from gui.constants import *
from gui.legacy_page import LegacyInquiryPage


class DashboardPage(LegacyInquiryPage):
    """شاشة System Overview (غير مربوطة بالسايد بار — كانت موجودة بدون ربط)."""
    LOAD_BRANCHES_ON_SHOW = False

    def build(self):
        """بناء الشاشة — الكود القديم كما هو (parent = الشاشة نفسها)."""
        parent = self
        # Header
        head = ctk.CTkFrame(parent, fg_color="transparent")
        head.pack(fill="x", pady=(0, 15))

        t_frame = ctk.CTkFrame(head, fg_color="transparent")
        t_frame.pack(side="left")
        ctk.CTkLabel(t_frame, text="System Overview", font=("Segoe UI", 26, "bold"), text_color=FIB_GREEN).pack(
            anchor="w")

        ctk.CTkButton(head, text="🔄 Refresh", width=100, height=35,
                      fg_color=COLOR_WHITE, text_color=COLOR_TEXT_MAIN, hover_color="#EEE",
                      border_width=1, border_color="#CCC",
                      command=self.refresh_dashboard_data).pack(side="right", anchor="ne")

        # Action Card
        card = ctk.CTkFrame(parent, fg_color=COLOR_WHITE, corner_radius=15, border_width=1, border_color="#E0E0E0")
        card.pack(fill="x", pady=15)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(padx=30, pady=25, fill="x")

        # 🔒 قفل الزرار لو مفيش رخصة
        if self.lic_data["active"]:
            btn_state = "normal"
            btn_text = "🚀 START PROCESS"
            btn_fg = FIB_GREEN
            lbl_status = "Status: IDLE"
        else:
            btn_state = "disabled"
            btn_text = "🔒 LICENSE REQUIRED"
            btn_fg = "gray"
            lbl_status = "Status: RESTRICTED MODE"

        ctk.CTkLabel(inner, text=lbl_status, font=("Segoe UI", 14, "bold"), text_color="gray").pack(side="right")

        self.btn_run = ctk.CTkButton(inner, text=btn_text, font=("Segoe UI", 14, "bold"),
                                     height=45, width=220, fg_color=btn_fg, hover_color="#00402C",
                                     state=btn_state,  # 👈 دي أهم حاجة
                                     command=self.start_process)
        self.btn_run.pack(side="left")

        self.progress = ctk.CTkProgressBar(card, height=4, progress_color=FIB_GOLD, fg_color="#EEE")
        self.progress.pack(fill="x", side="bottom")
        self.progress.pack_forget()

        # Tabs
        # التعديل الصحيح:
        # text_color="white": بيخلي الخط أبيض
        # segmented_button_unselected_color="#555": بيخلي خلفية الزرار اللي مش شغال غامقة عشان الأبيض يبان
        tabs = ctk.CTkTabview(parent,
                              fg_color=COLOR_WHITE,
                              text_color="white",
                              segmented_button_selected_color=FIB_GREEN,
                              segmented_button_unselected_color="#555",
                              segmented_button_unselected_hover_color="#444")

        tabs.pack(fill="both", expand=True)
        tabs.add("Live Monitor")
        tabs.add("History Log")
        # ✅ MONITOR: Dark Background & White Text
        self.log_box = ctk.CTkTextbox(tabs.tab("Live Monitor"), font=("Consolas", 11),
                                      fg_color=COLOR_DARK_BG, text_color=COLOR_TEXT_LITE)
        self.log_box.pack(fill="both", expand=True, padx=10, pady=10)

        # ✅ HISTORY: Dark Background & White Text
        cols = ("ID", "File Name", "ِAdded Rows", "Status", "Date")
        self.tree = ttk.Treeview(tabs.tab("History Log"), columns=cols, show="headings", height=10)
        self.style_treeview()  # Apply dark style

        for c in cols: self.tree.heading(c, text=c)
        self.tree.column("ID", width=60, anchor="center")
        self.tree.column("File Name", width=400)
        self.tree.column("ِAdded Rows", width=80)
        self.tree.column("Status", width=120, anchor="center")

        scrolly = ttk.Scrollbar(tabs.tab("History Log"), orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrolly.set)
        scrolly.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True, padx=5, pady=5)
