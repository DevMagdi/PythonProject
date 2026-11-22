# -*- coding: utf-8 -*-
"""
شاشة البحث عن عميل (Customer Inquiry) — نسخة فائقة السرعة (Token-Managed + Index-Optimized).
"""
import logging
import re
import threading

import tkinter as tk
import customtkinter as ctk
import pandas as pd

from gui.constants import *
from gui.legacy_page import LegacyInquiryPage


class CustomerInquiryPage(LegacyInquiryPage):
    """شاشة البحث عن عميل (Customer Inquiry)."""
    LOAD_BRANCHES_ON_SHOW = False

    def build(self):
        parent = self
        # =========================================
        # 🚀 1. Background Caching (الفروع فقط)
        # =========================================
        self.branches_cache = {}
        self._search_token = 0  # لإلغاء الاستعلامات القديمة المتداخلة

        def preload_branches_metadata():
            try:
                engine = self._get_db_connection()
                sql = "SELECT BranchCode, BranchName FROM [dbo].[TBL_Branches] WITH (NOLOCK)"
                df = pd.read_sql(sql, engine)
                for _, row in df.iterrows():
                    code = str(row['BranchCode']).replace('.0', '').strip()
                    name = str(row['BranchName']).strip()
                    self.branches_cache[code] = name
            except Exception as e:
                logging.error(f"Branch Caching Error: {e}")

        threading.Thread(target=preload_branches_metadata, daemon=True).start()

        # =========================================
        # 🎨 2. Premium & Stable Theme Colors
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

        title_lbl = ctk.CTkLabel(header, text="نظام استعلامات كبار العملاء (VIP) الشامل", font=("Segoe UI", 22, "bold"),
                                 text_color=CARD_BG)
        title_lbl.pack(side="right", padx=30, pady=15)

        content_frame = ctk.CTkFrame(main_container, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=20, pady=20)

        right_col = ctk.CTkFrame(content_frame, fg_color=CARD_BG, corner_radius=15, border_width=1,
                                 border_color="#E2E8F0", width=380)
        right_col.pack(side="right", fill="y", expand=False)
        right_col.pack_propagate(False)

        left_col = ctk.CTkFrame(content_frame, fg_color="transparent")
        left_col.pack(side="left", fill="both", expand=True, padx=(0, 20))

        search_title = ctk.CTkLabel(right_col, text="البحث الذكي (الاسم أو الكود)", font=("Segoe UI", 17, "bold"), text_color=FIB_GREEN)
        search_title.pack(anchor="e", padx=25, pady=(20, 10))

        self.search_container = ctk.CTkFrame(right_col, fg_color=BOX_BG, corner_radius=10, border_width=1,
                                             border_color="#CBD5E1", height=45)
        self.search_container.pack(fill="x", padx=20, pady=(0, 15))
        self.search_container.pack_propagate(False)

        def clear_search_bar():
            self._search_token += 1
            self.ent_cust_search.delete(0, 'end')
            for widget in self.results_scroll.winfo_children():
                widget.destroy()
            self.lbl_cust_name.configure(text="يرجى تحديد عميل من قائمة البحث")
            for key in self.cust_fields:
                self.cust_fields[key].configure(text="—")
            self.ent_cust_search.focus()

        self.btn_clear = ctk.CTkButton(self.search_container, text="✕", width=35, height=35, corner_radius=8,
                                       fg_color="transparent", text_color="#EF4444", hover_color="#FEE2E2",
                                       font=("Segoe UI", 16, "bold"), command=clear_search_bar)
        self.btn_clear.pack(side="left", padx=5)

        self.ent_cust_search = ctk.CTkEntry(self.search_container, font=("Segoe UI", 15, "bold"), border_width=0,
                                            fg_color=BOX_BG, text_color=TEXT_DARK, justify="right",
                                            placeholder_text="اكتب 3 أحرف من الاسم أو رقم العميل...")
        self.ent_cust_search.pack(side="right", fill="both", expand=True, padx=(10, 0))

        ctk.CTkFrame(right_col, fg_color="#F1F5F9", height=2).pack(fill="x", padx=20, pady=5)

        self.results_scroll = ctk.CTkScrollableFrame(right_col, fg_color="transparent")
        self.results_scroll.pack(fill="both", expand=True, padx=10, pady=10)

        profile_card = ctk.CTkFrame(left_col, fg_color=CARD_BG, corner_radius=15, border_width=1,
                                    border_color="#E2E8F0")
        profile_card.pack(fill="both", expand=True)

        card_header = ctk.CTkFrame(profile_card, fg_color=FIB_GREEN, corner_radius=13, height=80)
        card_header.pack(fill="x", padx=4, pady=4)

        avatar_circle = ctk.CTkFrame(profile_card, width=90, height=90, corner_radius=45, fg_color=CARD_BG,
                                     border_width=2, border_color=FIB_GOLD)
        avatar_circle.place(relx=0.5, y=80, anchor="center")
        avatar_circle.pack_propagate(False)
        ctk.CTkLabel(avatar_circle, text="👑", font=("Segoe UI", 40), text_color=FIB_GOLD).pack(expand=True, pady=(0, 5))

        self.lbl_cust_name = ctk.CTkLabel(
            profile_card,
            text="يرجى تحديد عميل من قائمة البحث",
            font=("Segoe UI", 24, "bold"),
            text_color=FIB_GREEN,
            wraplength=550,
            justify="center"
        )
        self.lbl_cust_name.pack(pady=(60, 20), padx=20)

        info_grid = ctk.CTkFrame(profile_card, fg_color="transparent")
        info_grid.pack(fill="x", expand=False, padx=20, pady=(0, 20))

        info_grid.grid_columnconfigure(0, weight=1)
        info_grid.grid_columnconfigure(1, weight=1)

        self.cust_fields = {}

        def create_data_box(parent_grid, row, col, label_text, key, icon):
            box_outer = ctk.CTkFrame(parent_grid, fg_color="transparent")
            box_outer.grid(row=row, column=col, padx=10, pady=6, sticky="ew")

            box = ctk.CTkFrame(box_outer, fg_color=BOX_BG, corner_radius=12, border_width=1, border_color="#E2E8F0",
                               height=65)
            box.pack(fill="x", expand=False)
            box.pack_propagate(False)

            accent_line = ctk.CTkFrame(box, fg_color=FIB_GOLD, width=4, corner_radius=0)
            accent_line.pack(side="right", fill="y", pady=8)

            content = ctk.CTkFrame(box, fg_color="transparent")
            content.pack(side="right", fill="both", expand=True, padx=15, pady=5)

            lbl_title = ctk.CTkLabel(content, text=f"{label_text} {icon}", font=("Segoe UI", 12, "bold"),
                                     text_color=TEXT_MUTED)
            lbl_title.pack(anchor="e")

            val_lbl = ctk.CTkLabel(content, text="—", font=("Segoe UI", 15, "bold"), text_color=TEXT_DARK,
                                   justify="right")
            val_lbl.pack(anchor="e", pady=(2, 0))

            self.cust_fields[key] = val_lbl

        create_data_box(info_grid, 0, 1, "رقم العميل", "BCLNT", "🔢")
        create_data_box(info_grid, 0, 0, "الرقم القومي", "BSNO1", "🪪")
        create_data_box(info_grid, 1, 1, "الفرع المضيف", "BBR", "🏦")
        create_data_box(info_grid, 1, 0, "تاريخ الميلاد", "BDAT2", "📅")

        addr_outer = ctk.CTkFrame(info_grid, fg_color="transparent")
        addr_outer.grid(row=2, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

        addr_box = ctk.CTkFrame(addr_outer, fg_color=BOX_BG, corner_radius=12, border_width=1, border_color="#E2E8F0",
                                height=85)
        addr_box.pack(fill="x", expand=False)
        addr_box.pack_propagate(False)

        ctk.CTkFrame(addr_box, fg_color=FIB_GREEN, width=4, corner_radius=0).pack(side="right", fill="y", pady=10)

        addr_content = ctk.CTkFrame(addr_box, fg_color="transparent")
        addr_content.pack(side="right", fill="both", expand=True, padx=20, pady=10)

        ctk.CTkLabel(addr_content, text="العنوان المسجل 📍", font=("Segoe UI", 13, "bold"), text_color=TEXT_MUTED).pack(
            anchor="e")

        self.cust_fields["FULL_ADDRESS"] = ctk.CTkLabel(
            addr_content, text="—", font=("Segoe UI", 14, "bold"),
            text_color=TEXT_DARK, justify="right", wraplength=450
        )
        self.cust_fields["FULL_ADDRESS"].pack(anchor="e", pady=(5, 0))

        # =========================================
        # 🧠 5. Search Engine & Modern List (🚀 Ultra-Fast)
        # =========================================
        self._search_timer = None

        def morphological_unglue_arabic(raw_name):
            if pd.isna(raw_name) or not raw_name:
                return "—"
            text = str(raw_name)
            text = re.sub(r'[^\u0621-\u064A\s]', ' ', text)
            previous_text = ""
            while text != previous_text:
                previous_text = text
                text = re.sub(r'([ةىء])([\u0621-\u064A])', r'\1 \2', text)
                text = re.sub(r'([\u0621-\u064A]{2,})((?:ب|ك|ف|و)?ال[\u0621-\u064A]{2,})', r'\1 \2', text)
                prefixes = ['عبد', 'ابو', 'أبو', 'ام', 'أم', 'بن', 'بنت', 'ذو', 'ذي', 'صاحب', 'سمو', 'معالي', 'سعادة']
                for p in prefixes:
                    text = re.sub(f'(?<![\u0621-\u064A])({p})(?=[\u0621-\u064A])', r'\1 ', text)
                text = re.sub(r'(صاحب)(سمو)', r'\1 \2', text)
                suffixes = ['الدين', 'الله', 'الاسلام', 'الإسلام', 'الحق']
                for s in suffixes:
                    text = re.sub(f'(?<=[\u0621-\u064A])({s})(?![\u0621-\u064A])', r' \1', text)
                text = re.sub(r'\s+', ' ', text).strip()
            return text if text else str(raw_name)

        def on_search_change(event):
            if event.keysym in ("Up", "Down", "Left", "Right", "Shift_L", "Shift_R", "Control_L", "Control_R"):
                return
            if self._search_timer:
                self.after_cancel(self._search_timer)
            # مهلة 500 مللي ثانية لمنع إرسال عشرات الاستعلامات أثناء الكتابة السريعة
            self._search_timer = self.after(500, execute_search)

        def execute_search():
            raw_query = self.ent_cust_search.get().strip()
            if len(raw_query) < 3 and not raw_query.isdigit():
                for widget in self.results_scroll.winfo_children():
                    widget.destroy()
                if len(raw_query) > 0:
                    ctk.CTkLabel(
                        self.results_scroll,
                        text="✍️ اكتب 3 أحرف على الأقل للبحث...",
                        font=("Segoe UI", 13, "bold"),
                        text_color=TEXT_MUTED
                    ).pack(pady=30)
                return

            self._search_token += 1
            current_token = self._search_token

            for widget in self.results_scroll.winfo_children():
                widget.destroy()

            lbl_loading = ctk.CTkLabel(
                self.results_scroll, text="⚡ جاري البحث السريع...",
                font=("Segoe UI", 13, "bold"), text_color=FIB_GOLD
            )
            lbl_loading.pack(pady=30)

            def fetch_data():
                try:
                    engine = self._get_db_connection()

                    # 1. إذا كان المدخل أرقاماً فقط -> بحث فوري ومباشر بالـ Index على رقم العميل BCLNT
                    if raw_query.isdigit():
                        cust_variants = list({raw_query, raw_query.lstrip('0'), raw_query.zfill(6), raw_query.zfill(7)})
                        placeholders = ",".join(["?"] * len(cust_variants))
                        sql = f"""
                            SELECT TOP 50
                                BCLNT, BNAME, BSNO1, BDAT2, BBR, BADRS1, BADRS2, BADRS3, BADRS4
                            FROM [dbo].[TBL_client_name] WITH (NOLOCK)
                            WHERE BCLNT IN ({placeholders})
                        """
                        df = pd.read_sql(sql, engine, params=tuple(cust_variants))
                    else:
                        # 2. البحث بالاسم: تجهيز صيغة الكلمات المتباعدة والملتصقة معاً لضمان التطابق 100%
                        clean_words = re.sub(r'\s+', '%', raw_query.strip())
                        shrunk_words = re.sub(r'\s+', '', raw_query.strip())

                        # توحيد الهمزات والياء والتاء المربوطة
                        def normalize_sql_pattern(txt):
                            txt = re.sub(r'[يى]', '[يى]', txt)
                            txt = re.sub(r'[اأإآ]', '[اأإآ]', txt)
                            txt = re.sub(r'[هة]', '[هة]', txt)
                            txt = re.sub(r'[وؤ]', '[وؤ]', txt)
                            txt = re.sub(r'[ئ]', '[ئي]', txt)
                            return txt

                        pat_spaced = normalize_sql_pattern(clean_words)
                        pat_shrunk = normalize_sql_pattern(shrunk_words)

                        # البحث في جدول البحث وجلب البيانات عبر الـ Index (IX_TBL_client_name_BCLNT)
                        sql = """
                            SELECT TOP 50
                                orig.BCLNT, orig.BNAME, orig.BSNO1, orig.BDAT2,
                                orig.BBR, orig.BADRS1, orig.BADRS2, orig.BADRS3, orig.BADRS4
                            FROM [dbo].[TBL_Search_Names] AS search WITH (NOLOCK)
                            INNER JOIN [dbo].[TBL_client_name] AS orig WITH (NOLOCK)
                                ON search.BCLNT = orig.BCLNT
                            WHERE search.BNAME_SHRINK LIKE ?
                               OR search.BNAME_SHRINK LIKE ?
                        """
                        df = pd.read_sql(
                            sql, engine,
                            params=(f"{pat_shrunk}%", f"%{pat_spaced}%")
                        )

                    # تجاهل النتيجة إذا كتب المستخدم حروفاً جديدة أثناء الاستعلام
                    if current_token != self._search_token:
                        return

                    if not df.empty:
                        df['DISPLAY_NAME'] = df['BNAME'].apply(morphological_unglue_arabic)

                    self.after(0, lambda: update_results_ui(df, current_token))
                except Exception as e:
                    logging.error(f"Search failed for '{raw_query}': {e}")
                    if current_token == self._search_token:
                        self.after(0, lambda: update_results_ui(pd.DataFrame(), current_token))

            threading.Thread(target=fetch_data, daemon=True).start()

        def update_results_ui(df, token):
            if token != self._search_token:
                return

            for widget in self.results_scroll.winfo_children():
                widget.destroy()

            self.current_cust_df = df

            if df.empty:
                ctk.CTkLabel(self.results_scroll, text="🔍 لا توجد نتائج مطابقة", font=("Segoe UI", 14, "bold"),
                             text_color="#EF4444").pack(pady=40)
                return

            for _, row in df.iterrows():
                bclnt = str(row['BCLNT']).replace('.0', '')
                display_name = row['DISPLAY_NAME']

                row_frame = ctk.CTkFrame(self.results_scroll, fg_color="transparent")
                row_frame.pack(fill="x", pady=0)

                list_item = ctk.CTkButton(
                    row_frame,
                    text=f"{display_name}  |  كود: {bclnt} 👤",
                    font=("Segoe UI", 13, "bold"),
                    fg_color="transparent",
                    text_color=TEXT_DARK,
                    hover_color="#E2E8F0",
                    corner_radius=4,
                    border_width=0,
                    anchor="e",
                    height=38,
                    command=lambda r=row: load_customer_profile(r)
                )
                list_item.pack(fill="x", expand=True, padx=5, pady=2)

                ctk.CTkFrame(row_frame, fg_color="#E2E8F0", height=1).pack(fill="x", padx=10, pady=(0, 2))

        def load_customer_profile(cust_row):
            raw_name = str(cust_row['BNAME'])
            bclnt_code = str(cust_row['BCLNT']).replace('.0', '') if pd.notna(cust_row['BCLNT']) else "Unknown"

            self.lbl_cust_name.configure(text=cust_row.get('DISPLAY_NAME', morphological_unglue_arabic(raw_name)))

            self.cust_fields["BCLNT"].configure(text=bclnt_code if bclnt_code != "Unknown" else "—")
            self.cust_fields["BSNO1"].configure(
                text=str(cust_row['BSNO1']).replace('.0', '') if pd.notna(cust_row['BSNO1']) else "—")

            self.cust_fields["BDAT2"].configure(
                text=str(cust_row['BDAT2']).split()[0] if pd.notna(cust_row['BDAT2']) else "—")

            raw_bbr = cust_row['BBR']
            if pd.isna(raw_bbr) or str(raw_bbr).strip() in ('None', 'nan', ''):
                self.cust_fields["BBR"].configure(text="—")
            else:
                try:
                    bbr_code = str(int(float(raw_bbr))) if isinstance(raw_bbr, float) else str(raw_bbr).strip()
                except Exception:
                    bbr_code = str(raw_bbr).strip()
                branch_name = self.branches_cache.get(bbr_code, "غير معرف")
                self.cust_fields["BBR"].configure(text=f"{branch_name} ({bbr_code})")

            addr_parts = [str(cust_row[col]) for col in ['BADRS1', 'BADRS2', 'BADRS3', 'BADRS4'] if
                          pd.notna(cust_row[col]) and str(cust_row[col]).strip() not in ('None', '', 'nan')]
            full_address = " - ".join(addr_parts) if addr_parts else "غير مسجل"
            self.cust_fields["FULL_ADDRESS"].configure(text=morphological_unglue_arabic(full_address))

        self.ent_cust_search.bind("<KeyRelease>", on_search_change)
        self.ent_cust_search.bind("<Return>", lambda e: execute_search())