# -*- coding: utf-8 -*-
"""
شاشة الاستفسار عن العملاء المتعثرين.

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


class DefaultingClientPage(LegacyInquiryPage):
    """شاشة الاستفسار عن العملاء المتعثرين."""
    LOAD_BRANCHES_ON_SHOW = True

    def build(self):
        """بناء الشاشة — الكود القديم كما هو (parent = الشاشة نفسها)."""
        parent = self

        # =========================================
        # 🎨 الألوان والتنسيقات (نفس الثيم المعتمد)
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
            header, text="الاستفسار عن عميل متعثر ⚠️",
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

        btn_clear = ctk.CTkButton(search_inner, text="🧹 مسح", font=("Segoe UI", 14, "bold"), fg_color="#64748B",
                                  hover_color="#475569", width=90, height=40, corner_radius=8,
                                  command=lambda: clear_search())
        btn_clear.pack(side="left", padx=(5, 10))

        btn_search = ctk.CTkButton(search_inner, text="🔍 بحث", font=("Segoe UI", 15, "bold"), fg_color=FIB_GREEN,
                                   hover_color="#004426", width=110, height=40, corner_radius=8,
                                   command=lambda: execute_search())
        btn_search.pack(side="left", padx=5)

        self.ent_defaulter_cust_no = ctk.CTkEntry(search_inner, font=("Segoe UI", 15, "bold"), justify="center",
                                                  placeholder_text="رقم العميل...", width=160, height=40,
                                                  border_color="#CBD5E1")
        self.ent_defaulter_cust_no.pack(side="left", padx=10)
        ctk.CTkLabel(search_inner, text="رقم الحساب:", font=("Segoe UI", 14, "bold"), text_color=TEXT_DARK).pack(
            side="left", padx=(10, 2))

        if hasattr(self, '_create_premium_select'):
            self.cmb_defaulter_branch_box, self.cmb_defaulter_branch = self._create_premium_select(search_inner,
                                                                                                   values=[
                                                                                                       "جاري التحميل..."],
                                                                                                   default="جاري التحميل...",
                                                                                                   title="اختر الفرع")
            self.cmb_defaulter_branch_box.pack(side="left", padx=10)
        else:
            self.cmb_defaulter_branch = ctk.CTkComboBox(search_inner, font=("Segoe UI", 14, "bold"), justify="right",
                                                        width=220, height=40, border_color="#CBD5E1")
            self.cmb_defaulter_branch.pack(side="left", padx=10)
        ctk.CTkLabel(search_inner, text="الفرع:", font=("Segoe UI", 14, "bold"), text_color=TEXT_DARK).pack(side="left",
                                                                                                            padx=(10,
                                                                                                                  2))

        self.defaulter_results_scroll = ctk.CTkScrollableFrame(main_container, fg_color="transparent")
        self.defaulter_results_scroll.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        # =========================================
        # ⚙️ تحميل الداتا الأولية (الفروع والعملات)
        # =========================================
        def load_initial_data():
            if hasattr(self, 'branch_mapping') and self.branch_mapping:
                branches = list(self.branch_mapping.keys())
                self.cmb_defaulter_branch.configure(values=branches)
                self.cmb_defaulter_branch.set(branches[0])
            else:
                if hasattr(self, 'nuwairy_load_branches'):
                    self.nuwairy_load_branches()
                self.after(500, load_initial_data)

        load_initial_data()
        self.ent_defaulter_cust_no.bind("<Return>", lambda event: execute_search())

        def clear_search():
            self.ent_defaulter_cust_no.delete(0, 'end')
            for widget in self.defaulter_results_scroll.winfo_children():
                widget.destroy()

        # =========================================
        # 🚀 تنفيذ البحث
        # =========================================
        def execute_search():
            branch_name = self.cmb_defaulter_branch.get().strip()
            cust_no = self.ent_defaulter_cust_no.get().strip()

            if not cust_no:
                messagebox.showwarning("تنبيه", "يرجى إدخال رقم العميل")
                return

            if not hasattr(self, 'branch_mapping') or branch_name not in self.branch_mapping:
                messagebox.showerror("خطأ", "برجاء اختيار فرع صحيح")
                return

            branch_info = self.branch_mapping[branch_name]
            branch_code = branch_info[0] if isinstance(branch_info, tuple) else branch_info

            for widget in self.defaulter_results_scroll.winfo_children():
                widget.destroy()

            ctk.CTkLabel(self.defaulter_results_scroll, text="⚡ جاري البحث عن بيانات العميل المتعثر...",
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

                    # 1. جلب اسم الجدول الديناميكي من جدول الفروع
                    target_table = None
                    branch_query = f"SELECT TableName FROM [dbo].[TBL_Branches] WITH (NOLOCK) WHERE BranchCode = '{branch_code}'"
                    branch_df = pd.read_sql(branch_query, engine)

                    if not branch_df.empty and pd.notna(branch_df.iloc[0]['TableName']):
                        target_table = str(branch_df.iloc[0]['TableName']).strip()
                    else:
                        raise Exception("لم يتم العثور على جدول البيانات المربوط بهذا الفرع.")

                    # 2. الاستعلام من الجدول الهدف
                    client_query = f"""
                        SELECT Dcur, ddat, Dname, dcod, dtel1, dtel2, ddat1, ddat2, 
                               dno, damt1, damt2, damt3, damt4, damt5, damt6, damt7, damt8, damt9, damt10, dclntm
                        FROM [dbo].[tbl_defaulted_customers] WITH (NOLOCK)
                        WHERE DBR = '{branch_code}' 
                          AND (Dclnt = '{cust_str}' OR Dclnt = '{cust_int_str}')
                    """
                    df = pd.read_sql(client_query, engine)

                    self.after(0, lambda: update_results_ui(df, cust_no, branch_name))
                except Exception as e:
                    logging.error(f"Error fetching defaulter: {e}")
                    self.after(0, lambda: update_results_ui(pd.DataFrame(), cust_no, branch_name, error=str(e)))

            threading.Thread(target=fetch_data, daemon=True).start()

        # =========================================
        # 📑 عرض النتائج
        # =========================================
        def update_results_ui(df, cust_no, branch_name, error=None):
            for widget in self.defaulter_results_scroll.winfo_children():
                widget.destroy()

            if error:
                ctk.CTkLabel(self.defaulter_results_scroll, text=f"❌ حدث خطأ:\n{error}", font=("Segoe UI", 14, "bold"),
                             text_color="#EF4444").pack(pady=40)
                return

            if df.empty:
                ctk.CTkLabel(self.defaulter_results_scroll, text="✔️ لا توجد بيانات تعثر مطابقة لهذا العميل",
                             font=("Segoe UI", 18, "bold"), text_color=TEXT_MUTED).pack(pady=60)
                return

            # الدوال المساعدة للتنسيق
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

            def create_stat_box(parent_frame, title, value, v_color, bg_color=BOX_BG):
                box = ctk.CTkFrame(parent_frame, fg_color=bg_color, corner_radius=8)
                box.pack(side="right", fill="x", expand=True, padx=4)
                ctk.CTkLabel(box, text=title, font=("Segoe UI", 12, "bold"), text_color=TEXT_MUTED).pack(
                    anchor="center", pady=(8, 2))
                ctk.CTkLabel(box, text=str(value), font=("Segoe UI", 16, "bold"), text_color=v_color).pack(
                    anchor="center", pady=(0, 8))

            row = df.iloc[0]  # عرض أول نتيجة للعميل

            client_name = str(row.get('Dname', 'غير مسجل')).strip()
            currency_code = str(row.get('Dcur', '—')).strip()
            currency_name = getattr(self, 'currency_map_code_to_name', {}).get(currency_code, currency_code)

            # 1. كارت البيانات الأساسية
            main_card = ctk.CTkFrame(self.defaulter_results_scroll, fg_color=CARD_BG, corner_radius=12, border_width=1,
                                     border_color="#CBD5E1")
            main_card.pack(fill="x", padx=10, pady=(5, 15))

            top_info = ctk.CTkFrame(main_card, fg_color="transparent")
            top_info.pack(fill="x", padx=20, pady=12)

            ctk.CTkLabel(top_info, text=f"👤 {client_name}", font=("Segoe UI", 18, "bold"), text_color=FIB_GREEN).pack(
                side="right")
            ctk.CTkLabel(top_info, text=f"الفرع: {branch_name} | رقم العميل: {cust_no}", font=("Segoe UI", 13, "bold"),
                         text_color=TEXT_MUTED, fg_color=BOX_BG, corner_radius=6).pack(side="left", ipadx=10, ipady=3)

            ctk.CTkFrame(main_card, fg_color="#F1F5F9", height=2).pack(fill="x", padx=20, pady=5)

            # بيانات التواصل والهوية
            contact_frame = ctk.CTkFrame(main_card, fg_color="transparent")
            contact_frame.pack(fill="x", padx=15, pady=(5, 15))

            create_stat_box(contact_frame, "رقم بالمركزي", row.get('dclntm', '—'), TEXT_DARK)
            create_stat_box(contact_frame, "الشكل القانوني", row.get('dcod', '—'), TEXT_DARK)
            create_stat_box(contact_frame, "محمول", row.get('dtel2', '—'), FIB_GOLD)
            create_stat_box(contact_frame, "تليفون أرضي", row.get('dtel1', '—'), TEXT_MUTED)

            # التواريخ
            dates_frame = ctk.CTkFrame(main_card, fg_color="transparent")
            dates_frame.pack(fill="x", padx=15, pady=(0, 15))

            create_stat_box(dates_frame, "تاريخ الحركة", format_date(row.get('ddat')), TEXT_DARK)
            create_stat_box(dates_frame, "تاريخ التوقف", format_date(row.get('ddat2')), "#DC2626",
                            bg_color="#FEE2E2")  # لون أحمر خفيف
            create_stat_box(dates_frame, "تاريخ بدء التعامل", format_date(row.get('ddat1')), FIB_GREEN)
            create_stat_box(dates_frame, "عدد الجدولات", row.get('dno', '0'), TEXT_MUTED)

            # 2. كارت البيانات المالية (damt1 to damt10)
            fin_card = ctk.CTkFrame(self.defaulter_results_scroll, fg_color=CARD_BG, corner_radius=12, border_width=1,
                                    border_color="#E2E8F0")
            fin_card.pack(fill="x", padx=10, pady=8)

            fin_header = ctk.CTkFrame(fin_card, fg_color="transparent")
            fin_header.pack(fill="x", padx=15, pady=(15, 5))
            ctk.CTkLabel(fin_header, text=f"💰 الموقف المالي (العملة: {currency_name})", font=("Segoe UI", 16, "bold"),
                         text_color=FIB_GOLD).pack(side="right")

            ctk.CTkFrame(fin_card, fg_color="#F1F5F9", height=2).pack(fill="x", padx=15, pady=5)

            # الصف المالي الأول
            fin_row1 = ctk.CTkFrame(fin_card, fg_color="transparent")
            fin_row1.pack(fill="x", padx=15, pady=(5, 5))
            create_stat_box(fin_row1, "إجمالي الالتزامات (damt9)", format_money(row.get('damt9', 0)), "#DC2626")
            create_stat_box(fin_row1, "الرصيد المدين (damt7)", format_money(row.get('damt7', 0)), "#EA580C")
            create_stat_box(fin_row1, "إجمالي المسدد (damt4)", format_money(row.get('damt4', 0)), FIB_GREEN)
            create_stat_box(fin_row1, "إجمالي المتأخرات (damt5)", format_money(row.get('damt5', 0)), "#DC2626")

            # الصف المالي الثاني
            fin_row2 = ctk.CTkFrame(fin_card, fg_color="transparent")
            fin_row2.pack(fill="x", padx=15, pady=5)
            create_stat_box(fin_row2, "المخصص للمديونية (damt10)", format_money(row.get('damt10', 0)), TEXT_DARK)
            create_stat_box(fin_row2, "التزامات أخرى (damt8)", format_money(row.get('damt8', 0)), TEXT_MUTED)
            create_stat_box(fin_row2, "العوائد المعلقة (damt6)", format_money(row.get('damt6', 0)), TEXT_MUTED)
            create_stat_box(fin_row2, "التعويضات وعائد الجدولة (damt3)", format_money(row.get('damt3', 0)), FIB_GOLD)

            # الصف المالي الثالث
            fin_row3 = ctk.CTkFrame(fin_card, fg_color="transparent")
            fin_row3.pack(fill="x", padx=15, pady=(5, 15))
            create_stat_box(fin_row3, "عائد البنك للعمليات (damt2)", format_money(row.get('damt2', 0)), FIB_GREEN)
            create_stat_box(fin_row3, "تمويل البنك للعمليات (damt1)", format_money(row.get('damt1', 0)), TEXT_DARK)
