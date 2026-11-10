# -*- coding: utf-8 -*-
"""
شاشة الاستفسار عن إجمالي التزامات عميل.

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


class TotalLiabilitiesInquiryPage(LegacyInquiryPage):
    """شاشة الاستفسار عن إجمالي التزامات عميل."""
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
            header, text="الاستفسار عن إجمالي التزامات عميل 💼",
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

        btn_clear = ctk.CTkButton(search_inner, text="🧹 مسح", font=("Segoe UI", 14, "bold"), fg_color="#64748B",
                                  hover_color="#475569", width=80, height=40, corner_radius=8,
                                  command=lambda: clear_search())
        btn_clear.pack(side="left", padx=(5, 10))

        btn_search = ctk.CTkButton(search_inner, text="🔍 بحث", font=("Segoe UI", 15, "bold"), fg_color=FIB_GREEN,
                                   hover_color="#004426", width=100, height=40, corner_radius=8,
                                   command=lambda: execute_search())
        btn_search.pack(side="left", padx=5)

        self.ent_liab_account_no = ctk.CTkEntry(search_inner, font=("Segoe UI", 15, "bold"), justify="center",
                                                placeholder_text="رقم الحساب...", width=160, height=40,
                                                border_color="#CBD5E1")
        self.ent_liab_account_no.pack(side="left", padx=10)
        ctk.CTkLabel(search_inner, text="رقم الحساب:", font=("Segoe UI", 14, "bold"), text_color=TEXT_DARK).pack(
            side="left", padx=(10, 2))

        if hasattr(self, '_create_premium_select'):
            self.cmb_liab_branch_box, self.cmb_liab_branch = self._create_premium_select(search_inner,
                                                                                         values=["جاري التحميل..."],
                                                                                         default="جاري التحميل...",
                                                                                         title="اختر الفرع")
            self.cmb_liab_branch_box.pack(side="left", padx=10)
        else:
            self.cmb_liab_branch = ctk.CTkComboBox(search_inner, font=("Segoe UI", 14, "bold"), justify="right",
                                                   width=200, height=40, border_color="#CBD5E1")
            self.cmb_liab_branch.pack(side="left", padx=10)
        ctk.CTkLabel(search_inner, text="الفرع:", font=("Segoe UI", 14, "bold"), text_color=TEXT_DARK).pack(side="left",
                                                                                                            padx=(10,
                                                                                                                  2))

        self.liab_results_scroll = ctk.CTkScrollableFrame(main_container, fg_color="transparent")
        self.liab_results_scroll.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        # =========================================
        # ⚙️ تحميل الفروع وإعداد الأحداث
        # =========================================
        def load_initial_branches():
            if hasattr(self, 'branch_mapping') and self.branch_mapping:
                branches = list(self.branch_mapping.keys())
                self.cmb_liab_branch.configure(values=branches)
                self.cmb_liab_branch.set(branches[0])
            else:
                self.after(500, load_initial_branches)

        self.after(500, load_initial_branches)
        self.ent_liab_account_no.bind("<Return>", lambda event: execute_search())

        def clear_search():
            self.ent_liab_account_no.delete(0, 'end')
            for widget in self.liab_results_scroll.winfo_children():
                widget.destroy()

        def safe_float(val):
            try:
                if pd.isna(val) or str(val).strip() == '':
                    return 0.0
                return float(val)
            except (ValueError, TypeError):
                return 0.0

        # =========================================
        # 🚀 تنفيذ الاستعلامات وجلب البيانات
        # =========================================
        def execute_search():
            branch_name = self.cmb_liab_branch.get().strip()
            account_no = self.ent_liab_account_no.get().strip()

            if not account_no:
                messagebox.showwarning("تنبيه", "يرجى إدخال رقم الحساب")
                return

            for widget in self.liab_results_scroll.winfo_children():
                widget.destroy()

            ctk.CTkLabel(self.liab_results_scroll, text="⚡ جاري تجميع بيانات التزامات العميل...",
                         font=("Segoe UI", 16, "bold"), text_color=FIB_GOLD).pack(pady=50)

            def fetch_data():
                try:
                    engine = getattr(self, '_get_db_connection', lambda: None)()
                    if not engine:
                        raise Exception("لا يوجد اتصال بقاعدة البيانات.")

                    # 1. جلب كود الفرع واسم جدول العملاء المرتبط به
                    branch_query = "SELECT branchcode, tablename FROM [dbo].[tbl_branches] WITH (NOLOCK) WHERE branchname = ?"
                    df_branch = pd.read_sql(branch_query, engine, params=(branch_name,))

                    if df_branch.empty:
                        raise Exception("تعذر العثور على بيانات الفرع في قاعدة البيانات.")

                    branch_code = str(df_branch.iloc[0]['branchcode']).strip()
                    client_table_name = str(df_branch.iloc[0]['tablename']).strip()

                    if not client_table_name or client_table_name.lower() == 'nan':
                        raise Exception("اسم جدول العملاء (tablename) غير مسجل لهذا الفرع.")

                    # 2. جلب اسم العميل ديناميكياً من الجدول المستخرج
                    client_query = f"SELECT Bname FROM [dbo].[{client_table_name}] WITH (NOLOCK) WHERE bclnt = ?"
                    df_client = pd.read_sql(client_query, engine, params=(account_no,))
                    client_name = str(df_client.iloc[0]['Bname']).strip() if not df_client.empty else "غير مدرج بالجدول"

                    # 3. جدول العمليات (tbl_localrecruitmentprocesses) - رصيد المدين
                    df_local = pd.read_sql(
                        "SELECT IAMT19 FROM [dbo].[tbl_localrecruitmentprocesses] WITH (NOLOCK) WHERE IBR = ? AND ICLNT = ?",
                        engine, params=(branch_code, account_no))
                    total_iamt19 = sum(safe_float(x) for x in df_local['IAMT19']) if not df_local.empty else 0.0

                    # 4. جدول الرعاة/الضامنين (tbl_sponser) - العملة الأغلب
                    df_sponsor = pd.read_sql(
                        "SELECT FAMT19, fcur FROM [dbo].[tbl_sponsers] WITH (NOLOCK) WHERE fbr = ? AND fclnt = ?",
                        engine, params=(branch_code, account_no))
                    total_sponsor = 0.0
                    if not df_sponsor.empty:
                        most_frequent_currency = df_sponsor['fcur'].mode()
                        if not most_frequent_currency.empty:
                            dominant_cur = most_frequent_currency[0]
                            total_sponsor = sum(safe_float(row['FAMT19']) for _, row in df_sponsor.iterrows() if
                                                row['fcur'] == dominant_cur)

                    # 5. جدول الضمانات (tbl_gurantees) - (lgval - lgcval)
                    df_guar = pd.read_sql(
                        "SELECT lgval, lgcval FROM [dbo].[tbl_gurantees] WITH (NOLOCK) WHERE lgbr = ? AND lgcno = ?",
                        engine, params=(branch_code, account_no))
                    total_guar = 0.0
                    if not df_guar.empty:
                        for _, row in df_guar.iterrows():
                            total_guar += (safe_float(row['lgval']) - safe_float(row['lgcval']))

                    # 6. جدول الاعتمادات (tbl_credits) - العملة الأغلب
                    df_credits = pd.read_sql(
                        "SELECT damt3, dcur3 FROM [dbo].[tbl_credits] WITH (NOLOCK) WHERE dbr = ? AND dclnt = ?", engine,
                        params=(branch_code, account_no))
                    total_credits = 0.0
                    if not df_credits.empty:
                        most_frequent_dcur = df_credits['dcur3'].mode()
                        if not most_frequent_dcur.empty:
                            dominant_dcur = most_frequent_dcur[0]
                            total_credits = sum(safe_float(row['damt3']) for _, row in df_credits.iterrows() if
                                                row['dcur3'] == dominant_dcur)

                    results = {
                        "client_name": client_name,
                        "iamt19": total_iamt19,
                        "sponsor": total_sponsor,
                        "guarantees": total_guar,
                        "credits": total_credits
                    }

                    self.after(0, lambda r=results, b=branch_name, a=account_no: update_results_ui(r, b, a))
                except Exception as e:
                    err_msg = str(e)
                    logging.error(f"Error fetching total liabilities: {err_msg}")
                    self.after(0, lambda err=err_msg: update_results_ui(None, branch_name, account_no, error=err))

            threading.Thread(target=fetch_data, daemon=True).start()

        # =========================================
        # 📑 عرض الواجهة الإحصائية للنتائج
        # =========================================
        def update_results_ui(results, branch_name, account_no, error=None):
            for widget in self.liab_results_scroll.winfo_children():
                widget.destroy()

            if error:
                ctk.CTkLabel(self.liab_results_scroll, text=f"❌ حدث خطأ أثناء الاستعلام:\n{error}",
                             font=("Segoe UI", 14, "bold"), text_color="#EF4444").pack(pady=40)
                return

            if not results:
                return

            header_card = ctk.CTkFrame(self.liab_results_scroll, fg_color=CARD_BG, corner_radius=12, border_width=1,
                                       border_color="#CBD5E1")
            header_card.pack(fill="x", padx=10, pady=(5, 15))

            top_row = ctk.CTkFrame(header_card, fg_color="transparent")
            top_row.pack(fill="x", padx=20, pady=15)

            ctk.CTkLabel(top_row, text=f"👤 اسم العميل: {results['client_name']}", font=("Segoe UI", 18, "bold"),
                         text_color=TEXT_DARK).pack(side="right")

            info_tags = ctk.CTkFrame(top_row, fg_color="transparent")
            info_tags.pack(side="left")
            ctk.CTkLabel(info_tags, text=f"الحساب: {account_no}", font=("Segoe UI", 13, "bold"), text_color=FIB_GOLD,
                         fg_color=BOX_BG, corner_radius=6).pack(side="left", padx=4, ipadx=8, ipady=3)
            ctk.CTkLabel(info_tags, text=f"الفرع: {branch_name}", font=("Segoe UI", 13, "bold"), text_color=TEXT_MUTED,
                         fg_color=BOX_BG, corner_radius=6).pack(side="left", padx=4, ipadx=8, ipady=3)

            summary_card = ctk.CTkFrame(self.liab_results_scroll, fg_color=CARD_BG, corner_radius=12, border_width=1,
                                        border_color="#E2E8F0")
            summary_card.pack(fill="x", padx=10, pady=5)

            card_title = ctk.CTkFrame(summary_card, fg_color="transparent")
            card_title.pack(fill="x", padx=15, pady=(15, 5))
            ctk.CTkLabel(card_title, text="💰 تفاصيل الالتزامات المالية", font=("Segoe UI", 16, "bold"),
                         text_color=FIB_GREEN).pack(side="right")

            ctk.CTkFrame(summary_card, fg_color="#F1F5F9", height=2).pack(fill="x", padx=15, pady=5)

            stats_row = ctk.CTkFrame(summary_card, fg_color="transparent")
            stats_row.pack(fill="x", padx=15, pady=15)

            def create_stat_box(parent, title, value, v_color=TEXT_DARK, bg_color=BOX_BG):
                box = ctk.CTkFrame(parent, fg_color=bg_color, corner_radius=8)
                box.pack(side="right", fill="x", expand=True, padx=6)
                ctk.CTkLabel(box, text=title, font=("Segoe UI", 13, "bold"), text_color=TEXT_MUTED).pack(
                    anchor="center", pady=(10, 2))
                ctk.CTkLabel(box, text=f"{value:,.2f}", font=("Segoe UI", 18, "bold"), text_color=v_color).pack(
                    anchor="center", pady=(0, 10))

            create_stat_box(stats_row, "رصيد المدين", abs(results['iamt19']), FIB_GREEN)
            create_stat_box(stats_row, "الكفالات", results['sponsor'], FIB_GOLD)
            create_stat_box(stats_row, "جزء غير مغطي من الضمانات", results['guarantees'], TEXT_DARK)
            create_stat_box(stats_row, "جزء غير مغطي من الاعتمادات", results['credits'], "#0369A1")
