# -*- coding: utf-8 -*-
"""
شاشة استعلام الشيكات المرفوضة — مبنية على BaseInquiryPage.

نفس SQL ونفس شكل الكروت كما في النسخة القديمة، مع إعادة استخدام
الهيدر/البحث/fix_arabic_name من الكلاس الأساسي.
"""

import customtkinter as ctk
import pandas as pd
from tkinter import messagebox

from gui.base_inquiry_page import BaseInquiryPage
from gui.constants import (
    BG_MAIN, CARD_BG, BOX_BG, TEXT_DARK, TEXT_MUTED,
    FIB_GOLD, FIB_GREEN,
)


class RejectedChequesPage(BaseInquiryPage):
    TITLE = "استعلام الشيكات المرفوضة"
    SEARCH_PLACEHOLDER = "رقم الحساب..."
    SEARCH_LABEL = "رقم الحساب:"
    EMPTY_MESSAGE = "🔍 لا توجد شيكات مرفوضة لهذا الحساب في هذا الفرع"
    LOADING_TEXT = "⚡ جاري البحث في قاعدة البيانات..."

    def build(self):
        # أسماء توافقية مع الكود القديم
        self.ent_rej_acc = self.search_entry
        self.cmb_rej_branch = self.branch_combo
        self.rej_results_scroll = self.results_scroll

    # =========================================================
    # ⚙️ البحث
    # =========================================================
    def on_search(self):
        acc_num = self.search_entry.get().strip()

        if not acc_num:
            messagebox.showwarning("تنبيه", "يرجى إدخال رقم الحساب أولاً")
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

            # 📌 أداء: محتاج Index على [dbo].[TBL_cheques] (MBR, MCLNT)
            sql = f"""
                    SELECT
                        c.MCHNO, c.MAMT1, c.MDAT1, c.MDAT2, c.MCOD, c.MBAL,
                        cl.BNAME
                    FROM [dbo].[TBL_cheques] AS c WITH (NOLOCK)
                    LEFT JOIN [dbo].[TBL_client_name] AS cl WITH (NOLOCK)
                        ON c.MCLNT = cl.BCLNT
                    WHERE c.MBR = N'{branch_code}' AND c.MCLNT = N'{acc_num}'
                """
            return pd.read_sql(sql, engine)

        self.run_async(work, self._render)

    # =========================================================
    # 🖼️ عرض النتائج (كروت)
    # =========================================================
    def _render(self, df):
        self.clear_results()

        if df.empty:
            self.show_empty()
            return

        for _, row in df.iterrows():
            chq_no = str(row['MCHNO']).replace('.0', '') if pd.notna(row['MCHNO']) else "غير معروف"
            reject_code = str(row['MCOD']).replace('.0', '') if pd.notna(row['MCOD']) else "—"
            cust_name = self.fix_arabic_name(row['BNAME'])

            # تنسيق المبالغ المالية
            try:
                amount = f"{float(row['MAMT1']):,.2f}" if pd.notna(row['MAMT1']) else "0.00"
                balance = f"{float(row['MBAL']):,.2f}" if pd.notna(row['MBAL']) else "0.00"
            except (TypeError, ValueError):
                amount = str(row['MAMT1'])
                balance = str(row['MBAL'])

            # تنسيق التواريخ
            rej_date = str(row['MDAT1']).split()[0] if pd.notna(row['MDAT1']) else "—"
            due_date = str(row['MDAT2']).split()[0] if pd.notna(row['MDAT2']) else "—"

            card = ctk.CTkFrame(self.results_scroll, fg_color=CARD_BG, corner_radius=12,
                                border_width=1, border_color="#E2E8F0")
            card.pack(fill="x", padx=10, pady=8)

            # الخط الذهبي الجانبي
            ctk.CTkFrame(card, fg_color=FIB_GOLD, width=5, corner_radius=0).pack(side="right", fill="y", pady=10)

            card_content = ctk.CTkFrame(card, fg_color="transparent")
            card_content.pack(fill="both", expand=True, padx=20, pady=15)

            # صف العنوان (رقم الشيك وكود الرفض)
            header_row = ctk.CTkFrame(card_content, fg_color="transparent")
            header_row.pack(fill="x", pady=(0, 5))

            ctk.CTkLabel(header_row, text=f"شيك رقم : {chq_no} 🧾", font=("Segoe UI", 18, "bold"),
                         text_color=FIB_GREEN).pack(side="right")
            ctk.CTkLabel(header_row, text=f"كود الرفض: {reject_code} ⛔", font=("Segoe UI", 14, "bold"),
                         text_color="#EF4444", fg_color="#FEE2E2", corner_radius=6).pack(side="left", ipadx=10,
                                                                                         ipady=2)

            # صف اسم العميل
            name_row = ctk.CTkFrame(card_content, fg_color="transparent")
            name_row.pack(fill="x", pady=(0, 10))
            ctk.CTkLabel(name_row, text=f"العميل: {cust_name} 👤", font=("Segoe UI", 15, "bold"),
                         text_color=TEXT_MUTED).pack(side="right")

            # خط فاصل
            ctk.CTkFrame(card_content, fg_color="#F1F5F9", height=2).pack(fill="x", pady=5)

            # صف الداتا (مقسم لـ 4 أجزاء بشكل أنيق)
            data_grid = ctk.CTkFrame(card_content, fg_color="transparent")
            data_grid.pack(fill="x", pady=10)
            data_grid.grid_columnconfigure((0, 1, 2, 3), weight=1)

            # ترتيب العناصر من اليمين لليسار في الجريد
            self.create_info_box(data_grid, 0, 3, "مبلغ الشيك", f"{amount} EGP", val_color=FIB_GREEN)
            self.create_info_box(data_grid, 0, 2, "تاريخ الاستحقاق", due_date)
            self.create_info_box(data_grid, 0, 1, "تاريخ الرفض", rej_date, val_color="#EF4444")
            self.create_info_box(data_grid, 0, 0, "رصيد الحساب", f"{balance} EGP", val_color=TEXT_DARK)
