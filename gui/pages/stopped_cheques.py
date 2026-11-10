# -*- coding: utf-8 -*-
"""
شاشة استعلام الشيكات الموقوفة — مبنية على BaseInquiryPage.

الكل منطق البحث والعرض محفوظ كما هو من النسخة القديمة (نفس الـ SQL ونفس الكروت)،
لكن بدلاً من 300 سطر متكررة يستفيد هذا الملف من:
الهيدر الموحّد + منطقة البحث الموحّدة + fix_arabic_name المشتركة + run_async.
"""
import customtkinter as ctk
import pandas as pd
from tkinter import messagebox

from gui.base_inquiry_page import BaseInquiryPage
from gui.constants import (
    BG_MAIN, CARD_BG, BOX_BG, TEXT_DARK, TEXT_MUTED,
    FIB_GOLD, FIB_GREEN, STOP_COLOR,
)


class StoppedChequesPage(BaseInquiryPage):
    TITLE = "استعلام الشيكات الموقوفة"
    SEARCH_PLACEHOLDER = "رقم الحساب..."
    SEARCH_LABEL = "رقم الحساب:"
    EMPTY_MESSAGE = "🔍 لا توجد شيكات موقوفة لهذا الحساب في هذا الفرع"
    LOADING_TEXT = "⚡ جاري البحث في قاعدة البيانات..."

    def build(self):
        # أسماء توافقية مع الكود القديم (كانت self.ent_stopped_acc إلخ)
        self.ent_stopped_acc = self.search_entry
        self.cmb_stopped_branch = self.branch_combo
        self.stopped_results_scroll = self.results_scroll

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

            # 📌 أداء: لو الاستعلام بطيء، محتاج Index على [dbo].[TBL_cheques] (BCHBR, BCLNT)
            sql = f"""
                    SELECT
                        c.BCHNO, c.BDAT, c.BDAT1, c.BCOD,
                        cl.BNAME
                    FROM [dbo].[TBL_cheques] AS c WITH (NOLOCK)
                    LEFT JOIN [dbo].[TBL_client_name] AS cl WITH (NOLOCK)
                        ON c.BCLNT = cl.BCLNT
                    WHERE c.BCHBR = N'{branch_code}' AND c.BCLNT = N'{acc_num}'
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
            chq_no = str(row['BCHNO']).replace('.0', '') if pd.notna(row['BCHNO']) else "غير معروف"
            stop_code = str(row['BCOD']).replace('.0', '') if pd.notna(row['BCOD']) else "—"
            cust_name = self.fix_arabic_name(row['BNAME'])

            stop_date = str(row['BDAT']).split()[0] if pd.notna(row['BDAT']) and str(row['BDAT']).strip() else "—"
            cancel_date = str(row['BDAT1']).split()[0] if pd.notna(row['BDAT1']) and str(
                row['BDAT1']).strip() else "—"

            card = ctk.CTkFrame(self.results_scroll, fg_color=CARD_BG, corner_radius=12,
                                border_width=1, border_color="#E2E8F0")
            card.pack(fill="x", padx=10, pady=8)

            ctk.CTkFrame(card, fg_color=STOP_COLOR, width=5, corner_radius=0).pack(side="right", fill="y", pady=10)

            card_content = ctk.CTkFrame(card, fg_color="transparent")
            card_content.pack(fill="both", expand=True, padx=20, pady=15)

            # صف العنوان
            header_row = ctk.CTkFrame(card_content, fg_color="transparent")
            header_row.pack(fill="x", pady=(0, 5))

            ctk.CTkLabel(header_row, text=f"شيك رقم : {chq_no} 🧾", font=("Segoe UI", 18, "bold"),
                         text_color=FIB_GREEN).pack(side="right")
            ctk.CTkLabel(header_row, text=f"كود الإيقاف/الإلغاء: {stop_code} 🛑", font=("Segoe UI", 14, "bold"),
                         text_color="#B45309", fg_color="#FEF3C7", corner_radius=6).pack(side="left", ipadx=10,
                                                                                         ipady=2)

            # صف اسم العميل
            name_row = ctk.CTkFrame(card_content, fg_color="transparent")
            name_row.pack(fill="x", pady=(0, 10))
            ctk.CTkLabel(name_row, text=f"العميل: {cust_name} 👤", font=("Segoe UI", 15, "bold"),
                         text_color=TEXT_MUTED).pack(side="right")

            # خط فاصل
            ctk.CTkFrame(card_content, fg_color="#F1F5F9", height=2).pack(fill="x", pady=5)

            # صف التواريخ (مقسم لنصفين)
            data_grid = ctk.CTkFrame(card_content, fg_color="transparent")
            data_grid.pack(fill="x", pady=10)
            data_grid.grid_columnconfigure((0, 1), weight=1)

            self.create_info_box(data_grid, 0, 1, "تاريخ الإيقاف", stop_date, val_color=STOP_COLOR)
            self.create_info_box(data_grid, 0, 0, "تاريخ الإلغاء", cancel_date, val_color=FIB_GREEN)
