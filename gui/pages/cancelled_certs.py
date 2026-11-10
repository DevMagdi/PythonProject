# -*- coding: utf-8 -*-
"""
شاشة الشهادات الملغاة برقم العميل.

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


class CancelledCertsPage(LegacyInquiryPage):
    """شاشة الشهادات الملغاة برقم العميل."""
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
        CANCEL_COLOR = "#DC2626"  # لون أحمر مميز للشهادات الملغاة

        # حاوية الشاشة الرئيسية
        main_container = ctk.CTkFrame(parent, fg_color=BG_MAIN)
        main_container.pack(fill="both", expand=True)

        # الهيدر العلوي
        header = ctk.CTkFrame(main_container, fg_color=FIB_GREEN, height=65, corner_radius=0)
        header.pack(fill="x")
        header.pack_propagate(False)

        ctk.CTkFrame(main_container, fg_color=FIB_GOLD, height=4, corner_radius=0).pack(fill="x")

        title_lbl = ctk.CTkLabel(header, text="استعلام الشهادات الملغاة برقم العميل", font=("Segoe UI", 22, "bold"),
                                 text_color=CARD_BG)
        title_lbl.pack(side="right", padx=30, pady=15)

        # =========================================
        # 🔍 2. Search Area (الفرع ورقم العميل)
        # =========================================
        search_frame = ctk.CTkFrame(main_container, fg_color=CARD_BG, corner_radius=15, border_width=1,
                                    border_color="#E2E8F0")
        search_frame.pack(fill="x", padx=20, pady=20)

        search_inner = ctk.CTkFrame(search_frame, fg_color="transparent")
        search_inner.pack(side="right", fill="y", padx=20, pady=15)

        # --- زر البحث ---
        btn_search = ctk.CTkButton(search_inner, text="🔍 بحث", font=("Segoe UI", 15, "bold"),
                                   fg_color=FIB_GREEN, hover_color="#004426", text_color="white",
                                   width=120, height=40, corner_radius=8, command=lambda: execute_search())
        btn_search.pack(side="left", padx=10)

        # --- رقم العميل ---
        self.ent_canc_cust_no = ctk.CTkEntry(search_inner, font=("Segoe UI", 15, "bold"),
                                             justify="center", placeholder_text="رقم العميل...",
                                             width=200, height=40, border_color="#CBD5E1")
        self.ent_canc_cust_no.pack(side="left", padx=10)

        ctk.CTkLabel(search_inner, text="رقم العميل:", font=("Segoe UI", 14, "bold"), text_color=TEXT_DARK).pack(
            side="left", padx=(10, 2))

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
            self.cmb_canc_branch = ctk.CTkComboBox(search_inner, font=("Segoe UI", 14, "bold"), justify="right",
                                                   width=250, height=40, border_color="#CBD5E1")
            self.cmb_canc_branch.pack(side="left", padx=10)

        ctk.CTkLabel(search_inner, text="الفرع:", font=("Segoe UI", 14, "bold"), text_color=TEXT_DARK).pack(side="left",
                                                                                                            padx=(10,
                                                                                                                  2))

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

        # ربط زر الـ Enter بالبحث
        self.ent_canc_cust_no.bind("<Return>", lambda event: execute_search())

        # =========================================
        # 📜 3. Results Area (كروت الشهادات)
        # =========================================
        self.canc_results_scroll = ctk.CTkScrollableFrame(main_container, fg_color="transparent")
        self.canc_results_scroll.pack(fill="both", expand=True, padx=15, pady=(0, 20))

        def fix_arabic_name(raw_name):
            if pd.isna(raw_name) or not str(raw_name).strip():
                return "غير مسجل"
            text = str(raw_name).strip()
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

        # =========================================
        # ⚙️ 4. Search Engine Logic
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

            # 1. الحصول على اسم الجدول وكود الفرع من المابنج بناءً على الشرح المطلوب
            branch_info = self.branch_mapping[branch_name]

            # دعم لو الـ branch_info عبارة عن tuple (كود الفرع, اسم الجدول) أو كود فقط
            if isinstance(branch_info, tuple):
                branch_code, target_table = branch_info
            else:
                branch_code = branch_info
                target_table = None

            # لو الجدول مش موجود في المابنج، نجيبه من جدول الفروع بالداتابيز كاحتياط
            for widget in self.canc_results_scroll.winfo_children():
                widget.destroy()

            lbl_loading = ctk.CTkLabel(self.canc_results_scroll, text="⚡ جاري البحث عن الشهادات الملغاة...",
                                       font=("Segoe UI", 16, "bold"), text_color=FIB_GOLD)
            lbl_loading.pack(pady=50)

            def fetch_data():
                try:
                    engine = getattr(self, '_get_db_connection', lambda: None)()
                    if not engine:
                        raise Exception("لم يتم العثور على دالة الاتصال بقاعدة البيانات.")

                    # بما أننا لدينا كود الفرع بالفعل (branch_code)،
                    # نحتاج فقط لمعرفة اسم الجدول الخاص بهذا الفرع من الـ branch_mapping أو جدول الفروع بطريقة صحيحة:

                    # يمكنك جلب اسم الجدول مباشرة بالبحث عن الفرع في جدول الفروع باستخدام كود الفرع (إذا كان العمود اسمه مثلاً BranchCode أو رقم الفرع)
                    branch_query = f"SELECT * FROM [dbo].[TBL_Branches] WHERE BranchCode = N'{branch_code}'"
                    branch_df = pd.read_sql(branch_query, engine)

                    if branch_df.empty:
                        raise Exception("لم يتم العثور على جدول هذا الفرع في قاعدة البيانات.")

                    # جلب اسم الجدول الفعلي من العمود المخصص (مثل GL_TableName أو TableName)
                    target_table = branch_df.iloc[0].get('GL_TableName') or branch_df.iloc[0].get('TableName')

                    if not target_table or pd.isna(target_table):
                        raise Exception("اسم الجدول الخاص بالفرع غير معرف في قاعدة البيانات.")

                    target_table = str(target_table).strip()

                    # الكويري المباشر للشهادات الملغاة باستخدام الجدول الخاص بالفرع وكود الفرع صحيحاً
                    sql = f"""
                        SELECT CCER, CNO, CAMT, CDAT1, CNAME, CDAT10
                        FROM [dbo].[{target_table}] WITH (NOLOCK)
                        WHERE CBR = N'{branch_code}' 
                          AND CCLNT = N'{cust_no}'
                          AND CDAT10 IS NOT NULL 
                          AND LTRIM(RTRIM(CDAT10)) <> ''
                          AND LTRIM(RTRIM(CDAT10)) <> '0'
                    """
                    df = pd.read_sql(sql, engine)

                    self.after(0, lambda: update_results_ui(df))
                except Exception as e:
                    logging.error(f"Error fetching cancelled certificates: {e}")
                    self.after(0, lambda: update_results_ui(pd.DataFrame(), error=str(e)))

            threading.Thread(target=fetch_data, daemon=True).start()

        def update_results_ui(df, error=None):
            for widget in self.canc_results_scroll.winfo_children():
                widget.destroy()

            if error:
                ctk.CTkLabel(self.canc_results_scroll, text=f"❌ حدث خطأ أثناء البحث:\n{error}",
                             font=("Segoe UI", 14, "bold"), text_color="#EF4444").pack(pady=40)
                return

            if df.empty:
                ctk.CTkLabel(self.canc_results_scroll, text="🔍 لا توجد شهادات ملغاة لهذا العميل في هذا الفرع",
                             font=("Segoe UI", 18, "bold"), text_color=TEXT_MUTED).pack(pady=60)
                return

            # إنشاء كارت مخصص لكل شهادة ملغاة
            for _, row in df.iterrows():
                ccer_val = str(row['CCER']).replace('.0', '') if pd.notna(row['CCER']) else "غير معروف"
                cno_val = str(row['CNO']).replace('.0', '') if pd.notna(row['CNO']) else "—"

                try:
                    camt_val = f"{float(row['CAMT']):,.2f}"
                except:
                    camt_val = "0.00"

                cust_name = fix_arabic_name(row['CNAME']) if pd.notna(row['CNAME']) else "غير مسجل"
                cdat1_val = str(row['CDAT1']).split()[0] if pd.notna(row['CDAT1']) and str(
                    row['CDAT1']).strip() else "—"
                cdat10_val = str(row['CDAT10']).split()[0] if pd.notna(row['CDAT10']) and str(
                    row['CDAT10']).strip() else "—"

                card = ctk.CTkFrame(self.canc_results_scroll, fg_color=CARD_BG, corner_radius=12,
                                    border_width=1, border_color="#E2E8F0")
                card.pack(fill="x", padx=10, pady=8)

                ctk.CTkFrame(card, fg_color=CANCEL_COLOR, width=5, corner_radius=0).pack(side="right", fill="y",
                                                                                         pady=10)

                card_content = ctk.CTkFrame(card, fg_color="transparent")
                card_content.pack(fill="both", expand=True, padx=20, pady=15)

                # صف العنوان (رقم الشهادة وقيمة الشهادة)
                header_row = ctk.CTkFrame(card_content, fg_color="transparent")
                header_row.pack(fill="x", pady=(0, 5))

                ctk.CTkLabel(header_row, text=f"شهادة رقم : {ccer_val} 📜", font=("Segoe UI", 18, "bold"),
                             text_color=FIB_GREEN).pack(side="right")
                ctk.CTkLabel(header_row, text=f"القيمة: {camt_val} 💰", font=("Segoe UI", 15, "bold"),
                             text_color=FIB_GOLD).pack(side="left")

                # صف اسم العميل ورقم أمر الشراء
                info_row = ctk.CTkFrame(card_content, fg_color="transparent")
                info_row.pack(fill="x", pady=(0, 10))
                ctk.CTkLabel(info_row, text=f"العميل: {cust_name} 👤", font=("Segoe UI", 15, "bold"),
                             text_color=TEXT_MUTED).pack(side="right")
                ctk.CTkLabel(info_row, text=f"رقم أمر الشراء: {cno_val}", font=("Segoe UI", 13, "bold"),
                             text_color=TEXT_MUTED).pack(side="left")

                # خط فاصل
                ctk.CTkFrame(card_content, fg_color="#F1F5F9", height=2).pack(fill="x", pady=5)

                # صف التواريخ (تاريخ الشراء وتاريخ الإلغاء)
                data_grid = ctk.CTkFrame(card_content, fg_color="transparent")
                data_grid.pack(fill="x", pady=10)
                data_grid.grid_columnconfigure((0, 1), weight=1)

                def create_info_box(parent, row_idx, col_idx, title, value, val_color=TEXT_DARK):
                    box = ctk.CTkFrame(parent, fg_color=BOX_BG, corner_radius=8)
                    box.grid(row=row_idx, column=col_idx, padx=5, pady=5, sticky="ew")
                    ctk.CTkLabel(box, text=title, font=("Segoe UI", 12, "bold"), text_color=TEXT_MUTED).pack(
                        anchor="center", pady=(5, 0))
                    ctk.CTkLabel(box, text=value, font=("Segoe UI", 15, "bold"), text_color=val_color).pack(
                        anchor="center", pady=(0, 5))

                create_info_box(data_grid, 0, 1, "تاريخ الشراء", cdat1_val, val_color=FIB_GREEN)
                create_info_box(data_grid, 0, 0, "تاريخ الإلغاء", cdat10_val, val_color=CANCEL_COLOR)
