# -*- coding: utf-8 -*-
"""
BaseInquiryPage — الكلاس الأساسي الموحّد لكل شاشات الاستعلام.

أي شاشة استعلام جديدة يجب أن ترث من هذا الكلاس وتنفّذ فقط:

1. ``TITLE``              — عنوان الشاشة في الهيدر الأخضر.
2. ``SEARCH_PLACEHOLDER`` / ``SEARCH_LABEL`` — نصوص حقل البحث.
3. ``on_search()``        — الكويري + طريقة عرض النتيجة (كروت أو جدول).
4. (اختيارياً) ``build_search_fields()`` — حقول بحث إضافية بجانب الفرع/الحقل الأساسي.

لو الشاشة لا تحتاج فرعاً: ضع ``SHOW_BRANCH = False``.
لو الشاشة تحتاج حقول بحث إضافية: نفّذ ``build_search_fields(parent)``.
لو الشاشة لا تتبع شكل (فرع + حقل واحد) إطلاقاً: ضع ``USE_STANDARD_CHROME = False``
وابنِ الواجهة بالكامل عبر ``build()`` (يستخدم لوضع الشاشات القديمة المُرحّلة).
"""
import logging
import re
import threading

import customtkinter as ctk
import pandas as pd
from tkinter import messagebox

from gui.constants import (
    BG_MAIN, CARD_BG, BOX_BG, TEXT_DARK, TEXT_MUTED, FIB_GOLD, FIB_GREEN,
    FIB_GREEN_DARK, ERROR_RED,
)



class BaseInquiryPage(ctk.CTkFrame):
    """كلاس أساسي لكل شاشات الاستعلام — هيدر موحّد + بحث + منطقة نتائج."""

    # ---- إعدادات الشاشة (تُضبط في كل Subclass) ----
    TITLE: str = ""
    SEARCH_PLACEHOLDER: str = "رقم الحساب..."
    SEARCH_LABEL: str = "رقم الحساب:"
    SEARCH_WIDTH: int = 200
    SHOW_BRANCH: bool = True
    USE_STANDARD_CHROME: bool = True
    LOAD_BRANCHES_ON_SHOW: bool = False
    LOADING_TEXT: str = "⚡ جاري البحث في قاعدة البيانات..."
    EMPTY_MESSAGE: str = "🔍 لا توجد نتائج مطابقة"
    ERROR_TITLE: str = "❌ حدث خطأ أثناء البحث:\n"

    def __init__(self, master, app=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        # app: مرجع للنافذة الرئيسية (MainWindow) — يُستخدم للاتصال بقاعدة البيانات
        # والوصول إلى branch_mapping والـ premium select وما شابه.
        self.app = app

        if self.USE_STANDARD_CHROME:
            self.main_container = ctk.CTkFrame(self, fg_color=BG_MAIN)
            self.main_container.pack(fill="both", expand=True)
            self._build_header()
            self._build_search_area()
            self._build_results_area()

        # خطاف للشاشات التي تحتاج بناء إضافي (الوضع القياسي: الافتراضي يمرر بصمت)
        self.build()

    # =========================================================
    # 🧩 Hooks — تُنفَّذ في كل شاشة حسب الحاجة
    # =========================================================
    def build(self):
        """بناء أي عناصر إضافية بعد الواجهة القياسية. الافتراضي: لا شيء."""

    def build_search_fields(self, parent):
        """حقول بحث إضافية تُضاف إلى منطقة البحث. الافتراضي: لا شيء."""

    def on_search(self):
        """دالة البحث الأساسية — إلزامية لكل شاشة استعلام."""
        raise NotImplementedError(f"{type(self).__name__} must implement on_search()")

    def on_show(self):
        """يُستدعى تلقائياً بواسطة MainWindow.show_page بعد إظهار الشاشة."""
        if self.LOAD_BRANCHES_ON_SHOW and self.app is not None:
            self.app.nuwairy_load_branches()

    # =========================================================
    # 🎨 1. الهيدر الموحّد (أخضر + خط ذهبي + عنوان على اليمين)
    # =========================================================
    def _build_header(self):
        header = ctk.CTkFrame(self.main_container, fg_color=FIB_GREEN, height=65, corner_radius=0)
        header.pack(fill="x")
        header.pack_propagate(False)

        ctk.CTkFrame(self.main_container, fg_color=FIB_GOLD, height=4, corner_radius=0).pack(fill="x")

        title_lbl = ctk.CTkLabel(header, text=self.TITLE, font=("Segoe UI", 22, "bold"),
                                 text_color=CARD_BG)
        title_lbl.pack(side="right", padx=30, pady=15)

    # =========================================================
    # 🔍 2. منطقة البحث الموحّدة (فرع + حقل إدخال + زر بحث)
    # =========================================================
    def _build_search_area(self):
        search_frame = ctk.CTkFrame(self.main_container, fg_color=CARD_BG, corner_radius=15,
                                    border_width=1, border_color="#E2E8F0")
        search_frame.pack(fill="x", padx=20, pady=20)

        search_inner = ctk.CTkFrame(search_frame, fg_color="transparent")
        search_inner.pack(side="right", fill="y", padx=20, pady=15)

        # --- زر البحث ---
        self.btn_search = ctk.CTkButton(
            search_inner, text="🔍 بحث", font=("Segoe UI", 15, "bold"),
            fg_color=FIB_GREEN, hover_color=FIB_GREEN_DARK, text_color="white",
            width=120, height=40, corner_radius=8, command=self.on_search,
        )
        self.btn_search.pack(side="left", padx=10)

        # --- حقل الإدخال الأساسي ---
        self.search_entry = ctk.CTkEntry(
            search_inner, font=("Segoe UI", 15, "bold"), justify="center",
            placeholder_text=self.SEARCH_PLACEHOLDER,
            width=self.SEARCH_WIDTH, height=40, border_color="#CBD5E1",
        )
        self.search_entry.pack(side="left", padx=10)
        self.search_entry.bind("<Return>", lambda _event: self.on_search())

        ctk.CTkLabel(search_inner, text=self.SEARCH_LABEL, font=("Segoe UI", 14, "bold"),
                     text_color=TEXT_DARK).pack(side="left", padx=(10, 2))

        # --- أي حقول إضافية تحتاجها الشاشة ---
        self.build_search_fields(search_inner)

        # --- قائمة الفروع (Premium Select مع ComboBox كاحتياطي) ---
        if self.SHOW_BRANCH:
            self.branch_box, self.branch_combo = self._create_branch_combo(search_inner)
            self.branch_box.pack(side="left", padx=10)
            ctk.CTkLabel(search_inner, text="الفرع:", font=("Segoe UI", 14, "bold"),
                         text_color=TEXT_DARK).pack(side="left", padx=(10, 2))
            self._schedule_branch_load()

    def _create_branch_combo(self, parent):
        """ينشئ قائمة الفروع باستخدام الـ Premium Select لو متاح، وإلا CTkComboBox."""
        app = self.app
        if app is not None and hasattr(app, "_create_premium_select"):
            return app._create_premium_select(
                parent, values=["جاري التحميل..."], default="جاري التحميل...", title="اختر الفرع"
            )
        combo = ctk.CTkComboBox(parent, font=("Segoe UI", 14, "bold"), justify="right",
                                width=250, height=40, border_color="#CBD5E1")
        return combo, combo  # (box, combo) — box == combo في الوضع الاحتياطي

    def _schedule_branch_load(self, max_attempts: int = 60, interval_ms: int = 500):
        """
        تعبئة قائمة الفروع من branch_mapping.

        تحسينات عن الكود القديم:
        - لو مفيش mapping، التحميل بيبدأ مرة واحدة فقط (مش كل 500ms) — كان بيعمل
          اتصال DB + رسالة خطأ كل نص ثانية والشاشة مفتوحة.
        - الانتظار بعدها للامتلاء في الـ cache بحد أقصى max_attempts محاولة.
        """
        load_started = False

        def poll(attempt: int = 0):
            nonlocal load_started
            app = self.app
            mapping = getattr(app, "branch_mapping", None) if app is not None else None
            if mapping:
                branches = list(mapping.keys())
                self.branch_combo.configure(values=branches)
                self.branch_combo.set(branches[0])
                return
            if not load_started and app is not None and hasattr(app, "nuwairy_load_branches"):
                load_started = True
                try:
                    app.nuwairy_load_branches()
                except Exception as exc:  # لا نسمح لخطأ تحميل الفروع بإغراق الشاشة برسالت متكررة
                    logging.error("فشل تحميل الفروع: %s", exc)
                mapping = getattr(app, "branch_mapping", None)
                if mapping:
                    branches = list(mapping.keys())
                    self.branch_combo.configure(values=branches)
                    self.branch_combo.set(branches[0])
                    return
            if attempt < max_attempts:
                self.after(interval_ms, lambda: poll(attempt + 1))

        poll()

    # =========================================================
    # 📜 3. منطقة النتائج الموحّدة
    # =========================================================
    def _build_results_area(self):
        self.results_scroll = ctk.CTkScrollableFrame(self.main_container, fg_color="transparent")
        self.results_scroll.pack(fill="both", expand=True, padx=15, pady=(0, 20))

    def clear_results(self):
        for widget in self.results_scroll.winfo_children():
            widget.destroy()

    def show_loading(self, text: str | None = None):
        self.clear_results()
        ctk.CTkLabel(self.results_scroll, text=text or self.LOADING_TEXT,
                     font=("Segoe UI", 16, "bold"), text_color=FIB_GOLD).pack(pady=50)

    def show_error(self, error):
        self.clear_results()
        ctk.CTkLabel(self.results_scroll, text=f"{self.ERROR_TITLE}{error}",
                     font=("Segoe UI", 14, "bold"), text_color=ERROR_RED,
                     justify="right").pack(pady=40)

    def show_empty(self, message: str | None = None):
        self.clear_results()
        ctk.CTkLabel(self.results_scroll, text=message or self.EMPTY_MESSAGE,
                     font=("Segoe UI", 18, "bold"), text_color=TEXT_MUTED).pack(pady=60)

    # =========================================================
    # ⚙️ 4. أدوات مشتركة للبحث
    # =========================================================
    def get_engine(self):
        """إرجاع محرك قاعدة البيانات من النافذة الرئيسية (أو None)."""
        if self.app is None or not hasattr(self.app, "_get_db_connection"):
            raise RuntimeError("لم يتم العثور على دالة الاتصال بقاعدة البيانات.")
        return self.app._get_db_connection()

    def selected_branch(self):
        """إرجاع (branch_code, branch_name) أو (None, branch_name) لو الفرع غير صالح."""
        branch_name = self.branch_combo.get().strip()
        mapping = getattr(self.app, "branch_mapping", None) if self.app is not None else None
        if not mapping or branch_name not in mapping:
            return None, branch_name
        info = mapping[branch_name]
        code = info[0] if isinstance(info, (tuple, list)) else info
        return code, branch_name

    def require_input(self, entry, message: str) -> bool:
        value = entry.get().strip()
        if not value:
            messagebox.showwarning("تنبيه", message)
            entry.focus()
            return False
        return True

    def require_branch(self):
        """التحقق من اختيار فرع صالح — يُرجع (branch_code, branch_name) أو None."""
        code, name = self.selected_branch()
        if code is None:
            messagebox.showerror("خطأ", "برجاء اختيار فرع صحيح")
            return None
        return code, name

    def run_async(self, work, on_success):
        """
        تنفيذ work() في خيط منفصل ثم استدعاء on_success(result) في خيط الـ UI.
        أي استثناء داخل work() يُعرض كخطأ في منطقة النتائج بدل أن يسقط التطبيق.
        """
        def runner():
            try:
                result = work()
            except Exception as exc:
                logging.exception("خلفية البحث فشلت: %s", exc)
                self.after(0, lambda exc=exc: self.show_error(str(exc)))
                return
            self.after(0, lambda: on_success(result))

        threading.Thread(target=runner, daemon=True).start()

    # =========================================================
    # 🔤 5. أدوات مشتركة للنصوص العربية والتاريخ
    # =========================================================
    @staticmethod
    def fix_arabic_name(raw_name) -> str:
        """
        معالجة الأسماء العربية: فصل الكلمات الملتصقة (ال التعريف، السوابق و
        اللواحق، الحروف غير المتصلة). كانت مكررة 5 مرات بداخل الشاشات — تجمّعت هنا.
        """
        if pd.isna(raw_name) or not str(raw_name).strip():
            return "غير مسجل"

        text = str(raw_name).strip()
        # إزالة أي أرقام مسجلة في بداية الاسم (مثل 300083)
        text = re.sub(r'^\d+', '', text).strip()
        text = re.sub(r'\s+(يه|ية|ه|ة)\b', r'\1', text)

        previous_text = ""
        while text != previous_text:
            previous_text = text
            # فصل الحروف التي لا تتصل بما بعدها (ة، ى، ء) إذا جاء بعدها حرف
            text = re.sub(r'([ةىء])([\u0621-\u064A])', r'\1 \2', text)
            # فصل أي كلمة تلتصق بـ "ال" المعرفة
            text = re.sub(r'([\u0621-\u064A]{2,})((?:ب|ك|ف|و)?ال[\u0621-\u064A]{2,})', r'\1 \2', text)
            # فصل الأسماء المركبة المشهورة (السوابق)
            for p in ['عبد', 'ابو', 'أبو', 'ام', 'أم', 'بن', 'بنت', 'ذو', 'ذي']:
                text = re.sub(f'(?<![\u0621-\u064A])({p})(?=[\u0621-\u064A])', r'\1 ', text)
            # فصل الأسماء المركبة المشهورة (اللواحق)
            for s in ['الدين', 'مخمد', 'الله', 'الاسلام', 'الإسلام', 'الحق']:
                text = re.sub(f'(?<=[\u0621-\u064A])({s})(?![\u0621-\u064A])', r' \1', text)
            text = re.sub(r'\s+', ' ', text).strip()

        return text

    @staticmethod
    def format_date_str(raw_date) -> str:
        """تنسيق التاريخ من YYYYMMDD إلى YYYY-MM-DD (مرآة format_date_str القديمة)."""
        if pd.isna(raw_date) or not str(raw_date).strip():
            return "—"
        d_str = str(raw_date).split()[0].split('.')[0].strip()
        if len(d_str) == 8 and d_str.isdigit():
            return f"{d_str[:4]}-{d_str[4:6]}-{d_str[6:]}"
        return d_str

    @staticmethod
    def create_info_box(parent, row_idx, col_idx, title, value, val_color=TEXT_DARK, bg_color=BOX_BG):
        """كرت معلومة صغير (عنوان فوق + قيمة تحت) — كان مكرراً في كل شاشة."""
        box = ctk.CTkFrame(parent, fg_color=bg_color, corner_radius=8)
        box.grid(row=row_idx, column=col_idx, padx=5, pady=5, sticky="ew")
        ctk.CTkLabel(box, text=title, font=("Segoe UI", 12, "bold"),
                     text_color=TEXT_MUTED).pack(anchor="center", pady=(5, 0))
        ctk.CTkLabel(box, text=value, font=("Segoe UI", 15, "bold"),
                     text_color=val_color).pack(anchor="center", pady=(0, 5))
