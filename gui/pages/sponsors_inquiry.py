# -*- coding: utf-8 -*-
"""
شاشة الاستفسار عن الكفلاء.

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


class SponsorsInquiryPage(LegacyInquiryPage):
    """شاشة الاستفسار عن الكفلاء."""
    LOAD_BRANCHES_ON_SHOW = True

    def build(self):
        """بناء الشاشة — الكود القديم كما هو (parent = الشاشة نفسها)."""
        parent = self

        # =========================================
        # 🎨 1. Theme Colors
        # =========================================
        FIB_GREEN = "#005C34"
        FIB_GOLD = "#C5A059"
        BG_MAIN = "#F8FAFC"
        CARD_BG = "#FFFFFF"
        BOX_BG = "#F1F5F9"
        TEXT_DARK = "#0F172A"
        TEXT_MUTED = "#64748B"

        # حاويات الشاشة
        main_container = ctk.CTkFrame(parent, fg_color=BG_MAIN)
        main_container.pack(fill="both", expand=True)

        header = ctk.CTkFrame(main_container, fg_color=FIB_GREEN, height=65, corner_radius=0)
        header.pack(fill="x")
        header.pack_propagate(False)

        ctk.CTkFrame(main_container, fg_color=FIB_GOLD, height=4, corner_radius=0).pack(fill="x")

        ctk.CTkLabel(
            header, text="الاستفسار عن الكفلاء 🤝",
            font=("Segoe UI", 22, "bold"), text_color=CARD_BG
        ).pack(side="right", padx=30, pady=15)

        # =========================================
        # 🔍 2. Search Area
        # =========================================
        search_frame = ctk.CTkFrame(main_container, fg_color=CARD_BG, corner_radius=15, border_width=1,
                                    border_color="#E2E8F0")
        search_frame.pack(fill="x", padx=20, pady=15)

        search_inner = ctk.CTkFrame(search_frame, fg_color="transparent")
        search_inner.pack(side="right", fill="y", padx=20, pady=15)

        # أزرار البحث والمسح
        btn_clear = ctk.CTkButton(search_inner, text="🧹 مسح", font=("Segoe UI", 14, "bold"), fg_color="#64748B",
                                  hover_color="#475569", width=90, height=40, corner_radius=8,
                                  command=lambda: clear_search())
        btn_clear.pack(side="left", padx=(5, 10))

        btn_search = ctk.CTkButton(search_inner, text="🔍 بحث", font=("Segoe UI", 15, "bold"), fg_color=FIB_GREEN,
                                   hover_color="#004426", width=110, height=40, corner_radius=8,
                                   command=lambda: execute_search())
        btn_search.pack(side="left", padx=5)

        # اختيار العملة
        self.cmb_sponsor_currency = ctk.CTkComboBox(search_inner, font=("Segoe UI", 14, "bold"), justify="right",
                                                    width=150, height=40, border_color="#CBD5E1",
                                                    values=["جاري التحميل..."])
        self.cmb_sponsor_currency.pack(side="left", padx=10)
        ctk.CTkLabel(search_inner, text="العملة:", font=("Segoe UI", 14, "bold"), text_color=TEXT_DARK).pack(
            side="left", padx=(10, 2))

        # إدخال رقم العميل
        self.ent_sponsor_cust_no = ctk.CTkEntry(search_inner, font=("Segoe UI", 15, "bold"), justify="center",
                                                placeholder_text="رقم الحساب/العميل...", width=160, height=40,
                                                border_color="#CBD5E1")
        self.ent_sponsor_cust_no.pack(side="left", padx=10)
        ctk.CTkLabel(search_inner, text="رقم الحساب:", font=("Segoe UI", 14, "bold"), text_color=TEXT_DARK).pack(
            side="left", padx=(10, 2))

        # اختيار الفرع
        if hasattr(self, '_create_premium_select'):
            self.cmb_sponsor_branch_box, self.cmb_sponsor_branch = self._create_premium_select(search_inner, values=[
                "جاري التحميل..."], default="جاري التحميل...", title="اختر الفرع")
            self.cmb_sponsor_branch_box.pack(side="left", padx=10)
        else:
            self.cmb_sponsor_branch = ctk.CTkComboBox(search_inner, font=("Segoe UI", 14, "bold"), justify="right",
                                                      width=200, height=40, border_color="#CBD5E1")
            self.cmb_sponsor_branch.pack(side="left", padx=10)
        ctk.CTkLabel(search_inner, text="الفرع:", font=("Segoe UI", 14, "bold"), text_color=TEXT_DARK).pack(side="left",
                                                                                                            padx=(10,
                                                                                                                  2))

        self.sponsor_summary_lbl = ctk.CTkLabel(main_container, text="", font=("Segoe UI", 13, "bold"),
                                                text_color=TEXT_MUTED)
        self.sponsor_summary_lbl.pack(anchor="e", padx=25, pady=(0, 5))

        self.sponsor_results_scroll = ctk.CTkScrollableFrame(main_container, fg_color="transparent")
        self.sponsor_results_scroll.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        # =========================================
        # ⚙️ 3. Initialization & Helpers
        # =========================================
        self.currency_dict_name_to_code = {}  # { "جنيه مصري": "0", "دولار": "1" }

        def load_initial_data():
            # 1. تحميل الفروع
            if hasattr(self, 'branch_mapping') and self.branch_mapping:
                branches = list(self.branch_mapping.keys())
                self.cmb_sponsor_branch.configure(values=branches)
                self.cmb_sponsor_branch.set(branches[0])
            else:
                if hasattr(self, 'nuwairy_load_branches'):
                    self.nuwairy_load_branches()
                self.after(500, load_initial_data)
                return  # استنى الفروع تحمل الأول

            # 2. تحميل العملات من قاعدة البيانات (Thread)
            def fetch_currencies():
                try:
                    engine = getattr(self, '_get_db_connection', lambda: None)()
                    if engine:
                        sql = "SELECT fcur, cnm FROM [dbo].[tbl_currency] WITH (NOLOCK) WHERE cnm IS NOT NULL"
                        df = pd.read_sql(sql, engine)
                        curr_list = []
                        self.currency_dict_name_to_code.clear()

                        for _, row in df.iterrows():
                            c_code = str(row['fcur']).strip()
                            c_name = str(row['cnm']).strip()
                            if c_name:
                                curr_list.append(c_name)
                                self.currency_dict_name_to_code[c_name] = c_code

                        if curr_list:
                            self.after(0, lambda: [
                                self.cmb_sponsor_currency.configure(values=curr_list),
                                self.cmb_sponsor_currency.set(curr_list[0])
                            ])
                except Exception as e:
                    logging.error(f"Error loading currencies: {e}")

            threading.Thread(target=fetch_currencies, daemon=True).start()

        load_initial_data()
        self.ent_sponsor_cust_no.bind("<Return>", lambda event: execute_search())

        def clear_search():
            self.ent_sponsor_cust_no.delete(0, 'end')
            self.sponsor_summary_lbl.configure(text="")
            for widget in self.sponsor_results_scroll.winfo_children():
                widget.destroy()

        # دالة تنظيف الأسماء (تم إزالة الريجيكس اللي كان بيفصل الحروف)
        def clean_arabic_name(name):
            if not isinstance(name, str) or not name.strip():
                return "—"

            cleaned = name.strip()

            # 1. تنظيف الرموز والمسافات الزائدة
            cleaned = re.sub(r'[_+\-]', ' ', cleaned)
            cleaned = re.sub(r'\s+', ' ', cleaned)

            # 2. فصل البادئات الشهيرة في الأسماء (ابن / عبد / ابو / ام)
            # مثال: ابنعمر -> ابن عمر | ابنسالم -> ابن سالم | عبدالله -> عبد الله
            cleaned = re.sub(r'(\bابن|\bعبد|\bابو|\bأبو|\bام|\bأم)([أ-ي])', r'\1 \2', cleaned)

            # 3. فصل الكلمات الملتصقة بعد التاء المربوطة أو الهاء (خاص بأسماء الشركات)
            # مثال: السعوديهتراست -> السعوديه تراست
            cleaned = re.sub(r'([ةه])([أ-ي])', r'\1 \2', cleaned)

            # 4. فصل الكلمات التجارية والخدمية الشهيرة الملتصقة (زي: للسياحة، للمقاولات، تراست... إلخ)
            # مثال: تراستللسياحه -> تراست للسياحه
            cleaned = re.sub(r'([أ-ي])(للسياح|للتجار|للمقاول|للاستثمار|للخدمات|للتأمين|تراست|جروب|كومباني)', r'\1 \2',
                             cleaned)

            # 5. إعادة إزالة أي مسافات مضاعفة نتجت عن الفصل
            return re.sub(r'\s+', ' ', cleaned).strip()

        # =========================================
        # 🚀 4. Execute Search & DB Logic
        # =========================================
        def execute_search():
            branch_name = self.cmb_sponsor_branch.get().strip()
            cust_no = self.ent_sponsor_cust_no.get().strip()
            curr_name = self.cmb_sponsor_currency.get().strip()

            if not cust_no:
                messagebox.showwarning("تنبيه", "يرجى إدخال رقم الحساب/العميل أولاً")
                self.ent_sponsor_cust_no.focus()
                return

            if not hasattr(self, 'branch_mapping') or branch_name not in self.branch_mapping:
                messagebox.showerror("خطأ", "برجاء اختيار فرع صحيح")
                return

            # استخراج الأكواد من القواميس
            branch_info = self.branch_mapping[branch_name]
            branch_code = branch_info[0] if isinstance(branch_info, tuple) else branch_info

            # لو العملة مالهاش كود في القاموس، هنعتبر الكود هو الصفر كافتراضي
            curr_code = self.currency_dict_name_to_code.get(curr_name, "0")

            # تفريغ الشاشة وتحميل
            for widget in self.sponsor_results_scroll.winfo_children():
                widget.destroy()

            self.sponsor_summary_lbl.configure(text="")
            ctk.CTkLabel(self.sponsor_results_scroll, text="⚡ جاري الاستعلام عن الكفلاء...",
                         font=("Segoe UI", 16, "bold"), text_color=FIB_GOLD).pack(pady=50)

            def fetch_data():
                try:
                    engine = getattr(self, '_get_db_connection', lambda: None)()
                    if not engine:
                        raise Exception("لم يتم العثور على دالة الاتصال بقاعدة البيانات.")

                    # تجهيز الرقم لضمان تطابق الـ Index (نفس فكرة الشاشة السابقة)
                    cust_str = cust_no.strip()
                    try:
                        cust_int_str = str(int(cust_str))
                    except:
                        cust_int_str = cust_str

                    # 1. جلب اسم الجدول للفرع من TBL_Branches
                    target_table = None
                    try:
                        branch_query = f"SELECT TableName FROM [dbo].[TBL_Branches] WITH (NOLOCK) WHERE BranchCode = '{branch_code}'"
                        branch_df = pd.read_sql(branch_query, engine)
                        if not branch_df.empty and pd.notna(branch_df.iloc[0]['TableName']):
                            target_table = str(branch_df.iloc[0]['TableName']).strip()
                    except Exception as b_err:
                        logging.error(f"Error fetching TableName: {b_err}")

                    # 2. جلب اسم العميل (Bname) من جدول الفرع
                    fetched_client_name = "غير مسجل"
                    if target_table:
                        try:
                            client_query = f"""
                                SELECT TOP 1 BNAME 
                                FROM [dbo].[{target_table}] WITH (NOLOCK) 
                                WHERE BCLNT = '{cust_str}' OR BCLNT = '{cust_int_str}'
                            """
                            client_df = pd.read_sql(client_query, engine)
                            # التعديل هنا: تمرير اسم العميل لدالة التنظيف
                            if not client_df.empty and pd.notna(client_df.iloc[0].get('BNAME')):
                                raw_client_name = str(client_df.iloc[0].get('BNAME')).strip()
                                fetched_client_name = clean_arabic_name(raw_client_name)
                        except Exception as cl_err:
                            logging.warning(f"Could not fetch client name: {cl_err}")

                    # 3. جلب الكفلاء من tbl_sponsers (بناءً على fbr, fclnt, fcur) باستخدام الـ Index السريع
                    sql_sponsors = f"""
                        SELECT fclntk, fclntm, fnam
                        FROM [dbo].[tbl_sponsers] WITH (NOLOCK)
                        WHERE fbr = '{branch_code}'
                          AND fcur = '{curr_code}'
                          AND (fclnt = '{cust_str}' OR fclnt = '{cust_int_str}')
                    """
                    df_sponsors = pd.read_sql(sql_sponsors, engine)

                    self.after(0, lambda: update_results_ui(df_sponsors, fetched_client_name, cust_no, branch_name,
                                                            curr_name))
                except Exception as e:
                    logging.error(f"Error fetching sponsors: {e}")
                    self.after(0, lambda: update_results_ui(pd.DataFrame(), "غير مسجل", cust_no, branch_name, curr_name,
                                                            error=str(e)))

            threading.Thread(target=fetch_data, daemon=True).start()

        # =========================================
        # 📑 5. Update Results UI
        # =========================================
        def update_results_ui(df, client_name, cust_no, branch_name, curr_name, error=None):
            for widget in self.sponsor_results_scroll.winfo_children():
                widget.destroy()

            if error:
                self.sponsor_summary_lbl.configure(text="")
                ctk.CTkLabel(self.sponsor_results_scroll, text=f"❌ حدث خطأ:\n{error}", font=("Segoe UI", 14, "bold"),
                             text_color="#EF4444").pack(pady=40)
                return

            if df.empty:
                self.sponsor_summary_lbl.configure(text="")
                ctk.CTkLabel(self.sponsor_results_scroll, text="🔍 لا يوجد كفلاء مسجلين لهذا الحساب بهذه العملة",
                             font=("Segoe UI", 18, "bold"), text_color=TEXT_MUTED).pack(pady=60)
                return

            self.sponsor_summary_lbl.configure(text=f"إجمالي عدد الكفلاء: {len(df)}")

            # --- كارت بيانات العميل الرئيسي ---
            client_card = ctk.CTkFrame(self.sponsor_results_scroll, fg_color=CARD_BG, corner_radius=12, border_width=1,
                                       border_color="#CBD5E1")
            client_card.pack(fill="x", padx=10, pady=(5, 15))

            client_inner = ctk.CTkFrame(client_card, fg_color="transparent")
            client_inner.pack(fill="x", padx=20, pady=12)

            ctk.CTkLabel(client_inner, text=f"👤 اسم العميل المقترض: {client_name}", font=("Segoe UI", 16, "bold"),
                         text_color=FIB_GREEN).pack(side="right")

            info_frame = ctk.CTkFrame(client_inner, fg_color="transparent")
            info_frame.pack(side="left")
            ctk.CTkLabel(info_frame, text=f"العملة: {curr_name}", font=("Segoe UI", 13, "bold"), text_color="#FFFFFF",
                         fg_color=FIB_GOLD, corner_radius=6).pack(side="right", padx=5, ipadx=10, ipady=3)
            ctk.CTkLabel(info_frame, text=f"الفرع: {branch_name} | الحساب: {cust_no}", font=("Segoe UI", 13, "bold"),
                         text_color=TEXT_MUTED, fg_color=BOX_BG, corner_radius=6).pack(side="right", ipadx=10, ipady=3)

            # --- رندر كروت الكفلاء ---
            for index, row in df.iterrows():
                # تنظيف اسم الكفيل باستخدام الريجيكس
                raw_name = str(row.get('fnam', '—'))
                clean_name = clean_arabic_name(raw_name)

                card = ctk.CTkFrame(self.sponsor_results_scroll, fg_color=CARD_BG, corner_radius=12, border_width=1,
                                    border_color="#E2E8F0")
                card.pack(fill="x", padx=10, pady=8)

                # شريط جانبي
                ctk.CTkFrame(card, fg_color="#334155", width=6, corner_radius=0).pack(side="right", fill="y", pady=10)

                card_content = ctk.CTkFrame(card, fg_color="transparent")
                card_content.pack(fill="both", expand=True, padx=20, pady=15)

                # اسم الكفيل
                ctk.CTkLabel(card_content, text=f"كفيل رقم ({index + 1})", font=("Segoe UI", 12, "bold"),
                             text_color=TEXT_MUTED).pack(anchor="e", pady=(0, 2))
                ctk.CTkLabel(card_content, text=clean_name, font=("Segoe UI", 18, "bold"), text_color=TEXT_DARK).pack(
                    anchor="e", pady=(0, 10))

                # خط فاصل
                ctk.CTkFrame(card_content, fg_color="#F1F5F9", height=2).pack(fill="x", pady=6)

                # أرقام الكفيل
                nums_frame = ctk.CTkFrame(card_content, fg_color="transparent")
                nums_frame.pack(fill="x", pady=(5, 0))

                # رقم الكفيل العادي
                box1 = ctk.CTkFrame(nums_frame, fg_color=BOX_BG, corner_radius=8)
                box1.pack(side="right", fill="x", expand=True, padx=(0, 5))
                ctk.CTkLabel(box1, text="رقم الكفيل (الفرع)", font=("Segoe UI", 12, "bold"),
                             text_color=TEXT_MUTED).pack(anchor="center", pady=(6, 2))
                ctk.CTkLabel(box1, text=row.get('fclntk', '—'), font=("Segoe UI", 16, "bold"),
                             text_color=FIB_GREEN).pack(anchor="center", pady=(0, 6))

                # رقم الكفيل المركزي
                box2 = ctk.CTkFrame(nums_frame, fg_color=BOX_BG, corner_radius=8)
                box2.pack(side="left", fill="x", expand=True, padx=(5, 0))
                ctk.CTkLabel(box2, text="رقم الكفيل (المركزي)", font=("Segoe UI", 12, "bold"),
                             text_color=TEXT_MUTED).pack(anchor="center", pady=(6, 2))
                ctk.CTkLabel(box2, text=row.get('fclntm', '—'), font=("Segoe UI", 16, "bold"),
                             text_color=FIB_GOLD).pack(anchor="center", pady=(0, 6))
