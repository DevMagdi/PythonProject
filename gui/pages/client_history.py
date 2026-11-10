# -*- coding: utf-8 -*-
"""
شاشة الاستفسار عن سابقة تعاملات عميل.

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


class ClientHistoryInquiryPage(LegacyInquiryPage):
    """شاشة الاستفسار عن سابقة تعاملات عميل."""
    LOAD_BRANCHES_ON_SHOW = True

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
            header, text="الاستفسار عن سابقة تعاملات عميل 📊",
            font=("Segoe UI", 22, "bold"), text_color=CARD_BG
        ).pack(side="right", padx=30, pady=15)

        # =========================================
        # 🔍 منطقة البحث (الفرع ورقم الحساب)
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

        # رقم الحساب / العميل
        self.ent_history_account_no = ctk.CTkEntry(search_inner, font=("Segoe UI", 15, "bold"), justify="center",
                                                   placeholder_text="رقم الحساب...", width=160, height=40,
                                                   border_color="#CBD5E1")
        self.ent_history_account_no.pack(side="left", padx=10)
        ctk.CTkLabel(search_inner, text="رقم الحساب:", font=("Segoe UI", 14, "bold"), text_color=TEXT_DARK).pack(
            side="left", padx=(10, 2))

        # الفرع
        if hasattr(self, '_create_premium_select'):
            self.cmb_history_branch_box, self.cmb_history_branch = self._create_premium_select(search_inner, values=[
                "جاري التحميل..."], default="جاري التحميل...", title="اختر الفرع")
            self.cmb_history_branch_box.pack(side="left", padx=10)
        else:
            self.cmb_history_branch = ctk.CTkComboBox(search_inner, font=("Segoe UI", 14, "bold"), justify="right",
                                                      width=200, height=40, border_color="#CBD5E1")
            self.cmb_history_branch.pack(side="left", padx=10)
        ctk.CTkLabel(search_inner, text="الفرع:", font=("Segoe UI", 14, "bold"), text_color=TEXT_DARK).pack(side="left",
                                                                                                            padx=(10,
                                                                                                                  2))

        # فريم نتائج البحث
        self.history_results_scroll = ctk.CTkScrollableFrame(main_container, fg_color="transparent")
        self.history_results_scroll.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        # =========================================
        # ⚙️ تحميل الفروع وإعداد الأحداث
        # =========================================
        def load_initial_branches():
            if hasattr(self, 'branch_mapping') and self.branch_mapping:
                branches = list(self.branch_mapping.keys())
                self.cmb_history_branch.configure(values=branches)
                self.cmb_history_branch.set(branches[0])
            else:
                self.after(500, load_initial_branches)

        self.after(500, load_initial_branches)
        self.ent_history_account_no.bind("<Return>", lambda event: execute_search())

        def clear_search():
            self.ent_history_account_no.delete(0, 'end')
            for widget in self.history_results_scroll.winfo_children():
                widget.destroy()

        # =========================================
        # 🛠️ دالة مساعدة لتحويل القيم المالية بأمان
        # =========================================
        def safe_float(val):
            try:
                if pd.isna(val) or str(val).strip() == '':
                    return 0.0
                return float(val)
            except (ValueError, TypeError):
                return 0.0

        # =========================================
        # 🚀 تنفيذ الاستعلام من قاعدة البيانات
        # =========================================
        def execute_search():
            branch_name = self.cmb_history_branch.get().strip()
            account_no = self.ent_history_account_no.get().strip()

            if not account_no:
                messagebox.showwarning("تنبيه", "يرجى إدخال رقم الحساب")
                return

            for widget in self.history_results_scroll.winfo_children():
                widget.destroy()

            ctk.CTkLabel(self.history_results_scroll, text="⚡ جاري جلب سابقة تعاملات العميل...",
                         font=("Segoe UI", 16, "bold"), text_color=FIB_GOLD).pack(pady=50)

            def fetch_data():
                try:
                    engine = getattr(self, '_get_db_connection', lambda: None)()
                    if not engine:
                        raise Exception("لا يوجد اتصال بقاعدة البيانات.")

                    # 1️⃣ جلب كود الفرع من tbl_branches بناءً على اسم الفرع المختار
                    branch_code_query = """
                                        SELECT branchcode
                                        FROM [dbo].[tbl_branches] \
                                        WITH (NOLOCK)
                                        WHERE branchname = ? \
                                        """
                    df_branch = pd.read_sql(branch_code_query, engine, params=(branch_name,))

                    if df_branch.empty:
                        if hasattr(self, 'branch_mapping') and branch_name in self.branch_mapping:
                            b_info = self.branch_mapping[branch_name]
                            branch_code = b_info[0] if isinstance(b_info, tuple) else b_info
                        else:
                            raise Exception(f"تعذر العثور على كود الفرع لـ ({branch_name})")
                    else:
                        branch_code = str(df_branch.iloc[0]['branchcode']).strip()

                    # 2️⃣ استعلام سابقة التعاملات على جدول tbl_localrecruitmentprocesses
                    history_query = """
                                    SELECT IAMT18, \
                                           IAMT19, \
                                           IAMT21
                                    FROM [dbo].[tbl_localrecruitmentprocesses] \
                                    WITH (NOLOCK)
                                    WHERE IBR = ? AND ICLNT = ? \
                                    """
                    df_history = pd.read_sql(history_query, engine, params=(branch_code, account_no))

                    self.after(0, lambda d=df_history, b=branch_name, a=account_no: update_results_ui(d, b, a))
                except Exception as e:
                    err_msg = str(e)
                    logging.error(f"Error fetching client history: {err_msg}")
                    self.after(0, lambda err=err_msg: update_results_ui(pd.DataFrame(), branch_name, account_no,
                                                                        error=err))

            threading.Thread(target=fetch_data, daemon=True).start()

        # =========================================
        # 📑 عرض نتائج الواجهة والحسابات
        # =========================================
        def update_results_ui(df, branch_name, account_no, error=None):
            for widget in self.history_results_scroll.winfo_children():
                widget.destroy()

            if error:
                ctk.CTkLabel(self.history_results_scroll, text=f"❌ حدث خطأ أثناء الاستعلام:\n{error}",
                             font=("Segoe UI", 14, "bold"), text_color="#EF4444").pack(pady=40)
                return

            if df.empty:
                ctk.CTkLabel(self.history_results_scroll, text="✔️ لا توجد سابقة تعاملات مطابقة للبيانات المدخلة",
                             font=("Segoe UI", 18, "bold"), text_color=TEXT_MUTED).pack(pady=60)
                return

            # =========================================
            # 🧮 العمليات الحسابية الشروطية
            # =========================================
            iamt18_sum = 0.0
            iamt21_sum = 0.0
            active_operations_count = 0  # 👈 عداد عمليات IAMT18 التي تحققت فيها الشروط

            for _, row in df.iterrows():
                iamt18_val = safe_float(row.get('IAMT18'))
                iamt19_val = safe_float(row.get('IAMT19'))
                iamt21_val = safe_float(row.get('IAMT21'))

                # الشرط: IAMT19 بالسالب (أقل من صفر)
                if iamt19_val < 0:
                    iamt18_sum += iamt18_val
                    active_operations_count += 1  # 👈 زيادة العداد بمقدار 1 لكل عملية مطابقة

                # إجمالي المتأخرات (مجموع IAMT21)
                iamt21_sum += iamt21_val

            total_sum = iamt18_sum

            # =========================================
            # 🎨 عرض الكروت الإحصائية للنتائج
            # =========================================
            header_card = ctk.CTkFrame(self.history_results_scroll, fg_color=CARD_BG, corner_radius=12, border_width=1,
                                       border_color="#CBD5E1")
            header_card.pack(fill="x", padx=10, pady=(5, 15))

            top_row = ctk.CTkFrame(header_card, fg_color="transparent")
            top_row.pack(fill="x", padx=20, pady=15)

            ctk.CTkLabel(top_row, text=f"👤 سابقة تعاملات الحساب: {account_no}", font=("Segoe UI", 18, "bold"),
                         text_color=FIB_GREEN).pack(side="right")
            ctk.CTkLabel(top_row, text=f"الفرع: {branch_name}", font=("Segoe UI", 13, "bold"), text_color=TEXT_MUTED,
                         fg_color=BOX_BG, corner_radius=6).pack(side="left", ipadx=10, ipady=4)

            # كارت الملخص المالي
            summary_card = ctk.CTkFrame(self.history_results_scroll, fg_color=CARD_BG, corner_radius=12, border_width=1,
                                        border_color="#E2E8F0")
            summary_card.pack(fill="x", padx=10, pady=5)

            card_title = ctk.CTkFrame(summary_card, fg_color="transparent")
            card_title.pack(fill="x", padx=15, pady=(15, 5))
            ctk.CTkLabel(card_title, text="💰 ملخص الحسابات والتعاملات", font=("Segoe UI", 16, "bold"),
                         text_color=FIB_GREEN).pack(side="right")

            ctk.CTkFrame(summary_card, fg_color="#F1F5F9", height=2).pack(fill="x", padx=15, pady=5)

            stats_row = ctk.CTkFrame(summary_card, fg_color="transparent")
            stats_row.pack(fill="x", padx=15, pady=15)

            def create_stat_box(parent, title, value, v_color=TEXT_DARK, bg_color=BOX_BG, is_int=False):
                box = ctk.CTkFrame(parent, fg_color=bg_color, corner_radius=8)
                box.pack(side="right", fill="x", expand=True, padx=6)
                ctk.CTkLabel(box, text=title, font=("Segoe UI", 13, "bold"), text_color=TEXT_MUTED).pack(
                    anchor="center", pady=(10, 2))

                # إذا كان عدد صحيح نعرضه كما هو، وإذا كان مبلغا ننسقه بفاصلة عشرية
                val_str = str(value) if is_int else f"{value:,.2f}"
                ctk.CTkLabel(box, text=val_str, font=("Segoe UI", 18, "bold"), text_color=v_color).pack(anchor="center",
                                                                                                        pady=(0, 10))

            # عرض الكروت الإحصائية الأربعة مرتبة
            create_stat_box(stats_row, "عدد العمليات القائمة", active_operations_count, FIB_GOLD, is_int=True)
            create_stat_box(stats_row, "إجمالي سابقة التعاملات (IAMT18)", iamt18_sum, FIB_GREEN)
            create_stat_box(stats_row, "إجمالي المتأخرات (IAMT21)", iamt21_sum, "#DC2626")
            create_stat_box(stats_row, "الإجمالي العام", total_sum, FIB_GOLD)
