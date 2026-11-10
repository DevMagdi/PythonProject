# -*- coding: utf-8 -*-
"""
شاشة الاستفسار عن اجمالي إجازات الموظف السابقة.

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


class LeavesMovementPage(LegacyInquiryPage):
    """شاشة الاستفسار عن اجمالي إجازات الموظف السابقة."""
    LOAD_BRANCHES_ON_SHOW = False

    def build(self):
        """بناء الشاشة — الكود القديم كما هو (parent = الشاشة نفسها)."""
        parent = self


        # =========================================
        # 🎨 الألوان والتنسيقات المعتمدة (Compact & Premium)
        # =========================================
        FIB_GREEN = "#005C34"
        FIB_GOLD = "#C5A059"
        BG_MAIN = "#F8FAFC"
        CARD_BG = "#FFFFFF"
        BOX_BG = "#F1F5F9"
        TEXT_DARK = "#0F172A"
        TEXT_MUTED = "#64748B"

        MAIN_FONT = "Arial"

        main_container = ctk.CTkFrame(parent, fg_color=BG_MAIN)
        main_container.pack(fill="both", expand=True)

        header = ctk.CTkFrame(main_container, fg_color=FIB_GREEN, height=55, corner_radius=0)
        header.pack(fill="x")
        header.pack_propagate(False)

        ctk.CTkFrame(main_container, fg_color=FIB_GOLD, height=3, corner_radius=0).pack(fill="x")

        ctk.CTkLabel(
            header, text="حركة إجازات الموظف السابقة ✈️",
            font=(MAIN_FONT, 20, "bold"), text_color=CARD_BG
        ).pack(side="right", padx=25, pady=12)

        # =========================================
        # 🔍 منطقة البحث (مضغوطة)
        # =========================================
        search_frame = ctk.CTkFrame(main_container, fg_color=CARD_BG, corner_radius=12, border_width=1,
                                    border_color="#E2E8F0")
        search_frame.pack(fill="x", padx=15, pady=10)

        search_inner = ctk.CTkFrame(search_frame, fg_color="transparent")
        search_inner.pack(side="right", fill="y", padx=15, pady=10)

        btn_clear = ctk.CTkButton(search_inner, text="🧹 مسح", font=(MAIN_FONT, 13, "bold"), fg_color="#64748B",
                                  hover_color="#475569", width=80, height=36, corner_radius=6,
                                  command=lambda: clear_search())
        btn_clear.pack(side="left", padx=(8, 12))

        btn_search = ctk.CTkButton(search_inner, text="🔍 بحث", font=(MAIN_FONT, 14, "bold"), fg_color=FIB_GREEN,
                                   hover_color="#004426", width=100, height=36, corner_radius=6,
                                   command=lambda: execute_search())
        btn_search.pack(side="left", padx=8)

        self.ent_leave_mov_file_no = ctk.CTkEntry(search_inner, font=(MAIN_FONT, 15, "bold"), justify="center",
                                                  placeholder_text="رقم الملف...", width=180, height=36,
                                                  border_color="#CBD5E1")
        self.ent_leave_mov_file_no.pack(side="left", padx=12)
        ctk.CTkLabel(search_inner, text="رقم الملف:", font=(MAIN_FONT, 14, "bold"), text_color=TEXT_DARK).pack(
            side="left", padx=(12, 4))

        # فريم النتائج الثابت (بدون سكرول للشاشة الرئيسية)
        self.leaves_mov_results_frame = ctk.CTkFrame(main_container, fg_color="transparent")
        self.leaves_mov_results_frame.pack(fill="both", expand=True, padx=15, pady=(0, 10))

        # =========================================
        # ⚙️ إعدادات الأحداث ودوال المساعدة
        # =========================================
        self.ent_leave_mov_file_no.bind("<Return>", lambda event: execute_search())

        def clear_search():
            self.ent_leave_mov_file_no.delete(0, 'end')
            for widget in self.leaves_mov_results_frame.winfo_children():
                widget.destroy()

        def safe_float(val):
            try:
                if pd.isna(val) or str(val).strip() == '': return 0.0
                return float(val)
            except (ValueError, TypeError):
                return 0.0

        def safe_str(val):
            if pd.isna(val): return "—"
            return str(val).strip()

        # =========================================
        # 🚀 تنفيذ الاستعلام فائق السرعة (Optimized Queries)
        # =========================================
        def execute_search():
            file_no = self.ent_leave_mov_file_no.get().strip()

            if not file_no:
                messagebox.showwarning("تنبيه", "يرجى إدخال رقم الملف")
                return

            for widget in self.leaves_mov_results_frame.winfo_children():
                widget.destroy()

            ctk.CTkLabel(self.leaves_mov_results_frame, text="⚡ جاري استعلام الملايين من السجلات بسرعة فائقة...",
                         font=(MAIN_FONT, 15, "bold"), text_color=FIB_GOLD).pack(pady=40)

            def fetch_data():
                try:
                    engine = getattr(self, '_get_db_connection', lambda: None)()
                    if not engine:
                        raise Exception("لا يوجد اتصال بقاعدة البيانات.")

                    # 1️⃣ استعلام الموظف (سريع جداً باستخدام TOP 1 مع NOLOCK)
                    query_info = """
                                 SELECT TOP 1 PNAME, PBR
                                 FROM [dbo].[TBL_annual_leaves] \
                                 WITH (NOLOCK)
                                 WHERE PDOC = ? \
                                 """
                    df_info = pd.read_sql(query_info, engine, params=(file_no,))

                    emp_name = "غير مدرج"
                    branch_name = "—"

                    if not df_info.empty:
                        first_row = df_info.iloc[0]
                        raw_name = str(first_row.get('PNAME', '')).strip()
                        if raw_name and raw_name != 'nan':
                            emp_name = raw_name
                            prefixes = ['عبد', 'ابو', 'أبو', 'ابن', 'بن', 'الدين', 'الله', 'جلال']
                            for p in prefixes:
                                emp_name = re.sub(rf'({p})([أ-ي])', r'\1 \2', emp_name)
                            emp_name = " ".join(emp_name.split())

                        pbr = str(first_row.get('PBR', '')).strip()
                        if pbr and pbr != 'nan':
                            query_branch = "SELECT branchname FROM [dbo].[tbl_branches] WITH (NOLOCK) WHERE branchcode = ?"
                            df_branch = pd.read_sql(query_branch, engine, params=(pbr,))
                            if not df_branch.empty:
                                branch_name = str(df_branch.iloc[0]['branchname']).strip()
                            else:
                                branch_name = pbr

                    emp_info = {
                        'name': emp_name,
                        'branch': branch_name
                    }

                    # 2️⃣ استعلام الحركات (معتمد على NOLOCK لتجنب الـ Blocking مع الـ 3 مليون ريكورد)
                    query_leaves = """
                                   SELECT HCOD,
                                          HDAT1,
                                          HDAT1E,
                                          HDAYNO,
                                          PTBNO,
                                          HMCOD
                                   FROM [dbo].[TBL_annual_leaves] \
                                   WITH (NOLOCK)
                                   WHERE HDOC = ?
                                   """
                    df_leaves = pd.read_sql(query_leaves, engine, params=(file_no,))

                    self.after(0, lambda d=emp_info, df=df_leaves, f=file_no: update_results_ui(d, df, f))
                except Exception as e:
                    err_msg = str(e)
                    logging.error(f"Error fetching leaves movement: {err_msg}")
                    self.after(0, lambda err=err_msg: update_results_ui(None, None, file_no, error=err))

            threading.Thread(target=fetch_data, daemon=True).start()

        # =========================================
        # 📑 عرض الواجهة المضغوطة (Compact View)
        # =========================================
        def update_results_ui(emp_info, df_leaves, file_no, error=None):
            for widget in self.leaves_mov_results_frame.winfo_children():
                widget.destroy()

            if error:
                ctk.CTkLabel(self.leaves_mov_results_frame, text=f"❌ {error}", font=(MAIN_FONT, 14, "bold"),
                             text_color="#EF4444").pack(pady=30)
                return

            if not emp_info:
                return

            # ==================== كارت معلومات الموظف (مصغر وأنيق) ====================
            header_card = ctk.CTkFrame(self.leaves_mov_results_frame, fg_color=CARD_BG, corner_radius=10,
                                       border_width=1, border_color="#CBD5E1", height=50)
            header_card.pack(fill="x", padx=10, pady=(0, 8))
            header_card.pack_propagate(False)

            top_row = ctk.CTkFrame(header_card, fg_color="transparent")
            top_row.pack(fill="both", expand=True, padx=20)

            ctk.CTkLabel(top_row, text=f"{emp_info['name']}", font=(MAIN_FONT, 16, "bold"), text_color=TEXT_DARK).pack(
                side="right", pady=10)
            ctk.CTkLabel(top_row, text="👤", font=(MAIN_FONT, 16)).pack(side="right", padx=(0, 6), pady=10)

            info_tags = ctk.CTkFrame(top_row, fg_color="transparent")
            info_tags.pack(side="left", pady=10)

            ctk.CTkLabel(info_tags, text=f"{file_no} :رقم الملف", font=(MAIN_FONT, 13, "bold"), text_color=FIB_GOLD,
                         fg_color=BOX_BG, corner_radius=6).pack(side="left", padx=6, ipadx=10, ipady=3)
            ctk.CTkLabel(info_tags, text=f"الفرع: {emp_info['branch']}", font=(MAIN_FONT, 13, "bold"),
                         text_color=TEXT_MUTED, fg_color=BOX_BG, corner_radius=6).pack(side="left", padx=6, ipadx=10,
                                                                                       ipady=3)

            # ==================== جدول حركات الإجازات (مضغوط وفي شاشة واحدة) ====================
            table_container = ctk.CTkFrame(self.leaves_mov_results_frame, fg_color=CARD_BG, corner_radius=10,
                                           border_width=1, border_color="#E2E8F0")
            table_container.pack(fill="both", expand=True, padx=10, pady=(0, 5))

            record_count = len(df_leaves) if df_leaves is not None else 0
            ctk.CTkLabel(table_container, text=f"🗓️ سجل حركات الإجازات ({record_count})",
                         font=(MAIN_FONT, 14, "bold"), text_color=FIB_GREEN).pack(anchor="e", padx=15, pady=6)

            # 1. رأس الجدول (Header مصغر)
            header_row = ctk.CTkFrame(table_container, fg_color=FIB_GREEN, corner_radius=4, height=36)
            header_row.pack(fill="x", padx=8, pady=(0, 4))
            header_row.pack_propagate(False)

            columns = ["كود المسجل", "تاريخ بدل راحة", "عدد الأيام", "نهاية الإجازة", "بداية الإجازة", "نوع الإجازة"]
            for i, col_name in enumerate(columns):
                header_row.grid_columnconfigure(i, weight=1, uniform="col")
                ctk.CTkLabel(header_row, text=col_name, font=(MAIN_FONT, 12, "bold"), text_color=CARD_BG).grid(row=0,
                                                                                                               column=i,
                                                                                                               pady=6)

            # 2. جسم الجدول الداخلي
            table_body = ctk.CTkScrollableFrame(table_container, fg_color="transparent")
            table_body.pack(fill="both", expand=True, padx=4, pady=4)

            if df_leaves is None or df_leaves.empty:
                ctk.CTkLabel(table_body, text="✔️ لا توجد حركات إجازات مسجلة بهذا الكود.", font=(MAIN_FONT, 13),
                             text_color=TEXT_MUTED).pack(pady=20)
                return

            def format_date(val):
                if pd.isna(val) or str(val).strip() == '': return "—"
                try:
                    return pd.to_datetime(val).strftime('%Y-%m-%d')
                except:
                    return str(val)

            for index, row in df_leaves.iterrows():
                row_color = BOX_BG if index % 2 == 0 else CARD_BG

                row_frame = ctk.CTkFrame(table_body, fg_color=row_color, corner_radius=4, height=34)
                row_frame.pack(fill="x", pady=1)
                row_frame.pack_propagate(False)

                hcod = safe_str(row.get('HCOD'))
                hdat1 = format_date(row.get('HDAT1'))
                hdat1e = format_date(row.get('HDAT1E'))
                hdayno = safe_float(row.get('HDAYNO'))
                ptbno = format_date(row.get('PTBNO'))
                hmcod = safe_str(row.get('HMCOD'))

                values_and_colors = [
                    (hmcod, TEXT_MUTED),
                    (ptbno, TEXT_DARK),
                    (f"{hdayno:g}", "#0369A1" if hdayno > 0 else TEXT_MUTED),
                    (hdat1e, "#DC2626"),
                    (hdat1, FIB_GREEN),
                    (hcod, TEXT_DARK)
                ]

                for i, (val, color) in enumerate(values_and_colors):
                    row_frame.grid_columnconfigure(i, weight=1, uniform="col")
                    ctk.CTkLabel(row_frame, text=val, font=(MAIN_FONT, 12, "bold"), text_color=color).grid(row=0,
                                                                                                           column=i,
                                                                                                           pady=6)
