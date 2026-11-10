# -*- coding: utf-8 -*-
"""
شاشة الاستفسار عن الضمانات لعميل.

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


class CustomerCollateralsInquiryPage(LegacyInquiryPage):
    """شاشة الاستفسار عن الضمانات لعميل."""
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
            header, text="الاستفسار عن الضمانات لعميل 🛡️",
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

        self.ent_col_account_no = ctk.CTkEntry(search_inner, font=("Segoe UI", 15, "bold"), justify="center",
                                               placeholder_text="رقم الحساب...", width=160, height=40,
                                               border_color="#CBD5E1")
        self.ent_col_account_no.pack(side="left", padx=10)
        ctk.CTkLabel(search_inner, text="رقم الحساب:", font=("Segoe UI", 14, "bold"), text_color=TEXT_DARK).pack(
            side="left", padx=(10, 2))

        if hasattr(self, '_create_premium_select'):
            self.cmb_col_branch_box, self.cmb_col_branch = self._create_premium_select(search_inner,
                                                                                       values=["جاري التحميل..."],
                                                                                       default="جاري التحميل...",
                                                                                       title="اختر الفرع")
            self.cmb_col_branch_box.pack(side="left", padx=10)
        else:
            self.cmb_col_branch = ctk.CTkComboBox(search_inner, font=("Segoe UI", 14, "bold"), justify="right",
                                                  width=200, height=40, border_color="#CBD5E1")
            self.cmb_col_branch.pack(side="left", padx=10)
        ctk.CTkLabel(search_inner, text="الفرع:", font=("Segoe UI", 14, "bold"), text_color=TEXT_DARK).pack(side="left",
                                                                                                            padx=(10,
                                                                                                                  2))

        self.col_results_scroll = ctk.CTkScrollableFrame(main_container, fg_color="transparent")
        self.col_results_scroll.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        # =========================================
        # ⚙️ دوال المساعدة وتحميل البيانات
        # =========================================
        def load_initial_branches():
            if hasattr(self, 'branch_mapping') and self.branch_mapping:
                branches = list(self.branch_mapping.keys())
                self.cmb_col_branch.configure(values=branches)
                self.cmb_col_branch.set(branches[0])
            else:
                self.after(500, load_initial_branches)

        self.after(500, load_initial_branches)
        self.ent_col_account_no.bind("<Return>", lambda event: execute_search())

        def clear_search():
            self.ent_col_account_no.delete(0, 'end')
            for widget in self.col_results_scroll.winfo_children():
                widget.destroy()

        def safe_float(val):
            try:
                if pd.isna(val) or str(val).strip() == '':
                    return 0.0
                return float(val)
            except (ValueError, TypeError):
                return 0.0

        # =========================================
        # 🚀 تنفيذ الاستعلامات حسب طلبك حرفياً
        # =========================================
        def execute_search():
            branch_name = self.cmb_col_branch.get().strip()
            account_no = self.ent_col_account_no.get().strip()

            if not account_no:
                messagebox.showwarning("تنبيه", "يرجى إدخال رقم الحساب")
                return

            for widget in self.col_results_scroll.winfo_children():
                widget.destroy()

            ctk.CTkLabel(self.col_results_scroll, text="⚡ جاري تجميع بيانات الضمانات...", font=("Segoe UI", 16, "bold"),
                         text_color=FIB_GOLD).pack(pady=50)

            def fetch_data():
                try:
                    engine = getattr(self, '_get_db_connection', lambda: None)()
                    if not engine:
                        raise Exception("لا يوجد اتصال بقاعدة البيانات.")

                    # 1. جلب رقم الفرع (branchcode) واسم الجدول (tablename) من tbl_branches
                    branch_query = "SELECT branchcode, tablename FROM [dbo].[tbl_branches] WITH (NOLOCK) WHERE branchname = ?"
                    df_branch = pd.read_sql(branch_query, engine, params=(branch_name,))

                    if df_branch.empty:
                        raise Exception("تعذر العثور على بيانات الفرع في جدول الفروع.")

                    branch_code = str(df_branch.iloc[0]['branchcode']).strip()
                    client_table_name = str(df_branch.iloc[0]['tablename']).strip()

                    if not client_table_name or client_table_name.lower() == 'nan':
                        raise Exception("اسم جدول العملاء (tablename) غير مسجل لهذا الفرع.")

                    # 2. جلب اسم العميل (Bname) من الجدول المستخرج بناءً على رقم العميل (bclnt)
                    client_query = f"SELECT Bname FROM [dbo].[{client_table_name}] WITH (NOLOCK) WHERE bclnt = ?"
                    df_client = pd.read_sql(client_query, engine, params=(account_no,))
                    client_name = str(
                        df_client.iloc[0]['Bname']).strip() if not df_client.empty else "الاسم غير مدرج بالجدول"

                    # 3. جدول الضمانات (TBL_customer_Collaterals): جلب الحقول المطلوبة حرفياً
                    col_query = """
                                SELECT GGL, \
                                       GSUB, \
                                       GCUR, \
                                       GNO1, \
                                       GKND, \
                                       GAMT, \
                                       GDAT1, \
                                       GDAT2, \
                                       GNM, \
                                       GDAT3, \
                                       GSTP, \
                                       GNM1
                                FROM [dbo].[TBL_customer_Collaterals] \
                                WITH (NOLOCK)
                                WHERE GBR = ? AND GCLNT = ? \
                                """
                    df_collaterals = pd.read_sql(col_query, engine, params=(branch_code, account_no))

                    results = {
                        "client_name": client_name,
                        "collaterals": df_collaterals
                    }

                    self.after(0, lambda r=results, b=branch_name, a=account_no: update_results_ui(r, b, a))
                except Exception as e:
                    err_msg = str(e)
                    logging.error(f"Error fetching collaterals: {err_msg}")
                    self.after(0, lambda err=err_msg: update_results_ui(None, branch_name, account_no, error=err))

            threading.Thread(target=fetch_data, daemon=True).start()

        # =========================================
        # 📑 عرض الواجهة الإحصائية للنتائج
        # =========================================
        def update_results_ui(results, branch_name, account_no, error=None):
            for widget in self.col_results_scroll.winfo_children():
                widget.destroy()

            if error:
                ctk.CTkLabel(self.col_results_scroll, text=f"❌ حدث خطأ أثناء الاستعلام:\n{error}",
                             font=("Segoe UI", 14, "bold"), text_color="#EF4444").pack(pady=40)
                return

            if not results:
                return

            # ==================== كارت معلومات العميل ====================
            header_card = ctk.CTkFrame(self.col_results_scroll, fg_color=CARD_BG, corner_radius=12, border_width=1,
                                       border_color="#CBD5E1")
            header_card.pack(fill="x", padx=10, pady=(5, 10))

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

            df_col = results['collaterals']
            if df_col.empty:
                ctk.CTkLabel(self.col_results_scroll, text="✔️ لا توجد ضمانات مسجلة لهذا العميل.",
                             font=("Segoe UI", 16, "bold"), text_color=TEXT_MUTED).pack(pady=40)
                return

            # ==================== كروت تفاصيل الضمانات ====================
            ctk.CTkLabel(self.col_results_scroll, text=f"📑 تفاصيل الضمانات ({len(df_col)})",
                         font=("Segoe UI", 16, "bold"), text_color=FIB_GREEN).pack(anchor="e", padx=15, pady=(10, 5))

            def format_date(val):
                if pd.isna(val) or str(val).strip() == '': return "—"
                try:
                    return pd.to_datetime(val).strftime('%Y-%m-%d')
                except:
                    return str(val)

            # عرض الكروت بناءً على الأعمدة المطلوبة فقط
            for _, row in df_col.iterrows():
                col_card = ctk.CTkFrame(self.col_results_scroll, fg_color=CARD_BG, corner_radius=10, border_width=1,
                                        border_color="#E2E8F0")
                col_card.pack(fill="x", padx=10, pady=6)

                card_top = ctk.CTkFrame(col_card, fg_color="transparent")
                card_top.pack(fill="x", padx=15, pady=10)

                gnm = row.get('GNM', '—')
                gamt = safe_float(row.get('GAMT', 0))
                gcur = row.get('GCUR', '')

                ctk.CTkLabel(card_top, text=f"📌 وصف الضمان : {gnm}", font=("Segoe UI", 16, "bold"),
                             text_color=TEXT_DARK).pack(side="right")
                ctk.CTkLabel(card_top, text=f"قيمة الضمان: {gamt:,.2f}", font=("Segoe UI", 15, "bold"),
                             text_color=FIB_GREEN, fg_color=BOX_BG, corner_radius=6).pack(side="left", ipadx=10,
                                                                                          ipady=3)

                ctk.CTkFrame(col_card, fg_color="#F1F5F9", height=2).pack(fill="x", padx=15)

                details_frame = ctk.CTkFrame(col_card, fg_color="transparent")
                details_frame.pack(fill="x", padx=15, pady=10)

                # --- العمود الأول (يمين) ---
                p1 = ctk.CTkFrame(details_frame, fg_color="transparent")
                p1.pack(side="right", fill="both", expand=True)
                ctk.CTkLabel(p1, text=f"رقم الضمان : {row.get('GNO1', '—')}", font=("Segoe UI", 13)).pack(
                    anchor="e", pady=2)
                ctk.CTkLabel(p1, text=f"نوع الضمان : {row.get('GKND', '—')}", font=("Segoe UI", 13)).pack(
                    anchor="e", pady=2)
                ctk.CTkLabel(p1, text=f"الأستاذ العام الرئيسي: {row.get('GGL', '—')}",
                             font=("Segoe UI", 13)).pack(anchor="e", pady=2)
                ctk.CTkLabel(p1, text=f"الأستاذ العام الفرعي: {row.get('GSUB', '—')}",
                             font=("Segoe UI", 13)).pack(anchor="e", pady=2)

                # --- العمود الثاني (وسط) ---
                p2 = ctk.CTkFrame(details_frame, fg_color="transparent")
                p2.pack(side="right", fill="both", expand=True)
                ctk.CTkLabel(p2, text=f"تاريخ نهاية الضمان: {format_date(row.get('GDAT1'))}",
                             font=("Segoe UI", 13)).pack(anchor="e", pady=2)
                ctk.CTkLabel(p2, text=f"تاريخ تجدد البوليصة: {format_date(row.get('GDAT2'))}",
                             font=("Segoe UI", 13)).pack(anchor="e", pady=2)
                ctk.CTkLabel(p2, text=f"تاريخ آخر تقييم: {format_date(row.get('GDAT3'))}",
                             font=("Segoe UI", 13)).pack(anchor="e", pady=2)

                # --- العمود الثالث (يسار) ---
                p3 = ctk.CTkFrame(details_frame, fg_color="transparent")
                p3.pack(side="right", fill="both", expand=True)
                ctk.CTkLabel(p3, text=f"درجة الرهن (GSTP): {row.get('GSTP', '—')}", font=("Segoe UI", 13)).pack(
                    anchor="e", pady=2)
                ctk.CTkLabel(p3, text=f"اسم الخبير (GNM1): {row.get('GNM1', '—')}", font=("Segoe UI", 13)).pack(
                    anchor="e", pady=2)
