# -*- coding: utf-8 -*-
"""
شاشة البحث برصيد العميل (Client Balances) — نسخة فائقة السرعة (Index-Optimized + In-Memory Lookups).
"""
import logging
import threading

import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
import pandas as pd

from gui.constants import *
from gui.legacy_page import LegacyInquiryPage


class CustomerBalancePage(LegacyInquiryPage):
    """شاشة البحث برصيد العميل (Client Balances)."""
    LOAD_BRANCHES_ON_SHOW = False

    def build(self):
        parent = self

        # =========================================
        # 🚀 1. كاش محلي للجداول المرجعية (الفروع، العملات، أنواع الحسابات)
        # =========================================
        self._branch_info_cache = {}
        self._acc_types_cache = None
        self._currencies_cache = None

        # =========================================
        # 🎨 2. الألوان والتنسيق
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
            header,
            text="💳 البحث بأرصدة وأنواع حسابات العميل",
            font=("Segoe UI", 22, "bold"),
            text_color=CARD_BG
        ).pack(side="right", padx=30, pady=15)

        # =========================================
        # 🔍 3. منطقة البحث
        # =========================================
        search_frame = ctk.CTkFrame(main_container, fg_color=CARD_BG, corner_radius=15, border_width=1,
                                    border_color="#E2E8F0")
        search_frame.pack(fill="x", padx=20, pady=20)

        search_inner = ctk.CTkFrame(search_frame, fg_color="transparent")
        search_inner.pack(side="right", fill="y", padx=20, pady=15)

        btn_search = ctk.CTkButton(
            search_inner, text="🔍 بحث", font=("Segoe UI", 15, "bold"),
            fg_color=FIB_GREEN, hover_color="#004426", text_color="white",
            width=120, height=40, corner_radius=8, command=lambda: execute_search()
        )
        btn_search.pack(side="left", padx=10)

        self.ent_bal_acc = ctk.CTkEntry(
            search_inner, font=("Segoe UI", 15, "bold"),
            justify="center", placeholder_text="رقم العميل...",
            width=200, height=40, border_color="#CBD5E1"
        )
        self.ent_bal_acc.pack(side="left", padx=10)

        ctk.CTkLabel(search_inner, text="رقم العميل:", font=("Segoe UI", 14, "bold"), text_color=TEXT_DARK).pack(
            side="left", padx=(10, 2))

        if hasattr(self, '_create_premium_select'):
            self.cmb_bal_branch_box, self.cmb_bal_branch = self._create_premium_select(
                search_inner, values=["جاري التحميل..."], default="جاري التحميل...", title="اختر الفرع"
            )
            self.cmb_bal_branch_box.pack(side="left", padx=10)
        else:
            self.cmb_bal_branch = ctk.CTkComboBox(
                search_inner, font=("Segoe UI", 14, "bold"), justify="right",
                width=250, height=40, border_color="#CBD5E1"
            )
            self.cmb_bal_branch.pack(side="left", padx=10)

        ctk.CTkLabel(search_inner, text="الفرع:", font=("Segoe UI", 14, "bold"), text_color=TEXT_DARK).pack(
            side="left", padx=(10, 2))

        def load_branches_to_combo():
            if hasattr(self, 'branch_mapping') and self.branch_mapping:
                branches = list(self.branch_mapping.keys())
                self.cmb_bal_branch.configure(values=branches)
                self.cmb_bal_branch.set(branches[0])
            else:
                if hasattr(self, 'nuwairy_load_branches'):
                    self.nuwairy_load_branches()
                self.after(500, load_branches_to_combo)

        load_branches_to_combo()
        self.ent_bal_acc.bind("<Return>", lambda event: execute_search())

        # =========================================
        # 📜 4. منطقة عرض النتائج
        # =========================================
        self.bal_results_scroll = ctk.CTkScrollableFrame(main_container, fg_color="transparent")
        self.bal_results_scroll.pack(fill="both", expand=True, padx=15, pady=(0, 20))

        # =========================================
        # ⚙️ 5. تنفيذ الاستعلام (فائق السرعة)
        # =========================================
        def execute_search():
            branch_name = self.cmb_bal_branch.get().strip()
            acc_num = self.ent_bal_acc.get().strip()

            if not acc_num:
                messagebox.showwarning("تنبيه", "يرجى إدخال رقم العميل أولاً")
                self.ent_bal_acc.focus()
                return

            if not branch_name or branch_name == "جاري التحميل...":
                messagebox.showerror("خطأ", "برجاء اختيار فرع صحيح")
                return

            for widget in self.bal_results_scroll.winfo_children():
                widget.destroy()

            lbl_loading = ctk.CTkLabel(
                self.bal_results_scroll,
                text="⚡ جاري الاستعلام السريع عن أرصدة العميل...",
                font=("Segoe UI", 16, "bold"), text_color=FIB_GOLD
            )
            lbl_loading.pack(pady=50)

            def fetch_data():
                try:
                    engine = getattr(self, '_get_db_connection', lambda: None)()
                    if not engine:
                        raise Exception("لم يتم العثور على دالة الاتصال بقاعدة البيانات.")

                    # 1. تحميل جداول العملات وأنواع الحسابات مرة واحدة في الذاكرة لتجنب بطء LEFT JOIN
                    if self._acc_types_cache is None:
                        try:
                            acc_df = pd.read_sql("SELECT ccod, CNM FROM [dbo].[TBL_AccTypes] WITH (NOLOCK)", engine)
                            self._acc_types_cache = {
                                str(r['ccod']).replace('.0', '').strip(): str(r['CNM']).strip()
                                for _, r in acc_df.iterrows() if pd.notna(r['ccod'])
                            }
                        except Exception:
                            self._acc_types_cache = {}

                    if self._currencies_cache is None:
                        try:
                            cur_df = pd.read_sql("SELECT fcur, cnm FROM [dbo].[tbl_currency] WITH (NOLOCK)", engine)
                            self._currencies_cache = {
                                str(r['fcur']).replace('.0', '').strip(): str(r['cnm']).strip()
                                for _, r in cur_df.iterrows() if pd.notna(r['fcur'])
                            }
                        except Exception:
                            self._currencies_cache = {}

                    # 2. جلب معلومات الفرع (من الكاش أولاً)
                    if branch_name in self._branch_info_cache:
                        branch_code, target_table = self._branch_info_cache[branch_name]
                    else:
                        get_branch_info_sql = """
                            SELECT TOP 1 [BranchCode], [tablename]
                            FROM [dbo].[TBL_Branches] WITH (NOLOCK)
                            WHERE [branchName] = ?
                        """
                        branch_df = pd.read_sql(get_branch_info_sql, engine, params=(branch_name,))
                        if branch_df.empty:
                            raise Exception(f"لم يتم العثور على الفرع '{branch_name}' في جدول TBL_Branches.")

                        branch_code = str(branch_df.iloc[0]['BranchCode']).strip()
                        target_table = str(branch_df.iloc[0]['tablename']).strip()
                        if not target_table:
                            raise Exception("اسم الجدول (tablename) فارغ لهذا الفرع.")

                        self._branch_info_cache[branch_name] = (branch_code, target_table)

                    clean_tbl = target_table if "[" in target_table else f"[dbo].[{target_table}]"

                    # 3. توليد احتمالات رقم العميل (مع وبدون أصفار) لاستخدام الـ Indexes مباشرة بدون دوال SQL
                    clean_acc = str(acc_num).strip()
                    acc_variants = list({clean_acc, clean_acc.lstrip('0'), clean_acc.zfill(6), clean_acc.zfill(7)})
                    placeholders = ",".join(["?"] * len(acc_variants))

                    # استبدال OR بـ UNION لتفعيل Index الـ BCLNT و Index الـ PCLNT في أجزاء من الثانية
                    sql = f"""
                        SELECT PGL, PCLNT, PCUR, PBAL, PAMTM, BNAME
                        FROM {clean_tbl} WITH (NOLOCK)
                        WHERE BCLNT IN ({placeholders})
                        UNION
                        SELECT PGL, PCLNT, PCUR, PBAL, PAMTM, BNAME
                        FROM {clean_tbl} WITH (NOLOCK)
                        WHERE PCLNT IN ({placeholders})
                    """
                    df = pd.read_sql(sql, engine, params=tuple(acc_variants + acc_variants))

                    # ربط أسماء الحسابات والعملات من الذاكرة فوراً
                    if not df.empty:
                        df['AccTypeName'] = df['PGL'].apply(
                            lambda x: self._acc_types_cache.get(str(x).replace('.0', '').strip(), 'غير معرف') if pd.notna(x) else 'غير معرف'
                        )
                        df['CurrencyName'] = df['PCUR'].apply(
                            lambda x: self._currencies_cache.get(str(x).replace('.0', '').strip(), 'غير معرف') if pd.notna(x) else 'غير معرف'
                        )

                    self.after(0, lambda: update_results_ui(df, target_table, branch_code))

                except Exception as e:
                    error_msg = str(e)
                    logging.error(f"Error fetching client balances: {error_msg}")
                    self.after(0, lambda msg=error_msg: update_results_ui(pd.DataFrame(), "", "", error=msg))

            threading.Thread(target=fetch_data, daemon=True).start()

        def update_results_ui(df, table_used, branch_code, error=None):
            for widget in self.bal_results_scroll.winfo_children():
                widget.destroy()

            if error:
                ctk.CTkLabel(
                    self.bal_results_scroll,
                    text=f"❌ حدث خطأ أثناء البحث:\n{error}",
                    font=("Segoe UI", 14, "bold"), text_color="#EF4444"
                ).pack(pady=40)
                return

            if df.empty:
                ctk.CTkLabel(
                    self.bal_results_scroll,
                    text=f"🔍 لا توجد نتائج لرقم العميل ({self.ent_bal_acc.get()}) في جدول [{table_used}]",
                    font=("Segoe UI", 18, "bold"), text_color=TEXT_MUTED
                ).pack(pady=60)
                return

            # 🔍 استخراج اسم العميل الموحد
            valid_cust_names = df[df['BNAME'].notna() & (df['BNAME'].astype(str).str.strip() != '')]['BNAME']
            global_cust_name = str(valid_cust_names.iloc[0]).strip() if not valid_cust_names.empty else "غير مدون"
            acc_num_val = self.ent_bal_acc.get().strip()

            # ============================================
            # 👑 كارت بيانات العميل الثابت (فوق خالص)
            # ============================================
            profile_frame = ctk.CTkFrame(self.bal_results_scroll, fg_color=FIB_GREEN, corner_radius=12)
            profile_frame.pack(fill="x", padx=10, pady=(0, 20))

            ctk.CTkLabel(
                profile_frame,
                text=f"👤 اسم العميل: {global_cust_name}    |    🔢 رقم العميل: {acc_num_val}",
                font=("Segoe UI", 18, "bold"), text_color="white"
            ).pack(pady=15)

            valid_cards = []
            for _, row in df.iterrows():
                pgl_code = str(row['PGL']).replace('.0', '') if pd.notna(row['PGL']) else "—"
                acc_type_name = str(row['AccTypeName']).strip()

                pcur_val = str(row['PCUR']).replace('.0', '') if pd.notna(row['PCUR']) else "—"
                curr_name = str(row['CurrencyName']).strip()

                is_invalid_type = (acc_type_name == "غير معرف" or pgl_code in ["—", "0", "nan"])
                is_invalid_currency = (curr_name == "غير معرف" or pcur_val in ["—", "0", "nan"])

                if is_invalid_type and is_invalid_currency:
                    continue

                valid_cards.append(row)

            summary_bar = ctk.CTkFrame(self.bal_results_scroll, fg_color=CARD_BG, corner_radius=10)
            summary_bar.pack(fill="x", padx=10, pady=(0, 10))

            if len(valid_cards) == 0:
                ctk.CTkLabel(
                    summary_bar,
                    text="⚠️ العميل موجود ولكن لا توجد حسابات أو عملات مسجلة له لعرضها.",
                    font=("Segoe UI", 15, "bold"), text_color="#EF4444"
                ).pack(side="right", padx=15, pady=10)
                return
            else:
                ctk.CTkLabel(
                    summary_bar,
                    text=f"تم العثور على {len(valid_cards)} حساب/حسابات نشطة 📊",
                    font=("Segoe UI", 14, "bold"), text_color=FIB_GREEN
                ).pack(side="right", padx=15, pady=10)

            # ============================================
            # 🗂️ عرض الكروت الخاصة بالحسابات
            # ============================================
            for row in valid_cards:
                pgl_code = str(row['PGL']).replace('.0', '') if pd.notna(row['PGL']) else "—"
                acc_type_name = str(row['AccTypeName']).strip()
                pcur_val = str(row['PCUR']).replace('.0', '') if pd.notna(row['PCUR']) else "—"
                curr_name = str(row['CurrencyName']).strip()

                balance_val = "0.00"
                if 'PBAL' in row and pd.notna(row['PBAL']):
                    try:
                        balance_val = f"{float(row['PBAL']):,.2f}"
                    except Exception:
                        balance_val = str(row['PBAL'])

                amtm_val = "0.00"
                if 'PAMTM' in row and pd.notna(row['PAMTM']):
                    try:
                        amtm_val = f"{float(row['PAMTM']):,.2f}"
                    except Exception:
                        amtm_val = str(row['PAMTM'])

                card = ctk.CTkFrame(self.bal_results_scroll, fg_color=CARD_BG, corner_radius=12, border_width=1,
                                    border_color="#E2E8F0")
                card.pack(fill="x", padx=10, pady=8)

                ctk.CTkFrame(card, fg_color=FIB_GOLD, width=5, corner_radius=0).pack(side="right", fill="y", pady=10)

                card_content = ctk.CTkFrame(card, fg_color="transparent")
                card_content.pack(fill="both", expand=True, padx=20, pady=15)

                header_row = ctk.CTkFrame(card_content, fg_color="transparent")
                header_row.pack(fill="x", pady=(0, 5))

                ctk.CTkLabel(
                    header_row,
                    text=f"نوع الحساب: {acc_type_name} 🏷️",
                    font=("Segoe UI", 16, "bold"), text_color=FIB_GREEN
                ).pack(side="right")

                ctk.CTkLabel(
                    header_row,
                    text=f"العملة: {curr_name} 💰",
                    font=("Segoe UI", 14, "bold"), text_color=TEXT_DARK
                ).pack(side="left")

                ctk.CTkFrame(card_content, fg_color="#F1F5F9", height=2).pack(fill="x", pady=10)

                data_grid = ctk.CTkFrame(card_content, fg_color="transparent")
                data_grid.pack(fill="x")
                data_grid.grid_columnconfigure((0, 1, 2, 3), weight=1)

                def create_info_box(parent_grid, col_idx, title, value, val_color=TEXT_DARK):
                    box = ctk.CTkFrame(parent_grid, fg_color=BOX_BG, corner_radius=8)
                    box.grid(row=0, column=col_idx, padx=4, pady=5, sticky="ew")
                    ctk.CTkLabel(box, text=title, font=("Segoe UI", 11, "bold"), text_color=TEXT_MUTED).pack(
                        anchor="center", pady=(5, 0))
                    ctk.CTkLabel(box, text=value, font=("Segoe UI", 14, "bold"), text_color=val_color).pack(
                        anchor="center", pady=(0, 5))

                create_info_box(data_grid, 3, "الرصيد القائم (PBAL)", balance_val, val_color=FIB_GREEN)
                create_info_box(data_grid, 2, "المبلغ (PAMTM)", amtm_val, val_color=TEXT_DARK)
                create_info_box(data_grid, 1, "كود العملة (PCUR)", pcur_val, val_color=FIB_GOLD)
                create_info_box(data_grid, 0, "كود الحساب (PGL)", pgl_code)