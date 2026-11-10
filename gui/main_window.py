# -*- coding: utf-8 -*-
"""
MainWindow — النافذة الرئيسية للتطبيق (كانت FGSApp في gui.py الأصلي).

المسؤوليات:
- بناء السايد بار من MENU_STRUCTURE (المصدر الوحيد لقائمة الشاشات).
- التنقل الديناميكي بين الشاشات عبر show_page() مع Lazy Loading
  (كل شاشة تُنشأ عند أول فتح لها فقط من PAGE_REGISTRY).
- إدارة الترخيص / Security Monitor / Exposure للعمليات الخلفية.
- الوصول المشترك لقاعدة البيانات (_get_db_connection) وتحميل الفروع (nuwairy_load_branches).
"""
import csv
import importlib
import json
import logging
import os
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import customtkinter as ctk
import pandas as pd
from sqlalchemy import text
from PIL import Image

from gui.constants import *          # FIB_GREEN, FIB_GOLD, COLOR_*, HAS_PANDAS, resource_path, ...
from gui.pages import PAGE_REGISTRY  # السجل المركزي للشاشات (Lazy Factory)
from utils import EnterpriseLogger
from database import DatabaseEngine

# ========================================================
# 🗂️ MENU_STRUCTURE — المصدر الوحيد لقائمة السايد بار
# إضافة شاشة جديدة = سطر هنا + سطر واحد في gui/pages/__init__.py (PAGE_REGISTRY)
# ========================================================
MENU_STRUCTURE = [
    ("📂 الحسابات العامة", [
        ("استعلام الحسابات", "nuwairy"),
        ("أستاذ الحسابات العام", "gl_inquiry"),
    ]),
    ("👥 خدمة العملاء", [
        ("بحث عن عميل", "customer"),
        ("بحث برصيد العميل", "customer_balance"),
        ("الشهادات الملغاة برقم العميل", "cancelled_certs"),
        ("الاستفسار عن التوكيلات", "mandates"),
        ("الاستفسار عن تعليمات عميل", "instructions"),
        ("الشيكات الموقوفة", "stopped_cheques"),
        ("الشيكات المرفوضة", "rejected_cheques"),
    ]),
    ("📄 التوظيف", [
        ("بحث التوظيف المحلي", "local_recruitment"),
        ("الاستفسار عن الشيكات المرتدة", "returned_cheques"),
        ("الاستفسار عن العملاء المتعثرين", "defaulted_clients"),
        ("الاستفسار عن خطابات الضمان", "guarantees"),
        ("الاستفسار عن عملاء الجدارة الائتمانية", "creditworthiness"),
        ("الاستفسار عن إجمالي التزامات عميل", "total_liabilities_inquiry"),
        ("الاستفسار عن الضمانات لعميل", "customer_collaterals_inquiry"),
        ("الاستفسار عن الكفلاء", "sponsors_inquiry"),
        ("الاستفسار عن سابقة تعاملات عميل", "client_history"),
    ]),
    ("📄 الارباح والمساهمين", [
        ("الاستفسار الأبجدي عن عملاء مساهمين", "contributing_clients"),
    ]),
    ("العلاج الطبي", [
        ("الاستفسار الأبجدي عن الموظفين واسرهم", "alphabetical_employees_families"),
        ("الاستفسار عن أرصدة العلاج الطبي للموظفين", "medical_balances_inquiry"),
        ("الاستفسار عن حركة فواتير العلاج الطبي", "medical_bills_movement"),
    ]),
    ("الاجازات والاستحقاقات", [
        ("الاستفسار عن إجازات الموظف السابقة", "previous_leaves_inquiry"),
        ("الاستفسار عن اجمالي إجازات الموظف السابقة", "leaves_movement"),
        ("الاستخقاقات - تسجيل البيانات الاساسية للموظفين", "entitlements_basic_data"),
    ]),
]


class MainWindow(ctk.CTk):
    """النافذة الرئيسية للتطبيق — السايد بار + منطقة المحتوى + التنقل."""

    def __init__(self, license_data=None):
        super().__init__()

        self.license_info = license_data

        # بيانات افتراضية لو مفيش ترخيص
        if license_data is None:
            self.lic_data = {
                "active": False,
                "mid": "UNKNOWN",
                "expiry": "N/A"
            }
        else:
            self.lic_data = license_data

        # 📝 1. تهيئة دفتر التسجيل أولاً
        self.sys_logger = EnterpriseLogger()
        self.sys_logger.log("✅ تم فتح البرنامج وبدء جلسة جديدة.")

        # Window Setup
        self.title("Faisal Islamic Bank | Data Integration Hub")
        self.geometry("1200x800")
        self.configure(fg_color=COLOR_BG)

        # ربط دالة الإغلاق الآمن
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        try:
            self.iconbitmap(resource_path("logo.ico"))
        except Exception:
            pass

        # 💡 تهيئة المتغيرات الأساسية
        self.folder_path_var = tk.StringVar()
        self.server_val = ""
        self.db_val = ""
        self.user_val = ""  # لضمان عدم وجود خطأ لو الدالة استدعتهم
        self.pass_val = ""

        # 🔥 التعديل السحري: تحميل الإعدادات فوراً قبل بناء الواجهة
        try:
            self.load_config_from_json()
        except Exception as e:
            self.sys_logger.log(f"⚠️ تنبيه: لم يتم تحميل ملف الإعدادات عند البداية: {e}", "WARNING")

        # Grid Layout (RTL): العمود 0 (اليسار) يتمدد للشاشات — العمود 1 (اليمين) للسايد بار
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0)
        self.grid_rowconfigure(0, weight=1)

        # 2. نظام الصفحات — Lazy Loading: لا تُنشأ أي شاشة هنا!
        self.pages = {}          # page_key -> page instance (يُملأ تدريجياً)
        self.nav_buttons = {}    # page_key -> زر السايد بار الخاص بها
        self._setup_content_area()

        # 3. Setup Sidebar
        self.setup_sidebar()

        # 4. تشغيل المراقب الأمني لو الرخصة فعالة
        if self.lic_data.get("active"):
            self.start_security_monitor()

            # Open Account Inquiry instead
            self.show_page("nuwairy")

    def _setup_content_area(self):
        """الحاوية الرئيسية اللي بتتعرض فيها الشاشات (تُنشأ مرة واحدة فقط)."""
        self.content_area = ctk.CTkFrame(self, fg_color="transparent")
        self.content_area.grid(row=0, column=0, sticky="nsew", padx=30, pady=30)

    # ========================================================
    # 🧭 التنقل الديناميكي (Lazy Loading) — لا توجد أي قوائم يدوية هنا
    # ========================================================
    def show_page(self, name):
        """إظهار شاشة بالاسم — إنشاء عند أول فتح فقط.

        - يُخفي كل الشاشات المُنشأة.
        - ينشئ الشاشة المطلوبة من PAGE_REGISTRY عند أول استدعاء.
        - يُبرز زرها ويستدعي on_show() (تحميل الفروع مثلاً).
        """
        if hasattr(self, 'sys_logger'):
            self.sys_logger.log(f"🔄 المستخدم انتقل إلى شاشة: {name}")

        # 1. إخفاء كل الصفحات الحالية
        for page in self.pages.values():
            page.pack_forget()

        # 2. إنشاء الصفحة عند أول فتح فقط (Lazy Loading)
        if name not in self.pages:
            page = self._create_page(name)
            if page is None:
                return  # الخطأ اتسجّل في الـ log وفي نافذة تنبيه
            self.pages[name] = page

        # 3. إظهار الشاشة + إبراز زرها
        page = self.pages[name]
        page.pack(fill="both", expand=True)
        self._highlight_button(name)

        # 4. hook تلقائي لكل شاشة (إعادة تحميل الفروع مثلاً)
        try:
            page.on_show()
        except Exception as exc:
            if hasattr(self, 'sys_logger'):
                self.sys_logger.log(f"⚠️ on_show لشاشة {name} فشلت: {exc}", "WARNING")

    def _create_page(self, page_key):
        """Factory: ينشئ الشاشة من PAGE_REGISTRY بالاستيراد الكسول."""
        spec = PAGE_REGISTRY.get(page_key)
        if spec is None:
            logging.error("شاشة غير معروفة في PAGE_REGISTRY: %s", page_key)
            if hasattr(self, 'sys_logger'):
                self.sys_logger.log(f"❌ شاشة غير معروفة: {page_key}", "ERROR")
            return None

        module_path, class_name = spec.split(":")
        try:
            module = importlib.import_module(module_path)
            page_class = getattr(module, class_name)
            return page_class(self.content_area, app=self)
        except Exception as exc:
            logging.exception("فشل إنشاء الشاشة %s", page_key)
            messagebox.showerror("خطأ", f"تعذر فتح الشاشة [{page_key}]:\n{exc}")
            return None

    def _page_attr(self, page_key, attr, default=None):
        """Attribute من داخل صفحة — يرجع default لو الصفحة لم تُنشأ بعد (Lazy Loading)."""
        pages = getattr(self, "pages", None)  # قد يستدعى قبل إنشاء self.pages أثناء الإقلاع
        page = pages.get(page_key) if pages else None
        return getattr(page, attr, default) if page is not None else default

    def _ui(self, page_key, name, default=None):
        """Resolve a UI element that may live on MainWindow or on a lazily-created page.

        شاشات dashboard و config_page كانت جزءًا من FGSApp الأصلي، وزرار/خانات
        التحكم بتاعتها انتقلت معها للـ page instance بعد التقسيم. هذا الـ helper
        يجمع بين المصدرين: يحاول أولًا على النافذة الرئيسية ثم على الصفحة.
        """
        if hasattr(self, name):
            value = getattr(self, name)
            if value is not None:
                return value
        return self._page_attr(page_key, name, default)

    def _highlight_button(self, active_key):
        """تلوين زر الشاشة النشطة في السايد بار وإرجاع الباقي للوضع الطبيعي."""
        for key, button in self.nav_buttons.items():
            if key == active_key:
                button.configure(fg_color=FIB_GREEN, text_color="white")
            else:
                button.configure(fg_color="transparent", text_color=COLOR_TEXT_MAIN)

    # ========================================================
    # 🧭 السايد بار — يُبنى بالكامل من MENU_STRUCTURE
    # ========================================================
    def setup_sidebar(self):
        # 1️⃣ عرض السايد بار 280
        self.sidebar = ctk.CTkFrame(self, width=280, corner_radius=0, fg_color=COLOR_WHITE)
        self.sidebar.grid(row=0, column=1, sticky="nsew")
        self.sidebar.grid_propagate(False)

        self.sidebar.grid_rowconfigure(2, weight=1)

        # 1. Logo Area
        logo_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo_frame.grid(row=0, column=0, pady=(30, 20), padx=10, sticky="ew")

        try:
            img_path = resource_path("logo.png")
            self.logo_image = ctk.CTkImage(
                light_image=Image.open(img_path),
                dark_image=Image.open(img_path),
                size=(160, 45)
            )
            ctk.CTkLabel(logo_frame, text="", image=self.logo_image).pack()
        except Exception:
            ctk.CTkLabel(logo_frame, text="FIB SYSTEM", font=("Arial", 20, "bold"), text_color=FIB_GREEN).pack()

        ctk.CTkFrame(self.sidebar, height=2, fg_color=FIB_GOLD).grid(row=1, column=0, sticky="ew", padx=15,
                                                                     pady=(0, 10))

        # ==========================================
        # 2. Menu Buttons — المصدر الوحيد: MENU_STRUCTURE
        # ==========================================
        self.menu_container = ctk.CTkScrollableFrame(self.sidebar, fg_color="transparent")
        self.menu_container.grid(row=2, column=0, sticky="nsew", padx=0, pady=0)

        self.sub_menus = {}

        for category, items in MENU_STRUCTURE:
            self.create_collapsible_menu(category, items)

        # ==========================================
        # 🆔 ACTIVATION & LICENSE CARD
        # ==========================================
        status_color = FIB_GREEN if getattr(self, 'lic_data', {}).get("active") else COLOR_RED_ALERT
        status_text = "ACTIVE LICENSE" if getattr(self, 'lic_data', {}).get("active") else "INACTIVE / DEMO"

        info_card = ctk.CTkFrame(self.sidebar, fg_color="#F8F9FA", corner_radius=10, border_width=1,
                                 border_color="#E0E0E0")
        info_card.grid(row=11, column=0, padx=10, pady=(10, 5), sticky="ew")

        status_row = ctk.CTkFrame(info_card, fg_color="transparent")
        status_row.pack(fill="x", padx=10, pady=8)

        self.lbl_dot = ctk.CTkLabel(status_row, text="●", font=("Arial", 16), text_color=status_color)
        self.lbl_dot.pack(side="left")
        self.lbl_status_text = ctk.CTkLabel(status_row, text=status_text, font=("Segoe UI", 10, "bold"),
                                            text_color=status_color)
        self.lbl_status_text.pack(side="left", padx=5)

        info_card.bind("<Double-1>", lambda e: self.show_admin_activation_popup())
        status_row.bind("<Double-1>", lambda e: self.show_admin_activation_popup())
        self.lbl_status_text.bind("<Double-1>", lambda e: self.show_admin_activation_popup())
        self.lbl_dot.bind("<Double-1>", lambda e: self.show_admin_activation_popup())

        # Footer
        ctk.CTkLabel(self.sidebar, text="v2.1 Enterprise © FGS", font=("Arial", 9), text_color="#CCC").grid(
            row=12, column=0, pady=(0, 10)
        )

    def create_collapsible_menu(self, category_text, items):
        # حاوية رئيسية لكل قسم
        category_container = ctk.CTkFrame(self.menu_container, fg_color="transparent")
        category_container.pack(fill="x", pady=2, padx=5)

        sub_frame = ctk.CTkFrame(category_container, fg_color="transparent")
        self.sub_menus[category_text] = sub_frame

        # الزرار الرئيسي
        main_btn = ctk.CTkButton(
            category_container,
            text=f"{category_text} ◀",
            font=("Segoe UI", 13, "bold"),
            anchor="e",
            fg_color="#E2E8F0", text_color="#333333", hover_color="#CBD5E1",
            height=34, corner_radius=6,
            command=lambda c=category_text: self.toggle_menu(c)
        )
        main_btn.pack(fill="x", padx=0, pady=2)
        self.sub_menus[f"{category_text}_btn"] = main_btn

        # إنشاء الزراير الفرعية للشاشات + تسجيلها في nav_buttons للإبراز/الإخفاء
        for text, page_name in items:
            sub_btn = ctk.CTkButton(
                sub_frame,
                text=text,
                font=("Segoe UI", 11, "bold"),
                anchor="e",  # المحاذاة لليمين تماماً
                fg_color="transparent", text_color="#475569", hover_color="#F0F9F4",
                height=30, corner_radius=6,
                command=lambda p=page_name: self.show_page(p)
            )
            sub_btn.pack(fill="x", padx=(0, 5), pady=1)

            # السجل المركزي للأزرار — لا حاجة لsetattr(self, f"btn_{page_name}")
            self.nav_buttons[page_name] = sub_btn


    def on_closing(self):
        """دالة الإغلاق الآمن لقتل أي عمليات في الخلفية"""
        self.sys_logger.log("🛑 جاري إغلاق النظام...")
        self.destroy()
        sys.exit(0)  # يغلق كافة الـ Threads المتبقية

    def system_startup(self):
        """Loads config and updates UI immediately"""
        self.load_config_from_json()
        self.refresh_dashboard_data()

    def refresh_dashboard_data(self):
        """Refreshes all data in the background"""
        if not self.lic_data.get("active"):
            return
        threading.Thread(target=self.load_history_data, daemon=True).start()

    def toggle_menu(self, category):
        sub_frame = self.sub_menus[category]
        btn = self.sub_menus[f"{category}_btn"]
        current_text = btn.cget("text")
    
        if sub_frame.winfo_ismapped():
            sub_frame.pack_forget()
            btn.configure(text=current_text.replace("▼", "◀"))
        else:
            sub_frame.pack(fill="x")
            btn.configure(text=current_text.replace("◀", "▼"))

    def show_admin_activation_popup(self):
        """نافذة سرية للمدير لتفعيل الرخصة بتفتح بالدبل كليك"""
        popup = ctk.CTkToplevel(self)
        popup.title("Admin License Manager - Secret")
        popup.geometry("450x250")
        popup.attributes("-topmost", True)
        popup.resizable(False, False)
    
        ctk.CTkLabel(popup, text="Enter New Activation Key:", font=("Segoe UI", 14, "bold")).pack(pady=(25, 10))
    
        ent_key = ctk.CTkEntry(popup, width=350, justify="center", font=("Consolas", 12))
        ent_key.pack(pady=10)
    
        mid = getattr(self, 'lic_data', {}).get("mid", "UNKNOWN")
        ctk.CTkLabel(popup, text=f"Machine ID: {mid}", font=("Segoe UI", 10), text_color="gray").pack()
    
        def do_activate():
            key_input = ent_key.get().strip()
            if not key_input:
                messagebox.showwarning("تنبيه", "Please paste the key first.")
                return
    
            self.ent_lic_key = ent_key
            self.on_activate_click()
    
            if hasattr(self, 'lic_data') and self.lic_data.get("active"):
                self.lbl_dot.configure(text_color="#00563B")
                self.lbl_status_text.configure(text="ACTIVE LICENSE", text_color="#00563B")
                popup.destroy()
    
        ctk.CTkButton(
            popup,
            text="Verify & Activate",
            fg_color="#C5A059",
            hover_color="#B58B00",
            command=do_activate
        ).pack(pady=20)

    def style_treeview(self):
        style = ttk.Style()
        style.theme_use("clam")
    
        # ✅ تعيين الألوان الداكنة للجدول (Dark Mode for Data)
        style.configure("Treeview",
                        background=COLOR_DARK_BG,
                        foreground=COLOR_TEXT_LITE,
                        fieldbackground=COLOR_DARK_BG,
                        rowheight=30,
                        font=("Segoe UI", 10))
    
        # الهيدر يفضل يكون فاتح شوية عشان التباين
        style.configure("Treeview.Heading",
                        background="#444",
                        foreground="white",
                        font=("Segoe UI", 10, "bold"),
                        relief="flat")
    
        style.map("Treeview", background=[('selected', FIB_GOLD)], foreground=[('selected', 'white')])

    def style_nuwairy_treeview(self):
        style = ttk.Style()
        style.theme_use("clam")
    
        # جدول أبيض حديث
        style.configure(
            "Nuwairy.Treeview",
            background="#FFFFFF",
            foreground="#111827",
            fieldbackground="#FFFFFF",
            rowheight=34,
            font=("Segoe UI", 10),
            borderwidth=0
        )
    
        # هيدر أنيق
        style.configure(
            "Nuwairy.Treeview.Heading",
            background="#F3F4F6",
            foreground="#111827",
            font=("Segoe UI", 10, "bold"),
            relief="flat"
        )
    
        style.map(
            "Nuwairy.Treeview",
            background=[("selected", "#DDEFE8")],
            foreground=[("selected", "#111827")]
        )

    def _create_premium_select(self, parent, values, default, title, width_popup=420, height_popup=360):
        class _PremiumSelectProxy:
            def __init__(self, outer, box, var):
                self._outer = outer
                self._box = box
                self._var = var
                self._values = [str(x) for x in (values or [])]
                self._title = title
                self._w = width_popup
                self._h = height_popup
    
            def get(self):
                return self._var.get()
    
            def set(self, v):
                self._var.set(str(v))
    
            def configure(self, values=None, **kwargs):
                if values is not None:
                    self._values = [str(x) for x in values]
    
            @property
            def _values_list(self):
                return self._values
    
            @property
            def _anchor(self):
                return self._box
    
        box = ctk.CTkFrame(parent, corner_radius=10, fg_color=FIB_GREEN)
        box.grid_columnconfigure(0, weight=1)
    
        var = ctk.StringVar(value=str(default))
    
        lbl = ctk.CTkLabel(box, textvariable=var, text_color="white", anchor="e")
        lbl.grid(row=0, column=0, sticky="ew", padx=(12, 6), pady=8)
    
        def open_dd():
            proxy = box._proxy  # type: ignore
            self._premium_dropdown(
                anchor_widget=proxy._anchor,
                values=proxy._values_list,
                on_select=lambda v: proxy.set(v),
                title=proxy._title,
                width=proxy._w,
                height=proxy._h
            )
    
        btn = ctk.CTkButton(
            box, text="▾", width=44,
            fg_color="#0E6B44",
            hover_color="#0B5C3A",
            command=open_dd
        )
        btn.grid(row=0, column=1, padx=(0, 8), pady=6)
    
        box.bind("<Button-1>", lambda e: open_dd())
        lbl.bind("<Button-1>", lambda e: open_dd())
    
        proxy = _PremiumSelectProxy(self, box, var)
        box._proxy = proxy  # type: ignore
        return box, proxy

    def _premium_dropdown(self, anchor_widget, values, on_select,
                          title="اختر", width=420, height=420):
    
        # Theme (same app palette)
        GREEN = globals().get("FIB_GREEN", "#0B5C3A")
        GOLD = globals().get("FIB_GOLD", "#B08D2D")
        WHITE = "#FFFFFF"
        TEXT = "#111827"
        MUTED = "#6B7280"
        BG = "#F7F7F7"
        LINE = "#E6E8EB"
        HOV = "#F3F4F6"
    
        values = [str(v) for v in (values or [])]
    
        # Close any existing dropdown
        if getattr(self, "_active_premium_dd", None):
            try:
                self._active_premium_dd.destroy()
            except:
                pass
            self._active_premium_dd = None
    
        top = ctk.CTkToplevel(self)
        self._active_premium_dd = top
    
        # Toplevel "dropdown" behavior
        top.overrideredirect(True)  # ✅ removes windows title-bar
        top.attributes("-topmost", True)  # ✅ stays above
        try:
            top.configure(fg_color="transparent")
        except:
            pass
    
        # Position right under anchor
        try:
            ax = anchor_widget.winfo_rootx()
            ay = anchor_widget.winfo_rooty()
            ah = anchor_widget.winfo_height()
            top.geometry(f"{width}x{height}+{ax}+{ay + ah + 6}")
        except:
            top.geometry(f"{width}x{height}")
    
        # Close helpers
        def close():
            try:
                top.destroy()
            except:
                pass
            self._active_premium_dd = None
    
        def choose(v):
            try:
                on_select(v)
            finally:
                close()
    
        # Close on focus out / click outside
        top.bind("<Escape>", lambda e: close())
        top.bind("<FocusOut>", lambda e: close())
    
        # Outer card
        outer = ctk.CTkFrame(top, corner_radius=14, fg_color=WHITE, border_width=1, border_color=LINE)
        outer.pack(fill="both", expand=True)
    
        # Header bar (premium)
        head = ctk.CTkFrame(outer, corner_radius=14, fg_color=GREEN)
        head.pack(fill="x")
    
        head.grid_columnconfigure(0, weight=1)
    
        lbl = ctk.CTkLabel(head, text=title, font=("Segoe UI", 12, "bold"), text_color="white", anchor="w")
        lbl.grid(row=0, column=0, sticky="w", padx=12, pady=10)
    
        btn_x = ctk.CTkButton(
            head, text="✕", width=36, height=28,
            fg_color="transparent", hover_color="#0E6B44",
            text_color="white", font=("Segoe UI", 12, "bold"),
            command=close
        )
        btn_x.grid(row=0, column=1, sticky="e", padx=10, pady=8)
    
        # Search row
        search_row = ctk.CTkFrame(outer, fg_color=BG, corner_radius=12)
        search_row.pack(fill="x", padx=12, pady=12)
    
        qvar = ctk.StringVar(value="")
    
        ent = ctk.CTkEntry(
            search_row, textvariable=qvar, height=38,
            corner_radius=10,
            border_width=1, border_color=LINE,
            fg_color=WHITE,
            placeholder_text="ابحث عن الفرع..."
        )
        ent.pack(side="left", fill="x", expand=True, padx=(10, 8), pady=10)
        ent.focus_set()
    
        def clear_q():
            qvar.set("")
            ent.focus_set()
    
        btn_clear = ctk.CTkButton(
            search_row, text="مسح", width=80, height=38,
            fg_color=GOLD, hover_color="#B78F38",
            text_color="white",
            font=("Segoe UI", 11, "bold"),
            corner_radius=10,
            command=clear_q
        )
        btn_clear.pack(side="left", padx=(0, 10), pady=10)
    
        # Table header
        th = ctk.CTkFrame(outer, fg_color=WHITE)
        th.pack(fill="x", padx=12)
    
        ctk.CTkLabel(th, text="اسم الفرع", font=("Segoe UI", 11, "bold"), text_color=TEXT, anchor="e").pack(
            side="right", padx=10, pady=(2, 6)
        )
    
        # List area
        sc = ctk.CTkScrollableFrame(
            outer, corner_radius=12,
            fg_color=WHITE,
            border_width=1, border_color=LINE
        )
        sc.pack(fill="both", expand=True, padx=12, pady=(0, 12))
    
        btns = []
        selected_var = ctk.StringVar(value="")
    
        def rebuild(items):
            for w in btns:
                try:
                    w.destroy()
                except:
                    pass
            btns.clear()
    
            if not items:
                empty = ctk.CTkLabel(sc, text="لا توجد نتائج", font=("Segoe UI", 11), text_color=MUTED)
                empty.pack(fill="x", pady=10)
                btns.append(empty)
                return
    
            for v in items:
                row = ctk.CTkFrame(sc, fg_color=WHITE, corner_radius=10)
                row.pack(fill="x", pady=4)
    
                def on_enter(_e, rr=row):
                    rr.configure(fg_color=HOV)
    
                def on_leave(_e, rr=row, vv=v):
                    rr.configure(fg_color=("#EAF2EE" if selected_var.get() == vv else WHITE))
    
                def do_select(vv=v):
                    selected_var.set(vv)
                    # refresh highlight quickly
                    for ww in btns:
                        if isinstance(ww, ctk.CTkFrame):
                            ww.configure(fg_color=WHITE)
                    row.configure(fg_color="#EAF2EE")
                    choose(vv)
    
                row.bind("<Enter>", on_enter)
                row.bind("<Leave>", on_leave)
                row.bind("<Button-1>", lambda e, vv=v: do_select(vv))
    
                # Right aligned text
                lab = ctk.CTkLabel(row, text=v, font=("Segoe UI", 12), text_color=TEXT, anchor="e")
                lab.pack(fill="x", padx=12, pady=10)
                lab.bind("<Button-1>", lambda e, vv=v: do_select(vv))
                lab.bind("<Enter>", on_enter)
                lab.bind("<Leave>", on_leave)
    
                btns.append(row)
    
        def apply_filter(*_):
            q = (qvar.get() or "").strip().lower()
            if not q:
                rebuild(values)
                return
            rebuild([v for v in values if q in v.lower()])
    
        qvar.trace_add("write", apply_filter)
        rebuild(values)

    def _get_db_connection(self):
        """إنشاء محرك قاعدة البيانات بالاعتماد على الذاكرة لحماية نسخة سيتركس"""
    
        # 1. الجلب الآمن من الذاكرة (بدلاً من الشاشة)
        server = getattr(self, 'server_val', '')
        db = getattr(self, 'db_val', '')
        user = getattr(self, 'user_val', '')
        pwd = getattr(self, 'pass_val', '')
    
        # 2. منع الاتصال لو السيرفر فاضي (عشان نلغي رسالة Windows Auth الفاضية)
        if not server or server.strip() == "":
            return None
        db_instance = DatabaseEngine(
            server=server,
            database=db,
            user=user,
            password=pwd,
            logger=getattr(self, 'sys_logger', None)  # عشان اللوج يظهر في الشاشة والملف
        )
    
        return db_instance.engine

    def _date_to_yyyymmdd(self, s: str) -> str:
        """
        يحول:
        - 2020-07-15 -> 20200715
        - 20200715 -> 20200715
        ويرجع "" لو فاضي
        ويرمي ValueError لو صيغة غلط
        """
        s = (s or "").strip()
        if not s:
            return ""
    
        s = s.replace("-", "").replace("/", "").replace(".", "")
        if len(s) != 8 or not s.isdigit():
            raise ValueError("صيغة التاريخ غير صحيحة. استخدم YYYY-MM-DD أو YYYYMMDD")
        return s

    def nuwairy_load_branches(self):
        """تحميل الفروع + ربط كل فرع باسم جدول الحركات بتاعه ديناميكيًا من dbo.TBL_Branches"""
    
        # مع Lazy Loading أصبحت قوائم الفروع ملكاً لشاشاتها عند إنشائها —
        # الوصول إليها يتم بأمان عبر _page_attr (يرجع None لو الشاشة لم تُنشأ بعد).
        cmb_nuwairy = self._page_attr("nuwairy", "cmb_branch")
        combo_gl = self._page_attr("gl_inquiry", "combo_gl_branch")
    
        def _nuwairy_set(values, current):
            if cmb_nuwairy is not None:
                cmb_nuwairy.configure(values=values)
                cmb_nuwairy.set(current)
    
        def _gl_set(values, current):
            if combo_gl is not None:
                combo_gl.configure(values=values)
                combo_gl.set(current)
    
        try:
            engine = self._get_db_connection()
    
            query = """
                    SELECT BranchCode, BranchName, TableName
                    FROM [dbo].[TBL_Branches]
                    WHERE BranchName IS NOT NULL
                    """
            df = pd.read_sql(query, engine)
    
            if df.empty:
                _nuwairy_set(["- لا توجد فروع -"], "- لا توجد فروع -")
    
                # تحديث حقل الأستاذ العام في حالة عدم وجود بيانات
                _gl_set(["- لا توجد فروع -"], "- لا توجد فروع -")
    
                self.branch_mapping = {}
                self.branch_table_mapping = {}
                return
    
            # 🔥 التعديل الأول: استخدام fillna("") لتحويل أي NULL إلى نص فارغ قبل الـ astype
            df["BranchCode"] = df["BranchCode"].fillna("").astype(str).str.strip()
            df["BranchName"] = df["BranchName"].fillna("").astype(str).str.strip()
            df["TableName"] = df["TableName"].fillna("").astype(str).str.strip()
    
            self.branch_mapping = dict(zip(df["BranchName"], df["BranchCode"]))
    
            self.branch_table_mapping = {}
            for _, row in df.iterrows():
                code = row["BranchCode"]
                tname = row["TableName"]
    
                # 🔥 التعديل الثاني: استخدام str() وتوسيع الفلتر ليشمل nan
                if not tname or str(tname).lower() in ["null", "nan", ""]:
                    continue
    
                tname_clean = str(tname).replace("[dbo].", "").replace("dbo.", "").strip()
                tname_clean = tname_clean.strip("[]")
                self.branch_table_mapping[code] = f"[dbo].[{tname_clean}]"
    
            branches_list = list(self.branch_mapping.keys())
            if branches_list:
                _nuwairy_set(branches_list, branches_list[0])
    
                # تحديث حقل الأستاذ العام بالبيانات الصحيحة
                _gl_set(branches_list, branches_list[0])
            else:
                _nuwairy_set(["- لا توجد فروع -"], "- لا توجد فروع -")
    
                # تحديث حقل الأستاذ العام لو القائمة فاضية
                _gl_set(["- لا توجد فروع -"], "- لا توجد فروع -")
    
                self.branch_mapping = {}
                self.branch_table_mapping = {}
    
        except Exception as e:
            # رسالة أوضح للمستخدم
            err = str(e)
            _nuwairy_set(["- خطأ في الاتصال بالداتا -"], "- خطأ في الاتصال بالداتا -")
    
            # إظهار الخطأ في حقل الأستاذ العام
            _gl_set(["- خطأ في الاتصال -"], "- خطأ في الاتصال -")
    
            self.branch_mapping = {}
            self.branch_table_mapping = {}
    
            if hasattr(self, 'sys_logger'):
                self.sys_logger.log(f"❌ خطأ أثناء تحميل الفروع من قاعدة البيانات: {e}", "ERROR")
    
            if "08001" in err or "Login timeout expired" in err or "could not open a connection" in err.lower():
                messagebox.showerror(
                    "خطأ اتصال",
                    "الاتصال بـ SQL Server فشل.\n\n"
                    "راجع Configuration:\n"
                    "- Server Host Address (اسم السيرفر/الـ Instance صحيح)\n"
                    "- SQL Server شغال\n"
                    "- جرّب Test Connection\n\n"
                    f"تفاصيل: {err}"
                )
            else:
                messagebox.showerror("خطأ", f"حدث خطأ أثناء تحميل الفروع:\n{err}")

    def start_security_monitor(self):
        """
        مراقب ذكي: يتحقق من الكود الموجود في البرنامج حالياً ضد البلاك ليست
        بدون الحاجة لملفات خارجية
        """
        self.is_locked_mode = False
    
        def _monitor_loop():
            try:
                from license_guard import LicenseGuard
            except:
                return
    
            while True:
                time.sleep(10)  # فحص كل 10 ثواني
    
                try:
                    # 1. هات الكود الحالي من الواجهة (لو متاح)
                    # بنستخدم invoke من الـ main thread عشان tkinter thread safety
                    # بس للتبسيط هنا هنعتمد على المتغير المحفوظ self.lic_data
    
                    current_key = self.lic_data.get("key_str", "")
    
                    if not current_key and self.lic_data["active"]:
                        # لو البرنامج مفعل بس مفيش كود (حالة غريبة)
                        self.is_locked_mode = True
                        self.after(0, self.activate_lockdown_mode)
                        continue
    
                    # 2. الفحص الأمني (Blacklist Check)
                    mid = self.lic_data["mid"]
    
                    # لو الكود محظور أونلاين
                    if LicenseGuard.check_online_blacklist(mid):
                        if not self.is_locked_mode:
                            print("🔒 BLOCKED BY SERVER")
                            self.is_locked_mode = True
                            self.after(0, self.activate_lockdown_mode)
    
                    # لو كل حاجة تمام وكان مقفول -> افتحه
                    elif self.is_locked_mode and current_key:
                        self.is_locked_mode = False
                        self.after(0, self.deactivate_lockdown_mode)
    
                except Exception:
                    # مراقب أمني — أي خطأ عابر لا يوقف الحلقة
                    continue
    
        threading.Thread(target=_monitor_loop, daemon=True).start()

    def activate_lockdown_mode(self):
        """تحويل البرنامج لوضع القفل الشامل"""
        # 1. إظهار رسالة تحذير (اختياري)
        # messagebox.showwarning("ALERT", "⚠️ License Revoked or File Missing.")
    
        # 2. تغيير حالة الكارت في السايد بار للأحمر 🔴
        if hasattr(self, 'lbl_dot'):
            self.lbl_dot.configure(text_color=COLOR_RED_ALERT)
    
        if hasattr(self, 'lbl_status_text'):
            self.lbl_status_text.configure(text="REVOKED / BLOCKED", text_color=COLOR_RED_ALERT)
    
        # 3. قفل زر التشغيل الرئيسي (على شاشة الداشبورد لو انفتحت)
        btn_run = self._ui("dashboard", "btn_run")
        if btn_run is not None:
            btn_run.configure(state="disabled", text="🚫 BLOCKED", fg_color="gray")
    
        # 4. قفل باقي الزراير (الإعدادات والتقارير)
        btn_save = self._ui("config_page", "btn_save")
        btn_test = self._ui("config_page", "btn_test")
        btn_export = self._ui("reports", "btn_export")
        if btn_save is not None: btn_save.configure(state="disabled")
        if btn_test is not None: btn_test.configure(state="disabled")
        if btn_export is not None: btn_export.configure(state="disabled", fg_color="gray")

    def deactivate_lockdown_mode(self):
        """إعادة تفعيل البرنامج بالكامل"""
        # 1. رسالة ترحيب (اختياري)
        # messagebox.showinfo("RESTORED", "✅ License Restored Successfully.")
    
        # 2. إرجاع حالة الكارت للأخضر 🟢
        if hasattr(self, 'lbl_dot'):
            self.lbl_dot.configure(text_color=FIB_GREEN)
    
        if hasattr(self, 'lbl_status_text'):
            self.lbl_status_text.configure(text="ACTIVE LICENSE", text_color=FIB_GREEN)
    
        # 3. تشغيل زر التشغيل الرئيسي (على شاشة الداشبورد لو انفتحت)
        btn_run = self._ui("dashboard", "btn_run")
        if btn_run is not None:
            btn_run.configure(state="normal", text="🚀 START PROCESS", fg_color=FIB_GREEN)
    
        # 4. تشغيل باقي الزراير
        btn_save = self._ui("config_page", "btn_save")
        btn_test = self._ui("config_page", "btn_test")
        btn_export = self._ui("reports", "btn_export")
        if btn_save is not None: btn_save.configure(state="normal")
        if btn_test is not None: btn_test.configure(state="normal")
        if btn_export is not None: btn_export.configure(state="normal", fg_color=FIB_GOLD)

    def on_activate_click(self):
        """
        دالة بتاخد الكود من الـ Entry وتتحقق منه وتفعل البرنامج
        """
        key_input = self.ent_lic_key.get().strip()
    
        if not key_input:
            messagebox.showwarning("Empty", "Please paste the activation key first.")
            return
    
        try:
            from license_guard import LicenseGuard
    
            # التحقق من الكود المدخل
            is_valid, msg = LicenseGuard.validate_license_string(key_input)
    
            if is_valid:
                # 1. تحديث الحالة في الواجهة
                self.lic_data["active"] = True
                self.lic_data["key_str"] = key_input  # نحفظ الكود في الذاكرة
    
                self.deactivate_lockdown_mode()  # فتح البرنامج
                messagebox.showinfo("Activated", f"License Activated Successfully!\n{msg}")
    
                # 2. حفظ الكود في ملف الكونفيج عشان يفضل شغال المرة الجاية
                self.save_config(silent=True)
    
                # 3. تشغيل المراقبة لو مكنتش شغالة
                self.start_security_monitor()
            else:
                self.activate_lockdown_mode()
                messagebox.showerror("Invalid", f"Activation Failed:\n{msg}")
    
        except ImportError:
            messagebox.showerror("Error", "License Guard module missing.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _f(self, size=12, weight="normal"):
        # safe font tuple for CTk / Tk
        if weight not in ("normal", "bold", "italic"):
            weight = "normal"
        return ("Segoe UI", int(size), weight)

    def create_stat_card(self, parent, title, val):
        f = ctk.CTkFrame(parent, fg_color=COLOR_WHITE, height=100)
        ctk.CTkLabel(f, text=title, font=("Segoe UI", 12), text_color="gray").pack(pady=(15, 5))
        lbl = ctk.CTkLabel(f, text=val, font=("Arial", 28, "bold"), text_color=FIB_GREEN)
        lbl.pack(pady=(0, 15))
        if "Total" in title:
            self.lbl_total_val = lbl
        else:
            self.lbl_today_val = lbl
        return f

    def browse_folder(self):
        radio = self._ui("config_page", "radio_var")
        mode = radio.get() if radio is not None else "Folder"
        if mode == "Access":
            p = filedialog.askopenfilename(title="Select Access Database",
                                           filetypes=[("Access DB", "*.accdb *.mdb"), ("All Files", "*.*")])
        else:
            p = filedialog.askdirectory(title="Select Source Folder")
        if p: self.folder_path_var.set(p)

    def load_config_from_json(self):
        config_path = get_config_path("config.json")
    
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
    
                    if "database" in data:
                        self.server_val = data["database"].get("server", "")
                        self.db_val = data["database"].get("db_name", "")
                        self.user_val = data["database"].get("user", "")
                        self.pass_val = data["database"].get("password", "")
    
                    if "app_settings" in data:
                        self.folder_path_var.set(data["app_settings"].get("root_folder", ""))
    
                # 1️⃣ استكمال تحديث الواجهة بالكامل (بشرط وجود العنصر على شاشة الإعدادات)
                for ent, val in (("ent_server", getattr(self, 'server_val', '')),
                                 ("ent_db", getattr(self, 'db_val', '')),
                                 ("ent_user", getattr(self, 'user_val', '')),
                                 ("ent_pass", getattr(self, 'pass_val', ''))):
                    widget = self._ui("config_page", ent)
                    if widget is not None:
                        widget.delete(0, "end")
                        widget.insert(0, val)
    
            except Exception as e:
                print(f"Error loading config: {e}")

    def save_config(self, silent=False):
        if hasattr(self, 'sys_logger'):
            self.sys_logger.log(f"💾 تم حفظ إعدادات جديدة -> المسار: {self.folder_path_var.get()}")
    
        config_path = get_config_path("config.json")
    
        # 2️⃣ الجلب الآمن: لو الخانة موجودة على شاشة الإعدادات خذ منها، وإلا القيمة من المتغير
        ent_server = self._ui("config_page", "ent_server")
        ent_db = self._ui("config_page", "ent_db")
        ent_user = self._ui("config_page", "ent_user")
        ent_pass = self._ui("config_page", "ent_pass")
        srv = ent_server.get().strip() if ent_server is not None else getattr(self, 'server_val', '')
        db_n = ent_db.get().strip() if ent_db is not None else getattr(self, 'db_val', '')
        usr = ent_user.get().strip() if ent_user is not None else getattr(self, 'user_val', '')
        pwd = ent_pass.get().strip() if ent_pass is not None else getattr(self, 'pass_val', '')
    
        # تجميع البيانات
        data = {
            "database": {
                "server": srv,
                "db_name": db_n,
                "user": usr,
                "password": pwd
            },
            "app_settings": {
                "root_folder": self.folder_path_var.get()
            },
            "license_info": {
                "key": self.lic_data.get("key_str", "")
            }
        }
    
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
    
            # تحديث المتغيرات الداخلية بالقيمة الجديدة
            self.server_val, self.db_val = srv, db_n
            self.user_val, self.pass_val = usr, pwd
    
            if not silent:
                messagebox.showinfo("Success", "Configuration saved successfully!")
        except Exception as e:
            if not silent:
                messagebox.showerror("Error", f"Failed to save config: {e}")

    def test_conn(self):
        # دالة الاختبار تعمل من شاشة الكونفيج — الخانات موجودة على الـ page instance
        ent_server = self._ui("config_page", "ent_server")
        ent_db = self._ui("config_page", "ent_db")
        ent_user = self._ui("config_page", "ent_user")
        ent_pass = self._ui("config_page", "ent_pass")
        if ent_server is None:
            return
    
        srv = ent_server.get().strip()
        db_n = ent_db.get().strip()
        usr = ent_user.get().strip()
        pwd = ent_pass.get().strip()
    
        if hasattr(self, 'sys_logger'):
            self.sys_logger.log(f"🔌 يتم الآن اختبار الاتصال بالسيرفر: [{srv}] قاعدة البيانات: [{db_n}]")
    
        if not srv or not db_n:
            messagebox.showwarning("Missing Info", "Please enter Server and Database name.")
            return
    
        btn_test = self._ui("config_page", "btn_test")
        if btn_test is not None:
            btn_test.configure(state="disabled", text="Connecting...")
    
        def _run_test():
            try:
                # استخدام None للوجر لأننا عدلناه ليكون اختيارياً في الخطوات السابقة
                DatabaseEngine(srv, db_n, usr, pwd, logger=None)
    
                self.after(0, lambda: messagebox.showinfo("Success", f"Connected to [{db_n}] Successfully! ✅"))
            except Exception as e:
                err_msg = str(e)
                self.after(0, lambda: messagebox.showerror("Connection Failed", f"Could not connect:\n{err_msg}"))
            finally:
                if btn_test is not None:
                    self.after(0, lambda: btn_test.configure(state="normal", text="🔌 Test Connection"))
    
        threading.Thread(target=_run_test, daemon=True).start()

    def start_process(self):
        if not self.folder_path_var.get():
            messagebox.showwarning("Warning", "Please select source folder in Configuration.")
            self.show_page("config_page")
            return
    
        btn_run = self._ui("dashboard", "btn_run")
        progress = self._ui("dashboard", "progress")
        log_box = self._ui("dashboard", "log_box")
        if btn_run is not None:
            btn_run.configure(state="disabled", text="PROCESSING... ⏳", fg_color="gray")
        if progress is not None:
            progress.pack(fill="x", side="bottom")
            progress.start()
        if log_box is not None:
            log_box.delete("1.0", "end")
        threading.Thread(target=self.run_engine, daemon=True).start()

    def run_engine(self):
        # استيراد كسول — الوحدتان تحتاجان pyodbc ولا تُستخدمان عند الإقلاع
        from access_migrator import AccessToSQL
        from etl import ETLOrchestrator
        try:
            path = self.folder_path_var.get()
    
            # 3️⃣ الجلب الآمن — الخانات موجودة على شاشة الإعدادات لو انفتحت
            ent_server = self._ui("config_page", "ent_server")
            ent_db = self._ui("config_page", "ent_db")
            ent_user = self._ui("config_page", "ent_user")
            ent_pass = self._ui("config_page", "ent_pass")
            srv = ent_server.get().strip() if ent_server is not None else getattr(self, 'server_val', '')
            db_n = ent_db.get().strip() if ent_db is not None else getattr(self, 'db_val', '')
            usr = ent_user.get().strip() if ent_user is not None else getattr(self, 'user_val', '')
            pwd = ent_pass.get().strip() if ent_pass is not None else getattr(self, 'pass_val', '')
    
            # التحقق الآمن من Checkboxes
            chk_append = self._ui("config_page", "chk_append_var")
            is_append = chk_append.get() if chk_append is not None else False
            write_mode = 'append' if is_append else 'replace'
    
            target_tbl = None
            chk_merge = self._ui("config_page", "chk_merge_var")
            ent_merge = self._ui("config_page", "ent_merge_name")
            if chk_merge is not None and chk_merge.get():
                target_tbl = ent_merge.get().strip() if ent_merge is not None else ""
                if not target_tbl:
                    self.log_gui("❌ Error: Merge selected but no table name!", "ERROR")
                    return
    
            # تحديد نوع العملية
            radio = self._ui("config_page", "radio_var")
            radio_choice = radio.get() if radio is not None else "Excel/CSV"
    
            if radio_choice == "Access":
                self.log_gui("🚀 Detected Access Database.")
                migrator = AccessToSQL(path, srv, db_n, self.log_gui, user=usr, password=pwd)
                migrator.migrate(mode=write_mode, target_table=target_tbl)
            else:
                orch = ETLOrchestrator(srv, db_n, usr, pwd, path, self.log_gui)
                orch.run()
    
            self.refresh_dashboard_data()
            self.log_gui("✅ PROCESS COMPLETED.", "SUCCESS")
    
        except Exception as e:
            self.log_gui(f"❌ CRITICAL ERROR: {e}", "ERROR")
        finally:
            self.after(0, getattr(self, 'reset_ui', lambda: None))

    def reset_ui(self):
        btn_run = self._ui("dashboard", "btn_run")
        progress = self._ui("dashboard", "progress")
        if btn_run is not None:
            btn_run.configure(state="normal", text="🚀 START PROCESS", fg_color=FIB_GREEN)
        if progress is not None:
            progress.stop()
            progress.pack_forget()

    def log_gui(self, msg, type="INFO"):
        log_box = self._ui("dashboard", "log_box")
        if log_box is None:
            # الداشبورد غير مفتوحة — سجّل في اللوق بدل ما تضيع الرسالة
            if hasattr(self, 'sys_logger'):
                self.sys_logger.log(msg)
            return
        self.after(0, lambda: [log_box.insert("end", f"{msg}\n"), log_box.see("end")])

    def load_history_data(self):
        def _bg_load():
            try:
                db = DatabaseEngine(self.server_val, self.db_val, logger=EnterpriseLogger(None))
                with db.engine.connect() as c:
                    rows = c.execute(text(
                        "SELECT TOP 50 ID, FILE_NAME, ROW_COUNT,STATUS, PROCESSED_AT FROM SYS_FILES_LOG ORDER BY ID DESC")).fetchall()
                    self.after(0, lambda: self._fill_tree(rows))
            except:
                pass
    
        threading.Thread(target=_bg_load, daemon=True).start()

    def _fill_tree(self, rows):
        tree = self._ui("dashboard", "tree")
        if tree is None:
            return  # الداشبورد غير مفتوحة — لا يوجد جدول للعرض
        tree.delete(*tree.get_children())
        for r in rows:
            dt = str(r[3])[:19] if r[3] else ""
            tree.insert("", "end", values=(r[0], r[1], r[2], r[3], dt))

    def export_report_excel(self):
        path = filedialog.asksaveasfilename(defaultextension=".xlsx",
                                            filetypes=[("Excel File", "*.xlsx"), ("CSV File", "*.csv")])
        if not path: return
    
        def _do_export():
            try:
                # Fetch full data
                db = DatabaseEngine(self.server_val, self.db_val, EnterpriseLogger(None))
                query = "SELECT * FROM SYS_FILES_LOG ORDER BY ID DESC"
    
                if HAS_PANDAS:
                    # Export using Pandas (Professional Excel)
                    with db.engine.connect() as conn:
                        df = pd.read_sql(query, conn)
    
                    if path.endswith(".csv"):
                        df.to_csv(path, index=False)
                    else:
                        df.to_excel(path, index=False)
                else:
                    # Fallback if pandas is missing (Basic CSV)
                    with db.engine.connect() as conn:
                        result = conn.execute(text(query))
                        with open(path, "w", newline="", encoding="utf-8") as f:
                            writer = csv.writer(f)
                            writer.writerow(result.keys())
                            writer.writerows(result.fetchall())
    
                messagebox.showinfo("Export Success", f"Report exported successfully to:\n{path}")
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to export: {e}")
    
        threading.Thread(target=_do_export, daemon=True).start()

# ✅ التوافق مع الكود القديم: main.py يستورد FGSApp من حزمة gui
FGSApp = MainWindow

__all__ = ["MainWindow", "FGSApp", "MENU_STRUCTURE"]
