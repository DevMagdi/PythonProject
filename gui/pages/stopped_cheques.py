# -*- coding: utf-8 -*-
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
    PAGE_SIZE = 30

    def build(self):
        self.ent_stopped_acc = self.search_entry
        self.cmb_stopped_branch = self.branch_combo
        self.stopped_results_scroll = self.results_scroll
        self._current_df = pd.DataFrame()
        self._cust_name = "—"
        self._current_page = 0

    def on_search(self):
        acc_num = self.search_entry.get().strip()
        if not acc_num:
            messagebox.showwarning("تنبيه", "يرجى إدخال رقم الحساب أولاً")
            self.search_entry.focus()
            return

        branch = self.require_branch()
        if branch is None:
            return
        branch_code, _ = branch

        table_name = getattr(self.app, "branch_table_mapping", {}).get(str(branch_code).strip())
        if not table_name:
            messagebox.showerror("خطأ", f"لا يوجد جدول مربوط بالفرع (BranchCode={branch_code})")
            return

        self.show_loading()

        def work():
            engine = self.get_engine()
            if not engine:
                raise Exception("لم يتم العثور على دالة الاتصال بقاعدة البيانات.")

            # 1️⃣ جلب اسم العميل مرة واحدة فقط
            sql_client = f"""
                SELECT TOP 1 BNAME
                FROM {table_name} WITH (NOLOCK)
                WHERE BCLNT = ? AND BNAME IS NOT NULL AND BNAME <> ''
            """
            df_client = pd.read_sql(sql_client, engine, params=(acc_num,))
            cust_name = self.fix_arabic_name(df_client.iloc[0]['BNAME']) if not df_client.empty else "غير مدرج"

            # 2️⃣ استخدام الـ Index الجديد BCLNT_Idx للسرعة القصوى
            sql_cheques = """
                SELECT BCHNO, BDAT, BDAT1, BCOD
                FROM [dbo].[TBL_cheques] WITH (NOLOCK)
                WHERE BCLNT_Idx = ?
            """
            df_cheques = pd.read_sql(sql_cheques, engine, params=(str(acc_num),))
            return cust_name, df_cheques

        self.run_async(work, self._on_data_loaded)

    def _on_data_loaded(self, result):
        self._cust_name, self._current_df = result
        self._current_page = 0
        self._render_page()

    def _render_page(self):
        self.clear_results()

        if self._current_df.empty:
            self.show_empty()
            return

        total_records = len(self._current_df)
        total_pages = (total_records + self.PAGE_SIZE - 1) // self.PAGE_SIZE
        start_idx = self._current_page * self.PAGE_SIZE
        end_idx = min(start_idx + self.PAGE_SIZE, total_records)

        nav_bar = ctk.CTkFrame(self.results_scroll, fg_color=CARD_BG, corner_radius=10, border_width=1, border_color="#CBD5E1")
        nav_bar.pack(fill="x", padx=10, pady=(0, 10))

        ctk.CTkLabel(
            nav_bar,
            text=f"إجمالي الشيكات الموقوفة: {total_records}  |  عرض ({start_idx + 1} - {end_idx})",
            font=("Arial", 14, "bold"), text_color=FIB_GREEN
        ).pack(side="right", padx=15, pady=10)

        if total_pages > 1:
            btns_frame = ctk.CTkFrame(nav_bar, fg_color="transparent")
            btns_frame.pack(side="left", padx=15, pady=6)

            ctk.CTkButton(btns_frame, text="التالي ◀", width=80, height=30, font=("Arial", 13, "bold"),
                          fg_color=FIB_GREEN, state="normal" if self._current_page < total_pages - 1 else "disabled",
                          command=lambda: self._change_page(1)).pack(side="left", padx=4)

            ctk.CTkLabel(btns_frame, text=f"صفحة {self._current_page + 1} من {total_pages}",
                         font=("Arial", 13, "bold"), text_color=TEXT_DARK).pack(side="left", padx=8)

            ctk.CTkButton(btns_frame, text="▶ السابق", width=80, height=30, font=("Arial", 13, "bold"),
                          fg_color=FIB_GREEN, state="normal" if self._current_page > 0 else "disabled",
                          command=lambda: self._change_page(-1)).pack(side="left", padx=4)

        page_df = self._current_df.iloc[start_idx:end_idx]

        for _, row in page_df.iterrows():
            chq_no = str(row['BCHNO']).replace('.0', '') if pd.notna(row['BCHNO']) else "غير معروف"
            stop_code = str(row['BCOD']).replace('.0', '') if pd.notna(row['BCOD']) else "—"

            stop_date = str(row['BDAT']).split()[0] if pd.notna(row['BDAT']) and str(row['BDAT']).strip() else "—"
            cancel_date = str(row['BDAT1']).split()[0] if pd.notna(row['BDAT1']) and str(row['BDAT1']).strip() else "—"

            card = ctk.CTkFrame(self.results_scroll, fg_color=CARD_BG, corner_radius=12,
                                border_width=1, border_color="#E2E8F0")
            card.pack(fill="x", padx=10, pady=6)

            ctk.CTkFrame(card, fg_color=STOP_COLOR, width=5, corner_radius=0).pack(side="right", fill="y", pady=10)

            card_content = ctk.CTkFrame(card, fg_color="transparent")
            card_content.pack(fill="both", expand=True, padx=20, pady=12)

            header_row = ctk.CTkFrame(card_content, fg_color="transparent")
            header_row.pack(fill="x", pady=(0, 5))

            ctk.CTkLabel(header_row, text=f"شيك رقم : {chq_no} 🧾", font=("Arial", 17, "bold"),
                         text_color=FIB_GREEN).pack(side="right")
            ctk.CTkLabel(header_row, text=f"كود الإيقاف/الإلغاء: {stop_code} 🛑", font=("Arial", 13, "bold"),
                         text_color="#B45309", fg_color="#FEF3C7", corner_radius=6).pack(side="left", ipadx=10, ipady=2)

            name_row = ctk.CTkFrame(card_content, fg_color="transparent")
            name_row.pack(fill="x", pady=(0, 8))
            ctk.CTkLabel(name_row, text=f"العميل: {self._cust_name} 👤", font=("Arial", 14, "bold"),
                         text_color=TEXT_MUTED).pack(side="right")

            ctk.CTkFrame(card_content, fg_color="#F1F5F9", height=2).pack(fill="x", pady=4)

            data_grid = ctk.CTkFrame(card_content, fg_color="transparent")
            data_grid.pack(fill="x", pady=6)
            data_grid.grid_columnconfigure((0, 1), weight=1)

            self.create_info_box(data_grid, 0, 1, "تاريخ الإيقاف", stop_date, val_color=STOP_COLOR)
            self.create_info_box(data_grid, 0, 0, "تاريخ الإلغاء", cancel_date, val_color=FIB_GREEN)

    def _change_page(self, delta):
        self._current_page += delta
        self._render_page()