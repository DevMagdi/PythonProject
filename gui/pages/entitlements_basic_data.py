# -*- coding: utf-8 -*-
"""
شاشة الاستحقاقات - البيانات الأساسية للموظفين.

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


class EntitlementsBasicDataPage(LegacyInquiryPage):
    """شاشة الاستحقاقات - البيانات الأساسية للموظفين."""
    LOAD_BRANCHES_ON_SHOW = False

    def build(self):
        """بناء الشاشة — الكود القديم كما هو (parent = الشاشة نفسها)."""
        parent = self
        # =========================================
        # 🎨 الألوان والتنسيقات المعتمدة (Premium Grid)
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
            header, text="الاستحقاقات - البيانات الأساسية للموظفين 📋",
            font=(MAIN_FONT, 20, "bold"), text_color=CARD_BG
        ).pack(side="right", padx=25, pady=12)

        # =========================================
        # 🔍 منطقة البحث
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

        self.ent_basic_data_file_no = ctk.CTkEntry(search_inner, font=(MAIN_FONT, 15, "bold"), justify="center",
                                                   placeholder_text="رقم الملف...", width=180, height=36,
                                                   border_color="#CBD5E1")
        self.ent_basic_data_file_no.pack(side="left", padx=12)
        ctk.CTkLabel(search_inner, text="رقم الملف:", font=(MAIN_FONT, 14, "bold"), text_color=TEXT_DARK).pack(
            side="left", padx=(12, 4))

        # فريم النتائج الثابت (بدون سكرول)
        self.basic_data_results_frame = ctk.CTkFrame(main_container, fg_color="transparent")
        self.basic_data_results_frame.pack(fill="both", expand=True, padx=15, pady=(0, 10))

        # =========================================
        # ⚙️ إعدادات الأحداث ودوال المساعدة (محدثة لضمان عرض الداتا)
        # =========================================
        self.ent_basic_data_file_no.bind("<Return>", lambda event: execute_search())

        def clear_search():
            self.ent_basic_data_file_no.delete(0, 'end')
            for widget in self.basic_data_results_frame.winfo_children():
                widget.destroy()

        def safe_str(val):
            if pd.isna(val): return "—"
            val_str = str(val).strip()
            if val_str.lower() in ['', 'nan', 'none', 'nat']: return "—"
            try:
                if float(val).is_integer():
                    return str(int(float(val)))
            except:
                pass
            return val_str

        def format_date(val):
            if pd.isna(val): return "—"
            val_str = str(val).strip()
            if val_str.lower() in ['', 'nan', 'none', 'nat']: return "—"
            try:
                return pd.to_datetime(val).strftime('%Y-%m-%d')
            except:
                return val_str

        # =========================================
        # 🚀 تنفيذ الاستعلام فائق السرعة
        # =========================================
        def execute_search():
            file_no = self.ent_basic_data_file_no.get().strip()

            if not file_no:
                messagebox.showwarning("تنبيه", "يرجى إدخال رقم الملف")
                return

            for widget in self.basic_data_results_frame.winfo_children():
                widget.destroy()

            ctk.CTkLabel(self.basic_data_results_frame, text="⚡ جاري جلب البيانات الأساسية...",
                         font=(MAIN_FONT, 15, "bold"), text_color=FIB_GOLD).pack(pady=40)

            def fetch_data():
                try:
                    engine = getattr(self, '_get_db_connection', lambda: None)()
                    if not engine:
                        raise Exception("لا يوجد اتصال بقاعدة البيانات.")

                    # الاستعلام مبني على TOP 1 و NOLOCK للسرعة القصوى
                    query = """
                            SELECT TOP 1 
                            PNAME, PBR, \
                                   PADM, \
                                   PJOB, \
                                   PCOD, \
                                   PCLNT, \
                                   PDATH, \
                                   PDATM1,
                                   PCOD1, \
                                   PDATMM, \
                                   PBAH1, \
                                   PDAT1, \
                                   PBAH2, \
                                   PDAT2,
                                   PCOD2, \
                                   PCOD3, \
                                   PCOD4, \
                                   PDAY
                            FROM [dbo].[TBL_Entitlements] \
                            WITH (NOLOCK)
                            WHERE PDOC = ? \
                            """
                    df_data = pd.read_sql(query, engine, params=(file_no,))

                    if df_data.empty:
                        self.after(0, lambda: update_results_ui(None, file_no,
                                                                error="لم يتم العثور على بيانات لرقم الملف المدخل."))
                        return

                    row = df_data.iloc[0]

                    # 🛠️ معالجة الاسم وتنظيفه
                    raw_name = str(row.get('PNAME', '')).strip()
                    if raw_name.lower() in ['nan', '', 'none']:
                        emp_name = "غير مدرج"
                    else:
                        emp_name = raw_name
                        prefixes = ['عبد', 'ابو', 'أبو', 'ابن', 'بن', 'الدين', 'الله', 'جلال']
                        for p in prefixes:
                            emp_name = re.sub(rf'({p})([أ-ي])', r'\1 \2', emp_name)
                        emp_name = " ".join(emp_name.split())

                    # 🛠️ مطابقة الفرع
                    pbr = str(row.get('PBR', '')).strip()
                    branch_name = pbr
                    if pbr and pbr.lower() not in ['nan', 'none', '']:
                        query_branch = "SELECT branchname FROM [dbo].[tbl_branches] WITH (NOLOCK) WHERE branchcode = ?"
                        df_branch = pd.read_sql(query_branch, engine, params=(pbr,))
                        if not df_branch.empty:
                            branch_name = str(df_branch.iloc[0]['branchname']).strip()

                    emp_data = {
                        'name': emp_name,
                        'branch': branch_name,
                        'PADM': safe_str(row.get('PADM')),
                        'PJOB': safe_str(row.get('PJOB')),
                        'PCOD': safe_str(row.get('PCOD')),
                        'PCLNT': safe_str(row.get('PCLNT')),
                        'PDATH': safe_str(row.get('PDATH')),
                        'PDATM1': format_date(row.get('PDATM1')),
                        'PCOD1': safe_str(row.get('PCOD1')),
                        'PDATMM': format_date(row.get('PDATMM')),
                        'PBAH1': safe_str(row.get('PBAH1')),
                        'PDAT1': safe_str(row.get('PDAT1')),
                        'PBAH2': safe_str(row.get('PBAH2')),
                        'PDAT2': safe_str(row.get('PDAT2')),
                        'PCOD2': safe_str(row.get('PCOD2')),
                        'PCOD3': safe_str(row.get('PCOD3')),
                        'PCOD4': safe_str(row.get('PCOD4')),
                        'PDAY': safe_str(row.get('PDAY'))
                    }

                    self.after(0, lambda d=emp_data, f=file_no: update_results_ui(d, f))
                except Exception as e:
                    err_msg = str(e)
                    logging.error(f"Error fetching basic data: {err_msg}")
                    self.after(0, lambda err=err_msg: update_results_ui(None, file_no, error=err))

            threading.Thread(target=fetch_data, daemon=True).start()

        # =========================================
        # 📑 عرض الواجهة (باستخدام نظام Grid الهندسي الجديد)
        # =========================================
        def update_results_ui(emp_data, file_no, error=None):
            for widget in self.basic_data_results_frame.winfo_children():
                widget.destroy()

            if error:
                ctk.CTkLabel(self.basic_data_results_frame, text=f"❌ {error}", font=(MAIN_FONT, 14, "bold"),
                             text_color="#EF4444").pack(pady=30)
                return

            if not emp_data:
                return

            # ==================== كارت معلومات الموظف ====================
            header_card = ctk.CTkFrame(self.basic_data_results_frame, fg_color=CARD_BG, corner_radius=10,
                                       border_width=1, border_color="#CBD5E1", height=60)
            header_card.pack(fill="x", padx=10, pady=(0, 10))
            header_card.pack_propagate(False)

            top_row = ctk.CTkFrame(header_card, fg_color="transparent")
            top_row.pack(fill="both", expand=True, padx=20)

            ctk.CTkLabel(top_row, text=f"{emp_data['name']}", font=(MAIN_FONT, 17, "bold"), text_color=TEXT_DARK).pack(
                side="right", pady=15)
            ctk.CTkLabel(top_row, text="👤", font=(MAIN_FONT, 16)).pack(side="right", padx=(0, 6), pady=15)

            info_tags = ctk.CTkFrame(top_row, fg_color="transparent")
            info_tags.pack(side="left", pady=15)

            ctk.CTkLabel(info_tags, text=f"{file_no} :رقم الملف", font=(MAIN_FONT, 13, "bold"), text_color=FIB_GOLD,
                         fg_color=BOX_BG, corner_radius=6).pack(side="left", padx=6, ipadx=10, ipady=3)
            ctk.CTkLabel(info_tags, text=f"الفرع: {emp_data['branch']}", font=(MAIN_FONT, 13, "bold"),
                         text_color=TEXT_MUTED, fg_color=BOX_BG, corner_radius=6).pack(side="left", padx=6, ipadx=10,
                                                                                       ipady=3)

            # ==================== شبكة البيانات (نظام Grid لمنع قطع الشاشة) ====================
            grid_container = ctk.CTkFrame(self.basic_data_results_frame, fg_color="transparent")
            grid_container.pack(fill="both", expand=True, padx=5, pady=0)

            # تهيئة الـ Grid ليكون 4 صفوف و 4 أعمدة بحجم متساوي تماماً
            for i in range(4):
                grid_container.grid_rowconfigure(i, weight=1, uniform="row")
                grid_container.grid_columnconfigure(i, weight=1, uniform="col")

            # مصفوفة الحقول (4 صفوف × 4 أعمدة) - الترتيب من اليمين لليسار برمجياً
            fields_layout = [
                [("الإدارة", emp_data['PADM']), ("مستوى وظيفي جديد", emp_data['PJOB']),
                 ("كود الوظيفة", emp_data['PCOD']), ("رقم الحساب", emp_data['PCLNT'])],
                [("تاريخ الميلاد", emp_data['PDATMM']), ("ت. التعيين - هجري", emp_data['PDATH']),
                 ("الحالة الاجتماعية", emp_data['PCOD1']), ("المدة الاعتبارية", emp_data['PDAY'])],
                [("المؤهل الدراسي 1", emp_data['PBAH1']), ("سنة الحصول عليه", emp_data['PDAT1']),
                 ("المؤهل الدراسي 2", emp_data['PBAH2']), ("سنة الحصول عليه", emp_data['PDAT2'])],
                [("ت. اشتراك ن/خ - م", emp_data['PDATM1']), ("كود اشتراك ن/خ", emp_data['PCOD2']),
                 ("كود اشتراك نقابة", emp_data['PCOD3']), ("كود استثناء حد/ق", emp_data['PCOD4'])]
            ]

            # رسم الشبكة بانتظام تام
            for r_idx, row_data in enumerate(fields_layout):
                for c_idx, (title, val) in enumerate(row_data):
                    # لحساب العمود الصحيح من اليمين لليسار (RTL Layout)
                    actual_col = 3 - c_idx

                    box = ctk.CTkFrame(grid_container, fg_color=CARD_BG, corner_radius=10, border_width=1,
                                       border_color="#E2E8F0")
                    box.grid(row=r_idx, column=actual_col, sticky="nsew", padx=5, pady=5)

                    # حاوية داخلية لضمان توسيط النصوص مهما كان حجم الشاشة
                    inner_box = ctk.CTkFrame(box, fg_color="transparent")
                    inner_box.pack(expand=True)

                    ctk.CTkLabel(inner_box, text=title, font=(MAIN_FONT, 12, "bold"), text_color=TEXT_MUTED).pack(
                        pady=(0, 4))
                    ctk.CTkLabel(inner_box, text=val, font=(MAIN_FONT, 16, "bold"), text_color=TEXT_DARK).pack(
                        pady=(4, 0))
