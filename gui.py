import tempfile

import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import json
import os
import sys
import datetime
from PIL import Image
from sqlalchemy import text

from database import DatabaseEngine
from utils import EnterpriseLogger

# محاولة استدعاء pandas لتصدير الإكسل
try:
    import pandas as pd

    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

# ========================================================
# 🎨 BRANDING & THEME
# ========================================================
ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("green")

FIB_GREEN = "#00563B"  # Official Dark Green
FIB_GOLD = "#C5A059"  # Gold Accent
COLOR_BG = "#F4F6F8"  # Light Gray Background
COLOR_WHITE = "#FFFFFF"
COLOR_TEXT_MAIN = "#2D3436"

# ألوان الوضع الليلي للداتا (Monitor & History)
COLOR_DARK_BG = "#1A1A1A"  # خليناها أسود تقريباً عشان الأخضر يبان
COLOR_TEXT_LITE = "#00FF41"  # ده كود اللون الأخضر بتاع الـ Matrix بالظبط
COLOR_RED_ALERT = "#E74C3C"


# ... (بعد الـ imports الموجودة)
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for Nuitka onefile """
    if "__compiled__" in globals():
        # Nuitka extracts data files to the directory of the executable context
        base_path = os.path.dirname(__file__)
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# ✅ الاستخدام الصحيح داخل الكود:
my_logo_path = resource_path("logo.png")
my_font_path = resource_path("Amiri-Regular.ttf")


def get_config_path(filename="config.json"):
    """
    دالة ذكية لتحديد مسار حفظ الإعدادات متوافقة مع Nuitka.
    """
    import sys
    import os

    if getattr(sys, 'frozen', False) or '__compiled__' in globals():
        application_path = os.path.dirname(os.path.abspath(sys.argv[0]))
    else:
        application_path = os.path.dirname(os.path.abspath(__file__))

    return os.path.join(application_path, filename)


def get_resource_path(filename):
    """
    دي للملفات الثابتة زي الصور (للقراءة فقط)
    """
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS  # مسار الـ Temp بتاع PyInstaller
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, filename)


import customtkinter as ctk
import tkinter as tk


class PremiumSearchPopup(ctk.CTkToplevel):
    def __init__(self, parent, title, data_list, callback):
        super().__init__(parent)
        self.callback = callback
        self.all_data = data_list

        # إعدادات الشاشة الأساسية
        self.title(title)
        self.geometry("550x600")  # كبرنا الشاشة شوية للفخامة
        self.attributes("-topmost", True)
        self.overrideredirect(True)  # إخفاء شريط الويندوز بالكامل
        self.configure(fg_color="#0B5C3A")  # لون الخلفية أخضر عشان يعمل إطار خارجي شيك

        # توسيط الشاشة
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() // 2) - (550 // 2)
        y = parent.winfo_rooty() + (parent.winfo_height() // 2) - (600 // 2)
        self.geometry(f"+{x}+{y}")

        # =========================
        # Main VIP Container (الحاوية الرئيسية بلون أبيض وحواف دائرية)
        # =========================
        main_container = ctk.CTkFrame(self, fg_color="#FFFFFF", corner_radius=12, border_width=2,
                                      border_color="#0B5C3A")
        main_container.pack(fill="both", expand=True, padx=2, pady=2)  # الـ Pad هنا بيعمل تأثير الـ Border الأخضر

        # =========================
        # 1. VIP Header (الهيدر)
        # =========================
        header = ctk.CTkFrame(main_container, fg_color="#0B5C3A", corner_radius=10)
        header.pack(fill="x", padx=5, pady=(5, 15))

        # زر القفل الدائري الشيك
        btn_close = ctk.CTkButton(header, text="✕", width=35, height=35, fg_color="#08472C",
                                  text_color="white", hover_color="#C62828", font=("Segoe UI", 16, "bold"),
                                  corner_radius=8, command=self.destroy)
        btn_close.pack(side="left", padx=10, pady=10)

        lbl_title = ctk.CTkLabel(header, text=f"✨ {title} ✨", text_color="white", font=("Segoe UI", 16, "bold"))
        lbl_title.pack(side="right", padx=15, pady=10)

        # =========================
        # 2. Modern Search Area (منطقة بحث فخمة)
        # =========================
        search_frame = ctk.CTkFrame(main_container, fg_color="transparent")
        search_frame.pack(fill="x", padx=20, pady=(0, 10))

        # زر مسح مدمج وشيك
        btn_clear = ctk.CTkButton(
            search_frame, text="مسح", width=60, height=45,
            fg_color="#F3F4F6", text_color="#4B5563", hover_color="#E5E7EB", font=("Segoe UI", 13, "bold"),
            corner_radius=10, command=self.clear_search
        )
        btn_clear.pack(side="left", padx=(0, 10))

        # مربع بحث دائري وكبير
        self.entry_search = ctk.CTkEntry(
            search_frame,
            placeholder_text="🔍 ابحث بالاسم أو الكود هنا...",
            justify="right",
            font=("Segoe UI", 14),
            height=45,
            corner_radius=10,
            border_width=1,
            border_color="#D1D5DB",
            fg_color="#F9FAFB",
            text_color="#111827"
        )
        self.entry_search.pack(side="left", fill="x", expand=True)
        self.entry_search.bind("<KeyRelease>", self.filter_data)

        # =========================
        # 3. Info Label (عداد النتائج الذكي)
        # =========================
        self.lbl_info = ctk.CTkLabel(main_container, text="", text_color="#6B7280", font=("Segoe UI", 11))
        self.lbl_info.pack(anchor="e", padx=25, pady=(0, 5))

        # =========================
        # 4. VIP List Area (استخدام العناصر الحديثة بدلاً من Listbox)
        # =========================
        self.list_frame = ctk.CTkScrollableFrame(
            main_container,
            fg_color="#FFFFFF",
            corner_radius=10,
            border_width=1,
            border_color="#E5E7EB"
        )
        self.list_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        # تحميل البيانات
        self.populate_list(self.all_data)
        self.entry_search.focus()

    def filter_data(self, event=None):
        query = self.entry_search.get().strip().lower()
        if not query:
            self.populate_list(self.all_data)
        else:
            filtered = [item for item in self.all_data if query in item.lower()]
            self.populate_list(filtered)

    def populate_list(self, data):
        # تفريغ القائمة القديمة
        for widget in self.list_frame.winfo_children():
            widget.destroy()

        # 🔥 السر هنا: نعرض 100 عنصر فقط كحد أقصى للحفاظ على سرعة البرق 🔥
        max_display = 100
        display_data = data[:max_display]

        if len(data) > max_display:
            self.lbl_info.configure(text=f"يتم عرض أول {max_display} نتيجة. يرجى كتابة المزيد في البحث للتخصيص.")
        elif len(data) == 0:
            self.lbl_info.configure(text="لا توجد نتائج مطابقة.")
        else:
            self.lbl_info.configure(text=f"تم العثور على {len(data)} نتيجة.")

        # رسم العناصر كأزرار فخمة (Hover effects, Spacing, Custom Fonts)
        for item in display_data:
            btn = ctk.CTkButton(
                self.list_frame,
                text=item,
                anchor="e",  # محاذاة لليمين
                font=("Segoe UI", 14),
                fg_color="transparent",
                text_color="#111827",
                hover_color="#E8F5E9",  # لون أخضر فاتح جداً عند مرور الماوس
                corner_radius=6,
                height=38,
                command=lambda val=item: self.select_item(val)
            )
            btn.pack(fill="x", pady=2, padx=2)

    def clear_search(self):
        self.entry_search.delete(0, tk.END)
        self.filter_data()

    def select_item(self, selected_val):
        self.callback(selected_val)
        self.destroy()
import customtkinter  # <--- هذا السطر هو الحل
import tkinter as tk
from license_guard import LicenseGuard  # (اللي ضفناه المرة اللي فاتت)

class FGSApp(customtkinter.CTk):
    import sys
    import threading
    import tkinter as tk
    import customtkinter as ctk
    from PIL import Image

    # افترضت وجود استدعاءاتك السابقة هنا للثوابت والدوال (COLOR_BG, FIB_GREEN, etc.)

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
        # ده بيخلي قيم (server_val) تتملي قبل ما شاشة الداشبورد تفتح
        try:
            self.load_config_from_json()
        except Exception as e:
            self.sys_logger.log(f"⚠️ تنبيه: لم يتم تحميل ملف الإعدادات عند البداية: {e}", "WARNING")

        # Grid Layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # 2. Setup UI
        # دلوقتي لما الـ Sidebar والـ Pages يتبنوا، القيم هتكون جاهزة
        self.setup_sidebar()
        self.setup_pages()

        # 3. تشغيل العمليات الخلفية (تحديث البيانات فقط)
        # قللنا الـ Delay شوية وبنخليه يحدث الداتا بس لأن الكونفيج اتحمل خلاص فوق
        #if hasattr(self, 'refresh_dashboard_data'):
        # self.after(500, self.refresh_dashboard_data)
            #else:
            # لو لسه بتعتمد على system_startup سيبها بس تأكد إنها مش بتصفر القيم تاني
            #self.after(100, self.system_startup)

        # 4. تشغيل المراقب الأمني لو الرخصة فعالة
        if self.lic_data.get("active"):
            self.start_security_monitor()

            # Open Account Inquiry instead
            self.show_page("nuwairy")

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

    def setup_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=250, corner_radius=0, fg_color=COLOR_WHITE)
        self.sidebar.grid(row=0, column=0, sticky="nsew")

        # حجز مساحة مرنة قبل كارت التفعيل لدفعه للأسفل
        self.sidebar.grid_rowconfigure(10, weight=1)

        # 1. Logo Area
        logo_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo_frame.grid(row=0, column=0, pady=(30, 20), padx=20, sticky="ew")

        try:
            img_path = resource_path("logo.png")
            self.logo_image = ctk.CTkImage(
                light_image=Image.open(img_path),
                dark_image=Image.open(img_path),
                size=(180, 50)
            )
            ctk.CTkLabel(logo_frame, text="", image=self.logo_image).pack()
        except Exception:  # تعديل: منع الـ Bare Exception
            ctk.CTkLabel(logo_frame, text="FIB SYSTEM", font=("Arial", 20, "bold"), text_color=FIB_GREEN).pack()

        ctk.CTkFrame(self.sidebar, height=2, fg_color=FIB_GOLD).grid(row=1, column=0, sticky="ew", padx=30,
                                                                     pady=(0, 20))

        # 2. Menu Buttons
        #self.btn_dash = self.create_nav_btn("📊  Dashboard", 2, "dashboard")
        #self.btn_conf = self.create_nav_btn("⚙️  Configuration", 3, "config")
        self.btn_nuwairy = self.create_nav_btn("✨  Account Inquiry", 4, "nuwairy")
        self.btn_gl_inquiry = self.create_nav_btn("✨  GL Account Inquiry", 5, "gl_inquiry")
        self.btn_customer = self.create_nav_btn("✨  Customer Inquiry", 6, "customer")
        # ==========================================
        # 🆔 ACTIVATION & LICENSE CARD (شكل مبسط وآمن للموظفين)
        # ==========================================
        status_color = FIB_GREEN if self.lic_data.get("active") else COLOR_RED_ALERT
        status_text = "ACTIVE LICENSE" if self.lic_data.get("active") else "INACTIVE / DEMO"

        info_card = ctk.CTkFrame(self.sidebar, fg_color="#F8F9FA", corner_radius=10, border_width=1,
                                 border_color="#E0E0E0")
        info_card.grid(row=11, column=0, padx=15, pady=20, sticky="ew")

        # -- Status Header (فقط الحالة هتظهر للموظف) --
        status_row = ctk.CTkFrame(info_card, fg_color="transparent")
        status_row.pack(fill="x", padx=10, pady=15)  # كبرت المسافة شوية عشان مفيش حاجة تحتها

        self.lbl_dot = ctk.CTkLabel(status_row, text="●", font=("Arial", 16), text_color=status_color)
        self.lbl_dot.pack(side="left")
        self.lbl_status_text = ctk.CTkLabel(status_row, text=status_text, font=("Segoe UI", 10, "bold"),
                                            text_color=status_color)
        self.lbl_status_text.pack(side="left", padx=5)

        # 🌟 الباب الخلفي السري للأدمن: دبل كليك بالماوس على الكارت يفتح شاشة التفعيل
        info_card.bind("<Double-1>", lambda e: self.show_admin_activation_popup())
        status_row.bind("<Double-1>", lambda e: self.show_admin_activation_popup())
        self.lbl_status_text.bind("<Double-1>", lambda e: self.show_admin_activation_popup())
        self.lbl_dot.bind("<Double-1>", lambda e: self.show_admin_activation_popup())

        # Footer
        ctk.CTkLabel(self.sidebar, text="v2.1 Enterprise © FGS", font=("Arial", 9), text_color="#CCC").grid(
            row=12,
            column=0,
            pady=(0, 10)
        )

    def show_admin_activation_popup(self):
        """نافذة سرية للمدير لتفعيل الرخصة بتفتح بالدبل كليك"""
        import customtkinter as ctk
        import tkinter.messagebox as messagebox

        popup = ctk.CTkToplevel(self)
        popup.title("Admin License Manager - Secret")
        popup.geometry("450x250")
        popup.attributes("-topmost", True)  # الشاشة دي هتبقى فوق كل حاجة
        popup.resizable(False, False)

        ctk.CTkLabel(popup, text="Enter New Activation Key:", font=("Segoe UI", 14, "bold")).pack(pady=(25, 10))

        # مربع الكود
        ent_key = ctk.CTkEntry(popup, width=350, justify="center", font=("Consolas", 12))
        ent_key.pack(pady=10)

        # عرض الـ Machine ID للأدمن عشان لو هتعمل جنريت لكود جديد
        mid = self.lic_data.get("mid", "UNKNOWN")
        ctk.CTkLabel(popup, text=f"Machine ID: {mid}", font=("Segoe UI", 10), text_color="gray").pack()

        def do_activate():
            key_input = ent_key.get().strip()
            if not key_input:
                messagebox.showwarning("تنبيه", "Please paste the key first.")
                return

            # بنخلي البرنامج يقرا من المربع الجديد ده بدل المربع القديم اللي شلناه
            self.ent_lic_key = ent_key
            self.on_activate_click()  # تشغيل دالة التفعيل بتاعتك الأساسية

            # لو التفعيل نجح، الواجهة تتحدث لـ أخضر والشاشة دي تتقفل
            if hasattr(self, 'lic_data') and self.lic_data.get("active"):
                self.lbl_dot.configure(text_color="#00563B")  # لون FIB_GREEN
                self.lbl_status_text.configure(text="ACTIVE LICENSE", text_color="#00563B")
                popup.destroy()

        ctk.CTkButton(
            popup,
            text="Verify & Activate",
            fg_color="#C5A059",  # لون FIB_GOLD
            hover_color="#B58B00",
            command=do_activate
        ).pack(pady=20)

    def create_nav_btn(self, text, row, page_name):
        btn = ctk.CTkButton(
            self.sidebar, text=text,
            font=("Segoe UI", 11,"bold"),  # 1️⃣ صغرنا الخط من 14 لـ 12
            anchor="w",
            fg_color="transparent",
            text_color=COLOR_TEXT_MAIN,
            hover_color="#F0F9F4",
            height=22,  # 2️⃣ صغرنا ارتفاع الزرار من 50 لـ 32
            corner_radius=6,  # (اختياري) صغرنا الكيرف شوية عشان يليق مع الحجم الصغير
            command=lambda: self.show_page(page_name)
        )
        btn.grid(row=row, column=0, sticky="ew", padx=10, pady=2)  # 3️⃣ قللنا الـ pady من 5 لـ 2 عشان يقربوا من بعض
        return btn

    def setup_pages(self):
        # الحاوية الرئيسية اللي بتتعرض فيها الشاشات
        self.content_area = ctk.CTkFrame(self, fg_color="transparent")
        self.content_area.grid(row=0, column=1, sticky="nsew", padx=30, pady=30)

        # 1. شاشة استعلام الحسابات (Account Inquiry)
        self.page_nuwairy = ctk.CTkFrame(self.content_area, fg_color="transparent")
        self.setup_nuwairy_ui(self.page_nuwairy)

        # 2. شاشة استعلام الأستاذ العام (GL Account Inquiry)
        self.page_gl_inquiry = ctk.CTkFrame(self.content_area, fg_color="transparent")
        self.setup_gl_inquiry_ui(self.page_gl_inquiry)

        self.page_customer = ctk.CTkFrame(self.content_area, fg_color="transparent")
        self.setup_customer_inquiry_ui(self.page_customer)

    def show_page(self, name):
        if hasattr(self, 'sys_logger'):
            self.sys_logger.log(f"🔄 المستخدم انتقل إلى شاشة: {name}")

        # 1. إخفاء الشاشتين الحاليين
        pages_to_hide = [
            getattr(self, 'page_nuwairy', None),
            getattr(self, 'page_gl_inquiry', None),
            getattr(self, 'page_customer', None)
        ]
        for p in pages_to_hide:
            if p is not None:
                p.pack_forget()

        # 2. إرجاع لون كل الزراير للحالة الطبيعية
        buttons_to_reset = [
            getattr(self, 'btn_nuwairy', None),
            getattr(self, 'btn_gl_inquiry', None),
            getattr(self, 'btn_customer', None)
        ]
        for b in buttons_to_reset:
            if b is not None:
                b.configure(fg_color="transparent", text_color=COLOR_TEXT_MAIN)

        # 3. إظهار الشاشة المطلوبة وتلوين الزرار بتاعها

        # --- تشغيل شاشة Account Inquiry ---
        if name == "nuwairy":
            if hasattr(self, 'page_nuwairy') and self.page_nuwairy is not None:
                self.page_nuwairy.pack(fill="both", expand=True)
                self.btn_nuwairy.configure(fg_color=FIB_GREEN, text_color="white")
                # لو عندك دالة تحميل فروع هنا شغلها
                if hasattr(self, 'nuwairy_load_branches'):
                    self.nuwairy_load_branches()

        # --- تشغيل شاشة GL Inquiry ---
        elif name == "gl_inquiry":
            if hasattr(self, 'page_gl_inquiry'):
                self.page_gl_inquiry.pack(fill="both", expand=True)
            if hasattr(self, 'btn_gl_inquiry'):
                self.btn_gl_inquiry.configure(fg_color=FIB_GREEN, text_color="white")
            # تحميل الداتا أوتوماتيك
            if hasattr(self, 'gl_load_codes'): self.gl_load_codes()
            if hasattr(self, 'nuwairy_load_branches'): self.nuwairy_load_branches()
            if hasattr(self, 'gl_load_currencies'): self.gl_load_currencies()
        elif name == "customer":
            if hasattr(self, 'page_customer'):
                self.page_customer.pack(fill="both", expand=True)
            if hasattr(self, 'btn_customer'):
                self.btn_customer.configure(fg_color=FIB_GREEN, text_color="white")





    def setup_dashboard_ui(self, parent):
        # Header
        head = ctk.CTkFrame(parent, fg_color="transparent")
        head.pack(fill="x", pady=(0, 15))

        t_frame = ctk.CTkFrame(head, fg_color="transparent")
        t_frame.pack(side="left")
        ctk.CTkLabel(t_frame, text="System Overview", font=("Segoe UI", 26, "bold"), text_color=FIB_GREEN).pack(
            anchor="w")

        ctk.CTkButton(head, text="🔄 Refresh", width=100, height=35,
                      fg_color=COLOR_WHITE, text_color=COLOR_TEXT_MAIN, hover_color="#EEE",
                      border_width=1, border_color="#CCC",
                      command=self.refresh_dashboard_data).pack(side="right", anchor="ne")

        # Action Card
        card = ctk.CTkFrame(parent, fg_color=COLOR_WHITE, corner_radius=15, border_width=1, border_color="#E0E0E0")
        card.pack(fill="x", pady=15)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(padx=30, pady=25, fill="x")

        # 🔒 قفل الزرار لو مفيش رخصة
        if self.lic_data["active"]:
            btn_state = "normal"
            btn_text = "🚀 START PROCESS"
            btn_fg = FIB_GREEN
            lbl_status = "Status: IDLE"
        else:
            btn_state = "disabled"
            btn_text = "🔒 LICENSE REQUIRED"
            btn_fg = "gray"
            lbl_status = "Status: RESTRICTED MODE"

        ctk.CTkLabel(inner, text=lbl_status, font=("Segoe UI", 14, "bold"), text_color="gray").pack(side="right")

        self.btn_run = ctk.CTkButton(inner, text=btn_text, font=("Segoe UI", 14, "bold"),
                                     height=45, width=220, fg_color=btn_fg, hover_color="#00402C",
                                     state=btn_state,  # 👈 دي أهم حاجة
                                     command=self.start_process)
        self.btn_run.pack(side="left")

        self.progress = ctk.CTkProgressBar(card, height=4, progress_color=FIB_GOLD, fg_color="#EEE")
        self.progress.pack(fill="x", side="bottom")
        self.progress.pack_forget()

        # Tabs
        # التعديل الصحيح:
        # text_color="white": بيخلي الخط أبيض
        # segmented_button_unselected_color="#555": بيخلي خلفية الزرار اللي مش شغال غامقة عشان الأبيض يبان
        tabs = ctk.CTkTabview(parent,
                              fg_color=COLOR_WHITE,
                              text_color="white",
                              segmented_button_selected_color=FIB_GREEN,
                              segmented_button_unselected_color="#555",
                              segmented_button_unselected_hover_color="#444")

        tabs.pack(fill="both", expand=True)
        tabs.add("Live Monitor")
        tabs.add("History Log")
        # ✅ MONITOR: Dark Background & White Text
        self.log_box = ctk.CTkTextbox(tabs.tab("Live Monitor"), font=("Consolas", 11),
                                      fg_color=COLOR_DARK_BG, text_color=COLOR_TEXT_LITE)
        self.log_box.pack(fill="both", expand=True, padx=10, pady=10)

        # ✅ HISTORY: Dark Background & White Text
        cols = ("ID", "File Name", "ِAdded Rows", "Status", "Date")
        self.tree = ttk.Treeview(tabs.tab("History Log"), columns=cols, show="headings", height=10)
        self.style_treeview()  # Apply dark style

        for c in cols: self.tree.heading(c, text=c)
        self.tree.column("ID", width=60, anchor="center")
        self.tree.column("File Name", width=400)
        self.tree.column("ِAdded Rows", width=80)
        self.tree.column("Status", width=120, anchor="center")

        scrolly = ttk.Scrollbar(tabs.tab("History Log"), orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=scrolly.set)
        scrolly.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True, padx=5, pady=5)

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

    def setup_config_ui(self, parent):
        # عنوان الصفحة
        ctk.CTkLabel(parent, text="System Configuration", font=("Segoe UI", 24, "bold"), text_color=FIB_GREEN).pack(
            anchor="w", pady=(0, 20))

        # الإطار الأبيض الكبير
        frame = ctk.CTkFrame(parent, fg_color=COLOR_WHITE, corner_radius=10)
        frame.pack(fill="both", expand=True)

        # 1. منطقة الإدخال (Inputs Area)
        scroll_frame = ctk.CTkScrollableFrame(frame, fg_color="transparent")
        scroll_frame.pack(fill="both", expand=True, padx=20, pady=20)

        inner = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        inner.pack(fill="x", padx=10, pady=10)

        # دالة مساعدة لرسم الحقول (معدلة لتقبل حقل الباسورد)
        def add_field(row, label, val, is_pass=False):
            ctk.CTkLabel(inner, text=label, font=("Segoe UI", 12, "bold"), text_color=FIB_GREEN).grid(row=row, column=0,
                                                                                                      sticky="w",
                                                                                                      pady=(5, 2))

            # لو هو باسورد خليه نجوم *
            show_char = "*" if is_pass else ""

            ent = ctk.CTkEntry(inner, width=400, height=35, border_color="#CCC", show=show_char)
            ent.grid(row=row + 1, column=0, sticky="w", pady=(0, 10))
            ent.delete(0, "end")
            ent.insert(0, str(val) if val else "")
            return ent

        # --- الحقول الأساسية ---

        # 1. Server
        self.ent_server = add_field(0, "Server Host Address", self.server_val)

        # 2. Database Name
        self.ent_db = add_field(2, "Database Name", self.db_val)

        # 3. SQL User (الجزء اللي كان ناقصك) 🔥
        user_v = getattr(self, 'user_val', '')  # حماية عشان لو المتغير مش موجود
        self.ent_user = add_field(4, "SQL Username (Optional)", user_v)

        # 4. SQL Password (الجزء اللي كان ناقصك) 🔥
        pass_v = getattr(self, 'pass_val', '')
        self.ent_pass = add_field(6, "SQL Password", pass_v, is_pass=True)

        # --- اختيار نوع المصدر ---
        # لاحظ غيرنا رقم الصف لـ 8 عشان وسعنا مكان لليوزر والباسورد
        ctk.CTkLabel(inner, text="Data Source Type", font=("Segoe UI", 12, "bold"), text_color=FIB_GREEN).grid(row=8,
                                                                                                               column=0,
                                                                                                               sticky="w",
                                                                                                               pady=(10,
                                                                                                                     5))

        if not hasattr(self, 'radio_var'): self.radio_var = tk.StringVar(value="Folder")

        radio_frame = ctk.CTkFrame(inner, fg_color="transparent")
        radio_frame.grid(row=9, column=0, sticky="w", pady=(0, 5))

        ctk.CTkRadioButton(radio_frame, text="Folder (CSV/Excel)", variable=self.radio_var, value="Folder",
                           text_color="#333", command=self.update_path_label).pack(side="left", padx=(0, 20))
        ctk.CTkRadioButton(radio_frame, text="MS Access Database", variable=self.radio_var, value="Access",
                           text_color="#333", command=self.update_path_label).pack(side="left")

        # --- مسار الملف ---
        self.lbl_path_title = ctk.CTkLabel(inner, text="Source Folder Path", font=("Segoe UI", 12, "bold"),
                                           text_color=FIB_GREEN)
        self.lbl_path_title.grid(row=10, column=0, sticky="w", pady=(10, 5))

        f_frame = ctk.CTkFrame(inner, fg_color="transparent")
        f_frame.grid(row=11, column=0, sticky="ew")

        self.ent_folder = ctk.CTkEntry(f_frame, textvariable=self.folder_path_var, height=35, border_color="#CCC",
                                       width=300)
        self.ent_folder.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(f_frame, text="Browse", width=80, height=35, fg_color=FIB_GOLD, text_color="white",
                      command=self.browse_folder).pack(side="left", padx=10)

        # --- خيارات متقدمة (Merge & Append) ---
        opts_frame = ctk.CTkFrame(inner, fg_color="#F1F3F5", corner_radius=6)
        opts_frame.grid(row=12, column=0, sticky="ew", pady=15)

        # أ. خيار التزويد Append
        self.chk_append_var = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(opts_frame, text="Append Data (Don't drop existing tables)", variable=self.chk_append_var,
                        font=("Segoe UI", 11, "bold"), text_color="#333").pack(anchor="w", padx=10, pady=10)

        # ب. خيار الدمج Merge
        self.chk_merge_var = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(opts_frame, text="Merge all tables into one SQL Table", variable=self.chk_merge_var,
                        command=self.toggle_merge_entry, font=("Segoe UI", 11, "bold"), text_color="#333").pack(
            anchor="w", padx=10, pady=(0, 5))

        # ج. خانة اسم الجدول المجمع
        self.ent_merge_name = ctk.CTkEntry(opts_frame, placeholder_text="Target Table Name (e.g. All_Branches)",
                                           width=300)
        self.ent_merge_name.pack(anchor="w", padx=35, pady=(0, 10))
        self.ent_merge_name.configure(state="disabled", fg_color="#EEE")

        # 2. منطقة الأزرار (Buttons Area)
        btn_box = ctk.CTkFrame(frame, fg_color="transparent")
        btn_box.pack(side="bottom", fill="x", pady=20)

        cfg_state = "normal" if self.lic_data.get("active", False) else "disabled"

        btn_inner = ctk.CTkFrame(btn_box, fg_color="transparent")
        btn_inner.pack()

        self.btn_save = ctk.CTkButton(btn_inner, text="💾 Save Settings", fg_color=FIB_GREEN, width=150, height=40,
                                      state=cfg_state, command=self.save_config)
        self.btn_save.pack(side="left", padx=10)

        self.btn_test = ctk.CTkButton(btn_inner, text="🔌 Test Connection", fg_color="#EEE", text_color="#333",
                                      width=150, height=40, state=cfg_state, command=self.test_conn)
        self.btn_test.pack(side="left", padx=10)

    def toggle_merge_entry(self):
        if self.chk_merge_var.get():
            self.ent_merge_name.configure(state="normal", fg_color="white")
        else:
            self.ent_merge_name.configure(state="disabled", fg_color="#EEE")

    def update_path_label(self):
        """تغيير عنوان المسار بناءً على الاختيار"""
        if self.radio_var.get() == "Access":
            self.lbl_path_title.configure(text="Access Database File (.accdb / .mdb)")
        else:
            self.lbl_path_title.configure(text="Source Folder Path")

    def setup_reports_ui(self, parent):
        ctk.CTkLabel(parent, text="Analytics & Reports", font=("Segoe UI", 24, "bold"), text_color=FIB_GREEN).pack(
            anchor="w", pady=(0, 20))

        # Stats
        stats_box = ctk.CTkFrame(parent, fg_color="transparent")
        stats_box.pack(fill="x", pady=10)

        self.card_total = self.create_stat_card(stats_box, "Total Files Processed", "0")
        self.card_total.pack(side="left", fill="x", expand=True, padx=10)

        self.card_today = self.create_stat_card(stats_box, "Processed Today", "0")
        self.card_today.pack(side="left", fill="x", expand=True, padx=10)

        # 🔒 لو مفيش رخصة الزرار لونه رمادي ومقفول
        excel_state = "normal" if self.lic_data["active"] else "disabled"
        excel_color = FIB_GOLD if self.lic_data["active"] else "gray"

        self.btn_export = ctk.CTkButton(parent, text="📥 Export to Excel", fg_color=excel_color, text_color="white",
                                        state=excel_state,
                                        command=self.export_report_excel)
        self.btn_export.pack(anchor="e", pady=(20, 5))

        # Text Report (Read-only view)
        self.txt_rep = ctk.CTkTextbox(parent, font=("Consolas", 11), fg_color=COLOR_WHITE)
        self.txt_rep.pack(fill="both", expand=True)

        # ==========================================

    def _init_nuwairy_sheet(self, parent):
        from tksheet import Sheet

        self.sheet = Sheet(
            parent,
            show_x_scrollbar=True,
            show_y_scrollbar=True,
            show_row_index=False,
            show_top_left=False,
            align="center",
            header_align="center",
            height=450,
            width=900,
            outline_thickness=1,
            outline_color="#E6E8EB",
            grid_color="#E5E7EB",
            selected_cells_bg="#DDEFE8",
            selected_cells_fg="#111827",
        )

        # ✅ لازم الهيدر يطابق عدد عناصر row = 9
        headers = [
            "التاريخ",
            "البيان",
            "دائن",
            "مدين",
            "الرصيد",
            "اسم الحركة",
            "الحساب الرئيسي",
            "الحساب الفرعي",
            "رقم النمارة",  # ✅ الجديد
        ]
        self.sheet.headers(headers)

        # ✅ 9 widths بدل 7 (الوصف أكبر + nseq صغير)
        self.sheet.set_column_widths([120, 520, 130, 130, 150, 180, 170, 140, 90])

        self.sheet.pack(fill="both", expand=True)

    def setup_nuwairy_ui(self, parent):
        import customtkinter as ctk

        # =========================
        # Page Wrapper
        # =========================
        page = ctk.CTkFrame(parent, fg_color="transparent")
        page.pack(fill="both", expand=True)

        # =========================
        # Header Bar (Title + Subtitle + Actions)
        # =========================
        header = ctk.CTkFrame(
            page,
            fg_color=COLOR_WHITE,
            corner_radius=14,
            border_width=1,
            border_color="#E6E8EB"
        )
        header.pack(fill="x", padx=10, pady=(0, 12))

        header_inner = ctk.CTkFrame(header, fg_color="transparent")
        header_inner.pack(fill="x", padx=16, pady=14)

        title_wrap = ctk.CTkFrame(header_inner, fg_color="transparent")
        title_wrap.pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(
            title_wrap,
            text="🔍 استعلام حركات العملاء",
            font=("Segoe UI", 22, "bold"),
            text_color=FIB_GREEN
        ).pack(anchor="w")

        ctk.CTkLabel(
            title_wrap,
            text="ابحث برقم العميل، اختر نوع الحساب والعملة، وحدد فترة التاريخ (اختياري).",
            font=("Segoe UI", 12),
            text_color="#6B7280"
        ).pack(anchor="w", pady=(4, 0))

        # Actions (Right)
        actions = ctk.CTkFrame(header_inner, fg_color="transparent")
        actions.pack(side="right")

        def _clear_filters():
            if hasattr(self, 'sys_logger'):
                self.sys_logger.log("🧹 المستخدم قام بمسح فلاتر استعلام حركات العملاء وإفراغ الشاشة.")
            if hasattr(self, "ent_client_no"):
                self.ent_client_no.delete(0, "end")

            if hasattr(self, "cmb_acc_type"):
                self.cmb_acc_type.configure(values=["- أدخل العميل أولاً -"])
                self.cmb_acc_type.set("- أدخل العميل أولاً -")

            if hasattr(self, "cmb_currency"):
                self.cmb_currency.configure(values=["- اختر نوع الحساب أولاً -"])
                self.cmb_currency.set("- اختر نوع الحساب أولاً -")

            if hasattr(self, "ent_date_from"):
                self.ent_date_from.delete(0, "end")
            if hasattr(self, "ent_date_to"):
                self.ent_date_to.delete(0, "end")

            if hasattr(self, "lbl_branch_info"):
                self.lbl_branch_info.configure(text="—")

            if hasattr(self, "sheet"):
                try:
                    self.sheet.set_sheet_data([], reset_col_positions=False, reset_row_positions=True)
                except:
                    pass

        self.btn_clear_nuwairy = ctk.CTkButton(
            actions,
            text="مسح",
            fg_color="#F3F4F6",
            text_color="#111827",
            hover_color="#E5E7EB",
            font=("Segoe UI", 12, "bold"),
            height=38,
            corner_radius=10,
            command=_clear_filters
        )
        self.btn_clear_nuwairy.pack(side="left", padx=(0, 10))

        self.btn_search_nuwairy = ctk.CTkButton(
            actions,
            text="بحث الحركات 🔎",
            fg_color=FIB_GOLD,
            text_color="white",
            hover_color="#B78F38",
            font=("Segoe UI", 12, "bold"),
            height=38,
            corner_radius=10,
            command=self.nuwairy_fetch_transactions
        )
        self.btn_search_nuwairy.pack(side="left")

        # =========================
        # Filters Card
        # =========================
        form_card = ctk.CTkFrame(
            page,
            fg_color=COLOR_WHITE,
            corner_radius=14,
            border_width=1,
            border_color="#E6E8EB"
        )
        form_card.pack(fill="x", padx=10, pady=(0, 12))

        form = ctk.CTkFrame(form_card, fg_color="transparent")
        form.pack(fill="x", padx=16, pady=16)
        form.columnconfigure((0, 1, 2, 3), weight=1, pad=10)

        label_font = ("Segoe UI", 12, "bold")

        # Row 1
        ctk.CTkLabel(form, text="الفرع:", font=label_font, text_color=COLOR_TEXT_MAIN).grid(
            row=0, column=3, sticky="e", pady=(0, 8)
        )
        self.cmb_branch_box, self.cmb_branch = self._create_premium_select(
            form,
            values=["جاري التحميل..."],
            default="جاري التحميل...",
            title="اختر الفرع"
        )
        self.cmb_branch_box.grid(row=0, column=2, sticky="ew", pady=(0, 8), padx=(10, 0))

        ctk.CTkLabel(form, text="رقم العميل:", font=label_font, text_color=COLOR_TEXT_MAIN).grid(
            row=0, column=1, sticky="e", pady=(0, 8)
        )
        self.ent_client_no = ctk.CTkEntry(
            form,
            placeholder_text="اكتب رقم العميل واضغط Enter",
            height=40,
            corner_radius=10
        )
        self.ent_client_no.grid(row=0, column=0, sticky="ew", pady=(0, 8), padx=(10, 0))
        self.ent_client_no.bind("<Return>", self.nuwairy_fetch_accounts)

        # Row 2
        ctk.CTkLabel(form, text="نوع الحساب:", font=label_font, text_color=COLOR_TEXT_MAIN).grid(
            row=1, column=3, sticky="e", pady=(0, 8)
        )
        self.cmb_acc_type_box, self.cmb_acc_type = self._create_premium_select(
            form,
            values=["- أدخل العميل أولاً -"],
            default="- أدخل العميل أولاً -",
            title="اختر نوع الحساب"
        )
        self.cmb_acc_type_box.grid(row=1, column=2, sticky="ew", pady=(0, 8), padx=(10, 0))

        ctk.CTkLabel(form, text="العملة:", font=label_font, text_color=COLOR_TEXT_MAIN).grid(
            row=1, column=1, sticky="e", pady=(0, 8)
        )
        self.cmb_currency_box, self.cmb_currency = self._create_premium_select(
            form,
            values=["- أدخل العميل أولاً -"],
            default="- أدخل العميل أولاً -",
            title="اختر العملة"
        )
        self.cmb_currency_box.grid(row=1, column=0, sticky="ew", pady=(0, 8), padx=(10, 0))

        # Row 3 (Dates)
        ctk.CTkLabel(form, text="من تاريخ:", font=label_font, text_color=COLOR_TEXT_MAIN).grid(
            row=2, column=3, sticky="e"
        )
        self.ent_date_from = ctk.CTkEntry(
            form,
            placeholder_text="YYYY-MM-DD أو YYYYMMDD",
            height=40,
            corner_radius=10
        )
        self.ent_date_from.grid(row=2, column=2, sticky="ew", padx=(10, 0))

        ctk.CTkLabel(form, text="إلى تاريخ:", font=label_font, text_color=COLOR_TEXT_MAIN).grid(
            row=2, column=1, sticky="e"
        )
        self.ent_date_to = ctk.CTkEntry(
            form,
            placeholder_text="YYYY-MM-DD أو YYYYMMDD",
            height=40,
            corner_radius=10
        )
        self.ent_date_to.grid(row=2, column=0, sticky="ew", padx=(10, 0))

        # =========================
        # Info Card
        # =========================
        info_card = ctk.CTkFrame(
            page,
            fg_color=COLOR_WHITE,
            corner_radius=14,
            border_width=1,
            border_color="#E6E8EB"
        )
        info_card.pack(fill="x", padx=10, pady=(0, 12))

        info_inner = ctk.CTkFrame(info_card, fg_color="transparent")
        info_inner.pack(fill="x", padx=16, pady=14)

        ctk.CTkLabel(
            info_inner,
            text="بيانات العميل",
            font=("Segoe UI", 12, "bold"),
            text_color=COLOR_TEXT_MAIN
        ).pack(anchor="w")

        self.lbl_branch_info = ctk.CTkLabel(
            info_inner,
            text="—",
            font=("Segoe UI", 12),
            text_color="#4B5563",
            justify="left",
            anchor="w",
            wraplength=900
        )
        self.lbl_branch_info.pack(anchor="w", pady=(6, 0))

        # =========================
        # Results (Excel-like Sheet) + Toolbar
        # =========================
        table_card = ctk.CTkFrame(
            page,
            fg_color=COLOR_WHITE,
            corner_radius=14,
            border_width=1,
            border_color="#E6E8EB"
        )
        table_card.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        table_inner = ctk.CTkFrame(table_card, fg_color="transparent")
        table_inner.pack(fill="both", expand=True, padx=12, pady=12)

        toolbar = ctk.CTkFrame(table_inner, fg_color="transparent")
        toolbar.pack(fill="x", pady=(0, 10))

        self.ent_search = ctk.CTkEntry(toolbar, placeholder_text="بحث داخل النتائج…", height=36, corner_radius=10)
        self.ent_search.pack(side="left", fill="x", expand=True, padx=(0, 10))

        btn_export = ctk.CTkButton(
            toolbar, text="🖨️ Export PDF",
            fg_color=FIB_GREEN, hover_color="#0B5C3A",
            height=36, corner_radius=10,
            font=("Segoe UI", 12, "bold"),
            command=self.nuwairy_export_pdf
        )
        btn_export.pack(side="left")

        btn_export_excel = ctk.CTkButton(
            toolbar, text="📊 Export Excel",
            fg_color=FIB_GREEN, hover_color="#0B5C3A",
            height=36, corner_radius=10,
            font=("Segoe UI", 12, "bold"),
            command=self.nuwairy_export_excel
        )
        btn_export_excel.pack(side="left", padx=(10, 0))

        sheet_frame = ctk.CTkFrame(table_inner, fg_color="transparent")
        sheet_frame.pack(fill="both", expand=True)

        self._init_nuwairy_sheet(sheet_frame)

        # تحميل الفروع
        self.nuwairy_load_branches()

    def gl_load_codes(self):
        """تحميل القائمة وتخزينها في الذاكرة لتعمل مع الـ Premium Popup"""

        def fetch_task():
            import pandas as pd
            try:
                engine = self._get_db_connection()
                query = "SELECT snmsubb FROM [dbo].[TBL_GL_Codes] WHERE snmsubb IS NOT NULL AND snmsubb != ''"
                df = pd.read_sql(query, engine)

                if df.empty:
                    self.all_gl_codes = []
                else:
                    # حفظ الأسماء في الميموري فوراً
                    self.all_gl_codes = df["snmsubb"].astype(str).str.strip().drop_duplicates().tolist()
                    self.all_gl_codes.sort()
                    if hasattr(self, 'sys_logger'):
                        self.sys_logger.log(f"✅ تم تحميل {len(self.all_gl_codes)} كود أستاذ عام بنجاح في الخلفية.")

            except Exception as e:
                if hasattr(self, 'sys_logger'):
                    self.sys_logger.log(f"❌ خطأ أثناء تحميل أكواد الأستاذ العام: {e}", "ERROR")
                self.all_gl_codes = ["- خطأ في الاتصال بقاعدة البيانات -"]

        import threading
        threading.Thread(target=fetch_task, daemon=True).start()

    def filter_gl_codes(self, event):
        """دالة للبحث الحي داخل الـ 4000 اسم بسرعة البرق"""
        if not hasattr(self, 'all_gl_codes'):
            return

        # لو بيتحرك بالأسهم مش عايزين نبوظ الفلترة
        if event.keysym in ('Up', 'Down', 'Left', 'Right', 'Return'):
            return

        typed_text = self.combo_gl_acc.get().strip()

        if typed_text == "":
            filtered_codes = self.all_gl_codes[:50]
        else:
            # List Comprehension دي أسرع طريقة بحث في بايثون
            filtered_codes = [code for code in self.all_gl_codes if typed_text.lower() in code.lower()][:50]

            if not filtered_codes:
                filtered_codes = ["- لا توجد نتائج -"]

        # التحديث الفوري للقائمة
        self.combo_gl_acc.configure(values=filtered_codes)
    def gl_load_currencies(self):
        def fetch_task():
            import pandas as pd
            try:
                # استخدام دالة الاتصال الجاهزة بتاعتك
                engine = self._get_db_connection()
                query = "SELECT cnm FROM [dbo].[TBL_Currency] WHERE cnm IS NOT NULL"
                df = pd.read_sql(query, engine)

                if df.empty:
                    currencies = ["- لا توجد عملات -"]
                else:
                    currencies = df["cnm"].astype(str).str.strip().tolist()

                if hasattr(self, 'combo_gl_currency'):
                    self.after(0, lambda: self.combo_gl_currency.configure(values=currencies))
                    self.after(0, lambda: self.combo_gl_currency.set(currencies[0]))
                if hasattr(self, 'sys_logger'):
                    self.sys_logger.log("✅ تم تحميل قائمة العملات للأستاذ العام بنجاح.")
            except Exception as e:
                if hasattr(self, 'sys_logger'):
                    self.sys_logger.log(f"❌ خطأ أثناء تحميل العملات للأستاذ العام: {e}", "ERROR")
                if hasattr(self, 'combo_gl_currency'):
                    self.after(0, lambda: self.combo_gl_currency.configure(values=["- خطأ في الاتصال -"]))
                    self.after(0, lambda: self.combo_gl_currency.set("- خطأ في الاتصال -"))

        import threading
        threading.Thread(target=fetch_task, daemon=True).start()
    def _init_gl_sheet(self, parent):
        from tksheet import Sheet

        self.gl_sheet = Sheet(
            parent,
            show_x_scrollbar=True,
            show_y_scrollbar=True,
            show_row_index=False,
            show_top_left=False,
            align="center",
            header_align="center",
            height=450,
            width=900,
            outline_thickness=1,
            outline_color="#E6E8EB",
            grid_color="#E5E7EB",
            selected_cells_bg="#DDEFE8",
            selected_cells_fg="#111827",
        )

        headers = [
            "التاريخ",
            "الفرع",
            "رقم الحساب",
            "العملة",
            "البيان",
            "مدين",
            "دائن",
            "الرصيد",
            "رقم النمارة"
        ]
        self.gl_sheet.headers(headers)

        # زودنا مساحة للعمود الأخير (100)
        self.gl_sheet.set_column_widths([100, 120, 130, 90, 420, 120, 120, 130, 100])

        # السطر السحري: إخفاء العمود التاسع (الاندكس بتاعه 8)
        self.gl_sheet.hide_columns([8])

        self.gl_sheet.pack(fill="both", expand=True)

    def setup_gl_inquiry_ui(self, parent):

        import customtkinter as ctk

        # =========================
        # Page Wrapper
        # =========================
        page = ctk.CTkFrame(parent, fg_color="transparent")
        page.pack(fill="both", expand=True)

        # =========================
        # Header Bar (Title + Subtitle + Actions)
        # =========================
        header = ctk.CTkFrame(
            page,
            fg_color=COLOR_WHITE,
            corner_radius=14,
            border_width=1,
            border_color="#E6E8EB"
        )
        header.pack(fill="x", padx=10, pady=(0, 12))

        header_inner = ctk.CTkFrame(header, fg_color="transparent")
        header_inner.pack(fill="x", padx=16, pady=14)

        title_wrap = ctk.CTkFrame(header_inner, fg_color="transparent")
        title_wrap.pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(
            title_wrap,
            text="🔍 استعلام الأستاذ العام",
            font=("Segoe UI", 22, "bold"),
            text_color=FIB_GREEN
        ).pack(anchor="w")

        ctk.CTkLabel(
            title_wrap,
            text="ابحث بحساب الأستاذ العام، اختر الفرع والعملة، وحدد فترة التاريخ.",
            font=("Segoe UI", 12),
            text_color="#6B7280"
        ).pack(anchor="w", pady=(4, 0))

        # Actions (Right)
        actions = ctk.CTkFrame(header_inner, fg_color="transparent")
        actions.pack(side="right")

        self.btn_clear_gl = ctk.CTkButton(
            actions,
            text="مسح",
            fg_color="#F3F4F6",
            text_color="#111827",
            hover_color="#E5E7EB",
            font=("Segoe UI", 12, "bold"),
            height=38,
            corner_radius=10,
            command=self.gl_clear
        )
        self.btn_clear_gl.pack(side="left", padx=(0, 10))

        self.btn_search_gl = ctk.CTkButton(
            actions,
            text="بحث الحركات 🔎",
            fg_color=FIB_GOLD,
            text_color="white",
            hover_color="#B78F38",
            font=("Segoe UI", 12, "bold"),
            height=38,
            corner_radius=10,
            command=self.gl_search
        )
        self.btn_search_gl.pack(side="left")

        # =========================
        # Filters Card
        # =========================
        form_card = ctk.CTkFrame(
            page,
            fg_color=COLOR_WHITE,
            corner_radius=14,
            border_width=1,
            border_color="#E6E8EB"
        )
        form_card.pack(fill="x", padx=10, pady=(0, 12))

        form = ctk.CTkFrame(form_card, fg_color="transparent")
        form.pack(fill="x", padx=16, pady=16)
        form.columnconfigure((0, 1, 2, 3), weight=1, pad=10)

        label_font = ("Segoe UI", 12, "bold")

        # Row 1 (الفرع - الأستاذ العام)
        ctk.CTkLabel(form, text="الفرع:", font=label_font, text_color=COLOR_TEXT_MAIN).grid(
            row=0, column=3, sticky="e", pady=(0, 8)
        )
        self.cmb_gl_branch_box, self.combo_gl_branch = self._create_premium_select(
            form,
            values=["جاري التحميل..."],
            default="جاري التحميل...",
            title="اختر الفرع"
        )
        self.cmb_gl_branch_box.grid(row=0, column=2, sticky="ew", pady=(0, 8), padx=(10, 0))

        ctk.CTkLabel(form, text="الأستاذ العام:", font=label_font, text_color=COLOR_TEXT_MAIN).grid(
            row=0, column=1, sticky="e", pady=(0, 8)
        )

        # 🌟 التعديل هنا: تعريف الدوال أولاً قبل استخدامها في الزرار 🌟
        def set_gl_acc_value(selected_val):
            # بنقوله لو الزرار متسجل فعلاً، غير النص بتاعه
            if hasattr(self, 'btn_gl_acc_select'):
                self.btn_gl_acc_select.configure(text=f"{selected_val} 🔽")
                self.selected_gl_acc = selected_val
            else:
                print("تنبيه: زرار الأستاذ العام غير مسجل في الـ self")

        def open_gl_acc_popup_cmd():
            data = getattr(self, 'all_gl_codes', [])
            if not data:
                data = ["جاري تحميل البيانات، يرجى الانتظار ثانية..."]
            # التأكد إن الـ PremiumSearchPopup موجودة في الكود
            PremiumSearchPopup(self, "اختر الأستاذ العام", data, set_gl_acc_value)

        # ==========================================
        # زرار الأستاذ العام الأخضر (Solid Green)
        # ==========================================
        # تأكد إنك كاتب self. قبل اسم الزرار
        self.btn_gl_acc_select = ctk.CTkButton(
            form,
            text="- اختر الأستاذ العام - 🔽",
            font=("Segoe UI", 12, "bold"),
            text_color="white",
            fg_color=FIB_GREEN,  # لون البنك
            hover_color="#08472C",
            border_width=0,
            height=40,
            corner_radius=10,
            anchor="e",
            command=open_gl_acc_popup_cmd
        )
        self.btn_gl_acc_select.grid(row=0, column=0, sticky="ew", pady=(0, 8), padx=(10, 0))

        # خدعة بسيطة لضمان عمل دالة البحث والمسح بدون تعديل
        self.combo_gl_acc = self.btn_gl_acc_select
        self.combo_gl_acc.get = lambda: getattr(self, 'selected_gl_acc', "")

        # Row 2 (العملة - من تاريخ)
        ctk.CTkLabel(form, text="العملة:", font=label_font, text_color=COLOR_TEXT_MAIN).grid(
            row=1, column=3, sticky="e", pady=(0, 8)
        )
        self.cmb_gl_curr_box, self.combo_gl_currency = self._create_premium_select(
            form,
            values=["جاري التحميل..."],
            default="جاري التحميل...",
            title="اختر العملة"
        )
        self.cmb_gl_curr_box.grid(row=1, column=2, sticky="ew", pady=(0, 8), padx=(10, 0))

        ctk.CTkLabel(form, text="من تاريخ:", font=label_font, text_color=COLOR_TEXT_MAIN).grid(
            row=1, column=1, sticky="e", pady=(0, 8)
        )
        self.ent_gl_date_from = ctk.CTkEntry(
            form,
            placeholder_text="YYYY-MM-DD",
            height=40,
            corner_radius=10
        )
        self.ent_gl_date_from.grid(row=1, column=0, sticky="ew", pady=(0, 8), padx=(10, 0))

        # Row 3 (إلى تاريخ - زرار التحديث)
        ctk.CTkLabel(form, text="إلى تاريخ:", font=label_font, text_color=COLOR_TEXT_MAIN).grid(
            row=2, column=1, sticky="e"
        )
        self.ent_gl_date_to = ctk.CTkEntry(
            form,
            placeholder_text="YYYY-MM-DD",
            height=40,
            corner_radius=10
        )
        self.ent_gl_date_to.grid(row=2, column=0, sticky="ew", padx=(10, 0))

        # زر تحديث القوائم (في المكان الفاضي عشان الشكل يكمل)
        def refresh_all_gl_data():
            if hasattr(self, 'sys_logger'):
                self.sys_logger.log("🔄 المستخدم طلب تحديث قوائم (الفرع، الأستاذ العام، العملات) يدوياً.")
            if hasattr(self, 'gl_load_codes'): self.gl_load_codes()
            if hasattr(self, 'nuwairy_load_branches'): self.nuwairy_load_branches()
            if hasattr(self, 'gl_load_currencies'): self.gl_load_currencies()

        self.btn_refresh_gl = ctk.CTkButton(
            form,
            text="🔄 تحديث القوائم",
            fg_color="#F3F4F6",
            text_color="#111827",
            hover_color="#E5E7EB",
            font=("Segoe UI", 12, "bold"),
            height=40,
            corner_radius=10,
            command=refresh_all_gl_data
        )
        self.btn_refresh_gl.grid(row=2, column=2, sticky="ew", padx=(10, 0))

        # =========================
        # Info Card
        # =========================
        info_card = ctk.CTkFrame(
            page,
            fg_color=COLOR_WHITE,
            corner_radius=14,
            border_width=1,
            border_color="#E6E8EB"
        )
        info_card.pack(fill="x", padx=10, pady=(0, 12))

        info_inner = ctk.CTkFrame(info_card, fg_color="transparent")
        info_inner.pack(fill="x", padx=16, pady=14)

        ctk.CTkLabel(
            info_inner,
            text="بيانات الحساب",
            font=("Segoe UI", 12, "bold"),
            text_color=COLOR_TEXT_MAIN
        ).pack(anchor="w")

        self.lbl_gl_info = ctk.CTkLabel(
            info_inner,
            text="—",
            font=("Segoe UI", 12),
            text_color="#4B5563",
            justify="left",
            anchor="w",
            wraplength=900
        )
        self.lbl_gl_info.pack(anchor="w", pady=(6, 0))

        # =========================
        # Results (Excel-like Sheet) + Toolbar
        # =========================
        table_card = ctk.CTkFrame(
            page,
            fg_color=COLOR_WHITE,
            corner_radius=14,
            border_width=1,
            border_color="#E6E8EB"
        )
        table_card.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        table_inner = ctk.CTkFrame(table_card, fg_color="transparent")
        table_inner.pack(fill="both", expand=True, padx=12, pady=12)

        toolbar = ctk.CTkFrame(table_inner, fg_color="transparent")
        toolbar.pack(fill="x", pady=(0, 10))

        self.ent_gl_search = ctk.CTkEntry(toolbar, placeholder_text="بحث داخل النتائج…", height=36,
                                          corner_radius=10)
        self.ent_gl_search.pack(side="left", fill="x", expand=True, padx=(0, 10))

        btn_export = ctk.CTkButton(
            toolbar, text="🖨️ Export PDF",
            fg_color=FIB_GREEN, hover_color="#0B5C3A",
            height=36, corner_radius=10,
            font=("Segoe UI", 12, "bold"),
            command=self.gl_export_pdf
        )
        btn_export.pack(side="left")

        btn_export_excel = ctk.CTkButton(
            toolbar, text="📊 Export Excel",
            fg_color=FIB_GREEN, hover_color="#0B5C3A",
            height=36, corner_radius=10,
            font=("Segoe UI", 12, "bold"),
            command=self.gl_export_excel
        )
        btn_export_excel.pack(side="left", padx=(10, 0))

        sheet_frame = ctk.CTkFrame(table_inner, fg_color="transparent")
        sheet_frame.pack(fill="both", expand=True)

        self._init_gl_sheet(sheet_frame)

    def gl_clear(self):
        """تفريغ الفلاتر وجدول البيانات"""

        # 1. مسح الأستاذ العام (التعامل معاه كـ Button مش ComboBox)
        if hasattr(self, "btn_gl_acc_select"):
            default_text = "- اختر الأستاذ العام -"
            self.btn_gl_acc_select.configure(text=f"{default_text} 🔽")
            self.selected_gl_acc = ""  # تفريغ المتغير اللي بيسحب منه الـ get

        # 2. مسح الفرع
        if hasattr(self, "combo_gl_branch"):
            vals = getattr(self.combo_gl_branch, '_values_list', ["- اختر الفرع -"])
            if hasattr(self.combo_gl_branch, 'set'):
                self.combo_gl_branch.set(vals[0] if vals else "")

        # 3. مسح العملة
        if hasattr(self, "combo_gl_currency"):
            vals = getattr(self.combo_gl_currency, '_values_list', ["الكل (All)"])
            if hasattr(self.combo_gl_currency, 'set'):
                self.combo_gl_currency.set(vals[0] if vals else "")

        # 4. مسح التواريخ
        if hasattr(self, "ent_gl_date_from"):
            self.ent_gl_date_from.delete(0, "end")
        if hasattr(self, "ent_gl_date_to"):
            self.ent_gl_date_to.delete(0, "end")

        # 5. مسح شريط البحث السريع
        if hasattr(self, "ent_gl_search"):
            self.ent_gl_search.delete(0, "end")

        # 6. مسح بيانات الحساب (Info Label)
        if hasattr(self, "lbl_gl_info"):
            self.lbl_gl_info.configure(text="—")

        # 7. مسح الشيت (مع الحفاظ على 8 أعمدة عشان الشكل ميبوظش)
        if hasattr(self, "gl_sheet"):
            try:
                empty_row = ["", "", "", "", "", "", "", ""]
                self.gl_sheet.set_sheet_data([empty_row], reset_col_positions=False, reset_row_positions=True)
            except:
                pass

        if hasattr(self, 'sys_logger'):
            self.sys_logger.log("🧹 المستخدم قام بمسح فلاتر بحث الأستاذ العام وإفراغ الجدول.")

    def gl_export_excel(self):
        from tkinter import filedialog, messagebox
        from datetime import datetime
        import re
        import os
        import sys

        # ==========================================
        # 1. التأكد من وجود بيانات صالحة للتصدير
        # ==========================================
        if not hasattr(self, "gl_sheet"):
            messagebox.showwarning("تنبيه", "لا توجد بيانات للتصدير.")
            return

        rows = self.gl_sheet.get_sheet_data()

        # التحقق من أن الشيت لا يحتوي على رسالة التحميل أو فارغ
        if not rows or (len(rows) == 1 and ("جاري" in str(rows[0]) or "لا توجد" in str(rows[0]))):
            messagebox.showwarning("تنبيه", "لا توجد بيانات حقيقية للتصدير. قم بالبحث أولاً.")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel Files", "*.xlsx")],
            title="تصدير إكسيل - الأستاذ العام"
        )
        if not file_path:
            return
        if hasattr(self, 'sys_logger'):
            self.sys_logger.log(f"📥 بدء عملية تصدير الأستاذ العام إلى إكسيل.. مسار الحفظ المختار: [{file_path}]")

        # ==========================================
        # 2. الدوال المساعدة (Helpers)
        # ==========================================
        def money_to_float(v):
            if v is None:
                return 0.0
            s = str(v).strip()
            if not s:
                return 0.0
            s = s.replace(",", "").replace(" ", "")
            s = re.sub(r"[^0-9\.\-]", "", s)
            try:
                return float(s) if s else 0.0
            except Exception:
                return 0.0

        def parse_date_safe(s):
            s = (s or "").strip()
            for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d", "%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S"):
                try:
                    return datetime.strptime(s, fmt).date()
                except ValueError:
                    continue
            return None

        def safe_txt(x):
            return "" if x is None else str(x).strip()

        def resource_try(*names):
            """لجلب مسار اللوجو سواء في بيئة التطوير أو بعد الـ Build"""
            for n in names:
                try:
                    if getattr(sys, 'frozen', False) or '__compiled__' in globals():
                        p = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), n)
                    else:
                        p = os.path.join(os.path.dirname(os.path.abspath(__file__)), n)
                    if os.path.exists(p):
                        return p
                except Exception:
                    pass
            return None

        # ==========================================
        # 3. إعداد البيانات والتنسيقات (Data Prep)
        # ==========================================
        try:
            import xlsxwriter

            # --- ألوان الهوية البصرية ---
            GREEN = "#0B5C3A"
            GOLD = "#B08D2D"
            GRID = "#E6EAEE"
            ZEBRA = "#FAFBFC"
            TEXT = "#111827"
            MUTED = "#4B5563"
            SOFT = "#F9F3E6"
            OPEN_BG = "#FFF1D6"
            CLOSE_BG = "#FFF5DB"

            # --- جلب الفلاتر الأساسية ---
            gl_acc_name = self.combo_gl_acc.get().strip() if hasattr(self, 'combo_gl_acc') else "—"
            branch = self.combo_gl_branch.get().strip() if hasattr(self, 'combo_gl_branch') else "—"
            date_from = self.ent_gl_date_from.get().strip() if hasattr(self, 'ent_gl_date_from') else ""
            date_to = self.ent_gl_date_to.get().strip() if hasattr(self, 'ent_gl_date_to') else ""

            table_rows = []
            total_credit = 0.0
            total_debit = 0.0
            closing_balance = 0.0
            opening_balance = 0.0
            is_first_row = True

            # معالجة الصفوف القادمة من الواجهة
            # الترتيب في الواجهة: [التاريخ, الفرع, رقم الحساب, العملة, البيان, مدين, دائن, الرصيد, رقم النمارة]
            for r in rows:
                if len(r) < 8:
                    continue

                d = safe_txt(r[0])
                acc_no = safe_txt(r[2])
                curr = safe_txt(r[3])
                desc = safe_txt(r[4])
                debit = money_to_float(r[5])
                credit = money_to_float(r[6])
                bal = money_to_float(r[7])

                # 🌟 قراءة النمارة من العمود المخفي 🌟
                aseq = safe_txt(r[8]) if len(r) > 8 else ""

                if is_first_row:
                    opening_balance = bal - credit + debit
                    is_first_row = False

                total_credit += credit
                total_debit += debit
                closing_balance = bal

                # 🌟 إضافة aseq لمصفوفة البيانات 🌟
                table_rows.append((d, desc, aseq, acc_no, curr, debit, credit, bal))

            if (not date_from or not date_to) and table_rows:
                ds = [parse_date_safe(x[0]) for x in table_rows]
                ds = [dx for dx in ds if dx]
                if ds:
                    mn, mx = min(ds), max(ds)
                    date_from = date_from or mn.strftime("%Y-%m-%d")
                    date_to = date_to or mx.strftime("%Y-%m-%d")

            printed_at = datetime.now().strftime("%Y-%m-%d %H:%M")

            # 🌟 تعديل المتغيرات المستخرجة عشان توافق العدد الجديد 🌟
            credits_only = [(d, desc, c) for (d, desc, aseq, acc, cur, deb, c, bal) in table_rows if c > 0]
            debits_only = [(d, desc, deb) for (d, desc, aseq, acc, cur, deb, c, bal) in table_rows if deb > 0]
            top_credits = sorted(credits_only, key=lambda x: x[2], reverse=True)[:5]
            top_debits = sorted(debits_only, key=lambda x: x[2], reverse=True)[:5]

            daily = {}
            for d, desc, aseq, acc, cur, deb, c, bal in table_rows:
                daily.setdefault(d, {"credit": 0.0, "debit": 0.0})
                daily[d]["credit"] += c
                daily[d]["debit"] += deb

            daily_days = sorted(daily.keys(), key=lambda x: (parse_date_safe(x) or datetime.max.date(), x))

            # ==========================================
            # 4. بناء ملف الإكسيل
            # ==========================================
            wb = xlsxwriter.Workbook(file_path)

            # --- إعداد تنسيقات الخلايا ---
            fmt_title = wb.add_format(
                {"bold": True, "font_size": 18, "font_color": "white", "align": "center", "valign": "vcenter",
                 "bg_color": GREEN})
            fmt_gold_line = wb.add_format({"bg_color": GOLD})
            fmt_label = wb.add_format({"bold": True, "font_size": 11, "font_color": TEXT})
            fmt_value = wb.add_format({"font_size": 11, "font_color": TEXT})
            fmt_muted = wb.add_format({"font_size": 10, "font_color": MUTED})
            fmt_card_cell = wb.add_format({"border": 1, "border_color": GRID, "bg_color": "white"})
            fmt_card_outer = wb.add_format({"border": 2, "border_color": GOLD, "bg_color": "white"})
            fmt_kpi_box = wb.add_format(
                {"border": 1, "border_color": GRID, "align": "center", "valign": "vcenter", "text_wrap": True})
            fmt_kpi_open = wb.add_format(
                {"border": 1, "border_color": GRID, "align": "center", "valign": "vcenter", "text_wrap": True,
                 "bg_color": OPEN_BG})
            fmt_kpi_close = wb.add_format(
                {"border": 1, "border_color": GRID, "align": "center", "valign": "vcenter", "text_wrap": True,
                 "bg_color": CLOSE_BG})
            fmt_kpi_head = wb.add_format({"border": 2, "border_color": GOLD})
            fmt_header = wb.add_format(
                {"bold": True, "font_color": "white", "bg_color": GREEN, "align": "center", "valign": "vcenter",
                 "border": 1, "border_color": GRID})
            fmt_footer = wb.add_format({"font_size": 9, "font_color": MUTED})

            fmt_mon = wb.add_format(
                {"font_size": 10, "align": "center", "valign": "vcenter", "border": 1, "border_color": GRID,
                 "num_format": "#,##0.00"})
            fmt_mon_z = wb.add_format(
                {"font_size": 10, "align": "center", "valign": "vcenter", "border": 1, "border_color": GRID,
                 "num_format": "#,##0.00", "bg_color": ZEBRA})
            fmt_dat = wb.add_format(
                {"font_size": 10, "align": "center", "valign": "vcenter", "border": 1, "border_color": GRID})
            fmt_dat_z = wb.add_format(
                {"font_size": 10, "align": "center", "valign": "vcenter", "border": 1, "border_color": GRID,
                 "bg_color": ZEBRA})
            fmt_txt = wb.add_format(
                {"font_size": 10, "align": "right", "valign": "vcenter", "border": 1, "border_color": GRID,
                 "text_wrap": True})
            fmt_txt_z = wb.add_format(
                {"font_size": 10, "align": "right", "valign": "vcenter", "border": 1, "border_color": GRID,
                 "text_wrap": True, "bg_color": ZEBRA})

            fmt_summary_h = wb.add_format(
                {"bold": True, "font_color": "white", "bg_color": GREEN, "align": "center", "valign": "vcenter",
                 "border": 1, "border_color": GRID})
            fmt_summary_money = wb.add_format(
                {"border": 1, "border_color": GRID, "num_format": "#,##0.00", "align": "center", "valign": "vcenter"})
            fmt_summary_text = wb.add_format(
                {"border": 1, "border_color": GRID, "align": "right", "valign": "vcenter", "text_wrap": True})
            fmt_kpi_label = wb.add_format(
                {"bold": True, "align": "center", "valign": "vcenter", "border": 1, "border_color": GRID,
                 "bg_color": SOFT, "font_color": MUTED})

            # ==========================================
            # Sheet 1: حركات الأستاذ العام
            # ==========================================
            ws = wb.add_worksheet("حركات الأستاذ العام")
            ws.right_to_left()
            ws.hide_gridlines(2)

            # 🌟 تعديل مساحات الأعمدة عشان توافق 8 أعمدة بدل 7 🌟
            ws.set_column("A:A", 14)  # التاريخ
            ws.set_column("B:B", 40)  # البيان
            ws.set_column("C:C", 14)  # النمارة (العمود الجديد)
            ws.set_column("D:D", 18)  # رقم الحساب
            ws.set_column("E:E", 10)  # العملة
            ws.set_column("F:H", 16)  # مدين، دائن، الرصيد

            ws.set_row(0, 50)
            ws.set_row(1, 30)
            ws.set_row(2, 6)

            branch_title = branch.split(" - ")[-1] if branch else "—"

            # 🌟 تمديد الدمج لعمود H 🌟
            ws.merge_range("A1:G2", f"كشف حساب أستاذ عام  |  الفرع: {branch_title}", fmt_title)
            ws.write("H1", "", fmt_title)
            ws.write("H2", "", fmt_title)
            ws.merge_range("A3:H3", "", fmt_gold_line)

            logo_path = resource_try("logo.png", "logo.jpeg", "logo.jpg")
            if logo_path:
                ws.insert_image("H1", logo_path, {
                    "x_scale": 0.14, "y_scale": 0.14,
                    "x_offset": 20, "y_offset": 8,
                    "object_position": 2
                })

            # --- كارت بيانات الحساب ---
            r1, r2 = 4, 6
            c1, c2 = 0, 7  # 🌟 تمديد الكارت لـ 7 بدل 6 🌟
            for r in range(r1, r2 + 1):
                for c in range(c1, c2 + 1):
                    ws.write_blank(r, c, None, fmt_card_cell)

            for c in range(c1, c2 + 1):
                ws.write_blank(r1, c, None, fmt_card_outer)
                ws.write_blank(r2, c, None, fmt_card_outer)
            for r in range(r1, r2 + 1):
                ws.write_blank(r, c1, None, fmt_card_outer)
                ws.write_blank(r, c2, None, fmt_card_outer)

            ws.set_row(4, 25)
            ws.set_row(5, 25)
            ws.set_row(6, 25)

            ws.write("D5", "اسم الحساب:", fmt_label)
            ws.merge_range("A5:C5", gl_acc_name, fmt_value)

            ws.write("H5", "الفرع المختار:", fmt_label)
            ws.merge_range("E5:G5", branch, fmt_value)

            ws.write("H6", "تاريخ البحث:", fmt_label)
            ws.merge_range("E6:G6", f"{date_from} إلى {date_to}", fmt_muted)

            # --- أرقام الـ KPI ---
            kpi_row = 8
            ws.set_row(kpi_row, 44)
            for c in range(0, 8):
                ws.write_blank(kpi_row, c, None, fmt_kpi_head)

            ws.write(kpi_row, 0, f"عدد الحركات\n{len(table_rows)}", fmt_kpi_box)
            ws.merge_range(kpi_row, 1, kpi_row, 2, f"الرصيد الختامي\n{closing_balance:,.2f}", fmt_kpi_close)
            ws.write(kpi_row, 3, f"إجمالي مدين\n{total_debit:,.2f}", fmt_kpi_box)
            ws.write(kpi_row, 4, f"إجمالي دائن\n{total_credit:,.2f}", fmt_kpi_box)
            ws.merge_range(kpi_row, 5, kpi_row, 7, f"الرصيد الافتتاحي\n{opening_balance:,.2f}", fmt_kpi_open)

            # --- جدول الحركات الأساسي ---
            table_start = 10
            ws.set_row(table_start, 22)

            # 🌟 إضافة رقم النمارة كعمود ثالث في الجدول 🌟
            headers = ["التاريخ", "البيان", "رقم النمارة", "رقم الحساب الفرعي", "العملة", "مدين", "دائن", "الرصيد"]
            for col, head in enumerate(headers):
                ws.write(table_start, col, head, fmt_header)

            # 🌟 إضافة aseq في اللوب الخاص بكتابة الصفوف 🌟
            for i, (d, desc, aseq, acc, cur, deb, cred, bal) in enumerate(table_rows):
                rr = table_start + 1 + i
                zebra = (i % 2 == 1)
                ws.write(rr, 0, d, fmt_dat_z if zebra else fmt_dat)
                ws.write(rr, 1, desc if desc else "—", fmt_txt_z if zebra else fmt_txt)
                ws.write(rr, 2, aseq if aseq else "—", fmt_dat_z if zebra else fmt_dat)
                ws.write(rr, 3, acc, fmt_dat_z if zebra else fmt_dat)
                ws.write(rr, 4, cur, fmt_dat_z if zebra else fmt_dat)
                ws.write_number(rr, 5, deb, fmt_mon_z if zebra else fmt_mon)
                ws.write_number(rr, 6, cred, fmt_mon_z if zebra else fmt_mon)
                ws.write_number(rr, 7, bal, fmt_mon_z if zebra else fmt_mon)

            last_row = table_start + len(table_rows)

            ws.set_landscape()
            ws.fit_to_pages(1, 0)
            ws.set_zoom(90)
            ws.write(last_row + 2, 0, f"تاريخ الطباعة: {printed_at}", fmt_footer)

            # ==========================================
            # Sheet 2: ملخص وإحصائيات
            # ==========================================
            ws2 = wb.add_worksheet("ملخص وإحصائيات")
            ws2.right_to_left()
            ws2.hide_gridlines(2)

            ws2.set_row(0, 50)
            ws2.set_row(1, 30)
            ws2.set_row(2, 6)
            ws2.set_column("A:A", 18)
            ws2.set_column("B:B", 40)
            ws2.set_column("C:E", 18)

            ws2.merge_range("A1:D2", "ملخص الأستاذ العام", fmt_title)
            ws2.write("E1", "", fmt_title)
            ws2.write("E2", "", fmt_title)
            ws2.merge_range("A3:E3", "", fmt_gold_line)

            if logo_path:
                ws2.insert_image("E1", logo_path, {
                    "x_scale": 0.14, "y_scale": 0.14,
                    "x_offset": 10, "y_offset": 8,
                    "object_position": 2
                })

            ws2.write("E5", "اسم الحساب:", fmt_label)
            ws2.merge_range("A5:D5", gl_acc_name, fmt_value)

            ws2.write("E7", "رصيد الافتتاح", fmt_kpi_label)
            ws2.write_number("D7", opening_balance, wb.add_format(
                {"border": 1, "border_color": GRID, "bg_color": OPEN_BG, "num_format": "#,##0.00", "align": "center"}))
            ws2.write("C7", "الرصيد الختامي", fmt_kpi_label)
            ws2.write_number("B7", closing_balance, wb.add_format(
                {"border": 1, "border_color": GRID, "bg_color": CLOSE_BG, "num_format": "#,##0.00", "align": "center"}))

            ws2.write("E8", "إجمالي دائن", fmt_kpi_label)
            ws2.write_number("D8", total_credit, wb.add_format(
                {"border": 1, "border_color": GRID, "num_format": "#,##0.00", "align": "center"}))
            ws2.write("C8", "إجمالي مدين", fmt_kpi_label)
            ws2.write_number("B8", total_debit, wb.add_format(
                {"border": 1, "border_color": GRID, "num_format": "#,##0.00", "align": "center"}))
            ws2.write("A8", f"عدد الحركات: {len(table_rows)}",
                      wb.add_format({"border": 1, "border_color": GRID, "bg_color": SOFT, "align": "center"}))

            # --- أكبر 5 حركات دائنة ---
            ws2.write("E11", "أكبر 5 حركات دائنة", wb.add_format({"bold": True, "font_size": 12, "font_color": GREEN}))
            ws2.write_row("A12", ["القيمة", "البيان", "التاريخ"], fmt_summary_h)
            for i, (d, desc, val) in enumerate(top_credits):
                rr = 12 + 1 + i
                ws2.write_number(rr, 0, val, fmt_summary_money)
                ws2.write(rr, 1, desc if desc else "—", fmt_summary_text)
                ws2.write(rr, 2, d, fmt_dat)

            # --- أكبر 5 حركات مدينة ---
            ws2.write("E19", "أكبر 5 حركات مدينة", wb.add_format({"bold": True, "font_size": 12, "font_color": GREEN}))
            ws2.write_row("A20", ["القيمة", "البيان", "التاريخ"], fmt_summary_h)
            for i, (d, desc, val) in enumerate(top_debits):
                rr = 20 + 1 + i
                ws2.write_number(rr, 0, val, fmt_summary_money)
                ws2.write(rr, 1, desc if desc else "—", fmt_summary_text)
                ws2.write(rr, 2, d, fmt_dat)

            # --- ملخص المخطط اليومي (Chart) ---
            ws2.write("E27", "ملخص يومي (للمخطط)", wb.add_format({"bold": True, "font_size": 12, "font_color": GREEN}))
            ws2.write_row("A28", ["إجمالي مدين", "إجمالي دائن", "التاريخ"], fmt_summary_h)

            base_r = 28
            for i, d in enumerate(daily_days):
                rr = base_r + 1 + i
                ws2.write_number(rr, 0, daily[d]["debit"], fmt_summary_money)
                ws2.write_number(rr, 1, daily[d]["credit"], fmt_summary_money)
                ws2.write(rr, 2, d, fmt_dat)

            if daily_days:
                chart = wb.add_chart({"type": "column"})
                chart.add_series({
                    "name": "إجمالي دائن",
                    "categories": ["ملخص وإحصائيات", base_r + 1, 2, base_r + len(daily_days), 2],
                    "values": ["ملخص وإحصائيات", base_r + 1, 1, base_r + len(daily_days), 1],
                })
                chart.add_series({
                    "name": "إجمالي مدين",
                    "categories": ["ملخص وإحصائيات", base_r + 1, 2, base_r + len(daily_days), 2],
                    "values": ["ملخص وإحصائيات", base_r + 1, 0, base_r + len(daily_days), 0],
                })
                chart.set_title({"name": "السيولة (مدين/دائن) حسب اليوم"})
                chart.set_legend({"position": "bottom"})
                chart.set_size({"width": 600, "height": 300})
                ws2.insert_chart("A32", chart)

            wb.close()

            # --- إنهاء العملية بنجاح ---
            messagebox.showinfo("تم", "تم تصدير تقرير الأستاذ العام إلى إكسيل بنجاح ✅")

            if hasattr(self, 'sys_logger'):
                self.sys_logger.log(f"📄 تم تصدير بيانات الأستاذ العام إلى ملف: {file_path}")

            try:
                os.startfile(file_path)
            except Exception:
                pass

        except Exception as e:
            messagebox.showerror("خطأ", f"حدث خطأ أثناء تصدير Excel:\n{e}")
            if hasattr(self, 'sys_logger'):
                self.sys_logger.log(f"❌ فشل تصدير الملف: {e}", type="ERROR")
    def gl_search(self):
        """البحث الديناميكي للحركات وتعبئة الشيت بترتيب محاسبي دقيق وأداء صاروخي"""
        import tkinter.messagebox as messagebox
        import threading
        import pandas as pd

        gl_acc_name = self.combo_gl_acc.get().strip()
        branch_name = self.combo_gl_branch.get().strip()
        currency_name = self.combo_gl_currency.get().strip()
        date_from = self.ent_gl_date_from.get().strip()
        date_to = self.ent_gl_date_to.get().strip()
        if hasattr(self, 'sys_logger'):
            self.sys_logger.log(
                f"🔎 بدء بحث الأستاذ العام -> الحساب: [{gl_acc_name}] | الفرع: [{branch_name}] | العملة: [{currency_name}] | من: [{date_from}] إلى: [{date_to}]")
        # التأكد من اختيار أستاذ عام
        if not gl_acc_name or "جاري التحميل" in gl_acc_name or "- اختر" in gl_acc_name:
            messagebox.showwarning("تنبيه", "يرجى اختيار أستاذ عام صحيح أولاً.")
            return

        # التأكد من اختيار فرع
        if not branch_name or "جاري التحميل" in branch_name or "- اختر" in branch_name:
            messagebox.showwarning("تنبيه", "يرجى اختيار الفرع أولاً لتحديد جدول البحث.")
            return

        # استخراج اسم الفرع الصافي
        branch_name_only = branch_name.split(" - ")[-1].strip()

        # الحفاظ على شكل الشيت أثناء التحميل (8 أعمدة)
        # الحفاظ على شكل الشيت أثناء التحميل (9 أعمدة مش 8)
        if hasattr(self, "gl_sheet"):
            loading_row = ["", "", "", "⏳ جاري سحب البيانات...", "", "", "", "", ""]  # ضفنا عنصر فاضي في الآخر
            self.gl_sheet.set_sheet_data([loading_row], reset_col_positions=False, reset_row_positions=True)

        def search_task():
            try:
                engine = self._get_db_connection()

                # 1. تحديد كود العملة (إن وجد)
                target_curr_code = None
                if currency_name and currency_name != "الكل (All)":
                    curr_query = f"SELECT FCUR FROM [dbo].[TBL_Currency] WHERE CNM LIKE N'%{currency_name}%'"
                    curr_df = pd.read_sql(curr_query, engine)
                    if not curr_df.empty:
                        target_curr_code = str(curr_df.iloc[0]['FCUR']).strip()
                    else:
                        alt_curr_name = currency_name.replace('ي', 'ى')
                        curr_query_alt = f"SELECT FCUR FROM [dbo].[TBL_Currency] WHERE CNM LIKE N'%{alt_curr_name}%'"
                        curr_df_alt = pd.read_sql(curr_query_alt, engine)
                        if not curr_df_alt.empty:
                            target_curr_code = str(curr_df_alt.iloc[0]['FCUR']).strip()

                # 2. الاستعلام عن SGL و SSUBB من جدول الأكواد
                codes_query = f"SELECT TOP 1 SGL, SSUBB FROM [dbo].[TBL_GL_Codes] WHERE SNMSUBB = N'{gl_acc_name}'"
                codes_df = pd.read_sql(codes_query, engine)

                if codes_df.empty:
                    self.after(0,
                               lambda: messagebox.showerror("خطأ", "لم يتم العثور على أكواد SGL و SSUBB لهذا الاسم."))
                    self.after(0, lambda: self.gl_sheet.set_sheet_data([[]]))
                    return

                target_sgl = str(codes_df.iloc[0]['SGL']).strip()
                target_ssubb = str(codes_df.iloc[0]['SSUBB']).strip()

                # 3. تحديد اسم الجدول للحركات بناءً على الفرع
                branch_query = f"SELECT GL_TableName FROM [dbo].[TBL_Branches] WHERE BranchName LIKE N'{branch_name_only}'"
                branch_df = pd.read_sql(branch_query, engine)

                if branch_df.empty or pd.isna(branch_df.iloc[0]['GL_TableName']):
                    self.after(0, lambda: messagebox.showerror("خطأ", f"لم يتم العثور على جدول (GL_TableName)."))
                    self.after(0, lambda: self.gl_sheet.set_sheet_data([[]]))
                    return
                target_table = branch_df.iloc[0]['GL_TableName'].strip()

                credit_codes = ['1', '4']
                debit_codes = ['2', '3']

                # 4. حساب الرصيد التراكمي السابق (الافتتاحي) - باستخدام itertuples للسرعة
                opening_balance = 0.0
                if date_from:
                    op_query = f"SELECT AAMT, ACOD1 FROM [dbo].[{target_table}] WHERE AGL = '{target_sgl}' AND ASB = '{target_ssubb}' AND ADATM < '{date_from}'"
                    if target_curr_code is not None:
                        op_query += f" AND ACUR = '{target_curr_code}'"

                    op_df = pd.read_sql(op_query, engine)
                    for row in op_df.itertuples(index=False):
                        op_scod = str(row.ACOD1).strip() if pd.notna(row.ACOD1) else ""
                        try:
                            op_amt = abs(float(row.AAMT))
                        except:
                            op_amt = 0.0

                        if op_scod in credit_codes:
                            opening_balance += op_amt
                        elif op_scod in debit_codes:
                            opening_balance -= op_amt
                        else:
                            if float(row.AAMT) > 0:
                                opening_balance += op_amt
                            else:
                                opening_balance -= op_amt

                # 5. جلب حركات الفترة الحالية
                main_query = f"""
                    SELECT ADATM, ABIAN, AAMT, ASEQ, AGL, ASB, ACUR, ACOD1
                    FROM [dbo].[{target_table}] 
                    WHERE AGL = '{target_sgl}' AND ASB = '{target_ssubb}'
                """
                if target_curr_code is not None:
                    main_query += f" AND ACUR = '{target_curr_code}'"
                if date_from:
                    main_query += f" AND ADATM >= '{date_from}'"
                if date_to:
                    main_query += f" AND ADATM <= '{date_to}'"

                # 🔥 اللوجيك المحاسبي للترتيب:
                # 1. التاريخ (تصاعدي)
                # 2. نوع الحركة: الدائن (1، 4 أو سالب) ييجي قبل المدين (2، 3 أو موجب)
                # 3. القيمة المطلقة (تصاعدي)
                main_query += """ 
                    ORDER BY 
                        ADATM ASC,
                        CASE 
                            WHEN ACOD1 IN ('1', '4') THEN 1
                            WHEN ACOD1 IN ('2', '3') THEN 2
                            WHEN AAMT <= 0 THEN 1
                            ELSE 2
                        END ASC,
                        ABS(AAMT) ASC
                """

                results_df = pd.read_sql(main_query, engine)

                # طباعة اللوج للبيانات المسحوبة
                if hasattr(self, 'sys_logger'):
                    self.sys_logger.log(f"تم سحب {len(results_df)} حركة.")

                formatted_data = []
                running_balance = opening_balance

                # بناء الجدول باستخدام itertuples (أسرع بكتير من iterrows)
                for row in results_df.itertuples(index=False):
                    date_val = str(row.ADATM) if pd.notna(row.ADATM) else ""
                    desc = str(row.ABIAN) if pd.notna(row.ABIAN) else ""
                    scod1_val = str(row.ACOD1).strip() if pd.notna(row.ACOD1) else ""
                    full_acc_number = f"{str(row.AGL)}-{str(row.ASB)}"
                    aseq_val = str(row.ASEQ).strip() if pd.notna(row.ASEQ) else ""
                    try:
                        raw_amt = float(row.AAMT)
                        amt = abs(raw_amt)
                    except:
                        raw_amt = 0.0
                        amt = 0.0

                    debit = 0.0
                    credit = 0.0

                    if scod1_val in credit_codes:
                        credit = amt
                        running_balance += amt
                    elif scod1_val in debit_codes:
                        debit = amt
                        running_balance -= amt
                    else:
                        if raw_amt > 0:
                            debit = amt
                            running_balance += amt
                        else:
                            credit = amt
                            running_balance -= amt

                    formatted_data.append([
                        date_val,
                        branch_name_only,
                        full_acc_number,
                        currency_name if currency_name != "الكل (All)" else str(row.ACUR),
                        desc,
                        f"{debit:,.2f}" if debit > 0 else "0.00",
                        f"{credit:,.2f}" if credit > 0 else "0.00",
                        f"{running_balance:,.2f}",
                        aseq_val  # <--- إضافة رقم النمارة كعنصر تاسع هنا
                    ])

                if not formatted_data:
                    formatted_data = [["", "", "", "لا توجد حركات مطابقة لشروط البحث", "", "", "", "", ""]]

                # عرض البيانات في الشيت
                self.after(0, lambda: self.gl_sheet.set_sheet_data(formatted_data, reset_col_positions=False,
                                                                   reset_row_positions=True))

                if hasattr(self, 'sys_logger'):
                    self.sys_logger.log("✅ تم سحب وعرض بيانات الأستاذ العام بنجاح.")


            except Exception as e:

                if hasattr(self, 'sys_logger'):
                    self.sys_logger.log(f"❌ خطأ أثناء البحث: {e}", "ERROR")
                self.after(0, lambda: messagebox.showerror("خطأ برمجي", f"حدث خطأ أثناء جلب البيانات:\n{e}"))
                self.after(0, lambda: self.gl_sheet.set_sheet_data([["", "", "", "❌ حدث خطأ", "", "", "", "", ""]]))

        # تشغيل الفانكشن في Background Thread عشان الشاشة متهنجش
        threading.Thread(target=search_task, daemon=True).start()

    def setup_customer_inquiry_ui(self, parent):
        import customtkinter as ctk
        import threading
        import pandas as pd
        import re
        import logging

        # =========================================
        # 🚀 1. Background Caching (الفروع فقط)
        # =========================================
        self.branches_cache = {}

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
                print(f"Branch Caching Error: {e}")

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

        search_title = ctk.CTkLabel(right_col, text="البحث الذكي", font=("Segoe UI", 18, "bold"), text_color=FIB_GREEN)
        search_title.pack(anchor="e", padx=25, pady=(20, 10))

        self.search_container = ctk.CTkFrame(right_col, fg_color=BOX_BG, corner_radius=10, border_width=1,
                                             border_color="#CBD5E1", height=45)
        self.search_container.pack(fill="x", padx=20, pady=(0, 15))
        self.search_container.pack_propagate(False)

        def clear_search_bar():
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
                                            placeholder_text="اكتب اسم العميل...")
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

        def create_data_box(parent, row, col, label_text, key, icon):
            box_outer = ctk.CTkFrame(parent, fg_color="transparent")
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
        # 🧠 5. Search Engine & Modern List (🚀 Optimized)
        # =========================================
        self._search_timer = None

        def morphological_unglue_arabic(raw_name):
            if pd.isna(raw_name) or not raw_name: return "—"
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
            if self._search_timer:
                self.after_cancel(self._search_timer)
            self._search_timer = self.after(300, execute_search)

        def execute_search():
            raw_query = self.ent_cust_search.get().strip()
            if len(raw_query) < 2: return

            logging.info(f"User Searching for: '{raw_query}'")

            normalized_query = morphological_unglue_arabic(raw_query)

            pattern = re.sub(r'\s+', '%', normalized_query).replace("'", "''")
            pattern = re.sub(r'[يى]', '[يى]', pattern)
            pattern = re.sub(r'[اأإآ]', '[اأإآ]', pattern)
            pattern = re.sub(r'[هة]', '[هة]', pattern)
            pattern = re.sub(r'[وؤ]', '[وؤ]', pattern)
            pattern = re.sub(r'[ئ]', '[ئي]', pattern)

            for widget in self.results_scroll.winfo_children():
                widget.destroy()

            lbl_loading = ctk.CTkLabel(self.results_scroll, text="⚡ جاري البحث...", font=("Segoe UI", 13, "bold"),
                                       text_color=FIB_GOLD)
            lbl_loading.pack(pady=30)

            def fetch_data():
                try:
                    engine = self._get_db_connection()

                    # نفس الكويري بتاعتك بالظبط بدون أي تعديل
                    sql = f"""
                                        SELECT TOP 50 
                                            orig.BCLNT, orig.BNAME, orig.BSNO1, orig.BDAT2, 
                                            orig.BBR, orig.BADRS1, orig.BADRS2, orig.BADRS3, orig.BADRS4
                                        FROM [dbo].[TBL_Search_Names] AS search WITH (NOLOCK)
                                        INNER JOIN [dbo].[TBL_client_name] AS orig WITH (NOLOCK) 
                                            ON search.BCLNT = orig.BCLNT
                                        WHERE search.BNAME_SHRINK LIKE N'%{pattern}%'
                                    """
                    df = pd.read_sql(sql, engine)

                    if not df.empty:
                        df['DISPLAY_NAME'] = df['BNAME'].apply(morphological_unglue_arabic)

                    self.after(0, lambda: update_results_ui(df))
                except Exception as e:
                    print(f"DB Search Error: {e}")
                    logging.error(f"Search failed for '{raw_query}': {e}")
                    self.after(0, lambda: update_results_ui(pd.DataFrame()))

            threading.Thread(target=fetch_data, daemon=True).start()

        def update_results_ui(df):
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

                # =========================================
                # التعديل هنا فقط: شكل الليست المسطح والاحترافي
                # =========================================
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

                # خط فاصل رفيع تحت كل اسم
                ctk.CTkFrame(row_frame, fg_color="#E2E8F0", height=1).pack(fill="x", padx=10, pady=(0, 2))

        def load_customer_profile(cust_row):
            raw_name = str(cust_row['BNAME'])
            bclnt_code = str(cust_row['BCLNT']).replace('.0', '') if pd.notna(cust_row['BCLNT']) else "Unknown"

            logging.info(f"User viewed profile for: {raw_name} (Client Code: {bclnt_code})")

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
                except:
                    bbr_code = str(raw_bbr).strip()
                branch_name = self.branches_cache.get(bbr_code, "غير معرف")
                self.cust_fields["BBR"].configure(text=f"{branch_name} ({bbr_code})")

            addr_parts = [str(cust_row[col]) for col in ['BADRS1', 'BADRS2', 'BADRS3', 'BADRS4'] if
                          pd.notna(cust_row[col]) and str(cust_row[col]).strip() not in ('None', '', 'nan')]
            full_address = " - ".join(addr_parts) if addr_parts else "غير مسجل"
            self.cust_fields["FULL_ADDRESS"].configure(text=morphological_unglue_arabic(full_address))

        self.ent_cust_search.bind("<KeyRelease>", on_search_change)








    def gl_export_pdf(self):
        """تصدير PDF بالتنسيق السليم واعتبار أول حركة هي الرصيد الافتتاحي"""
        import tkinter.messagebox as messagebox
        from tkinter import filedialog
        from datetime import datetime
        import re, os
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.lib import colors
        from reportlab.lib.utils import ImageReader
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Spacer, Paragraph
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_RIGHT, TA_CENTER, TA_LEFT

        try:
            import arabic_reshaper
            from bidi.algorithm import get_display

            def ar(txt: str) -> str:
                txt = "" if txt is None else str(txt)
                reshaped = arabic_reshaper.reshape(txt)
                return get_display(reshaped, base_dir='R')
        except Exception:
            def ar(txt: str) -> str:
                return "" if txt is None else str(txt)

        try:
            rows = self.gl_sheet.get_sheet_data()
        except Exception:
            rows = []

        if not rows or (len(rows) == 1 and ("جاري" in str(rows[0]) or "لا توجد" in str(rows[0]))):
            messagebox.showwarning("تنبيه", "لا توجد بيانات للتصدير.")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF Files", "*.pdf")],
            initialfile=f"كشف_حساب_أستاذ_عام_{datetime.now().strftime('%Y%m%d')}.pdf"
        )

        if not file_path:
            return
        if hasattr(self, 'sys_logger'):
            self.sys_logger.log(f"📥 بدء عملية تصدير الأستاذ العام إلى إكسيل.. مسار الحفظ المختار: [{file_path}]")
        GREEN = colors.HexColor("#1F6B4B")
        GOLD = colors.HexColor("#B08D2D")
        DGRAY = colors.HexColor("#5B6770")
        GRID = colors.HexColor("#E7ECEF")
        BORDER = colors.HexColor("#C9D1D8")
        ZEBRA = colors.HexColor("#FAFBFC")
        OPEN_BG = colors.HexColor("#FFF1D6")
        CLOSE_BG = colors.HexColor("#FFF5DB")

        def resource_path(relative_path):
            import sys
            try:
                base_path = sys._MEIPASS
            except Exception:
                base_path = os.path.abspath(".")
            return os.path.join(base_path, relative_path)

        def resource_try(*names):
            for n in names:
                p = resource_path(n)
                if p and os.path.exists(p): return p
            return None

        def money_to_float(s):
            if not s: return 0.0
            s = str(s).replace(",", "").replace(" ", "")
            s = re.sub(r"[^0-9\.\-]", "", s)
            try:
                return float(s) if s else 0.0
            except:
                return 0.0

        def fmt2(x: float) -> str:
            return f"{x:,.2f}"

        gl_acc_name = self.combo_gl_acc.get().strip()
        branch_name = self.combo_gl_branch.get().strip().split(" - ")[-1]
        currency_name = self.combo_gl_currency.get().strip()
        date_from = self.ent_gl_date_from.get().strip()
        date_to = self.ent_gl_date_to.get().strip()

        period_text = ""
        if date_from or date_to:
            period_text = f"الفترة: {date_from if date_from else 'البداية'}  إلى  {date_to if date_to else 'اليوم'}"

        total_credit = 0.0
        total_debit = 0.0
        closing_balance = 0.0
        opening_balance_val = 0.0
        trx_count = 0

        # ✅ هنا السحر: قراءة رصيد الافتتاح من أول حركة في الشيت مباشرة
        for r in rows:
            if len(r) < 8: continue

            if trx_count == 0:
                opening_balance_val = money_to_float(r[7])  # رصيد أول حركة

            total_debit += money_to_float(r[5])
            total_credit += money_to_float(r[6])
            closing_balance = money_to_float(r[7])
            trx_count += 1

        printed_at = datetime.now().strftime("%Y-%m-%d %H:%M")

        try:
            font_path = resource_try("Amiri-Regular.ttf")
            if not font_path:
                messagebox.showerror("خطأ", "ملف الخط Amiri-Regular.ttf غير موجود.")
                return

            pdfmetrics.registerFont(TTFont("AR", font_path))
            base_font = "AR"
            styles = getSampleStyleSheet()

            st_right = ParagraphStyle("right_ar", parent=styles["Normal"], fontName=base_font, fontSize=10, leading=14,
                                      alignment=TA_RIGHT, textColor=colors.black)
            st_left = ParagraphStyle("left_muted", parent=styles["Normal"], fontName=base_font, fontSize=10, leading=14,
                                     alignment=TA_LEFT, textColor=DGRAY)
            st_center_date = ParagraphStyle("center_date", parent=styles["Normal"], fontName=base_font, fontSize=9,
                                            leading=12, alignment=TA_CENTER, textColor=colors.black)
            st_kpi_label = ParagraphStyle("kpi_label", parent=styles["Normal"], fontName=base_font, fontSize=9,
                                          leading=11, alignment=TA_CENTER, textColor=DGRAY)
            st_kpi_value = ParagraphStyle("kpi_value", parent=styles["Normal"], fontName=base_font, fontSize=11,
                                          leading=14, alignment=TA_CENTER, textColor=colors.black)

            doc = SimpleDocTemplate(file_path, pagesize=A4, leftMargin=14 * mm, rightMargin=14 * mm, topMargin=46 * mm,
                                    bottomMargin=14 * mm)

            logo_img = None
            logo_path = resource_try("logo.png", "logo.jpg", "faisal_logo.png", "faisal_logo.jpg")
            if logo_path:
                try:
                    logo_img = ImageReader(logo_path)
                except:
                    pass

            def draw_header_footer(canv, doc_):
                canv.saveState()
                ww, hh = A4
                header_h = 34 * mm
                canv.setFillColor(GREEN)
                canv.rect(0, hh - header_h, ww, header_h, fill=1, stroke=0)
                canv.setFillColor(GOLD)
                canv.rect(0, hh - header_h, ww, 2 * mm, fill=1, stroke=0)

                if logo_img:
                    canv.setFillColor(colors.white)
                    canv.roundRect(13 * mm, hh - header_h + 4.5 * mm, 26 * mm, 26 * mm, 3 * mm, fill=1, stroke=0)
                    canv.drawImage(logo_img, 15 * mm, hh - header_h + 6.5 * mm, width=22 * mm, height=22 * mm,
                                   preserveAspectRatio=True, mask='auto')

                canv.setFillColor(colors.white)
                canv.setFont(base_font, 16)
                title = f"كشف الأستاذ العام | فرع: {branch_name}" if branch_name else "كشف الأستاذ العام"
                canv.drawCentredString(ww / 2, hh - 17.5 * mm, ar(title))

                footer_y = 9 * mm
                canv.setStrokeColor(BORDER)
                canv.setLineWidth(0.5)
                canv.line(14 * mm, footer_y + 6 * mm, ww - 14 * mm, footer_y + 6 * mm)
                canv.setFillColor(DGRAY)
                canv.setFont(base_font, 9)
                canv.drawString(14 * mm, footer_y, ar(f"تاريخ الطباعة: {printed_at}"))
                canv.drawRightString(ww - 14 * mm, footer_y, ar(f"صفحة {doc_.page}"))
                canv.restoreState()

            story = []

            right_lines = [f"حساب الأستاذ العام: {gl_acc_name}", f"الفرع: {branch_name}"]
            left_lines = [f"العملة: {currency_name}", period_text if period_text else "الفترة: غير محددة"]

            info_tbl = Table([
                [[Paragraph(ar(x), st_right) for x in right_lines], [Paragraph(ar(x), st_left) for x in left_lines]]
            ], colWidths=[116 * mm, 66 * mm])

            info_tbl.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                ("BOX", (0, 0), (-1, -1), 1, GOLD),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, GRID),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]))
            story.append(info_tbl)
            story.append(Spacer(1, 5 * mm))

            # KPIs
            kpis = [
                ("رصيد الافتتاح", fmt2(opening_balance_val)),
                ("إجمالي دائن", fmt2(total_credit)),
                ("إجمالي مدين", fmt2(total_debit)),
                ("الرصيد الختامي", fmt2(closing_balance)),
                ("عدد الحركات", str(trx_count)),
            ]
            kpi_cells = [[Paragraph(ar(l), st_kpi_label), Spacer(1, 1 * mm), Paragraph(ar(v), st_kpi_value)] for l, v in
                         kpis]
            kpi_tbl = Table([kpi_cells], colWidths=[182 * mm / 5.0] * 5)
            kpi_tbl.setStyle(TableStyle([
                ("BOX", (0, 0), (-1, -1), 1, GOLD),
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                ("LINEBEFORE", (1, 0), (4, 0), 0.25, GRID),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("BACKGROUND", (0, 0), (0, 0), OPEN_BG),
                ("BACKGROUND", (3, 0), (3, 0), CLOSE_BG),
            ]))
            story.append(kpi_tbl)
            story.append(Spacer(1, 5 * mm))

            # Table Header
            header = [ar("الرصيد"), ar("دائن"), ar("مدين"), ar("البيان"), ar("التاريخ")]
            table_data = [header]

            for r in rows:
                if len(r) < 8: continue

                raw_date = str(r[0]).strip()
                # فصل الوقت عن التاريخ لمنع التداخل
                formatted_date = raw_date.replace(" ", "<br/>")
                date_val = Paragraph(formatted_date, st_center_date)

                # --- بداية تعديل البيان ورقم النمارة ---
                desc_val = str(r[4]).strip()

                # هنقرا النمارة من العمود التاسع (الاندكس 8) مع حماية لو الشيت فاضي
                aseq_val = str(r[8]).strip() if len(r) > 8 else ""

                if aseq_val and aseq_val not in ["None", "", "0"]:
                    # تشكيل العربي
                    desc_ar = ar(desc_val)
                    aseq_ar = ar(f"رقم النمارة: {aseq_val}")

                    # دمجهم في سطرين (البيان بخط عادي، النمارة تحته بخط أصغر ولون رمادي)
                    final_desc_html = f"{desc_ar}<br/><font color='#5B6770' size='8'>{aseq_ar}</font>"
                else:
                    final_desc_html = ar(desc_val)

                desc_para = Paragraph(final_desc_html, st_right)
                # --- نهاية التعديل ---

                debit_val = str(r[5])
                credit_val = str(r[6])
                bal_val = str(r[7])

                table_data.append([bal_val, credit_val, debit_val, desc_para, date_val])

            # مقاسات تمنع أي تداخل (الإجمالي 182 مم)
            main_tbl = Table(table_data, colWidths=[25 * mm, 20 * mm, 20 * mm, 88 * mm, 29 * mm], repeatRows=1)
            main_tbl.setStyle(TableStyle([
                ("FONTNAME", (0, 0), (-1, -1), base_font),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("FONTSIZE", (0, 1), (-1, -1), 9),
                ("BACKGROUND", (0, 0), (-1, 0), GREEN),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("LINEBELOW", (0, 0), (-1, 0), 1.2, GOLD),
                ("GRID", (0, 0), (-1, -1), 0.25, BORDER),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ZEBRA]),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 1), (2, -1), "CENTER"),
                ("ALIGN", (3, 1), (3, -1), "RIGHT"),
                ("RIGHTPADDING", (3, 1), (3, -1), 6),
                ("ALIGN", (4, 1), (4, -1), "CENTER"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            story.append(main_tbl)

            doc.build(story, onFirstPage=draw_header_footer, onLaterPages=draw_header_footer)
            messagebox.showinfo("تم", "تم تصدير PDF بنجاح ✅")
            try:
                os.startfile(file_path)
            except:
                pass

        except Exception as e:
            messagebox.showerror("خطأ", f"حدث خطأ أثناء تصدير PDF:\n{e}")
            self.sys_logger.log(f"❌ فشل تصدير ملف الأستاذ العام: {e}", "ERROR")

    def _premium_dropdown(self, anchor_widget, values, on_select, title="اختر", width=420, height=360):
        import customtkinter as ctk

        values = [str(v) for v in (values or [])]

        if getattr(self, "_active_premium_dd", None):
            try:
                self._active_premium_dd.destroy()
            except:
                pass
            self._active_premium_dd = None

        top = ctk.CTkToplevel(self)
        self._active_premium_dd = top
        top.title(title)
        top.resizable(False, False)
        top.transient(self)
        top.attributes("-topmost", True)

        try:
            ax = anchor_widget.winfo_rootx()
            ay = anchor_widget.winfo_rooty()
            ah = anchor_widget.winfo_height()
            top.geometry(f"{width}x{height}+{ax}+{ay + ah + 6}")
        except:
            top.geometry(f"{width}x{height}")

        wrap = ctk.CTkFrame(top, corner_radius=12)
        wrap.pack(fill="both", expand=True, padx=10, pady=10)

        qvar = ctk.StringVar(value="")
        ent = ctk.CTkEntry(wrap, textvariable=qvar, placeholder_text="ابحث...", height=38)
        ent.pack(fill="x", padx=10, pady=(10, 8))
        ent.focus_set()

        sc = ctk.CTkScrollableFrame(wrap, corner_radius=10)
        sc.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        btns = []

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

        def rebuild(items):
            for b in btns:
                try:
                    b.destroy()
                except:
                    pass
            btns.clear()

            if not items:
                b = ctk.CTkButton(sc, text="لا توجد نتائج", height=36,
                                  fg_color="transparent", hover=False, text_color="#6B7280")
                b.pack(fill="x", pady=4)
                btns.append(b)
                return

            for v in items:
                b = ctk.CTkButton(
                    sc, text=v, height=36,
                    fg_color="transparent",
                    hover_color="#F3F4F6",
                    text_color="#111827",
                    anchor="e",
                    command=lambda vv=v: choose(vv)
                )
                b.pack(fill="x", pady=2)
                btns.append(b)

        def apply_filter(*_):
            q = (qvar.get() or "").strip().lower()
            if not q:
                rebuild(values)
                return
            rebuild([v for v in values if q in v.lower()])

        qvar.trace_add("write", apply_filter)
        rebuild(values)

        top.bind("<Escape>", lambda e: close())
        top.protocol("WM_DELETE_WINDOW", close)

    def _create_premium_select(self, parent, values, default, title, width_popup=420, height_popup=360):
        import customtkinter as ctk

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

        # 3. إنشاء الاتصال وتمرير اللوجر
        from database import DatabaseEngine
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
        from tkinter import messagebox
        import pandas as pd

        try:
            engine = self._get_db_connection()

            query = """
                    SELECT BranchCode, BranchName, TableName
                    FROM [dbo].[TBL_Branches]
                    WHERE BranchName IS NOT NULL
                    """
            df = pd.read_sql(query, engine)

            if df.empty:
                self.cmb_branch.configure(values=["- لا توجد فروع -"])
                self.cmb_branch.set("- لا توجد فروع -")

                # تحديث حقل الأستاذ العام في حالة عدم وجود بيانات
                if hasattr(self, 'combo_gl_branch'):
                    self.combo_gl_branch.configure(values=["- لا توجد فروع -"])
                    self.combo_gl_branch.set("- لا توجد فروع -")

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
                self.cmb_branch.configure(values=branches_list)
                self.cmb_branch.set(branches_list[0])

                # تحديث حقل الأستاذ العام بالبيانات الصحيحة
                if hasattr(self, 'combo_gl_branch'):
                    self.combo_gl_branch.configure(values=branches_list)
                    self.combo_gl_branch.set(branches_list[0])
            else:
                self.cmb_branch.configure(values=["- لا توجد فروع -"])
                self.cmb_branch.set("- لا توجد فروع -")

                # تحديث حقل الأستاذ العام لو القائمة فاضية
                if hasattr(self, 'combo_gl_branch'):
                    self.combo_gl_branch.configure(values=["- لا توجد فروع -"])
                    self.combo_gl_branch.set("- لا توجد فروع -")

                self.branch_mapping = {}
                self.branch_table_mapping = {}

        except Exception as e:
            # رسالة أوضح للمستخدم
            err = str(e)
            self.cmb_branch.configure(values=["- خطأ في الاتصال بالداتا -"])
            self.cmb_branch.set("- خطأ في الاتصال بالداتا -")

            # إظهار الخطأ في حقل الأستاذ العام
            if hasattr(self, 'combo_gl_branch'):
                self.combo_gl_branch.configure(values=["- خطأ في الاتصال -"])
                self.combo_gl_branch.set("- خطأ في الاتصال -")

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

    def _premium_dropdown(self, anchor_widget, values, on_select,
                          title="اختر", width=420, height=420):
        import customtkinter as ctk

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

    def nuwairy_fetch_accounts(self, event=None):
        from tkinter import messagebox
        import pandas as pd
        from sqlalchemy import text
        import getpass
        import re

        branch_name = self.cmb_branch.get()
        client_no = self.ent_client_no.get().strip()
        if hasattr(self, 'sys_logger'):
            self.sys_logger.log(f"🔍 أداة الاستعلام: المستخدم يبحث عن رقم العميل [{client_no}]")

        if not client_no:
            messagebox.showwarning("تنبيه", "يرجى إدخال رقم العميل أولاً")
            return

        branch_code = str(self.branch_mapping.get(branch_name, "")).strip()
        table_name = self.branch_table_mapping.get(branch_code)
        if not branch_code:
            messagebox.showerror("خطأ", "لم يتم العثور على كود الفرع!")
            return

        if not table_name:
            messagebox.showerror("خطأ", f"لا يوجد جدول مربوط بالفرع ده (BranchCode={branch_code})")
            return

        try:
            engine = self._get_db_connection()

            # ==========================================
            # 🛡️ البوابة الأمنية: حماية الحسابات المحظورة
            # ==========================================
            current_user = getpass.getuser()
            current_user = re.sub(r'[\\/*?:"<>|]', "_", current_user)

            check_query = text("""
                DECLARE @User NVARCHAR(100) = :user;
                DECLARE @Client NVARCHAR(100) = :client;

                IF EXISTS (SELECT 1 FROM [dbo].[TBL_RESTRICTED_NUWAIRY] WHERE Client_No = @Client)
                BEGIN
                    IF EXISTS (SELECT 1 FROM [dbo].[TBL_RESTRICTED_NUWAIRY] WHERE Client_No = @Client AND Allowed_User = @User) OR @User = 'Admin'
                        SELECT 'ALLOWED' AS Status
                    ELSE
                        SELECT 'DENIED' AS Status
                END
                ELSE
                BEGIN
                    SELECT 'ALLOWED' AS Status
                END
            """)

            perm_df = pd.read_sql(check_query, engine, params={"user": current_user, "client": client_no})

            if not perm_df.empty and perm_df.iloc[0]['Status'] == 'DENIED':
                messagebox.showerror("مرفوض",
                                     "⛔ هذا الحساب محظور (VIP / حسابات داخلية). ليس لديك صلاحية للاستعلام عنه.")
                if hasattr(self, 'sys_logger'):
                    self.sys_logger.log(
                        f"🚨 وصول مرفوض: المستخدم [{current_user}] حاول الاستعلام عن العميل المحظور [{client_no}]",
                        "WARNING")

                # إخفاء وتصفير أي بيانات للعميل
                self.cmb_acc_type.configure(values=["- حساب محظور -"])
                self.cmb_acc_type.set("- حساب محظور -")
                self.cmb_currency.configure(values=["-"])
                self.cmb_currency.set("-")
                if hasattr(self, "lbl_branch_info"):
                    self.lbl_branch_info.configure(text="⛔ تم حجب بيانات العميل للحماية.")

                if hasattr(self, "sheet"):
                    self.sheet.set_sheet_data([], reset_col_positions=False, reset_row_positions=True)
                return
            # ==========================================
            # ✅ نهاية البوابة الأمنية - اللوجيك القديم بيكمل من هنا
            # ==========================================

            # التعديل هنا: جلبنا أنواع الحسابات والعملات فقط بدل كل حركات العميل!
            q1 = text(f"""
                SELECT DISTINCT ngl, ncur
                FROM {table_name}
                WHERE NCLNT = :client_no
            """)
            df = pd.read_sql(q1, engine, params={"client_no": client_no})

            q2 = text(f"""
                SELECT DISTINCT Bname, BADRS3, BADRS4
                FROM {table_name}
                WHERE BCLNT = :client_no
            """)
            df2 = pd.read_sql(q2, engine, params={"client_no": client_no})

            if hasattr(self, "lbl_branch_info"):
                if not df2.empty:
                    bname = str(df2.iloc[0].get("Bname", "") or "")
                    adr3 = str(df2.iloc[0].get("BADRS3", "") or "")
                    adr4 = str(df2.iloc[0].get("BADRS4", "") or "")
                    self.lbl_branch_info.configure(text=f"اسم العميل: {bname}\nالعنوان: {adr3}   {adr4}")
                else:
                    self.lbl_branch_info.configure(text="لا توجد بيانات فرع/عنوان لهذا العميل.")

            # مسحنا الـ self.nuwairy_df لأننا مش هنحمل الملايين في الميموري

            if df.empty:
                self.cmb_acc_type.configure(values=["لا يوجد حسابات"])
                self.cmb_acc_type.set("لا يوجد حسابات")
                self.cmb_currency.configure(values=["-"])
                self.cmb_currency.set("-")
                return

            # ===== reference: Currency
            q_cur = text("SELECT FCUR, CNM FROM TBL_Currency")
            cur_df = pd.read_sql(q_cur, engine)
            currency_code_to_name = dict(
                zip(cur_df["FCUR"].astype(str).str.strip(), cur_df["CNM"].astype(str).str.strip())
            )

            # ===== reference: Account Types
            q_acc = text("SELECT CCOD, CNM FROM dbo.TBL_AccTypes")
            acc_df = pd.read_sql(q_acc, engine)
            acc_code_to_name = dict(
                zip(acc_df["CCOD"].astype(str).str.strip(), acc_df["CNM"].astype(str).str.strip())
            )

            # ===== reference: Transaction Codes
            q_trx = text("SELECT ncod1, ntnm FROM dbo.TBL_trx_code")
            trx_df = pd.read_sql(q_trx, engine)
            trx_code_to_name = dict(
                zip(trx_df["ncod1"].astype(str).str.strip(), trx_df["ntnm"].astype(str).str.strip())
            )

            self.acc_code_to_name = acc_code_to_name
            self.trx_code_to_name = trx_code_to_name

            acc_codes = sorted(df["ngl"].astype(str).str.strip().unique().tolist())
            cur_codes = sorted(df["ncur"].astype(str).str.strip().unique().tolist())

            acc_names = [acc_code_to_name.get(code, f"({code})") for code in acc_codes]
            cur_names = [currency_code_to_name.get(code, f"({code})") for code in cur_codes]

            self.acc_name_to_code = {name: code for name, code in zip(acc_names, acc_codes)}
            self.currency_name_to_code = {name: code for name, code in zip(cur_names, cur_codes)}

            self.cmb_acc_type.configure(values=acc_names)
            self.cmb_acc_type.set(acc_names[0] if acc_names else "لا يوجد حسابات")

            self.cmb_currency.configure(values=cur_names)
            self.cmb_currency.set(cur_names[0] if cur_names else "-")
            if hasattr(self, 'sys_logger'):
                self.sys_logger.log(f"✅ تم سحب البيانات بنجاح للعميل [{client_no}]")
        except Exception as e:
            messagebox.showerror("خطأ", f"حدث خطأ أثناء البحث في الداتابيز:\n{e}")
            if hasattr(self, 'sys_logger'):
                self.sys_logger.log(f"❌ خطأ أثناء الاستعلام عن العميل [{client_no}]: {e}", type="ERROR")

    def nuwairy_fetch_transactions(self):
        from tkinter import messagebox
        import threading

        # ✅ التعديل السابع: منع الضغط المتكرر (Thread Explosion)
        if getattr(self, "_loading", False):
            return

        client_no = self.ent_client_no.get().strip()
        acc_type_name = str(self.cmb_acc_type.get()).strip()
        currency_name = str(self.cmb_currency.get()).strip()

        date_from = self.ent_date_from.get().strip()
        date_to = self.ent_date_to.get().strip()

        if not client_no:
            messagebox.showwarning("تنبيه", "يرجى إدخال رقم العميل أولاً")
            return
        if acc_type_name in ("- أدخل العميل أولاً -", "لا يوجد حسابات", "", "-"):
            messagebox.showwarning("تنبيه", "يرجى اختيار نوع الحساب")
            return
        if currency_name in ("- أدخل العميل أولاً -", "", "-"):
            messagebox.showwarning("تنبيه", "يرجى اختيار العملة")
            return

        # ✅ التعديل الثامن: حد إجباري للتاريخ لتقليل البيانات
        if not date_from and not date_to:
            messagebox.showwarning("تنبيه", "برجاء تحديد فترة التاريخ (من - إلى) لتقليل حجم البيانات.")
            return

        # 👇 تسجيل بيانات البحث في اللوج
        if hasattr(self, 'sys_logger'):
            self.sys_logger.log(
                f"🔎 بدء استعلام حركات العملاء -> رقم العميل: [{client_no}] | الحساب: [{acc_type_name}] | العملة: [{currency_name}] | من: [{date_from}] إلى: [{date_to}]")
        self._loading = True

        if hasattr(self, 'btn_search'):
            self.btn_search.configure(text="جاري التحميل...", state="disabled")

        threading.Thread(target=self._bg_fetch_transactions_logic, args=(client_no, acc_type_name, currency_name),
                         daemon=True).start()

    def _bg_fetch_transactions_logic(self, client_no, acc_type_name, currency_name):
        import pandas as pd
        from sqlalchemy import text
        from tkinter import messagebox

        try:
            engine = self._get_db_connection()

            if not hasattr(self, "currency_code_to_name"):
                cur_df = pd.read_sql("SELECT FCUR, CNM FROM TBL_Currency", engine)
                self.currency_code_to_name = dict(
                    zip(cur_df["FCUR"].astype(str).str.strip(), cur_df["CNM"].astype(str).str.strip()))

            if not hasattr(self, "acc_code_to_name"):
                acc_df = pd.read_sql("SELECT CCOD, CNM FROM dbo.TBL_AccTypes", engine)
                self.acc_code_to_name = dict(
                    zip(acc_df["CCOD"].astype(str).str.strip(), acc_df["CNM"].astype(str).str.strip()))

            if not hasattr(self, "trx_code_to_name"):
                trx_df = pd.read_sql("SELECT ncod1, ntnm FROM dbo.TBL_trx_code", engine)
                self.trx_code_to_name = dict(
                    zip(trx_df["ncod1"].astype(str).str.strip(), trx_df["ntnm"].astype(str).str.strip()))
                if not hasattr(self, "trx_code_to_name"):
                    trx_df = pd.read_sql("SELECT ncod1, ntnm FROM dbo.TBL_trx_code", engine)
                    self.trx_code_to_name = dict(
                        zip(trx_df["ncod1"].astype(str).str.strip(), trx_df["ntnm"].astype(str).str.strip()))

                # ✅ جبناه على نفس المحاذاة (برا الـ if اللي فوق)
            if not hasattr(self, "add_code_to_name") or not self.add_code_to_name:
                try:
                    add_df = pd.read_sql("SELECT ccod, cnm FROM dbo.TBL_add_codes", engine)
                    cleaned_ccod = add_df["ccod"].astype(str).str.strip().apply(
                        lambda x: x[:-2] if str(x).endswith(".0") else x)
                    cleaned_cnm = add_df["cnm"].astype(str).str.strip()
                    self.add_code_to_name = dict(zip(cleaned_ccod, cleaned_cnm))

                    #print(f"🔴 DEBUG 1: تم تحميل عدد {len(self.add_code_to_name)} كود من جدول TBL_add_codes")
                except Exception as e:
                    if hasattr(self, 'sys_logger'):
                        self.sys_logger.log(f"⚠️ فشل جلب جدول TBL_add_codes: {e}", "WARNING")
                    self.add_code_to_name = {}

            acc_type_code = getattr(self, "acc_name_to_code", {}).get(acc_type_name, acc_type_name)
            currency_code = getattr(self, "currency_name_to_code", {}).get(currency_name, currency_name)

            try:
                date_from_val = self._date_to_yyyymmdd(self.ent_date_from.get())
                date_to_val = self._date_to_yyyymmdd(self.ent_date_to.get())
            except Exception as ve:
                error_msg = str(ve)
                self.after(0, lambda msg=error_msg: messagebox.showwarning("تنبيه", msg))
                self._loading = False
                self._reset_search_btn()
                return

            branch_name = self.cmb_branch.get()
            branch_code = str(self.branch_mapping.get(branch_name, "")).strip()
            table_name = self.branch_table_mapping.get(branch_code)

            # ✅ حساب الرصيد في 31-03-2017 باستخدام Pandas لمنع أخطاء الـ Execution
            balance_2017_val = 0.0
            try:
                bal_query = f"""
                    SELECT ncod1, namt
                    FROM {table_name} WITH (NOLOCK)
                    WHERE NCLNT = :client_no 
                      AND ngl = :acc_code 
                      AND ncur = :curr_code 
                      AND ndatm <= '20170331'
                """
                bal_params = {"client_no": client_no, "acc_code": str(acc_type_code), "curr_code": str(currency_code)}

                with engine.connect() as conn:
                    bal_df = pd.read_sql(text(bal_query), conn, params=bal_params)

                for r_bal in bal_df.itertuples(index=False):
                    # التعديل الأول: الاعتماد على رقم الكود لتحديد الإضافة والخصم
                    t_code = str(getattr(r_bal, "ncod1", "")).strip()

                    # معالجة لو القيمة NULL
                    t_amt_raw = getattr(r_bal, "namt", 0.0)
                    t_amt = float(t_amt_raw if pd.notnull(t_amt_raw) else 0.0)
                    amt_abs = abs(t_amt)

                    if t_code in ("3", "4"):  # سحب أو خصم (مدين)
                        balance_2017_val -= amt_abs
                    elif t_code in ("1", "2"):  # إيداع أو إضافة (دائن)
                        balance_2017_val += amt_abs
                    else:
                        # حل احتياطي لو ظهر كود جديد غير معروف
                        if t_amt < 0:
                            balance_2017_val -= amt_abs
                        else:
                            balance_2017_val += amt_abs
            except Exception as e:
                if hasattr(self, 'sys_logger'):
                    self.sys_logger.log(f"⚠️ فشل جلب رصيد 2017: {e}", "WARNING")

            query = f"""
                SELECT TOP 5000 ngl, ncur, ndatm, nbian, namt, ncod1, nsb, nseq, ncod2
                FROM {table_name} WITH (NOLOCK)
                WHERE NCLNT = :client_no 
                  AND ngl = :acc_code 
                  AND ncur = :curr_code
            """
            params_dict = {"client_no": client_no, "acc_code": str(acc_type_code), "curr_code": str(currency_code)}

            if date_from_val:
                query += " AND ndatm >= :date_from"
                params_dict["date_from"] = date_from_val
            if date_to_val:
                query += " AND ndatm <= :date_to"
                params_dict["date_to"] = date_to_val

            query += " ORDER BY ndatm ASC"

            with engine.connect() as conn:
                view_df = pd.read_sql(text(query), conn, params=params_dict)



            if view_df.empty:
                self.after(0, lambda: messagebox.showinfo("معلومة", "لا توجد حركات مطابقة للبيانات المختارة."))
                if hasattr(self, 'sys_logger'):
                    self.sys_logger.log(f"⚠️ لا توجد حركات للعميل [{client_no}] تتطابق مع شروط البحث.", "WARNING")

                if hasattr(self, "sheet"):
                    self.after(0, lambda: self.sheet.set_sheet_data([], reset_col_positions=False,
                                                                    reset_row_positions=True))
                return

            # ✅ تنظيف البيانات من الـ nan بشكل جذري
            view_df["nbian"] = view_df["nbian"].fillna("").astype(str).str.strip()
            view_df["nbian"] = view_df["nbian"].replace(["nan", "NaN", "None"], "")

            view_df["ncod1"] = view_df["ncod1"].astype(str).str.strip()
            view_df["namt"] = pd.to_numeric(view_df["namt"], errors="coerce").fillna(0)

            # 🆕 تنظيف عمود ncod2 لو موجود
            if "ncod2" in view_df.columns:
                view_df["ncod2"] = view_df["ncod2"].fillna("").astype(str).str.strip()
                view_df["ncod2"] = view_df["ncod2"].replace(["nan", "NaN", "None", "<NA>"], "")
                # في حالة إن البانداس حول الرقم لـ float (مثلا 1.0 بدل 1) بنشيل الـ .0
                view_df["ncod2"] = view_df["ncod2"].apply(lambda x: x[:-2] if str(x).endswith(".0") else x)

            trx_map = getattr(self, "trx_code_to_name", {})
            acc_map = getattr(self, "acc_code_to_name", {})
            add_map = getattr(self, "add_code_to_name", {})
            rows_data = []

            for r in view_df.itertuples(index=False):
                ndatm = str(getattr(r, "ndatm", "")).strip()
                ndatm_fmt = f"{ndatm[:4]}-{ndatm[4:6]}-{ndatm[6:]}" if len(ndatm) == 8 and ndatm.isdigit() else ndatm

                # التعديل الثاني: الاعتماد على رقم الكود لتصنيف الحركات في كشف الحساب
                # التعديل الثاني: الاعتماد على رقم الكود لتصنيف الحركات في كشف الحساب
                trx_code = str(getattr(r, "ncod1", "")).strip()
                # 🛡️ الحماية الأولى: ضفنا str()
                trx_name = str(trx_map.get(trx_code, trx_code) or "").strip()

                # 🆕 استخراج ncod2 والبحث عن اسمه في القاموس
                ncod2_val = str(getattr(r, "ncod2", "")).strip()
                # 🛡️ الحماية الثانية الأهم: ضفنا str() هنا عشان ميديناش خطأ الـ float
                doc_name = str(add_map.get(ncod2_val, "")).strip()

                amt = float(getattr(r, "namt", 0.0))
                amt_abs = abs(amt)

                if trx_code in ("3", "4"):  # سحب أو خصم (مدين)
                    credit, debit = 0.0, amt_abs
                elif trx_code in ("1", "2"):  # إيداع أو إضافة (دائن)
                    credit, debit = amt_abs, 0.0
                else:
                    # حل احتياطي لو ظهر كود جديد غير معروف
                    credit, debit = (0.0, amt_abs) if amt < 0 else (amt_abs, 0.0)

                rows_data.append({
                    'ndatm_raw': ndatm,
                    'ndatm_fmt': ndatm_fmt,
                    'desc': getattr(r, "nbian", ""),
                    'credit': credit,
                    'debit': debit,
                    'trx_name': trx_name,
                    'gl_main_name': acc_map.get(str(getattr(r, "ngl", "")).strip(), str(getattr(r, "ngl", "")).strip()),
                    'gl_sub': str(getattr(r, "nsb", "")).strip(),
                    'nseq': str(getattr(r, "nseq", "")).strip(),
                    'doc_name': doc_name # 🆕 إضافة اسم المستند للداتا
                })

            rows_data.sort(key=lambda x: (
                x['ndatm_raw'],
                x['debit'] > 0,
                max(x['credit'], x['debit'])
            ))

            running_balance = 0.0
            for item in rows_data:
                running_balance += item['credit'] - item['debit']
                item['balance'] = running_balance

            opening_balance = rows_data[0]['balance'] - rows_data[0]['credit'] + rows_data[0][
                'debit'] if rows_data else 0.0

            def fmt_money(x: float) -> str:
                return f"{x:,.2f}" if x != 0.0 else ""

            rows = []
            for item in rows_data:
                rows.append([
                    item['ndatm_fmt'],
                    item['desc'],
                    fmt_money(item['credit']),
                    fmt_money(item['debit']),
                    f"{item['balance']:,.2f}",
                    item['trx_name'],
                    item['gl_main_name'],
                    item['gl_sub'],
                    item['nseq'],
                    item['doc_name'] # Index [9]
                ])

            if not hasattr(self, "sheet"): return
            self.after(0, lambda: self.sheet.set_sheet_data(rows, reset_col_positions=False, reset_row_positions=True))

            self.nuwairy_last_rows = rows
            self.nuwairy_last_meta = {
                "client_no": client_no,
                "account_no": client_no,
                "branch_name": str(self.cmb_branch.get()).strip() if hasattr(self, "cmb_branch") else "",
                "acc_type": acc_type_name,
                "currency": currency_name,
                "date_from": self.ent_date_from.get().strip() if hasattr(self, "ent_date_from") else "",
                "date_to": self.ent_date_to.get().strip() if hasattr(self, "ent_date_to") else "",
                "client_info": self.lbl_branch_info.cget("text") if hasattr(self, "lbl_branch_info") else "",
                "opening_balance": f"{opening_balance:,.2f}",
                "balance_2017": f"{balance_2017_val:,.2f}"
            }
            if hasattr(self, 'sys_logger'):
                self.sys_logger.log(f"✅ تم عرض {len(rows)} حركة للعميل [{client_no}] بنجاح.")
        except Exception as e:
            error_msg = str(e)
            if hasattr(self, 'sys_logger'):
                self.sys_logger.log(f"❌ فشل جلب حركات العميل [{client_no}]: {error_msg}", "ERROR")
            self.after(0, lambda msg=error_msg: messagebox.showerror("خطأ", f"حدث خطأ:\n{msg}"))
        finally:
            self._loading = False
            self._reset_search_btn()

    def _reset_search_btn(self):
        if hasattr(self, 'btn_search'):
            self.after(0, lambda: self.btn_search.configure(text="بحث", state="normal"))

    def nuwairy_export_pdf(self):

        from tkinter import filedialog, messagebox
        from datetime import datetime
        import re
        import os
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.lib import colors
        from reportlab.lib.utils import ImageReader
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Spacer, Paragraph
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_RIGHT, TA_CENTER, TA_LEFT

        lang_choice = messagebox.askyesnocancel("اللغة / Language",
                                                "اضغط نعم للغة الإنجليزية، لا للغة العربية\nPress Yes for English, No for Arabic")
        if lang_choice is None:
            if hasattr(self, 'sys_logger'): self.sys_logger.log("⚠️ تم إلغاء التصدير.", type="WARNING")
            return
        lang = "en" if lang_choice else "ar"

        # ==========================================
        # 1. قاموس المصطلحات البنكية الثابتة (Offline)
        # ==========================================
        loc = {
            "اسم العميل:": {"ar": "اسم العميل:", "en": "Customer Name:"},
            "العنوان:": {"ar": "العنوان:", "en": "Address:"},
            "رقم الحساب:": {"ar": "رقم الحساب:", "en": "Account No:"},
            "نوع الحساب:": {"ar": "نوع الحساب:", "en": "Account Type:"},
            "العملة:": {"ar": "العملة:", "en": "Currency:"},
            "جنيه مصري": {"ar": "جنيه مصري", "en": "EGP"},
            "دولار أمريكي": {"ar": "دولار أمريكي", "en": "USD"},
            "الفترة:": {"ar": "الفترة:", "en": "Period:"},
            "إلى": {"ar": "إلى", "en": "to"},
            "رصيد 31-03-2017:": {"ar": "رصيد 31-03-2017:", "en": "Balance 31-03-2017:"},
            "رصيد الافتتاح": {"ar": "رصيد الافتتاح", "en": "Opening Balance"},
            "إجمالي دائن": {"ar": "إجمالي دائن", "en": "Total Credit"},
            "إجمالي مدين": {"ar": "إجمالي مدين", "en": "Total Debit"},
            "الرصيد الختامي": {"ar": "الرصيد الختامي", "en": "Closing Balance"},
            "عدد الحركات": {"ar": "عدد الحركات", "en": "Trx Count"},
            "تاريخ الطباعة:": {"ar": "تاريخ الطباعة:", "en": "Printed at:"},
            "صفحة": {"ar": "صفحة", "en": "Page"},
            "كشف حساب": {"ar": "كشف حساب", "en": "Account Statement"},
            "فرع:": {"ar": "فرع:", "en": "Branch:"},
            "رقم النمارة:": {"ar": "رقم النمارة:", "en": "Doc No:"},
            "الرصيد": {"ar": "الرصيد", "en": "Balance"},
            "دائن": {"ar": "دائن", "en": "Credit"},
            "مدين": {"ar": "مدين", "en": "Debit"},
            "البيان / نوع المستند": {"ar": "البيان / نوع المستند", "en": "Description / Doc Type"},
            "التاريخ": {"ar": "التاريخ", "en": "Date"},
            "—": {"ar": "—", "en": "—"},
            "سحب": {"ar": "سحب", "en": "Withdrawal"},
            "خصم": {"ar": "خصم", "en": "Debit"},
            "إيداع": {"ar": "إيداع", "en": "Deposit"},
            "اضافه": {"ar": "اضافه", "en": "Credit Add"},
            "إضافة": {"ar": "إضافة", "en": "Credit Add"},
            "نقدي": {"ar": "نقدي", "en": "Cash"},
            "تحويل": {"ar": "تحويل", "en": "Transfer"},
            "عمولة": {"ar": "عمولة", "en": "Commission"},
            "جاري": {"ar": "جاري", "en": "Current Account"},
            "توفير": {"ar": "توفير", "en": "Savings Account"},
            "تغطيه المكشوف من الجارى": {"ar": "تغطيه المكشوف من الجارى", "en": "Overdraft Coverage"},
            "مصاريف فتح الحسابات الجديدة": {"ar": "مصاريف فتح الحسابات الجديدة", "en": "New Account Opening Fees"},
            "000035 / مصاريف فتح الحساب ات الجديدةح": {"ar": "مصاريف فتح الحسابات الجديدة",
                                                       "en": "New Account Opening Fees"},
            "000046 / مصاريف فتح الحساب ات الجديدةح": {"ar": "مصاريف فتح الحسابات الجديدة",
                                                       "en": "New Account Opening Fees"},
            "عائد الربع الثالث": {"ar": "عائد الربع الثالث", "en": "Q3 Return"},
            "عائد الربع الرابع": {"ar": "عائد الربع الرابع", "en": "Q4 Return"},
            "مصاريف خدمه الاستثمار": {"ar": "مصاريف خدمه الاستثمار", "en": "Investment Service Fees"},
            "دمغه كشف حساب": {"ar": "دمغه كشف حساب", "en": "Statement Stamp Tax"},
        }

        def t(word):
            word_str = str(word).strip()
            return loc.get(word_str, {}).get(lang, word_str)

        # ==========================================
        # 2. دالة الترجمة الصوتية للأسماء والعناوين (Offline)
        # ==========================================
        def transliterate_ar_to_en(text):
            if not text: return ""
            text = str(text).strip()

            # معالجة المقاطع الشائعة أولاً
            replacements = {
                "عبد ال": "Abd El-", "عبدال": "Abd El-", "عبد ": "Abd ",
                "ابو ": "Abou ", "أبو ": "Abou ", " ابو ": " Abou ",
                " الدين": " El-Din", "الدين": "El-Din",
                " الله": " Allah", "الله": "Allah",
                " ال": " El-", "ال": "El-"
            }
            for ar_str, en_str in replacements.items():
                text = text.replace(ar_str, en_str)

            # خريطة الحروف المتبقية
            char_map = {
                'أ': 'A', 'ا': 'A', 'إ': 'E', 'آ': 'A', 'ب': 'B', 'ت': 'T', 'ث': 'Th',
                'ج': 'G', 'ح': 'H', 'خ': 'Kh', 'د': 'D', 'ذ': 'Z', 'ر': 'R', 'ز': 'Z',
                'س': 'S', 'ش': 'Sh', 'ص': 'S', 'ض': 'D', 'ط': 'T', 'ظ': 'Z', 'ع': 'A',
                'غ': 'Gh', 'ف': 'F', 'ق': 'Q', 'ك': 'K', 'ل': 'L', 'م': 'M', 'ن': 'N',
                'ه': 'H', 'ة': 'a', 'و': 'W', 'ي': 'Y', 'ى': 'a', 'ئ': 'E', 'ء': 'A', 'ؤ': 'O',
                '١': '1', '٢': '2', '٣': '3', '٤': '4', '٥': '5', '٦': '6', '٧': '7', '٨': '8', '٩': '9', '٠': '0'
            }

            result = ""
            for char in text:
                result += char_map.get(char, char)  # لو مش حرف عربي ينزل زي ما هو (أرقام/مسافات)

            # تظبيط شكل الحروف (أول حرف كابيتال والباقي سمول في كل كلمة)
            return " ".join([word.capitalize() for word in result.split()])

        # ==========================================
        # 3. دالة معالجة العربي عشان مايطلعش مقلوب
        # ==========================================
        try:
            import arabic_reshaper
            from bidi.algorithm import get_display

            def ar(txt: str) -> str:
                txt = "" if txt is None else str(txt)
                # بنعمل معالجة للعربي حتى لو التقرير إنجليزي عشان الوصف اللي مالوش ترجمة
                return get_display(arabic_reshaper.reshape(txt))
        except Exception:
            def ar(txt: str) -> str:
                return "" if txt is None else str(txt)

        rows = getattr(self, "nuwairy_last_rows", None)
        meta = getattr(self, "nuwairy_last_meta", {}) or {}

        if not rows:
            messagebox.showwarning("تنبيه", "لا توجد بيانات للتصدير. اعمل بحث الحركات أولاً.")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF Files", "*.pdf")]
        )

        if not file_path:
            return

        GREEN = colors.HexColor("#1F6B4B")
        GOLD = colors.HexColor("#B08D2D")
        DGRAY = colors.HexColor("#5B6770")
        GRID = colors.HexColor("#E7ECEF")
        BORDER = colors.HexColor("#C9D1D8")
        ZEBRA = colors.HexColor("#FAFBFC")
        OPEN_BG = colors.HexColor("#FFF1D6")
        CLOSE_BG = colors.HexColor("#FFF5DB")

        def resource_try(*names):
            for n in names:
                try:
                    p = resource_path(n)
                    if p and os.path.exists(p):
                        return p
                except Exception:
                    pass
            return None

        def money_to_float(s):
            if s is None: return 0.0
            s = str(s).strip()
            if not s: return 0.0
            s = s.replace(",", "").replace(" ", "")
            s = re.sub(r"[^0-9\.\-]", "", s)
            try:
                return float(s) if s else 0.0
            except Exception:
                return 0.0

        def fmt2(x: float) -> str:
            return f"{x:,.2f}"

        def _parse_date_safe(s: str):
            s = (s or "").strip()
            for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"):
                try:
                    return datetime.strptime(s, fmt).date()
                except:
                    pass
            return None

        def safe_one_line(x: str) -> str:
            x = "" if x is None else str(x)
            return " ".join(x.replace("\r", " ").replace("\n", " ").split()).strip()

        dates = []
        for r in rows:
            if r and len(r) > 0:
                d = _parse_date_safe(r[0])
                if d: dates.append(d)
        min_date = min(dates) if dates else None
        max_date = max(dates) if dates else None

        if min_date and max_date:
            period_text = f"{t('الفترة:')} {min_date.strftime('%Y-%m-%d')}  {t('إلى')}  {max_date.strftime('%Y-%m-%d')}"
        else:
            df_ = (meta.get("date_from") or "").strip()
            dt_ = (meta.get("date_to") or "").strip()
            period_text = f"{t('الفترة:')} {df_}  {t('إلى')}  {dt_}" if (df_ or dt_) else ""

        total_credit = 0.0
        total_debit = 0.0
        closing_balance = 0.0
        for r in rows:
            if len(r) < 5: continue
            total_credit += money_to_float(r[2])
            total_debit += money_to_float(r[3])
            closing_balance = money_to_float(r[4])

        printed_at = datetime.now().strftime("%Y-%m-%d %H:%M")

        opening_balance_txt = (meta.get("opening_balance") or "").strip()
        opening_balance_val = money_to_float(opening_balance_txt) if opening_balance_txt else 0.0

        client_no = (meta.get("client_no") or "").strip()
        account_no = (meta.get("account_no") or "").strip()
        if not account_no: account_no = client_no

        def make_logo_transparent(input_path, output_path, white_threshold=245):
            try:
                from PIL import Image
                im = Image.open(input_path).convert("RGBA")
                pixels = im.getdata()
                new_pixels = []
                for rr, gg, bb, aa in pixels:
                    if rr >= white_threshold and gg >= white_threshold and bb >= white_threshold:
                        new_pixels.append((rr, gg, bb, 0))
                    else:
                        new_pixels.append((rr, gg, bb, aa))
                im.putdata(new_pixels)
                im.save(output_path, "PNG")
                return True
            except Exception:
                return False

        try:
            font_path = resource_try("Amiri-Regular.ttf")
            if not font_path:
                messagebox.showerror("خطأ", "ملف الخط Amiri-Regular.ttf غير موجود جنب gui.py")
                return

            pdfmetrics.registerFont(TTFont("AR", font_path))
            base_font = "AR"

            styles = getSampleStyleSheet()
            align_choice = TA_LEFT if lang == "en" else TA_RIGHT

            st_right = ParagraphStyle("right_ar", parent=styles["Normal"], fontName=base_font, fontSize=10.2,
                                      leading=14, alignment=align_choice, textColor=colors.black)
            st_right_small = ParagraphStyle("right_ar_small", parent=styles["Normal"], fontName=base_font, fontSize=8.8,
                                            leading=11.2, alignment=align_choice, textColor=DGRAY)
            st_center_small = ParagraphStyle("center_small", parent=styles["Normal"], fontName=base_font, fontSize=9.2,
                                             leading=12, alignment=TA_CENTER, textColor=DGRAY)
            st_kpi_label = ParagraphStyle("kpi_label", parent=styles["Normal"], fontName=base_font, fontSize=8.6,
                                          leading=10.5, alignment=TA_CENTER, textColor=DGRAY)
            st_kpi_value = ParagraphStyle("kpi_value", parent=styles["Normal"], fontName=base_font, fontSize=12.2,
                                          leading=14, alignment=TA_CENTER, textColor=colors.black)

            w, h = A4
            header_h = 34 * mm
            doc = SimpleDocTemplate(file_path, pagesize=A4, leftMargin=14 * mm, rightMargin=14 * mm,
                                    topMargin=(header_h + 12 * mm), bottomMargin=14 * mm)

            import tempfile
            logo_png = resource_try("logo.png", "faisal_logo.png")
            logo_jpg = resource_try("logo.jpeg", "logo.jpg", "faisal_logo.jpeg", "faisal_logo.jpg")

            logo_path = None
            if logo_png:
                logo_path = logo_png
            elif logo_jpg:
                try:
                    temp_dir = tempfile.gettempdir()
                    gen_png = os.path.join(temp_dir, "faisal_logo.png")
                    if not os.path.exists(gen_png): make_logo_transparent(logo_jpg, gen_png, white_threshold=245)
                    logo_path = gen_png if os.path.exists(gen_png) else logo_jpg
                except Exception:
                    logo_path = logo_jpg

            logo_img = ImageReader(logo_path) if logo_path else None

            def draw_header_footer(canv, doc_):
                canv.saveState()
                ww, hh = A4
                canv.setFillColor(GREEN)
                canv.rect(0, hh - header_h, ww, header_h, fill=1, stroke=0)
                canv.setFillColor(GOLD)
                canv.rect(0, hh - header_h, ww, 2.0 * mm, fill=1, stroke=0)

                if logo_img:
                    box_x, box_y, box_w, box_h = 13 * mm, hh - header_h + 4.5 * mm, 26 * mm, 26 * mm
                    canv.setFillColor(colors.white)
                    canv.roundRect(box_x, box_y, box_w, box_h, 3 * mm, fill=1, stroke=0)
                    canv.drawImage(logo_img, box_x + 2 * mm, box_y + 2 * mm, width=22 * mm, height=22 * mm,
                                   preserveAspectRatio=True, mask='auto')

                canv.setFillColor(colors.white)
                canv.setFont(base_font, 16.2)

                branch_val = (meta.get("branch_name") or "").strip()
                branch_name = transliterate_ar_to_en(branch_val) if lang == "en" else branch_val
                title = f"{t('كشف حساب')}  |  {t('فرع:')} {branch_name}" if branch_name else t("كشف حساب")

                canv.drawCentredString(ww / 2, hh - 17.5 * mm, ar(title))

                footer_y = 9 * mm
                canv.setStrokeColor(colors.HexColor("#D7DCE0"))
                canv.setLineWidth(0.55)
                canv.line(14 * mm, footer_y + 6 * mm, ww - 14 * mm, footer_y + 6 * mm)
                canv.setFillColor(DGRAY)
                canv.setFont(base_font, 9.2)
                canv.drawString(14 * mm, footer_y, ar(f"{t('تاريخ الطباعة:')} {printed_at}"))
                canv.drawRightString(ww - 14 * mm, footer_y, ar(f"{t('صفحة')} {doc_.page}"))
                canv.restoreState()

            story = []

            client_info = (meta.get("client_info") or "").strip()
            acc_type = (meta.get("acc_type") or "").strip()
            cur = (meta.get("currency") or "").strip()

            client_lines = []
            if client_info:
                for ln in client_info.split("\n"):
                    ln = ln.strip()
                    if ln and ln != "—":
                        if ln.startswith("اسم العميل:"):
                            name_val = ln.replace("اسم العميل:", "").strip()
                            # تفعيل الترجمة الصوتية للاسم لو اللغة إنجليزي
                            final_name = transliterate_ar_to_en(name_val) if lang == "en" else name_val
                            client_lines.append(f"{t('اسم العميل:')} {final_name}")
                        elif ln.startswith("العنوان:"):
                            addr_val = ln.replace("العنوان:", "").strip()
                            # تفعيل الترجمة الصوتية للعنوان لو اللغة إنجليزي
                            final_addr = transliterate_ar_to_en(addr_val) if lang == "en" else addr_val
                            client_lines.append(f"{t('العنوان:')} {final_addr}")
                        else:
                            client_lines.append(ln)

            if not client_lines:
                client_lines = [f"{t('اسم العميل:')} {t('—')}", f"{t('العنوان:')} {t('—')}"]

            if account_no: client_lines.append(f"{t('رقم الحساب:')} {account_no}")
            if acc_type: client_lines.append(f"{t('نوع الحساب:')} {t(acc_type)}")
            if cur: client_lines.append(f"{t('العملة:')} {t(cur)}")
            if period_text: client_lines.append(period_text)

            # 1. بنبني السطور العادية الأول
            info_block = [Paragraph(ar(x), st_right) for x in client_lines]

            # 2. بنجهز سطر الرصيد القديم
            balance_2017_txt = meta.get("balance_2017", "0.00")
            bal_text = f"{t('   الرصيد في 31-03-2017:   ')} {balance_2017_txt}"

            # 3. بنعمل معالجة للعربي الأول (ar)، وبعدين نغلفه بتاج الهايلايت الأزرق
            highlighted_bal = f'<font backColor="#facc69">{ar(bal_text)}</font>'

            # 4. بنضيفه للبلوك
            info_block.append(Paragraph(highlighted_bal, st_right))

            info_tbl = Table([[info_block]], colWidths=[176 * mm])

            info_tbl.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                ("BOX", (0, 0), (-1, -1), 1.15, GOLD),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ]))
            story.append(info_tbl)
            story.append(Spacer(1, 6 * mm))

            kpis = [
                ("رصيد الافتتاح", fmt2(opening_balance_val)),
                ("إجمالي دائن", fmt2(total_credit)),
                ("إجمالي مدين", fmt2(total_debit)),
                ("الرصيد الختامي", fmt2(closing_balance)),
                ("عدد الحركات", str(len(rows))),
            ]

            if lang == "en": kpis = list(reversed(kpis))

            kpi_cells = []
            for label, value in kpis:
                kpi_cells.append([
                    Paragraph(ar(t(label)), st_kpi_label),
                    Spacer(1, 1.0 * mm),
                    Paragraph(ar(value), st_kpi_value)
                ])

            usable_w = (A4[0] - doc.leftMargin - doc.rightMargin)
            kpi_tbl = Table([kpi_cells], colWidths=[usable_w / 5.0] * 5)

            open_idx = 4 if lang == "en" else 0
            close_idx = 1 if lang == "en" else 3

            kpi_tbl.setStyle(TableStyle([
                ("BOX", (0, 0), (-1, -1), 1.10, GOLD),
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                ("LINEBEFORE", (1, 0), (1, 0), 0.35, GRID),
                ("LINEBEFORE", (2, 0), (2, 0), 0.35, GRID),
                ("LINEBEFORE", (3, 0), (3, 0), 0.35, GRID),
                ("LINEBEFORE", (4, 0), (4, 0), 0.35, GRID),
                ("TOPPADDING", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("BACKGROUND", (open_idx, 0), (open_idx, 0), OPEN_BG),
                ("BACKGROUND", (close_idx, 0), (close_idx, 0), CLOSE_BG),
            ]))
            story.append(kpi_tbl)
            story.append(Spacer(1, 7 * mm))

            if lang == "en":
                header = [ar(t("التاريخ")), ar(t("البيان / نوع المستند")), ar(t("مدين")), ar(t("دائن")),
                          ar(t("الرصيد"))]
                col_widths = [26 * mm, 86 * mm, 24 * mm, 24 * mm, 30 * mm]
            else:
                header = [ar(t("الرصيد")), ar(t("دائن")), ar(t("مدين")), ar(t("البيان / نوع المستند")),
                          ar(t("التاريخ"))]
                col_widths = [30 * mm, 24 * mm, 24 * mm, 86 * mm, 26 * mm]

            table_data = [header]

            for r in rows:
                date = r[0] if len(r) > 0 else ""
                desc = safe_one_line(r[1] if len(r) > 1 else "")
                credit = r[2] if len(r) > 2 else ""
                debit = r[3] if len(r) > 3 else ""
                bal = r[4] if len(r) > 4 else ""
                nseq = (r[8] if len(r) > 8 else "")
                # 🆕 ضيف السطر ده عشان تسحب اسم المستند اللي جه من الداتا
                doc_name = (r[9] if len(r) > 9 else "")

                desc_flow = [Paragraph(ar(t(desc) if desc else "—"), st_right)]
                if nseq: desc_flow.append(Paragraph(ar(f"{t('رقم النمارة:')} {nseq}"), st_right_small))
                # 🆕 ضيف السطر ده عشان يطبع اسم المستند لو موجود تحت رقم النمارة
                if doc_name: desc_flow.append(Paragraph(ar(f"المستند: {doc_name}"), st_right_small))
                if lang == "en":
                    table_data.append([date, desc_flow, debit, credit, bal])
                else:
                    table_data.append([bal, credit, debit, desc_flow, date])

            main_tbl = Table(table_data, colWidths=col_widths, repeatRows=1, hAlign="LEFT")

            align_style_col2 = "LEFT" if lang == "en" else "RIGHT"

            main_tbl.setStyle(TableStyle([
                ("FONTNAME", (0, 0), (-1, -1), base_font),
                ("FONTSIZE", (0, 0), (-1, 0), 10.2),
                ("FONTSIZE", (0, 1), (-1, -1), 9.3),
                ("BACKGROUND", (0, 0), (-1, 0), GREEN),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("LINEBELOW", (0, 0), (-1, 0), 1.2, GOLD),
                ("GRID", (0, 0), (-1, -1), 0.28, BORDER),
                ("BOX", (0, 0), (-1, -1), 0.95, BORDER),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ZEBRA]),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 1), (0, -1), "CENTER"),
                ("ALIGN", (1, 1), (1, -1), align_style_col2 if lang == "en" else "CENTER"),
                ("ALIGN", (2, 1), (4, -1), "CENTER"),
                ("ALIGN", (1, 1), (1, -1), "LEFT" if lang == "en" else "RIGHT"),
                ("RIGHTPADDING", (1, 1) if lang == "en" else (3, 1), (1, -1) if lang == "en" else (3, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]))

            story.append(main_tbl)

            doc.build(story, onFirstPage=draw_header_footer, onLaterPages=draw_header_footer)
            messagebox.showinfo("تم / Success", "تم تصدير PDF بنجاح ✅\nPDF Exported Successfully ✅")
            if hasattr(self, 'sys_logger'): self.sys_logger.log(f"📄  تم تصدير PDF بنجاح إلى ملف: {file_path}")
        except Exception as e:
            messagebox.showerror("خطأ / Error", f"حدث خطأ أثناء تصدير PDF:\n{e}")
            if hasattr(self, 'sys_logger'): self.sys_logger.log(f"❌ فشل تصدير الملف: {e}", type="ERROR")
    def nuwairy_export_excel(self):
        from tkinter import filedialog, messagebox
        from datetime import datetime
        import re
        import os

        rows = getattr(self, "nuwairy_last_rows", None)
        meta = getattr(self, "nuwairy_last_meta", {}) or {}

        if not rows:
            messagebox.showwarning("تنبيه", "لا توجد بيانات للتصدير. اعمل بحث الحركات أولاً.")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel Files", "*.xlsx")]
        )
        if not file_path:
            return

        # ---------- Helpers ----------
        def money_to_float(v):
            if v is None:
                return 0.0
            s = str(v).strip()
            if not s:
                return 0.0
            s = s.replace(",", "").replace(" ", "")
            s = re.sub(r"[^0-9\.\-]", "", s)
            try:
                return float(s) if s else 0.0
            except:
                return 0.0

        def parse_date_safe(s):
            s = (s or "").strip()
            for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d", "%d-%m-%Y", "%d/%m/%Y"):
                try:
                    return datetime.strptime(s, fmt).date()
                except:
                    pass
            return None

        def safe_txt(x):
            return "" if x is None else str(x)

        def resource_try(*names):
            for n in names:
                try:
                    p = None
                    try:
                        p = resource_path(n)  # type: ignore
                    except:
                        p = None
                    if not p:
                        p = os.path.join(os.getcwd(), n)
                    if p and os.path.exists(p):
                        return p
                except:
                    pass
            return None

        try:
            import xlsxwriter

            # ---------- Theme ----------
            GREEN = "#0B5C3A"
            GOLD = "#B08D2D"
            GRID = "#E6EAEE"
            ZEBRA = "#FAFBFC"
            TEXT = "#111827"
            MUTED = "#4B5563"
            SOFT = "#F9F3E6"
            OPEN_BG = "#FFF1D6"
            CLOSE_BG = "#FFF5DB"

            # ---------- Meta ----------
            client_info = (meta.get("client_info") or "").strip()
            branch = (meta.get("branch_name") or "").strip()
            acc_type = (meta.get("acc_type") or "").strip()
            cur = (meta.get("currency") or "").strip()
            client_no = (meta.get("client_no") or "").strip()
            account_no = (meta.get("account_no") or "").strip()
            date_from = (meta.get("date_from") or "").strip()
            date_to = (meta.get("date_to") or "").strip()
            opening_balance = money_to_float(meta.get("opening_balance"))

            # ---------- Prepare table rows ----------
            # rows format from fetch: [date, desc, credit, debit, balance, trx_name, gl_main, gl_sub, nseq]
            # Needed order in excel: date | desc | debit | credit | balance | nseq
            table_rows = []
            total_credit = 0.0
            total_debit = 0.0
            closing_balance = 0.0

            for r in rows:
                d = safe_txt(r[0]) if len(r) > 0 else ""
                desc = safe_txt(r[1]) if len(r) > 1 else ""
                credit = money_to_float(r[2]) if len(r) > 2 else 0.0
                debit = money_to_float(r[3]) if len(r) > 3 else 0.0
                bal = money_to_float(r[4]) if len(r) > 4 else 0.0
                nseq = safe_txt(r[8]) if len(r) > 8 else ""  # ✅ رقم النمارة

                total_credit += credit
                total_debit += debit
                closing_balance = bal

                table_rows.append((d, desc, debit, credit, bal, nseq))  # ✅ ضفناه فعليًا

            # Keep exact meta period if exists; else infer
            if (not date_from or not date_to) and table_rows:
                ds = [parse_date_safe(x[0]) for x in table_rows]
                ds = [d for d in ds if d]
                if ds:
                    mn, mx = min(ds), max(ds)
                    date_from = date_from or mn.strftime("%Y-%m-%d")
                    date_to = date_to or mx.strftime("%Y-%m-%d")

            printed_at = datetime.now().strftime("%Y-%m-%d %H:%M")

            # Summary prep
            credits_only = [(d, desc, c) for (d, desc, deb, c, bal, nseq) in table_rows if c and c > 0]
            debits_only = [(d, desc, deb) for (d, desc, deb, c, bal, nseq) in table_rows if deb and deb > 0]
            top_credits = sorted(credits_only, key=lambda x: x[2], reverse=True)[:5]
            top_debits = sorted(debits_only, key=lambda x: x[2], reverse=True)[:5]

            daily = {}
            for d, desc, deb, c, bal, nseq in table_rows:
                daily.setdefault(d, {"credit": 0.0, "debit": 0.0})
                daily[d]["credit"] += c
                daily[d]["debit"] += deb
            daily_days = sorted(daily.keys(), key=lambda x: (parse_date_safe(x) or datetime.max.date(), x))

            # ---------- Workbook ----------
            wb = xlsxwriter.Workbook(file_path)

            # ---------- Formats ----------
            fmt_title = wb.add_format({
                "bold": True, "font_size": 18, "font_color": "white",
                "align": "center", "valign": "vcenter",
                "bg_color": GREEN
            })
            fmt_gold_line = wb.add_format({"bg_color": GOLD})

            fmt_label = wb.add_format({"bold": True, "font_size": 11, "font_color": TEXT})
            fmt_value = wb.add_format({"font_size": 11, "font_color": TEXT})
            fmt_muted = wb.add_format({"font_size": 10, "font_color": MUTED})

            fmt_card_cell = wb.add_format({"border": 1, "border_color": GRID, "bg_color": "white"})
            fmt_card_outer = wb.add_format({"border": 2, "border_color": GOLD, "bg_color": "white"})

            fmt_kpi_box = wb.add_format(
                {"border": 1, "border_color": GRID, "align": "center", "valign": "vcenter", "text_wrap": True})
            fmt_kpi_open = wb.add_format(
                {"border": 1, "border_color": GRID, "align": "center", "valign": "vcenter", "text_wrap": True,
                 "bg_color": OPEN_BG})
            fmt_kpi_close = wb.add_format(
                {"border": 1, "border_color": GRID, "align": "center", "valign": "vcenter", "text_wrap": True,
                 "bg_color": CLOSE_BG})
            fmt_kpi_head = wb.add_format({"border": 2, "border_color": GOLD})

            fmt_header = wb.add_format({
                "bold": True, "font_color": "white", "bg_color": GREEN,
                "align": "center", "valign": "vcenter",
                "border": 1, "border_color": GRID
            })
            fmt_footer = wb.add_format({"font_size": 9, "font_color": MUTED})

            fmt_table_money = wb.add_format(
                {"font_size": 10, "align": "center", "valign": "vcenter", "border": 1, "border_color": GRID,
                 "num_format": "#,##0.00"})
            fmt_table_money_z = wb.add_format(
                {"font_size": 10, "align": "center", "valign": "vcenter", "border": 1, "border_color": GRID,
                 "num_format": "#,##0.00", "bg_color": ZEBRA})

            fmt_table_date = wb.add_format(
                {"font_size": 10, "align": "center", "valign": "vcenter", "border": 1, "border_color": GRID})
            fmt_table_date_z = wb.add_format(
                {"font_size": 10, "align": "center", "valign": "vcenter", "border": 1, "border_color": GRID,
                 "bg_color": ZEBRA})

            fmt_table_text = wb.add_format(
                {"font_size": 10, "align": "right", "valign": "vcenter", "border": 1, "border_color": GRID,
                 "text_wrap": True})
            fmt_table_text_z = wb.add_format(
                {"font_size": 10, "align": "right", "valign": "vcenter", "border": 1, "border_color": GRID,
                 "text_wrap": True, "bg_color": ZEBRA})

            fmt_table_nseq = wb.add_format(
                {"font_size": 10, "align": "center", "valign": "vcenter", "border": 1, "border_color": GRID})
            fmt_table_nseq_z = wb.add_format(
                {"font_size": 10, "align": "center", "valign": "vcenter", "border": 1, "border_color": GRID,
                 "bg_color": ZEBRA})

            fmt_summary_h = wb.add_format(
                {"bold": True, "font_color": "white", "bg_color": GREEN, "align": "center", "valign": "vcenter",
                 "border": 1, "border_color": GRID})
            fmt_summary_money = wb.add_format(
                {"border": 1, "border_color": GRID, "num_format": "#,##0.00", "align": "center", "valign": "vcenter"})
            fmt_summary_text = wb.add_format(
                {"border": 1, "border_color": GRID, "align": "right", "valign": "vcenter", "text_wrap": True})

            fmt_kpi_label = wb.add_format({
                "bold": True, "align": "center", "valign": "vcenter",
                "border": 1, "border_color": GRID,
                "bg_color": SOFT, "font_color": MUTED
            })

            # =========================
            # Sheet 1: كشف حساب
            # =========================
            ws = wb.add_worksheet("كشف حساب")
            ws.right_to_left()
            ws.hide_gridlines(2)

            # ✅ أعرض الأعمدة مضبوط (وجود F للـ nseq)
            ws.set_column("A:A", 14)  # التاريخ
            ws.set_column("B:B", 50)  # البيان
            ws.set_column("C:E", 16)  # مدين/دائن/رصيد
            ws.set_column("F:F", 14)  # رقم النمارة

            ws.set_row(0, 50)
            ws.set_row(1, 30)
            ws.set_row(2, 6)

            # ✅ Header: لازم يمتد لحد F علشان الشكل مايبقاش ناقص
            ws.merge_range("A1:E2", f"كشف حساب  |  فرع: {branch or '—'}", fmt_title)
            ws.merge_range("F1:F2", "", fmt_title)
            ws.merge_range("A3:F3", "", fmt_gold_line)

            logo_path = resource_try("logo.png", "logo.png")
            if logo_path:
                ws.insert_image("F1", logo_path, {
                    "x_scale": 0.14, "y_scale": 0.14,
                    "x_offset": 18, "y_offset": 8,
                    "object_position": 2
                })

            # ---- Customer card area A5:F8 ----
            r1, r2 = 4, 7  # rows 5..8
            c1, c2 = 0, 5  # A..F

            for r in range(r1, r2 + 1):
                for c in range(c1, c2 + 1):
                    ws.write_blank(r, c, None, fmt_card_cell)

            # outer frame
            for c in range(c1, c2 + 1):
                ws.write_blank(r1, c, None, fmt_card_outer)
                ws.write_blank(r2, c, None, fmt_card_outer)
            for r in range(r1, r2 + 1):
                ws.write_blank(r, c1, None, fmt_card_outer)
                ws.write_blank(r, c2, None, fmt_card_outer)

            ws.set_row(4, 22)
            ws.set_row(5, 22)
            ws.set_row(6, 22)
            ws.set_row(7, 22)

            client_line = client_info.replace("\n", " | ").strip() if client_info else "—"

            ws.write("C5", "اسم العميل:", fmt_label)
            ws.merge_range("A5:B5", client_line, fmt_value)

            ws.write("C6", "العنوان:", fmt_label)
            addr = ""
            for ln in (client_info.split("\n") if client_info else []):
                if "العنوان" in ln:
                    addr = ln.split(":", 1)[-1].strip()
            ws.merge_range("A6:B6", addr or "—", fmt_value)

            ws.write("F5", "رقم الحساب:", fmt_label)
            ws.write("E5", account_no or "—", fmt_value)

            ws.write("F6", "نوع الحساب:", fmt_label)
            ws.write("E6", acc_type or "—", fmt_value)

            ws.write("F7", "العملة:", fmt_label)
            ws.write("E7", cur or "—", fmt_value)

            ws.write("F8", "الفترة:", fmt_label)
            ws.merge_range("A8:E8", f"{date_from} إلى {date_to}", fmt_muted)

            # ---- KPI Row ----
            kpi_row = 9
            ws.set_row(kpi_row, 44)
            for c in range(0, 6):
                ws.write_blank(kpi_row, c, None, fmt_kpi_head)

            # ✅ خلي KPI على 5 خلايا + خلية فاضية مكانها F علشان اللوجو/التوازن
            ws.write(kpi_row, 0, f"عدد الحركات\n{len(table_rows)}", fmt_kpi_box)
            ws.write(kpi_row, 1, f"الرصيد الختامي\n{closing_balance:,.2f}", fmt_kpi_close)
            ws.write(kpi_row, 2, f"إجمالي مدين\n{total_debit:,.2f}", fmt_kpi_box)
            ws.write(kpi_row, 3, f"إجمالي دائن\n{total_credit:,.2f}", fmt_kpi_box)
            ws.write(kpi_row, 4, f"رصيد الافتتاح\n{opening_balance:,.2f}", fmt_kpi_open)
            ws.write(kpi_row, 5, "", fmt_kpi_box)

            # ---- Main Table ----
            table_start = 11
            ws.set_row(table_start, 22)

            ws.write(table_start, 0, "التاريخ", fmt_header)
            ws.write(table_start, 1, "البيان / نوع المستند", fmt_header)
            ws.write(table_start, 2, "مدين", fmt_header)
            ws.write(table_start, 3, "دائن", fmt_header)
            ws.write(table_start, 4, "الرصيد", fmt_header)
            ws.write(table_start, 5, "رقم النمارة", fmt_header)

            for i, (d, desc, debit, credit, bal, nseq) in enumerate(table_rows):
                rr = table_start + 1 + i
                zebra = (i % 2 == 1)

                f_date = fmt_table_date_z if zebra else fmt_table_date
                f_text = fmt_table_text_z if zebra else fmt_table_text
                f_mon = fmt_table_money_z if zebra else fmt_table_money
                f_seq = fmt_table_nseq_z if zebra else fmt_table_nseq

                ws.write(rr, 0, d, f_date)
                ws.write(rr, 1, desc if desc else "—", f_text)
                ws.write_number(rr, 2, debit, f_mon)
                ws.write_number(rr, 3, credit, f_mon)
                ws.write_number(rr, 4, bal, f_mon)
                ws.write(rr, 5, nseq, f_seq)  # ✅ اكتب رقم النمارة فعليًا

            last_row = table_start + len(table_rows)

            # ✅ تثبيت الهيدر بتاع الجدول فقط (عشان كله يبقا واضح)
            # ws.freeze_panes(table_start + 1, 0)

            # ✅ للطباعة: كرر صف الهيدر بتاع الجدول فقط (مش الهيدر الكبير)
            # ws.repeat_rows(table_start, table_start)

            ws.set_landscape()
            ws.fit_to_pages(1, 0)
            ws.set_zoom(100)  # زووم طبيعي
            ws.set_default_row(15)

            ws.write(last_row + 2, 0, f"تاريخ الطباعة: {printed_at}", fmt_footer)

            # =========================
            # Sheet 2: Summary
            # =========================
            ws2 = wb.add_worksheet("Summary")
            ws2.right_to_left()
            ws2.hide_gridlines(2)

            ws2.set_row(0, 50)
            ws2.set_row(1, 30)
            ws2.set_row(2, 6)

            ws2.set_column("A:A", 18)
            ws2.set_column("B:B", 24)
            ws2.set_column("C:D", 18)
            ws2.set_column("E:E", 46)

            ws2.merge_range("A1:D2", "ملخص كشف الحساب", fmt_title)
            ws2.merge_range("E1:E2", "", fmt_title)
            ws2.merge_range("A3:E3", "", fmt_gold_line)

            if logo_path:
                ws2.insert_image("E1", logo_path, {
                    "x_scale": 0.14, "y_scale": 0.14,
                    "x_offset": 18, "y_offset": 8,
                    "object_position": 2
                })

            ws2.write("E5", "رقم الحساب:", fmt_label)
            ws2.write("D5", account_no or "—", fmt_value)
            ws2.write("C5", "رقم العميل:", fmt_label)
            ws2.write("B5", client_no or "—", fmt_value)
            ws2.write("A5", f"الفترة: {date_from} إلى {date_to}", fmt_muted)

            ws2.write("E7", "رصيد الافتتاح", fmt_kpi_label)
            ws2.write_number("D7", opening_balance, wb.add_format(
                {"border": 1, "border_color": GRID, "bg_color": OPEN_BG, "num_format": "#,##0.00", "align": "center"}))
            ws2.write("C7", "الرصيد الختامي", fmt_kpi_label)
            ws2.write_number("B7", closing_balance, wb.add_format(
                {"border": 1, "border_color": GRID, "bg_color": CLOSE_BG, "num_format": "#,##0.00", "align": "center"}))

            ws2.write("E8", "إجمالي دائن", fmt_kpi_label)
            ws2.write_number("D8", total_credit, wb.add_format(
                {"border": 1, "border_color": GRID, "num_format": "#,##0.00", "align": "center"}))
            ws2.write("C8", "إجمالي مدين", fmt_kpi_label)
            ws2.write_number("B8", total_debit, wb.add_format(
                {"border": 1, "border_color": GRID, "num_format": "#,##0.00", "align": "center"}))
            ws2.write("A8", f"عدد الحركات: {len(table_rows)}",
                      wb.add_format({"border": 1, "border_color": GRID, "bg_color": SOFT, "align": "center"}))

            ws2.write("E11", "أكبر 5 دائن", wb.add_format({"bold": True, "font_size": 12, "font_color": GREEN}))
            ws2.write_row("A12", ["القيمة", "البيان", "التاريخ"], fmt_summary_h)

            for i, (d, desc, val) in enumerate(top_credits, start=0):
                rr = 12 + 1 + i
                ws2.write_number(rr, 0, val, fmt_summary_money)
                ws2.write(rr, 1, desc if desc else "—", fmt_summary_text)
                ws2.write(rr, 2, d, fmt_table_date)

            ws2.write("E18", "أكبر 5 مدين", wb.add_format({"bold": True, "font_size": 12, "font_color": GREEN}))
            ws2.write_row("A19", ["القيمة", "البيان", "التاريخ"], fmt_summary_h)

            for i, (d, desc, val) in enumerate(top_debits, start=0):
                rr = 19 + 1 + i
                ws2.write_number(rr, 0, val, fmt_summary_money)
                ws2.write(rr, 1, desc if desc else "—", fmt_summary_text)
                ws2.write(rr, 2, d, fmt_table_date)

            ws2.write("E26", "ملخص يومي (للمخطط)", wb.add_format({"bold": True, "font_size": 12, "font_color": GREEN}))
            ws2.write_row("A27", ["إجمالي مدين", "إجمالي دائن", "التاريخ"], fmt_summary_h)

            base_r = 27
            for i, d in enumerate(daily_days):
                rr = base_r + 1 + i
                ws2.write_number(rr, 0, daily[d]["debit"], fmt_summary_money)
                ws2.write_number(rr, 1, daily[d]["credit"], fmt_summary_money)
                ws2.write(rr, 2, d, fmt_table_date)

            if daily_days:
                chart = wb.add_chart({"type": "column"})
                chart.add_series({
                    "name": "إجمالي دائن",
                    "categories": ["Summary", base_r + 1, 2, base_r + len(daily_days), 2],
                    "values": ["Summary", base_r + 1, 1, base_r + len(daily_days), 1],
                })
                chart.add_series({
                    "name": "إجمالي مدين",
                    "categories": ["Summary", base_r + 1, 2, base_r + len(daily_days), 2],
                    "values": ["Summary", base_r + 1, 0, base_r + len(daily_days), 0],
                })
                chart.set_title({"name": "إجمالي دائن/مدين حسب اليوم"})
                chart.set_legend({"position": "bottom"})
                chart.set_size({"width": 720, "height": 300})
                ws2.insert_chart("A31", chart)

            wb.close()
            messagebox.showinfo("تم", "تم تصدير Excel بشكل ثابت ✅")

            self.sys_logger.log(f"📄 تم تصدير بيانات العميل إلى ملف: {file_path}")
            #messagebox.showinfo("نجاح", "تم التصدير بنجاح")
        except Exception as e:
            messagebox.showerror("خطأ", f"حدث خطأ أثناء تصدير Excel:\n{e}")
            self.sys_logger.log(f"❌ فشل تصدير الملف: {e}", type="ERROR")

    def _f(self, size=12, weight="normal"):
        # safe font tuple for CTk / Tk
        if weight not in ("normal", "bold", "italic"):
            weight = "normal"
        return ("Segoe UI", int(size), weight)

    def resource_path(relative_path: str) -> str:
        # PyInstaller support
        base_path = getattr(sys, "_MEIPASS", None)
        if base_path:
            return os.path.join(base_path, relative_path)

        # normal python run: directory of this file (NOT working dir)
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)

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

    # ========================================================
    # 🔧 LOGIC
    # ========================================================
    def browse_folder(self):
        mode = self.radio_var.get()
        if mode == "Access":
            p = filedialog.askopenfilename(title="Select Access Database",
                                           filetypes=[("Access DB", "*.accdb *.mdb"), ("All Files", "*.*")])
        else:
            p = filedialog.askdirectory(title="Select Source Folder")
        if p: self.folder_path_var.set(p)

    import json
    import os
    import threading
    from tkinter import messagebox
    from utils import get_config_path

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

                # 1️⃣ استكمال تحديث الواجهة بالكامل (بشرط وجود العنصر)
                if hasattr(self, 'ent_server') and self.ent_server:
                    self.ent_server.delete(0, "end")
                    self.ent_server.insert(0, getattr(self, 'server_val', ''))

                if hasattr(self, 'ent_db') and self.ent_db:
                    self.ent_db.delete(0, "end")
                    self.ent_db.insert(0, getattr(self, 'db_val', ''))

                if hasattr(self, 'ent_user') and self.ent_user:
                    self.ent_user.delete(0, "end")
                    self.ent_user.insert(0, getattr(self, 'user_val', ''))

                if hasattr(self, 'ent_pass') and self.ent_pass:
                    self.ent_pass.delete(0, "end")
                    self.ent_pass.insert(0, getattr(self, 'pass_val', ''))

            except Exception as e:
                print(f"Error loading config: {e}")

    def save_config(self, silent=False):
        if hasattr(self, 'sys_logger'):
            self.sys_logger.log(f"💾 تم حفظ إعدادات جديدة -> المسار: {self.folder_path_var.get()}")

        config_path = get_config_path("config.json")

        # 2️⃣ الجلب الآمن: لو الخانة مش موجودة (سيتركس)، هات القيمة من المتغير عشان الملف ميفضاش!
        srv = self.ent_server.get().strip() if hasattr(self, 'ent_server') else getattr(self, 'server_val', '')
        db_n = self.ent_db.get().strip() if hasattr(self, 'ent_db') else getattr(self, 'db_val', '')
        usr = self.ent_user.get().strip() if hasattr(self, 'ent_user') else getattr(self, 'user_val', '')
        pwd = self.ent_pass.get().strip() if hasattr(self, 'ent_pass') else getattr(self, 'pass_val', '')

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
        # دالة الاختبار تعمل غالباً من شاشة الكونفيج، لذلك يمكن الاعتماد على الشاشة هنا
        if not hasattr(self, 'ent_server'):
            return

        srv = self.ent_server.get().strip()
        db_n = self.ent_db.get().strip()
        usr = self.ent_user.get().strip()
        pwd = self.ent_pass.get().strip()

        if hasattr(self, 'sys_logger'):
            self.sys_logger.log(f"🔌 يتم الآن اختبار الاتصال بالسيرفر: [{srv}] قاعدة البيانات: [{db_n}]")

        if not srv or not db_n:
            messagebox.showwarning("Missing Info", "Please enter Server and Database name.")
            return

        self.btn_test.configure(state="disabled", text="Connecting...")

        def _run_test():
            try:
                from database import DatabaseEngine
                # استخدام None للوجر لأننا عدلناه ليكون اختيارياً في الخطوات السابقة
                db = DatabaseEngine(srv, db_n, usr, pwd, logger=None)

                self.after(0, lambda: messagebox.showinfo("Success", f"Connected to [{db_n}] Successfully! ✅"))
            except Exception as e:
                err_msg = str(e)
                self.after(0, lambda: messagebox.showerror("Connection Failed", f"Could not connect:\n{err_msg}"))
            finally:
                self.after(0, lambda: self.btn_test.configure(state="normal", text="🔌 Test Connection"))

        threading.Thread(target=_run_test, daemon=True).start()

    def start_process(self):
        if not self.folder_path_var.get():
            messagebox.showwarning("Warning", "Please select source folder in Configuration.")
            self.show_page("config")
            return

        self.btn_run.configure(state="disabled", text="PROCESSING... ⏳", fg_color="gray")
        self.progress.pack(fill="x", side="bottom")
        self.progress.start()
        self.log_box.delete("1.0", "end")
        threading.Thread(target=self.run_engine, daemon=True).start()

    def run_engine(self):
        try:
            path = self.folder_path_var.get()

            # 3️⃣ الجلب الآمن لحماية نسخة سيتركس
            srv = self.ent_server.get().strip() if hasattr(self, 'ent_server') else getattr(self, 'server_val', '')
            db_n = self.ent_db.get().strip() if hasattr(self, 'ent_db') else getattr(self, 'db_val', '')
            usr = self.ent_user.get().strip() if hasattr(self, 'ent_user') else getattr(self, 'user_val', '')
            pwd = self.ent_pass.get().strip() if hasattr(self, 'ent_pass') else getattr(self, 'pass_val', '')

            # التحقق الآمن من Checkboxes (لأنها ممكن تكون مش موجودة في سيتركس)
            is_append = self.chk_append_var.get() if hasattr(self, 'chk_append_var') else False
            write_mode = 'append' if is_append else 'replace'

            target_tbl = None
            if hasattr(self, 'chk_merge_var') and self.chk_merge_var.get():
                target_tbl = self.ent_merge_name.get().strip()
                if not target_tbl:
                    self.log_gui("❌ Error: Merge selected but no table name!", "ERROR")
                    return

            # تحديد نوع العملية
            radio_choice = self.radio_var.get() if hasattr(self, 'radio_var') else "Excel/CSV"

            if radio_choice == "Access":
                from access_migrator import AccessToSQL
                self.log_gui(f"🚀 Detected Access Database.")
                migrator = AccessToSQL(path, srv, db_n, self.log_gui, user=usr, password=pwd)
                migrator.migrate(mode=write_mode, target_table=target_tbl)
            else:
                from etl import ETLOrchestrator
                orch = ETLOrchestrator(srv, db_n, usr, pwd, path, self.log_gui)
                orch.run()

            self.refresh_dashboard_data()
            self.log_gui("✅ PROCESS COMPLETED.", "SUCCESS")

        except Exception as e:
            self.log_gui(f"❌ CRITICAL ERROR: {e}", "ERROR")
        finally:
            self.after(0, getattr(self, 'reset_ui', lambda: None))

    def reset_ui(self):
        self.btn_run.configure(state="normal", text="🚀 START PROCESS", fg_color=FIB_GREEN)
        self.progress.stop()
        self.progress.pack_forget()

    def log_gui(self, msg, type="INFO"):
        self.after(0, lambda: [self.log_box.insert("end", f"{msg}\n"), self.log_box.see("end")])

    def load_history_data(self):
        def _bg_load():
            try:
                from sqlalchemy import text
                from database import DatabaseEngine
                from utils import EnterpriseLogger
                db = DatabaseEngine(self.server_val, self.db_val, EnterpriseLogger(None))
                with db.engine.connect() as c:
                    rows = c.execute(text(
                        "SELECT TOP 50 ID, FILE_NAME, ROW_COUNT,STATUS, PROCESSED_AT FROM SYS_FILES_LOG ORDER BY ID DESC")).fetchall()
                    self.after(0, lambda: self._fill_tree(rows))
            except:
                pass

        threading.Thread(target=_bg_load, daemon=True).start()

    def _fill_tree(self, rows):
        self.tree.delete(*self.tree.get_children())
        for r in rows:
            dt = str(r[3])[:19] if r[3] else ""
            self.tree.insert("", "end", values=(r[0], r[1], r[2], r[3], dt))

    def export_report_excel(self):
        path = filedialog.asksaveasfilename(defaultextension=".xlsx",
                                            filetypes=[("Excel File", "*.xlsx"), ("CSV File", "*.csv")])
        if not path: return

        def _do_export():
            try:
                from sqlalchemy import text
                from database import DatabaseEngine
                from utils import EnterpriseLogger

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
                    import csv
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

    # ========================================================
    # 🛡️ SMART SECURITY MONITOR (المراقب الذكي)
    # ========================================================
    def start_security_monitor(self):
        """
        مراقب ذكي: يتحقق من الكود الموجود في البرنامج حالياً ضد البلاك ليست
        بدون الحاجة لملفات خارجية
        """
        self.is_locked_mode = False

        def _monitor_loop():
            import time
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

                except Exception as e:
                    #print(f"Monitor Error: {e}")
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

        # 3. قفل زر التشغيل الرئيسي
        if hasattr(self, 'btn_run'):
            self.btn_run.configure(state="disabled", text="🚫 BLOCKED", fg_color="gray")

        # 4. قفل باقي الزراير (الإعدادات والتقارير)
        if hasattr(self, 'btn_save'): self.btn_save.configure(state="disabled")
        if hasattr(self, 'btn_test'): self.btn_test.configure(state="disabled")
        if hasattr(self, 'btn_export'): self.btn_export.configure(state="disabled", fg_color="gray")

    def deactivate_lockdown_mode(self):
        """إعادة تفعيل البرنامج بالكامل"""
        # 1. رسالة ترحيب (اختياري)
        # messagebox.showinfo("RESTORED", "✅ License Restored Successfully.")

        # 2. إرجاع حالة الكارت للأخضر 🟢
        if hasattr(self, 'lbl_dot'):
            self.lbl_dot.configure(text_color=FIB_GREEN)

        if hasattr(self, 'lbl_status_text'):
            self.lbl_status_text.configure(text="ACTIVE LICENSE", text_color=FIB_GREEN)

        # 3. تشغيل زر التشغيل الرئيسي
        if hasattr(self, 'btn_run'):
            self.btn_run.configure(state="normal", text="🚀 START PROCESS", fg_color=FIB_GREEN)

        # 4. تشغيل باقي الزراير
        if hasattr(self, 'btn_save'): self.btn_save.configure(state="normal")
        if hasattr(self, 'btn_test'): self.btn_test.configure(state="normal")
        if hasattr(self, 'btn_export'): self.btn_export.configure(state="normal", fg_color=FIB_GOLD)

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
