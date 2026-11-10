# -*- coding: utf-8 -*-
"""
شاشة استعلام الحسابات (Account Inquiry).

مُرحّلة حرفياً من gui.py الأصلي — منطق البحث والعرض كما هو دون تغيير.
"""
import getpass
import logging
import re
import threading
from datetime import datetime
import os
import tempfile

from sqlalchemy import text
import xlsxwriter
import arabic_reshaper

import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
import pandas as pd
from bidi.algorithm import get_display
from PIL import Image
from tksheet import Sheet
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Spacer, Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_RIGHT, TA_CENTER, TA_LEFT

from gui.constants import *
from gui.legacy_page import LegacyInquiryPage


class NuwairyPage(LegacyInquiryPage):
    """شاشة استعلام الحسابات (Account Inquiry)."""
    LOAD_BRANCHES_ON_SHOW = False

    def build(self):
        """بناء الشاشة — الكود القديم كما هو (parent = الشاشة نفسها)."""
        parent = self

        # =========================
        # Page Wrapper
        # =========================
        page = ctk.CTkFrame(parent, fg_color="transparent")
        page.pack(fill="both", expand=True)

        # =========================
        # Header Bar (Title + Subtitle + Actions)
        # =========================
        header = ctk.CTkFrame(
            page,
            fg_color=COLOR_WHITE,
            corner_radius=14,
            border_width=1,
            border_color="#E6E8EB"
        )
        header.pack(fill="x", padx=10, pady=(0, 12))

        header_inner = ctk.CTkFrame(header, fg_color="transparent")
        header_inner.pack(fill="x", padx=16, pady=14)

        # 1. التعديل هنا: العنوان يروح يمين (right)
        title_wrap = ctk.CTkFrame(header_inner, fg_color="transparent")
        title_wrap.pack(side="right", fill="x", expand=True)

        ctk.CTkLabel(
            title_wrap,
            text="🔍 استعلام حركات العملاء",
            font=("Segoe UI", 22, "bold"),
            text_color=FIB_GREEN
        ).pack(anchor="e")  # المحاذاة يمين (e)

        ctk.CTkLabel(
            title_wrap,
            text="ابحث برقم العميل، اختر نوع الحساب والعملة، وحدد فترة التاريخ (اختياري).",
            font=("Segoe UI", 12),
            text_color="#6B7280"
        ).pack(anchor="e", pady=(4, 0))  # المحاذاة يمين (e)

        # 2. التعديل هنا: الزراير تروح شمال (left)
        actions = ctk.CTkFrame(header_inner, fg_color="transparent")
        actions.pack(side="left")

        def _clear_filters():
            if hasattr(self, 'sys_logger'):
                self.sys_logger.log("🧹 المستخدم قام بمسح فلاتر استعلام حركات العملاء وإفراغ الشاشة.")
            if hasattr(self, "ent_client_no"):
                self.ent_client_no.delete(0, "end")

            if hasattr(self, "cmb_acc_type"):
                self.cmb_acc_type.configure(values=["- أدخل العميل أولاً -"])
                self.cmb_acc_type.set("- أدخل العميل أولاً -")

            if hasattr(self, "cmb_currency"):
                self.cmb_currency.configure(values=["- اختر نوع الحساب أولاً -"])
                self.cmb_currency.set("- اختر نوع الحساب أولاً -")

            if hasattr(self, "ent_date_from"):
                self.ent_date_from.delete(0, "end")
            if hasattr(self, "ent_date_to"):
                self.ent_date_to.delete(0, "end")

            if hasattr(self, "lbl_branch_info"):
                self.lbl_branch_info.configure(text="—")

            if hasattr(self, "sheet"):
                try:
                    self.sheet.set_sheet_data([], reset_col_positions=False, reset_row_positions=True)
                except:
                    pass

        # 3. التعديل هنا: ترتيب الزراير جوه الحاوية يبدأ من اليمين لليسار (side="right")
        self.btn_clear_nuwairy = ctk.CTkButton(
            actions,
            text="مسح",
            fg_color="#F3F4F6",
            text_color="#111827",
            hover_color="#E5E7EB",
            font=("Segoe UI", 12, "bold"),
            height=38,
            corner_radius=10,
            command=_clear_filters
        )
        self.btn_clear_nuwairy.pack(side="right", padx=(10, 0))  # عكسنا الـ padx

        self.btn_search_nuwairy = ctk.CTkButton(
            actions,
            text="بحث الحركات 🔎",
            fg_color=FIB_GOLD,
            text_color="white",
            hover_color="#B78F38",
            font=("Segoe UI", 12, "bold"),
            height=38,
            corner_radius=10,
            command=self.nuwairy_fetch_transactions
        )
        self.btn_search_nuwairy.pack(side="right")

        # =========================
        # Filters Card (الـ Grid بتاعك هنا ممتاز جداً ومظبوط عربي)
        # =========================
        form_card = ctk.CTkFrame(
            page,
            fg_color=COLOR_WHITE,
            corner_radius=14,
            border_width=1,
            border_color="#E6E8EB"
        )
        form_card.pack(fill="x", padx=10, pady=(0, 12))

        form = ctk.CTkFrame(form_card, fg_color="transparent")
        form.pack(fill="x", padx=16, pady=16)
        form.columnconfigure((0, 1, 2, 3), weight=1, pad=10)

        label_font = ("Segoe UI", 12, "bold")

        # Row 1
        ctk.CTkLabel(form, text="الفرع:", font=label_font, text_color=COLOR_TEXT_MAIN).grid(
            row=0, column=3, sticky="e", pady=(0, 8)
        )
        self.cmb_branch_box, self.cmb_branch = self._create_premium_select(
            form,
            values=["جاري التحميل..."],
            default="جاري التحميل...",
            title="اختر الفرع"
        )
        # 4. التعديل هنا: عكسنا الـ padx في المربعات عشان تدي مسافة من ناحية اليمين
        self.cmb_branch_box.grid(row=0, column=2, sticky="ew", pady=(0, 8), padx=(0, 10))

        ctk.CTkLabel(form, text="رقم العميل:", font=label_font, text_color=COLOR_TEXT_MAIN).grid(
            row=0, column=1, sticky="e", pady=(0, 8)
        )
        self.ent_client_no = ctk.CTkEntry(
            form,
            placeholder_text="اكتب رقم العميل واضغط Enter",
            justify="right",  # إضافة: الكتابة جوه المربع تبدأ من اليمين
            height=40,
            corner_radius=10
        )
        self.ent_client_no.grid(row=0, column=0, sticky="ew", pady=(0, 8), padx=(0, 10))
        self.ent_client_no.bind("<Return>", self.nuwairy_fetch_accounts)

        # Row 2
        ctk.CTkLabel(form, text="نوع الحساب:", font=label_font, text_color=COLOR_TEXT_MAIN).grid(
            row=1, column=3, sticky="e", pady=(0, 8)
        )
        self.cmb_acc_type_box, self.cmb_acc_type = self._create_premium_select(
            form,
            values=["- أدخل العميل أولاً -"],
            default="- أدخل العميل أولاً -",
            title="اختر نوع الحساب"
        )
        self.cmb_acc_type_box.grid(row=1, column=2, sticky="ew", pady=(0, 8), padx=(0, 10))

        ctk.CTkLabel(form, text="العملة:", font=label_font, text_color=COLOR_TEXT_MAIN).grid(
            row=1, column=1, sticky="e", pady=(0, 8)
        )
        self.cmb_currency_box, self.cmb_currency = self._create_premium_select(
            form,
            values=["- أدخل العميل أولاً -"],
            default="- أدخل العميل أولاً -",
            title="اختر العملة"
        )
        self.cmb_currency_box.grid(row=1, column=0, sticky="ew", pady=(0, 8), padx=(0, 10))

        # Row 3 (Dates)
        ctk.CTkLabel(form, text="من تاريخ:", font=label_font, text_color=COLOR_TEXT_MAIN).grid(
            row=2, column=3, sticky="e"
        )
        self.ent_date_from = ctk.CTkEntry(
            form,
            placeholder_text="YYYY-MM-DD أو YYYYMMDD",
            justify="right",  # إضافة
            height=40,
            corner_radius=10
        )
        self.ent_date_from.grid(row=2, column=2, sticky="ew", padx=(0, 10))

        ctk.CTkLabel(form, text="إلى تاريخ:", font=label_font, text_color=COLOR_TEXT_MAIN).grid(
            row=2, column=1, sticky="e"
        )
        self.ent_date_to = ctk.CTkEntry(
            form,
            placeholder_text="YYYY-MM-DD أو YYYYMMDD",
            justify="right",  # إضافة
            height=40,
            corner_radius=10
        )
        self.ent_date_to.grid(row=2, column=0, sticky="ew", padx=(0, 10))

        # =========================
        # Info Card
        # =========================
        info_card = ctk.CTkFrame(
            page,
            fg_color=COLOR_WHITE,
            corner_radius=14,
            border_width=1,
            border_color="#E6E8EB"
        )
        info_card.pack(fill="x", padx=10, pady=(0, 12))

        info_inner = ctk.CTkFrame(info_card, fg_color="transparent")
        info_inner.pack(fill="x", padx=16, pady=14)

        # 5. التعديل هنا: محاذاة النص لليمين (anchor="e")
        ctk.CTkLabel(
            info_inner,
            text="بيانات العميل",
            font=("Segoe UI", 12, "bold"),
            text_color=COLOR_TEXT_MAIN
        ).pack(anchor="e")

        self.lbl_branch_info = ctk.CTkLabel(
            info_inner,
            text="—",
            font=("Segoe UI", 12),
            text_color="#4B5563",
            justify="right",  # التعديل هنا لليمين
            anchor="e",  # التعديل هنا لليمين
            wraplength=900
        )
        self.lbl_branch_info.pack(anchor="e", pady=(6, 0))

        # =========================
        # Results (Excel-like Sheet) + Toolbar
        # =========================
        table_card = ctk.CTkFrame(
            page,
            fg_color=COLOR_WHITE,
            corner_radius=14,
            border_width=1,
            border_color="#E6E8EB"
        )
        table_card.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        table_inner = ctk.CTkFrame(table_card, fg_color="transparent")
        table_inner.pack(fill="both", expand=True, padx=12, pady=12)

        toolbar = ctk.CTkFrame(table_inner, fg_color="transparent")
        toolbar.pack(fill="x", pady=(0, 10))

        # 6. التعديل هنا: شريط البحث يروح يمين
        self.ent_search = ctk.CTkEntry(toolbar, placeholder_text="بحث داخل النتائج…", justify="right", height=36,
                                       corner_radius=10)
        self.ent_search.pack(side="right", fill="x", expand=True, padx=(10, 0))

        # زراير التصدير تترص من اليمين للشمال
        btn_export = ctk.CTkButton(
            toolbar, text="🖨️ Export PDF",
            fg_color=FIB_GREEN, hover_color="#0B5C3A",
            height=36, corner_radius=10,
            font=("Segoe UI", 12, "bold"),
            command=self.nuwairy_export_pdf
        )
        btn_export.pack(side="right")

        btn_export_excel = ctk.CTkButton(
            toolbar, text="📊 Export Excel",
            fg_color=FIB_GREEN, hover_color="#0B5C3A",
            height=36, corner_radius=10,
            font=("Segoe UI", 12, "bold"),
            command=self.nuwairy_export_excel
        )
        btn_export_excel.pack(side="right", padx=(0, 10))

        sheet_frame = ctk.CTkFrame(table_inner, fg_color="transparent")
        sheet_frame.pack(fill="both", expand=True)

        self._init_nuwairy_sheet(sheet_frame)

        # تحميل الفروع
        self.nuwairy_load_branches()

    def _init_nuwairy_sheet(self, parent):
        self.sheet = Sheet(
            parent,
            show_x_scrollbar=True,
            show_y_scrollbar=True,
            show_row_index=False,
            show_top_left=False,
            align="e",  # 👈 التعديل الأول: محاذاة البيانات لليمين
            header_align="e",  # 👈 التعديل الثاني: محاذاة العناوين لليمين
            height=450,
            width=900,
            outline_thickness=1,
            outline_color="#E6E8EB",
            grid_color="#E5E7EB",
            selected_cells_bg="#DDEFE8",
            selected_cells_fg="#111827",
        )

        # ✅ لازم الهيدر يطابق عدد عناصر row = 9
        headers = [
            "التاريخ",
            "البيان",
            "دائن",
            "مدين",
            "الرصيد",
            "اسم الحركة",
            "الحساب الرئيسي",
            "الحساب الفرعي",
            "رقم النمارة",  # ✅ الجديد
        ]
        self.sheet.headers(headers)

        # ✅ 9 widths بدل 7 (الوصف أكبر + nseq صغير)
        self.sheet.set_column_widths([120, 520, 130, 130, 150, 180, 170, 140, 90])

        self.sheet.pack(fill="both", expand=True)

    def nuwairy_fetch_accounts(self, event=None):

        branch_name = self.cmb_branch.get()
        client_no = self.ent_client_no.get().strip()
        if hasattr(self, 'sys_logger'):
            self.sys_logger.log(f"🔍 أداة الاستعلام: المستخدم يبحث عن رقم العميل [{client_no}]")

        if not client_no:
            messagebox.showwarning("تنبيه", "يرجى إدخال رقم العميل أولاً")
            return

        branch_code = str(self.branch_mapping.get(branch_name, "")).strip()
        table_name = self.branch_table_mapping.get(branch_code)
        if not branch_code:
            messagebox.showerror("خطأ", "لم يتم العثور على كود الفرع!")
            return

        if not table_name:
            messagebox.showerror("خطأ", f"لا يوجد جدول مربوط بالفرع ده (BranchCode={branch_code})")
            return

        try:
            engine = self._get_db_connection()

            # ==========================================
            # 🛡️ البوابة الأمنية: حماية الحسابات المحظورة
            # ==========================================
            current_user = getpass.getuser()
            current_user = re.sub(r'[\\/*?:"<>|]', "_", current_user)

            check_query = text("""
                DECLARE @User NVARCHAR(100) = :user;
                DECLARE @Client NVARCHAR(100) = :client;

                IF EXISTS (SELECT 1 FROM [dbo].[TBL_RESTRICTED_NUWAIRY] WHERE Client_No = @Client)
                BEGIN
                    IF EXISTS (SELECT 1 FROM [dbo].[TBL_RESTRICTED_NUWAIRY] WHERE Client_No = @Client AND Allowed_User = @User) OR @User = 'Admin'
                        SELECT 'ALLOWED' AS Status
                    ELSE
                        SELECT 'DENIED' AS Status
                END
                ELSE
                BEGIN
                    SELECT 'ALLOWED' AS Status
                END
            """)

            perm_df = pd.read_sql(check_query, engine, params={"user": current_user, "client": client_no})

            if not perm_df.empty and perm_df.iloc[0]['Status'] == 'DENIED':
                messagebox.showerror("مرفوض",
                                     "⛔ هذا الحساب محظور (VIP / حسابات داخلية). ليس لديك صلاحية للاستعلام عنه.")
                if hasattr(self, 'sys_logger'):
                    self.sys_logger.log(
                        f"🚨 وصول مرفوض: المستخدم [{current_user}] حاول الاستعلام عن العميل المحظور [{client_no}]",
                        "WARNING")

                # إخفاء وتصفير أي بيانات للعميل
                self.cmb_acc_type.configure(values=["- حساب محظور -"])
                self.cmb_acc_type.set("- حساب محظور -")
                self.cmb_currency.configure(values=["-"])
                self.cmb_currency.set("-")
                if hasattr(self, "lbl_branch_info"):
                    self.lbl_branch_info.configure(text="⛔ تم حجب بيانات العميل للحماية.")

                if hasattr(self, "sheet"):
                     self.sheet.set_sheet_data([], reset_col_positions=False, reset_row_positions=True)
                return
            # ==========================================
            # ✅ نهاية البوابة الأمنية - اللوجيك القديم بيكمل من هنا
            # ==========================================

            # التعديل هنا: جلبنا أنواع الحسابات والعملات فقط بدل كل حركات العميل!
            # 📌 أداء: محتاج Index على جدول الحركة (NCLNT) — بيُبحث بيها في كل استعلام
            q1 = text(f"""
                SELECT DISTINCT ngl, ncur
                FROM {table_name}
                WHERE NCLNT = :client_no
            """)
            df = pd.read_sql(q1, engine, params={"client_no": client_no})

            # 📌 أداء: نفس الفكرة على (BCLNT)
            q2 = text(f"""
                SELECT DISTINCT Bname, BADRS3, BADRS4
                FROM {table_name}
                WHERE BCLNT = :client_no
            """)
            df2 = pd.read_sql(q2, engine, params={"client_no": client_no})

            if hasattr(self, "lbl_branch_info"):
                if not df2.empty:
                    bname = str(df2.iloc[0].get("Bname", "") or "")
                    adr3 = str(df2.iloc[0].get("BADRS3", "") or "")
                    adr4 = str(df2.iloc[0].get("BADRS4", "") or "")
                    self.lbl_branch_info.configure(text=f"اسم العميل: {bname}\nالعنوان: {adr3}   {adr4}")
                else:
                    q3 = text(f"""
                                                        SELECT DISTINCT EBname, EBADRS3, EBADRS4
                                                        FROM {table_name}
                                                        WHERE EBCLNT = :client_no
                                                    """)
                    df3 = pd.read_sql(q2, engine, params={"client_no": client_no})
                    ebname = str(df2.iloc[0].get("EBname", "") or "")
                    ebadr3 = str(df2.iloc[0].get("EBADRS3", "") or "")
                    ebadr4 = str(df2.iloc[0].get("EBADRS4", "") or "")
                    self.lbl_branch_info.configure(text=f"اسم العميل: {ebname}\nالعنوان: {ebadr3}   {ebadr4}")
                    #self.lbl_branch_info.configure(text="لا توجد بيانات فرع/عنوان لهذا العميل.")

            # مسحنا الـ self.nuwairy_df لأننا مش هنحمل الملايين في الميموري

            if df.empty:
                self.cmb_acc_type.configure(values=["لا يوجد حسابات"])
                self.cmb_acc_type.set("لا يوجد حسابات")
                self.cmb_currency.configure(values=["-"])
                self.cmb_currency.set("-")
                return

            # ===== reference: Currency
            q_cur = text("SELECT FCUR, CNM FROM TBL_Currency")
            cur_df = pd.read_sql(q_cur, engine)
            currency_code_to_name = dict(
                zip(cur_df["FCUR"].astype(str).str.strip(), cur_df["CNM"].astype(str).str.strip())
            )

            # ===== reference: Account Types
            q_acc = text("SELECT CCOD, CNM FROM dbo.TBL_AccTypes")
            acc_df = pd.read_sql(q_acc, engine)
            acc_code_to_name = dict(
                zip(acc_df["CCOD"].astype(str).str.strip(), acc_df["CNM"].astype(str).str.strip())
            )

            # ===== reference: Transaction Codes
            q_trx = text("SELECT ncod1, ntnm FROM dbo.TBL_trx_code")
            trx_df = pd.read_sql(q_trx, engine)
            trx_code_to_name = dict(
                zip(trx_df["ncod1"].astype(str).str.strip(), trx_df["ntnm"].astype(str).str.strip())
            )

            self.acc_code_to_name = acc_code_to_name
            self.trx_code_to_name = trx_code_to_name

            acc_codes = sorted(df["ngl"].astype(str).str.strip().unique().tolist())
            cur_codes = sorted(df["ncur"].astype(str).str.strip().unique().tolist())

            acc_names = [acc_code_to_name.get(code, f"({code})") for code in acc_codes]
            cur_names = [currency_code_to_name.get(code, f"({code})") for code in cur_codes]

            self.acc_name_to_code = {name: code for name, code in zip(acc_names, acc_codes)}
            self.currency_name_to_code = {name: code for name, code in zip(cur_names, cur_codes)}

            self.cmb_acc_type.configure(values=acc_names)
            self.cmb_acc_type.set(acc_names[0] if acc_names else "لا يوجد حسابات")

            self.cmb_currency.configure(values=cur_names)
            self.cmb_currency.set(cur_names[0] if cur_names else "-")
            if hasattr(self, 'sys_logger'):
                self.sys_logger.log(f"✅ تم سحب البيانات بنجاح للعميل [{client_no}]")
        except Exception as e:
            messagebox.showerror("خطأ", f"حدث خطأ أثناء البحث في الداتابيز:\n{e}")
            if hasattr(self, 'sys_logger'):
                self.sys_logger.log(f"❌ خطأ أثناء الاستعلام عن العميل [{client_no}]: {e}", type="ERROR")

    def nuwairy_fetch_transactions(self):
        # ✅ التعديل السابع: منع الضغط المتكرر (Thread Explosion)
        if getattr(self, "_loading", False):
            return

        client_no = self.ent_client_no.get().strip()
        acc_type_name = str(self.cmb_acc_type.get()).strip()
        currency_name = str(self.cmb_currency.get()).strip()

        date_from = self.ent_date_from.get().strip()
        date_to = self.ent_date_to.get().strip()

        if not client_no:
            messagebox.showwarning("تنبيه", "يرجى إدخال رقم العميل أولاً")
            return
        if acc_type_name in ("- أدخل العميل أولاً -", "لا يوجد حسابات", "", "-"):
            messagebox.showwarning("تنبيه", "يرجى اختيار نوع الحساب")
            return
        if currency_name in ("- أدخل العميل أولاً -", "", "-"):
            messagebox.showwarning("تنبيه", "يرجى اختيار العملة")
            return

        # ✅ التعديل الثامن: حد إجباري للتاريخ لتقليل البيانات
        if not date_from and not date_to:
            messagebox.showwarning("تنبيه", "برجاء تحديد فترة التاريخ (من - إلى) لتقليل حجم البيانات.")
            return

        # 👇 تسجيل بيانات البحث في اللوج
        if hasattr(self, 'sys_logger'):
            self.sys_logger.log(
                f"🔎 بدء استعلام حركات العملاء -> رقم العميل: [{client_no}] | الحساب: [{acc_type_name}] | العملة: [{currency_name}] | من: [{date_from}] إلى: [{date_to}]")
        self._loading = True

        if hasattr(self, 'btn_search'):
            self.btn_search.configure(text="جاري التحميل...", state="disabled")

        threading.Thread(target=self._bg_fetch_transactions_logic, args=(client_no, acc_type_name, currency_name),
                         daemon=True).start()

    def _bg_fetch_transactions_logic(self, client_no, acc_type_name, currency_name):
        try:
            engine = self._get_db_connection()

            if not hasattr(self, "currency_code_to_name"):
                cur_df = pd.read_sql("SELECT FCUR, CNM FROM TBL_Currency", engine)
                self.currency_code_to_name = dict(
                    zip(cur_df["FCUR"].astype(str).str.strip(), cur_df["CNM"].astype(str).str.strip()))

            if not hasattr(self, "acc_code_to_name"):
                acc_df = pd.read_sql("SELECT CCOD, CNM FROM dbo.TBL_AccTypes", engine)
                self.acc_code_to_name = dict(
                    zip(acc_df["CCOD"].astype(str).str.strip(), acc_df["CNM"].astype(str).str.strip()))

            if not hasattr(self, "trx_code_to_name"):
                trx_df = pd.read_sql("SELECT ncod1, ntnm FROM dbo.TBL_trx_code", engine)
                self.trx_code_to_name = dict(
                    zip(trx_df["ncod1"].astype(str).str.strip(), trx_df["ntnm"].astype(str).str.strip()))
                if not hasattr(self, "trx_code_to_name"):
                    trx_df = pd.read_sql("SELECT ncod1, ntnm FROM dbo.TBL_trx_code", engine)
                    self.trx_code_to_name = dict(
                        zip(trx_df["ncod1"].astype(str).str.strip(), trx_df["ntnm"].astype(str).str.strip()))

            # ✅ جبناه على نفس المحاذاة (برا الـ if اللي فوق)
            if not hasattr(self, "add_code_to_name") or not self.add_code_to_name:
                try:
                    add_df = pd.read_sql("SELECT ccod, cnm FROM dbo.TBL_add_codes", engine)
                    cleaned_ccod = add_df["ccod"].astype(str).str.strip().apply(
                        lambda x: x[:-2] if str(x).endswith(".0") else x)
                    cleaned_cnm = add_df["cnm"].astype(str).str.strip()
                    self.add_code_to_name = dict(zip(cleaned_ccod, cleaned_cnm))

                    # print(f"🔴 DEBUG 1: تم تحميل عدد {len(self.add_code_to_name)} كود من جدول TBL_add_codes")
                except Exception as e:
                    if hasattr(self, 'sys_logger'):
                        self.sys_logger.log(f"⚠️ فشل جلب جدول TBL_add_codes: {e}", "WARNING")
                    self.add_code_to_name = {}

            acc_type_code = getattr(self, "acc_name_to_code", {}).get(acc_type_name, acc_type_name)
            currency_code = getattr(self, "currency_name_to_code", {}).get(currency_name, currency_name)

            try:
                date_from_val = self._date_to_yyyymmdd(self.ent_date_from.get())
                date_to_val = self._date_to_yyyymmdd(self.ent_date_to.get())
            except Exception as ve:
                error_msg = str(ve)
                self.after(0, lambda msg=error_msg: messagebox.showwarning("تنبيه", msg))
                self._loading = False
                self._reset_search_btn()
                return

            branch_name = self.cmb_branch.get()
            branch_code = str(self.branch_mapping.get(branch_name, "")).strip()
            table_name = self.branch_table_mapping.get(branch_code)

            # =========================================================
            # بداية التدخل الجراحي الموحد (PBAL + رصيد 2017 + الرصيد الافتتاحي)
            # =========================================================

            pbal_val = 0.0
            actual_opening_balance = 0.0
            balance_2017_val = 0.0

            # ✅ 1. استخراج الرصيد الثابت (PBAL) لتاريخ 30-06-2016
            try:
                # 🛑 تنبيه هام: غير 'TBL_Accounts_Master' لاسم الجدول الحقيقي عندك اللي فيه الـ PBAL
                pbal_query = text(f"""
                            SELECT ISNULL(PBAL, 0) 
                            FROM {table_name} 
                            WHERE NCLNT = :client_no AND ngl = :acc_code AND ncur = :curr_code
                        """)
                with engine.connect() as conn:
                    res = conn.execute(pbal_query, {"client_no": client_no, "acc_code": str(acc_type_code),
                                                    "curr_code": str(currency_code)}).fetchone()
                    if res:
                        pbal_val = float(res[0])
                        # 🔥 تعديل تصفير المكشوف: لو رصيد المنقول نفسه جاي بالسالب نصفره
                        if pbal_val < 0:
                            pbal_val = 0.0
            except Exception as e:
                if hasattr(self, 'sys_logger'):
                    self.sys_logger.log(f"⚠️ فشل جلب PBAL: {e}", "WARNING")

            # ✅ 2. حساب رصيد 2017 الصحيح (رصيد الافتتاح PBAL + الحركات لحد 31-03-2017)
            balance_2017_val = pbal_val
            try:
                bal_2017_query = f"""
                            SELECT ncod1, namt
                            FROM {table_name} WITH (NOLOCK)
                            WHERE NCLNT = :client_no 
                              AND ngl = :acc_code 
                              AND ncur = :curr_code 
                              AND ndatm > '20160630' 
                              AND ndatm <= '20170331'
                        """
                bal_2017_params = {"client_no": client_no, "acc_code": str(acc_type_code),
                                   "curr_code": str(currency_code)}
                with engine.connect() as conn:
                    bal_2017_df = pd.read_sql(text(bal_2017_query), conn, params=bal_2017_params)

                for r_bal in bal_2017_df.itertuples(index=False):
                    t_code = str(getattr(r_bal, "ncod1", "")).strip()
                    t_amt_raw = getattr(r_bal, "namt", 0.0)
                    t_amt = float(t_amt_raw if pd.notnull(t_amt_raw) else 0.0)
                    amt_abs = abs(t_amt)

                    if t_code in ("3", "4"):
                        balance_2017_val -= amt_abs
                    elif t_code in ("1", "2"):
                        balance_2017_val += amt_abs
                    else:
                        if t_amt < 0:
                            balance_2017_val -= amt_abs
                        else:
                            balance_2017_val += amt_abs
            except Exception as e:
                if hasattr(self, 'sys_logger'):
                    self.sys_logger.log(f"⚠️ فشل جلب رصيد 2017: {e}", "WARNING")

            # =========================================================
            # ✅ 3. حساب الرصيد الافتتاحي الفعلي + (ديباج / Debugging)
            # =========================================================
            if date_from_val:
                try:
                    # 🔥 تعديل: ضفنا ndatm للـ SELECT و ORDER BY عشان نحسب الرصيد حركة بحركة صح
                    bal_query = f"""
                                    SELECT ncod1, namt, ndatm
                                    FROM {table_name} WITH (NOLOCK)
                                    WHERE NCLNT = :client_no 
                                      AND ngl = :acc_code 
                                      AND ncur = :curr_code 
                                      AND ndatm < :date_from
                                    ORDER BY ndatm ASC
                                """
                    bal_params = {"client_no": client_no, "acc_code": str(acc_type_code),
                                  "curr_code": str(currency_code), "date_from": date_from_val}

                    with engine.connect() as conn:
                        bal_df = pd.read_sql(text(bal_query), conn, params=bal_params)

                    debug_total_in = 0.0
                    debug_total_out = 0.0

                    for r_bal in bal_df.itertuples(index=False):
                        t_code = str(getattr(r_bal, "ncod1", "")).strip()
                        t_amt = float(getattr(r_bal, "namt", 0.0) or 0.0)
                        t_ndatm = str(getattr(r_bal, "ndatm", "")).strip() # 🔥 استخراج التاريخ
                        amt_abs = abs(t_amt)

                        if t_code in ("3", "4"):  # خصم
                            actual_opening_balance -= amt_abs
                            debug_total_out += amt_abs
                        elif t_code in ("1", "2"):  # إضافة
                            actual_opening_balance += amt_abs
                            debug_total_in += amt_abs
                        else:
                            if t_amt < 0:
                                actual_opening_balance -= amt_abs
                                debug_total_out += amt_abs
                            else:
                                actual_opening_balance += amt_abs
                                debug_total_in += amt_abs

                        # 🔥 تعديل تصفير المكشوف: لو الرصيد الافتتاحي نزل سالب قبل أو في 30-6 بنصفره
                        if actual_opening_balance < 0 and t_ndatm <= '20160630':
                            actual_opening_balance = 0.0

                    if hasattr(self, 'sys_logger'):
                        self.sys_logger.log(
                            f"🔎 ديباج الرصيد الافتتاحي -> إضافات: {debug_total_in:,.2f} | خصومات: {debug_total_out:,.2f} | الرصيد النهائي: {actual_opening_balance:,.2f}")

                except Exception as e:
                    if hasattr(self, 'sys_logger'):
                        self.sys_logger.log(f"⚠️ فشل حساب الرصيد الافتتاحي: {e}", "WARNING")
            # =========================================================
            # نهاية التدخل الجراحي الموحد
            # =========================================================

            query = f"""
                SELECT TOP 5000 ngl, ncur, ndatm, nbian, namt, ncod1, nsb, nseq, ncod2
                FROM {table_name} WITH (NOLOCK)
                WHERE NCLNT = :client_no 
                  AND ngl = :acc_code 
                  AND ncur = :curr_code
            """
            params_dict = {"client_no": client_no, "acc_code": str(acc_type_code), "curr_code": str(currency_code)}

            if date_from_val:
                query += " AND ndatm >= :date_from"
                params_dict["date_from"] = date_from_val
            if date_to_val:
                query += " AND ndatm <= :date_to"
                params_dict["date_to"] = date_to_val

            query += " ORDER BY ndatm ASC"

            with engine.connect() as conn:
                view_df = pd.read_sql(text(query), conn, params=params_dict)

            if view_df.empty:
                self.after(0, lambda: messagebox.showinfo("معلومة", "لا توجد حركات مطابقة للبيانات المختارة."))
                if hasattr(self, 'sys_logger'):
                    self.sys_logger.log(f"⚠️ لا توجد حركات للعميل [{client_no}] تتطابق مع شروط البحث.", "WARNING")

                if hasattr(self, "sheet"):
                    self.after(0, lambda: self.sheet.set_sheet_data([], reset_col_positions=False,
                                                                    reset_row_positions=True))
                return

            view_df["nbian"] = view_df["nbian"].fillna("").astype(str).str.strip()
            view_df["nbian"] = view_df["nbian"].replace(["nan", "NaN", "None"], "")

            view_df["ncod1"] = view_df["ncod1"].astype(str).str.strip()
            view_df["namt"] = pd.to_numeric(view_df["namt"], errors="coerce").fillna(0)

            if "ncod2" in view_df.columns:
                view_df["ncod2"] = view_df["ncod2"].fillna("").astype(str).str.strip()
                view_df["ncod2"] = view_df["ncod2"].replace(["nan", "NaN", "None", "<NA>"], "")
                view_df["ncod2"] = view_df["ncod2"].apply(lambda x: x[:-2] if str(x).endswith(".0") else x)

            trx_map = getattr(self, "trx_code_to_name", {})
            acc_map = getattr(self, "acc_code_to_name", {})
            add_map = getattr(self, "add_code_to_name", {})
            rows_data = []

            for r in view_df.itertuples(index=False):
                ndatm = str(getattr(r, "ndatm", "")).strip()
                ndatm_fmt = f"{ndatm[:4]}-{ndatm[4:6]}-{ndatm[6:]}" if len(ndatm) == 8 and ndatm.isdigit() else ndatm

                trx_code = str(getattr(r, "ncod1", "")).strip()
                trx_name = str(trx_map.get(trx_code, trx_code) or "").strip()
                ncod2_val = str(getattr(r, "ncod2", "")).strip()
                doc_name = str(add_map.get(ncod2_val, "")).strip()

                amt = float(getattr(r, "namt", 0.0))
                amt_abs = abs(amt)

                if trx_code in ("3", "4"):
                    credit, debit = 0.0, amt_abs
                elif trx_code in ("1", "2"):
                    credit, debit = amt_abs, 0.0
                else:
                    credit, debit = (0.0, amt_abs) if amt < 0 else (amt_abs, 0.0)

                rows_data.append({
                    'ndatm_raw': ndatm,
                    'ndatm_fmt': ndatm_fmt,
                    'desc': getattr(r, "nbian", ""),
                    'credit': credit,
                    'debit': debit,
                    'trx_name': trx_name,
                    'gl_main_name': acc_map.get(str(getattr(r, "ngl", "")).strip(), str(getattr(r, "ngl", "")).strip()),
                    'gl_sub': str(getattr(r, "nsb", "")).strip(),
                    'nseq': str(getattr(r, "nseq", "")).strip(),
                    'doc_name': doc_name
                })

            rows_data.sort(key=lambda x: (
                x['ndatm_raw'],
                x['debit'] > 0,
                max(x['credit'], x['debit'])
            ))

            running_balance = actual_opening_balance
            passed_cutoff = True if (date_from_val and date_from_val > '20160630') else False

            final_rows_data = []

            for item in rows_data:
                if not passed_cutoff and item['ndatm_raw'] > '20160630':
                    settlement_row = {
                        'ndatm_raw': '20160630',
                        'ndatm_fmt': '2016-06-30',
                        'desc': 'رصيد منقول (PBAL)',
                        'credit': 0.0,
                        'debit': 0.0,
                        'trx_name': 'تسوية',
                        'gl_main_name': '',
                        'gl_sub': '',
                        'nseq': '',
                        'doc_name': '',
                        'balance': pbal_val
                    }
                    final_rows_data.append(settlement_row)
                    running_balance = pbal_val
                    passed_cutoff = True

                running_balance += item['credit'] - item['debit']

                # 🔥 تعديل تصفير المكشوف: لو الرصيد نزل بالسالب جوه كشف الحساب نفسه قبل 30-06-2016
                if running_balance < 0 and item['ndatm_raw'] <= '20160630':
                    running_balance = 0.0

                item['balance'] = running_balance
                final_rows_data.append(item)

            opening_balance = actual_opening_balance
            rows_data = final_rows_data

            def fmt_money(x: float) -> str:
                return f"{x:,.2f}" if x != 0.0 else ""

            rows = []
            for item in rows_data:
                rows.append([
                    item['ndatm_fmt'],
                    item['desc'],
                    fmt_money(item['credit']),
                    fmt_money(item['debit']),
                    f"{item['balance']:,.2f}",
                    item['trx_name'],
                    item['gl_main_name'],
                    item['gl_sub'],
                    item['nseq'],
                    item['doc_name']
                ])

            if not hasattr(self, "sheet"): return
            self.after(0, lambda: self.sheet.set_sheet_data(rows, reset_col_positions=False, reset_row_positions=True))

            self.nuwairy_last_rows = rows
            self.nuwairy_last_meta = {
                "client_no": client_no,
                "account_no": client_no,
                "branch_name": str(self.cmb_branch.get()).strip() if hasattr(self, "cmb_branch") else "",
                "acc_type": acc_type_name,
                "currency": currency_name,
                "date_from": self.ent_date_from.get().strip() if hasattr(self, "ent_date_from") else "",
                "date_to": self.ent_date_to.get().strip() if hasattr(self, "ent_date_to") else "",
                "client_info": self.lbl_branch_info.cget("text") if hasattr(self, "lbl_branch_info") else "",
                "opening_balance": f"{opening_balance:,.2f}",
                "balance_2017": f"{balance_2017_val:,.2f}"
            }
            if hasattr(self, 'sys_logger'):
                self.sys_logger.log(f"✅ تم عرض {len(rows)} حركة للعميل [{client_no}] بنجاح.")
        except Exception as e:
            error_msg = str(e)
            if hasattr(self, 'sys_logger'):
                self.sys_logger.log(f"❌ فشل جلب حركات العميل [{client_no}]: {error_msg}", "ERROR")
            self.after(0, lambda msg=error_msg: messagebox.showerror("خطأ", f"حدث خطأ:\n{msg}"))
        finally:
            self._loading = False
            self._reset_search_btn()

    def _reset_search_btn(self):
        if hasattr(self, 'btn_search'):
            self.after(0, lambda: self.btn_search.configure(text="بحث", state="normal"))

    def nuwairy_export_pdf(self):
        lang_choice = messagebox.askyesnocancel("اللغة / Language",
                                                "اضغط نعم للغة الإنجليزية، لا للغة العربية\nPress Yes for English, No for Arabic")
        if lang_choice is None:
            if hasattr(self, 'sys_logger'): self.sys_logger.log("⚠️ تم إلغاء التصدير.", type="WARNING")
            return
        lang = "en" if lang_choice else "ar"

        # ==========================================
        # 1. قاموس المصطلحات البنكية الثابتة (Offline)
        # ==========================================
        loc = {
            "اسم العميل:": {"ar": "اسم العميل:", "en": "Customer Name:"},
            "العنوان:": {"ar": "العنوان:", "en": "Address:"},
            "رقم الحساب:": {"ar": "رقم الحساب:", "en": "Account No:"},
            "نوع الحساب:": {"ar": "نوع الحساب:", "en": "Account Type:"},
            "العملة:": {"ar": "العملة:", "en": "Currency:"},
            "جنيه مصري": {"ar": "جنيه مصري", "en": "EGP"},
            "دولار أمريكي": {"ar": "دولار أمريكي", "en": "USD"},
            "الفترة:": {"ar": "الفترة:", "en": "Period:"},
            "إلى": {"ar": "إلى", "en": "to"},
            "رصيد 31-03-2017:": {"ar": "رصيد 31-03-2017:", "en": "Balance 31-03-2017:"},
            "رصيد الافتتاح": {"ar": "رصيد الافتتاح", "en": "Opening Balance"},
            "إجمالي دائن": {"ar": "إجمالي دائن", "en": "Total Credit"},
            "إجمالي مدين": {"ar": "إجمالي مدين", "en": "Total Debit"},
            "الرصيد الختامي": {"ar": "الرصيد الختامي", "en": "Closing Balance"},
            "عدد الحركات": {"ar": "عدد الحركات", "en": "Trx Count"},
            "تاريخ الطباعة:": {"ar": "تاريخ الطباعة:", "en": "Printed at:"},
            "صفحة": {"ar": "صفحة", "en": "Page"},
            "كشف حساب": {"ar": "كشف حساب", "en": "Account Statement"},
            "فرع:": {"ar": "فرع:", "en": "Branch:"},
            "رقم النمارة:": {"ar": "رقم النمارة:", "en": "Doc No:"},
            "الرصيد": {"ar": "الرصيد", "en": "Balance"},
            "دائن": {"ar": "دائن", "en": "Credit"},
            "مدين": {"ar": "مدين", "en": "Debit"},
            "البيان / نوع المستند": {"ar": "البيان / نوع المستند", "en": "Description / Doc Type"},
            "التاريخ": {"ar": "التاريخ", "en": "Date"},
            "—": {"ar": "—", "en": "—"},
            "سحب": {"ar": "سحب", "en": "Withdrawal"},
            "خصم": {"ar": "خصم", "en": "Debit"},
            "إيداع": {"ar": "إيداع", "en": "Deposit"},
            "اضافه": {"ar": "اضافه", "en": "Credit Add"},
            "إضافة": {"ar": "إضافة", "en": "Credit Add"},
            "نقدي": {"ar": "نقدي", "en": "Cash"},
            "تحويل": {"ar": "تحويل", "en": "Transfer"},
            "عمولة": {"ar": "عمولة", "en": "Commission"},
            "جاري": {"ar": "جاري", "en": "Current Account"},
            "توفير": {"ar": "توفير", "en": "Savings Account"},
            "تغطيه المكشوف من الجارى": {"ar": "تغطيه المكشوف من الجارى", "en": "Overdraft Coverage"},
            "مصاريف فتح الحسابات الجديدة": {"ar": "مصاريف فتح الحسابات الجديدة", "en": "New Account Opening Fees"},
            "000035 / مصاريف فتح الحساب ات الجديدةح": {"ar": "مصاريف فتح الحسابات الجديدة",
                                                       "en": "New Account Opening Fees"},
            "000046 / مصاريف فتح الحساب ات الجديدةح": {"ar": "مصاريف فتح الحسابات الجديدة",
                                                       "en": "New Account Opening Fees"},
            "عائد الربع الثالث": {"ar": "عائد الربع الثالث", "en": "Q3 Return"},
            "عائد الربع الرابع": {"ar": "عائد الربع الرابع", "en": "Q4 Return"},
            "مصاريف خدمه الاستثمار": {"ar": "مصاريف خدمه الاستثمار", "en": "Investment Service Fees"},
            "دمغه كشف حساب": {"ar": "دمغه كشف حساب", "en": "Statement Stamp Tax"},
        }

        def t(word):
            word_str = str(word).strip()
            return loc.get(word_str, {}).get(lang, word_str)

        # ==========================================
        # 2. دالة الترجمة الصوتية للأسماء والعناوين (Offline)
        # ==========================================
        def transliterate_ar_to_en(text):
            if not text: return ""
            text = str(text).strip()

            # معالجة المقاطع الشائعة أولاً
            replacements = {
                "عبد ال": "Abd El-", "عبدال": "Abd El-", "عبد ": "Abd ",
                "ابو ": "Abou ", "أبو ": "Abou ", " ابو ": " Abou ",
                " الدين": " El-Din", "الدين": "El-Din",
                " الله": " Allah", "الله": "Allah",
                " ال": " El-", "ال": "El-"
            }
            for ar_str, en_str in replacements.items():
                text = text.replace(ar_str, en_str)

            # خريطة الحروف المتبقية
            char_map = {
                'أ': 'A', 'ا': 'A', 'إ': 'E', 'آ': 'A', 'ب': 'B', 'ت': 'T', 'ث': 'Th',
                'ج': 'G', 'ح': 'H', 'خ': 'Kh', 'د': 'D', 'ذ': 'Z', 'ر': 'R', 'ز': 'Z',
                'س': 'S', 'ش': 'Sh', 'ص': 'S', 'ض': 'D', 'ط': 'T', 'ظ': 'Z', 'ع': 'A',
                'غ': 'Gh', 'ف': 'F', 'ق': 'Q', 'ك': 'K', 'ل': 'L', 'م': 'M', 'ن': 'N',
                'ه': 'H', 'ة': 'a', 'و': 'W', 'ي': 'Y', 'ى': 'a', 'ئ': 'E', 'ء': 'A', 'ؤ': 'O',
                '١': '1', '٢': '2', '٣': '3', '٤': '4', '٥': '5', '٦': '6', '٧': '7', '٨': '8', '٩': '9', '٠': '0'
            }

            result = ""
            for char in text:
                result += char_map.get(char, char)  # لو مش حرف عربي ينزل زي ما هو (أرقام/مسافات)

            # تظبيط شكل الحروف (أول حرف كابيتال والباقي سمول في كل كلمة)
            return " ".join([word.capitalize() for word in result.split()])

        # ==========================================
        # 3. دالة معالجة العربي عشان مايطلعش مقلوب
        # ==========================================
        try:
            def ar(txt: str) -> str:
                txt = "" if txt is None else str(txt)
                # بنعمل معالجة للعربي حتى لو التقرير إنجليزي عشان الوصف اللي مالوش ترجمة
                return get_display(arabic_reshaper.reshape(txt))
        except Exception:
            def ar(txt: str) -> str:
                return "" if txt is None else str(txt)

        rows = getattr(self, "nuwairy_last_rows", None)
        meta = getattr(self, "nuwairy_last_meta", {}) or {}

        if not rows:
            messagebox.showwarning("تنبيه", "لا توجد بيانات للتصدير. اعمل بحث الحركات أولاً.")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF Files", "*.pdf")]
        )

        if not file_path:
            return

        GREEN = colors.HexColor("#1F6B4B")
        GOLD = colors.HexColor("#B08D2D")
        DGRAY = colors.HexColor("#5B6770")
        GRID = colors.HexColor("#E7ECEF")
        BORDER = colors.HexColor("#C9D1D8")
        ZEBRA = colors.HexColor("#FAFBFC")
        OPEN_BG = colors.HexColor("#FFF1D6")
        CLOSE_BG = colors.HexColor("#FFF5DB")

        def resource_try(*names):
            for n in names:
                try:
                    p = resource_path(n)
                    if p and os.path.exists(p):
                        return p
                except Exception:
                    pass
            return None

        def money_to_float(s):
            if s is None: return 0.0
            s = str(s).strip()
            if not s: return 0.0
            s = s.replace(",", "").replace(" ", "")
            s = re.sub(r"[^0-9\.\-]", "", s)
            try:
                return float(s) if s else 0.0
            except Exception:
                return 0.0

        def fmt2(x: float) -> str:
            return f"{x:,.2f}"

        def _parse_date_safe(s: str):
            s = (s or "").strip()
            for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"):
                try:
                    return datetime.strptime(s, fmt).date()
                except:
                    pass
            return None

        def safe_one_line(x: str) -> str:
            x = "" if x is None else str(x)
            return " ".join(x.replace("\r", " ").replace("\n", " ").split()).strip()

        dates = []
        for r in rows:
            if r and len(r) > 0:
                d = _parse_date_safe(r[0])
                if d: dates.append(d)
        min_date = min(dates) if dates else None
        max_date = max(dates) if dates else None

        if min_date and max_date:
            period_text = f"{t('الفترة:')} {min_date.strftime('%Y-%m-%d')}  {t('إلى')}  {max_date.strftime('%Y-%m-%d')}"
        else:
            df_ = (meta.get("date_from") or "").strip()
            dt_ = (meta.get("date_to") or "").strip()
            period_text = f"{t('الفترة:')} {df_}  {t('إلى')}  {dt_}" if (df_ or dt_) else ""

        total_credit = 0.0
        total_debit = 0.0
        closing_balance = 0.0
        for r in rows:
            if len(r) < 5: continue
            total_credit += money_to_float(r[2])
            total_debit += money_to_float(r[3])
            closing_balance = money_to_float(r[4])

        printed_at = datetime.now().strftime("%Y-%m-%d %H:%M")

        opening_balance_txt = (meta.get("opening_balance") or "").strip()
        opening_balance_val = money_to_float(opening_balance_txt) if opening_balance_txt else 0.0

        client_no = (meta.get("client_no") or "").strip()
        account_no = (meta.get("account_no") or "").strip()
        if not account_no: account_no = client_no

        def make_logo_transparent(input_path, output_path, white_threshold=245):
            try:
                im = Image.open(input_path).convert("RGBA")
                pixels = im.getdata()
                new_pixels = []
                for rr, gg, bb, aa in pixels:
                    if rr >= white_threshold and gg >= white_threshold and bb >= white_threshold:
                        new_pixels.append((rr, gg, bb, 0))
                    else:
                        new_pixels.append((rr, gg, bb, aa))
                im.putdata(new_pixels)
                im.save(output_path, "PNG")
                return True
            except Exception:
                return False

        try:
            font_path = resource_try("Amiri-Regular.ttf")
            if not font_path:
                messagebox.showerror("خطأ", "ملف الخط Amiri-Regular.ttf غير موجود جنب gui.py")
                return

            pdfmetrics.registerFont(TTFont("AR", font_path))
            base_font = "AR"

            styles = getSampleStyleSheet()
            align_choice = TA_LEFT if lang == "en" else TA_RIGHT

            st_right = ParagraphStyle("right_ar", parent=styles["Normal"], fontName=base_font, fontSize=10.2,
                                      leading=14, alignment=align_choice, textColor=colors.black)
            st_right_small = ParagraphStyle("right_ar_small", parent=styles["Normal"], fontName=base_font, fontSize=8.8,
                                            leading=11.2, alignment=align_choice, textColor=DGRAY)
            st_center_small = ParagraphStyle("center_small", parent=styles["Normal"], fontName=base_font, fontSize=9.2,
                                             leading=12, alignment=TA_CENTER, textColor=DGRAY)
            st_kpi_label = ParagraphStyle("kpi_label", parent=styles["Normal"], fontName=base_font, fontSize=8.6,
                                          leading=10.5, alignment=TA_CENTER, textColor=DGRAY)
            st_kpi_value = ParagraphStyle("kpi_value", parent=styles["Normal"], fontName=base_font, fontSize=12.2,
                                          leading=14, alignment=TA_CENTER, textColor=colors.black)

            w, h = A4
            header_h = 34 * mm
            doc = SimpleDocTemplate(file_path, pagesize=A4, leftMargin=14 * mm, rightMargin=14 * mm,
                                    topMargin=(header_h + 12 * mm), bottomMargin=14 * mm)
            logo_png = resource_try("logo.png", "faisal_logo.png")
            logo_jpg = resource_try("logo.jpeg", "logo.jpg", "faisal_logo.jpeg", "faisal_logo.jpg")

            logo_path = None
            if logo_png:
                logo_path = logo_png
            elif logo_jpg:
                try:
                    temp_dir = tempfile.gettempdir()
                    gen_png = os.path.join(temp_dir, "faisal_logo.png")
                    if not os.path.exists(gen_png): make_logo_transparent(logo_jpg, gen_png, white_threshold=245)
                    logo_path = gen_png if os.path.exists(gen_png) else logo_jpg
                except Exception:
                    logo_path = logo_jpg

            logo_img = ImageReader(logo_path) if logo_path else None

            def draw_header_footer(canv, doc_):
                canv.saveState()
                ww, hh = A4
                canv.setFillColor(GREEN)
                canv.rect(0, hh - header_h, ww, header_h, fill=1, stroke=0)
                canv.setFillColor(GOLD)
                canv.rect(0, hh - header_h, ww, 2.0 * mm, fill=1, stroke=0)

                if logo_img:
                    box_x, box_y, box_w, box_h = 13 * mm, hh - header_h + 4.5 * mm, 26 * mm, 26 * mm
                    canv.setFillColor(colors.white)
                    canv.roundRect(box_x, box_y, box_w, box_h, 3 * mm, fill=1, stroke=0)
                    canv.drawImage(logo_img, box_x + 2 * mm, box_y + 2 * mm, width=22 * mm, height=22 * mm,
                                   preserveAspectRatio=True, mask='auto')

                canv.setFillColor(colors.white)
                canv.setFont(base_font, 16.2)

                branch_val = (meta.get("branch_name") or "").strip()
                branch_name = transliterate_ar_to_en(branch_val) if lang == "en" else branch_val
                title = f"{t('كشف حساب')}  |  {t('فرع:')} {branch_name}" if branch_name else t("كشف حساب")

                canv.drawCentredString(ww / 2, hh - 17.5 * mm, ar(title))

                footer_y = 9 * mm
                canv.setStrokeColor(colors.HexColor("#D7DCE0"))
                canv.setLineWidth(0.55)
                canv.line(14 * mm, footer_y + 6 * mm, ww - 14 * mm, footer_y + 6 * mm)
                canv.setFillColor(DGRAY)
                canv.setFont(base_font, 9.2)
                canv.drawString(14 * mm, footer_y, ar(f"{t('تاريخ الطباعة:')} {printed_at}"))
                canv.drawRightString(ww - 14 * mm, footer_y, ar(f"{t('صفحة')} {doc_.page}"))
                canv.restoreState()

            story = []

            client_info = (meta.get("client_info") or "").strip()
            acc_type = (meta.get("acc_type") or "").strip()
            cur = (meta.get("currency") or "").strip()

            client_lines = []
            if client_info:
                for ln in client_info.split("\n"):
                    ln = ln.strip()
                    if ln and ln != "—":
                        if ln.startswith("اسم العميل:"):
                            name_val = ln.replace("اسم العميل:", "").strip()
                            # تفعيل الترجمة الصوتية للاسم لو اللغة إنجليزي
                            final_name = transliterate_ar_to_en(name_val) if lang == "en" else name_val
                            client_lines.append(f"{t('اسم العميل:')} {final_name}")
                        elif ln.startswith("العنوان:"):
                            addr_val = ln.replace("العنوان:", "").strip()
                            # تفعيل الترجمة الصوتية للعنوان لو اللغة إنجليزي
                            final_addr = transliterate_ar_to_en(addr_val) if lang == "en" else addr_val
                            client_lines.append(f"{t('العنوان:')} {final_addr}")
                        else:
                            client_lines.append(ln)

            if not client_lines:
                client_lines = [f"{t('اسم العميل:')} {t('—')}", f"{t('العنوان:')} {t('—')}"]

            if account_no: client_lines.append(f"{t('رقم الحساب:')} {account_no}")
            if acc_type: client_lines.append(f"{t('نوع الحساب:')} {t(acc_type)}")
            if cur: client_lines.append(f"{t('العملة:')} {t(cur)}")
            if period_text: client_lines.append(period_text)

            # 1. بنبني السطور العادية الأول
            info_block = [Paragraph(ar(x), st_right) for x in client_lines]

            # 2. بنجهز سطر الرصيد القديم
            balance_2017_txt = meta.get("balance_2017", "0.00")
            bal_text = f"{t('   الرصيد في 31-03-2017:   ')} {balance_2017_txt}"

            # 3. بنعمل معالجة للعربي الأول (ar)، وبعدين نغلفه بتاج الهايلايت الأزرق
            highlighted_bal = f'<font backColor="#facc69">{ar(bal_text)}</font>'

            # 4. بنضيفه للبلوك
            info_block.append(Paragraph(highlighted_bal, st_right))

            info_tbl = Table([[info_block]], colWidths=[176 * mm])

            info_tbl.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                ("BOX", (0, 0), (-1, -1), 1.15, GOLD),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ]))
            story.append(info_tbl)
            story.append(Spacer(1, 6 * mm))

            kpis = [
                ("رصيد الافتتاح", fmt2(opening_balance_val)),
                ("إجمالي دائن", fmt2(total_credit)),
                ("إجمالي مدين", fmt2(total_debit)),
                ("الرصيد الختامي", fmt2(closing_balance)),
                ("عدد الحركات", str(len(rows))),
            ]

            if lang == "en": kpis = list(reversed(kpis))

            kpi_cells = []
            for label, value in kpis:
                kpi_cells.append([
                    Paragraph(ar(t(label)), st_kpi_label),
                    Spacer(1, 1.0 * mm),
                    Paragraph(ar(value), st_kpi_value)
                ])

            usable_w = (A4[0] - doc.leftMargin - doc.rightMargin)
            kpi_tbl = Table([kpi_cells], colWidths=[usable_w / 5.0] * 5)

            open_idx = 4 if lang == "en" else 0
            close_idx = 1 if lang == "en" else 3

            kpi_tbl.setStyle(TableStyle([
                ("BOX", (0, 0), (-1, -1), 1.10, GOLD),
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                ("LINEBEFORE", (1, 0), (1, 0), 0.35, GRID),
                ("LINEBEFORE", (2, 0), (2, 0), 0.35, GRID),
                ("LINEBEFORE", (3, 0), (3, 0), 0.35, GRID),
                ("LINEBEFORE", (4, 0), (4, 0), 0.35, GRID),
                ("TOPPADDING", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("BACKGROUND", (open_idx, 0), (open_idx, 0), OPEN_BG),
                ("BACKGROUND", (close_idx, 0), (close_idx, 0), CLOSE_BG),
            ]))
            story.append(kpi_tbl)
            story.append(Spacer(1, 7 * mm))

            if lang == "en":
                header = [ar(t("التاريخ")), ar(t("البيان / نوع المستند")), ar(t("مدين")), ar(t("دائن")),
                          ar(t("الرصيد"))]
                col_widths = [26 * mm, 86 * mm, 24 * mm, 24 * mm, 30 * mm]
            else:
                header = [ar(t("الرصيد")), ar(t("دائن")), ar(t("مدين")), ar(t("البيان / نوع المستند")),
                          ar(t("التاريخ"))]
                col_widths = [30 * mm, 24 * mm, 24 * mm, 86 * mm, 26 * mm]

            table_data = [header]

            for r in rows:
                date = r[0] if len(r) > 0 else ""
                desc = safe_one_line(r[1] if len(r) > 1 else "")
                credit = r[2] if len(r) > 2 else ""
                debit = r[3] if len(r) > 3 else ""
                bal = r[4] if len(r) > 4 else ""
                nseq = (r[8] if len(r) > 8 else "")
                # 🆕 ضيف السطر ده عشان تسحب اسم المستند اللي جه من الداتا
                doc_name = (r[9] if len(r) > 9 else "")

                desc_flow = []

                # 1. المستند الأول (لو موجود)
                if doc_name:
                    desc_flow.append(Paragraph(ar(f"{doc_name}"), st_right_small))

                # 2. البيان (أساسي)
                desc_flow.append(Paragraph(ar(t(desc) if desc else "—"), st_right))

                # 3. رقم النمارة (لو موجود)
                if nseq:
                    desc_flow.append(Paragraph(ar(f"{t('رقم النمارة:')} {nseq}"), st_right_small))
                if lang == "en":
                    table_data.append([date, desc_flow, debit, credit, bal])
                else:
                    table_data.append([bal, credit, debit, desc_flow, date])

            main_tbl = Table(table_data, colWidths=col_widths, repeatRows=1, hAlign="LEFT")

            align_style_col2 = "LEFT" if lang == "en" else "RIGHT"

            main_tbl.setStyle(TableStyle([
                ("FONTNAME", (0, 0), (-1, -1), base_font),
                ("FONTSIZE", (0, 0), (-1, 0), 10.2),
                ("FONTSIZE", (0, 1), (-1, -1), 9.3),
                ("BACKGROUND", (0, 0), (-1, 0), GREEN),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("LINEBELOW", (0, 0), (-1, 0), 1.2, GOLD),
                ("GRID", (0, 0), (-1, -1), 0.28, BORDER),
                ("BOX", (0, 0), (-1, -1), 0.95, BORDER),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ZEBRA]),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 1), (0, -1), "CENTER"),
                ("ALIGN", (1, 1), (1, -1), align_style_col2 if lang == "en" else "CENTER"),
                ("ALIGN", (2, 1), (4, -1), "CENTER"),
                ("ALIGN", (1, 1), (1, -1), "LEFT" if lang == "en" else "RIGHT"),
                ("RIGHTPADDING", (1, 1) if lang == "en" else (3, 1), (1, -1) if lang == "en" else (3, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]))

            story.append(main_tbl)

            doc.build(story, onFirstPage=draw_header_footer, onLaterPages=draw_header_footer)
            messagebox.showinfo("تم / Success", "تم تصدير PDF بنجاح ✅\nPDF Exported Successfully ✅")
            if hasattr(self, 'sys_logger'): self.sys_logger.log(f"📄  تم تصدير PDF بنجاح إلى ملف: {file_path}")
        except Exception as e:
            messagebox.showerror("خطأ / Error", f"حدث خطأ أثناء تصدير PDF:\n{e}")
            if hasattr(self, 'sys_logger'): self.sys_logger.log(f"❌ فشل تصدير الملف: {e}", type="ERROR")

    def nuwairy_export_excel(self):
        rows = getattr(self, "nuwairy_last_rows", None)
        meta = getattr(self, "nuwairy_last_meta", {}) or {}

        if not rows:
            messagebox.showwarning("تنبيه", "لا توجد بيانات للتصدير. اعمل بحث الحركات أولاً.")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel Files", "*.xlsx")]
        )
        if not file_path:
            return

        # ---------- Helpers ----------
        def money_to_float(v):
            if v is None:
                return 0.0
            s = str(v).strip()
            if not s:
                return 0.0
            s = s.replace(",", "").replace(" ", "")
            s = re.sub(r"[^0-9\.\-]", "", s)
            try:
                return float(s) if s else 0.0
            except:
                return 0.0

        def parse_date_safe(s):
            s = (s or "").strip()
            for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d", "%d-%m-%Y", "%d/%m/%Y"):
                try:
                    return datetime.strptime(s, fmt).date()
                except:
                    pass
            return None

        def safe_txt(x):
            return "" if x is None else str(x)

        def resource_try(*names):
            for n in names:
                try:
                    p = None
                    try:
                        p = resource_path(n)  # type: ignore
                    except:
                        p = None
                    if not p:
                        p = os.path.join(os.getcwd(), n)
                    if p and os.path.exists(p):
                        return p
                except:
                    pass
            return None

        try:

            # ---------- Theme ----------
            GREEN = "#0B5C3A"
            GOLD = "#B08D2D"
            GRID = "#E6EAEE"
            ZEBRA = "#FAFBFC"
            TEXT = "#111827"
            MUTED = "#4B5563"
            SOFT = "#F9F3E6"
            OPEN_BG = "#FFF1D6"
            CLOSE_BG = "#FFF5DB"

            # ---------- Meta ----------
            client_info = (meta.get("client_info") or "").strip()
            branch = (meta.get("branch_name") or "").strip()
            acc_type = (meta.get("acc_type") or "").strip()
            cur = (meta.get("currency") or "").strip()
            client_no = (meta.get("client_no") or "").strip()
            account_no = (meta.get("account_no") or "").strip()
            date_from = (meta.get("date_from") or "").strip()
            date_to = (meta.get("date_to") or "").strip()
            opening_balance = money_to_float(meta.get("opening_balance"))

            # ---------- Prepare table rows ----------
            # rows format from fetch: [date, desc, credit, debit, balance, trx_name, gl_main, gl_sub, nseq]
            # Needed order in excel: date | desc | debit | credit | balance | nseq
            table_rows = []
            total_credit = 0.0
            total_debit = 0.0
            closing_balance = 0.0

            for r in rows:
                d = safe_txt(r[0]) if len(r) > 0 else ""
                desc = safe_txt(r[1]) if len(r) > 1 else ""
                credit = money_to_float(r[2]) if len(r) > 2 else 0.0
                debit = money_to_float(r[3]) if len(r) > 3 else 0.0
                bal = money_to_float(r[4]) if len(r) > 4 else 0.0
                nseq = safe_txt(r[8]) if len(r) > 8 else ""  # ✅ رقم النمارة

                total_credit += credit
                total_debit += debit
                closing_balance = bal

                table_rows.append((d, desc, debit, credit, bal, nseq))  # ✅ ضفناه فعليًا

            # Keep exact meta period if exists; else infer
            if (not date_from or not date_to) and table_rows:
                ds = [parse_date_safe(x[0]) for x in table_rows]
                ds = [d for d in ds if d]
                if ds:
                    mn, mx = min(ds), max(ds)
                    date_from = date_from or mn.strftime("%Y-%m-%d")
                    date_to = date_to or mx.strftime("%Y-%m-%d")

            printed_at = datetime.now().strftime("%Y-%m-%d %H:%M")

            # Summary prep
            credits_only = [(d, desc, c) for (d, desc, deb, c, bal, nseq) in table_rows if c and c > 0]
            debits_only = [(d, desc, deb) for (d, desc, deb, c, bal, nseq) in table_rows if deb and deb > 0]
            top_credits = sorted(credits_only, key=lambda x: x[2], reverse=True)[:5]
            top_debits = sorted(debits_only, key=lambda x: x[2], reverse=True)[:5]

            daily = {}
            for d, desc, deb, c, bal, nseq in table_rows:
                daily.setdefault(d, {"credit": 0.0, "debit": 0.0})
                daily[d]["credit"] += c
                daily[d]["debit"] += deb
            daily_days = sorted(daily.keys(), key=lambda x: (parse_date_safe(x) or datetime.max.date(), x))

            # ---------- Workbook ----------
            wb = xlsxwriter.Workbook(file_path)

            # ---------- Formats ----------
            fmt_title = wb.add_format({
                "bold": True, "font_size": 18, "font_color": "white",
                "align": "center", "valign": "vcenter",
                "bg_color": GREEN
            })
            fmt_gold_line = wb.add_format({"bg_color": GOLD})

            fmt_label = wb.add_format({"bold": True, "font_size": 11, "font_color": TEXT})
            fmt_value = wb.add_format({"font_size": 11, "font_color": TEXT})
            fmt_muted = wb.add_format({"font_size": 10, "font_color": MUTED})

            fmt_card_cell = wb.add_format({"border": 1, "border_color": GRID, "bg_color": "white"})
            fmt_card_outer = wb.add_format({"border": 2, "border_color": GOLD, "bg_color": "white"})

            fmt_kpi_box = wb.add_format(
                {"border": 1, "border_color": GRID, "align": "center", "valign": "vcenter", "text_wrap": True})
            fmt_kpi_open = wb.add_format(
                {"border": 1, "border_color": GRID, "align": "center", "valign": "vcenter", "text_wrap": True,
                 "bg_color": OPEN_BG})
            fmt_kpi_close = wb.add_format(
                {"border": 1, "border_color": GRID, "align": "center", "valign": "vcenter", "text_wrap": True,
                 "bg_color": CLOSE_BG})
            fmt_kpi_head = wb.add_format({"border": 2, "border_color": GOLD})

            fmt_header = wb.add_format({
                "bold": True, "font_color": "white", "bg_color": GREEN,
                "align": "center", "valign": "vcenter",
                "border": 1, "border_color": GRID
            })
            fmt_footer = wb.add_format({"font_size": 9, "font_color": MUTED})

            fmt_table_money = wb.add_format(
                {"font_size": 10, "align": "center", "valign": "vcenter", "border": 1, "border_color": GRID,
                 "num_format": "#,##0.00"})
            fmt_table_money_z = wb.add_format(
                {"font_size": 10, "align": "center", "valign": "vcenter", "border": 1, "border_color": GRID,
                 "num_format": "#,##0.00", "bg_color": ZEBRA})

            fmt_table_date = wb.add_format(
                {"font_size": 10, "align": "center", "valign": "vcenter", "border": 1, "border_color": GRID})
            fmt_table_date_z = wb.add_format(
                {"font_size": 10, "align": "center", "valign": "vcenter", "border": 1, "border_color": GRID,
                 "bg_color": ZEBRA})

            fmt_table_text = wb.add_format(
                {"font_size": 10, "align": "right", "valign": "vcenter", "border": 1, "border_color": GRID,
                 "text_wrap": True})
            fmt_table_text_z = wb.add_format(
                {"font_size": 10, "align": "right", "valign": "vcenter", "border": 1, "border_color": GRID,
                 "text_wrap": True, "bg_color": ZEBRA})

            fmt_table_nseq = wb.add_format(
                {"font_size": 10, "align": "center", "valign": "vcenter", "border": 1, "border_color": GRID})
            fmt_table_nseq_z = wb.add_format(
                {"font_size": 10, "align": "center", "valign": "vcenter", "border": 1, "border_color": GRID,
                 "bg_color": ZEBRA})

            fmt_summary_h = wb.add_format(
                {"bold": True, "font_color": "white", "bg_color": GREEN, "align": "center", "valign": "vcenter",
                 "border": 1, "border_color": GRID})
            fmt_summary_money = wb.add_format(
                {"border": 1, "border_color": GRID, "num_format": "#,##0.00", "align": "center", "valign": "vcenter"})
            fmt_summary_text = wb.add_format(
                {"border": 1, "border_color": GRID, "align": "right", "valign": "vcenter", "text_wrap": True})

            fmt_kpi_label = wb.add_format({
                "bold": True, "align": "center", "valign": "vcenter",
                "border": 1, "border_color": GRID,
                "bg_color": SOFT, "font_color": MUTED
            })

            # =========================
            # Sheet 1: كشف حساب
            # =========================
            ws = wb.add_worksheet("كشف حساب")
            ws.right_to_left()
            ws.hide_gridlines(2)

            # ✅ أعرض الأعمدة مضبوط (وجود F للـ nseq)
            ws.set_column("A:A", 14)  # التاريخ
            ws.set_column("B:B", 50)  # البيان
            ws.set_column("C:E", 16)  # مدين/دائن/رصيد
            ws.set_column("F:F", 14)  # رقم النمارة

            ws.set_row(0, 50)
            ws.set_row(1, 30)
            ws.set_row(2, 6)

            # ✅ Header: لازم يمتد لحد F علشان الشكل مايبقاش ناقص
            ws.merge_range("A1:E2", f"كشف حساب  |  فرع: {branch or '—'}", fmt_title)
            ws.merge_range("F1:F2", "", fmt_title)
            ws.merge_range("A3:F3", "", fmt_gold_line)

            logo_path = resource_try("logo.png", "logo.png")
            if logo_path:
                ws.insert_image("F1", logo_path, {
                    "x_scale": 0.14, "y_scale": 0.14,
                    "x_offset": 18, "y_offset": 8,
                    "object_position": 2
                })

            # ---- Customer card area A5:F8 ----
            r1, r2 = 4, 7  # rows 5..8
            c1, c2 = 0, 5  # A..F

            for r in range(r1, r2 + 1):
                for c in range(c1, c2 + 1):
                    ws.write_blank(r, c, None, fmt_card_cell)

            # outer frame
            for c in range(c1, c2 + 1):
                ws.write_blank(r1, c, None, fmt_card_outer)
                ws.write_blank(r2, c, None, fmt_card_outer)
            for r in range(r1, r2 + 1):
                ws.write_blank(r, c1, None, fmt_card_outer)
                ws.write_blank(r, c2, None, fmt_card_outer)

            ws.set_row(4, 22)
            ws.set_row(5, 22)
            ws.set_row(6, 22)
            ws.set_row(7, 22)

            client_line = client_info.replace("\n", " | ").strip() if client_info else "—"

            ws.write("C5", "اسم العميل:", fmt_label)
            ws.merge_range("A5:B5", client_line, fmt_value)

            ws.write("C6", "العنوان:", fmt_label)
            addr = ""
            for ln in (client_info.split("\n") if client_info else []):
                if "العنوان" in ln:
                    addr = ln.split(":", 1)[-1].strip()
            ws.merge_range("A6:B6", addr or "—", fmt_value)

            ws.write("F5", "رقم الحساب:", fmt_label)
            ws.write("E5", account_no or "—", fmt_value)

            ws.write("F6", "نوع الحساب:", fmt_label)
            ws.write("E6", acc_type or "—", fmt_value)

            ws.write("F7", "العملة:", fmt_label)
            ws.write("E7", cur or "—", fmt_value)

            ws.write("F8", "الفترة:", fmt_label)
            ws.merge_range("A8:E8", f"{date_from} إلى {date_to}", fmt_muted)

            # ---- KPI Row ----
            kpi_row = 9
            ws.set_row(kpi_row, 44)
            for c in range(0, 6):
                ws.write_blank(kpi_row, c, None, fmt_kpi_head)

            # ✅ خلي KPI على 5 خلايا + خلية فاضية مكانها F علشان اللوجو/التوازن
            ws.write(kpi_row, 0, f"عدد الحركات\n{len(table_rows)}", fmt_kpi_box)
            ws.write(kpi_row, 1, f"الرصيد الختامي\n{closing_balance:,.2f}", fmt_kpi_close)
            ws.write(kpi_row, 2, f"إجمالي مدين\n{total_debit:,.2f}", fmt_kpi_box)
            ws.write(kpi_row, 3, f"إجمالي دائن\n{total_credit:,.2f}", fmt_kpi_box)
            ws.write(kpi_row, 4, f"رصيد الافتتاح\n{opening_balance:,.2f}", fmt_kpi_open)
            ws.write(kpi_row, 5, "", fmt_kpi_box)

            # ---- Main Table ----
            table_start = 11
            ws.set_row(table_start, 22)

            ws.write(table_start, 0, "التاريخ", fmt_header)
            ws.write(table_start, 1, "البيان / نوع المستند", fmt_header)
            ws.write(table_start, 2, "مدين", fmt_header)
            ws.write(table_start, 3, "دائن", fmt_header)
            ws.write(table_start, 4, "الرصيد", fmt_header)
            ws.write(table_start, 5, "رقم النمارة", fmt_header)

            for i, (d, desc, debit, credit, bal, nseq) in enumerate(table_rows):
                rr = table_start + 1 + i
                zebra = (i % 2 == 1)

                f_date = fmt_table_date_z if zebra else fmt_table_date
                f_text = fmt_table_text_z if zebra else fmt_table_text
                f_mon = fmt_table_money_z if zebra else fmt_table_money
                f_seq = fmt_table_nseq_z if zebra else fmt_table_nseq

                ws.write(rr, 0, d, f_date)
                ws.write(rr, 1, desc if desc else "—", f_text)
                ws.write_number(rr, 2, debit, f_mon)
                ws.write_number(rr, 3, credit, f_mon)
                ws.write_number(rr, 4, bal, f_mon)
                ws.write(rr, 5, nseq, f_seq)  # ✅ اكتب رقم النمارة فعليًا

            last_row = table_start + len(table_rows)

            # ✅ تثبيت الهيدر بتاع الجدول فقط (عشان كله يبقا واضح)
            # ws.freeze_panes(table_start + 1, 0)

            # ✅ للطباعة: كرر صف الهيدر بتاع الجدول فقط (مش الهيدر الكبير)
            # ws.repeat_rows(table_start, table_start)

            ws.set_landscape()
            ws.fit_to_pages(1, 0)
            ws.set_zoom(100)  # زووم طبيعي
            ws.set_default_row(15)

            ws.write(last_row + 2, 0, f"تاريخ الطباعة: {printed_at}", fmt_footer)

            # =========================
            # Sheet 2: Summary
            # =========================
            ws2 = wb.add_worksheet("Summary")
            ws2.right_to_left()
            ws2.hide_gridlines(2)

            ws2.set_row(0, 50)
            ws2.set_row(1, 30)
            ws2.set_row(2, 6)

            ws2.set_column("A:A", 18)
            ws2.set_column("B:B", 24)
            ws2.set_column("C:D", 18)
            ws2.set_column("E:E", 46)

            ws2.merge_range("A1:D2", "ملخص كشف الحساب", fmt_title)
            ws2.merge_range("E1:E2", "", fmt_title)
            ws2.merge_range("A3:E3", "", fmt_gold_line)

            if logo_path:
                ws2.insert_image("E1", logo_path, {
                    "x_scale": 0.14, "y_scale": 0.14,
                    "x_offset": 18, "y_offset": 8,
                    "object_position": 2
                })

            ws2.write("E5", "رقم الحساب:", fmt_label)
            ws2.write("D5", account_no or "—", fmt_value)
            ws2.write("C5", "رقم العميل:", fmt_label)
            ws2.write("B5", client_no or "—", fmt_value)
            ws2.write("A5", f"الفترة: {date_from} إلى {date_to}", fmt_muted)

            ws2.write("E7", "رصيد الافتتاح", fmt_kpi_label)
            ws2.write_number("D7", opening_balance, wb.add_format(
                {"border": 1, "border_color": GRID, "bg_color": OPEN_BG, "num_format": "#,##0.00", "align": "center"}))
            ws2.write("C7", "الرصيد الختامي", fmt_kpi_label)
            ws2.write_number("B7", closing_balance, wb.add_format(
                {"border": 1, "border_color": GRID, "bg_color": CLOSE_BG, "num_format": "#,##0.00", "align": "center"}))

            ws2.write("E8", "إجمالي دائن", fmt_kpi_label)
            ws2.write_number("D8", total_credit, wb.add_format(
                {"border": 1, "border_color": GRID, "num_format": "#,##0.00", "align": "center"}))
            ws2.write("C8", "إجمالي مدين", fmt_kpi_label)
            ws2.write_number("B8", total_debit, wb.add_format(
                {"border": 1, "border_color": GRID, "num_format": "#,##0.00", "align": "center"}))
            ws2.write("A8", f"عدد الحركات: {len(table_rows)}",
                      wb.add_format({"border": 1, "border_color": GRID, "bg_color": SOFT, "align": "center"}))

            ws2.write("E11", "أكبر 5 دائن", wb.add_format({"bold": True, "font_size": 12, "font_color": GREEN}))
            ws2.write_row("A12", ["القيمة", "البيان", "التاريخ"], fmt_summary_h)

            for i, (d, desc, val) in enumerate(top_credits, start=0):
                rr = 12 + 1 + i
                ws2.write_number(rr, 0, val, fmt_summary_money)
                ws2.write(rr, 1, desc if desc else "—", fmt_summary_text)
                ws2.write(rr, 2, d, fmt_table_date)

            ws2.write("E18", "أكبر 5 مدين", wb.add_format({"bold": True, "font_size": 12, "font_color": GREEN}))
            ws2.write_row("A19", ["القيمة", "البيان", "التاريخ"], fmt_summary_h)

            for i, (d, desc, val) in enumerate(top_debits, start=0):
                rr = 19 + 1 + i
                ws2.write_number(rr, 0, val, fmt_summary_money)
                ws2.write(rr, 1, desc if desc else "—", fmt_summary_text)
                ws2.write(rr, 2, d, fmt_table_date)

            ws2.write("E26", "ملخص يومي (للمخطط)", wb.add_format({"bold": True, "font_size": 12, "font_color": GREEN}))
            ws2.write_row("A27", ["إجمالي مدين", "إجمالي دائن", "التاريخ"], fmt_summary_h)

            base_r = 27
            for i, d in enumerate(daily_days):
                rr = base_r + 1 + i
                ws2.write_number(rr, 0, daily[d]["debit"], fmt_summary_money)
                ws2.write_number(rr, 1, daily[d]["credit"], fmt_summary_money)
                ws2.write(rr, 2, d, fmt_table_date)

            if daily_days:
                chart = wb.add_chart({"type": "column"})
                chart.add_series({
                    "name": "إجمالي دائن",
                    "categories": ["Summary", base_r + 1, 2, base_r + len(daily_days), 2],
                    "values": ["Summary", base_r + 1, 1, base_r + len(daily_days), 1],
                })
                chart.add_series({
                    "name": "إجمالي مدين",
                    "categories": ["Summary", base_r + 1, 2, base_r + len(daily_days), 2],
                    "values": ["Summary", base_r + 1, 0, base_r + len(daily_days), 0],
                })
                chart.set_title({"name": "إجمالي دائن/مدين حسب اليوم"})
                chart.set_legend({"position": "bottom"})
                chart.set_size({"width": 720, "height": 300})
                ws2.insert_chart("A31", chart)

            wb.close()
            messagebox.showinfo("تم", "تم تصدير Excel بشكل ثابت ✅")

            self.sys_logger.log(f"📄 تم تصدير بيانات العميل إلى ملف: {file_path}")
            #messagebox.showinfo("نجاح", "تم التصدير بنجاح")
        except Exception as e:
            messagebox.showerror("خطأ", f"حدث خطأ أثناء تصدير Excel:\n{e}")
            self.sys_logger.log(f"❌ فشل تصدير الملف: {e}", type="ERROR")

    def on_show(self):
        """نفس سلوك show_page القديم: تحميل الفروع عند فتح شاشة الحسابات."""
        if self.app is not None:
            self.app.nuwairy_load_branches()
