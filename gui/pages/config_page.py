# -*- coding: utf-8 -*-
"""
شاشة إعدادات الاتصال (غير مربوطة بالسايد بار — كانت موجودة بدون ربط).

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


class ConfigPage(LegacyInquiryPage):
    """شاشة إعدادات الاتصال (غير مربوطة بالسايد بار — كانت موجودة بدون ربط)."""
    LOAD_BRANCHES_ON_SHOW = False

    def build(self):
        """بناء الشاشة — الكود القديم كما هو (parent = الشاشة نفسها)."""
        parent = self
        # عنوان الصفحة
        ctk.CTkLabel(parent, text="System Configuration", font=("Segoe UI", 24, "bold"), text_color=FIB_GREEN).pack(
            anchor="w", pady=(0, 20))

        # الإطار الأبيض الكبير
        frame = ctk.CTkFrame(parent, fg_color=COLOR_WHITE, corner_radius=10)
        frame.pack(fill="both", expand=True)

        # 1. منطقة الإدخال (Inputs Area)
        scroll_frame = ctk.CTkScrollableFrame(frame, fg_color="transparent")
        scroll_frame.pack(fill="both", expand=True, padx=20, pady=20)

        inner = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        inner.pack(fill="x", padx=10, pady=10)

        # دالة مساعدة لرسم الحقول (معدلة لتقبل حقل الباسورد)
        def add_field(row, label, val, is_pass=False):
            ctk.CTkLabel(inner, text=label, font=("Segoe UI", 12, "bold"), text_color=FIB_GREEN).grid(row=row, column=0,
                                                                                                      sticky="w",
                                                                                                      pady=(5, 2))

            # لو هو باسورد خليه نجوم *
            show_char = "*" if is_pass else ""

            ent = ctk.CTkEntry(inner, width=400, height=35, border_color="#CCC", show=show_char)
            ent.grid(row=row + 1, column=0, sticky="w", pady=(0, 10))
            ent.delete(0, "end")
            ent.insert(0, str(val) if val else "")
            return ent

        # --- الحقول الأساسية ---

        # 1. Server
        self.ent_server = add_field(0, "Server Host Address", self.server_val)

        # 2. Database Name
        self.ent_db = add_field(2, "Database Name", self.db_val)

        # 3. SQL User (الجزء اللي كان ناقصك) 🔥
        user_v = getattr(self, 'user_val', '')  # حماية عشان لو المتغير مش موجود
        self.ent_user = add_field(4, "SQL Username (Optional)", user_v)

        # 4. SQL Password (الجزء اللي كان ناقصك) 🔥
        pass_v = getattr(self, 'pass_val', '')
        self.ent_pass = add_field(6, "SQL Password", pass_v, is_pass=True)

        # --- اختيار نوع المصدر ---
        # لاحظ غيرنا رقم الصف لـ 8 عشان وسعنا مكان لليوزر والباسورد
        ctk.CTkLabel(inner, text="Data Source Type", font=("Segoe UI", 12, "bold"), text_color=FIB_GREEN).grid(row=8,
                                                                                                               column=0,
                                                                                                               sticky="w",
                                                                                                               pady=(10,
                                                                                                                     5))

        if not hasattr(self, 'radio_var'): self.radio_var = tk.StringVar(value="Folder")

        radio_frame = ctk.CTkFrame(inner, fg_color="transparent")
        radio_frame.grid(row=9, column=0, sticky="w", pady=(0, 5))

        ctk.CTkRadioButton(radio_frame, text="Folder (CSV/Excel)", variable=self.radio_var, value="Folder",
                           text_color="#333", command=self.update_path_label).pack(side="left", padx=(0, 20))
        ctk.CTkRadioButton(radio_frame, text="MS Access Database", variable=self.radio_var, value="Access",
                           text_color="#333", command=self.update_path_label).pack(side="left")

        # --- مسار الملف ---
        self.lbl_path_title = ctk.CTkLabel(inner, text="Source Folder Path", font=("Segoe UI", 12, "bold"),
                                           text_color=FIB_GREEN)
        self.lbl_path_title.grid(row=10, column=0, sticky="w", pady=(10, 5))

        f_frame = ctk.CTkFrame(inner, fg_color="transparent")
        f_frame.grid(row=11, column=0, sticky="ew")

        self.ent_folder = ctk.CTkEntry(f_frame, textvariable=self.folder_path_var, height=35, border_color="#CCC",
                                       width=300)
        self.ent_folder.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(f_frame, text="Browse", width=80, height=35, fg_color=FIB_GOLD, text_color="white",
                      command=self.browse_folder).pack(side="left", padx=10)

        # --- خيارات متقدمة (Merge & Append) ---
        opts_frame = ctk.CTkFrame(inner, fg_color="#F1F3F5", corner_radius=6)
        opts_frame.grid(row=12, column=0, sticky="ew", pady=15)

        # أ. خيار التزويد Append
        self.chk_append_var = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(opts_frame, text="Append Data (Don't drop existing tables)", variable=self.chk_append_var,
                        font=("Segoe UI", 11, "bold"), text_color="#333").pack(anchor="w", padx=10, pady=10)

        # ب. خيار الدمج Merge
        self.chk_merge_var = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(opts_frame, text="Merge all tables into one SQL Table", variable=self.chk_merge_var,
                        command=self.toggle_merge_entry, font=("Segoe UI", 11, "bold"), text_color="#333").pack(
            anchor="w", padx=10, pady=(0, 5))

        # ج. خانة اسم الجدول المجمع
        self.ent_merge_name = ctk.CTkEntry(opts_frame, placeholder_text="Target Table Name (e.g. All_Branches)",
                                           width=300)
        self.ent_merge_name.pack(anchor="w", padx=35, pady=(0, 10))
        self.ent_merge_name.configure(state="disabled", fg_color="#EEE")

        # 2. منطقة الأزرار (Buttons Area)
        btn_box = ctk.CTkFrame(frame, fg_color="transparent")
        btn_box.pack(side="bottom", fill="x", pady=20)

        cfg_state = "normal" if self.lic_data.get("active", False) else "disabled"

        btn_inner = ctk.CTkFrame(btn_box, fg_color="transparent")
        btn_inner.pack()

        self.btn_save = ctk.CTkButton(btn_inner, text="💾 Save Settings", fg_color=FIB_GREEN, width=150, height=40,
                                      state=cfg_state, command=self.save_config)
        self.btn_save.pack(side="left", padx=10)

        self.btn_test = ctk.CTkButton(btn_inner, text="🔌 Test Connection", fg_color="#EEE", text_color="#333",
                                      width=150, height=40, state=cfg_state, command=self.test_conn)
        self.btn_test.pack(side="left", padx=10)

    def toggle_merge_entry(self):
        if self.chk_merge_var.get():
            self.ent_merge_name.configure(state="normal", fg_color="white")
        else:
            self.ent_merge_name.configure(state="disabled", fg_color="#EEE")

    def update_path_label(self):
        """تغيير عنوان المسار بناءً على الاختيار"""
        if self.radio_var.get() == "Access":
            self.lbl_path_title.configure(text="Access Database File (.accdb / .mdb)")
        else:
            self.lbl_path_title.configure(text="Source Folder Path")
