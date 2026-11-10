# -*- coding: utf-8 -*-
"""
شاشة الاستفسار عن التوكيلات برقم العميل — مبنية على BaseInquiryPage.

نفس المنطق والـ SQL الأصلي (TBL_Branches → اسم جدول الحركات → اسم العميل →
tbl_BAMandates) وبنفس كروت العرض، مع الاستفادة من بنية الكلاس الأساسي.
"""

import customtkinter as ctk
import pandas as pd
from tkinter import messagebox

from gui.base_inquiry_page import BaseInquiryPage
from gui.constants import (
    BG_MAIN, CARD_BG, BOX_BG, TEXT_DARK, TEXT_MUTED,
    FIB_GOLD, FIB_GREEN,
)


class MandatesPage(BaseInquiryPage):
    TITLE = "الاستفسار عن التوكيلات برقم العميل"
    SEARCH_PLACEHOLDER = "رقم العميل..."
    SEARCH_LABEL = "رقم العميل:"
    EMPTY_MESSAGE = "🔍 لا توجد توكيلات مسجلة لهذا العميل في هذا الفرع"
    LOADING_TEXT = "⚡ جاري البحث عن التوكيلات..."

    def build(self):
        # أسماء توافقية مع الكود القديم
        self.ent_mandates_cust_no = self.search_entry
        self.cmb_mandates_branch = self.branch_combo
        self.mandates_results_scroll = self.results_scroll

    # =========================================================
    # ⚙️ البحث
    # =========================================================
    def on_search(self):
        branch_name = self.branch_combo.get()
        cust_no = self.search_entry.get().strip()

        if not cust_no:
            messagebox.showwarning("تنبيه", "يرجى إدخال رقم العميل أولاً")
            self.search_entry.focus()
            return

        branch = self.require_branch()
        if branch is None:
            return
        branch_code, _branch_name = branch

        self.show_loading()

        def work():
            engine = self.get_engine()
            if not engine:
                raise Exception("لم يتم العثور على دالة الاتصال بقاعدة البيانات.")

            # 1. جلب اسم الجدول الخاص بالفرع
            # 📌 أداء: محتاج Index على [dbo].[TBL_Branches] (BranchCode)
            branch_query = f"SELECT GL_TableName, TableName FROM [dbo].[TBL_Branches] WITH (NOLOCK) WHERE BranchCode = N'{branch_code}'"
            branch_df = pd.read_sql(branch_query, engine)

            target_table = None
            if not branch_df.empty:
                target_table = branch_df.iloc[0].get('GL_TableName') or branch_df.iloc[0].get('TableName')

            fetched_client_name = "غير مسجل"
            if target_table and pd.notna(target_table):
                target_table = str(target_table).strip()
                client_query = f"SELECT TOP 1 BNAME FROM [dbo].[{target_table}] WITH (NOLOCK) WHERE BCLNT = N'{cust_no}'"
                client_df = pd.read_sql(client_query, engine)
                if not client_df.empty and pd.notna(client_df.iloc[0].get('BNAME')):
                    fetched_client_name = str(client_df.iloc[0].get('BNAME')).strip()

            # 2. الاستعلام عن التوكيلات
            # 📌 أداء: محتاج Index على [dbo].[tbl_BAMandates] (SBR, sclnt)
            sql = f"""
                SELECT sname, sdatt, stknum, SEE
                FROM [dbo].[tbl_BAMandates] WITH (NOLOCK)
                WHERE SBR = N'{branch_code}'
                  AND sclnt = N'{cust_no}'
            """
            df = pd.read_sql(sql, engine)
            return df, fetched_client_name

        def on_success(result):
            df, client_name = result
            self._render(df, client_name, cust_no, branch_name)

        self.run_async(work, on_success)

    # =========================================================
    # 🖼️ عرض النتائج (كروت)
    # =========================================================
    def _render(self, df, client_name, cust_no, branch_name):
        self.clear_results()

        if df.empty:
            self.show_empty()
            return

        cleaned_client_name = self.fix_arabic_name(client_name)

        # =========================================
        # 👤 1. كارت بيانات العميل الرئيسي (مرة واحدة بالفيو)
        # =========================================
        client_header_card = ctk.CTkFrame(self.results_scroll, fg_color=CARD_BG, corner_radius=12,
                                          border_width=1, border_color="#CBD5E1")
        client_header_card.pack(fill="x", padx=10, pady=(5, 15))

        client_inner = ctk.CTkFrame(client_header_card, fg_color="transparent")
        client_inner.pack(fill="x", padx=20, pady=12)

        ctk.CTkLabel(client_inner, text=f"👤 اسم العميل: {cleaned_client_name}", font=("Segoe UI", 16, "bold"),
                     text_color=FIB_GREEN).pack(side="right")

        ctk.CTkLabel(client_inner, text=f"الفرع: {branch_name} | رقم العميل: {cust_no}",
                     font=("Segoe UI", 13, "bold"),
                     text_color=TEXT_MUTED, fg_color=BOX_BG, corner_radius=6).pack(side="left", ipadx=10, ipady=3)

        # =========================================
        # 📑 2. كروت التوكيلات الخاصة بالعميل
        # =========================================
        for _, row in df.iterrows():
            agent_name = self.fix_arabic_name(row['sname'])
            mandate_num = str(row['stknum']).replace('.0', '') if pd.notna(row['stknum']) else "—"
            mandate_date = self.format_date_str(row['sdatt'])

            # كود الإلغاء SEE (1 = ملغي, 0 = ساري)
            see_val = str(row['SEE']).replace('.0', '').strip() if pd.notna(row['SEE']) else ""

            if see_val == '1':
                status_text = "ملغي 🛑"
                status_color = "#DC2626"
                status_bg = "#FEE2E2"
            elif see_val == '0':
                status_text = "ساري ✅"
                status_color = "#005C34"
                status_bg = "#DCFCE7"
            else:
                status_text = f"غير محدد ({see_val})"
                status_color = TEXT_MUTED
                status_bg = BOX_BG

            card = ctk.CTkFrame(self.results_scroll, fg_color=CARD_BG, corner_radius=12,
                                border_width=1, border_color="#E2E8F0")
            card.pack(fill="x", padx=10, pady=8)

            stripe_color = status_color if see_val in ['0', '1'] else FIB_GOLD
            ctk.CTkFrame(card, fg_color=stripe_color, width=5, corner_radius=0).pack(side="right", fill="y", pady=10)

            card_content = ctk.CTkFrame(card, fg_color="transparent")
            card_content.pack(fill="both", expand=True, padx=20, pady=12)

            # الهيدر: رقم التوكيل والحالة
            header_row = ctk.CTkFrame(card_content, fg_color="transparent")
            header_row.pack(fill="x", pady=(0, 8))

            ctk.CTkLabel(header_row, text=f"رقم التوكيل: {mandate_num} 📑", font=("Segoe UI", 16, "bold"),
                         text_color=TEXT_DARK).pack(side="right")

            ctk.CTkLabel(header_row, text=f"الحالة: {status_text}", font=("Segoe UI", 13, "bold"),
                         text_color=status_color, fg_color=status_bg, corner_radius=6).pack(side="left", ipadx=8,
                                                                                            ipady=2)

            # تفاصيل التوكيل: اسم صاحب التوكيل وتاريخ التوكيل
            details_row = ctk.CTkFrame(card_content, fg_color="transparent")
            details_row.pack(fill="x", pady=4)

            ctk.CTkLabel(details_row, text=f"اسم صاحب التوكيل: {agent_name} 📝", font=("Segoe UI", 14, "bold"),
                         text_color=TEXT_MUTED).pack(side="right")

            ctk.CTkLabel(details_row, text=f"تاريخ التوكيل: {mandate_date} 📅", font=("Segoe UI", 13, "bold"),
                         text_color=FIB_GREEN, fg_color=BOX_BG, corner_radius=6).pack(side="left", ipadx=10, ipady=2)
