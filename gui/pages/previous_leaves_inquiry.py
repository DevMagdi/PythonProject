# -*- coding: utf-8 -*-
"""
شاشة الاستفسار عن إجازات الموظف السابقة.

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


class PreviousLeavesInquiryPage(LegacyInquiryPage):
    """شاشة الاستفسار عن إجازات الموظف السابقة."""
    LOAD_BRANCHES_ON_SHOW = False

    def build(self):
        """بناء الشاشة — الكود القديم كما هو (parent = الشاشة نفسها)."""
        parent = self

        # =========================================
        # 🎨 الألوان والتنسيقات المعتمدة
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

        header = ctk.CTkFrame(main_container, fg_color=FIB_GREEN, height=65, corner_radius=0)
        header.pack(fill="x")
        header.pack_propagate(False)

        ctk.CTkFrame(main_container, fg_color=FIB_GOLD, height=4, corner_radius=0).pack(fill="x")

        ctk.CTkLabel(
            header, text="الاستفسار عن إجازات الموظف السابقة 🏖️",
            font=(MAIN_FONT, 22, "bold"), text_color=CARD_BG
        ).pack(side="right", padx=30, pady=15)

        # =========================================
        # 🔍 منطقة البحث (رقم الملف فقط)
        # =========================================
        search_frame = ctk.CTkFrame(main_container, fg_color=CARD_BG, corner_radius=15, border_width=1,
                                    border_color="#E2E8F0")
        # تقليل الـ pady هنا عشان نوفر مساحة للشاشة
        search_frame.pack(fill="x", padx=25, pady=15)

        search_inner = ctk.CTkFrame(search_frame, fg_color="transparent")
        search_inner.pack(side="right", fill="y", padx=25, pady=15)

        btn_clear = ctk.CTkButton(search_inner, text="🧹 مسح", font=(MAIN_FONT, 14, "bold"), fg_color="#64748B",
                                  hover_color="#475569", width=90, height=45, corner_radius=8,
                                  command=lambda: clear_search())
        btn_clear.pack(side="left", padx=(10, 15))

        btn_search = ctk.CTkButton(search_inner, text="🔍 بحث", font=(MAIN_FONT, 15, "bold"), fg_color=FIB_GREEN,
                                   hover_color="#004426", width=110, height=45, corner_radius=8,
                                   command=lambda: execute_search())
        btn_search.pack(side="left", padx=10)

        self.ent_leave_file_no = ctk.CTkEntry(search_inner, font=(MAIN_FONT, 16, "bold"), justify="center",
                                              placeholder_text="رقم الملف...", width=220, height=45,
                                              border_color="#CBD5E1")
        self.ent_leave_file_no.pack(side="left", padx=15)
        ctk.CTkLabel(search_inner, text="رقم الملف:", font=(MAIN_FONT, 15, "bold"), text_color=TEXT_DARK).pack(
            side="left", padx=(15, 5))

        # 🚀 التعديل الجذري: استخدام CTkFrame العادي بدلاً من CTkScrollableFrame لإلغاء السكرول تماماً
        self.leave_results_frame = ctk.CTkFrame(main_container, fg_color="transparent")
        self.leave_results_frame.pack(fill="both", expand=True, padx=20, pady=(0, 15))

        # =========================================
        # ⚙️ إعدادات الأحداث ودوال المساعدة
        # =========================================
        self.ent_leave_file_no.bind("<Return>", lambda event: execute_search())

        def clear_search():
            self.ent_leave_file_no.delete(0, 'end')
            for widget in self.leave_results_frame.winfo_children():
                widget.destroy()

        def safe_float(val):
            try:
                if pd.isna(val) or str(val).strip() == '':
                    return 0.0
                return float(val)
            except (ValueError, TypeError):
                return 0.0

        # =========================================
        # 🚀 تنفيذ الاستعلام وجلب البيانات
        # =========================================
        def execute_search():
            file_no = self.ent_leave_file_no.get().strip()

            if not file_no:
                messagebox.showwarning("تنبيه", "يرجى إدخال رقم الملف")
                return

            for widget in self.leave_results_frame.winfo_children():
                widget.destroy()

            ctk.CTkLabel(self.leave_results_frame, text="⚡ جاري جلب بيانات الإجازات...", font=(MAIN_FONT, 16, "bold"),
                         text_color=FIB_GOLD).pack(pady=60)

            def fetch_data():
                try:
                    engine = getattr(self, '_get_db_connection', lambda: None)()
                    if not engine:
                        raise Exception("لا يوجد اتصال بقاعدة البيانات.")

                    # 1️⃣ الاستعلام الأول
                    query_leaves = """
                                   SELECT PNAME, \
                                          PBR, \
                                          PBALS2, \
                                          PBALS1, \
                                          PBALA, \
                                          PTMNO, \
                                          PTBNO, \
                                          PTENO
                                   FROM [dbo].[TBL_annual_leaves] \
                                   WITH (NOLOCK)
                                   WHERE PDOC = ? \
                                   """
                    df_leaves = pd.read_sql(query_leaves, engine, params=(file_no,))

                    if df_leaves.empty:
                        self.after(0, lambda: update_results_ui(None, file_no,
                                                                error="لم يتم العثور على بيانات إجازات لرقم الملف المدخل."))
                        return

                    row = df_leaves.iloc[0]

                    emp_name = str(row.get('PNAME', 'غير مدرج')).strip()
                    if emp_name == 'nan' or emp_name == '':
                        emp_name = "غير مدرج"
                    else:
                        prefixes = ['عبد', 'ابو', 'أبو', 'ابن', 'بن', 'الدين', 'الله', 'جلال']
                        for p in prefixes:
                            emp_name = re.sub(rf'({p})([أ-ي])', r'\1 \2', emp_name)
                        emp_name = " ".join(emp_name.split())

                    pbr = str(row.get('PBR', '')).strip()

                    # 2️⃣ مطابقة الفرع
                    branch_name = pbr
                    if pbr and pbr != 'nan':
                        query_branch = "SELECT branchname FROM [dbo].[tbl_branches] WITH (NOLOCK) WHERE branchcode = ?"
                        df_branch = pd.read_sql(query_branch, engine, params=(pbr,))
                        if not df_branch.empty:
                            branch_name = str(df_branch.iloc[0]['branchname']).strip()

                    emp_data = {
                        'name': emp_name,
                        'branch': branch_name,
                        'pbals2': safe_float(row.get('PBALS2')),
                        'pbals1': safe_float(row.get('PBALS1')),
                        'pbala': safe_float(row.get('PBALA')),
                        'ptmno': safe_float(row.get('PTMNO')),
                        'ptbno': safe_float(row.get('PTBNO')),
                        'pteno': safe_float(row.get('PTENO'))
                    }

                    self.after(0, lambda d=emp_data, f=file_no: update_results_ui(d, f))
                except Exception as e:
                    err_msg = str(e)
                    logging.error(f"Error fetching leaves data: {err_msg}")
                    self.after(0, lambda err=err_msg: update_results_ui(None, file_no, error=err))

            threading.Thread(target=fetch_data, daemon=True).start()

        # =========================================
        # 📑 عرض الواجهة الإحصائية للنتائج (بدون سكرول)
        # =========================================
        def update_results_ui(emp_data, file_no, error=None):
            for widget in self.leave_results_frame.winfo_children():
                widget.destroy()

            if error:
                ctk.CTkLabel(self.leave_results_frame, text=f"❌ {error}", font=(MAIN_FONT, 16, "bold"),
                             text_color="#EF4444").pack(pady=50)
                return

            if not emp_data:
                return

            # ==================== كارت معلومات الموظف ====================
            header_card = ctk.CTkFrame(self.leave_results_frame, fg_color=CARD_BG, corner_radius=15, border_width=1,
                                       border_color="#CBD5E1")
            header_card.pack(fill="x", padx=15, pady=(5, 15))

            top_row = ctk.CTkFrame(header_card, fg_color="transparent")
            top_row.pack(fill="x", padx=30, pady=15)

            ctk.CTkLabel(top_row, text=f"{emp_data['name']}", font=(MAIN_FONT, 20, "bold"), text_color=TEXT_DARK).pack(
                side="right")
            ctk.CTkLabel(top_row, text="👤", font=(MAIN_FONT, 20)).pack(side="right", padx=(0, 8))

            info_tags = ctk.CTkFrame(top_row, fg_color="transparent")
            info_tags.pack(side="left")

            ctk.CTkLabel(info_tags, text=f"{file_no} :رقم الملف", font=(MAIN_FONT, 15, "bold"), text_color=FIB_GOLD,
                         fg_color=BOX_BG, corner_radius=8).pack(side="left", padx=8, ipadx=15, ipady=6)
            ctk.CTkLabel(info_tags, text=f"الفرع: {emp_data['branch']}", font=(MAIN_FONT, 15, "bold"),
                         text_color=TEXT_MUTED, fg_color=BOX_BG, corner_radius=8).pack(side="left", padx=8, ipadx=15,
                                                                                       ipady=6)

            # ==================== كروت تفاصيل الأرصدة ====================
            details_card = ctk.CTkFrame(self.leave_results_frame, fg_color=CARD_BG, corner_radius=15, border_width=1,
                                        border_color="#E2E8F0")
            details_card.pack(fill="both", expand=True, padx=15, pady=(0, 10))

            card_title = ctk.CTkFrame(details_card, fg_color="transparent")
            card_title.pack(fill="x", padx=25, pady=(15, 5))
            ctk.CTkLabel(card_title, text="📊 تفاصيل أرصدة الإجازات السابقة", font=(MAIN_FONT, 18, "bold"),
                         text_color=FIB_GREEN).pack(side="right")
            ctk.CTkFrame(details_card, fg_color="#F1F5F9", height=2).pack(fill="x", padx=25, pady=5)

            def create_stat_box(parent, title, value_str, v_color=TEXT_DARK):
                box = ctk.CTkFrame(parent, fg_color=BOX_BG, corner_radius=12)
                box.pack(side="right", fill="both", expand=True, padx=12, pady=10)
                ctk.CTkLabel(box, text=title, font=(MAIN_FONT, 14, "bold"), text_color=TEXT_MUTED).pack(anchor="center",
                                                                                                        pady=(15, 5))
                ctk.CTkLabel(box, text=value_str, font=(MAIN_FONT, 20, "bold"), text_color=v_color).pack(
                    anchor="center", pady=(5, 15))

            # --- الصف الأول ---
            row1 = ctk.CTkFrame(details_card, fg_color="transparent")
            row1.pack(fill="both", expand=True, padx=20, pady=5)

            create_stat_box(row1, "رصيد إجازة سنوي (PBALS2)", f"{emp_data['pbals2']:g} يوم", FIB_GREEN)
            create_stat_box(row1, "رصيد مرحل سنوي (PBALS1)", f"{emp_data['pbals1']:g} يوم", FIB_GOLD)
            create_stat_box(row1, "رصيد إجازات عارضة (PBALA)", f"{emp_data['pbala']:g} يوم", TEXT_DARK)

            # --- الصف الثاني ---
            row2 = ctk.CTkFrame(details_card, fg_color="transparent")
            row2.pack(fill="both", expand=True, padx=20, pady=(5, 15))

            create_stat_box(row2, "إجمالي إجازة مرضي (PTMNO)", f"{emp_data['ptmno']:g} يوم", "#0369A1")
            create_stat_box(row2, "إجمالي بدون مرتب (PTBNO)", f"{emp_data['ptbno']:g} يوم", "#DC2626")
            create_stat_box(row2, "إجمالي إجازة إيقاف (PTENO)", f"{emp_data['pteno']:g} يوم", TEXT_MUTED)
