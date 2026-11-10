# -*- coding: utf-8 -*-
"""
شاشة الاستفسار عن تعليمات عميل.

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


class InstructionsPage(LegacyInquiryPage):
    """شاشة الاستفسار عن تعليمات عميل."""
    LOAD_BRANCHES_ON_SHOW = True

    def build(self):
        """بناء الشاشة — الكود القديم كما هو (parent = الشاشة نفسها)."""
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

        # شريط ملخص النتائج / العداد (مثل التوكيلات)
        self.instructions_summary_lbl = ctk.CTkLabel(main_container, text="", font=("Segoe UI", 13, "bold"),
                                                     text_color=TEXT_MUTED)
        self.instructions_summary_lbl.pack(anchor="e", padx=25, pady=(0, 5))

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

        # --- دالة تنظيف اسم العميل فقط ---
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
            self.instructions_summary_lbl.configure(text="")
            for widget in self.instructions_results_scroll.winfo_children():
                widget.destroy()

        # =========================================
        # ⚙️ 4. Search Engine Logic
        # =========================================
        def execute_search():
            branch_name = self.cmb_instructions_branch.get().strip()
            cust_no = self.ent_instructions_cust_no.get().strip()

            if not cust_no:
                messagebox.showwarning("تنبيه", "يرجى إدخال رقم العميل أولاً")
                self.ent_instructions_cust_no.focus()
                return

            # التحقق بنفس طريقة التوكيلات تماماً
            if not hasattr(self, 'branch_mapping') or branch_name not in self.branch_mapping:
                messagebox.showerror("خطأ", "برجاء اختيار فرع صحيح")
                return

            # جلب كود الفرع فقط من الـ mapping (لغينا محاولة جلب اسم الجدول من هنا)
            branch_info = self.branch_mapping[branch_name]
            branch_code = branch_info[0] if isinstance(branch_info, (tuple, list)) else branch_info

            for widget in self.instructions_results_scroll.winfo_children():
                widget.destroy()

            self.instructions_summary_lbl.configure(text="")
            lbl_loading = ctk.CTkLabel(
                self.instructions_results_scroll,
                text="⚡ جاري البحث عن تعليمات العميل...",
                font=("Segoe UI", 16, "bold"),
                text_color=FIB_GOLD
            )
            lbl_loading.pack(pady=50)

            def fetch_data():
                try:
                    engine = getattr(self, '_get_db_connection', lambda: None)()
                    if not engine:
                        raise Exception("لم يتم العثور على دالة الاتصال بقاعدة البيانات.")

                    # --- التعديل الجديد: جلب اسم الجدول من TBL_Branches ---
                    target_table = None
                    try:
                        # افترضنا هنا إن اسم حقل كود الفرع في الجدول هو BranchCode، راجع الاسم لو مختلف عندك
                        branch_query = f"SELECT TableName FROM [dbo].[TBL_Branches] WITH (NOLOCK) WHERE BranchCode = N'{branch_code}'"
                        branch_df = pd.read_sql(branch_query, engine)
                        if not branch_df.empty and pd.notna(branch_df.iloc[0]['TableName']):
                            target_table = str(branch_df.iloc[0]['TableName']).strip()
                    except Exception as b_err:
                        print(f"DEBUG Error fetching TableName from TBL_Branches: {b_err}")
                        logging.error(f"Error fetching TableName from TBL_Branches: {b_err}")
                    # --------------------------------------------------------

                    # 1. جلب اسم العميل مع طباعة أسباب عدم الظهور للتشخيص
                    fetched_client_name = "غير مسجل"

                    print(
                        f"DEBUG: target_table = '{target_table}', branch_code = '{branch_code}', cust_no = '{cust_no}'")

                    if target_table and pd.notna(target_table) and str(target_table).strip():
                        try:
                            tbl_str = str(target_table).strip()

                            # استعلام مرن يتعامل مع الأرقام سواء بأصفار على الشمال أو بدونها
                            client_query = f"""
                                SELECT TOP 1 BNAME 
                                FROM [dbo].[{tbl_str}] WITH (NOLOCK) 
                                WHERE LTRIM(RTRIM(BCLNT)) = N'{cust_no}' 
                                   OR TRY_CAST(BCLNT AS INT) = TRY_CAST(N'{cust_no}' AS INT)
                            """
                            client_df = pd.read_sql(client_query, engine)

                            if not client_df.empty:
                                raw_bname = client_df.iloc[0].get('BNAME')
                                print(f"DEBUG: Found Raw BNAME from DB = '{raw_bname}'")
                                if pd.notna(raw_bname) and str(raw_bname).strip():
                                    fetched_client_name = str(raw_bname).strip()
                            else:
                                print(f"DEBUG: No rows returned from [{tbl_str}] for cust_no '{cust_no}'")

                        except Exception as cl_err:
                            print(f"DEBUG Error in client_query: {cl_err}")
                            logging.warning(f"Could not fetch client name: {cl_err}")
                    else:
                        print(f"DEBUG: target_table is EMPTY or NONE for branch '{branch_name}'.")

                    # 2. الاستعلام الرئيسي المباشر من جدول تعليمات الحسابات
                    sql = f"""
                        SELECT tmm, tnm1, tnm2, tdat, tmh
                        FROM [dbo].[tbl_instructionsBankAccounts] WITH (NOLOCK)
                        WHERE (nbr = N'{branch_code}' OR tbr = N'{branch_code}') 
                          AND (nclnt = N'{cust_no}' OR tclnt = N'{cust_no}')
                    """
                    df = pd.read_sql(sql, engine)

                    self.after(0, lambda: update_results_ui(df, fetched_client_name, cust_no, branch_name))
                except Exception as e:
                    logging.error(f"Error fetching instructions: {e}")
                    self.after(0, lambda: update_results_ui(pd.DataFrame(), "غير مسجل", cust_no, branch_name,
                                                            error=str(e)))

            threading.Thread(target=fetch_data, daemon=True).start()

        def update_results_ui(df, client_name, cust_no, branch_name, error=None):
            for widget in self.instructions_results_scroll.winfo_children():
                widget.destroy()

            if error:
                self.instructions_summary_lbl.configure(text="")
                ctk.CTkLabel(
                    self.instructions_results_scroll,
                    text=f"❌ حدث خطأ أثناء البحث:\n{error}",
                    font=("Segoe UI", 14, "bold"),
                    text_color="#EF4444"
                ).pack(pady=40)
                return

            if df.empty:
                self.instructions_summary_lbl.configure(text="")
                ctk.CTkLabel(
                    self.instructions_results_scroll,
                    text="🔍 لا توجد تعليمات مسجلة لهذا العميل في هذا الفرع",
                    font=("Segoe UI", 18, "bold"),
                    text_color=TEXT_MUTED
                ).pack(pady=60)
                return

            # تحديث عداد النتائج
            self.instructions_summary_lbl.configure(text=f"إجمالي عدد التعليمات المضبوطة: {len(df)}")

            # تنظيف اسم العميل للعرض في أعلى النتائج
            cleaned_client_name = clean_arabic_name(client_name)

            # =========================================
            # 👤 1. كارت بيانات العميل الرئيسي
            # =========================================
            client_header_card = ctk.CTkFrame(
                self.instructions_results_scroll,
                fg_color=CARD_BG,
                corner_radius=12,
                border_width=1,
                border_color="#CBD5E1"
            )
            client_header_card.pack(fill="x", padx=10, pady=(5, 15))

            client_inner = ctk.CTkFrame(client_header_card, fg_color="transparent")
            client_inner.pack(fill="x", padx=20, pady=12)

            ctk.CTkLabel(
                client_inner,
                text=f"👤 اسم العميل: {cleaned_client_name}",
                font=("Segoe UI", 16, "bold"),
                text_color=FIB_GREEN
            ).pack(side="right")

            ctk.CTkLabel(
                client_inner,
                text=f"الفرع: {branch_name} | رقم العميل: {cust_no}",
                font=("Segoe UI", 13, "bold"),
                text_color=TEXT_MUTED,
                fg_color=BOX_BG,
                corner_radius=6
            ).pack(side="left", ipadx=10, ipady=3)

            # =========================================
            # 📑 2. إنشاء كارت لكل تعليمات
            # =========================================
            for _, row in df.iterrows():
                instruction_serial = str(row['tmm']).replace('.0', '') if pd.notna(row['tmm']) else "—"
                text1 = str(row['tnm1']).strip() if pd.notna(row['tnm1']) else ""
                text2 = str(row['tnm2']).strip() if pd.notna(row['tnm2']) else ""
                trans_date = format_date_str(row['tdat'])

                # كود الإلغاء tmh (1 = ملغي, 0 = ساري)
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

                # شريط ملون جانبي يعبر عن الحالة
                stripe_color = status_color if tmh_val in ['0', '1'] else FIB_GOLD
                ctk.CTkFrame(card, fg_color=stripe_color, width=6, corner_radius=0).pack(side="right", fill="y",
                                                                                         pady=10)

                card_content = ctk.CTkFrame(card, fg_color="transparent")
                card_content.pack(fill="both", expand=True, padx=20, pady=12)

                # صف العنوان (مسلسل التعليمات والحالة)
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

                # صندوق نصوص التعليمات (tnm1 & tnm2)
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

                # صف تاريخ الحركة
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
