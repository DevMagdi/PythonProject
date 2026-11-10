# -*- coding: utf-8 -*-
"""
شاشة الاستفسار عن الشيكات المرتدة.

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


class ReturnedChequesPage(LegacyInquiryPage):
    """شاشة الاستفسار عن الشيكات المرتدة."""
    LOAD_BRANCHES_ON_SHOW = True

    def build(self):
        """بناء الشاشة — الكود القديم كما هو (parent = الشاشة نفسها)."""
        parent = self

        # =========================================
        # 🎨 الألوان والتنسيقات
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
            header, text="الاستفسار عن الشيكات المرتدة 📉",
            font=("Segoe UI", 22, "bold"), text_color=CARD_BG
        ).pack(side="right", padx=30, pady=15)

        # =========================================
        # 🔍 منطقة البحث
        # =========================================
        search_frame = ctk.CTkFrame(main_container, fg_color=CARD_BG, corner_radius=15, border_width=1,
                                    border_color="#E2E8F0")
        search_frame.pack(fill="x", padx=20, pady=15)

        search_inner = ctk.CTkFrame(search_frame, fg_color="transparent")
        search_inner.pack(side="right", fill="y", padx=20, pady=15)

        # أزرار البحث والمسح
        btn_clear = ctk.CTkButton(search_inner, text="🧹 مسح", font=("Segoe UI", 14, "bold"), fg_color="#64748B",
                                  hover_color="#475569", width=90, height=40, corner_radius=8,
                                  command=lambda: clear_search())
        btn_clear.pack(side="left", padx=(5, 10))

        btn_search = ctk.CTkButton(search_inner, text="🔍 بحث", font=("Segoe UI", 15, "bold"), fg_color=FIB_GREEN,
                                   hover_color="#004426", width=110, height=40, corner_radius=8,
                                   command=lambda: execute_search())
        btn_search.pack(side="left", padx=5)

        # إدخال رقم العميل
        self.ent_cheque_cust_no = ctk.CTkEntry(search_inner, font=("Segoe UI", 15, "bold"), justify="center",
                                               placeholder_text="رقم العميل...", width=160, height=40,
                                               border_color="#CBD5E1")
        self.ent_cheque_cust_no.pack(side="left", padx=10)
        ctk.CTkLabel(search_inner, text="رقم الحساب:", font=("Segoe UI", 14, "bold"), text_color=TEXT_DARK).pack(
            side="left", padx=(10, 2))

        # اختيار الفرع
        if hasattr(self, '_create_premium_select'):
            self.cmb_cheque_branch_box, self.cmb_cheque_branch = self._create_premium_select(search_inner,
                                                                                             values=["جاري التحميل..."],
                                                                                             default="جاري التحميل...",
                                                                                             title="اختر الفرع")
            self.cmb_cheque_branch_box.pack(side="left", padx=10)
        else:
            self.cmb_cheque_branch = ctk.CTkComboBox(search_inner, font=("Segoe UI", 14, "bold"), justify="right",
                                                     width=220, height=40, border_color="#CBD5E1")
            self.cmb_cheque_branch.pack(side="left", padx=10)
        ctk.CTkLabel(search_inner, text="الفرع:", font=("Segoe UI", 14, "bold"), text_color=TEXT_DARK).pack(side="left",
                                                                                                            padx=(10,
                                                                                                                  2))

        self.cheque_results_scroll = ctk.CTkScrollableFrame(main_container, fg_color="transparent")
        self.cheque_results_scroll.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        # =========================================
        # ⚙️ تحميل الداتا الأولية (الفروع والعملات)
        # =========================================
        self.currency_map_code_to_name = {}

        def load_initial_data():
            if hasattr(self, 'branch_mapping') and self.branch_mapping:
                branches = list(self.branch_mapping.keys())
                self.cmb_cheque_branch.configure(values=branches)
                self.cmb_cheque_branch.set(branches[0])
            else:
                if hasattr(self, 'nuwairy_load_branches'):
                    self.nuwairy_load_branches()
                self.after(500, load_initial_data)
                return

            def fetch_currencies():
                try:
                    engine = getattr(self, '_get_db_connection', lambda: None)()
                    if engine:
                        sql = "SELECT fcur, cnm FROM [dbo].[tbl_currency] WITH (NOLOCK) WHERE cnm IS NOT NULL"
                        df = pd.read_sql(sql, engine)
                        self.currency_map_code_to_name.clear()
                        for _, row in df.iterrows():
                            if pd.notna(row['fcur']) and pd.notna(row['cnm']):
                                k = str(row['fcur']).strip()
                                v = str(row['cnm']).strip()
                                self.currency_map_code_to_name[k] = v
                except Exception as e:
                    logging.error(f"Error loading currencies: {e}")

            threading.Thread(target=fetch_currencies, daemon=True).start()

        load_initial_data()
        self.ent_cheque_cust_no.bind("<Return>", lambda event: execute_search())

        def clear_search():
            self.ent_cheque_cust_no.delete(0, 'end')
            for widget in self.cheque_results_scroll.winfo_children():
                widget.destroy()

        def clean_arabic_name(name):
            if not isinstance(name, str) or not name.strip():
                return "—"
            cleaned = name.strip()
            cleaned = re.sub(r'[_+\-]', ' ', cleaned)
            cleaned = re.sub(r'\s+', ' ', cleaned)
            cleaned = re.sub(r'(\bابن|\bعبد|\bابو|\bأبو|\bام|\bأم)([أ-ي])', r'\1 \2', cleaned)
            cleaned = re.sub(r'([ةه])([أ-ي])', r'\1 \2', cleaned)
            cleaned = re.sub(r'([أ-ي])(للسياح|للتجار|للمقاول|للاستثمار|للخدمات|للتأمين|تراست|جروب|كومباني)', r'\1 \2',
                             cleaned)
            return re.sub(r'\s+', ' ', cleaned).strip()

        # =========================================
        # 🚀 تنفيذ البحث وتجميع البيانات
        # =========================================
        def execute_search():
            branch_name = self.cmb_cheque_branch.get().strip()
            cust_no = self.ent_cheque_cust_no.get().strip()

            if not cust_no:
                messagebox.showwarning("تنبيه", "يرجى إدخال رقم العميل")
                return

            if not hasattr(self, 'branch_mapping') or branch_name not in self.branch_mapping:
                messagebox.showerror("خطأ", "برجاء اختيار فرع صحيح")
                return

            branch_info = self.branch_mapping[branch_name]
            branch_code = branch_info[0] if isinstance(branch_info, tuple) else branch_info

            for widget in self.cheque_results_scroll.winfo_children():
                widget.destroy()

            ctk.CTkLabel(self.cheque_results_scroll, text="⚡ جاري سحب وتجميع بيانات الشيكات...",
                         font=("Segoe UI", 16, "bold"), text_color=FIB_GOLD).pack(pady=50)

            def fetch_data():
                try:
                    engine = getattr(self, '_get_db_connection', lambda: None)()
                    if not engine:
                        raise Exception("لا يوجد اتصال بقاعدة البيانات.")

                    cust_str = cust_no.strip()
                    try:
                        cust_int_str = str(int(cust_str))
                    except Exception:
                        cust_int_str = cust_str

                    # 1. جلب اسم العميل
                    target_table = None
                    try:
                        branch_query = f"SELECT TableName FROM [dbo].[TBL_Branches] WITH (NOLOCK) WHERE BranchCode = '{branch_code}'"
                        branch_df = pd.read_sql(branch_query, engine)
                        if not branch_df.empty and pd.notna(branch_df.iloc[0]['TableName']):
                            target_table = str(branch_df.iloc[0]['TableName']).strip()
                    except Exception:
                        pass

                    fetched_client_name = "غير مسجل"
                    if target_table:
                        try:
                            client_query = f"""
                                SELECT TOP 1 BNAME 
                                FROM [dbo].[{target_table}] WITH (NOLOCK) 
                                WHERE BCLNT = '{cust_str}' OR BCLNT = '{cust_int_str}'
                            """
                            client_df = pd.read_sql(client_query, engine)
                            if not client_df.empty and pd.notna(client_df.iloc[0].get('BNAME')):
                                fetched_client_name = clean_arabic_name(str(client_df.iloc[0].get('BNAME')).strip())
                        except Exception:
                            pass

                    # 2. الاستعلام عن الشيكات المرتدة (تم إلغاء التصفية بحالة الشيك)
                            # 2. الاستعلام عن الشيكات المرتدة (تم التعديل لاستخدام العمود المُفهرس)
                        sql_cheques = f"""
                                    SELECT ccur, camt1, camt9, camt7, camt8, cchno, cdat1, csub, cgl
                                    FROM [dbo].[tbl_refferedcheques] WITH (NOLOCK)
                                    WHERE cbr = '{branch_code}'
                                      AND (cclnt_indexed = '{cust_str}' OR cclnt_indexed = '{cust_int_str}')
                                """
                    df = pd.read_sql(sql_cheques, engine)

                    # 3. المعالجة والتجميع باستخدام Pandas
                    if not df.empty:
                        for col in ['camt1', 'camt9', 'camt7', 'camt8']:
                            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

                        df['CURR_NAME'] = df['ccur'].astype(str).str.strip().map(self.currency_map_code_to_name).fillna(
                            df['ccur'].astype(str))

                        summary_df = df.groupby('CURR_NAME').agg(
                            check_count=('camt1', 'count'),
                            total_camt1=('camt1', 'sum'),
                            total_camt9=('camt9', 'sum'),
                            total_camt7=('camt7', 'sum'),
                            total_camt8=('camt8', 'sum')
                        ).reset_index()
                    else:
                        summary_df = pd.DataFrame()

                    self.after(0, lambda: update_results_ui(df, summary_df, fetched_client_name, cust_no, branch_name))
                except Exception as e:
                    logging.error(f"Error fetching cheques: {e}")
                    self.after(0, lambda: update_results_ui(pd.DataFrame(), pd.DataFrame(), "غير مسجل", cust_no,
                                                            branch_name, error=str(e)))

            threading.Thread(target=fetch_data, daemon=True).start()

        # =========================================
        # 📑 عرض النتائج والتجميعات
        # =========================================
        def update_results_ui(df, summary_df, client_name, cust_no, branch_name, error=None):
            for widget in self.cheque_results_scroll.winfo_children():
                widget.destroy()

            if error:
                ctk.CTkLabel(self.cheque_results_scroll, text=f"❌ حدث خطأ:\n{error}", font=("Segoe UI", 14, "bold"),
                             text_color="#EF4444").pack(pady=40)
                return

            if summary_df.empty or df.empty:
                ctk.CTkLabel(self.cheque_results_scroll, text="✔️ لا توجد شيكات مرتدة مطابقة لبحثك",
                             font=("Segoe UI", 18, "bold"), text_color=TEXT_MUTED).pack(pady=60)
                return

            # --- 1. كارت بيانات العميل الرئيسي ---
            client_card = ctk.CTkFrame(self.cheque_results_scroll, fg_color=CARD_BG, corner_radius=12, border_width=1,
                                       border_color="#CBD5E1")
            client_card.pack(fill="x", padx=10, pady=(5, 15))

            client_inner = ctk.CTkFrame(client_card, fg_color="transparent")
            client_inner.pack(fill="x", padx=20, pady=12)

            ctk.CTkLabel(client_inner, text=f"👤 اسم العميل: {client_name}", font=("Segoe UI", 16, "bold"),
                         text_color=FIB_GREEN).pack(side="right")

            info_frame = ctk.CTkFrame(client_inner, fg_color="transparent")
            info_frame.pack(side="left")
            ctk.CTkLabel(info_frame, text=f"الفرع: {branch_name} | الحساب: {cust_no}", font=("Segoe UI", 13, "bold"),
                         text_color=TEXT_MUTED, fg_color=BOX_BG, corner_radius=6).pack(side="right", ipadx=10, ipady=3)

            # دالة لتنسيق المبالغ المالية
            def format_money(val):
                try:
                    return "{:,.2f}".format(float(val))
                except Exception:
                    return "0.00"

            # دالة مساعدة لإنشاء المربعات
            def create_stat_box(parent_frame, title, value, v_color):
                box = ctk.CTkFrame(parent_frame, fg_color=BOX_BG, corner_radius=8)
                box.pack(side="right", fill="x", expand=True, padx=4)
                ctk.CTkLabel(box, text=title, font=("Segoe UI", 12, "bold"), text_color=TEXT_MUTED).pack(
                    anchor="center", pady=(8, 2))
                ctk.CTkLabel(box, text=value, font=("Segoe UI", 16, "bold"), text_color=v_color).pack(anchor="center",
                                                                                                      pady=(0, 8))

            # =========================================
            # --- 2. رندر كروت الخلاصة (الإجماليات) ---
            # =========================================
            for index, row in summary_df.iterrows():
                card = ctk.CTkFrame(self.cheque_results_scroll, fg_color=CARD_BG, corner_radius=12, border_width=1,
                                    border_color="#E2E8F0")
                card.pack(fill="x", padx=10, pady=8)

                header_row = ctk.CTkFrame(card, fg_color="transparent")
                header_row.pack(fill="x", padx=15, pady=(15, 5))
                ctk.CTkLabel(header_row, text=f"📊 ملخص المبالغ بعُملة: {row.get('CURR_NAME', '')}",
                             font=("Segoe UI", 16, "bold"), text_color=FIB_GOLD).pack(side="right")

                ctk.CTkFrame(card, fg_color="#F1F5F9", height=2).pack(fill="x", padx=15, pady=5)

                stats_frame = ctk.CTkFrame(card, fg_color="transparent")
                stats_frame.pack(fill="x", padx=15, pady=(5, 15))

                create_stat_box(stats_frame, "إجمالي التعويض", format_money(row.get('total_camt8', 0)), "#DC2626")
                create_stat_box(stats_frame, "إجمالي المتأخرات", format_money(row.get('total_camt7', 0)), "#EA580C")
                create_stat_box(stats_frame, "إجمالي المسدد", format_money(row.get('total_camt9', 0)), "#2563EB")
                create_stat_box(stats_frame, "مجموع المبالغ", format_money(row.get('total_camt1', 0)), FIB_GREEN)
                create_stat_box(stats_frame, "عدد الشيكات", str(row.get('check_count', 0)), TEXT_DARK)

            # =========================================
            # --- فاصل بصري بين الخلاصة والتفاصيل ---
            # =========================================
            separator_frame = ctk.CTkFrame(self.cheque_results_scroll, fg_color="transparent")
            separator_frame.pack(fill="x", padx=10, pady=(20, 10))
            ctk.CTkLabel(separator_frame, text="📑 تفاصيل الشيكات (كل شيك على حدة)", font=("Segoe UI", 18, "bold"),
                         text_color=FIB_GREEN).pack(side="right")
            ctk.CTkFrame(separator_frame, fg_color="#CBD5E1", height=2).pack(side="right", fill="x", expand=True,
                                                                             padx=(20, 10))

            # =========================================
            # --- 3. رندر كروت التفاصيل (كل شيك لوحده) ---
            # =========================================
            for index, row in df.iterrows():
                detail_card = ctk.CTkFrame(self.cheque_results_scroll, fg_color=CARD_BG, corner_radius=12,
                                           border_width=1, border_color="#E2E8F0")
                detail_card.pack(fill="x", padx=10, pady=6)

                ctk.CTkFrame(detail_card, fg_color=FIB_GREEN, width=6, corner_radius=0).pack(side="right", fill="y",
                                                                                             pady=10)

                card_content = ctk.CTkFrame(detail_card, fg_color="transparent")
                card_content.pack(fill="both", expand=True, padx=15, pady=12)

                # رأس كارت الشيك
                detail_header = ctk.CTkFrame(card_content, fg_color="transparent")
                detail_header.pack(fill="x", pady=(0, 8))

                cchno_val = str(row.get('cchno', '—')).strip()
                if cchno_val in ['nan', 'None', '']: cchno_val = '—'

                curr_display = row.get('CURR_NAME', str(row.get('ccur', '—')))

                cdat1_val = row.get('cdat1')
                if pd.isna(cdat1_val):
                    cdat1_str = "—"
                else:
                    try:
                        cdat1_str = pd.to_datetime(cdat1_val).strftime('%Y-%m-%d')
                    except Exception:
                        cdat1_str = str(cdat1_val)

                ctk.CTkLabel(detail_header, text=f"رقم الشيك: {cchno_val}", font=("Segoe UI", 16, "bold"),
                             text_color=TEXT_DARK).pack(side="right")
                ctk.CTkLabel(detail_header, text=f"العملة: {curr_display}", font=("Segoe UI", 12, "bold"),
                             text_color="#FFFFFF", fg_color=TEXT_MUTED, corner_radius=6).pack(side="left", ipadx=8,
                                                                                              ipady=2)

                ctk.CTkFrame(card_content, fg_color="#F1F5F9", height=2).pack(fill="x", pady=4)

                # قيم الشيك الفردية والحسابات
                detail_stats = ctk.CTkFrame(card_content, fg_color="transparent")
                detail_stats.pack(fill="x", pady=(5, 0))

                cgl_val = str(row.get('cgl', '—')).strip()
                if cgl_val in ['nan', 'None', '']: cgl_val = '—'

                csub_val = str(row.get('csub', '—')).strip()
                if csub_val in ['nan', 'None', '']: csub_val = '—'

                create_stat_box(detail_stats, "قيمة الشيك", format_money(row.get('camt1', 0)), FIB_GREEN)
                create_stat_box(detail_stats, "المتأخرات", format_money(row.get('camt7', 0)), "#EA580C")
                create_stat_box(detail_stats, "تاريخ الاستحقاق", cdat1_str, TEXT_DARK)
                create_stat_box(detail_stats, "أستاذ عام", cgl_val, TEXT_MUTED)
                create_stat_box(detail_stats, "أستاذ فرعي", csub_val, TEXT_MUTED)
