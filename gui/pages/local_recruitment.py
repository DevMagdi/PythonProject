# -*- coding: utf-8 -*-
"""
شاشة بحث التوظيف المحلي.

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


class LocalRecruitmentPage(LegacyInquiryPage):
    """شاشة بحث التوظيف المحلي."""
    LOAD_BRANCHES_ON_SHOW = True

    def build(self):
        """بناء الشاشة — الكود القديم كما هو (parent = الشاشة نفسها)."""
        parent = self

        # =========================================
        # 🎨 1. Theme Colors & Styles
        # =========================================
        FIB_GREEN = "#005C34"
        FIB_GOLD = "#C5A059"
        BG_MAIN = "#F8FAFC"
        CARD_BG = "#FFFFFF"
        BOX_BG = "#F1F5F9"
        TEXT_DARK = "#0F172A"
        TEXT_MUTED = "#64748B"

        # الحاوية الرئيسية
        main_container = ctk.CTkFrame(parent, fg_color=BG_MAIN)
        main_container.pack(fill="both", expand=True)

        # الهيدر العلوي
        header = ctk.CTkFrame(main_container, fg_color=FIB_GREEN, height=65, corner_radius=0)
        header.pack(fill="x")
        header.pack_propagate(False)

        ctk.CTkFrame(main_container, fg_color=FIB_GOLD, height=4, corner_radius=0).pack(fill="x")

        title_lbl = ctk.CTkLabel(
            header,
            text="بحث التوظيف المحلي للعملاء 💼",
            font=("Segoe UI", 22, "bold"),
            text_color=CARD_BG
        )
        title_lbl.pack(side="right", padx=30, pady=15)

        # =========================================
        # 🔍 2. Search Area
        # =========================================
        search_frame = ctk.CTkFrame(main_container, fg_color=CARD_BG, corner_radius=15, border_width=1,
                                    border_color="#E2E8F0")
        search_frame.pack(fill="x", padx=20, pady=15)

        search_inner = ctk.CTkFrame(search_frame, fg_color="transparent")
        search_inner.pack(side="right", fill="y", padx=20, pady=15)

        # --- زر مسح البيانات ---
        btn_clear = ctk.CTkButton(
            search_inner, text="🧹 مسح", font=("Segoe UI", 14, "bold"),
            fg_color="#64748B", hover_color="#475569", text_color="white",
            width=90, height=40, corner_radius=8, command=lambda: clear_search()
        )
        btn_clear.pack(side="left", padx=(5, 10))

        # --- زر البحث ---
        btn_search = ctk.CTkButton(
            search_inner, text="🔍 بحث", font=("Segoe UI", 15, "bold"),
            fg_color=FIB_GREEN, hover_color="#004426", text_color="white",
            width=110, height=40, corner_radius=8, command=lambda: execute_search()
        )
        btn_search.pack(side="left", padx=5)

        # --- إدخال رقم العميل ---
        self.ent_recruitment_cust_no = ctk.CTkEntry(
            search_inner, font=("Segoe UI", 15, "bold"),
            justify="center", placeholder_text="رقم العميل...",
            width=180, height=40, border_color="#CBD5E1"
        )
        self.ent_recruitment_cust_no.pack(side="left", padx=10)

        ctk.CTkLabel(search_inner, text="رقم العميل:", font=("Segoe UI", 14, "bold"), text_color=TEXT_DARK).pack(
            side="left", padx=(10, 2))

        # --- قائمة الفروع ---
        if hasattr(self, '_create_premium_select'):
            self.cmb_recruitment_branch_box, self.cmb_recruitment_branch = self._create_premium_select(
                search_inner,
                values=["جاري التحميل..."],
                default="جاري التحميل...",
                title="اختر الفرع"
            )
            self.cmb_recruitment_branch_box.pack(side="left", padx=10)
        else:
            self.cmb_recruitment_branch = ctk.CTkComboBox(
                search_inner, font=("Segoe UI", 14, "bold"), justify="right",
                width=230, height=40, border_color="#CBD5E1"
            )
            self.cmb_recruitment_branch.pack(side="left", padx=10)

        ctk.CTkLabel(search_inner, text="الفرع:", font=("Segoe UI", 14, "bold"), text_color=TEXT_DARK).pack(side="left",
                                                                                                            padx=(10,
                                                                                                                  2))

        # شريط ملخص النتائج / العداد
        self.recruitment_summary_lbl = ctk.CTkLabel(main_container, text="", font=("Segoe UI", 13, "bold"),
                                                    text_color=TEXT_MUTED)
        self.recruitment_summary_lbl.pack(anchor="e", padx=25, pady=(0, 5))

        # تحميل الفروع
        def load_branches_to_combo():
            if hasattr(self, 'branch_mapping') and self.branch_mapping:
                branches = list(self.branch_mapping.keys())
                self.cmb_recruitment_branch.configure(values=branches)
                self.cmb_recruitment_branch.set(branches[0])
            else:
                if hasattr(self, 'nuwairy_load_branches'):
                    self.nuwairy_load_branches()
                self.after(500, load_branches_to_combo)

        load_branches_to_combo()
        self.ent_recruitment_cust_no.bind("<Return>", lambda event: execute_search())

        # =========================================
        # 📜 3. Results Container
        # =========================================
        self.recruitment_results_scroll = ctk.CTkScrollableFrame(main_container, fg_color="transparent")
        self.recruitment_results_scroll.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        def clear_search():
            self.ent_recruitment_cust_no.delete(0, 'end')
            self.recruitment_summary_lbl.configure(text="")
            for widget in self.recruitment_results_scroll.winfo_children():
                widget.destroy()

        def format_money(val):
            try:
                if pd.isna(val) or val == "":
                    return "0.00"
                return f"{float(val):,.2f}"
            except:
                return str(val)

        # =========================================
        # ⚙️ 4. Search & Thread Execution
        # =========================================
        def execute_search():
            branch_name = self.cmb_recruitment_branch.get().strip()
            cust_no = self.ent_recruitment_cust_no.get().strip()

            if not cust_no:
                messagebox.showwarning("تنبيه", "يرجى إدخال رقم العميل أولاً")
                self.ent_recruitment_cust_no.focus()
                return

            if not hasattr(self, 'branch_mapping') or branch_name not in self.branch_mapping:
                messagebox.showerror("خطأ", "برجاء اختيار فرع صحيح")
                return

            branch_info = self.branch_mapping[branch_name]
            branch_code = branch_info[0] if isinstance(branch_info, tuple) else branch_info

            # تفريغ الواجهة لعرض أنيميشن التحميل
            for widget in self.recruitment_results_scroll.winfo_children():
                widget.destroy()

            self.recruitment_summary_lbl.configure(text="")
            lbl_loading = ctk.CTkLabel(
                self.recruitment_results_scroll,
                text="⚡ جاري الاستعلام عن التوظيف المحلي...",
                font=("Segoe UI", 16, "bold"), text_color=FIB_GOLD
            )
            lbl_loading.pack(pady=50)

            def fetch_data():
                try:
                    engine = getattr(self, '_get_db_connection', lambda: None)()
                    if not engine:
                        raise Exception("لم يتم العثور على دالة الاتصال بقاعدة البيانات.")

                    # --- تجهيز رقم العميل ---
                    cust_str = cust_no.strip()
                    try:
                        cust_int_str = str(int(cust_str))
                    except:
                        cust_int_str = cust_str

                    # 1. جلب خريطة العملات من tbl_currency (fcur -> cnm)
                    currency_map = {}
                    try:
                        curr_query = "SELECT fcur, cnm FROM [dbo].[tbl_currency] WITH (NOLOCK)"
                        curr_df = pd.read_sql(curr_query, engine)
                        if not curr_df.empty:
                            for _, crow in curr_df.iterrows():
                                if pd.notna(crow.get('fcur')) and pd.notna(crow.get('cnm')):
                                    k = str(crow['fcur']).strip()
                                    v = str(crow['cnm']).strip()
                                    currency_map[k] = v
                    except Exception as curr_err:
                        logging.warning(f"Error fetching currencies: {curr_err}")

                    # 2. جلب اسم الجدول من TBL_Branches
                    target_table = None
                    try:
                        branch_query = f"SELECT TableName FROM [dbo].[TBL_Branches] WITH (NOLOCK) WHERE BranchCode = '{branch_code}'"
                        branch_df = pd.read_sql(branch_query, engine)
                        if not branch_df.empty and pd.notna(branch_df.iloc[0]['TableName']):
                            target_table = str(branch_df.iloc[0]['TableName']).strip()
                    except Exception as b_err:
                        logging.error(f"Error fetching TableName: {b_err}")

                    # 3. جلب اسم العميل
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
                                fetched_client_name = str(client_df.iloc[0].get('BNAME')).strip()
                        except Exception as cl_err:
                            logging.warning(f"Could not fetch client name: {cl_err}")

                    # 4. جلب بيانات التوظيف المحلي
                    sql = f"""
                        SELECT IGL, ISUB, ICUR, ICOD, IAMT17, IAMT19, IAMT20, IAMT21
                        FROM [dbo].[tbl_localrecruitmentprocesses] WITH (NOLOCK)
                        WHERE iclnt = '{cust_str}' OR iclnt = '{cust_int_str}'
                    """
                    df = pd.read_sql(sql, engine)

                    # 5. مطابقة كود العملة باسم العملة من tbl_currency
                    if not df.empty and 'ICUR' in df.columns:
                        df['CURRENCY_NAME'] = df['ICUR'].astype(str).str.strip().map(currency_map)
                        # لو الكود مش موجود في جدول العملات يرجع نفس الكود الأصلي
                        df['CURRENCY_NAME'] = df['CURRENCY_NAME'].fillna(df['ICUR'].astype(str))

                    self.after(0, lambda: update_results_ui(df, fetched_client_name, cust_no, branch_name))
                except Exception as e:
                    logging.error(f"Error fetching recruitment: {e}")
                    self.after(0, lambda: update_results_ui(pd.DataFrame(), "غير مسجل", cust_no, branch_name, error=str(e)))

            threading.Thread(target=fetch_data, daemon=True).start()

        def update_results_ui(df, client_name, cust_no, branch_name, error=None):
            for widget in self.recruitment_results_scroll.winfo_children():
                widget.destroy()

            if error:
                self.recruitment_summary_lbl.configure(text="")
                ctk.CTkLabel(
                    self.recruitment_results_scroll,
                    text=f"❌ حدث خطأ أثناء الاتصال بقاعدة البيانات:\n{error}",
                    font=("Segoe UI", 14, "bold"), text_color="#EF4444"
                ).pack(pady=40)
                return

            # =========================================
            # 🚀 التعديل الجديد: استبعاد العمليات الصفرية
            # =========================================
            if not df.empty and 'IAMT19' in df.columns:
                # تحويل عمود قيمة العملية لأرقام (ولو فيه خطأ يعتبره صفر)
                df['IAMT19_numeric'] = pd.to_numeric(df['IAMT19'], errors='coerce').fillna(0)
                # فلترة الداتا واختيار العمليات اللي قيمتها لا تساوي صفر فقط
                df = df[df['IAMT19_numeric'] != 0]

            if df.empty:
                self.recruitment_summary_lbl.configure(text="")
                ctk.CTkLabel(
                    self.recruitment_results_scroll,
                    text="🔍 لا توجد بيانات توظيف محلي مسجلة لهذا العميل (أو العمليات قيمتها صفر)",
                    font=("Segoe UI", 18, "bold"), text_color=TEXT_MUTED
                ).pack(pady=60)
                return

            # تحديث عداد النتائج (هيقرا العدد بعد استبعاد الأصفار)
            self.recruitment_summary_lbl.configure(text=f"إجمالي عدد العمليات: {len(df)}")

            # =========================================
            # 👤 كارت بيانات العميل الرئيسي
            # =========================================
            client_header_card = ctk.CTkFrame(self.recruitment_results_scroll, fg_color=CARD_BG, corner_radius=12,
                                              border_width=1, border_color="#CBD5E1")
            client_header_card.pack(fill="x", padx=10, pady=(5, 15))

            client_inner = ctk.CTkFrame(client_header_card, fg_color="transparent")
            client_inner.pack(fill="x", padx=20, pady=12)

            ctk.CTkLabel(client_inner, text=f"👤 اسم العميل: {client_name}", font=("Segoe UI", 16, "bold"),
                         text_color=FIB_GREEN).pack(side="right")
            ctk.CTkLabel(client_inner, text=f"الفرع: {branch_name} | رقم العميل: {cust_no}",
                         font=("Segoe UI", 13, "bold"), text_color=TEXT_MUTED, fg_color=BOX_BG, corner_radius=6).pack(
                side="left", ipadx=10, ipady=3)

            # =========================================
            # 📑 رندر كروت العمليات
            # =========================================
            for _, row in df.iterrows():
                # جسم الكارت
                card = ctk.CTkFrame(
                    self.recruitment_results_scroll, fg_color=CARD_BG, corner_radius=12,
                    border_width=1, border_color="#E2E8F0"
                )
                card.pack(fill="x", padx=10, pady=8)

                # شريط جانبي
                ctk.CTkFrame(card, fg_color=FIB_GOLD, width=6, corner_radius=0).pack(side="right", fill="y", pady=10)

                card_content = ctk.CTkFrame(card, fg_color="transparent")
                card_content.pack(fill="both", expand=True, padx=20, pady=15)

                # --- صف رأس الكارت (الأكواد الأساسية) ---
                header_row = ctk.CTkFrame(card_content, fg_color="transparent")
                header_row.pack(fill="x", pady=(0, 10))

                curr_display = row.get('CURRENCY_NAME', row.get('ICUR', '—'))

                ctk.CTkLabel(
                    header_row,
                    text=f"العملة: {curr_display}",
                    font=("Segoe UI", 13, "bold"),
                    text_color="#FFFFFF",
                    fg_color=FIB_GREEN,
                    corner_radius=6
                ).pack(side="left", ipadx=10, ipady=3)
                ctk.CTkLabel(header_row, text=f"الأستاذ الفرع (ISUB): {row.get('ISUB', '—')}",
                             font=("Segoe UI", 14, "bold"), text_color=TEXT_MUTED).pack(side="right", padx=15)
                ctk.CTkLabel(header_row, text=f"الأستاذ العام (IGL): {row.get('IGL', '—')}",
                             font=("Segoe UI", 14, "bold"), text_color=TEXT_MUTED).pack(side="right", padx=15)

                # خط فاصل
                ctk.CTkFrame(card_content, fg_color="#F1F5F9", height=2).pack(fill="x", pady=6)

                # --- شبكة القيم والمبالغ ---
                data_grid = ctk.CTkFrame(card_content, fg_color="transparent")
                data_grid.pack(fill="x", pady=5)
                data_grid.grid_columnconfigure((0, 1, 2, 3), weight=1)

                def create_info_box(parent, col_idx, title, value, val_color=TEXT_DARK):
                    box = ctk.CTkFrame(parent, fg_color=BOX_BG, corner_radius=8)
                    box.grid(row=0, column=col_idx, padx=5, pady=5, sticky="ew")
                    ctk.CTkLabel(box, text=title, font=("Segoe UI", 12, "bold"), text_color=TEXT_MUTED).pack(
                        anchor="center", pady=(6, 2))
                    ctk.CTkLabel(box, text=format_money(value), font=("Segoe UI", 16, "bold"),
                                 text_color=val_color).pack(anchor="center", pady=(0, 6))

                # المربعات (من اليمين لليسار في الجريد: col=3 لـ col=0)
                create_info_box(data_grid, 3, "قيمة العملية", row.get('IAMT17', 0), val_color=TEXT_DARK)
                create_info_box(data_grid, 2, "رصيد العملية", abs(float(row.get('IAMT19', 0) or 0)),
                                val_color=FIB_GREEN)
                create_info_box(data_grid, 1, "رصيد متناقص", abs(float(row.get('IAMT20', 0) or 0)), val_color=FIB_GOLD)
                create_info_box(data_grid, 0, "متأخرات", abs(float(row.get('IAMT21', 0) or 0)), val_color="#DC2626")
