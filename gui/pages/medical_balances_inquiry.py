# -*- coding: utf-8 -*-
"""
شاشة الاستفسار عن أرصدة العلاج الطبي للموظفين.

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


class MedicalBalancesInquiryPage(LegacyInquiryPage):
    """شاشة الاستفسار عن أرصدة العلاج الطبي للموظفين."""
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

        main_container = ctk.CTkFrame(parent, fg_color=BG_MAIN)
        main_container.pack(fill="both", expand=True)

        header = ctk.CTkFrame(main_container, fg_color=FIB_GREEN, height=65, corner_radius=0)
        header.pack(fill="x")
        header.pack_propagate(False)

        ctk.CTkFrame(main_container, fg_color=FIB_GOLD, height=4, corner_radius=0).pack(fill="x")

        ctk.CTkLabel(
            header, text="الاستفسار عن أرصدة العلاج الطبي للموظفين 🏥",
            font=("Segoe UI", 22, "bold"), text_color=CARD_BG
        ).pack(side="right", padx=30, pady=15)

        # =========================================
        # 🔍 منطقة البحث (رقم الملف فقط)
        # =========================================
        search_frame = ctk.CTkFrame(main_container, fg_color=CARD_BG, corner_radius=15, border_width=1,
                                    border_color="#E2E8F0")
        search_frame.pack(fill="x", padx=20, pady=15)

        search_inner = ctk.CTkFrame(search_frame, fg_color="transparent")
        search_inner.pack(side="right", fill="y", padx=20, pady=15)

        btn_clear = ctk.CTkButton(search_inner, text="🧹 مسح", font=("Segoe UI", 14, "bold"), fg_color="#64748B",
                                  hover_color="#475569", width=80, height=40, corner_radius=8,
                                  command=lambda: clear_search())
        btn_clear.pack(side="left", padx=(5, 10))

        btn_search = ctk.CTkButton(search_inner, text="🔍 بحث", font=("Segoe UI", 15, "bold"), fg_color=FIB_GREEN,
                                   hover_color="#004426", width=100, height=40, corner_radius=8,
                                   command=lambda: execute_search())
        btn_search.pack(side="left", padx=5)

        self.ent_med_file_no = ctk.CTkEntry(search_inner, font=("Segoe UI", 15, "bold"), justify="center",
                                            placeholder_text="رقم الملف...", width=200, height=40,
                                            border_color="#CBD5E1")
        self.ent_med_file_no.pack(side="left", padx=10)
        ctk.CTkLabel(search_inner, text="رقم الملف:", font=("Segoe UI", 14, "bold"), text_color=TEXT_DARK).pack(
            side="left", padx=(10, 2))

        self.med_results_scroll = ctk.CTkScrollableFrame(main_container, fg_color="transparent")
        self.med_results_scroll.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        # =========================================
        # ⚙️ إعدادات الأحداث
        # =========================================
        self.ent_med_file_no.bind("<Return>", lambda event: execute_search())

        def clear_search():
            self.ent_med_file_no.delete(0, 'end')
            for widget in self.med_results_scroll.winfo_children():
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
            file_no = self.ent_med_file_no.get().strip()

            if not file_no:
                messagebox.showwarning("تنبيه", "يرجى إدخال رقم الملف")
                return

            for widget in self.med_results_scroll.winfo_children():
                widget.destroy()

            ctk.CTkLabel(self.med_results_scroll, text="⚡ جاري جلب بيانات العلاج الطبي...",
                         font=("Segoe UI", 16, "bold"), text_color=FIB_GOLD).pack(pady=50)

            def fetch_data():
                try:
                    engine = getattr(self, '_get_db_connection', lambda: None)()
                    if not engine:
                        raise Exception("لا يوجد اتصال بقاعدة البيانات.")

                    # الاستعلام مبني على رقم الملف (PDOC)
                    query = """
                            SELECT Pname, \
                                   PTAMT2, \
                                   PTAMT1, \
                                   PEAMT4, \
                                   PEAMT2, \
                                   PEAMT, \
                                   PEAMTB
                            FROM [dbo].[TBL_medical_treatment] \
                            WITH (NOLOCK)
                            WHERE PDOC = ? \
                            """
                    df = pd.read_sql(query, engine, params=(file_no,))

                    self.after(0, lambda d=df, f=file_no: update_results_ui(d, f))
                except Exception as e:
                    err_msg = str(e)
                    logging.error(f"Error fetching medical data: {err_msg}")
                    self.after(0, lambda err=err_msg: update_results_ui(pd.DataFrame(), file_no, error=err))

            threading.Thread(target=fetch_data, daemon=True).start()

        # =========================================
        # 📑 عرض الواجهة الإحصائية للنتائج
        # =========================================
        def update_results_ui(df, file_no, error=None):
            for widget in self.med_results_scroll.winfo_children():
                widget.destroy()

            if error:
                ctk.CTkLabel(self.med_results_scroll, text=f"❌ حدث خطأ أثناء الاستعلام:\n{error}",
                             font=("Segoe UI", 14, "bold"), text_color="#EF4444").pack(pady=40)
                return

            if df.empty:
                ctk.CTkLabel(self.med_results_scroll, text="✔️ لا توجد بيانات علاج مسجلة لرقم الملف المدخل.",
                             font=("Segoe UI", 18, "bold"), text_color=TEXT_MUTED).pack(pady=60)
                return

            # أخذ السجل الأول (بافتراض أن رقم الملف فريد للموظف)
            row = df.iloc[0]
            emp_name = row.get('Pname', 'غير مدرج')
            if pd.isna(emp_name) or str(emp_name).strip() == "":
                emp_name = "غير مدرج"

            # ==================== كارت معلومات الموظف ====================
            header_card = ctk.CTkFrame(self.med_results_scroll, fg_color=CARD_BG, corner_radius=12, border_width=1,
                                       border_color="#CBD5E1")
            header_card.pack(fill="x", padx=10, pady=(5, 10))

            top_row = ctk.CTkFrame(header_card, fg_color="transparent")
            top_row.pack(fill="x", padx=20, pady=15)

            ctk.CTkLabel(top_row, text=f"👤 اسم الموظف: {emp_name}", font=("Segoe UI", 18, "bold"),
                         text_color=TEXT_DARK).pack(side="right")

            info_tags = ctk.CTkFrame(top_row, fg_color="transparent")
            info_tags.pack(side="left")
            ctk.CTkLabel(info_tags, text=f"رقم الملف: {file_no}", font=("Segoe UI", 14, "bold"), text_color=FIB_GOLD,
                         fg_color=BOX_BG, corner_radius=6).pack(side="left", padx=4, ipadx=8, ipady=3)

            # ==================== كروت تفاصيل الأرصدة والمصاريف ====================
            details_card = ctk.CTkFrame(self.med_results_scroll, fg_color=CARD_BG, corner_radius=12, border_width=1,
                                        border_color="#E2E8F0")
            details_card.pack(fill="x", padx=10, pady=10)

            card_title = ctk.CTkFrame(details_card, fg_color="transparent")
            card_title.pack(fill="x", padx=15, pady=(15, 5))
            ctk.CTkLabel(card_title, text="💰 تفاصيل ومصاريف العلاج", font=("Segoe UI", 16, "bold"),
                         text_color=FIB_GREEN).pack(side="right")
            ctk.CTkFrame(details_card, fg_color="#F1F5F9", height=2).pack(fill="x", padx=15, pady=5)

            def create_stat_box(parent, title, value_str, v_color=TEXT_DARK):
                box = ctk.CTkFrame(parent, fg_color=BOX_BG, corner_radius=8)
                box.pack(side="right", fill="both", expand=True, padx=6, pady=5)
                ctk.CTkLabel(box, text=title, font=("Segoe UI", 13, "bold"), text_color=TEXT_MUTED).pack(
                    anchor="center", pady=(10, 2))
                ctk.CTkLabel(box, text=value_str, font=("Segoe UI", 16, "bold"), text_color=v_color).pack(
                    anchor="center", pady=(0, 10))

            # --- الصف الأول: مصاريف الموظف ---
            row1 = ctk.CTkFrame(details_card, fg_color="transparent")
            row1.pack(fill="x", padx=15, pady=5)

            ptamt2 = safe_float(row.get('PTAMT2'))
            ptamt1 = safe_float(row.get('PTAMT1'))

            create_stat_box(row1, "إجمالي مصاريف علاج الموظف (PTAMT1)", f"{ptamt1:,.2f}", FIB_GREEN)
            create_stat_box(row1, "مصاريف علاج الموظف السنوية (PTAMT2)", f"{ptamt2:,.2f}", TEXT_DARK)

            # --- الصف الثاني: مصاريف العمليات الأسرية ---
            row2 = ctk.CTkFrame(details_card, fg_color="transparent")
            row2.pack(fill="x", padx=15, pady=5)

            peamt2 = safe_float(row.get('PEAMT2'))
            peamt4 = safe_float(row.get('PEAMT4'))

            create_stat_box(row2, "إجمالي مصاريف عمليات أسرية (PEAMT2)", f"{peamt2:,.2f}", FIB_GOLD)
            create_stat_box(row2, "مصاريف عمليات أسرية سنوية (PEAMT4)", f"{peamt4:,.2f}", TEXT_DARK)

            # --- الصف الثالث: العلاج الأسري والباقي ---
            row3 = ctk.CTkFrame(details_card, fg_color="transparent")
            row3.pack(fill="x", padx=15, pady=(5, 15))

            peamt = safe_float(row.get('PEAMT'))
            peamtb = safe_float(row.get('PEAMTB'))

            # حساب الباقي (طرح PEAMT من PEAMTB)
            remaining = peamt - peamtb

            create_stat_box(row3, "مبلغ العلاج الأسري (PEAMT)", f"{peamt:,.2f}", TEXT_DARK)
            create_stat_box(row3, "رصيد العلاج الأسري (PEAMTB)", f"{peamtb:,.2f}", TEXT_DARK)
            create_stat_box(row3, "الباقي", f"{remaining:,.2f} دائن", "#DC2626")  # تم إضافة كلمة "دائن" هنا
