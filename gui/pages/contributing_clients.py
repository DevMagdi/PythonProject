# -*- coding: utf-8 -*-
"""
شاشة الاستفسار الأبجدي عن عملاء مساهمين.

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


class ContributingClientsInquiryPage(LegacyInquiryPage):
    """شاشة الاستفسار الأبجدي عن عملاء مساهمين."""
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
            header, text="الاستفسار الأبجدي عن عملاء مساهمين 👥",
            font=("Segoe UI", 22, "bold"), text_color=CARD_BG
        ).pack(side="right", padx=30, pady=15)

        # =========================================
        # 🔍 منطقة البحث (الاسم)
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

        self.ent_search_name = ctk.CTkEntry(search_inner, font=("Segoe UI", 15, "bold"), justify="right",
                                            placeholder_text="أدخل الاسم أو أول حرفين...", width=300, height=40,
                                            border_color="#CBD5E1")
        self.ent_search_name.pack(side="left", padx=10)
        ctk.CTkLabel(search_inner, text="اسم العميل:", font=("Segoe UI", 14, "bold"), text_color=TEXT_DARK).pack(
            side="left", padx=(10, 2))

        self.contrib_results_scroll = ctk.CTkScrollableFrame(main_container, fg_color="transparent")
        self.contrib_results_scroll.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        # =========================================
        # ⏱️ البحث المباشر أثناء الكتابة (Live Search)
        # =========================================
        self.search_timer = None

        def on_key_release(event):
            if self.search_timer is not None:
                self.after_cancel(self.search_timer)
            self.search_timer = self.after(500, execute_search)

        self.ent_search_name.bind("<KeyRelease>", on_key_release)
        self.ent_search_name.bind("<Return>", lambda event: execute_search())

        # =========================================
        # 🛠️ معالجة الاسم العربي الملتصق
        # =========================================
        def format_arabic_name(raw_name):
            if not raw_name or pd.isna(raw_name):
                return "غير متوفر"
            text = str(raw_name).strip()
            prefixes = ['عبد', 'ابن', 'أبو', 'بن', 'الله', 'الدين']
            for p in prefixes:
                text = re.sub(rf'({p})([أ-ي])', r'\1 \2', text)
            return " ".join(text.split())

        # =========================================
        # 🧹 تنظيف الشاشة
        # =========================================
        def clear_search():
            self.ent_search_name.delete(0, 'end')
            for widget in self.contrib_results_scroll.winfo_children():
                widget.destroy()

        # =========================================
        # 📊 عرض تفاصيل حركات العميل (النافذة المنبثقة)
        # =========================================
        def show_client_details(client_name, client_code):
            details_win = ctk.CTkToplevel(self)
            details_win.title(f"تفاصيل حركات العميل: {client_name}")
            details_win.geometry("850x600")
            details_win.attributes('-topmost', True)
            details_win.configure(fg_color=BG_MAIN)

            header_frame = ctk.CTkFrame(details_win, fg_color=FIB_GREEN, height=60, corner_radius=0)
            header_frame.pack(fill="x")
            header_frame.pack_propagate(False)
            ctk.CTkLabel(header_frame, text=f"سجل حركات: {client_name} - (كود: {client_code})",
                         font=("Segoe UI", 18, "bold"), text_color=CARD_BG).pack(pady=15)

            scroll_details = ctk.CTkScrollableFrame(details_win, fg_color="transparent")
            scroll_details.pack(fill="both", expand=True, padx=20, pady=20)

            ctk.CTkLabel(scroll_details, text="⚡ جاري جلب التفاصيل...", font=("Segoe UI", 16, "bold"),
                         text_color=FIB_GOLD).pack(pady=50)

            def fetch_details():
                try:
                    engine = getattr(self, '_get_db_connection', lambda: None)()
                    if not engine:
                        raise Exception("لا يوجد اتصال بقاعدة البيانات.")

                    # الاستعلام مبني على الرقم الكودي لضمان جلب كل حركات العميل
                    query = """
                            SELECT Hdat, \
                                   Hshrp, \
                                   HAMTPR, \
                                   HSHRD, \
                                   HAMTDR, \
                                   HBRD
                            FROM [dbo].[TBL_contributng_clients] \
                            WITH (NOLOCK)
                            WHERE HCODL = ?
                            ORDER BY Hdat DESC \
                            """
                    df_details = pd.read_sql(query, engine, params=(client_code,))
                    self.after(0, lambda d=df_details: render_details_ui(d))
                except Exception as e:
                    err_msg = str(e)
                    logging.error(f"Error fetching client details: {err_msg}")
                    self.after(0, lambda err=err_msg: render_details_ui(pd.DataFrame(), error=err))

            def render_details_ui(df, error=None):
                for widget in scroll_details.winfo_children():
                    widget.destroy()

                if error:
                    ctk.CTkLabel(scroll_details, text=f"❌ خطأ:\n{error}", font=("Segoe UI", 14, "bold"),
                                 text_color="#EF4444").pack(pady=20)
                    return
                if df.empty:
                    ctk.CTkLabel(scroll_details, text="✔️ لا توجد حركات مسجلة لهذا العميل.",
                                 font=("Segoe UI", 16, "bold"), text_color=TEXT_MUTED).pack(pady=40)
                    return

                # === دالة مساعدة لتحويل القيم إلى Float بأمان ===
                def safe_float(val):
                    try:
                        if pd.isna(val) or str(val).strip() == '':
                            return 0.0
                        return float(val)
                    except (ValueError, TypeError):
                        return 0.0

                for _, row in df.iterrows():
                    move_card = ctk.CTkFrame(scroll_details, fg_color=CARD_BG, corner_radius=10, border_width=1,
                                             border_color="#E2E8F0")
                    move_card.pack(fill="x", pady=8)

                    hdat = pd.to_datetime(row.get('Hdat')).strftime('%Y-%m-%d') if pd.notna(row.get('Hdat')) else "—"
                    ctk.CTkLabel(move_card, text=f"📅 تاريخ الحركة: {hdat}", font=("Segoe UI", 14, "bold"),
                                 text_color=TEXT_DARK).pack(anchor="e", padx=15, pady=(10, 5))

                    data_row = ctk.CTkFrame(move_card, fg_color="transparent")
                    data_row.pack(fill="x", padx=10, pady=(0, 10))

                    # تنظيف وتحويل القيم بأمان
                    hamtpr_val = safe_float(row.get('HAMTPR', 0))
                    hamtdr_val = safe_float(row.get('HAMTDR', 0))

                    egp_frame = ctk.CTkFrame(data_row, fg_color=BOX_BG, corner_radius=8)
                    egp_frame.pack(side="right", fill="x", expand=True, padx=5)
                    ctk.CTkLabel(egp_frame, text="🇪🇬 البيانات المحلية", font=("Segoe UI", 13, "bold"),
                                 text_color=FIB_GREEN).pack(pady=5)
                    ctk.CTkLabel(egp_frame, text=f"الأسهم (Hshrp): {row.get('Hshrp', 0)}", font=("Segoe UI", 12)).pack()
                    ctk.CTkLabel(egp_frame, text=f"الأرباح (HAMTPR): {hamtpr_val:,.2f}", font=("Segoe UI", 12)).pack()
                    ctk.CTkLabel(egp_frame, text=f"الفرع (HBRD): {row.get('HBRD', '—')}", font=("Segoe UI", 12)).pack(
                        pady=(0, 5))

                    usd_frame = ctk.CTkFrame(data_row, fg_color="#F0F9FF", corner_radius=8)
                    usd_frame.pack(side="left", fill="x", expand=True, padx=5)
                    ctk.CTkLabel(usd_frame, text="💵 البيانات بالدولار", font=("Segoe UI", 13, "bold"),
                                 text_color="#0369A1").pack(pady=5)
                    ctk.CTkLabel(usd_frame, text=f"الأسهم (HSHRD): {row.get('HSHRD', 0)}", font=("Segoe UI", 12)).pack()
                    ctk.CTkLabel(usd_frame, text=f"الأرباح (HAMTDR): {hamtdr_val:,.2f}", font=("Segoe UI", 12)).pack()
                    ctk.CTkLabel(usd_frame, text=f"الفرع (HBRD): {row.get('HBRD', '—')}", font=("Segoe UI", 12)).pack(
                        pady=(0, 5))

            threading.Thread(target=fetch_details, daemon=True).start()

        # =========================================
        # 📑 عرض نتائج الواجهة
        # =========================================
        def update_results_ui(df, error=None):
            for widget in self.contrib_results_scroll.winfo_children():
                widget.destroy()

            if error:
                ctk.CTkLabel(self.contrib_results_scroll, text=f"❌ حدث خطأ أثناء الاستعلام:\n{error}",
                             font=("Segoe UI", 14, "bold"), text_color="#EF4444").pack(pady=40)
                return

            if df.empty:
                ctk.CTkLabel(self.contrib_results_scroll, text="✔️ لا توجد أسماء مساهمين مطابقة لبحثك",
                             font=("Segoe UI", 18, "bold"), text_color=TEXT_MUTED).pack(pady=60)
                return

            results_count_frame = ctk.CTkFrame(self.contrib_results_scroll, fg_color="transparent")
            results_count_frame.pack(fill="x", padx=10, pady=(0, 10))
            ctk.CTkLabel(results_count_frame, text=f"تم العثور على ({len(df)}) نتيجة مطابقة",
                         font=("Segoe UI", 13, "bold"), text_color=FIB_GREEN).pack(side="right")

            for index, row in df.iterrows():
                raw_name = row.get('HNAME', 'غير متوفر')
                client_name = format_arabic_name(raw_name)
                client_code = row.get('HCODL', '—')

                card = ctk.CTkFrame(self.contrib_results_scroll, fg_color=CARD_BG, corner_radius=10, border_width=1,
                                    border_color="#CBD5E1", cursor="hand2")
                card.pack(fill="x", padx=10, pady=5)

                inner_row = ctk.CTkFrame(card, fg_color="transparent")
                inner_row.pack(fill="x", padx=20, pady=15)

                lbl_name = ctk.CTkLabel(inner_row, text=f"👤 {client_name}", font=("Segoe UI", 18, "bold"),
                                        text_color=TEXT_DARK)
                lbl_name.pack(side="right")

                code_frame = ctk.CTkFrame(inner_row, fg_color=BOX_BG, corner_radius=6)
                code_frame.pack(side="left")
                ctk.CTkLabel(code_frame, text="الرقم الكودي:", font=("Segoe UI", 12, "bold"),
                             text_color=TEXT_MUTED).pack(side="right", padx=(10, 5), pady=5)
                ctk.CTkLabel(code_frame, text=f"{client_code}", font=("Segoe UI", 16, "bold"),
                             text_color=FIB_GOLD).pack(side="right", padx=(5, 10), pady=5)

                def on_card_click(event, n=client_name, c=client_code):
                    show_client_details(n, c)

                card.bind("<Button-1>", on_card_click)
                inner_row.bind("<Button-1>", on_card_click)
                lbl_name.bind("<Button-1>", on_card_click)
                code_frame.bind("<Button-1>", on_card_click)
                for child in code_frame.winfo_children():
                    child.bind("<Button-1>", on_card_click)

        # =========================================
        # 🚀 تنفيذ الاستعلام من قاعدة البيانات
        # =========================================
        def execute_search():
            search_name = self.ent_search_name.get().strip()

            if not search_name:
                for widget in self.contrib_results_scroll.winfo_children():
                    widget.destroy()
                return

            for widget in self.contrib_results_scroll.winfo_children():
                widget.destroy()

            ctk.CTkLabel(self.contrib_results_scroll, text="⚡ جاري البحث عن المساهمين...",
                         font=("Segoe UI", 16, "bold"), text_color=FIB_GOLD).pack(pady=50)

            def fetch_data():
                try:
                    engine = getattr(self, '_get_db_connection', lambda: None)()
                    if not engine:
                        raise Exception("لا يوجد اتصال بقاعدة البيانات.")

                    # الاستعلام الرئيسي لجلب العميل برقم كودي موحد فقط
                    query = """
                            SELECT DISTINCT HNAME, HCODL
                            FROM [dbo].[TBL_contributng_clients] \
                            WITH (NOLOCK)
                            WHERE HNAME LIKE ?
                            ORDER BY HNAME ASC \
                            """

                    search_param = f"{search_name}%"
                    df = pd.read_sql(query, engine, params=(search_param,))

                    self.after(0, lambda d=df: update_results_ui(d))
                except Exception as e:
                    err_msg = str(e)
                    logging.error(f"Error fetching contributing clients: {err_msg}")
                    self.after(0, lambda err=err_msg: update_results_ui(pd.DataFrame(), error=err))

            threading.Thread(target=fetch_data, daemon=True).start()
