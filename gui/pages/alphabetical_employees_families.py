# -*- coding: utf-8 -*-
"""
شاشة الاستفسار الأبجدي عن الموظفين وأسرهم.

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


class AlphabeticalEmployeesFamiliesPage(LegacyInquiryPage):
    """شاشة الاستفسار الأبجدي عن الموظفين وأسرهم."""
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
            header, text="الاستفسار الأبجدي عن الموظفين وأسرهم 👨‍👩‍👧‍👦",
            font=("Segoe UI", 22, "bold"), text_color=CARD_BG
        ).pack(side="right", padx=30, pady=15)

        # =========================================
        # 🔍 منطقة البحث (الاسم فقط)
        # =========================================
        search_frame = ctk.CTkFrame(main_container, fg_color=CARD_BG, corner_radius=15, border_width=1,
                                    border_color="#E2E8F0")
        search_frame.pack(fill="x", padx=20, pady=15)

        search_inner = ctk.CTkFrame(search_frame, fg_color="transparent")
        search_inner.pack(side="right", fill="y", padx=20, pady=15)

        # الأزرار
        btn_clear = ctk.CTkButton(search_inner, text="🧹 مسح", font=("Segoe UI", 14, "bold"), fg_color="#64748B",
                                  hover_color="#475569", width=80, height=40, corner_radius=8,
                                  command=lambda: clear_search())
        btn_clear.pack(side="left", padx=(5, 10))

        btn_search = ctk.CTkButton(search_inner, text="🔍 بحث", font=("Segoe UI", 15, "bold"), fg_color=FIB_GREEN,
                                   hover_color="#004426", width=100, height=40, corner_radius=8,
                                   command=lambda: execute_search())
        btn_search.pack(side="left", padx=5)

        # إدخال الاسم
        self.ent_emp_search_name = ctk.CTkEntry(search_inner, font=("Segoe UI", 15, "bold"), justify="right",
                                                placeholder_text="أدخل اسم الموظف أو المستفيد...", width=350, height=40,
                                                border_color="#CBD5E1")
        self.ent_emp_search_name.pack(side="left", padx=10)
        ctk.CTkLabel(search_inner, text="الاسم:", font=("Segoe UI", 14, "bold"), text_color=TEXT_DARK).pack(side="left",
                                                                                                            padx=(10,
                                                                                                                  2))

        # فريم نتائج البحث
        self.emp_results_scroll = ctk.CTkScrollableFrame(main_container, fg_color="transparent")
        self.emp_results_scroll.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        # =========================================
        # ⏱️ البحث المباشر أثناء الكتابة (Live Search)
        # =========================================
        self.emp_search_timer = None

        def on_key_release(event):
            if self.emp_search_timer is not None:
                self.after_cancel(self.emp_search_timer)
            self.emp_search_timer = self.after(500, execute_search)

        self.ent_emp_search_name.bind("<KeyRelease>", on_key_release)
        self.ent_emp_search_name.bind("<Return>", lambda event: execute_search())

        # =========================================
        # 🛠️ معالجة الاسم العربي الملتصق لتجميل العرض
        # =========================================
        def format_arabic_name(raw_name):
            if not raw_name or pd.isna(raw_name):
                return "غير متوفر"
            text = str(raw_name).strip()
            prefixes = ['عبد', 'ابن', 'أبو', 'بن', 'الله', 'الدين']
            for p in prefixes:
                text = re.sub(rf'({p})([أ-ي])', r'\1 \2', text)
            return " ".join(text.split())

        # =========================================
        # 🧹 تنظيف الشاشة
        # =========================================
        def clear_search():
            self.ent_emp_search_name.delete(0, 'end')
            for widget in self.emp_results_scroll.winfo_children():
                widget.destroy()

        # =========================================
        # 🚀 تنفيذ الاستعلام من قاعدة البيانات
        # =========================================
        def execute_search():
            search_name = self.ent_emp_search_name.get().strip()

            # لو المربع فاضي، امسح النتائج فقط وماتعملش سيرش
            if not search_name:
                for widget in self.emp_results_scroll.winfo_children():
                    widget.destroy()
                return

            for widget in self.emp_results_scroll.winfo_children():
                widget.destroy()

            ctk.CTkLabel(self.emp_results_scroll, text="⚡ جاري البحث في السجلات الطبية...",
                         font=("Segoe UI", 16, "bold"), text_color=FIB_GOLD).pack(pady=50)

            def fetch_data():
                try:
                    engine = getattr(self, '_get_db_connection', lambda: None)()
                    if not engine:
                        raise Exception("لا يوجد اتصال بقاعدة البيانات.")

                    # الاستعلام: جلب الأسماء بدون تكرار وترتيبها أبجدياً
                    query = """
                            SELECT DISTINCT Bname
                            FROM [dbo].[TBL_medical_treatment] \
                            WITH (NOLOCK)
                            WHERE Bname LIKE ?
                            ORDER BY Bname ASC \
                            """

                    # استخدام % بعد النص لجلب أي اسم يبدأ بالحروف المدخلة
                    search_param = f"{search_name}%"
                    df = pd.read_sql(query, engine, params=(search_param,))

                    self.after(0, lambda d=df: update_results_ui(d))
                except Exception as e:
                    err_msg = str(e)
                    logging.error(f"Error fetching employees: {err_msg}")
                    self.after(0, lambda err=err_msg: update_results_ui(pd.DataFrame(), error=err))

            threading.Thread(target=fetch_data, daemon=True).start()

        # =========================================
        # 📑 عرض نتائج الواجهة
        # =========================================
        def update_results_ui(df, error=None):
            for widget in self.emp_results_scroll.winfo_children():
                widget.destroy()

            if error:
                ctk.CTkLabel(self.emp_results_scroll, text=f"❌ حدث خطأ أثناء الاستعلام:\n{error}",
                             font=("Segoe UI", 14, "bold"), text_color="#EF4444").pack(pady=40)
                return

            if df.empty:
                ctk.CTkLabel(self.emp_results_scroll, text="✔️ لا توجد أسماء مطابقة لبحثك",
                             font=("Segoe UI", 18, "bold"), text_color=TEXT_MUTED).pack(pady=60)
                return

            results_count_frame = ctk.CTkFrame(self.emp_results_scroll, fg_color="transparent")
            results_count_frame.pack(fill="x", padx=10, pady=(0, 10))
            ctk.CTkLabel(results_count_frame, text=f"تم العثور على ({len(df)}) نتيجة مطابقة",
                         font=("Segoe UI", 13, "bold"), text_color=FIB_GREEN).pack(side="right")

            # عرض الأسماء في كروت مبسطة وأنيقة
            for index, row in df.iterrows():
                raw_name = row.get('Bname', 'غير متوفر')
                formatted_name = format_arabic_name(raw_name)

                card = ctk.CTkFrame(self.emp_results_scroll, fg_color=CARD_BG, corner_radius=10, border_width=1,
                                    border_color="#CBD5E1")
                card.pack(fill="x", padx=10, pady=5)

                inner_row = ctk.CTkFrame(card, fg_color="transparent")
                inner_row.pack(fill="x", padx=20, pady=12)

                ctk.CTkLabel(inner_row, text=f"👤 {formatted_name}", font=("Segoe UI", 18, "bold"),
                             text_color=TEXT_DARK).pack(side="right")
