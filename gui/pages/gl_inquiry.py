# -*- coding: utf-8 -*-
"""
شاشة أستاذ الحسابات العام (GL Inquiry).

مُرحّلة حرفياً من gui.py الأصلي — منطق البحث والعرض كما هو دون تغيير.
"""
import logging
import re
import threading
from datetime import datetime
import os
import sys
import xlsxwriter
import arabic_reshaper

import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
import pandas as pd
from bidi.algorithm import get_display
from tksheet import Sheet
from gui.popup import PremiumSearchPopup
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


class GLInquiryPage(LegacyInquiryPage):
    """شاشة أستاذ الحسابات العام (GL Inquiry)."""
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

        # 1. العنوان والعنوان الفرعي لليمين
        title_wrap = ctk.CTkFrame(header_inner, fg_color="transparent")
        title_wrap.pack(side="right", fill="x", expand=True)  # التعديل هنا: side="right"

        ctk.CTkLabel(
            title_wrap,
            text="🔍 استعلام الأستاذ العام",
            font=("Segoe UI", 22, "bold"),
            text_color=FIB_GREEN
        ).pack(anchor="e")  # التعديل هنا: anchor="e"

        ctk.CTkLabel(
            title_wrap,
            text="ابحث بحساب الأستاذ العام، اختر الفرع والعملة، وحدد فترة التاريخ.",
            font=("Segoe UI", 12),
            text_color="#6B7280"
        ).pack(anchor="e", pady=(4, 0))  # التعديل هنا: anchor="e"

        # 2. أزرار الأكشن لليسار (وتترص من اليمين للشمال)
        actions = ctk.CTkFrame(header_inner, fg_color="transparent")
        actions.pack(side="left")  # التعديل هنا: side="left" (عكس الـ title_wrap)

        self.btn_clear_gl = ctk.CTkButton(
            actions,
            text="مسح",
            fg_color="#F3F4F6",
            text_color="#111827",
            hover_color="#E5E7EB",
            font=("Segoe UI", 12, "bold"),
            height=38,
            corner_radius=10,
            command=self.gl_clear
        )
        self.btn_clear_gl.pack(side="right", padx=(10, 0))  # التعديل هنا: side="right" وعكس الـ padx

        self.btn_search_gl = ctk.CTkButton(
            actions,
            text="بحث الحركات 🔎",
            fg_color=FIB_GOLD,
            text_color="white",
            hover_color="#B78F38",
            font=("Segoe UI", 12, "bold"),
            height=38,
            corner_radius=10,
            command=self.gl_search
        )
        self.btn_search_gl.pack(side="right")  # التعديل هنا: side="right"

        # =========================
        # Filters Card
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

        # Row 1 (الفرع - الأستاذ العام)
        ctk.CTkLabel(form, text="الفرع:", font=label_font, text_color=COLOR_TEXT_MAIN).grid(
            row=0, column=3, sticky="e", pady=(0, 8)
        )
        self.cmb_gl_branch_box, self.combo_gl_branch = self._create_premium_select(
            form,
            values=["جاري التحميل..."],
            default="جاري التحميل...",
            title="اختر الفرع"
        )
        self.cmb_gl_branch_box.grid(row=0, column=2, sticky="ew", pady=(0, 8), padx=(0, 10))  # عكس الـ padx

        ctk.CTkLabel(form, text="الأستاذ العام:", font=label_font, text_color=COLOR_TEXT_MAIN).grid(
            row=0, column=1, sticky="e", pady=(0, 8)
        )

        # 🌟 التعديل هنا: تعريف الدوال أولاً قبل استخدامها في الزرار 🌟 (لم يتم التعديل في المنطق)
        def set_gl_acc_value(selected_val):
            if hasattr(self, 'btn_gl_acc_select'):
                # إضافة: عكسنا السهم ليتناسب مع العربي (السهم على اليسار)
                self.btn_gl_acc_select.configure(text=f"🔽 {selected_val}")
                self.selected_gl_acc = selected_val
            else:
                print("تنبيه: زرار الأستاذ العام غير مسجل في الـ self")

        def open_gl_acc_popup_cmd():
            data = getattr(self, 'all_gl_codes', [])
            if not data:
                data = ["جاري تحميل البيانات، يرجى الانتظار ثانية..."]
            PremiumSearchPopup(self, "اختر الأستاذ العام", data, set_gl_acc_value)

        # ==========================================
        # زرار الأستاذ العام الأخضر (Solid Green)
        # ==========================================
        self.btn_gl_acc_select = ctk.CTkButton(
            form,
            text="🔽 - اختر الأستاذ العام -",  # التعديل هنا: السهم على اليسار
            font=("Segoe UI", 12, "bold"),
            text_color="white",
            fg_color=FIB_GREEN,
            hover_color="#08472C",
            border_width=0,
            height=40,
            corner_radius=10,
            anchor="e",  # النص يبدأ من اليمين
            command=open_gl_acc_popup_cmd
        )
        self.btn_gl_acc_select.grid(row=0, column=0, sticky="ew", pady=(0, 8), padx=(0, 10))  # عكس الـ padx

        self.combo_gl_acc = self.btn_gl_acc_select
        self.combo_gl_acc.get = lambda: getattr(self, 'selected_gl_acc', "")

        # Row 2 (العملة - من تاريخ)
        ctk.CTkLabel(form, text="العملة:", font=label_font, text_color=COLOR_TEXT_MAIN).grid(
            row=1, column=3, sticky="e", pady=(0, 8)
        )
        self.cmb_gl_curr_box, self.combo_gl_currency = self._create_premium_select(
            form,
            values=["جاري التحميل..."],
            default="جاري التحميل...",
            title="اختر العملة"
        )
        self.cmb_gl_curr_box.grid(row=1, column=2, sticky="ew", pady=(0, 8), padx=(0, 10))  # عكس الـ padx

        ctk.CTkLabel(form, text="من تاريخ:", font=label_font, text_color=COLOR_TEXT_MAIN).grid(
            row=1, column=1, sticky="e", pady=(0, 8)
        )
        self.ent_gl_date_from = ctk.CTkEntry(
            form,
            placeholder_text="YYYY-MM-DD",
            justify="right",  # التعديل هنا: المؤشر يبدأ من اليمين
            height=40,
            corner_radius=10
        )
        self.ent_gl_date_from.grid(row=1, column=0, sticky="ew", pady=(0, 8), padx=(0, 10))  # عكس الـ padx

        # Row 3 (إلى تاريخ - زرار التحديث)
        ctk.CTkLabel(form, text="إلى تاريخ:", font=label_font, text_color=COLOR_TEXT_MAIN).grid(
            row=2, column=1, sticky="e"
        )
        self.ent_gl_date_to = ctk.CTkEntry(
            form,
            placeholder_text="YYYY-MM-DD",
            justify="right",  # التعديل هنا: المؤشر يبدأ من اليمين
            height=40,
            corner_radius=10
        )
        self.ent_gl_date_to.grid(row=2, column=0, sticky="ew", padx=(0, 10))  # عكس الـ padx

        def refresh_all_gl_data():
            if hasattr(self, 'sys_logger'):
                self.sys_logger.log("🔄 المستخدم طلب تحديث قوائم (الفرع، الأستاذ العام، العملات) يدوياً.")
            if hasattr(self, 'gl_load_codes'): self.gl_load_codes()
            if hasattr(self, 'nuwairy_load_branches'): self.nuwairy_load_branches()
            if hasattr(self, 'gl_load_currencies'): self.gl_load_currencies()

        self.btn_refresh_gl = ctk.CTkButton(
            form,
            text="تحديث القوائم 🔄",  # التعديل هنا: الأيقونة لليسار
            fg_color="#F3F4F6",
            text_color="#111827",
            hover_color="#E5E7EB",
            font=("Segoe UI", 12, "bold"),
            height=40,
            corner_radius=10,
            command=refresh_all_gl_data
        )
        self.btn_refresh_gl.grid(row=2, column=2, sticky="ew", padx=(0, 10))  # عكس الـ padx

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

        # 3. محاذاة كارت المعلومات لليمين
        ctk.CTkLabel(
            info_inner,
            text="بيانات الحساب",
            font=("Segoe UI", 12, "bold"),
            text_color=COLOR_TEXT_MAIN
        ).pack(anchor="e")  # التعديل هنا: anchor="e"

        self.lbl_gl_info = ctk.CTkLabel(
            info_inner,
            text="—",
            font=("Segoe UI", 12),
            text_color="#4B5563",
            justify="right",  # التعديل هنا: justify="right"
            anchor="e",  # التعديل هنا: anchor="e"
            wraplength=900
        )
        self.lbl_gl_info.pack(anchor="e", pady=(6, 0))  # التعديل هنا: anchor="e"

        # 👇👇 الإضافة الجديدة: مكان مخصص لعرض رصيد 31-03-2017
        self.lbl_gl_balance_2017 = ctk.CTkLabel(
            info_inner,
            text="الرصيد في 31-03-2017: 0.00",
            font=("Segoe UI", 13, "bold"),
            text_color="#10B981",  # لون أخضر مميز
            justify="right",
            anchor="e"
        )
        self.lbl_gl_balance_2017.pack(anchor="e", pady=(4, 0))
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

        # 4. شريط البحث وأزرار التصدير لليمين
        self.ent_gl_search = ctk.CTkEntry(
            toolbar,
            placeholder_text="بحث داخل النتائج…",
            justify="right",  # التعديل هنا: المؤشر يبدأ يمين
            height=36,
            corner_radius=10
        )
        self.ent_gl_search.pack(side="right", fill="x", expand=True,
                                padx=(10, 0))  # التعديل هنا: side="right" وعكس الـ padx

        btn_export = ctk.CTkButton(
            toolbar, text="🖨️ Export PDF",
            fg_color=FIB_GREEN, hover_color="#0B5C3A",
            height=36, corner_radius=10,
            font=("Segoe UI", 12, "bold"),
            command=self.gl_export_pdf
        )
        btn_export.pack(side="right")  # التعديل هنا: side="right"

        btn_export_excel = ctk.CTkButton(
            toolbar, text="📊 Export Excel",
            fg_color=FIB_GREEN, hover_color="#0B5C3A",
            height=36, corner_radius=10,
            font=("Segoe UI", 12, "bold"),
            command=self.gl_export_excel
        )
        btn_export_excel.pack(side="right", padx=(0, 10))  # التعديل هنا: side="right" وعكس الـ padx

        sheet_frame = ctk.CTkFrame(table_inner, fg_color="transparent")
        sheet_frame.pack(fill="both", expand=True)

        self._init_gl_sheet(sheet_frame)

    def gl_load_codes(self):
        """تحميل القائمة وتخزينها في الذاكرة لتعمل مع الـ Premium Popup"""

        def fetch_task():
            try:
                engine = self._get_db_connection()
                query = "SELECT snmsubb FROM [dbo].[TBL_GL_Codes] WHERE snmsubb IS NOT NULL AND snmsubb != ''"
                df = pd.read_sql(query, engine)

                if df.empty:
                    self.all_gl_codes = []
                else:
                    # حفظ الأسماء في الميموري فوراً
                    self.all_gl_codes = df["snmsubb"].astype(str).str.strip().drop_duplicates().tolist()
                    self.all_gl_codes.sort()
                    if hasattr(self, 'sys_logger'):
                        self.sys_logger.log(f"✅ تم تحميل {len(self.all_gl_codes)} كود أستاذ عام بنجاح في الخلفية.")

            except Exception as e:
                if hasattr(self, 'sys_logger'):
                    self.sys_logger.log(f"❌ خطأ أثناء تحميل أكواد الأستاذ العام: {e}", "ERROR")
                self.all_gl_codes = ["- خطأ في الاتصال بقاعدة البيانات -"]
        threading.Thread(target=fetch_task, daemon=True).start()

    def filter_gl_codes(self, event):
        """دالة للبحث الحي داخل الـ 4000 اسم بسرعة البرق"""
        if not hasattr(self, 'all_gl_codes'):
            return

        # لو بيتحرك بالأسهم مش عايزين نبوظ الفلترة
        if event.keysym in ('Up', 'Down', 'Left', 'Right', 'Return'):
            return

        typed_text = self.combo_gl_acc.get().strip()

        if typed_text == "":
            filtered_codes = self.all_gl_codes[:50]
        else:
            # List Comprehension دي أسرع طريقة بحث في بايثون
            filtered_codes = [code for code in self.all_gl_codes if typed_text.lower() in code.lower()][:50]

            if not filtered_codes:
                filtered_codes = ["- لا توجد نتائج -"]

        # التحديث الفوري للقائمة
        self.combo_gl_acc.configure(values=filtered_codes)

    def gl_load_currencies(self):
        def fetch_task():
            try:
                # استخدام دالة الاتصال الجاهزة بتاعتك
                engine = self._get_db_connection()
                query = "SELECT cnm FROM [dbo].[TBL_Currency] WHERE cnm IS NOT NULL"
                df = pd.read_sql(query, engine)

                if df.empty:
                    currencies = ["- لا توجد عملات -"]
                else:
                    currencies = df["cnm"].astype(str).str.strip().tolist()

                if hasattr(self, 'combo_gl_currency'):
                    self.after(0, lambda: self.combo_gl_currency.configure(values=currencies))
                    self.after(0, lambda: self.combo_gl_currency.set(currencies[0]))
                if hasattr(self, 'sys_logger'):
                    self.sys_logger.log("✅ تم تحميل قائمة العملات للأستاذ العام بنجاح.")
            except Exception as e:
                if hasattr(self, 'sys_logger'):
                    self.sys_logger.log(f"❌ خطأ أثناء تحميل العملات للأستاذ العام: {e}", "ERROR")
                if hasattr(self, 'combo_gl_currency'):
                    self.after(0, lambda: self.combo_gl_currency.configure(values=["- خطأ في الاتصال -"]))
                    self.after(0, lambda: self.combo_gl_currency.set("- خطأ في الاتصال -"))
        threading.Thread(target=fetch_task, daemon=True).start()

    def _init_gl_sheet(self, parent):
        self.gl_sheet = Sheet(
            parent,
            show_x_scrollbar=True,
            show_y_scrollbar=True,
            show_row_index=False,
            show_top_left=False,
            align="e",  # 👈 التعديل الأول: محاذاة بيانات الخلايا لليمين
            header_align="e",  # 👈 التعديل الثاني: محاذاة عناوين الأعمدة لليمين
            height=450,
            width=900,
            outline_thickness=1,
            outline_color="#E6E8EB",
            grid_color="#E5E7EB",
            selected_cells_bg="#DDEFE8",
            selected_cells_fg="#111827",
        )

        headers = [
            "التاريخ",
            "الفرع",
            "رقم الحساب",
            "العملة",
            "البيان",
            "مدين",
            "دائن",
            "الرصيد",
            "رقم النمارة"
        ]
        self.gl_sheet.headers(headers)

        # زودنا مساحة للعمود الأخير (100)
        self.gl_sheet.set_column_widths([100, 120, 130, 90, 420, 120, 120, 130, 100])

        # السطر السحري: إخفاء العمود التاسع (الاندكس بتاعه 8)
        self.gl_sheet.hide_columns([8])

        self.gl_sheet.pack(fill="both", expand=True)

    def gl_clear(self):
        """تفريغ الفلاتر وجدول البيانات"""

        # 1. مسح الأستاذ العام (التعامل معاه كـ Button مش ComboBox)
        if hasattr(self, "btn_gl_acc_select"):
            default_text = "- اختر الأستاذ العام -"
            self.btn_gl_acc_select.configure(text=f"{default_text} 🔽")
            self.selected_gl_acc = ""  # تفريغ المتغير اللي بيسحب منه الـ get

        # 2. مسح الفرع
        if hasattr(self, "combo_gl_branch"):
            vals = getattr(self.combo_gl_branch, '_values_list', ["- اختر الفرع -"])
            if hasattr(self.combo_gl_branch, 'set'):
                self.combo_gl_branch.set(vals[0] if vals else "")

        # 3. مسح العملة
        if hasattr(self, "combo_gl_currency"):
            vals = getattr(self.combo_gl_currency, '_values_list', ["الكل (All)"])
            if hasattr(self.combo_gl_currency, 'set'):
                self.combo_gl_currency.set(vals[0] if vals else "")

        # 4. مسح التواريخ
        if hasattr(self, "ent_gl_date_from"):
            self.ent_gl_date_from.delete(0, "end")
        if hasattr(self, "ent_gl_date_to"):
            self.ent_gl_date_to.delete(0, "end")

        # 5. مسح شريط البحث السريع
        if hasattr(self, "ent_gl_search"):
            self.ent_gl_search.delete(0, "end")

        # 6. مسح بيانات الحساب (Info Label)
        if hasattr(self, "lbl_gl_info"):
            self.lbl_gl_info.configure(text="—")

        # 7. مسح الشيت (مع الحفاظ على 8 أعمدة عشان الشكل ميبوظش)
        if hasattr(self, "gl_sheet"):
            try:
                empty_row = ["", "", "", "", "", "", "", ""]
                self.gl_sheet.set_sheet_data([empty_row], reset_col_positions=False, reset_row_positions=True)
            except:
                pass

        if hasattr(self, 'sys_logger'):
            self.sys_logger.log("🧹 المستخدم قام بمسح فلاتر بحث الأستاذ العام وإفراغ الجدول.")

    def gl_export_excel(self):
        # ==========================================
        # 1. التأكد من وجود بيانات صالحة للتصدير
        # ==========================================
        if not hasattr(self, "gl_sheet"):
            messagebox.showwarning("تنبيه", "لا توجد بيانات للتصدير.")
            return

        rows = self.gl_sheet.get_sheet_data()

        # التحقق من أن الشيت لا يحتوي على رسالة التحميل أو فارغ
        if not rows or (len(rows) == 1 and ("جاري" in str(rows[0]) or "لا توجد" in str(rows[0]))):
            messagebox.showwarning("تنبيه", "لا توجد بيانات حقيقية للتصدير. قم بالبحث أولاً.")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel Files", "*.xlsx")],
            title="تصدير إكسيل - الأستاذ العام"
        )
        if not file_path:
            return
        if hasattr(self, 'sys_logger'):
            self.sys_logger.log(f"📥 بدء عملية تصدير الأستاذ العام إلى إكسيل.. مسار الحفظ المختار: [{file_path}]")

        # ==========================================
        # 2. الدوال المساعدة (Helpers)
        # ==========================================
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
            except Exception:
                return 0.0

        def parse_date_safe(s):
            s = (s or "").strip()
            for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d", "%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S"):
                try:
                    return datetime.strptime(s, fmt).date()
                except ValueError:
                    continue
            return None

        def safe_txt(x):
            return "" if x is None else str(x).strip()

        def resource_try(*names):
            """لجلب مسار اللوجو سواء في بيئة التطوير أو بعد الـ Build"""
            for n in names:
                try:
                    if getattr(sys, 'frozen', False) or '__compiled__' in globals():
                        p = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), n)
                    else:
                        p = os.path.join(os.path.dirname(os.path.abspath(__file__)), n)
                    if os.path.exists(p):
                        return p
                except Exception:
                    pass
            return None

        # ==========================================
        # 3. إعداد البيانات والتنسيقات (Data Prep)
        # ==========================================
        try:
            # --- ألوان الهوية البصرية ---
            GREEN = "#0B5C3A"
            GOLD = "#B08D2D"
            GRID = "#E6EAEE"
            ZEBRA = "#FAFBFC"
            TEXT = "#111827"
            MUTED = "#4B5563"
            SOFT = "#F9F3E6"
            OPEN_BG = "#FFF1D6"
            CLOSE_BG = "#FFF5DB"

            # --- جلب الفلاتر الأساسية ---
            gl_acc_name = self.combo_gl_acc.get().strip() if hasattr(self, 'combo_gl_acc') else "—"
            branch = self.combo_gl_branch.get().strip() if hasattr(self, 'combo_gl_branch') else "—"
            date_from = self.ent_gl_date_from.get().strip() if hasattr(self, 'ent_gl_date_from') else ""
            date_to = self.ent_gl_date_to.get().strip() if hasattr(self, 'ent_gl_date_to') else ""

            table_rows = []
            total_credit = 0.0
            total_debit = 0.0
            closing_balance = 0.0
            opening_balance = 0.0
            is_first_row = True

            # معالجة الصفوف القادمة من الواجهة
            # الترتيب في الواجهة: [التاريخ, الفرع, رقم الحساب, العملة, البيان, مدين, دائن, الرصيد, رقم النمارة]
            for r in rows:
                if len(r) < 8:
                    continue

                d = safe_txt(r[0])
                acc_no = safe_txt(r[2])
                curr = safe_txt(r[3])
                desc = safe_txt(r[4])
                debit = money_to_float(r[5])
                credit = money_to_float(r[6])
                bal = money_to_float(r[7])

                # 🌟 قراءة النمارة من العمود المخفي 🌟
                aseq = safe_txt(r[8]) if len(r) > 8 else ""

                if is_first_row:
                    opening_balance = bal - credit + debit
                    is_first_row = False

                total_credit += credit
                total_debit += debit
                closing_balance = bal

                # 🌟 إضافة aseq لمصفوفة البيانات 🌟
                table_rows.append((d, desc, aseq, acc_no, curr, debit, credit, bal))

            if (not date_from or not date_to) and table_rows:
                ds = [parse_date_safe(x[0]) for x in table_rows]
                ds = [dx for dx in ds if dx]
                if ds:
                    mn, mx = min(ds), max(ds)
                    date_from = date_from or mn.strftime("%Y-%m-%d")
                    date_to = date_to or mx.strftime("%Y-%m-%d")

            printed_at = datetime.now().strftime("%Y-%m-%d %H:%M")

            # 🌟 تعديل المتغيرات المستخرجة عشان توافق العدد الجديد 🌟
            credits_only = [(d, desc, c) for (d, desc, aseq, acc, cur, deb, c, bal) in table_rows if c > 0]
            debits_only = [(d, desc, deb) for (d, desc, aseq, acc, cur, deb, c, bal) in table_rows if deb > 0]
            top_credits = sorted(credits_only, key=lambda x: x[2], reverse=True)[:5]
            top_debits = sorted(debits_only, key=lambda x: x[2], reverse=True)[:5]

            daily = {}
            for d, desc, aseq, acc, cur, deb, c, bal in table_rows:
                daily.setdefault(d, {"credit": 0.0, "debit": 0.0})
                daily[d]["credit"] += c
                daily[d]["debit"] += deb

            daily_days = sorted(daily.keys(), key=lambda x: (parse_date_safe(x) or datetime.max.date(), x))

            # ==========================================
            # 4. بناء ملف الإكسيل
            # ==========================================
            wb = xlsxwriter.Workbook(file_path)

            # --- إعداد تنسيقات الخلايا ---
            fmt_title = wb.add_format(
                {"bold": True, "font_size": 18, "font_color": "white", "align": "center", "valign": "vcenter",
                 "bg_color": GREEN})
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
            fmt_header = wb.add_format(
                {"bold": True, "font_color": "white", "bg_color": GREEN, "align": "center", "valign": "vcenter",
                 "border": 1, "border_color": GRID})
            fmt_footer = wb.add_format({"font_size": 9, "font_color": MUTED})

            fmt_mon = wb.add_format(
                {"font_size": 10, "align": "center", "valign": "vcenter", "border": 1, "border_color": GRID,
                 "num_format": "#,##0.00"})
            fmt_mon_z = wb.add_format(
                {"font_size": 10, "align": "center", "valign": "vcenter", "border": 1, "border_color": GRID,
                 "num_format": "#,##0.00", "bg_color": ZEBRA})
            fmt_dat = wb.add_format(
                {"font_size": 10, "align": "center", "valign": "vcenter", "border": 1, "border_color": GRID})
            fmt_dat_z = wb.add_format(
                {"font_size": 10, "align": "center", "valign": "vcenter", "border": 1, "border_color": GRID,
                 "bg_color": ZEBRA})
            fmt_txt = wb.add_format(
                {"font_size": 10, "align": "right", "valign": "vcenter", "border": 1, "border_color": GRID,
                 "text_wrap": True})
            fmt_txt_z = wb.add_format(
                {"font_size": 10, "align": "right", "valign": "vcenter", "border": 1, "border_color": GRID,
                 "text_wrap": True, "bg_color": ZEBRA})

            fmt_summary_h = wb.add_format(
                {"bold": True, "font_color": "white", "bg_color": GREEN, "align": "center", "valign": "vcenter",
                 "border": 1, "border_color": GRID})
            fmt_summary_money = wb.add_format(
                {"border": 1, "border_color": GRID, "num_format": "#,##0.00", "align": "center", "valign": "vcenter"})
            fmt_summary_text = wb.add_format(
                {"border": 1, "border_color": GRID, "align": "right", "valign": "vcenter", "text_wrap": True})
            fmt_kpi_label = wb.add_format(
                {"bold": True, "align": "center", "valign": "vcenter", "border": 1, "border_color": GRID,
                 "bg_color": SOFT, "font_color": MUTED})

            # ==========================================
            # Sheet 1: حركات الأستاذ العام
            # ==========================================
            ws = wb.add_worksheet("حركات الأستاذ العام")
            ws.right_to_left()
            ws.hide_gridlines(2)

            # 🌟 تعديل مساحات الأعمدة عشان توافق 8 أعمدة بدل 7 🌟
            ws.set_column("A:A", 14)  # التاريخ
            ws.set_column("B:B", 40)  # البيان
            ws.set_column("C:C", 14)  # النمارة (العمود الجديد)
            ws.set_column("D:D", 18)  # رقم الحساب
            ws.set_column("E:E", 10)  # العملة
            ws.set_column("F:H", 16)  # مدين، دائن، الرصيد

            ws.set_row(0, 50)
            ws.set_row(1, 30)
            ws.set_row(2, 6)

            branch_title = branch.split(" - ")[-1] if branch else "—"

            # 🌟 تمديد الدمج لعمود H 🌟
            ws.merge_range("A1:G2", f"كشف حساب أستاذ عام  |  الفرع: {branch_title}", fmt_title)
            ws.write("H1", "", fmt_title)
            ws.write("H2", "", fmt_title)
            ws.merge_range("A3:H3", "", fmt_gold_line)

            logo_path = resource_try("logo.png", "logo.jpeg", "logo.jpg")
            if logo_path:
                ws.insert_image("H1", logo_path, {
                    "x_scale": 0.14, "y_scale": 0.14,
                    "x_offset": 20, "y_offset": 8,
                    "object_position": 2
                })

            # --- كارت بيانات الحساب ---
            r1, r2 = 4, 6
            c1, c2 = 0, 7  # 🌟 تمديد الكارت لـ 7 بدل 6 🌟
            for r in range(r1, r2 + 1):
                for c in range(c1, c2 + 1):
                    ws.write_blank(r, c, None, fmt_card_cell)

            for c in range(c1, c2 + 1):
                ws.write_blank(r1, c, None, fmt_card_outer)
                ws.write_blank(r2, c, None, fmt_card_outer)
            for r in range(r1, r2 + 1):
                ws.write_blank(r, c1, None, fmt_card_outer)
                ws.write_blank(r, c2, None, fmt_card_outer)

            ws.set_row(4, 25)
            ws.set_row(5, 25)
            ws.set_row(6, 25)

            ws.write("D5", "اسم الحساب:", fmt_label)
            ws.merge_range("A5:C5", gl_acc_name, fmt_value)

            ws.write("H5", "الفرع المختار:", fmt_label)
            ws.merge_range("E5:G5", branch, fmt_value)

            ws.write("H6", "تاريخ البحث:", fmt_label)
            ws.merge_range("E6:G6", f"{date_from} إلى {date_to}", fmt_muted)

            # --- أرقام الـ KPI ---
            kpi_row = 8
            ws.set_row(kpi_row, 44)
            for c in range(0, 8):
                ws.write_blank(kpi_row, c, None, fmt_kpi_head)

            ws.write(kpi_row, 0, f"عدد الحركات\n{len(table_rows)}", fmt_kpi_box)
            ws.merge_range(kpi_row, 1, kpi_row, 2, f"الرصيد الختامي\n{closing_balance:,.2f}", fmt_kpi_close)
            ws.write(kpi_row, 3, f"إجمالي مدين\n{total_debit:,.2f}", fmt_kpi_box)
            ws.write(kpi_row, 4, f"إجمالي دائن\n{total_credit:,.2f}", fmt_kpi_box)
            ws.merge_range(kpi_row, 5, kpi_row, 7, f"الرصيد الافتتاحي\n{opening_balance:,.2f}", fmt_kpi_open)

            # --- جدول الحركات الأساسي ---
            table_start = 10
            ws.set_row(table_start, 22)

            # 🌟 إضافة رقم النمارة كعمود ثالث في الجدول 🌟
            headers = ["التاريخ", "البيان", "رقم النمارة", "رقم الحساب الفرعي", "العملة", "مدين", "دائن", "الرصيد"]
            for col, head in enumerate(headers):
                ws.write(table_start, col, head, fmt_header)

            # 🌟 إضافة aseq في اللوب الخاص بكتابة الصفوف 🌟
            for i, (d, desc, aseq, acc, cur, deb, cred, bal) in enumerate(table_rows):
                rr = table_start + 1 + i
                zebra = (i % 2 == 1)
                ws.write(rr, 0, d, fmt_dat_z if zebra else fmt_dat)
                ws.write(rr, 1, desc if desc else "—", fmt_txt_z if zebra else fmt_txt)
                ws.write(rr, 2, aseq if aseq else "—", fmt_dat_z if zebra else fmt_dat)
                ws.write(rr, 3, acc, fmt_dat_z if zebra else fmt_dat)
                ws.write(rr, 4, cur, fmt_dat_z if zebra else fmt_dat)
                ws.write_number(rr, 5, deb, fmt_mon_z if zebra else fmt_mon)
                ws.write_number(rr, 6, cred, fmt_mon_z if zebra else fmt_mon)
                ws.write_number(rr, 7, bal, fmt_mon_z if zebra else fmt_mon)

            last_row = table_start + len(table_rows)

            ws.set_landscape()
            ws.fit_to_pages(1, 0)
            ws.set_zoom(90)
            ws.write(last_row + 2, 0, f"تاريخ الطباعة: {printed_at}", fmt_footer)

            # ==========================================
            # Sheet 2: ملخص وإحصائيات
            # ==========================================
            ws2 = wb.add_worksheet("ملخص وإحصائيات")
            ws2.right_to_left()
            ws2.hide_gridlines(2)

            ws2.set_row(0, 50)
            ws2.set_row(1, 30)
            ws2.set_row(2, 6)
            ws2.set_column("A:A", 18)
            ws2.set_column("B:B", 40)
            ws2.set_column("C:E", 18)

            ws2.merge_range("A1:D2", "ملخص الأستاذ العام", fmt_title)
            ws2.write("E1", "", fmt_title)
            ws2.write("E2", "", fmt_title)
            ws2.merge_range("A3:E3", "", fmt_gold_line)

            if logo_path:
                ws2.insert_image("E1", logo_path, {
                    "x_scale": 0.14, "y_scale": 0.14,
                    "x_offset": 10, "y_offset": 8,
                    "object_position": 2
                })

            ws2.write("E5", "اسم الحساب:", fmt_label)
            ws2.merge_range("A5:D5", gl_acc_name, fmt_value)

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

            # --- أكبر 5 حركات دائنة ---
            ws2.write("E11", "أكبر 5 حركات دائنة", wb.add_format({"bold": True, "font_size": 12, "font_color": GREEN}))
            ws2.write_row("A12", ["القيمة", "البيان", "التاريخ"], fmt_summary_h)
            for i, (d, desc, val) in enumerate(top_credits):
                rr = 12 + 1 + i
                ws2.write_number(rr, 0, val, fmt_summary_money)
                ws2.write(rr, 1, desc if desc else "—", fmt_summary_text)
                ws2.write(rr, 2, d, fmt_dat)

            # --- أكبر 5 حركات مدينة ---
            ws2.write("E19", "أكبر 5 حركات مدينة", wb.add_format({"bold": True, "font_size": 12, "font_color": GREEN}))
            ws2.write_row("A20", ["القيمة", "البيان", "التاريخ"], fmt_summary_h)
            for i, (d, desc, val) in enumerate(top_debits):
                rr = 20 + 1 + i
                ws2.write_number(rr, 0, val, fmt_summary_money)
                ws2.write(rr, 1, desc if desc else "—", fmt_summary_text)
                ws2.write(rr, 2, d, fmt_dat)

            # --- ملخص المخطط اليومي (Chart) ---
            ws2.write("E27", "ملخص يومي (للمخطط)", wb.add_format({"bold": True, "font_size": 12, "font_color": GREEN}))
            ws2.write_row("A28", ["إجمالي مدين", "إجمالي دائن", "التاريخ"], fmt_summary_h)

            base_r = 28
            for i, d in enumerate(daily_days):
                rr = base_r + 1 + i
                ws2.write_number(rr, 0, daily[d]["debit"], fmt_summary_money)
                ws2.write_number(rr, 1, daily[d]["credit"], fmt_summary_money)
                ws2.write(rr, 2, d, fmt_dat)

            if daily_days:
                chart = wb.add_chart({"type": "column"})
                chart.add_series({
                    "name": "إجمالي دائن",
                    "categories": ["ملخص وإحصائيات", base_r + 1, 2, base_r + len(daily_days), 2],
                    "values": ["ملخص وإحصائيات", base_r + 1, 1, base_r + len(daily_days), 1],
                })
                chart.add_series({
                    "name": "إجمالي مدين",
                    "categories": ["ملخص وإحصائيات", base_r + 1, 2, base_r + len(daily_days), 2],
                    "values": ["ملخص وإحصائيات", base_r + 1, 0, base_r + len(daily_days), 0],
                })
                chart.set_title({"name": "السيولة (مدين/دائن) حسب اليوم"})
                chart.set_legend({"position": "bottom"})
                chart.set_size({"width": 600, "height": 300})
                ws2.insert_chart("A32", chart)

            wb.close()

            # --- إنهاء العملية بنجاح ---
            messagebox.showinfo("تم", "تم تصدير تقرير الأستاذ العام إلى إكسيل بنجاح ✅")

            if hasattr(self, 'sys_logger'):
                self.sys_logger.log(f"📄 تم تصدير بيانات الأستاذ العام إلى ملف: {file_path}")

            try:
                os.startfile(file_path)
            except Exception:
                pass

        except Exception as e:
            messagebox.showerror("خطأ", f"حدث خطأ أثناء تصدير Excel:\n{e}")
            if hasattr(self, 'sys_logger'):
                self.sys_logger.log(f"❌ فشل تصدير الملف: {e}", type="ERROR")

    def gl_export_pdf(self):
        """تصدير PDF بالتنسيق السليم واعتبار أول حركة هي الرصيد الافتتاحي مع إضافة رصيد 2017"""

        try:
            def ar(txt: str) -> str:
                txt = "" if txt is None else str(txt)
                reshaped = arabic_reshaper.reshape(txt)
                return get_display(reshaped, base_dir='R')
        except Exception:
            def ar(txt: str) -> str:
                return "" if txt is None else str(txt)

        try:
            rows = self.gl_sheet.get_sheet_data()
        except Exception:
            rows = []

        if not rows or (len(rows) == 1 and ("جاري" in str(rows[0]) or "لا توجد" in str(rows[0]))):
            messagebox.showwarning("تنبيه", "لا توجد بيانات للتصدير.")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF Files", "*.pdf")],
            initialfile=f"كشف_حساب_أستاذ_عام_{datetime.now().strftime('%Y%m%d')}.pdf"
        )

        if not file_path:
            return
        if hasattr(self, 'sys_logger'):
            self.sys_logger.log(f"📥 بدء عملية تصدير الأستاذ العام إلى إكسيل.. مسار الحفظ المختار: [{file_path}]")
        GREEN = colors.HexColor("#1F6B4B")
        GOLD = colors.HexColor("#B08D2D")
        DGRAY = colors.HexColor("#5B6770")
        GRID = colors.HexColor("#E7ECEF")
        BORDER = colors.HexColor("#C9D1D8")
        ZEBRA = colors.HexColor("#FAFBFC")
        OPEN_BG = colors.HexColor("#FFF1D6")
        CLOSE_BG = colors.HexColor("#FFF5DB")

        def resource_path(relative_path):
            try:
                base_path = sys._MEIPASS
            except Exception:
                base_path = os.path.abspath(".")
            return os.path.join(base_path, relative_path)

        def resource_try(*names):
            for n in names:
                p = resource_path(n)
                if p and os.path.exists(p): return p
            return None

        def money_to_float(s):
            if not s: return 0.0
            s = str(s).replace(",", "").replace(" ", "")
            s = re.sub(r"[^0-9\.\-]", "", s)
            try:
                return float(s) if s else 0.0
            except:
                return 0.0

        def fmt2(x: float) -> str:
            return f"{x:,.2f}"

        gl_acc_name = self.combo_gl_acc.get().strip()
        branch_name = self.combo_gl_branch.get().strip().split(" - ")[-1]
        currency_name = self.combo_gl_currency.get().strip()
        date_from = self.ent_gl_date_from.get().strip()
        date_to = self.ent_gl_date_to.get().strip()

        period_text = ""
        if date_from or date_to:
            period_text = f"الفترة: {date_from if date_from else 'البداية'}  إلى  {date_to if date_to else 'اليوم'}"

        total_credit = 0.0
        total_debit = 0.0
        closing_balance = 0.0
        opening_balance_val = 0.0
        trx_count = 0

        # ✅ قراءة رصيد الافتتاح من أول حركة في الشيت مباشرة
        for r in rows:
            if len(r) < 8: continue

            if trx_count == 0:
                opening_balance_val = money_to_float(r[7])  # رصيد أول حركة

            total_debit += money_to_float(r[5])
            total_credit += money_to_float(r[6])
            closing_balance = money_to_float(r[7])
            trx_count += 1

        printed_at = datetime.now().strftime("%Y-%m-%d %H:%M")

        try:
            font_path = resource_try("Amiri-Regular.ttf")
            if not font_path:
                messagebox.showerror("خطأ", "ملف الخط Amiri-Regular.ttf غير موجود.")
                return

            pdfmetrics.registerFont(TTFont("AR", font_path))
            base_font = "AR"
            styles = getSampleStyleSheet()

            st_right = ParagraphStyle("right_ar", parent=styles["Normal"], fontName=base_font, fontSize=10, leading=14,
                                      alignment=TA_RIGHT, textColor=colors.black)
            st_left = ParagraphStyle("left_muted", parent=styles["Normal"], fontName=base_font, fontSize=10, leading=14,
                                     alignment=TA_LEFT, textColor=DGRAY)
            st_center_date = ParagraphStyle("center_date", parent=styles["Normal"], fontName=base_font, fontSize=9,
                                            leading=12, alignment=TA_CENTER, textColor=colors.black)
            st_kpi_label = ParagraphStyle("kpi_label", parent=styles["Normal"], fontName=base_font, fontSize=9,
                                          leading=11, alignment=TA_CENTER, textColor=DGRAY)
            st_kpi_value = ParagraphStyle("kpi_value", parent=styles["Normal"], fontName=base_font, fontSize=11,
                                          leading=14, alignment=TA_CENTER, textColor=colors.black)

            doc = SimpleDocTemplate(file_path, pagesize=A4, leftMargin=14 * mm, rightMargin=14 * mm, topMargin=46 * mm,
                                    bottomMargin=14 * mm)

            logo_img = None
            logo_path = resource_try("logo.png", "logo.jpg", "faisal_logo.png", "faisal_logo.jpg")
            if logo_path:
                try:
                    logo_img = ImageReader(logo_path)
                except:
                    pass

            def draw_header_footer(canv, doc_):
                canv.saveState()
                ww, hh = A4
                header_h = 34 * mm
                canv.setFillColor(GREEN)
                canv.rect(0, hh - header_h, ww, header_h, fill=1, stroke=0)
                canv.setFillColor(GOLD)
                canv.rect(0, hh - header_h, ww, 2 * mm, fill=1, stroke=0)

                if logo_img:
                    canv.setFillColor(colors.white)
                    canv.roundRect(13 * mm, hh - header_h + 4.5 * mm, 26 * mm, 26 * mm, 3 * mm, fill=1, stroke=0)
                    canv.drawImage(logo_img, 15 * mm, hh - header_h + 6.5 * mm, width=22 * mm, height=22 * mm,
                                   preserveAspectRatio=True, mask='auto')

                canv.setFillColor(colors.white)
                canv.setFont(base_font, 16)
                title = f"كشف الأستاذ العام | فرع: {branch_name}" if branch_name else "كشف الأستاذ العام"
                canv.drawCentredString(ww / 2, hh - 17.5 * mm, ar(title))

                footer_y = 9 * mm
                canv.setStrokeColor(BORDER)
                canv.setLineWidth(0.5)
                canv.line(14 * mm, footer_y + 6 * mm, ww - 14 * mm, footer_y + 6 * mm)
                canv.setFillColor(DGRAY)
                canv.setFont(base_font, 9)
                canv.drawString(14 * mm, footer_y, ar(f"تاريخ الطباعة: {printed_at}"))
                canv.drawRightString(ww - 14 * mm, footer_y, ar(f"صفحة {doc_.page}"))
                canv.restoreState()

            story = []

            # ========================================================
            # 🌟 إضافة رصيد 2017 إلى الـ Info Table في ملف الـ PDF 🌟
            # ========================================================
            right_lines = [f"حساب الأستاذ العام: {gl_acc_name}", f"الفرع: {branch_name}"]
            left_lines = [f"العملة: {currency_name}", period_text if period_text else "الفترة: غير محددة"]

            # بنجيب رصيد 2017 من الميتا داتا اللي حفظناها ونضيفه كسطر ثالث في اليمين
            if hasattr(self, 'gl_last_meta') and 'balance_2017' in self.gl_last_meta:
                bal_2017 = self.gl_last_meta['balance_2017']
                right_lines.append(f"الرصيد في 31-03-2017: {bal_2017}")
            # ========================================================

            info_tbl = Table([
                [[Paragraph(ar(x), st_right) for x in right_lines], [Paragraph(ar(x), st_left) for x in left_lines]]
            ], colWidths=[116 * mm, 66 * mm])

            info_tbl.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                ("BOX", (0, 0), (-1, -1), 1, GOLD),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, GRID),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]))
            story.append(info_tbl)
            story.append(Spacer(1, 5 * mm))

            # KPIs
            kpis = [
                ("رصيد الافتتاح", fmt2(opening_balance_val)),
                ("إجمالي دائن", fmt2(total_credit)),
                ("إجمالي مدين", fmt2(total_debit)),
                ("الرصيد الختامي", fmt2(closing_balance)),
                ("عدد الحركات", str(trx_count)),
            ]
            kpi_cells = [[Paragraph(ar(l), st_kpi_label), Spacer(1, 1 * mm), Paragraph(ar(v), st_kpi_value)] for l, v in
                         kpis]
            kpi_tbl = Table([kpi_cells], colWidths=[182 * mm / 5.0] * 5)
            kpi_tbl.setStyle(TableStyle([
                ("BOX", (0, 0), (-1, -1), 1, GOLD),
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                ("LINEBEFORE", (1, 0), (4, 0), 0.25, GRID),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("BACKGROUND", (0, 0), (0, 0), OPEN_BG),
                ("BACKGROUND", (3, 0), (3, 0), CLOSE_BG),
            ]))
            story.append(kpi_tbl)
            story.append(Spacer(1, 5 * mm))

            # Table Header
            header = [ar("الرصيد"), ar("دائن"), ar("مدين"), ar("البيان"), ar("التاريخ")]
            table_data = [header]

            for r in rows:
                if len(r) < 8: continue

                raw_date = str(r[0]).strip()
                formatted_date = raw_date.replace(" ", "<br/>")
                date_val = Paragraph(formatted_date, st_center_date)

                desc_val = str(r[4]).strip()
                aseq_val = str(r[8]).strip() if len(r) > 8 else ""

                if aseq_val and aseq_val not in ["None", "", "0"]:
                    desc_ar = ar(desc_val)
                    aseq_ar = ar(f"رقم النمارة: {aseq_val}")
                    final_desc_html = f"{desc_ar}<br/><font color='#5B6770' size='8'>{aseq_ar}</font>"
                else:
                    final_desc_html = ar(desc_val)

                desc_para = Paragraph(final_desc_html, st_right)

                debit_val = str(r[5])
                credit_val = str(r[6])
                bal_val = str(r[7])

                table_data.append([bal_val, credit_val, debit_val, desc_para, date_val])

            main_tbl = Table(table_data, colWidths=[25 * mm, 20 * mm, 20 * mm, 88 * mm, 29 * mm], repeatRows=1)
            main_tbl.setStyle(TableStyle([
                ("FONTNAME", (0, 0), (-1, -1), base_font),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("FONTSIZE", (0, 1), (-1, -1), 9),
                ("BACKGROUND", (0, 0), (-1, 0), GREEN),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("LINEBELOW", (0, 0), (-1, 0), 1.2, GOLD),
                ("GRID", (0, 0), (-1, -1), 0.25, BORDER),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ZEBRA]),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 1), (2, -1), "CENTER"),
                ("ALIGN", (3, 1), (3, -1), "RIGHT"),
                ("RIGHTPADDING", (3, 1), (3, -1), 6),
                ("ALIGN", (4, 1), (4, -1), "CENTER"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            story.append(main_tbl)

            doc.build(story, onFirstPage=draw_header_footer, onLaterPages=draw_header_footer)
            messagebox.showinfo("تم", "تم تصدير PDF بنجاح ✅")
            try:
                os.startfile(file_path)
            except:
                pass

        except Exception as e:
            messagebox.showerror("خطأ", f"حدث خطأ أثناء تصدير PDF:\n{e}")
            if hasattr(self, 'sys_logger'):
                self.sys_logger.log(f"❌ فشل تصدير ملف الأستاذ العام: {e}", "ERROR")

    def gl_search(self):
        """البحث الديناميكي للحركات وتعبئة الشيت بترتيب محاسبي دقيق وأداء صاروخي"""

        gl_acc_name = self.combo_gl_acc.get().strip()
        branch_name = self.combo_gl_branch.get().strip()
        currency_name = self.combo_gl_currency.get().strip()
        date_from = self.ent_gl_date_from.get().strip()
        date_to = self.ent_gl_date_to.get().strip()
        if hasattr(self, 'sys_logger'):
            self.sys_logger.log(
                f"🔎 بدء بحث الأستاذ العام -> الحساب: [{gl_acc_name}] | الفرع: [{branch_name}] | العملة: [{currency_name}] | من: [{date_from}] إلى: [{date_to}]")

        # التأكد من اختيار أستاذ عام
        if not gl_acc_name or "جاري التحميل" in gl_acc_name or "- اختر" in gl_acc_name:
            messagebox.showwarning("تنبيه", "يرجى اختيار أستاذ عام صحيح أولاً.")
            return

        # التأكد من اختيار فرع
        if not branch_name or "جاري التحميل" in branch_name or "- اختر" in branch_name:
            messagebox.showwarning("تنبيه", "يرجى اختيار الفرع أولاً لتحديد جدول البحث.")
            return

        # استخراج اسم الفرع الصافي
        branch_name_only = branch_name.split(" - ")[-1].strip()

        if hasattr(self, "gl_sheet"):
            loading_row = ["", "", "", "⏳ جاري سحب البيانات...", "", "", "", "", ""]
            self.gl_sheet.set_sheet_data([loading_row], reset_col_positions=False, reset_row_positions=True)

        def search_task():
            try:
                engine = self._get_db_connection()

                # 1. تحديد كود العملة (إن وجد)
                target_curr_code = None
                if currency_name and currency_name != "الكل (All)":
                    curr_query = f"SELECT FCUR FROM [dbo].[TBL_Currency] WHERE CNM LIKE N'%{currency_name}%'"
                    curr_df = pd.read_sql(curr_query, engine)
                    if not curr_df.empty:
                        target_curr_code = str(curr_df.iloc[0]['FCUR']).strip()
                    else:
                        alt_curr_name = currency_name.replace('ي', 'ى')
                        curr_query_alt = f"SELECT FCUR FROM [dbo].[TBL_Currency] WHERE CNM LIKE N'%{alt_curr_name}%'"
                        curr_df_alt = pd.read_sql(curr_query_alt, engine)
                        if not curr_df_alt.empty:
                            target_curr_code = str(curr_df_alt.iloc[0]['FCUR']).strip()

                # 2. الاستعلام عن SGL و SSUBB من جدول الأكواد
                codes_query = f"SELECT TOP 1 SGL, SSUBB FROM [dbo].[TBL_GL_Codes] WHERE SNMSUBB = N'{gl_acc_name}'"
                codes_df = pd.read_sql(codes_query, engine)

                if codes_df.empty:
                    self.after(0,
                               lambda: messagebox.showerror("خطأ", "لم يتم العثور على أكواد SGL و SSUBB لهذا الاسم."))
                    self.after(0, lambda: self.gl_sheet.set_sheet_data([[]]))
                    return

                target_sgl = str(codes_df.iloc[0]['SGL']).strip()
                target_ssubb = str(codes_df.iloc[0]['SSUBB']).strip()

                # 3. تحديد اسم الجدول للحركات بناءً على الفرع
                branch_query = f"SELECT GL_TableName FROM [dbo].[TBL_Branches] WHERE BranchName LIKE N'{branch_name_only}'"
                branch_df = pd.read_sql(branch_query, engine)

                if branch_df.empty or pd.isna(branch_df.iloc[0]['GL_TableName']):
                    self.after(0, lambda: messagebox.showerror("خطأ", "لم يتم العثور على جدول (GL_TableName)."))
                    self.after(0, lambda: self.gl_sheet.set_sheet_data([[]]))
                    return
                target_table = branch_df.iloc[0]['GL_TableName'].strip()

                credit_codes = ['1', '4']
                debit_codes = ['2', '3']

                # 4. حساب الرصيد التراكمي السابق (الافتتاحي)
                opening_balance = 0.0
                if date_from:
                    # 📌 أداء: محتاج Index مركّب على جدول الحركة (AGL, ASB, ADATM) — الاستعلام يعيد الشي مش مسح كامل
                    op_query = f"SELECT AAMT, ACOD1 FROM [dbo].[{target_table}] WHERE AGL = '{target_sgl}' AND ASB = '{target_ssubb}' AND ADATM < '{date_from}'"
                    if target_curr_code is not None:
                        op_query += f" AND ACUR = '{target_curr_code}'"

                    op_df = pd.read_sql(op_query, engine)
                    for row in op_df.itertuples(index=False):
                        op_scod = str(row.ACOD1).strip() if pd.notna(row.ACOD1) else ""
                        try:
                            op_amt = abs(float(row.AAMT))
                        except:
                            op_amt = 0.0

                        if op_scod in credit_codes:
                            opening_balance += op_amt
                        elif op_scod in debit_codes:
                            opening_balance -= op_amt
                        else:
                            if float(row.AAMT) > 0:
                                opening_balance += op_amt
                            else:
                                opening_balance -= op_amt

                # =======================================================
                # 🌟 4.5 حساب رصيد 31-03-2017 المخصص (الإضافة الجديدة) 🌟
                # =======================================================
                balance_2017_val = 0.0
                try:
                    bal2017_query = f"SELECT AAMT, ACOD1 FROM [dbo].[{target_table}] WHERE AGL = '{target_sgl}' AND ASB = '{target_ssubb}' AND ADATM <= '20170331'"
                    if target_curr_code is not None:
                        bal2017_query += f" AND ACUR = '{target_curr_code}'"

                    bal2017_df = pd.read_sql(bal2017_query, engine)
                    for row in bal2017_df.itertuples(index=False):
                        t_scod = str(row.ACOD1).strip() if pd.notna(row.ACOD1) else ""
                        try:
                            t_amt = abs(float(row.AAMT))
                        except:
                            t_amt = 0.0

                        if t_scod in credit_codes:
                            balance_2017_val += t_amt
                        elif t_scod in debit_codes:
                            balance_2017_val -= t_amt
                        else:
                            if float(row.AAMT) > 0:
                                balance_2017_val += t_amt
                            else:
                                balance_2017_val -= t_amt
                except Exception as e:
                    if hasattr(self, 'sys_logger'):
                        self.sys_logger.log(f"⚠️ فشل حساب رصيد 2017 للأستاذ العام: {e}", "WARNING")
                # =======================================================

                # 5. جلب حركات الفترة الحالية
                main_query = f"""
                    SELECT ADATM, ABIAN, AAMT, ASEQ, AGL, ASB, ACUR, ACOD1
                    FROM [dbo].[{target_table}] 
                    WHERE AGL = '{target_sgl}' AND ASB = '{target_ssubb}'
                """
                if target_curr_code is not None:
                    main_query += f" AND ACUR = '{target_curr_code}'"
                if date_from:
                    main_query += f" AND ADATM >= '{date_from}'"
                if date_to:
                    main_query += f" AND ADATM <= '{date_to}'"

                main_query += """ 
                    ORDER BY 
                        ADATM ASC,
                        CASE 
                            WHEN ACOD1 IN ('1', '4') THEN 1
                            WHEN ACOD1 IN ('2', '3') THEN 2
                            WHEN AAMT <= 0 THEN 1
                            ELSE 2
                        END ASC,
                        ABS(AAMT) ASC
                """

                results_df = pd.read_sql(main_query, engine)

                if hasattr(self, 'sys_logger'):
                    self.sys_logger.log(f"تم سحب {len(results_df)} حركة.")

                formatted_data = []
                running_balance = opening_balance

                for row in results_df.itertuples(index=False):
                    date_val = str(row.ADATM) if pd.notna(row.ADATM) else ""
                    desc = str(row.ABIAN) if pd.notna(row.ABIAN) else ""
                    scod1_val = str(row.ACOD1).strip() if pd.notna(row.ACOD1) else ""
                    full_acc_number = f"{str(row.AGL)}-{str(row.ASB)}"
                    aseq_val = str(row.ASEQ).strip() if pd.notna(row.ASEQ) else ""
                    try:
                        raw_amt = float(row.AAMT)
                        amt = abs(raw_amt)
                    except:
                        raw_amt = 0.0
                        amt = 0.0

                    debit = 0.0
                    credit = 0.0

                    if scod1_val in credit_codes:
                        credit = amt
                        running_balance += amt
                    elif scod1_val in debit_codes:
                        debit = amt
                        running_balance -= amt
                    else:
                        if raw_amt > 0:
                            debit = amt
                            running_balance += amt
                        else:
                            credit = amt
                            running_balance -= amt

                    formatted_data.append([
                        date_val,
                        branch_name_only,
                        full_acc_number,
                        currency_name if currency_name != "الكل (All)" else str(row.ACUR),
                        desc,
                        f"{debit:,.2f}" if debit > 0 else "0.00",
                        f"{credit:,.2f}" if credit > 0 else "0.00",
                        f"{running_balance:,.2f}",
                        aseq_val
                    ])

                if not formatted_data:
                    formatted_data = [["", "", "", "لا توجد حركات مطابقة لشروط البحث", "", "", "", "", ""]]

                # عرض البيانات في الشيت
                self.after(0, lambda: self.gl_sheet.set_sheet_data(formatted_data, reset_col_positions=False,
                                                                   reset_row_positions=True))

                # 🌟 تحديث واجهة المستخدم برصيد 2017 اللي ضفناه في الخطوة السابقة 🌟
                if hasattr(self, 'lbl_gl_balance_2017'):
                    self.after(0, lambda: self.lbl_gl_balance_2017.configure(
                        text=f"الرصيد في 31-03-2017: {balance_2017_val:,.2f}"))

                # 🌟 حفظ البيانات الخاصة بالتصدير للـ PDF (Meta Data) 🌟
                self.gl_last_meta = {
                    "gl_acc_name": gl_acc_name,
                    "branch_name": branch_name,
                    "currency": currency_name,
                    "date_from": date_from,
                    "date_to": date_to,
                    "opening_balance": f"{opening_balance:,.2f}",
                    "balance_2017": f"{balance_2017_val:,.2f}"
                }

                if hasattr(self, 'sys_logger'):
                    self.sys_logger.log("✅ تم سحب وعرض بيانات الأستاذ العام بنجاح.")

            except Exception as e:
                if hasattr(self, 'sys_logger'):
                    self.sys_logger.log(f"❌ خطأ أثناء البحث: {e}", "ERROR")
                self.after(0, lambda: messagebox.showerror("خطأ برمجي", f"حدث خطأ أثناء جلب البيانات:\n{e}"))
                self.after(0, lambda: self.gl_sheet.set_sheet_data([["", "", "", "❌ حدث خطأ", "", "", "", "", ""]]))

        threading.Thread(target=search_task, daemon=True).start()

    def on_show(self):
        """نفس سلوك show_page القديم: أكواد + فروع + عملات."""
        self.gl_load_codes()
        if self.app is not None:
            self.app.nuwairy_load_branches()
        self.gl_load_currencies()
