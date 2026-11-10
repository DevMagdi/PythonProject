# -*- coding: utf-8 -*-
"""
شاشة التقارير (غير مربوطة بالسايد بار — كانت موجودة بدون ربط).

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

from gui.constants import *
from gui.legacy_page import LegacyInquiryPage


class ReportsPage(LegacyInquiryPage):
    """شاشة التقارير (غير مربوطة بالسايد بار — كانت موجودة بدون ربط)."""
    LOAD_BRANCHES_ON_SHOW = False

    def build(self):
        """بناء الشاشة — الكود القديم كما هو (parent = الشاشة نفسها)."""
        parent = self
        ctk.CTkLabel(parent, text="Analytics & Reports", font=("Segoe UI", 24, "bold"), text_color=FIB_GREEN).pack(
            anchor="w", pady=(0, 20))

        # Stats
        stats_box = ctk.CTkFrame(parent, fg_color="transparent")
        stats_box.pack(fill="x", pady=10)

        self.card_total = self.create_stat_card(stats_box, "Total Files Processed", "0")
        self.card_total.pack(side="left", fill="x", expand=True, padx=10)

        self.card_today = self.create_stat_card(stats_box, "Processed Today", "0")
        self.card_today.pack(side="left", fill="x", expand=True, padx=10)

        # 🔒 لو مفيش رخصة الزرار لونه رمادي ومقفول
        excel_state = "normal" if self.lic_data["active"] else "disabled"
        excel_color = FIB_GOLD if self.lic_data["active"] else "gray"

        self.btn_export = ctk.CTkButton(parent, text="📥 Export to Excel", fg_color=excel_color, text_color="white",
                                        state=excel_state,
                                        command=self.export_report_excel)
        self.btn_export.pack(anchor="e", pady=(20, 5))

        # Text Report (Read-only view)
        self.txt_rep = ctk.CTkTextbox(parent, font=("Consolas", 11), fg_color=COLOR_WHITE)
        self.txt_rep.pack(fill="both", expand=True)
