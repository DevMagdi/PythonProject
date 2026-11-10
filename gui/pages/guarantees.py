# -*- coding: utf-8 -*-
"""
شاشة الاستفسار عن خطابات الضمان.

مُرحّلة حرفياً من gui.py الأصلي — منطق البحث والعرض كما هو دون تغيير.
"""
import logging
import re
import threading
import datetime

import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
import pandas as pd

from gui.constants import *
from gui.legacy_page import LegacyInquiryPage


class GuaranteesInquiryPage(LegacyInquiryPage):
    """شاشة الاستفسار عن خطابات الضمان."""
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
            header, text="الاستفسار عن خطابات الضمان لعميل 📜",
            font=("Segoe UI", 22, "bold"), text_color=CARD_BG
        ).pack(side="right", padx=30, pady=15)

        # =========================================
        # 🔍 منطقة البحث (الفرع، العميل، السنة، العملة)
        # =========================================
        search_frame = ctk.CTkFrame(main_container, fg_color=CARD_BG, corner_radius=15, border_width=1,
                                    border_color="#E2E8F0")
        search_frame.pack(fill="x", padx=20, pady=15)

        search_inner = ctk.CTkFrame(search_frame, fg_color="transparent")
        search_inner.pack(side="right", fill="y", padx=20, pady=15)

        # أزرار البحث والمسح
        btn_clear = ctk.CTkButton(search_inner, text="🧹 مسح", font=("Segoe UI", 14, "bold"), fg_color="#64748B",
                                  hover_color="#475569", width=80, height=40, corner_radius=8,
                                  command=lambda: clear_search())
        btn_clear.pack(side="left", padx=(5, 10))

        btn_search = ctk.CTkButton(search_inner, text="🔍 بحث", font=("Segoe UI", 15, "bold"), fg_color=FIB_GREEN,
                                   hover_color="#004426", width=100, height=40, corner_radius=8,
                                   command=lambda: execute_search())
        btn_search.pack(side="left", padx=5)

        # العملة
        self.cmb_lg_currency = ctk.CTkComboBox(search_inner, font=("Segoe UI", 14, "bold"), justify="center", width=120,
                                               height=40, border_color="#CBD5E1")
        self.cmb_lg_currency.pack(side="left", padx=10)
        ctk.CTkLabel(search_inner, text="العملة:", font=("Segoe UI", 14, "bold"), text_color=TEXT_DARK).pack(
            side="left", padx=(10, 2))

        # سنة الإصدار
        current_year = datetime.datetime.now().year
        years_list = [str(y) for y in range(current_year, 1999, -1)]
        self.cmb_lg_year = ctk.CTkComboBox(search_inner, values=years_list, font=("Segoe UI", 14, "bold"),
                                           justify="center", width=100, height=40, border_color="#CBD5E1")
        self.cmb_lg_year.pack(side="left", padx=10)
        ctk.CTkLabel(search_inner, text="حتى سنة:", font=("Segoe UI", 14, "bold"), text_color=TEXT_DARK).pack(
            side="left", padx=(10, 2))

        # رقم العميل
        self.ent_lg_cust_no = ctk.CTkEntry(search_inner, font=("Segoe UI", 15, "bold"), justify="center",
                                           placeholder_text="رقم العميل...", width=140, height=40,
                                           border_color="#CBD5E1")
        self.ent_lg_cust_no.pack(side="left", padx=10)
        ctk.CTkLabel(search_inner, text="رقم العميل:", font=("Segoe UI", 14, "bold"), text_color=TEXT_DARK).pack(
            side="left", padx=(10, 2))

        # الفرع
        if hasattr(self, '_create_premium_select'):
            self.cmb_lg_branch_box, self.cmb_lg_branch = self._create_premium_select(search_inner,
                                                                                     values=["جاري التحميل..."],
                                                                                     default="جاري التحميل...",
                                                                                     title="اختر الفرع")
            self.cmb_lg_branch_box.pack(side="left", padx=10)
        else:
            self.cmb_lg_branch = ctk.CTkComboBox(search_inner, font=("Segoe UI", 14, "bold"), justify="right",
                                                 width=200, height=40, border_color="#CBD5E1")
            self.cmb_lg_branch.pack(side="left", padx=10)
        ctk.CTkLabel(search_inner, text="الفرع:", font=("Segoe UI", 14, "bold"), text_color=TEXT_DARK).pack(side="left",
                                                                                                            padx=(10,
                                                                                                                  2))

        # الفريم الخاص بالنتائج
        self.lg_results_scroll = ctk.CTkScrollableFrame(main_container, fg_color="transparent")
        self.lg_results_scroll.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        # =========================================
        # ⚙️ تحميل الداتا الأولية (الفروع والعملات)
        # =========================================
        def load_initial_data():
            # الفروع
            if hasattr(self, 'branch_mapping') and self.branch_mapping:
                branches = list(self.branch_mapping.keys())
                self.cmb_lg_branch.configure(values=branches)
                self.cmb_lg_branch.set(branches[0])

            # العملات
            if hasattr(self, 'currency_map_name_to_code') and self.currency_map_name_to_code:
                currencies = list(self.currency_map_name_to_code.keys())
                self.cmb_lg_currency.configure(values=currencies)
                if currencies: self.cmb_lg_currency.set(currencies[0])
            else:
                self.cmb_lg_currency.configure(values=["الجنيه المصري", "دولار أمريكي", "يورو"])

        self.after(500, load_initial_data)
        self.ent_lg_cust_no.bind("<Return>", lambda event: execute_search())

        def clear_search():
            self.ent_lg_cust_no.delete(0, 'end')
            for widget in self.lg_results_scroll.winfo_children():
                widget.destroy()

        # =========================================
        # 🚀 تنفيذ البحث وتجميع الداتا
        # =========================================
        def execute_search():
            branch_name = self.cmb_lg_branch.get().strip()
            cust_no = self.ent_lg_cust_no.get().strip()
            selected_year = self.cmb_lg_year.get().strip()
            currency_name = self.cmb_lg_currency.get().strip()

            if not cust_no:
                messagebox.showwarning("تنبيه", "يرجى إدخال رقم العميل")
                return

            if not hasattr(self, 'branch_mapping') or branch_name not in self.branch_mapping:
                messagebox.showerror("خطأ", "برجاء اختيار فرع صحيح")
                return

            branch_info = self.branch_mapping[branch_name]
            branch_code = branch_info[0] if isinstance(branch_info, tuple) else branch_info

            currency_code = getattr(self, 'currency_map_name_to_code', {}).get(currency_name,
                                                                               "1")  # افتراضي 1 لو غير موجود

            for widget in self.lg_results_scroll.winfo_children():
                widget.destroy()

            ctk.CTkLabel(self.lg_results_scroll, text="⚡ جاري البحث عن خطابات الضمان...", font=("Segoe UI", 16, "bold"),
                         text_color=FIB_GOLD).pack(pady=50)

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

                    # 1. جلب اسم الجدول للفرع
                    branch_query = f"SELECT TableName FROM [dbo].[TBL_Branches] WITH (NOLOCK) WHERE BranchCode = '{branch_code}'"
                    branch_df = pd.read_sql(branch_query, engine)

                    if not branch_df.empty and pd.notna(branch_df.iloc[0]['TableName']):
                        target_table = str(branch_df.iloc[0]['TableName']).strip()
                    else:
                        raise Exception("لم يتم العثور على جدول البيانات المربوط بهذا الفرع.")

                    # 2. جلب اسم العميل BNAME من جدول الفرع
                    name_query = f"SELECT BNAME FROM [dbo].[{target_table}] WITH (NOLOCK) WHERE BCLNT = '{cust_str}' OR BCLNT = '{cust_int_str}'"
                    name_df = pd.read_sql(name_query, engine)
                    client_name = str(name_df.iloc[0]['BNAME']).strip() if not name_df.empty else "غير مسجل"

                    # 3. الاستعلام عن خطابات الضمان
                    # افترضت أن كود العملة موجود في عمود LGCUR، يمكنك تعديله إذا كان مختلفاً
                    lg_query = f"""
                        SELECT LGNO, LGTYPE, LGVAL, LGCVRP, LGCVAL, LGCINV, LGIDAT, LGDUDT, LGBNAM
                        FROM [dbo].[TBL_gurantees] WITH (NOLOCK)
                        WHERE LGBR = '{branch_code}' 
                          AND (LGCNO = '{cust_str}' OR LGCNO = '{cust_int_str}')
                          AND LGCUR = '{currency_code}'
                          AND LGIDAT <= '{selected_year}-12-31'
                    """
                    df = pd.read_sql(lg_query, engine)

                    self.after(0, lambda: update_results_ui(df, client_name, cust_no, branch_name, currency_name))
                except Exception as e:
                    logging.error(f"Error fetching guarantees: {e}")
                    self.after(0, lambda: update_results_ui(pd.DataFrame(), "", cust_no, branch_name, currency_name,
                                                            error=str(e)))

            threading.Thread(target=fetch_data, daemon=True).start()

        # =========================================
        # 📑 عرض النتائج (الإجماليات ثم التفاصيل)
        # =========================================
        def update_results_ui(df, client_name, cust_no, branch_name, currency_name, error=None):
            for widget in self.lg_results_scroll.winfo_children():
                widget.destroy()

            if error:
                ctk.CTkLabel(self.lg_results_scroll, text=f"❌ حدث خطأ:\n{error}", font=("Segoe UI", 14, "bold"),
                             text_color="#EF4444").pack(pady=40)
                return

            if df.empty:
                ctk.CTkLabel(self.lg_results_scroll, text="✔️ لا توجد خطابات ضمان مطابقة للبحث",
                             font=("Segoe UI", 18, "bold"), text_color=TEXT_MUTED).pack(pady=60)
                return

            def format_money(val):
                try:
                    return "{:,.2f}".format(float(val))
                except:
                    return "0.00"

            def format_date(val):
                if pd.isna(val): return "—"
                try:
                    return pd.to_datetime(val).strftime('%Y-%m-%d')
                except:
                    return str(val)

            # حساب الإجماليات
            total_lgval = df['LGVAL'].apply(pd.to_numeric, errors='coerce').sum()
            total_lgcinv = df['LGCINV'].apply(pd.to_numeric, errors='coerce').sum()

            # =========================================
            # 💳 كارت الإجماليات (Top Summary Card)
            # =========================================
            summary_card = ctk.CTkFrame(self.lg_results_scroll, fg_color=FIB_GREEN, corner_radius=12)
            summary_card.pack(fill="x", padx=10, pady=(5, 20))

            summary_inner = ctk.CTkFrame(summary_card, fg_color="transparent")
            summary_inner.pack(fill="x", padx=20, pady=15)

            # اسم العميل وبياناته
            client_info = ctk.CTkFrame(summary_inner, fg_color="transparent")
            client_info.pack(side="right")
            ctk.CTkLabel(client_info, text=f"👤 {client_name}", font=("Segoe UI", 20, "bold"), text_color=CARD_BG).pack(
                anchor="e")
            ctk.CTkLabel(client_info, text=f"الفرع: {branch_name} | رقم العميل: {cust_no} | العملة: {currency_name}",
                         font=("Segoe UI", 14), text_color="#E2E8F0").pack(anchor="e")

            # بلوكات الإجماليات
            totals_frame = ctk.CTkFrame(summary_inner, fg_color="transparent")
            totals_frame.pack(side="left")

            tot_box1 = ctk.CTkFrame(totals_frame, fg_color=CARD_BG, corner_radius=8)
            tot_box1.pack(side="left", padx=10)
            ctk.CTkLabel(tot_box1, text="إجمالي قيم خطابات الضمان", font=("Segoe UI", 12, "bold"),
                         text_color=TEXT_MUTED).pack(padx=15, pady=(8, 0))
            ctk.CTkLabel(tot_box1, text=f"{format_money(total_lgval)}", font=("Segoe UI", 18, "bold"),
                         text_color=FIB_GREEN).pack(padx=15, pady=(0, 8))

            tot_box2 = ctk.CTkFrame(totals_frame, fg_color=CARD_BG, corner_radius=8)
            tot_box2.pack(side="left", padx=10)
            ctk.CTkLabel(tot_box2, text="إجمالي ضمان الاستثمار", font=("Segoe UI", 12, "bold"),
                         text_color=TEXT_MUTED).pack(padx=15, pady=(8, 0))
            ctk.CTkLabel(tot_box2, text=f"{format_money(total_lgcinv)}", font=("Segoe UI", 18, "bold"),
                         text_color=FIB_GOLD).pack(padx=15, pady=(0, 8))

            # =========================================
            # 📄 كروت خطابات الضمان (Records)
            # =========================================
            for idx, row in df.iterrows():
                record_card = ctk.CTkFrame(self.lg_results_scroll, fg_color=CARD_BG, corner_radius=10, border_width=1,
                                           border_color="#CBD5E1")
                record_card.pack(fill="x", padx=10, pady=5)

                # رأس الكارت (رقم الخطاب ونوعه والمستفيد)
                rec_header = ctk.CTkFrame(record_card, fg_color="transparent")
                rec_header.pack(fill="x", padx=15, pady=(10, 5))

                ctk.CTkLabel(rec_header, text=f"خطاب رقم: {row.get('LGNO', '—')}", font=("Segoe UI", 16, "bold"),
                             text_color=FIB_GREEN).pack(side="right")
                ctk.CTkLabel(rec_header, text=f"نوع الخطاب: {row.get('LGTYPE', '—')}", font=("Segoe UI", 14, "bold"),
                             text_color=TEXT_DARK, fg_color=BOX_BG, corner_radius=6).pack(side="right", padx=15,
                                                                                          ipadx=8, ipady=2)
                ctk.CTkLabel(rec_header, text=f"الجهة المستفيدة: {row.get('LGBNAM', '—')}",
                             font=("Segoe UI", 14, "bold"), text_color=FIB_GOLD).pack(side="left")

                ctk.CTkFrame(record_card, fg_color="#F1F5F9", height=2).pack(fill="x", padx=15, pady=5)

                # بيانات الكارت
                details_frame = ctk.CTkFrame(record_card, fg_color="transparent")
                details_frame.pack(fill="x", padx=10, pady=(5, 10))

                def create_detail_box(parent, title, value, v_color=TEXT_DARK):
                    box = ctk.CTkFrame(parent, fg_color=BOX_BG, corner_radius=6)
                    box.pack(side="right", fill="x", expand=True, padx=4)
                    ctk.CTkLabel(box, text=title, font=("Segoe UI", 12, "bold"), text_color=TEXT_MUTED).pack(
                        pady=(5, 0))
                    ctk.CTkLabel(box, text=str(value), font=("Segoe UI", 14, "bold"), text_color=v_color).pack(
                        pady=(0, 5))

                # الصف الأول
                row1 = ctk.CTkFrame(details_frame, fg_color="transparent")
                row1.pack(fill="x", pady=2)
                create_detail_box(row1, "قيمة خطاب الضمان (LGVAL)", format_money(row.get('LGVAL')), FIB_GREEN)
                create_detail_box(row1, "قيمة الغطاء (LGCVAL)", format_money(row.get('LGCVAL')), TEXT_DARK)
                create_detail_box(row1, "قيمة ضمان استثمار (LGCINV)", format_money(row.get('LGCINV')), FIB_GOLD)

                # الصف الثاني
                row2 = ctk.CTkFrame(details_frame, fg_color="transparent")
                row2.pack(fill="x", pady=2)
                create_detail_box(row2, "تاريخ الإصدار (LGIDAT)", format_date(row.get('LGIDAT')), TEXT_DARK)
                create_detail_box(row2, "تاريخ انتهاء الصلاحية (LGDUDT)", format_date(row.get('LGDUDT')),
                                  "#DC2626")  # أحمر للتنبيه
                create_detail_box(row2, "كود تحصيل الغطاء (LGCVRP)", row.get('LGCVRP', '—'), TEXT_MUTED)
