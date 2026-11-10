# -*- coding: utf-8 -*-
"""
شاشة الاستفسار عن عملاء الجدارة الائتمانية.

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


class CreditworthinessInquiryPage(LegacyInquiryPage):
    """شاشة الاستفسار عن عملاء الجدارة الائتمانية."""
    LOAD_BRANCHES_ON_SHOW = True

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
            header, text="الاستفسار عن عملاء الجدارة الائتمانية 🛡️",
            font=("Segoe UI", 22, "bold"), text_color=CARD_BG
        ).pack(side="right", padx=30, pady=15)

        # =========================================
        # 🔍 منطقة البحث (الفرع، رقم العميل، رقم المركزي)
        # =========================================
        search_frame = ctk.CTkFrame(main_container, fg_color=CARD_BG, corner_radius=15, border_width=1,
                                    border_color="#E2E8F0")
        search_frame.pack(fill="x", padx=20, pady=15)

        search_inner = ctk.CTkFrame(search_frame, fg_color="transparent")
        search_inner.pack(side="right", fill="y", padx=20, pady=15)

        # الأزرار
        btn_clear = ctk.CTkButton(search_inner, text="🧹 مسح", font=("Segoe UI", 14, "bold"), fg_color="#64748B",
                                  hover_color="#475569", width=80, height=40, corner_radius=8,
                                  command=lambda: clear_search())
        btn_clear.pack(side="left", padx=(5, 10))

        btn_search = ctk.CTkButton(search_inner, text="🔍 بحث", font=("Segoe UI", 15, "bold"), fg_color=FIB_GREEN,
                                   hover_color="#004426", width=100, height=40, corner_radius=8,
                                   command=lambda: execute_search())
        btn_search.pack(side="left", padx=5)

        # رقم العميل بالمركزي
        self.ent_credit_cclntm = ctk.CTkEntry(search_inner, font=("Segoe UI", 15, "bold"), justify="center",
                                              placeholder_text="العميل بالمركزي...", width=140, height=40,
                                              border_color="#CBD5E1")
        self.ent_credit_cclntm.pack(side="left", padx=10)
        ctk.CTkLabel(search_inner, text="رقم المركزي:", font=("Segoe UI", 14, "bold"), text_color=TEXT_DARK).pack(
            side="left", padx=(10, 2))

        # رقم العميل
        self.ent_credit_cust_no = ctk.CTkEntry(search_inner, font=("Segoe UI", 15, "bold"), justify="center",
                                               placeholder_text="رقم العميل...", width=130, height=40,
                                               border_color="#CBD5E1")
        self.ent_credit_cust_no.pack(side="left", padx=10)
        ctk.CTkLabel(search_inner, text="رقم العميل:", font=("Segoe UI", 14, "bold"), text_color=TEXT_DARK).pack(
            side="left", padx=(10, 2))

        # الفرع
        if hasattr(self, '_create_premium_select'):
            self.cmb_credit_branch_box, self.cmb_credit_branch = self._create_premium_select(search_inner,
                                                                                             values=["جاري التحميل..."],
                                                                                             default="جاري التحميل...",
                                                                                             title="اختر الفرع")
            self.cmb_credit_branch_box.pack(side="left", padx=10)
        else:
            self.cmb_credit_branch = ctk.CTkComboBox(search_inner, font=("Segoe UI", 14, "bold"), justify="right",
                                                     width=200, height=40, border_color="#CBD5E1")
            self.cmb_credit_branch.pack(side="left", padx=10)
        ctk.CTkLabel(search_inner, text="الفرع:", font=("Segoe UI", 14, "bold"), text_color=TEXT_DARK).pack(side="left",
                                                                                                            padx=(10,
                                                                                                                  2))

        # فريم نتائج البحث
        self.credit_results_scroll = ctk.CTkScrollableFrame(main_container, fg_color="transparent")
        self.credit_results_scroll.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        # =========================================
        # ⚙️ تحميل الفروع وإعداد الأحداث
        # =========================================
        def load_initial_data():
            if hasattr(self, 'branch_mapping') and self.branch_mapping:
                branches = list(self.branch_mapping.keys())
                self.cmb_credit_branch.configure(values=branches)
                self.cmb_credit_branch.set(branches[0])
            else:
                self.after(500, load_initial_data)

        self.after(500, load_initial_data)
        self.ent_credit_cust_no.bind("<Return>", lambda event: execute_search())
        self.ent_credit_cclntm.bind("<Return>", lambda event: execute_search())

        def clear_search():
            self.ent_credit_cust_no.delete(0, 'end')
            self.ent_credit_cclntm.delete(0, 'end')
            for widget in self.credit_results_scroll.winfo_children():
                widget.destroy()

        # =========================================
        # 🛠️ معالجة الاسم العربي الملتصق
        # =========================================
        def format_arabic_name(raw_name):
            if not raw_name or pd.isna(raw_name):
                return "غير مسجل"
            text = str(raw_name).strip()

            # إضافة مسافات إضافية بين مقاطع الكلمات الملتصقة في الأنظمة القديمة
            prefixes = ['عبد', 'ابن', 'أبو', 'بن', 'الله']
            for p in prefixes:
                text = re.sub(rf'({p})([أ-ي])', r'\1 \2', text)

            # إزالة أي مسافات مضاعفة متكررة
            return " ".join(text.split())

        # =========================================
        # 🚀 تنفيذ الاستعلام من قاعدة البيانات
        # =========================================
        def execute_search():
            branch_name = self.cmb_credit_branch.get().strip()
            cust_no = self.ent_credit_cust_no.get().strip()
            cclntm_no = self.ent_credit_cclntm.get().strip()

            if not cust_no and not cclntm_no:
                messagebox.showwarning("تنبيه", "يرجى إدخال رقم العميل أو رقم العميل بالمركزي")
                return

            if not hasattr(self, 'branch_mapping') or branch_name not in self.branch_mapping:
                messagebox.showerror("خطأ", "برجاء اختيار فرع صحيح")
                return

            branch_info = self.branch_mapping[branch_name]
            branch_code = branch_info[0] if isinstance(branch_info, tuple) else branch_info

            for widget in self.credit_results_scroll.winfo_children():
                widget.destroy()

            ctk.CTkLabel(self.credit_results_scroll, text="⚡ جاري جلب بيانات الجدارة الائتمانية...",
                         font=("Segoe UI", 16, "bold"), text_color=FIB_GOLD).pack(pady=50)

            def fetch_data():
                try:
                    engine = getattr(self, '_get_db_connection', lambda: None)()
                    if not engine:
                        raise Exception("لا يوجد اتصال بقاعدة البيانات.")

                    cust_str = cust_no.strip()
                    try:
                        cust_int_str = str(int(cust_str)) if cust_str else ""
                    except Exception:
                        cust_int_str = cust_str

                    # بناء كويري مطابقة العميل مع الربط بجدول الأكواد TBL_creditworthinessCodes
                    credit_query = f"""
                        SELECT 
                            L.INAME, L.ICLNTM, L.ICOD, 
                            C.INAMEC,
                            L.IAMT, L.IDAT1, L.IAMT1, 
                            L.IAMTD, L.IDAT2, L.IAMT2, 
                            L.IAMTY, L.IDAT3, L.IAMT3, 
                            L.IEE
                        FROM [dbo].[TBL_creditworthinessLimits] L WITH (NOLOCK)
                        LEFT JOIN [dbo].[TBL_creditworthinessCodes] C WITH (NOLOCK) ON L.ICOD = C.ICOD
                        WHERE L.IBR = '{branch_code}'
                          AND (
                               ('{cust_str}' <> '' AND (L.ICLNT = '{cust_str}' OR L.ICLNT = '{cust_int_str}'))
                               OR
                               ('{cclntm_no}' <> '' AND L.ICLNTM = '{cclntm_no}')
                          )
                    """
                    df = pd.read_sql(credit_query, engine)

                    self.after(0, lambda: update_results_ui(df, cust_no, cclntm_no, branch_name))
                except Exception as e:
                    logging.error(f"Error fetching creditworthiness data: {e}")
                    self.after(0,
                               lambda: update_results_ui(pd.DataFrame(), cust_no, cclntm_no, branch_name, error=str(e)))

            threading.Thread(target=fetch_data, daemon=True).start()

        # =========================================
        # 📑 عرض الواجهة
        # =========================================
        def update_results_ui(df, cust_no, cclntm_no, branch_name, error=None):
            for widget in self.credit_results_scroll.winfo_children():
                widget.destroy()

            if error:
                ctk.CTkLabel(self.credit_results_scroll, text=f"❌ حدث خطأ أثناء الاستعلام:\n{error}",
                             font=("Segoe UI", 14, "bold"), text_color="#EF4444").pack(pady=40)
                return

            if df.empty:
                ctk.CTkLabel(self.credit_results_scroll, text="✔️ لا توجد بيانات جدارة ائتمانية مطابقة",
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

            def create_stat_box(parent, title, value, v_color=TEXT_DARK, bg_color=BOX_BG):
                box = ctk.CTkFrame(parent, fg_color=bg_color, corner_radius=8)
                box.pack(side="right", fill="x", expand=True, padx=4)
                ctk.CTkLabel(box, text=title, font=("Segoe UI", 12, "bold"), text_color=TEXT_MUTED).pack(
                    anchor="center", pady=(8, 2))
                ctk.CTkLabel(box, text=str(value), font=("Segoe UI", 15, "bold"), text_color=v_color).pack(
                    anchor="center", pady=(0, 8))

            row = df.iloc[0]

            # 1. المعالجة وضبط البيانات الرئيسية
            formatted_name = format_arabic_name(row.get('INAME'))
            risk_level_name = row.get('INAMEC') if pd.notna(row.get('INAMEC')) else f"كود: {row.get('ICOD', '—')}"

            # 👤 كارت معلومات العميل
            header_card = ctk.CTkFrame(self.credit_results_scroll, fg_color=CARD_BG, corner_radius=12, border_width=1,
                                       border_color="#CBD5E1")
            header_card.pack(fill="x", padx=10, pady=(5, 15))

            top_row = ctk.CTkFrame(header_card, fg_color="transparent")
            top_row.pack(fill="x", padx=20, pady=15)

            # الجهة اليمنى: اسم العميل
            ctk.CTkLabel(top_row, text=f"👤 {formatted_name}", font=("Segoe UI", 20, "bold"), text_color=FIB_GREEN).pack(
                side="right")

            # الجهة اليسرى: الملاحظات الأساسية
            info_tags = ctk.CTkFrame(top_row, fg_color="transparent")
            info_tags.pack(side="left")

            ctk.CTkLabel(info_tags, text=f"الفرع: {branch_name}", font=("Segoe UI", 13, "bold"), text_color=TEXT_MUTED,
                         fg_color=BOX_BG, corner_radius=6).pack(side="left", padx=4, ipadx=8, ipady=3)
            ctk.CTkLabel(info_tags, text=f"المركزى: {row.get('ICLNTM', '—')}", font=("Segoe UI", 13, "bold"),
                         text_color=FIB_GOLD, fg_color=BOX_BG, corner_radius=6).pack(side="left", padx=4, ipadx=8,
                                                                                     ipady=3)
            ctk.CTkLabel(info_tags, text=f"كود الإلغاء (IEE): {row.get('IEE', '—')}", font=("Segoe UI", 13, "bold"),
                         text_color="#DC2626", fg_color="#FEE2E2", corner_radius=6).pack(side="left", padx=4, ipadx=8,
                                                                                         ipady=3)

            # شريط مستوى المخاطر
            risk_bar = ctk.CTkFrame(header_card, fg_color=BOX_BG, corner_radius=8)
            risk_bar.pack(fill="x", padx=20, pady=(0, 15))
            ctk.CTkLabel(risk_bar, text=f"مستوى المخاطر الائتمانية:  {risk_level_name}", font=("Segoe UI", 15, "bold"),
                         text_color="#B45309").pack(pady=8)

            # 📊 كارت مخصصات وتجنيب الجدارة (المراحل الثلاث)
            data_card = ctk.CTkFrame(self.credit_results_scroll, fg_color=CARD_BG, corner_radius=12, border_width=1,
                                     border_color="#E2E8F0")
            data_card.pack(fill="x", padx=10, pady=5)

            card_title = ctk.CTkFrame(data_card, fg_color="transparent")
            card_title.pack(fill="x", padx=15, pady=(15, 5))
            ctk.CTkLabel(card_title, text="💰 تفاصيل المبالغ المجنبة ومخصصات خسائر الاضمحلال",
                         font=("Segoe UI", 16, "bold"), text_color=FIB_GREEN).pack(side="right")

            ctk.CTkFrame(data_card, fg_color="#F1F5F9", height=2).pack(fill="x", padx=15, pady=5)

            # المرحلة الأولى
            stage1_frame = ctk.CTkFrame(data_card, fg_color="transparent")
            stage1_frame.pack(fill="x", padx=15, pady=8)
            create_stat_box(stage1_frame, "مخصص خسائر الاضمحلال (1)", format_money(row.get('IAMT1')), "#DC2626")
            create_stat_box(stage1_frame, "تاريخ التجنيب (1)", format_date(row.get('IDAT1')), TEXT_DARK)
            create_stat_box(stage1_frame, "المبلغ المجنب (IAMT)", format_money(row.get('IAMT')), FIB_GREEN)

            # المرحلة الثانية
            stage2_frame = ctk.CTkFrame(data_card, fg_color="transparent")
            stage2_frame.pack(fill="x", padx=15, pady=8)
            create_stat_box(stage2_frame, "مخصص خسائر الاضمحلال (2)", format_money(row.get('IAMT2')), "#DC2626")
            create_stat_box(stage2_frame, "تاريخ التجنيب (2)", format_date(row.get('IDAT2')), TEXT_DARK)
            create_stat_box(stage2_frame, "المبلغ المجنب (IAMTD)", format_money(row.get('IAMTD')), FIB_GOLD)

            # المرحلة الثالثة
            stage3_frame = ctk.CTkFrame(data_card, fg_color="transparent")
            stage3_frame.pack(fill="x", padx=15, pady=(8, 15))
            create_stat_box(stage3_frame, "مخصص خسائر الاضمحلال (3)", format_money(row.get('IAMT3')), "#DC2626")
            create_stat_box(stage3_frame, "تاريخ التجنيب (3)", format_date(row.get('IDAT3')), TEXT_DARK)
            create_stat_box(stage3_frame, "المبلغ المجنب (IAMTY)", format_money(row.get('IAMTY')), TEXT_DARK)
