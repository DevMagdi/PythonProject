# -*- coding: utf-8 -*-
"""
شاشة الاستفسار عن التوكيلات برقم العميل — نسخة فائقة السرعة (Index-Optimized + Pagination).
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
    LOADING_TEXT = "⚡ جاري البحث السريع عن التوكيلات..."
    PAGE_SIZE = 30  # عرض 30 توكيل في الصفحة لمنع تهنيج الواجهة

    def build(self):
        # أسماء توافقية مع الكود القديم
        self.ent_mandates_cust_no = self.search_entry
        self.cmb_mandates_branch = self.branch_combo
        self.mandates_results_scroll = self.results_scroll

        self._current_df = pd.DataFrame()
        self._client_name = "غير مسجل"
        self._cust_no = ""
        self._branch_name = ""
        self._current_page = 0

    # =========================================================
    # ⚙️ البحث (فائق السرعة)
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

            clean_branch = str(branch_code).strip()
            clean_cust = str(cust_no).strip()

            # تجهيز احتمالات الأصفار البادئة في بايثون لضرب الـ Index مباشرة
            branch_variants = list({clean_branch, clean_branch.lstrip('0'), clean_branch.zfill(3)})
            cust_variants = list({clean_cust, clean_cust.lstrip('0'), clean_cust.zfill(6), clean_cust.zfill(7)})

            # 1. جلب اسم العميل (من الكاش أولاً لتوفير استعلام)
            fetched_client_name = "غير مسجل"
            try:
                target_table = getattr(self, "branch_table_mapping", {}).get(clean_branch)
                if not target_table and hasattr(self, "app"):
                    target_table = getattr(self.app, "branch_table_mapping", {}).get(clean_branch)

                if not target_table:
                    branch_query = "SELECT TOP 1 TableName FROM [dbo].[TBL_Branches] WITH (NOLOCK) WHERE BranchCode = ?"
                    branch_df = pd.read_sql(branch_query, engine, params=(clean_branch,))
                    if not branch_df.empty:
                        target_table = branch_df.iloc[0].get('TableName')

                if target_table and pd.notna(target_table):
                    target_table = str(target_table).strip()
                    clean_table = target_table if "[" in target_table else f"[dbo].[{target_table}]"

                    c_placeholders_tbl = ",".join(["?"] * len(cust_variants))
                    client_query = f"""
                        SELECT TOP 1 BNAME 
                        FROM {clean_table} WITH (NOLOCK) 
                        WHERE BCLNT IN ({c_placeholders_tbl})
                          AND BNAME IS NOT NULL 
                          AND BNAME <> ''
                    """
                    client_df = pd.read_sql(client_query, engine, params=tuple(cust_variants))
                    if not client_df.empty and pd.notna(client_df.iloc[0].get('BNAME')):
                        fetched_client_name = str(client_df.iloc[0].get('BNAME')).strip()
            except Exception:
                pass

            # 2. الاستعلام المباشر والسريع عن التوكيلات (مطابق لترتيب IX_tbl_BAMandates_SCLNT_SBR)
            c_placeholders = ",".join(["?"] * len(cust_variants))
            b_placeholders = ",".join(["?"] * len(branch_variants))

            sql = f"""
                SELECT sname, sdatt, stknum, SEE
                FROM [dbo].[tbl_BAMandates] WITH (NOLOCK)
                WHERE sclnt IN ({c_placeholders})
                  AND SBR IN ({b_placeholders})
            """
            df = pd.read_sql(sql, engine, params=tuple(cust_variants + branch_variants))
            return df, fetched_client_name

        def on_success(result):
            df, client_name = result
            self._current_df = df
            self._client_name = self.fix_arabic_name(client_name)
            self._cust_no = cust_no
            self._branch_name = branch_name
            self._current_page = 0
            self._render_page()

        self.run_async(work, on_success)

    def _change_page(self, delta):
        self._current_page += delta
        self._render_page()

    # =========================================================
    # 🖼️ عرض النتائج (كروت + Pagination)
    # =========================================================
    def _render_page(self):
        self.clear_results()

        if self._current_df.empty:
            self.show_empty()
            return

        total_records = len(self._current_df)
        total_pages = (total_records + self.PAGE_SIZE - 1) // self.PAGE_SIZE
        start_idx = self._current_page * self.PAGE_SIZE
        end_idx = min(start_idx + self.PAGE_SIZE, total_records)

        # =========================================
        # 👤 1. كارت بيانات العميل الرئيسي
        # =========================================
        client_header_card = ctk.CTkFrame(
            self.results_scroll, fg_color=CARD_BG, corner_radius=12,
            border_width=1, border_color="#CBD5E1"
        )
        client_header_card.pack(fill="x", padx=10, pady=(5, 12))

        client_inner = ctk.CTkFrame(client_header_card, fg_color="transparent")
        client_inner.pack(fill="x", padx=20, pady=12)

        ctk.CTkLabel(
            client_inner, text=f"👤 اسم العميل: {self._client_name}",
            font=("Segoe UI", 16, "bold"), text_color=FIB_GREEN
        ).pack(side="right")

        ctk.CTkLabel(
            client_inner,
            text=f"الفرع: {self._branch_name} | رقم العميل: {self._cust_no} | الإجمالي: {total_records}",
            font=("Segoe UI", 13, "bold"),
            text_color=TEXT_MUTED, fg_color=BOX_BG, corner_radius=6
        ).pack(side="left", ipadx=10, ipady=3)

        # =========================================
        # 🔄 شريط التنقل بين الصفحات (إذا زادت النتائج عن 30)
        # =========================================
        if total_pages > 1:
            nav_bar = ctk.CTkFrame(
                self.results_scroll, fg_color=CARD_BG, corner_radius=10,
                border_width=1, border_color="#E2E8F0"
            )
            nav_bar.pack(fill="x", padx=10, pady=(0, 10))

            ctk.CTkLabel(
                nav_bar,
                text=f"عرض التوكيلات ({start_idx + 1} - {end_idx}) من أصل {total_records}",
                font=("Segoe UI", 13, "bold"), text_color=TEXT_DARK
            ).pack(side="right", padx=15, pady=8)

            btns_frame = ctk.CTkFrame(nav_bar, fg_color="transparent")
            btns_frame.pack(side="left", padx=15, pady=5)

            ctk.CTkButton(
                btns_frame, text="التالي ◀", width=80, height=30, font=("Segoe UI", 13, "bold"),
                fg_color=FIB_GREEN, state="normal" if self._current_page < total_pages - 1 else "disabled",
                command=lambda: self._change_page(1)
            ).pack(side="left", padx=4)

            ctk.CTkLabel(
                btns_frame, text=f"صفحة {self._current_page + 1} من {total_pages}",
                font=("Segoe UI", 13, "bold"), text_color=TEXT_DARK
            ).pack(side="left", padx=8)

            ctk.CTkButton(
                btns_frame, text="▶ السابق", width=80, height=30, font=("Segoe UI", 13, "bold"),
                fg_color=FIB_GREEN, state="normal" if self._current_page > 0 else "disabled",
                command=lambda: self._change_page(-1)
            ).pack(side="left", padx=4)

        # =========================================
        # 📑 2. كروت التوكيلات الخاصة بالصفحة الحالية فقط
        # =========================================
        page_df = self._current_df.iloc[start_idx:end_idx]

        for _, row in page_df.iterrows():
            agent_name = self.fix_arabic_name(row['sname'])
            mandate_num = str(row['stknum']).replace('.0', '') if pd.notna(row['stknum']) else "—"
            mandate_date = self.format_date_str(row['sdatt'])

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

            card = ctk.CTkFrame(
                self.results_scroll, fg_color=CARD_BG, corner_radius=12,
                border_width=1, border_color="#E2E8F0"
            )
            card.pack(fill="x", padx=10, pady=8)

            stripe_color = status_color if see_val in ['0', '1'] else FIB_GOLD
            ctk.CTkFrame(card, fg_color=stripe_color, width=5, corner_radius=0).pack(side="right", fill="y", pady=10)

            card_content = ctk.CTkFrame(card, fg_color="transparent")
            card_content.pack(fill="both", expand=True, padx=20, pady=12)

            header_row = ctk.CTkFrame(card_content, fg_color="transparent")
            header_row.pack(fill="x", pady=(0, 8))

            ctk.CTkLabel(
                header_row, text=f"رقم التوكيل: {mandate_num} 📑",
                font=("Segoe UI", 16, "bold"), text_color=TEXT_DARK
            ).pack(side="right")

            ctk.CTkLabel(
                header_row, text=f"الحالة: {status_text}",
                font=("Segoe UI", 13, "bold"),
                text_color=status_color, fg_color=status_bg, corner_radius=6
            ).pack(side="left", ipadx=8, ipady=2)

            details_row = ctk.CTkFrame(card_content, fg_color="transparent")
            details_row.pack(fill="x", pady=4)

            ctk.CTkLabel(
                details_row, text=f"اسم صاحب التوكيل: {agent_name} 📝",
                font=("Segoe UI", 14, "bold"), text_color=TEXT_MUTED
            ).pack(side="right")

            ctk.CTkLabel(
                details_row, text=f"تاريخ التوكيل: {mandate_date} 📅",
                font=("Segoe UI", 13, "bold"),
                text_color=FIB_GREEN, fg_color=BOX_BG, corner_radius=6
            ).pack(side="left", ipadx=10, ipady=2)