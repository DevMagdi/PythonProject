# -*- coding: utf-8 -*-
"""
شاشة الاستفسار عن حركة فواتير العلاج الطبي.

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


class MedicalBillsMovementPage(LegacyInquiryPage):
    """شاشة الاستفسار عن حركة فواتير العلاج الطبي."""
    LOAD_BRANCHES_ON_SHOW = False

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
            header, text="حركة فواتير العلاج الطبي 🧾",
            font=("Segoe UI", 22, "bold"), text_color=CARD_BG
        ).pack(side="right", padx=30, pady=15)

        # =========================================
        # 🔍 منطقة البحث (رقم الملف والنوع)
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

        # اختيار النوع
        self.cmb_bill_type = ctk.CTkComboBox(search_inner, font=("Segoe UI", 14, "bold"), justify="right",
                                             values=["1 - موظف", "2 - أسري"], width=130, height=40,
                                             border_color="#CBD5E1")
        self.cmb_bill_type.pack(side="left", padx=10)
        ctk.CTkLabel(search_inner, text="رقم النوع:", font=("Segoe UI", 14, "bold"), text_color=TEXT_DARK).pack(
            side="left", padx=(10, 2))

        # إدخال رقم الملف
        self.ent_bill_file_no = ctk.CTkEntry(search_inner, font=("Segoe UI", 15, "bold"), justify="center",
                                             placeholder_text="رقم الملف...", width=160, height=40,
                                             border_color="#CBD5E1")
        self.ent_bill_file_no.pack(side="left", padx=10)
        ctk.CTkLabel(search_inner, text="رقم الملف:", font=("Segoe UI", 14, "bold"), text_color=TEXT_DARK).pack(
            side="left", padx=(10, 2))

        # حاوية النتائج (بها السكرول الرئيسي للشاشة كلها)
        self.bills_results_scroll = ctk.CTkScrollableFrame(main_container, fg_color="transparent")
        self.bills_results_scroll.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        # =========================================
        # ⚙️ دوال المساعدة وتحميل البيانات
        # =========================================
        self.ent_bill_file_no.bind("<Return>", lambda event: execute_search())

        def clear_search():
            self.ent_bill_file_no.delete(0, 'end')
            self.cmb_bill_type.set("1 - موظف")
            for widget in self.bills_results_scroll.winfo_children():
                widget.destroy()

        def safe_float(val):
            try:
                if pd.isna(val) or str(val).strip() == '':
                    return 0.0
                return float(val)
            except (ValueError, TypeError):
                return 0.0

        def safe_int(val):
            try:
                if pd.isna(val) or str(val).strip() == '':
                    return -1
                return int(float(val))
            except (ValueError, TypeError):
                return -1

        # =========================================
        # 🚀 تنفيذ الاستعلامات
        # =========================================
        def execute_search():
            file_no = self.ent_bill_file_no.get().strip()
            # أخذ الرقم الأول من الكومبوبوكس (1 أو 2)
            type_val = self.cmb_bill_type.get().split(" ")[0]

            if not file_no:
                messagebox.showwarning("تنبيه", "يرجى إدخال رقم الملف")
                return

            for widget in self.bills_results_scroll.winfo_children():
                widget.destroy()

            ctk.CTkLabel(self.bills_results_scroll, text="⚡ جاري جلب حركات الفواتير...", font=("Segoe UI", 16, "bold"),
                         text_color=FIB_GOLD).pack(pady=50)

            def fetch_data():
                try:
                    engine = getattr(self, '_get_db_connection', lambda: None)()
                    if not engine:
                        raise Exception("لا يوجد اتصال بقاعدة البيانات.")

                    # 1️⃣ جلب بيانات الموظف (الاسم، الفرع، رقم الحساب، تاريخ التعيين) من TBL_medical_treatment
                    q_info = "SELECT Pname, pclnt, PBr, PDATM FROM [dbo].[TBL_medical_treatment] WITH (NOLOCK) WHERE PDOC = ?"
                    df_info = pd.read_sql(q_info, engine, params=(file_no,))

                    if df_info.empty:
                        self.after(0, lambda: update_results_ui(None, None,
                                                                error="لم يتم العثور على بيانات لرقم الملف المدخل."))
                        return

                    emp_name = str(df_info.iloc[0]['Pname']).strip()
                    acc_no = str(df_info.iloc[0]['pclnt']).strip()
                    pbr = str(df_info.iloc[0]['PBr']).strip()
                    pdatm = df_info.iloc[0]['PDATM']

                    # 2️⃣ مطابقة PBr مع جدول الفروع لجلب اسم الفرع
                    q_branch = "SELECT branchname FROM [dbo].[tbl_branches] WITH (NOLOCK) WHERE branchcode = ?"
                    df_branch = pd.read_sql(q_branch, engine, params=(pbr,))
                    branch_name = str(df_branch.iloc[0]['branchname']).strip() if not df_branch.empty else pbr

                    emp_info = {
                        "name": emp_name,
                        "acc_no": acc_no,
                        "branch": branch_name,
                        "hire_date": pdatm
                    }

                    # 3️⃣ جلب بيانات الحركات والفواتير بناءً على رقم الملف والنوع المختار
                    q_bills = """
                              SELECT FDAT1, FTIM, FAMT, FCOD1, FKND2, FNO
                              FROM [dbo].[TBL_medical_treatment] \
                              WITH (NOLOCK)
                              WHERE FDOC = ? AND FKND2 = ? \
                              """
                    df_bills = pd.read_sql(q_bills, engine, params=(file_no, type_val))

                    self.after(0, lambda: update_results_ui(emp_info, df_bills))
                except Exception as e:
                    err_msg = str(e)
                    logging.error(f"Error fetching medical bills: {err_msg}")
                    self.after(0, lambda: update_results_ui(None, None, error=err_msg))

            threading.Thread(target=fetch_data, daemon=True).start()

        # =========================================
        # 📑 عرض الواجهة الإحصائية للنتائج
        # =========================================
        def update_results_ui(emp_info, df_bills, error=None):
            for widget in self.bills_results_scroll.winfo_children():
                widget.destroy()

            if error:
                ctk.CTkLabel(self.bills_results_scroll, text=f"❌ حدث خطأ:\n{error}", font=("Segoe UI", 14, "bold"),
                             text_color="#EF4444").pack(pady=40)
                return

            if not emp_info:
                return

            # ==================== كارت معلومات الموظف ====================
            header_card = ctk.CTkFrame(self.bills_results_scroll, fg_color=CARD_BG, corner_radius=12, border_width=1,
                                       border_color="#CBD5E1")
            header_card.pack(fill="x", padx=10, pady=(5, 10))

            top_row = ctk.CTkFrame(header_card, fg_color="transparent")
            top_row.pack(fill="x", padx=20, pady=15)

            ctk.CTkLabel(top_row, text=f"👤 {emp_info['name']}", font=("Segoe UI", 18, "bold"),
                         text_color=TEXT_DARK).pack(side="right")

            info_tags = ctk.CTkFrame(top_row, fg_color="transparent")
            info_tags.pack(side="left")

            hire_date_str = pd.to_datetime(emp_info['hire_date']).strftime('%Y-%m-%d') if pd.notna(
                emp_info['hire_date']) else "—"

            ctk.CTkLabel(info_tags, text=f"تاريخ التعيين: {hire_date_str}", font=("Segoe UI", 13, "bold"),
                         text_color=TEXT_DARK, fg_color=BOX_BG, corner_radius=6).pack(side="left", padx=4, ipadx=8,
                                                                                      ipady=3)
            ctk.CTkLabel(info_tags, text=f"الحساب: {emp_info['acc_no']}", font=("Segoe UI", 13, "bold"),
                         text_color=FIB_GOLD, fg_color=BOX_BG, corner_radius=6).pack(side="left", padx=4, ipadx=8,
                                                                                     ipady=3)
            ctk.CTkLabel(info_tags, text=f"الفرع: {emp_info['branch']}", font=("Segoe UI", 13, "bold"),
                         text_color=TEXT_MUTED, fg_color=BOX_BG, corner_radius=6).pack(side="left", padx=4, ipadx=8,
                                                                                       ipady=3)

            if df_bills is None or df_bills.empty:
                ctk.CTkLabel(self.bills_results_scroll, text="✔️ لا توجد فواتير مسجلة لهذا النوع.",
                             font=("Segoe UI", 16, "bold"), text_color=TEXT_MUTED).pack(pady=40)
                return

            # ==================== جدول البيانات (Premium Data Grid المظبوط بالمللي) ====================
            table_container = ctk.CTkFrame(self.bills_results_scroll, fg_color=CARD_BG, corner_radius=12,
                                           border_width=1, border_color="#E2E8F0")
            table_container.pack(fill="both", expand=True, padx=10, pady=(0, 10))

            ctk.CTkLabel(table_container, text=f"🧾 تفاصيل حركة الفواتير ({len(df_bills)})",
                         font=("Segoe UI", 15, "bold"), text_color=FIB_GREEN).pack(anchor="e", padx=15, pady=10)

            # 1. رأس الجدول (Header)
            header_row = ctk.CTkFrame(table_container, fg_color=FIB_GREEN, corner_radius=6, height=40)
            header_row.pack(fill="x", padx=10, pady=(0, 5))
            header_row.pack_propagate(False)

            # الأعمدة بترتيب عربي (التاريخ على اليمين خالص)
            columns = ["مبلغ أنجال", "مبلغ موظف/زوجة", "الطبيب", "نوع العلاج", "الحركة", "الوقت", "التاريخ"]
            for i, col_name in enumerate(columns):
                # 🚀 سر التظبيط هنا: uniform="col" بيخلي كل الأعمدة نفس المقاس غصب عنها، فمستحيل تترحل
                header_row.grid_columnconfigure(i, weight=1, uniform="col")
                ctk.CTkLabel(header_row, text=col_name, font=("Segoe UI", 13, "bold"), text_color=CARD_BG).grid(row=0,
                                                                                                                column=i,
                                                                                                                pady=8)

            # 2. جسم الجدول (هنا استخدمنا فريم عادي من غير سكرول عشان الشاشة كلها مفرودة في صفحة واحدة)
            table_body = ctk.CTkFrame(table_container, fg_color="transparent")
            table_body.pack(fill="both", expand=True, padx=10, pady=5)

            def format_date(val):
                if pd.isna(val) or str(val).strip() == '': return "—"
                try:
                    return pd.to_datetime(val).strftime('%Y-%m-%d')
                except:
                    return str(val)

            for index, row in df_bills.iterrows():
                # تلوين تبادلي لراحة العين
                row_color = BOX_BG if index % 2 == 0 else CARD_BG

                row_frame = ctk.CTkFrame(table_body, fg_color=row_color, corner_radius=4, height=38)
                row_frame.pack(fill="x", pady=1)
                row_frame.pack_propagate(False)

                fdat1 = format_date(row.get('FDAT1'))
                ftim = row.get('FTIM', '—')
                famt = safe_float(row.get('FAMT', 0))
                fcod1 = safe_int(row.get('FCOD1'))
                fknd2 = safe_int(row.get('FKND2'))
                fno = str(row.get('FNO', '—'))

                # Mapping
                if fcod1 in [1, 2]:
                    fcod_str, fcod_color = "إضافة", FIB_GREEN
                elif fcod1 in [3, 4]:
                    fcod_str, fcod_color = "خصم", "#DC2626"
                else:
                    fcod_str, fcod_color = str(fcod1), TEXT_MUTED

                if fknd2 == 2:
                    fknd_str = "أدوية"
                elif fknd2 == 3:
                    fknd_str = "تحاليل وأشعة"
                elif fknd2 == 8:
                    fknd_str = "تجاوزات"
                else:
                    fknd_str = str(fknd2)

                emp_wife_amt = famt if fcod1 == 2 else 0.0
                children_amt = famt if fcod1 != 2 else 0.0

                # وضع الداتا بنفس ترتيب رأس الجدول (من الشمال لليمين عشان تترسم صح بالعربي)
                values_and_colors = [
                    (f"{children_amt:,.2f}", "#0369A1" if children_amt > 0 else TEXT_MUTED),
                    (f"{emp_wife_amt:,.2f}", FIB_GREEN if emp_wife_amt > 0 else TEXT_MUTED),
                    (fno, TEXT_MUTED),
                    (fknd_str, TEXT_DARK),
                    (fcod_str, fcod_color),
                    (ftim, TEXT_DARK),
                    (fdat1, TEXT_DARK)
                ]

                for i, (val, color) in enumerate(values_and_colors):
                    # 🚀 سر التظبيط للصفوف: نفس الـ uniform="col" فتنزل الداتا تحت رأس الجدول بالمللي
                    row_frame.grid_columnconfigure(i, weight=1, uniform="col")
                    ctk.CTkLabel(row_frame, text=val, font=("Segoe UI", 13, "bold"), text_color=color).grid(row=0,
                                                                                                            column=i,
                                                                                                            pady=8)
