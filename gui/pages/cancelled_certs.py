# -*- coding: utf-8 -*-
"""
شاشة الشهادات الملغاة برقم العميل — نسخة فائقة السرعة بدون تعديل قاعدة البيانات.
(In-Memory Results Caching + Branch Caching + Token Cancellation + Python Filtering + Pagination)
"""
import logging
import re
import threading

import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
import pandas as pd

from gui.constants import *
from gui.legacy_page import LegacyInquiryPage


class CancelledCertsPage(LegacyInquiryPage):
    """شاشة الشهادات الملغاة برقم العميل."""
    LOAD_BRANCHES_ON_SHOW = True
    PAGE_SIZE = 30

    def build(self):
        parent = self

        # =========================================
        # 🎨 1. Premium Theme Colors
        # =========================================
        FIB_GREEN = "#005C34"
        FIB_GOLD = "#C5A059"
        BG_MAIN = "#F8FAFC"
        CARD_BG = "#FFFFFF"
        BOX_BG = "#F1F5F9"
        TEXT_DARK = "#0F172A"
        TEXT_MUTED = "#64748B"
        CANCEL_COLOR = "#DC2626"

        # كاش محلي لتسريع الاستعلامات المتكررة فوراً
        self._branch_table_cache = {}
        self._results_cache = {}
        self._name_fix_cache = {}
        self._search_token = 0
        self._current_df = pd.DataFrame()
        self._current_page = 0

        # حاوية الشاشة الرئيسية
        main_container = ctk.CTkFrame(parent, fg_color=BG_MAIN)
        main_container.pack(fill="both", expand=True)

        # الهيدر العلوي
        header = ctk.CTkFrame(main_container, fg_color=FIB_GREEN, height=65, corner_radius=0)
        header.pack(fill="x")
        header.pack_propagate(False)

        ctk.CTkFrame(main_container, fg_color=FIB_GOLD, height=4, corner_radius=0).pack(fill="x")

        title_lbl = ctk.CTkLabel(
            header,
            text="استعلام الشهادات الملغاة برقم العميل",
            font=("Segoe UI", 22, "bold"),
            text_color=CARD_BG
        )
        title_lbl.pack(side="right", padx=30, pady=15)

        # =========================================
        # 🔍 2. Search Area (الفرع ورقم العميل)
        # =========================================
        search_frame = ctk.CTkFrame(
            main_container, fg_color=CARD_BG, corner_radius=15,
            border_width=1, border_color="#E2E8F0"
        )
        search_frame.pack(fill="x", padx=20, pady=20)

        search_inner = ctk.CTkFrame(search_frame, fg_color="transparent")
        search_inner.pack(side="right", fill="y", padx=20, pady=15)

        # --- زر البحث ---
        btn_search = ctk.CTkButton(
            search_inner, text="🔍 بحث", font=("Segoe UI", 15, "bold"),
            fg_color=FIB_GREEN, hover_color="#004426", text_color="white",
            width=120, height=40, corner_radius=8, command=lambda: execute_search()
        )
        btn_search.pack(side="left", padx=10)

        # --- رقم العميل ---
        self.ent_canc_cust_no = ctk.CTkEntry(
            search_inner, font=("Segoe UI", 15, "bold"),
            justify="center", placeholder_text="رقم العميل...",
            width=200, height=40, border_color="#CBD5E1"
        )
        self.ent_canc_cust_no.pack(side="left", padx=10)

        ctk.CTkLabel(
            search_inner, text="رقم العميل:", font=("Segoe UI", 14, "bold"), text_color=TEXT_DARK
        ).pack(side="left", padx=(10, 2))

        # --- قائمة الفروع ---
        if hasattr(self, '_create_premium_select'):
            self.cmb_canc_branch_box, self.cmb_canc_branch = self._create_premium_select(
                search_inner,
                values=["جاري التحميل..."],
                default="جاري التحميل...",
                title="اختر الفرع"
            )
            self.cmb_canc_branch_box.pack(side="left", padx=10)
        else:
            self.cmb_canc_branch = ctk.CTkComboBox(
                search_inner, font=("Segoe UI", 14, "bold"), justify="right",
                width=250, height=40, border_color="#CBD5E1"
            )
            self.cmb_canc_branch.pack(side="left", padx=10)

        ctk.CTkLabel(
            search_inner, text="الفرع:", font=("Segoe UI", 14, "bold"), text_color=TEXT_DARK
        ).pack(side="left", padx=(10, 2))

        # تعبئة الفروع تلقائياً
        def load_branches_to_combo():
            if hasattr(self, 'branch_mapping') and self.branch_mapping:
                branches = list(self.branch_mapping.keys())
                self.cmb_canc_branch.configure(values=branches)
                self.cmb_canc_branch.set(branches[0])
            else:
                if hasattr(self, 'nuwairy_load_branches'):
                    self.nuwairy_load_branches()
                self.after(500, load_branches_to_combo)

        load_branches_to_combo()
        self.ent_canc_cust_no.bind("<Return>", lambda event: execute_search())

        # =========================================
        # 📜 3. Results Area (كروت الشهادات)
        # =========================================
        self.canc_results_scroll = ctk.CTkScrollableFrame(main_container, fg_color="transparent")
        self.canc_results_scroll.pack(fill="both", expand=True, padx=15, pady=(0, 20))

        # دالة تنظيف الاسم مع كاش فوري
        def fix_arabic_name(raw_name):
            if pd.isna(raw_name) or not str(raw_name).strip():
                return "غير مسجل"
            raw_str = str(raw_name).strip()
            if raw_str in self._name_fix_cache:
                return self._name_fix_cache[raw_str]

            text = re.sub(r'\s+(يه|ية|ه|ة)\b', r'\1', raw_str)
            previous_text = ""
            while text != previous_text:
                previous_text = text
                text = re.sub(r'([ةىء])([\u0621-\u064A])', r'\1 \2', text)
                text = re.sub(r'([\u0621-\u064A]{2,})((?:ب|ك|ف|و)?ال[\u0621-\u064A]{2,})', r'\1 \2', text)
                for p in ['عبد', 'ابو', 'أبو', 'ام', 'أم', 'بن', 'بنت', 'ذو', 'ذي']:
                    text = re.sub(f'(?<![\u0621-\u064A])({p})(?=[\u0621-\u064A])', r'\1 ', text)
                for s in ['الدين', 'مخمد', 'الله', 'الاسلام', 'الإسلام', 'الحق']:
                    text = re.sub(f'(?<=[\u0621-\u064A])({s})(?![\u0621-\u064A])', r' \1', text)
                text = re.sub(r'\s+', ' ', text).strip()

            self._name_fix_cache[raw_str] = text
            return text

        # =========================================
        # ⚙️ 4. Search Engine Logic (بدون أي تعديل DB)
        # =========================================
        def execute_search():
            branch_name = self.cmb_canc_branch.get()
            cust_no = self.ent_canc_cust_no.get().strip()

            if not cust_no:
                messagebox.showwarning("تنبيه", "يرجى إدخال رقم العميل أولاً")
                self.ent_canc_cust_no.focus()
                return

            if not hasattr(self, 'branch_mapping') or branch_name not in self.branch_mapping:
                messagebox.showerror("خطأ", "برجاء اختيار فرع صحيح")
                return

            branch_info = self.branch_mapping[branch_name]
            if isinstance(branch_info, tuple):
                branch_code, mapped_table = branch_info
            else:
                branch_code = branch_info
                mapped_table = None

            clean_branch = str(branch_code).strip()
            clean_cust = str(cust_no).strip()

            # 1. التحقق من الكاش الفوري (لو تم البحث عن نفس العميل من قبل تظهر النتيجة في 0 ثانية)
            cache_key = f"{clean_branch}_{clean_cust}"
            if cache_key in self._results_cache:
                on_data_loaded(self._results_cache[cache_key])
                return

            self._search_token += 1
            current_token = self._search_token

            for widget in self.canc_results_scroll.winfo_children():
                widget.destroy()

            lbl_loading = ctk.CTkLabel(
                self.canc_results_scroll, text="⚡ جاري البحث السريع عن الشهادات الملغاة...",
                font=("Segoe UI", 16, "bold"), text_color=FIB_GOLD
            )
            lbl_loading.pack(pady=50)

            def fetch_data():
                try:
                    engine = getattr(self, '_get_db_connection', lambda: None)()
                    if not engine:
                        raise Exception("لم يتم العثور على دالة الاتصال بقاعدة البيانات.")

                    # 2. جلب اسم الجدول من الكاش المحلي أو كاش التطبيق لتوفير استعلام على TBL_Branches
                    target_table = mapped_table or self._branch_table_cache.get(clean_branch)
                    if not target_table and hasattr(self, "app"):
                        target_table = getattr(self.app, "branch_table_mapping", {}).get(clean_branch)

                    if not target_table:
                        branch_query = "SELECT TOP 1 TableName FROM [dbo].[TBL_Branches] WITH (NOLOCK) WHERE BranchCode = ?"
                        branch_df = pd.read_sql(branch_query, engine, params=(clean_branch,))
                        if branch_df.empty:
                            raise Exception("لم يتم العثور على جدول هذا الفرع في قاعدة البيانات.")

                        target_table = branch_df.iloc[0].get('TableName')
                        if not target_table or pd.isna(target_table):
                            raise Exception("اسم الجدول (TableName) الخاص بالفرع غير معرف في قاعدة البيانات.")

                        target_table = str(target_table).strip()
                        self._branch_table_cache[clean_branch] = target_table

                    clean_tbl = target_table if "[" in target_table else f"[dbo].[{target_table}]"

                    # 3. توليد احتمالات الأصفار البادئة لضرب أي Index موجود مباشرة بدون دوال SQL
                    branch_variants = list({clean_branch, clean_branch.lstrip('0'), clean_branch.zfill(3)})
                    cust_variants = list({clean_cust, clean_cust.lstrip('0'), clean_cust.zfill(6), clean_cust.zfill(7)})

                    c_placeholders = ",".join(["?"] * len(cust_variants))
                    b_placeholders = ",".join(["?"] * len(branch_variants))

                    # استعلام خفيف يسحب أعمدة الشهادات فقط للعميل المحدد
                    sql = f"""
                        SELECT CCER, CNO, CAMT, CDAT1, CNAME, CDAT10
                        FROM {clean_tbl} WITH (NOLOCK)
                        WHERE CCLNT IN ({c_placeholders})
                          AND CBR IN ({b_placeholders})
                          AND CDAT10 IS NOT NULL
                    """
                    df = pd.read_sql(sql, engine, params=tuple(cust_variants + branch_variants))

                    if current_token != self._search_token:
                        return

                    # 4. فلترة الشهادات الملغاة في البايثون فوراً (أسرع بكتير من LTRIM/RTRIM داخل SQL)
                    if not df.empty:
                        cdat10_clean = df['CDAT10'].astype(str).str.strip().str.replace('.0', '', regex=False)
                        df = df[
                            (cdat10_clean != '') &
                            (cdat10_clean != '0') &
                            (cdat10_clean.str.lower() != 'none') &
                            (cdat10_clean.str.lower() != 'nan')
                        ]

                    # حفظ في الكاش
                    self._results_cache[cache_key] = df

                    self.after(0, lambda: on_data_loaded(df, current_token))
                except Exception as e:
                    logging.error(f"Error fetching cancelled certificates: {e}")
                    err_msg = str(e)
                    if current_token == self._search_token:
                        self.after(0, lambda: render_error(err_msg))

            threading.Thread(target=fetch_data, daemon=True).start()

        def render_error(error_msg):
            for widget in self.canc_results_scroll.winfo_children():
                widget.destroy()
            ctk.CTkLabel(
                self.canc_results_scroll, text=f"❌ حدث خطأ أثناء البحث:\n{error_msg}",
                font=("Segoe UI", 14, "bold"), text_color="#EF4444"
            ).pack(pady=40)

        def on_data_loaded(df, token=None):
            if token is not None and token != self._search_token:
                return
            self._current_df = df
            self._current_page = 0
            render_page()

        def change_page(delta):
            self._current_page += delta
            render_page()

        def render_page():
            for widget in self.canc_results_scroll.winfo_children():
                widget.destroy()

            if self._current_df.empty:
                ctk.CTkLabel(
                    self.canc_results_scroll, text="🔍 لا توجد شهادات ملغاة لهذا العميل في هذا الفرع",
                    font=("Segoe UI", 18, "bold"), text_color=TEXT_MUTED
                ).pack(pady=60)
                return

            total_records = len(self._current_df)
            total_pages = (total_records + self.PAGE_SIZE - 1) // self.PAGE_SIZE
            start_idx = self._current_page * self.PAGE_SIZE
            end_idx = min(start_idx + self.PAGE_SIZE, total_records)

            # شريط ملخص وأزرار صفحات إذا زاد العدد عن 30
            summary_bar = ctk.CTkFrame(
                self.canc_results_scroll, fg_color=CARD_BG, corner_radius=10,
                border_width=1, border_color="#E2E8F0"
            )
            summary_bar.pack(fill="x", padx=10, pady=(0, 10))

            ctk.CTkLabel(
                summary_bar,
                text=f"إجمالي الشهادات الملغاة: {total_records} (عرض {start_idx + 1} - {end_idx})",
                font=("Segoe UI", 13, "bold"), text_color=CANCEL_COLOR
            ).pack(side="right", padx=15, pady=8)

            if total_pages > 1:
                btns_frame = ctk.CTkFrame(summary_bar, fg_color="transparent")
                btns_frame.pack(side="left", padx=15, pady=5)

                ctk.CTkButton(
                    btns_frame, text="التالي ◀", width=80, height=30, font=("Segoe UI", 13, "bold"),
                    fg_color=FIB_GREEN, state="normal" if self._current_page < total_pages - 1 else "disabled",
                    command=lambda: change_page(1)
                ).pack(side="left", padx=4)

                ctk.CTkLabel(
                    btns_frame, text=f"صفحة {self._current_page + 1} من {total_pages}",
                    font=("Segoe UI", 13, "bold"), text_color=TEXT_DARK
                ).pack(side="left", padx=8)

                ctk.CTkButton(
                    btns_frame, text="▶ السابق", width=80, height=30, font=("Segoe UI", 13, "bold"),
                    fg_color=FIB_GREEN, state="normal" if self._current_page > 0 else "disabled",
                    command=lambda: change_page(-1)
                ).pack(side="left", padx=4)

            # رسم كروت الصفحة الحالية فقط
            page_df = self._current_df.iloc[start_idx:end_idx]

            for _, row in page_df.iterrows():
                ccer_val = str(row['CCER']).replace('.0', '') if pd.notna(row['CCER']) else "غير معروف"
                cno_val = str(row['CNO']).replace('.0', '') if pd.notna(row['CNO']) else "—"

                try:
                    camt_val = f"{float(row['CAMT']):,.2f}"
                except Exception:
                    camt_val = "0.00"

                cust_name = fix_arabic_name(row['CNAME']) if pd.notna(row['CNAME']) else "غير مسجل"
                cdat1_val = str(row['CDAT1']).split()[0] if pd.notna(row['CDAT1']) and str(row['CDAT1']).strip() else "—"
                cdat10_val = str(row['CDAT10']).split()[0] if pd.notna(row['CDAT10']) and str(row['CDAT10']).strip() else "—"

                card = ctk.CTkFrame(
                    self.canc_results_scroll, fg_color=CARD_BG, corner_radius=12,
                    border_width=1, border_color="#E2E8F0"
                )
                card.pack(fill="x", padx=10, pady=8)

                ctk.CTkFrame(card, fg_color=CANCEL_COLOR, width=5, corner_radius=0).pack(side="right", fill="y", pady=10)

                card_content = ctk.CTkFrame(card, fg_color="transparent")
                card_content.pack(fill="both", expand=True, padx=20, pady=15)

                header_row = ctk.CTkFrame(card_content, fg_color="transparent")
                header_row.pack(fill="x", pady=(0, 5))

                ctk.CTkLabel(
                    header_row, text=f"شهادة رقم : {ccer_val} 📜",
                    font=("Segoe UI", 18, "bold"), text_color=FIB_GREEN
                ).pack(side="right")
                ctk.CTkLabel(
                    header_row, text=f"القيمة: {camt_val} 💰",
                    font=("Segoe UI", 15, "bold"), text_color=FIB_GOLD
                ).pack(side="left")

                info_row = ctk.CTkFrame(card_content, fg_color="transparent")
                info_row.pack(fill="x", pady=(0, 10))
                ctk.CTkLabel(
                    info_row, text=f"العميل: {cust_name} 👤",
                    font=("Segoe UI", 15, "bold"), text_color=TEXT_MUTED
                ).pack(side="right")
                ctk.CTkLabel(
                    info_row, text=f"رقم أمر الشراء: {cno_val}",
                    font=("Segoe UI", 13, "bold"), text_color=TEXT_MUTED
                ).pack(side="left")

                ctk.CTkFrame(card_content, fg_color="#F1F5F9", height=2).pack(fill="x", pady=5)

                data_grid = ctk.CTkFrame(card_content, fg_color="transparent")
                data_grid.pack(fill="x", pady=10)
                data_grid.grid_columnconfigure((0, 1), weight=1)

                def create_info_box(parent_grid, row_idx, col_idx, title, value, val_color=TEXT_DARK):
                    box = ctk.CTkFrame(parent_grid, fg_color=BOX_BG, corner_radius=8)
                    box.grid(row=row_idx, column=col_idx, padx=5, pady=5, sticky="ew")
                    ctk.CTkLabel(box, text=title, font=("Segoe UI", 12, "bold"), text_color=TEXT_MUTED).pack(
                        anchor="center", pady=(5, 0))
                    ctk.CTkLabel(box, text=value, font=("Segoe UI", 15, "bold"), text_color=val_color).pack(
                        anchor="center", pady=(0, 5))

                create_info_box(data_grid, 0, 1, "تاريخ الشراء", cdat1_val, val_color=FIB_GREEN)
                create_info_box(data_grid, 0, 0, "تاريخ الإلغاء", cdat10_val, val_color=CANCEL_COLOR)