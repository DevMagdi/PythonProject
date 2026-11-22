# -*- coding: utf-8 -*-
"""
شاشة الاستفسار عن تعليمات عميل — نسخة فائقة السرعة (Index-Optimized + Pagination).
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


class InstructionsPage(LegacyInquiryPage):
    """شاشة الاستفسار عن تعليمات عميل."""
    LOAD_BRANCHES_ON_SHOW = True
    PAGE_SIZE = 30  # عرض 30 كارت في الصفحة لمنع تهنيج الواجهة مع البيانات الضخمة

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

        self._current_df = pd.DataFrame()
        self._client_name = "غير مسجل"
        self._cust_no = ""
        self._branch_name = ""
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
            text="الاستفسار عن تعليمات عميل 📜",
            font=("Segoe UI", 22, "bold"),
            text_color=CARD_BG
        )
        title_lbl.pack(side="right", padx=30, pady=15)

        # =========================================
        # 🔍 2. Search Area (الفرع ورقم العميل)
        # =========================================
        search_frame = ctk.CTkFrame(
            main_container,
            fg_color=CARD_BG,
            corner_radius=15,
            border_width=1,
            border_color="#E2E8F0"
        )
        search_frame.pack(fill="x", padx=20, pady=15)

        search_inner = ctk.CTkFrame(search_frame, fg_color="transparent")
        search_inner.pack(side="right", fill="y", padx=20, pady=15)

        # --- زر مسح البيانات ---
        btn_clear = ctk.CTkButton(
            search_inner,
            text="🧹 مسح",
            font=("Segoe UI", 14, "bold"),
            fg_color="#64748B",
            hover_color="#475569",
            text_color="white",
            width=90,
            height=40,
            corner_radius=8,
            command=lambda: clear_search()
        )
        btn_clear.pack(side="left", padx=(5, 10))

        # --- زر البحث ---
        btn_search = ctk.CTkButton(
            search_inner,
            text="🔍 بحث",
            font=("Segoe UI", 15, "bold"),
            fg_color=FIB_GREEN,
            hover_color="#004426",
            text_color="white",
            width=110,
            height=40,
            corner_radius=8,
            command=lambda: execute_search()
        )
        btn_search.pack(side="left", padx=5)

        # --- رقم العميل ---
        self.ent_instructions_cust_no = ctk.CTkEntry(
            search_inner,
            font=("Segoe UI", 15, "bold"),
            justify="center",
            placeholder_text="رقم العميل...",
            width=180,
            height=40,
            border_color="#CBD5E1"
        )
        self.ent_instructions_cust_no.pack(side="left", padx=10)

        ctk.CTkLabel(
            search_inner,
            text="رقم العميل:",
            font=("Segoe UI", 14, "bold"),
            text_color=TEXT_DARK
        ).pack(side="left", padx=(10, 2))

        # --- قائمة الفروع ---
        if hasattr(self, '_create_premium_select'):
            self.cmb_instructions_branch_box, self.cmb_instructions_branch = self._create_premium_select(
                search_inner,
                values=["جاري التحميل..."],
                default="جاري التحميل...",
                title="اختر الفرع"
            )
            self.cmb_instructions_branch_box.pack(side="left", padx=10)
        else:
            self.cmb_instructions_branch = ctk.CTkComboBox(
                search_inner,
                font=("Segoe UI", 14, "bold"),
                justify="right",
                width=230,
                height=40,
                border_color="#CBD5E1"
            )
            self.cmb_instructions_branch.pack(side="left", padx=10)

        ctk.CTkLabel(
            search_inner,
            text="الفرع:",
            font=("Segoe UI", 14, "bold"),
            text_color=TEXT_DARK
        ).pack(side="left", padx=(10, 2))

        # تعبئة الفروع تلقائياً
        def load_branches_to_combo():
            if hasattr(self, 'branch_mapping') and self.branch_mapping:
                branches = list(self.branch_mapping.keys())
                self.cmb_instructions_branch.configure(values=branches)
                self.cmb_instructions_branch.set(branches[0])
            else:
                if hasattr(self, 'nuwairy_load_branches'):
                    self.nuwairy_load_branches()
                self.after(500, load_branches_to_combo)

        load_branches_to_combo()

        # ربط زر الـ Enter بالبحث
        self.ent_instructions_cust_no.bind("<Return>", lambda event: execute_search())

        # =========================================
        # 📜 3. Results Area (كروت التعليمات)
        # =========================================
        self.instructions_results_scroll = ctk.CTkScrollableFrame(main_container, fg_color="transparent")
        self.instructions_results_scroll.pack(fill="both", expand=True, padx=15, pady=(0, 20))

        # --- دالة تنظيف اسم العميل ---
        def clean_arabic_name(raw_name):
            if pd.isna(raw_name) or not str(raw_name).strip():
                return "غير مسجل"
            text = str(raw_name).strip()
            text = re.sub(r'^\d+', '', text).strip()
            text = re.sub(r'\s+(يه|ية|ه|ة)\b', r'\1', text)
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
            return text

        # --- دالة تنسيق التاريخ ---
        def format_date_str(raw_date):
            if pd.isna(raw_date) or not str(raw_date).strip():
                return "—"
            d_str = str(raw_date).split()[0].split('.')[0].strip()
            if len(d_str) == 8 and d_str.isdigit():
                return f"{d_str[:4]}-{d_str[4:6]}-{d_str[6:]}"
            return d_str

        def clear_search():
            self.ent_instructions_cust_no.delete(0, 'end')
            self._current_df = pd.DataFrame()
            for widget in self.instructions_results_scroll.winfo_children():
                widget.destroy()

        # =========================================
        # ⚙️ 4. Search Engine Logic (فائق السرعة)
        # =========================================
        def execute_search():
            branch_name = self.cmb_instructions_branch.get().strip()
            cust_no = self.ent_instructions_cust_no.get().strip()

            if not cust_no:
                messagebox.showwarning("تنبيه", "يرجى إدخال رقم العميل أولاً")
                self.ent_instructions_cust_no.focus()
                return

            if not hasattr(self, 'branch_mapping') or branch_name not in self.branch_mapping:
                messagebox.showerror("خطأ", "برجاء اختيار فرع صحيح")
                return

            branch_info = self.branch_mapping[branch_name]
            branch_code = branch_info[0] if isinstance(branch_info, (tuple, list)) else branch_info

            for widget in self.instructions_results_scroll.winfo_children():
                widget.destroy()

            lbl_loading = ctk.CTkLabel(
                self.instructions_results_scroll,
                text="⚡ جاري البحث السريع عن تعليمات العميل...",
                font=("Segoe UI", 16, "bold"),
                text_color=FIB_GOLD
            )
            lbl_loading.pack(pady=50)

            def fetch_data():
                try:
                    engine = getattr(self, '_get_db_connection', lambda: None)()
                    if not engine:
                        raise Exception("لم يتم العثور على دالة الاتصال بقاعدة البيانات.")

                    clean_branch = str(branch_code).strip()
                    clean_cust = str(cust_no).strip()

                    # توليد احتمالات الأصفار البادئة في بايثون لضرب الـ Index مباشرة بدون دوال ثقيلة في SQL
                    branch_variants = list({clean_branch, clean_branch.lstrip('0'), clean_branch.zfill(3)})
                    cust_variants = list({clean_cust, clean_cust.lstrip('0'), clean_cust.zfill(6), clean_cust.zfill(7)})

                    # 1. جلب اسم الجدول الخاص بالفرع (من الكاش أولاً لتوفير استعلام)
                    target_table = getattr(self, "branch_table_mapping", {}).get(clean_branch)
                    if not target_table and hasattr(self, 'app'):
                        target_table = getattr(self.app, "branch_table_mapping", {}).get(clean_branch)

                    if not target_table:
                        branch_query = "SELECT TOP 1 TableName FROM [dbo].[TBL_Branches] WITH (NOLOCK) WHERE BranchCode = ?"
                        branch_df = pd.read_sql(branch_query, engine, params=(clean_branch,))
                        if not branch_df.empty and pd.notna(branch_df.iloc[0]['TableName']):
                            target_table = str(branch_df.iloc[0]['TableName']).strip()

                    # 2. جلب اسم العميل باستخدام Index عمود BCLNT مباشرة
                    fetched_client_name = "غير مسجل"
                    if target_table and pd.notna(target_table) and str(target_table).strip():
                        try:
                            tbl_str = str(target_table).strip()
                            clean_tbl = tbl_str if "[" in tbl_str else f"[dbo].[{tbl_str}]"
                            c_placeholders_tbl = ",".join(["?"] * len(cust_variants))

                            client_query = f"""
                                SELECT TOP 1 BNAME 
                                FROM {clean_tbl} WITH (NOLOCK) 
                                WHERE BCLNT IN ({c_placeholders_tbl})
                                  AND BNAME IS NOT NULL 
                                  AND BNAME <> ''
                            """
                            client_df = pd.read_sql(client_query, engine, params=tuple(cust_variants))
                            if not client_df.empty and pd.notna(client_df.iloc[0].get('BNAME')):
                                fetched_client_name = str(client_df.iloc[0]['BNAME']).strip()
                        except Exception as cl_err:
                            logging.warning(f"Could not fetch client name: {cl_err}")

                    # 3. الاستعلام المباشر والسريع من جدول التعليمات (تفعيل IX_Instructions_TCLNT_TBR)
                    c_placeholders = ",".join(["?"] * len(cust_variants))
                    b_placeholders = ",".join(["?"] * len(branch_variants))

                    sql = f"""
                        SELECT tmm, tnm1, tnm2, tdat, tmh
                        FROM [dbo].[tbl_instructionsBankAccounts] WITH (NOLOCK)
                        WHERE tclnt IN ({c_placeholders})
                          AND tbr IN ({b_placeholders})
                    """
                    df = pd.read_sql(sql, engine, params=tuple(cust_variants + branch_variants))

                    self.after(0, lambda: on_data_loaded(df, fetched_client_name, clean_cust, branch_name))
                except Exception as e:
                    logging.error(f"Error fetching instructions: {e}")
                    err_msg = str(e)
                    self.after(0, lambda: render_error(err_msg))

            threading.Thread(target=fetch_data, daemon=True).start()

        def render_error(error_msg):
            for widget in self.instructions_results_scroll.winfo_children():
                widget.destroy()
            ctk.CTkLabel(
                self.instructions_results_scroll,
                text=f"❌ حدث خطأ أثناء البحث:\n{error_msg}",
                font=("Segoe UI", 14, "bold"),
                text_color="#EF4444"
            ).pack(pady=40)

        def on_data_loaded(df, client_name, cust_no, branch_name):
            self._current_df = df
            self._client_name = clean_arabic_name(client_name)
            self._cust_no = cust_no
            self._branch_name = branch_name
            self._current_page = 0
            render_page()

        def change_page(delta):
            self._current_page += delta
            render_page()

        def render_page():
            for widget in self.instructions_results_scroll.winfo_children():
                widget.destroy()

            if self._current_df.empty:
                ctk.CTkLabel(
                    self.instructions_results_scroll,
                    text="🔍 لا توجد تعليمات مسجلة لهذا العميل في هذا الفرع",
                    font=("Segoe UI", 18, "bold"),
                    text_color=TEXT_MUTED
                ).pack(pady=60)
                return

            total_records = len(self._current_df)
            total_pages = (total_records + self.PAGE_SIZE - 1) // self.PAGE_SIZE
            start_idx = self._current_page * self.PAGE_SIZE
            end_idx = min(start_idx + self.PAGE_SIZE, total_records)

            # =========================================
            # 👤 1. كارت بيانات العميل + شريط التنقل
            # =========================================
            client_header_card = ctk.CTkFrame(
                self.instructions_results_scroll,
                fg_color=CARD_BG,
                corner_radius=12,
                border_width=1,
                border_color="#CBD5E1"
            )
            client_header_card.pack(fill="x", padx=10, pady=(5, 12))

            client_inner = ctk.CTkFrame(client_header_card, fg_color="transparent")
            client_inner.pack(fill="x", padx=20, pady=12)

            ctk.CTkLabel(
                client_inner,
                text=f"👤 اسم العميل: {self._client_name}",
                font=("Segoe UI", 16, "bold"),
                text_color=FIB_GREEN
            ).pack(side="right")

            ctk.CTkLabel(
                client_inner,
                text=f"الفرع: {self._branch_name} | رقم العميل: {self._cust_no} | الإجمالي: {total_records}",
                font=("Segoe UI", 13, "bold"),
                text_color=TEXT_MUTED,
                fg_color=BOX_BG,
                corner_radius=6
            ).pack(side="left", ipadx=10, ipady=3)

            # أزرار التنقل بين الصفحات إذا زادت النتائج عن 30
            if total_pages > 1:
                nav_bar = ctk.CTkFrame(self.instructions_results_scroll, fg_color=CARD_BG, corner_radius=10, border_width=1, border_color="#E2E8F0")
                nav_bar.pack(fill="x", padx=10, pady=(0, 10))

                ctk.CTkLabel(
                    nav_bar,
                    text=f"عرض التعليمات ({start_idx + 1} - {end_idx}) من أصل {total_records}",
                    font=("Segoe UI", 13, "bold"), text_color=TEXT_DARK
                ).pack(side="right", padx=15, pady=8)

                btns_frame = ctk.CTkFrame(nav_bar, fg_color="transparent")
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

            # =========================================
            # 📑 2. إنشاء كارت لكل تعليمات في الصفحة الحالية فقط
            # =========================================
            page_df = self._current_df.iloc[start_idx:end_idx]

            for _, row in page_df.iterrows():
                instruction_serial = str(row['tmm']).replace('.0', '') if pd.notna(row['tmm']) else "—"
                text1 = str(row['tnm1']).strip() if pd.notna(row['tnm1']) else ""
                text2 = str(row['tnm2']).strip() if pd.notna(row['tnm2']) else ""
                trans_date = format_date_str(row['tdat'])

                tmh_val = str(row['tmh']).replace('.0', '').strip() if pd.notna(row['tmh']) else ""

                if tmh_val == '1':
                    status_text = "1"
                    status_color = "#DC2626"
                    status_bg = "#FEE2E2"
                elif tmh_val == '0':
                    status_text = "0"
                    status_color = "#005C34"
                    status_bg = "#DCFCE7"
                else:
                    status_text = f"غير محدد ({tmh_val})" if tmh_val else "غير محدد"
                    status_color = TEXT_MUTED
                    status_bg = BOX_BG

                card = ctk.CTkFrame(
                    self.instructions_results_scroll,
                    fg_color=CARD_BG,
                    corner_radius=12,
                    border_width=1,
                    border_color="#E2E8F0"
                )
                card.pack(fill="x", padx=10, pady=8)

                stripe_color = status_color if tmh_val in ['0', '1'] else FIB_GOLD
                ctk.CTkFrame(card, fg_color=stripe_color, width=6, corner_radius=0).pack(side="right", fill="y", pady=10)

                card_content = ctk.CTkFrame(card, fg_color="transparent")
                card_content.pack(fill="both", expand=True, padx=20, pady=12)

                header_row = ctk.CTkFrame(card_content, fg_color="transparent")
                header_row.pack(fill="x", pady=(0, 8))

                ctk.CTkLabel(
                    header_row,
                    text=f"مسلسل التعليمات: {instruction_serial} 📜",
                    font=("Segoe UI", 16, "bold"),
                    text_color=TEXT_DARK
                ).pack(side="right")

                ctk.CTkLabel(
                    header_row,
                    text=f"كود الالغاء: {status_text}",
                    font=("Segoe UI", 13, "bold"),
                    text_color=status_color,
                    fg_color=status_bg,
                    corner_radius=6
                ).pack(side="left", ipadx=8, ipady=2)

                text_container = ctk.CTkFrame(
                    card_content,
                    fg_color=BOX_BG,
                    corner_radius=8,
                    border_width=1,
                    border_color="#E2E8F0"
                )
                text_container.pack(fill="x", pady=8, ipady=6)

                if text1:
                    ctk.CTkLabel(
                        text_container,
                        text=text1,
                        font=("Segoe UI", 14, "bold"),
                        text_color=TEXT_DARK,
                        justify="right",
                        anchor="e",
                        wraplength=750
                    ).pack(fill="x", padx=15, pady=(8, 4))

                if text2:
                    ctk.CTkLabel(
                        text_container,
                        text=text2,
                        font=("Segoe UI", 13),
                        text_color="#334155",
                        justify="right",
                        anchor="e",
                        wraplength=750
                    ).pack(fill="x", padx=15, pady=(2, 8))

                footer_row = ctk.CTkFrame(card_content, fg_color="transparent")
                footer_row.pack(fill="x", pady=(4, 0))

                ctk.CTkLabel(
                    footer_row,
                    text=f"تاريخ الحركة م: {trans_date} 📅",
                    font=("Segoe UI", 13, "bold"),
                    text_color=FIB_GREEN,
                    fg_color=BOX_BG,
                    corner_radius=6
                ).pack(side="left", ipadx=10, ipady=2)