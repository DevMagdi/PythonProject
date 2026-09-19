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
        # --- التعديل الجديد (RTL) ---
        # بنخلي العمود رقم 0 (اللي على الشمال) هو اللي يتمدد عشان يشيل الشاشات
        self.grid_columnconfigure(0, weight=1)
        # بنخلي العمود رقم 1 (اللي على اليمين) مساحته ثابتة للسايد بار
        self.grid_columnconfigure(1, weight=0)
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
        # 1️⃣ ظبطنا عرض السايد بار لـ 280 عشان يلم الفراغات الزيادة من اليمين والشمال
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
        # 2. Menu Buttons
        # ==========================================
        self.menu_container = ctk.CTkScrollableFrame(self.sidebar, fg_color="transparent")
        # 2️⃣ صفرنا الـ padx هنا تماماً عشان الفريم يلصق في أقصى اليمين واليسار بدون أي فراغات
        self.menu_container.grid(row=2, column=0, sticky="nsew", padx=0, pady=0)

        self.sub_menus = {}

        menu_structure = {
            "📂 الحسابات العامة": [
                ("استعلام الحسابات", "nuwairy"),
                ("أستاذ الحسابات العام", "gl_inquiry"),
            ],
            "👥 شؤون العملاء": [
                ("بحث عن عميل", "customer"),
                ("بحث برصيد العميل", "customer_balance"),
                ("الشهادات الملغاة برقم العميل", "cancelled_certs"),
                ("الاستفسار عن التوكيلات", "mandates"),
                ("الاستفسار عن تعليمات عميل", "instructions"),
                ("الاستفسار عن الكفلاء", "sponsors_inquiry"),
            ],
            "📄 الشيكات": [
                ("الشيكات الموقوفة", "stopped_cheques"),
                ("الشيكات المرفوضة", "rejected_cheques"),
            ],
            "📄 التوظيف": [
                ("بحث التوظيف المحلي", "local_recruitment"),
                ("الاستفسار عن الشيكات المرتدة", "returned_cheques"),
                ("الاستفسار عن العملاء المتعثرين", "defaulted_clients"),
                ("الاستفسار عن خطابات الضمان", "guarantees"),
                ("الاستفسار عن عملاء الجدارة الائتمانية", "creditworthiness"),
                ("الاستفسار عن إجمالي التزامات عميل", "total_liabilities_inquiry"),
                ("الاستفسار عن الضمانات لعميل", "customer_collaterals_inquiry"),
            ],
            "📄 الارباح والمساهمين": [
                ("الاستفسار الأبجدي عن عملاء مساهمين", "contributing_clients"),
                ("الاستفسار عن سابقة تعاملات عميل", "client_history"),
            ],
            "العلاج الطبي": [
                ("الاستفسار الأبجدي عن الموظفين واسرهم", "alphabetical_employees_families"),
                ("الاستفسار عن أرصدة العلاج الطبي للموظفين", "medical_balances_inquiry"),
            ]
        }

        for category, items in menu_structure.items():
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
        # حاوية رئيسية لكل قسم (بدون هوامش يمين)
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

        # إنشاء الزراير الفرعية للشاشات
        for text, page_name in items:
            sub_btn = ctk.CTkButton(
                sub_frame,
                text=text,
                font=("Segoe UI", 11, "bold"),  # صغرنا الخط سكة بسيطة عشان الكلام الطويل يفرش براحته ومايتقصش
                anchor="e",  # المحاذاة لليمين تماماً
                fg_color="transparent", text_color="#475569", hover_color="#F0F9F4",
                height=30, corner_radius=6,
                command=lambda p=page_name: self.show_page(p)
            )
            # 3️⃣ التعديل الجذري هنا: خلير الـ padx عبارة عن (0, 5) عشان الزرار يلزق في أقصى اليمين ومش يسيب مسافة ضخمة
            sub_btn.pack(fill="x", padx=(0, 5), pady=1)

            setattr(self, f"btn_{page_name}", sub_btn)

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
        import customtkinter as ctk
        import tkinter.messagebox as messagebox

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

    def setup_pages(self):
        # الحاوية الرئيسية اللي بتتعرض فيها الشاشات
        self.content_area = ctk.CTkFrame(self, fg_color="transparent")
        self.content_area.grid(row=0, column=0, sticky="nsew", padx=30, pady=30)

        # 1. شاشة استعلام الحسابات (Account Inquiry)
        self.page_nuwairy = ctk.CTkFrame(self.content_area, fg_color="transparent")
        self.setup_nuwairy_ui(self.page_nuwairy)

        # 2. شاشة استعلام الأستاذ العام (GL Account Inquiry)
        self.page_gl_inquiry = ctk.CTkFrame(self.content_area, fg_color="transparent")
        self.setup_gl_inquiry_ui(self.page_gl_inquiry)

        self.page_customer = ctk.CTkFrame(self.content_area, fg_color="transparent")
        self.setup_customer_inquiry_ui(self.page_customer)
        # 4. شاشة الشيكات الموقوفة
        self.page_stopped_cheques = ctk.CTkFrame(self.content_area, fg_color="transparent")
        self.setup_stopped_cheques_ui(self.page_stopped_cheques)

        # 5. شاشة الشيكات المرفوضة
        self.page_rejected_cheques = ctk.CTkFrame(self.content_area, fg_color="transparent")
        self.setup_rejected_cheques_ui(self.page_rejected_cheques)

        # 6. شاشة أرصدة العملاء
        self.page_customer_balance = ctk.CTkFrame(self.content_area, fg_color="transparent")
        self.setup_client_balances_ui(self.page_customer_balance)

        # 7. شاشة الشهادات الملغاة برقم العميل (الشاشة الجديدة)
        self.page_cancelled_certs = ctk.CTkFrame(self.content_area, fg_color="transparent")
        self.setup_cancelled_certs_ui(self.page_cancelled_certs)

        # 8. شاشة الاستفسار عن التوكيلات (الشاشة الجديدة)
        self.page_mandates = ctk.CTkFrame(self.content_area, fg_color="transparent")
        self.setup_mandates_ui(self.page_mandates)

        # 9. شاشة الاستفسار عن تعليمات عميل (الشاشة الجديدة)
        self.page_instructions = ctk.CTkFrame(self.content_area, fg_color="transparent")
        self.setup_instructions_ui(self.page_instructions)
        # 10. شاشة بحث التوظيف المحلي للعملاء (الشاشة الجديدة)
        self.page_local_recruitment = ctk.CTkFrame(self.content_area, fg_color="transparent")
        self.setup_local_recruitment_ui(self.page_local_recruitment)
        # 11. شاشة الاستفسار عن الكفلاء
        self.page_sponsors_inquiry = ctk.CTkFrame(self.content_area, fg_color="transparent")
        self.setup_sponsors_inquiry_ui(self.page_sponsors_inquiry)

        # 12. شاشة الشيكات المرتدة
        self.page_returned_cheques = ctk.CTkFrame(self.content_area, fg_color="transparent")
        self.setup_returned_cheques_ui(self.page_returned_cheques)

        # 13. شاشة العملاء المتعثرين
        self.page_defaulted_clients = ctk.CTkFrame(self.content_area, fg_color="transparent")
        self.setup_defaulting_client_ui(self.page_defaulted_clients)
        # 14. شاشة الاستفسار عن خطابات الضمان
        self.page_guarantees = ctk.CTkFrame(self.content_area, fg_color="transparent")
        self.setup_guarantees_inquiry_ui(self.page_guarantees)
        # 15. شاشة الاستفسار عن عملاء الجدارة الائتمانية
        self.page_creditworthiness = ctk.CTkFrame(self.content_area, fg_color="transparent")
        self.setup_creditworthiness_inquiry_ui(self.page_creditworthiness)
        # 16. لاستفسار الأبجدي عن عملاء مساهمين
        self.page_contributing_clients = ctk.CTkFrame(self.content_area, fg_color="transparent")
        self.setup_alphabetical_contributors_inquiry_ui(self.page_contributing_clients)
        # 17. شاشة الاستفسار عن سابقة تعاملات عميل
        self.page_client_history = ctk.CTkFrame(self.content_area, fg_color="transparent")
        self.setup_client_history_inquiry_ui(self.page_client_history)
        # 18. الاستفسار عن إجمالي التزامات عميل
        self.page_total_liabilities_inquiry = ctk.CTkFrame(self.content_area, fg_color="transparent")
        self.setup_total_liabilities_inquiry_ui(self.page_total_liabilities_inquiry)
        # 19. الاستفسار عن الضمانات لعميل
        self.page_customer_collaterals_inquiry = ctk.CTkFrame(self.content_area, fg_color="transparent")
        self.setup_customer_collaterals_inquiry_ui(self.page_customer_collaterals_inquiry)
        # 20. الاستفسار الأبجدي عن الموظفين وأسرهم
        self.page_alphabetical_employees_families = ctk.CTkFrame(self.content_area, fg_color="transparent")
        self.setup_alphabetical_employees_families_ui(self.page_alphabetical_employees_families)
        # 21. الاستفسار عن أرصدة العلاج الطبي للموظفين
        self.page_medical_balances_inquiry = ctk.CTkFrame(self.content_area, fg_color="transparent")
        self.setup_medical_balances_inquiry_ui(self.page_medical_balances_inquiry)


    def show_page(self, name):
        if hasattr(self, 'sys_logger'):
            self.sys_logger.log(f"🔄 المستخدم انتقل إلى شاشة: {name}")

        # 1. إخفاء الشاشتين الحاليين
        pages_to_hide = [
            getattr(self, 'page_nuwairy', None),
            getattr(self, 'page_gl_inquiry', None),
            getattr(self, 'page_customer', None),
            getattr(self, 'page_stopped_cheques', None),
            getattr(self, 'page_rejected_cheques', None),
            getattr(self, 'page_customer_balance', None),
            getattr(self, 'page_cancelled_certs', None),
            getattr(self, 'page_mandates', None),
            getattr(self, 'page_instructions', None),
            getattr(self, 'page_local_recruitment', None),
            getattr(self, 'page_sponsors_inquiry', None),
            getattr(self, 'page_returned_cheques', None),
            getattr(self, 'page_defaulted_clients', None),
            getattr(self, 'page_guarantees', None),
            getattr(self, 'page_creditworthiness', None),
            getattr(self, 'page_contributing_clients', None),
            getattr(self, 'page_client_history', None),
            getattr(self, 'total_liabilities_inquiry', None),
            getattr(self, 'customer_collaterals_inquiry', None),
            getattr(self, 'alphabetical_employees_families', None),
            getattr(self, 'medical_balances_inquiry', None),
        ]
        for p in pages_to_hide:
            if p is not None:
                p.pack_forget()

        # 2. إرجاع لون كل الزراير للحالة الطبيعية
        buttons_to_reset = [
            getattr(self, 'btn_nuwairy', None),
            getattr(self, 'btn_gl_inquiry', None),
            getattr(self, 'btn_customer', None),
            getattr(self, 'btn_stopped_cheques', None),
            getattr(self, 'btn_rejected_cheques', None),
            getattr(self, 'btn_customer_balance', None),
            getattr(self, 'btn_cancelled_certs', None),
            getattr(self, 'btn_mandates', None),
            getattr(self, 'btn_instructions', None),
            getattr(self, 'btn_local_recruitment', None),
            getattr(self, 'btn_sponsors_inquiry', None),
            getattr(self, 'btn_returned_cheques', None),
            getattr(self, 'btn_defaulted_clients', None),
            getattr(self, 'btn_guarantees', None),
            getattr(self, 'btn_creditworthiness', None),
            getattr(self, 'btn_contributing_clients', None),
            getattr(self, 'btn_client_history', None),
            getattr(self, 'total_liabilities_inquiry', None),
            getattr(self, 'customer_collaterals_inquiry', None),
            getattr(self, 'alphabetical_employees_families', None),
            getattr(self, 'medical_balances_inquiry', None),
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
        elif name == "stopped_cheques":
            if hasattr(self, 'page_stopped_cheques'):
                self.page_stopped_cheques.pack(fill="both", expand=True)
            if hasattr(self, 'btn_stopped_cheques'):
                self.btn_stopped_cheques.configure(fg_color=FIB_GREEN, text_color="white")
            if hasattr(self, 'load_stopped_cheques_data'):
                self.load_stopped_cheques_data()

        elif name == "rejected_cheques":
            if hasattr(self, 'page_rejected_cheques'):
                self.page_rejected_cheques.pack(fill="both", expand=True)
            if hasattr(self, 'btn_rejected_cheques'):
                self.btn_rejected_cheques.configure(fg_color=FIB_GREEN, text_color="white")
            if hasattr(self, 'load_rejected_cheques_data'):
                self.load_rejected_cheques_data()
        elif name == "customer_balance":
            if hasattr(self, 'page_customer_balance'):
                self.page_customer_balance.pack(fill="both", expand=True)
            if hasattr(self, 'btn_customer_balance'):
                self.btn_customer_balance.configure(fg_color=FIB_GREEN, text_color="white")

        # --- تشغيل شاشة الشهادات الملغاة الجديدة ---
        elif name == "cancelled_certs":
            if hasattr(self, 'page_cancelled_certs'):
                self.page_cancelled_certs.pack(fill="both", expand=True)
            if hasattr(self, 'btn_cancelled_certs'):
                self.btn_cancelled_certs.configure(fg_color=FIB_GREEN, text_color="white")
            # تحميل الفروع تلقائياً عند فتح الشاشة لو دالة الفروع متاحة عندك
            if hasattr(self, 'nuwairy_load_branches'):
                self.nuwairy_load_branches()

        # --- تشغيل شاشة التوكيلات الجديدة ---
        elif name == "mandates":
            if hasattr(self, 'page_mandates'):
                self.page_mandates.pack(fill="both", expand=True)
            if hasattr(self, 'btn_mandates'):
                self.btn_mandates.configure(fg_color=FIB_GREEN, text_color="white")
            if hasattr(self, 'nuwairy_load_branches'):
                self.nuwairy_load_branches()
        # --- تشغيل شاشة التعليمات الجديدة ---
        elif name == "instructions":
            if hasattr(self, 'page_instructions'):
                self.page_instructions.pack(fill="both", expand=True)
            if hasattr(self, 'btn_instructions'):
                self.btn_instructions.configure(fg_color=FIB_GREEN, text_color="white")
            if hasattr(self, 'nuwairy_load_branches'):
                self.nuwairy_load_branches()

        # --- تشغيل شاشة التوظيف المحلي الجديدة ---
        elif name == "local_recruitment":
            if hasattr(self, 'page_local_recruitment'):
                self.page_local_recruitment.pack(fill="both", expand=True)
            if hasattr(self, 'btn_local_recruitment'):
                self.btn_local_recruitment.configure(fg_color=FIB_GREEN, text_color="white")
            if hasattr(self, 'nuwairy_load_branches'):
                self.nuwairy_load_branches()

        # --- تشغيل شاشة الكفلاء الجديدة ---
        elif name == "sponsors_inquiry":
            if hasattr(self, 'page_sponsors_inquiry'):
                self.page_sponsors_inquiry.pack(fill="both", expand=True)
            if hasattr(self, 'btn_sponsors_inquiry'):
                self.btn_sponsors_inquiry.configure(fg_color=FIB_GREEN, text_color="white")
            if hasattr(self, 'nuwairy_load_branches'):
                self.nuwairy_load_branches()
        # --- تشغيل شاشة الشيكات المرتدة ---
        elif name == "returned_cheques":
            if hasattr(self, 'page_returned_cheques'):
                self.page_returned_cheques.pack(fill="both", expand=True)
            if hasattr(self, 'btn_returned_cheques'):
                self.btn_returned_cheques.configure(fg_color=FIB_GREEN, text_color="white")
            if hasattr(self, 'nuwairy_load_branches'):
                self.nuwairy_load_branches()
        elif name == "defaulted_clients":
            if hasattr(self, 'page_defaulted_clients'):
                self.page_defaulted_clients.pack(fill="both", expand=True)
            if hasattr(self, 'btn_rdefaulted_clients'):
                self.btn_defaulted_clients.configure(fg_color=FIB_GREEN, text_color="white")
            if hasattr(self, 'nuwairy_load_branches'):
                self.nuwairy_load_branches()

        elif name == "guarantees":
            if hasattr(self, 'page_guarantees'):
                self.page_guarantees.pack(fill="both", expand=True)
            if hasattr(self, 'btn_guarantees'):
                self.btn_guarantees.configure(fg_color=FIB_GREEN, text_color="white")
            if hasattr(self, 'nuwairy_load_branches'):
                self.nuwairy_load_branches()
        elif name == "creditworthiness":
            if hasattr(self, 'page_creditworthiness'):
                self.page_creditworthiness.pack(fill="both", expand=True)
            if hasattr(self, 'btn_creditworthiness'):
                self.btn_creditworthiness.configure(fg_color=FIB_GREEN, text_color="white")
            if hasattr(self, 'nuwairy_load_branches'):
                self.nuwairy_load_branches()
        elif name == "contributing_clients":
            if hasattr(self, 'page_contributing_clients'):
                self.page_contributing_clients.pack(fill="both", expand=True)
            if hasattr(self, 'btn_contributing_clients'):
                self.btn_contributing_clients.configure(fg_color=FIB_GREEN, text_color="white")
        elif name == "client_history":
            if hasattr(self, 'page_client_history'):
                self.page_client_history.pack(fill="both", expand=True)
            if hasattr(self, 'btn_client_history'):
                self.btn_client_history.configure(fg_color=FIB_GREEN, text_color="white")
            if hasattr(self, 'nuwairy_load_branches'):
                self.nuwairy_load_branches()
        elif name == "total_liabilities_inquiry":
            if hasattr(self, 'page_total_liabilities_inquiry'):
                self.page_total_liabilities_inquiry.pack(fill="both", expand=True)
            if hasattr(self, 'btn_total_liabilities_inquiry'):
                self.btn_total_liabilities_inquiry.configure(fg_color=FIB_GREEN, text_color="white")
            if hasattr(self, 'nuwairy_load_branches'):
                self.nuwairy_load_branches()
        elif name == "customer_collaterals_inquiry":
            if hasattr(self, 'page_customer_collaterals_inquiry'):
                self.page_customer_collaterals_inquiry.pack(fill="both", expand=True)
            if hasattr(self, 'btn_customer_collaterals_inquiry'):
                self.btn_customer_collaterals_inquiry.configure(fg_color=FIB_GREEN, text_color="white")
            if hasattr(self, 'nuwairy_load_branches'):
                self.nuwairy_load_branches()
        elif name == "alphabetical_employees_families":
            if hasattr(self, 'page_alphabetical_employees_families'):
                self.page_alphabetical_employees_families.pack(fill="both", expand=True)
            if hasattr(self, 'btn_alphabetical_employees_families'):
                self.btn_alphabetical_employees_families.configure(fg_color=FIB_GREEN, text_color="white")
        elif name == "medical_balances_inquiry":
            if hasattr(self, 'page_medical_balances_inquiry'):
                self.page_medical_balances_inquiry.pack(fill="both", expand=True)
            if hasattr(self, 'btn_medical_balances_inquiry'):
                self.btn_medical_balances_inquiry.configure(fg_color=FIB_GREEN, text_color="white")

    def setup_medical_balances_inquiry_ui(self, parent):
        import pandas as pd
        import customtkinter as ctk
        from tkinter import messagebox
        import threading
        import logging

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
            header, text="الاستفسار عن أرصدة العلاج الطبي للموظفين 🏥",
            font=("Segoe UI", 22, "bold"), text_color=CARD_BG
        ).pack(side="right", padx=30, pady=15)

        # =========================================
        # 🔍 منطقة البحث (رقم الملف فقط)
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

        self.ent_med_file_no = ctk.CTkEntry(search_inner, font=("Segoe UI", 15, "bold"), justify="center",
                                            placeholder_text="رقم الملف...", width=200, height=40,
                                            border_color="#CBD5E1")
        self.ent_med_file_no.pack(side="left", padx=10)
        ctk.CTkLabel(search_inner, text="رقم الملف:", font=("Segoe UI", 14, "bold"), text_color=TEXT_DARK).pack(
            side="left", padx=(10, 2))

        self.med_results_scroll = ctk.CTkScrollableFrame(main_container, fg_color="transparent")
        self.med_results_scroll.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        # =========================================
        # ⚙️ إعدادات الأحداث
        # =========================================
        self.ent_med_file_no.bind("<Return>", lambda event: execute_search())

        def clear_search():
            self.ent_med_file_no.delete(0, 'end')
            for widget in self.med_results_scroll.winfo_children():
                widget.destroy()

        def safe_float(val):
            try:
                if pd.isna(val) or str(val).strip() == '':
                    return 0.0
                return float(val)
            except (ValueError, TypeError):
                return 0.0

        # =========================================
        # 🚀 تنفيذ الاستعلام وجلب البيانات
        # =========================================
        def execute_search():
            file_no = self.ent_med_file_no.get().strip()

            if not file_no:
                messagebox.showwarning("تنبيه", "يرجى إدخال رقم الملف")
                return

            for widget in self.med_results_scroll.winfo_children():
                widget.destroy()

            ctk.CTkLabel(self.med_results_scroll, text="⚡ جاري جلب بيانات العلاج الطبي...",
                         font=("Segoe UI", 16, "bold"), text_color=FIB_GOLD).pack(pady=50)

            def fetch_data():
                try:
                    engine = getattr(self, '_get_db_connection', lambda: None)()
                    if not engine:
                        raise Exception("لا يوجد اتصال بقاعدة البيانات.")

                    # الاستعلام مبني على رقم الملف (PDOC)
                    query = """
                            SELECT Pname, \
                                   PTAMT2, \
                                   PTAMT1, \
                                   PEAMT4, \
                                   PEAMT2, \
                                   PEAMT, \
                                   PEAMTB
                            FROM [dbo].[TBL_medical_treatment] \
                            WITH (NOLOCK)
                            WHERE PDOC = ? \
                            """
                    df = pd.read_sql(query, engine, params=(file_no,))

                    self.after(0, lambda d=df, f=file_no: update_results_ui(d, f))
                except Exception as e:
                    err_msg = str(e)
                    logging.error(f"Error fetching medical data: {err_msg}")
                    self.after(0, lambda err=err_msg: update_results_ui(pd.DataFrame(), file_no, error=err))

            threading.Thread(target=fetch_data, daemon=True).start()

        # =========================================
        # 📑 عرض الواجهة الإحصائية للنتائج
        # =========================================
        def update_results_ui(df, file_no, error=None):
            for widget in self.med_results_scroll.winfo_children():
                widget.destroy()

            if error:
                ctk.CTkLabel(self.med_results_scroll, text=f"❌ حدث خطأ أثناء الاستعلام:\n{error}",
                             font=("Segoe UI", 14, "bold"), text_color="#EF4444").pack(pady=40)
                return

            if df.empty:
                ctk.CTkLabel(self.med_results_scroll, text="✔️ لا توجد بيانات علاج مسجلة لرقم الملف المدخل.",
                             font=("Segoe UI", 18, "bold"), text_color=TEXT_MUTED).pack(pady=60)
                return

            # أخذ السجل الأول (بافتراض أن رقم الملف فريد للموظف)
            row = df.iloc[0]
            emp_name = row.get('Pname', 'غير مدرج')
            if pd.isna(emp_name) or str(emp_name).strip() == "":
                emp_name = "غير مدرج"

            # ==================== كارت معلومات الموظف ====================
            header_card = ctk.CTkFrame(self.med_results_scroll, fg_color=CARD_BG, corner_radius=12, border_width=1,
                                       border_color="#CBD5E1")
            header_card.pack(fill="x", padx=10, pady=(5, 10))

            top_row = ctk.CTkFrame(header_card, fg_color="transparent")
            top_row.pack(fill="x", padx=20, pady=15)

            ctk.CTkLabel(top_row, text=f"👤 اسم الموظف: {emp_name}", font=("Segoe UI", 18, "bold"),
                         text_color=TEXT_DARK).pack(side="right")

            info_tags = ctk.CTkFrame(top_row, fg_color="transparent")
            info_tags.pack(side="left")
            ctk.CTkLabel(info_tags, text=f"رقم الملف: {file_no}", font=("Segoe UI", 14, "bold"), text_color=FIB_GOLD,
                         fg_color=BOX_BG, corner_radius=6).pack(side="left", padx=4, ipadx=8, ipady=3)

            # ==================== كروت تفاصيل الأرصدة والمصاريف ====================
            details_card = ctk.CTkFrame(self.med_results_scroll, fg_color=CARD_BG, corner_radius=12, border_width=1,
                                        border_color="#E2E8F0")
            details_card.pack(fill="x", padx=10, pady=10)

            card_title = ctk.CTkFrame(details_card, fg_color="transparent")
            card_title.pack(fill="x", padx=15, pady=(15, 5))
            ctk.CTkLabel(card_title, text="💰 تفاصيل ومصاريف العلاج", font=("Segoe UI", 16, "bold"),
                         text_color=FIB_GREEN).pack(side="right")
            ctk.CTkFrame(details_card, fg_color="#F1F5F9", height=2).pack(fill="x", padx=15, pady=5)

            def create_stat_box(parent, title, value_str, v_color=TEXT_DARK):
                box = ctk.CTkFrame(parent, fg_color=BOX_BG, corner_radius=8)
                box.pack(side="right", fill="both", expand=True, padx=6, pady=5)
                ctk.CTkLabel(box, text=title, font=("Segoe UI", 13, "bold"), text_color=TEXT_MUTED).pack(
                    anchor="center", pady=(10, 2))
                ctk.CTkLabel(box, text=value_str, font=("Segoe UI", 16, "bold"), text_color=v_color).pack(
                    anchor="center", pady=(0, 10))

            # --- الصف الأول: مصاريف الموظف ---
            row1 = ctk.CTkFrame(details_card, fg_color="transparent")
            row1.pack(fill="x", padx=15, pady=5)

            ptamt2 = safe_float(row.get('PTAMT2'))
            ptamt1 = safe_float(row.get('PTAMT1'))

            create_stat_box(row1, "إجمالي مصاريف علاج الموظف (PTAMT1)", f"{ptamt1:,.2f}", FIB_GREEN)
            create_stat_box(row1, "مصاريف علاج الموظف السنوية (PTAMT2)", f"{ptamt2:,.2f}", TEXT_DARK)

            # --- الصف الثاني: مصاريف العمليات الأسرية ---
            row2 = ctk.CTkFrame(details_card, fg_color="transparent")
            row2.pack(fill="x", padx=15, pady=5)

            peamt2 = safe_float(row.get('PEAMT2'))
            peamt4 = safe_float(row.get('PEAMT4'))

            create_stat_box(row2, "إجمالي مصاريف عمليات أسرية (PEAMT2)", f"{peamt2:,.2f}", FIB_GOLD)
            create_stat_box(row2, "مصاريف عمليات أسرية سنوية (PEAMT4)", f"{peamt4:,.2f}", TEXT_DARK)

            # --- الصف الثالث: العلاج الأسري والباقي ---
            row3 = ctk.CTkFrame(details_card, fg_color="transparent")
            row3.pack(fill="x", padx=15, pady=(5, 15))

            peamt = safe_float(row.get('PEAMT'))
            peamtb = safe_float(row.get('PEAMTB'))

            # حساب الباقي (طرح PEAMT من PEAMTB)
            remaining = peamt - peamtb

            create_stat_box(row3, "مبلغ العلاج الأسري (PEAMT)", f"{peamt:,.2f}", TEXT_DARK)
            create_stat_box(row3, "رصيد العلاج الأسري (PEAMTB)", f"{peamtb:,.2f}", TEXT_DARK)
            create_stat_box(row3, "الباقي", f"{remaining:,.2f} دائن", "#DC2626")  # تم إضافة كلمة "دائن" هنا
    def setup_alphabetical_employees_families_ui(self, parent):
        import pandas as pd
        import customtkinter as ctk
        from tkinter import messagebox
        import threading
        import logging
        import re

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
            header, text="الاستفسار الأبجدي عن الموظفين وأسرهم 👨‍👩‍👧‍👦",
            font=("Segoe UI", 22, "bold"), text_color=CARD_BG
        ).pack(side="right", padx=30, pady=15)

        # =========================================
        # 🔍 منطقة البحث (الاسم فقط)
        # =========================================
        search_frame = ctk.CTkFrame(main_container, fg_color=CARD_BG, corner_radius=15, border_width=1,
                                    border_color="#E2E8F0")
        search_frame.pack(fill="x", padx=20, pady=15)

        search_inner = ctk.CTkFrame(search_frame, fg_color="transparent")
        search_inner.pack(side="right", fill="y", padx=20, pady=15)

        # الأزرار
        btn_clear = ctk.CTkButton(search_inner, text="🧹 مسح", font=("Segoe UI", 14, "bold"), fg_color="#64748B",
                                  hover_color="#475569", width=80, height=40, corner_radius=8,
                                  command=lambda: clear_search())
        btn_clear.pack(side="left", padx=(5, 10))

        btn_search = ctk.CTkButton(search_inner, text="🔍 بحث", font=("Segoe UI", 15, "bold"), fg_color=FIB_GREEN,
                                   hover_color="#004426", width=100, height=40, corner_radius=8,
                                   command=lambda: execute_search())
        btn_search.pack(side="left", padx=5)

        # إدخال الاسم
        self.ent_emp_search_name = ctk.CTkEntry(search_inner, font=("Segoe UI", 15, "bold"), justify="right",
                                                placeholder_text="أدخل اسم الموظف أو المستفيد...", width=350, height=40,
                                                border_color="#CBD5E1")
        self.ent_emp_search_name.pack(side="left", padx=10)
        ctk.CTkLabel(search_inner, text="الاسم:", font=("Segoe UI", 14, "bold"), text_color=TEXT_DARK).pack(side="left",
                                                                                                            padx=(10,
                                                                                                                  2))

        # فريم نتائج البحث
        self.emp_results_scroll = ctk.CTkScrollableFrame(main_container, fg_color="transparent")
        self.emp_results_scroll.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        # =========================================
        # ⏱️ البحث المباشر أثناء الكتابة (Live Search)
        # =========================================
        self.emp_search_timer = None

        def on_key_release(event):
            if self.emp_search_timer is not None:
                self.after_cancel(self.emp_search_timer)
            self.emp_search_timer = self.after(500, execute_search)

        self.ent_emp_search_name.bind("<KeyRelease>", on_key_release)
        self.ent_emp_search_name.bind("<Return>", lambda event: execute_search())

        # =========================================
        # 🛠️ معالجة الاسم العربي الملتصق لتجميل العرض
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
            self.ent_emp_search_name.delete(0, 'end')
            for widget in self.emp_results_scroll.winfo_children():
                widget.destroy()

        # =========================================
        # 🚀 تنفيذ الاستعلام من قاعدة البيانات
        # =========================================
        def execute_search():
            search_name = self.ent_emp_search_name.get().strip()

            # لو المربع فاضي، امسح النتائج فقط وماتعملش سيرش
            if not search_name:
                for widget in self.emp_results_scroll.winfo_children():
                    widget.destroy()
                return

            for widget in self.emp_results_scroll.winfo_children():
                widget.destroy()

            ctk.CTkLabel(self.emp_results_scroll, text="⚡ جاري البحث في السجلات الطبية...",
                         font=("Segoe UI", 16, "bold"), text_color=FIB_GOLD).pack(pady=50)

            def fetch_data():
                try:
                    engine = getattr(self, '_get_db_connection', lambda: None)()
                    if not engine:
                        raise Exception("لا يوجد اتصال بقاعدة البيانات.")

                    # الاستعلام: جلب الأسماء بدون تكرار وترتيبها أبجدياً
                    query = """
                            SELECT DISTINCT Bname
                            FROM [dbo].[TBL_medical_treatment] \
                            WITH (NOLOCK)
                            WHERE Bname LIKE ?
                            ORDER BY Bname ASC \
                            """

                    # استخدام % بعد النص لجلب أي اسم يبدأ بالحروف المدخلة
                    search_param = f"{search_name}%"
                    df = pd.read_sql(query, engine, params=(search_param,))

                    self.after(0, lambda d=df: update_results_ui(d))
                except Exception as e:
                    err_msg = str(e)
                    logging.error(f"Error fetching employees: {err_msg}")
                    self.after(0, lambda err=err_msg: update_results_ui(pd.DataFrame(), error=err))

            threading.Thread(target=fetch_data, daemon=True).start()

        # =========================================
        # 📑 عرض نتائج الواجهة
        # =========================================
        def update_results_ui(df, error=None):
            for widget in self.emp_results_scroll.winfo_children():
                widget.destroy()

            if error:
                ctk.CTkLabel(self.emp_results_scroll, text=f"❌ حدث خطأ أثناء الاستعلام:\n{error}",
                             font=("Segoe UI", 14, "bold"), text_color="#EF4444").pack(pady=40)
                return

            if df.empty:
                ctk.CTkLabel(self.emp_results_scroll, text="✔️ لا توجد أسماء مطابقة لبحثك",
                             font=("Segoe UI", 18, "bold"), text_color=TEXT_MUTED).pack(pady=60)
                return

            results_count_frame = ctk.CTkFrame(self.emp_results_scroll, fg_color="transparent")
            results_count_frame.pack(fill="x", padx=10, pady=(0, 10))
            ctk.CTkLabel(results_count_frame, text=f"تم العثور على ({len(df)}) نتيجة مطابقة",
                         font=("Segoe UI", 13, "bold"), text_color=FIB_GREEN).pack(side="right")

            # عرض الأسماء في كروت مبسطة وأنيقة
            for index, row in df.iterrows():
                raw_name = row.get('Bname', 'غير متوفر')
                formatted_name = format_arabic_name(raw_name)

                card = ctk.CTkFrame(self.emp_results_scroll, fg_color=CARD_BG, corner_radius=10, border_width=1,
                                    border_color="#CBD5E1")
                card.pack(fill="x", padx=10, pady=5)

                inner_row = ctk.CTkFrame(card, fg_color="transparent")
                inner_row.pack(fill="x", padx=20, pady=12)

                ctk.CTkLabel(inner_row, text=f"👤 {formatted_name}", font=("Segoe UI", 18, "bold"),
                             text_color=TEXT_DARK).pack(side="right")
    def setup_customer_collaterals_inquiry_ui(self, parent):
        import pandas as pd
        import customtkinter as ctk
        from tkinter import messagebox
        import threading
        import logging

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
            header, text="الاستفسار عن الضمانات لعميل 🛡️",
            font=("Segoe UI", 22, "bold"), text_color=CARD_BG
        ).pack(side="right", padx=30, pady=15)

        # =========================================
        # 🔍 منطقة البحث (الفرع ورقم الحساب)
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

        self.ent_col_account_no = ctk.CTkEntry(search_inner, font=("Segoe UI", 15, "bold"), justify="center",
                                               placeholder_text="رقم الحساب...", width=160, height=40,
                                               border_color="#CBD5E1")
        self.ent_col_account_no.pack(side="left", padx=10)
        ctk.CTkLabel(search_inner, text="رقم الحساب:", font=("Segoe UI", 14, "bold"), text_color=TEXT_DARK).pack(
            side="left", padx=(10, 2))

        if hasattr(self, '_create_premium_select'):
            self.cmb_col_branch_box, self.cmb_col_branch = self._create_premium_select(search_inner,
                                                                                       values=["جاري التحميل..."],
                                                                                       default="جاري التحميل...",
                                                                                       title="اختر الفرع")
            self.cmb_col_branch_box.pack(side="left", padx=10)
        else:
            self.cmb_col_branch = ctk.CTkComboBox(search_inner, font=("Segoe UI", 14, "bold"), justify="right",
                                                  width=200, height=40, border_color="#CBD5E1")
            self.cmb_col_branch.pack(side="left", padx=10)
        ctk.CTkLabel(search_inner, text="الفرع:", font=("Segoe UI", 14, "bold"), text_color=TEXT_DARK).pack(side="left",
                                                                                                            padx=(10,
                                                                                                                  2))

        self.col_results_scroll = ctk.CTkScrollableFrame(main_container, fg_color="transparent")
        self.col_results_scroll.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        # =========================================
        # ⚙️ دوال المساعدة وتحميل البيانات
        # =========================================
        def load_initial_branches():
            if hasattr(self, 'branch_mapping') and self.branch_mapping:
                branches = list(self.branch_mapping.keys())
                self.cmb_col_branch.configure(values=branches)
                self.cmb_col_branch.set(branches[0])
            else:
                self.after(500, load_initial_branches)

        self.after(500, load_initial_branches)
        self.ent_col_account_no.bind("<Return>", lambda event: execute_search())

        def clear_search():
            self.ent_col_account_no.delete(0, 'end')
            for widget in self.col_results_scroll.winfo_children():
                widget.destroy()

        def safe_float(val):
            try:
                if pd.isna(val) or str(val).strip() == '':
                    return 0.0
                return float(val)
            except (ValueError, TypeError):
                return 0.0

        # =========================================
        # 🚀 تنفيذ الاستعلامات حسب طلبك حرفياً
        # =========================================
        def execute_search():
            branch_name = self.cmb_col_branch.get().strip()
            account_no = self.ent_col_account_no.get().strip()

            if not account_no:
                messagebox.showwarning("تنبيه", "يرجى إدخال رقم الحساب")
                return

            for widget in self.col_results_scroll.winfo_children():
                widget.destroy()

            ctk.CTkLabel(self.col_results_scroll, text="⚡ جاري تجميع بيانات الضمانات...", font=("Segoe UI", 16, "bold"),
                         text_color=FIB_GOLD).pack(pady=50)

            def fetch_data():
                try:
                    engine = getattr(self, '_get_db_connection', lambda: None)()
                    if not engine:
                        raise Exception("لا يوجد اتصال بقاعدة البيانات.")

                    # 1. جلب رقم الفرع (branchcode) واسم الجدول (tablename) من tbl_branches
                    branch_query = "SELECT branchcode, tablename FROM [dbo].[tbl_branches] WITH (NOLOCK) WHERE branchname = ?"
                    df_branch = pd.read_sql(branch_query, engine, params=(branch_name,))

                    if df_branch.empty:
                        raise Exception("تعذر العثور على بيانات الفرع في جدول الفروع.")

                    branch_code = str(df_branch.iloc[0]['branchcode']).strip()
                    client_table_name = str(df_branch.iloc[0]['tablename']).strip()

                    if not client_table_name or client_table_name.lower() == 'nan':
                        raise Exception("اسم جدول العملاء (tablename) غير مسجل لهذا الفرع.")

                    # 2. جلب اسم العميل (Bname) من الجدول المستخرج بناءً على رقم العميل (bclnt)
                    client_query = f"SELECT Bname FROM [dbo].[{client_table_name}] WITH (NOLOCK) WHERE bclnt = ?"
                    df_client = pd.read_sql(client_query, engine, params=(account_no,))
                    client_name = str(
                        df_client.iloc[0]['Bname']).strip() if not df_client.empty else "الاسم غير مدرج بالجدول"

                    # 3. جدول الضمانات (TBL_customer_Collaterals): جلب الحقول المطلوبة حرفياً
                    col_query = """
                                SELECT GGL, \
                                       GSUB, \
                                       GCUR, \
                                       GNO1, \
                                       GKND, \
                                       GAMT, \
                                       GDAT1, \
                                       GDAT2, \
                                       GNM, \
                                       GDAT3, \
                                       GSTP, \
                                       GNM1
                                FROM [dbo].[TBL_customer_Collaterals] \
                                WITH (NOLOCK)
                                WHERE GBR = ? AND GCLNT = ? \
                                """
                    df_collaterals = pd.read_sql(col_query, engine, params=(branch_code, account_no))

                    results = {
                        "client_name": client_name,
                        "collaterals": df_collaterals
                    }

                    self.after(0, lambda r=results, b=branch_name, a=account_no: update_results_ui(r, b, a))
                except Exception as e:
                    err_msg = str(e)
                    logging.error(f"Error fetching collaterals: {err_msg}")
                    self.after(0, lambda err=err_msg: update_results_ui(None, branch_name, account_no, error=err))

            threading.Thread(target=fetch_data, daemon=True).start()

        # =========================================
        # 📑 عرض الواجهة الإحصائية للنتائج
        # =========================================
        def update_results_ui(results, branch_name, account_no, error=None):
            for widget in self.col_results_scroll.winfo_children():
                widget.destroy()

            if error:
                ctk.CTkLabel(self.col_results_scroll, text=f"❌ حدث خطأ أثناء الاستعلام:\n{error}",
                             font=("Segoe UI", 14, "bold"), text_color="#EF4444").pack(pady=40)
                return

            if not results:
                return

            # ==================== كارت معلومات العميل ====================
            header_card = ctk.CTkFrame(self.col_results_scroll, fg_color=CARD_BG, corner_radius=12, border_width=1,
                                       border_color="#CBD5E1")
            header_card.pack(fill="x", padx=10, pady=(5, 10))

            top_row = ctk.CTkFrame(header_card, fg_color="transparent")
            top_row.pack(fill="x", padx=20, pady=15)

            ctk.CTkLabel(top_row, text=f"👤 اسم العميل: {results['client_name']}", font=("Segoe UI", 18, "bold"),
                         text_color=TEXT_DARK).pack(side="right")

            info_tags = ctk.CTkFrame(top_row, fg_color="transparent")
            info_tags.pack(side="left")
            ctk.CTkLabel(info_tags, text=f"الحساب: {account_no}", font=("Segoe UI", 13, "bold"), text_color=FIB_GOLD,
                         fg_color=BOX_BG, corner_radius=6).pack(side="left", padx=4, ipadx=8, ipady=3)
            ctk.CTkLabel(info_tags, text=f"الفرع: {branch_name}", font=("Segoe UI", 13, "bold"), text_color=TEXT_MUTED,
                         fg_color=BOX_BG, corner_radius=6).pack(side="left", padx=4, ipadx=8, ipady=3)

            df_col = results['collaterals']
            if df_col.empty:
                ctk.CTkLabel(self.col_results_scroll, text="✔️ لا توجد ضمانات مسجلة لهذا العميل.",
                             font=("Segoe UI", 16, "bold"), text_color=TEXT_MUTED).pack(pady=40)
                return

            # ==================== كروت تفاصيل الضمانات ====================
            ctk.CTkLabel(self.col_results_scroll, text=f"📑 تفاصيل الضمانات ({len(df_col)})",
                         font=("Segoe UI", 16, "bold"), text_color=FIB_GREEN).pack(anchor="e", padx=15, pady=(10, 5))

            def format_date(val):
                if pd.isna(val) or str(val).strip() == '': return "—"
                try:
                    return pd.to_datetime(val).strftime('%Y-%m-%d')
                except:
                    return str(val)

            # عرض الكروت بناءً على الأعمدة المطلوبة فقط
            for _, row in df_col.iterrows():
                col_card = ctk.CTkFrame(self.col_results_scroll, fg_color=CARD_BG, corner_radius=10, border_width=1,
                                        border_color="#E2E8F0")
                col_card.pack(fill="x", padx=10, pady=6)

                card_top = ctk.CTkFrame(col_card, fg_color="transparent")
                card_top.pack(fill="x", padx=15, pady=10)

                gnm = row.get('GNM', '—')
                gamt = safe_float(row.get('GAMT', 0))
                gcur = row.get('GCUR', '')

                ctk.CTkLabel(card_top, text=f"📌 وصف الضمان : {gnm}", font=("Segoe UI", 16, "bold"),
                             text_color=TEXT_DARK).pack(side="right")
                ctk.CTkLabel(card_top, text=f"قيمة الضمان: {gamt:,.2f}", font=("Segoe UI", 15, "bold"),
                             text_color=FIB_GREEN, fg_color=BOX_BG, corner_radius=6).pack(side="left", ipadx=10,
                                                                                          ipady=3)

                ctk.CTkFrame(col_card, fg_color="#F1F5F9", height=2).pack(fill="x", padx=15)

                details_frame = ctk.CTkFrame(col_card, fg_color="transparent")
                details_frame.pack(fill="x", padx=15, pady=10)

                # --- العمود الأول (يمين) ---
                p1 = ctk.CTkFrame(details_frame, fg_color="transparent")
                p1.pack(side="right", fill="both", expand=True)
                ctk.CTkLabel(p1, text=f"رقم الضمان : {row.get('GNO1', '—')}", font=("Segoe UI", 13)).pack(
                    anchor="e", pady=2)
                ctk.CTkLabel(p1, text=f"نوع الضمان : {row.get('GKND', '—')}", font=("Segoe UI", 13)).pack(
                    anchor="e", pady=2)
                ctk.CTkLabel(p1, text=f"الأستاذ العام الرئيسي: {row.get('GGL', '—')}",
                             font=("Segoe UI", 13)).pack(anchor="e", pady=2)
                ctk.CTkLabel(p1, text=f"الأستاذ العام الفرعي: {row.get('GSUB', '—')}",
                             font=("Segoe UI", 13)).pack(anchor="e", pady=2)

                # --- العمود الثاني (وسط) ---
                p2 = ctk.CTkFrame(details_frame, fg_color="transparent")
                p2.pack(side="right", fill="both", expand=True)
                ctk.CTkLabel(p2, text=f"تاريخ نهاية الضمان: {format_date(row.get('GDAT1'))}",
                             font=("Segoe UI", 13)).pack(anchor="e", pady=2)
                ctk.CTkLabel(p2, text=f"تاريخ تجدد البوليصة: {format_date(row.get('GDAT2'))}",
                             font=("Segoe UI", 13)).pack(anchor="e", pady=2)
                ctk.CTkLabel(p2, text=f"تاريخ آخر تقييم: {format_date(row.get('GDAT3'))}",
                             font=("Segoe UI", 13)).pack(anchor="e", pady=2)

                # --- العمود الثالث (يسار) ---
                p3 = ctk.CTkFrame(details_frame, fg_color="transparent")
                p3.pack(side="right", fill="both", expand=True)
                ctk.CTkLabel(p3, text=f"درجة الرهن (GSTP): {row.get('GSTP', '—')}", font=("Segoe UI", 13)).pack(
                    anchor="e", pady=2)
                ctk.CTkLabel(p3, text=f"اسم الخبير (GNM1): {row.get('GNM1', '—')}", font=("Segoe UI", 13)).pack(
                    anchor="e", pady=2)
    def setup_total_liabilities_inquiry_ui(self, parent):
        import pandas as pd
        import customtkinter as ctk
        from tkinter import messagebox
        import threading
        import logging

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
            header, text="الاستفسار عن إجمالي التزامات عميل 💼",
            font=("Segoe UI", 22, "bold"), text_color=CARD_BG
        ).pack(side="right", padx=30, pady=15)

        # =========================================
        # 🔍 منطقة البحث (الفرع ورقم الحساب)
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

        self.ent_liab_account_no = ctk.CTkEntry(search_inner, font=("Segoe UI", 15, "bold"), justify="center",
                                                placeholder_text="رقم الحساب...", width=160, height=40,
                                                border_color="#CBD5E1")
        self.ent_liab_account_no.pack(side="left", padx=10)
        ctk.CTkLabel(search_inner, text="رقم الحساب:", font=("Segoe UI", 14, "bold"), text_color=TEXT_DARK).pack(
            side="left", padx=(10, 2))

        if hasattr(self, '_create_premium_select'):
            self.cmb_liab_branch_box, self.cmb_liab_branch = self._create_premium_select(search_inner,
                                                                                         values=["جاري التحميل..."],
                                                                                         default="جاري التحميل...",
                                                                                         title="اختر الفرع")
            self.cmb_liab_branch_box.pack(side="left", padx=10)
        else:
            self.cmb_liab_branch = ctk.CTkComboBox(search_inner, font=("Segoe UI", 14, "bold"), justify="right",
                                                   width=200, height=40, border_color="#CBD5E1")
            self.cmb_liab_branch.pack(side="left", padx=10)
        ctk.CTkLabel(search_inner, text="الفرع:", font=("Segoe UI", 14, "bold"), text_color=TEXT_DARK).pack(side="left",
                                                                                                            padx=(10,
                                                                                                                  2))

        self.liab_results_scroll = ctk.CTkScrollableFrame(main_container, fg_color="transparent")
        self.liab_results_scroll.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        # =========================================
        # ⚙️ تحميل الفروع وإعداد الأحداث
        # =========================================
        def load_initial_branches():
            if hasattr(self, 'branch_mapping') and self.branch_mapping:
                branches = list(self.branch_mapping.keys())
                self.cmb_liab_branch.configure(values=branches)
                self.cmb_liab_branch.set(branches[0])
            else:
                self.after(500, load_initial_branches)

        self.after(500, load_initial_branches)
        self.ent_liab_account_no.bind("<Return>", lambda event: execute_search())

        def clear_search():
            self.ent_liab_account_no.delete(0, 'end')
            for widget in self.liab_results_scroll.winfo_children():
                widget.destroy()

        def safe_float(val):
            try:
                if pd.isna(val) or str(val).strip() == '':
                    return 0.0
                return float(val)
            except (ValueError, TypeError):
                return 0.0

        # =========================================
        # 🚀 تنفيذ الاستعلامات وجلب البيانات
        # =========================================
        def execute_search():
            branch_name = self.cmb_liab_branch.get().strip()
            account_no = self.ent_liab_account_no.get().strip()

            if not account_no:
                messagebox.showwarning("تنبيه", "يرجى إدخال رقم الحساب")
                return

            for widget in self.liab_results_scroll.winfo_children():
                widget.destroy()

            ctk.CTkLabel(self.liab_results_scroll, text="⚡ جاري تجميع بيانات التزامات العميل...",
                         font=("Segoe UI", 16, "bold"), text_color=FIB_GOLD).pack(pady=50)

            def fetch_data():
                try:
                    engine = getattr(self, '_get_db_connection', lambda: None)()
                    if not engine:
                        raise Exception("لا يوجد اتصال بقاعدة البيانات.")

                    # 1. جلب كود الفرع واسم جدول العملاء المرتبط به
                    branch_query = "SELECT branchcode, tablename FROM [dbo].[tbl_branches] WITH (NOLOCK) WHERE branchname = ?"
                    df_branch = pd.read_sql(branch_query, engine, params=(branch_name,))

                    if df_branch.empty:
                        raise Exception("تعذر العثور على بيانات الفرع في قاعدة البيانات.")

                    branch_code = str(df_branch.iloc[0]['branchcode']).strip()
                    client_table_name = str(df_branch.iloc[0]['tablename']).strip()

                    if not client_table_name or client_table_name.lower() == 'nan':
                        raise Exception("اسم جدول العملاء (tablename) غير مسجل لهذا الفرع.")

                    # 2. جلب اسم العميل ديناميكياً من الجدول المستخرج
                    client_query = f"SELECT Bname FROM [dbo].[{client_table_name}] WITH (NOLOCK) WHERE bclnt = ?"
                    df_client = pd.read_sql(client_query, engine, params=(account_no,))
                    client_name = str(df_client.iloc[0]['Bname']).strip() if not df_client.empty else "غير مدرج بالجدول"

                    # 3. جدول العمليات (tbl_localrecruitmentprocesses) - رصيد المدين
                    df_local = pd.read_sql(
                        "SELECT IAMT19 FROM [dbo].[tbl_localrecruitmentprocesses] WITH (NOLOCK) WHERE IBR = ? AND ICLNT = ?",
                        engine, params=(branch_code, account_no))
                    total_iamt19 = sum(safe_float(x) for x in df_local['IAMT19']) if not df_local.empty else 0.0

                    # 4. جدول الرعاة/الضامنين (tbl_sponser) - العملة الأغلب
                    df_sponsor = pd.read_sql(
                        "SELECT FAMT19, fcur FROM [dbo].[tbl_sponsers] WITH (NOLOCK) WHERE fbr = ? AND fclnt = ?",
                        engine, params=(branch_code, account_no))
                    total_sponsor = 0.0
                    if not df_sponsor.empty:
                        most_frequent_currency = df_sponsor['fcur'].mode()
                        if not most_frequent_currency.empty:
                            dominant_cur = most_frequent_currency[0]
                            total_sponsor = sum(safe_float(row['FAMT19']) for _, row in df_sponsor.iterrows() if
                                                row['fcur'] == dominant_cur)

                    # 5. جدول الضمانات (tbl_gurantees) - (lgval - lgcval)
                    df_guar = pd.read_sql(
                        "SELECT lgval, lgcval FROM [dbo].[tbl_gurantees] WITH (NOLOCK) WHERE lgbr = ? AND lgcno = ?",
                        engine, params=(branch_code, account_no))
                    total_guar = 0.0
                    if not df_guar.empty:
                        for _, row in df_guar.iterrows():
                            total_guar += (safe_float(row['lgval']) - safe_float(row['lgcval']))

                    # 6. جدول الاعتمادات (tbl_credits) - العملة الأغلب
                    df_credits = pd.read_sql(
                        "SELECT damt3, dcur3 FROM [dbo].[tbl_credits] WITH (NOLOCK) WHERE dbr = ? AND dclnt = ?", engine,
                        params=(branch_code, account_no))
                    total_credits = 0.0
                    if not df_credits.empty:
                        most_frequent_dcur = df_credits['dcur3'].mode()
                        if not most_frequent_dcur.empty:
                            dominant_dcur = most_frequent_dcur[0]
                            total_credits = sum(safe_float(row['damt3']) for _, row in df_credits.iterrows() if
                                                row['dcur3'] == dominant_dcur)

                    results = {
                        "client_name": client_name,
                        "iamt19": total_iamt19,
                        "sponsor": total_sponsor,
                        "guarantees": total_guar,
                        "credits": total_credits
                    }

                    self.after(0, lambda r=results, b=branch_name, a=account_no: update_results_ui(r, b, a))
                except Exception as e:
                    err_msg = str(e)
                    logging.error(f"Error fetching total liabilities: {err_msg}")
                    self.after(0, lambda err=err_msg: update_results_ui(None, branch_name, account_no, error=err))

            threading.Thread(target=fetch_data, daemon=True).start()

        # =========================================
        # 📑 عرض الواجهة الإحصائية للنتائج
        # =========================================
        def update_results_ui(results, branch_name, account_no, error=None):
            for widget in self.liab_results_scroll.winfo_children():
                widget.destroy()

            if error:
                ctk.CTkLabel(self.liab_results_scroll, text=f"❌ حدث خطأ أثناء الاستعلام:\n{error}",
                             font=("Segoe UI", 14, "bold"), text_color="#EF4444").pack(pady=40)
                return

            if not results:
                return

            header_card = ctk.CTkFrame(self.liab_results_scroll, fg_color=CARD_BG, corner_radius=12, border_width=1,
                                       border_color="#CBD5E1")
            header_card.pack(fill="x", padx=10, pady=(5, 15))

            top_row = ctk.CTkFrame(header_card, fg_color="transparent")
            top_row.pack(fill="x", padx=20, pady=15)

            ctk.CTkLabel(top_row, text=f"👤 اسم العميل: {results['client_name']}", font=("Segoe UI", 18, "bold"),
                         text_color=TEXT_DARK).pack(side="right")

            info_tags = ctk.CTkFrame(top_row, fg_color="transparent")
            info_tags.pack(side="left")
            ctk.CTkLabel(info_tags, text=f"الحساب: {account_no}", font=("Segoe UI", 13, "bold"), text_color=FIB_GOLD,
                         fg_color=BOX_BG, corner_radius=6).pack(side="left", padx=4, ipadx=8, ipady=3)
            ctk.CTkLabel(info_tags, text=f"الفرع: {branch_name}", font=("Segoe UI", 13, "bold"), text_color=TEXT_MUTED,
                         fg_color=BOX_BG, corner_radius=6).pack(side="left", padx=4, ipadx=8, ipady=3)

            summary_card = ctk.CTkFrame(self.liab_results_scroll, fg_color=CARD_BG, corner_radius=12, border_width=1,
                                        border_color="#E2E8F0")
            summary_card.pack(fill="x", padx=10, pady=5)

            card_title = ctk.CTkFrame(summary_card, fg_color="transparent")
            card_title.pack(fill="x", padx=15, pady=(15, 5))
            ctk.CTkLabel(card_title, text="💰 تفاصيل الالتزامات المالية", font=("Segoe UI", 16, "bold"),
                         text_color=FIB_GREEN).pack(side="right")

            ctk.CTkFrame(summary_card, fg_color="#F1F5F9", height=2).pack(fill="x", padx=15, pady=5)

            stats_row = ctk.CTkFrame(summary_card, fg_color="transparent")
            stats_row.pack(fill="x", padx=15, pady=15)

            def create_stat_box(parent, title, value, v_color=TEXT_DARK, bg_color=BOX_BG):
                box = ctk.CTkFrame(parent, fg_color=bg_color, corner_radius=8)
                box.pack(side="right", fill="x", expand=True, padx=6)
                ctk.CTkLabel(box, text=title, font=("Segoe UI", 13, "bold"), text_color=TEXT_MUTED).pack(
                    anchor="center", pady=(10, 2))
                ctk.CTkLabel(box, text=f"{value:,.2f}", font=("Segoe UI", 18, "bold"), text_color=v_color).pack(
                    anchor="center", pady=(0, 10))

            create_stat_box(stats_row, "رصيد المدين", abs(results['iamt19']), FIB_GREEN)
            create_stat_box(stats_row, "الكفالات", results['sponsor'], FIB_GOLD)
            create_stat_box(stats_row, "جزء غير مغطي من الضمانات", results['guarantees'], TEXT_DARK)
            create_stat_box(stats_row, "جزء غير مغطي من الاعتمادات", results['credits'], "#0369A1")
    def setup_client_history_inquiry_ui(self, parent):
        import pandas as pd
        import customtkinter as ctk
        from tkinter import messagebox
        import threading
        import logging

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
            header, text="الاستفسار عن سابقة تعاملات عميل 📊",
            font=("Segoe UI", 22, "bold"), text_color=CARD_BG
        ).pack(side="right", padx=30, pady=15)

        # =========================================
        # 🔍 منطقة البحث (الفرع ورقم الحساب)
        # =========================================
        search_frame = ctk.CTkFrame(main_container, fg_color=CARD_BG, corner_radius=15, border_width=1,
                                    border_color="#E2E8F0")
        search_frame.pack(fill="x", padx=20, pady=15)

        search_inner = ctk.CTkFrame(search_frame, fg_color="transparent")
        search_inner.pack(side="right", fill="y", padx=20, pady=15)

        # الأزرار
        btn_clear = ctk.CTkButton(search_inner, text="🧹 مسح", font=("Segoe UI", 14, "bold"), fg_color="#64748B",
                                  hover_color="#475569", width=80, height=40, corner_radius=8,
                                  command=lambda: clear_search())
        btn_clear.pack(side="left", padx=(5, 10))

        btn_search = ctk.CTkButton(search_inner, text="🔍 بحث", font=("Segoe UI", 15, "bold"), fg_color=FIB_GREEN,
                                   hover_color="#004426", width=100, height=40, corner_radius=8,
                                   command=lambda: execute_search())
        btn_search.pack(side="left", padx=5)

        # رقم الحساب / العميل
        self.ent_history_account_no = ctk.CTkEntry(search_inner, font=("Segoe UI", 15, "bold"), justify="center",
                                                   placeholder_text="رقم الحساب...", width=160, height=40,
                                                   border_color="#CBD5E1")
        self.ent_history_account_no.pack(side="left", padx=10)
        ctk.CTkLabel(search_inner, text="رقم الحساب:", font=("Segoe UI", 14, "bold"), text_color=TEXT_DARK).pack(
            side="left", padx=(10, 2))

        # الفرع
        if hasattr(self, '_create_premium_select'):
            self.cmb_history_branch_box, self.cmb_history_branch = self._create_premium_select(search_inner, values=[
                "جاري التحميل..."], default="جاري التحميل...", title="اختر الفرع")
            self.cmb_history_branch_box.pack(side="left", padx=10)
        else:
            self.cmb_history_branch = ctk.CTkComboBox(search_inner, font=("Segoe UI", 14, "bold"), justify="right",
                                                      width=200, height=40, border_color="#CBD5E1")
            self.cmb_history_branch.pack(side="left", padx=10)
        ctk.CTkLabel(search_inner, text="الفرع:", font=("Segoe UI", 14, "bold"), text_color=TEXT_DARK).pack(side="left",
                                                                                                            padx=(10,
                                                                                                                  2))

        # فريم نتائج البحث
        self.history_results_scroll = ctk.CTkScrollableFrame(main_container, fg_color="transparent")
        self.history_results_scroll.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        # =========================================
        # ⚙️ تحميل الفروع وإعداد الأحداث
        # =========================================
        def load_initial_branches():
            if hasattr(self, 'branch_mapping') and self.branch_mapping:
                branches = list(self.branch_mapping.keys())
                self.cmb_history_branch.configure(values=branches)
                self.cmb_history_branch.set(branches[0])
            else:
                self.after(500, load_initial_branches)

        self.after(500, load_initial_branches)
        self.ent_history_account_no.bind("<Return>", lambda event: execute_search())

        def clear_search():
            self.ent_history_account_no.delete(0, 'end')
            for widget in self.history_results_scroll.winfo_children():
                widget.destroy()

        # =========================================
        # 🛠️ دالة مساعدة لتحويل القيم المالية بأمان
        # =========================================
        def safe_float(val):
            try:
                if pd.isna(val) or str(val).strip() == '':
                    return 0.0
                return float(val)
            except (ValueError, TypeError):
                return 0.0

        # =========================================
        # 🚀 تنفيذ الاستعلام من قاعدة البيانات
        # =========================================
        def execute_search():
            branch_name = self.cmb_history_branch.get().strip()
            account_no = self.ent_history_account_no.get().strip()

            if not account_no:
                messagebox.showwarning("تنبيه", "يرجى إدخال رقم الحساب")
                return

            for widget in self.history_results_scroll.winfo_children():
                widget.destroy()

            ctk.CTkLabel(self.history_results_scroll, text="⚡ جاري جلب سابقة تعاملات العميل...",
                         font=("Segoe UI", 16, "bold"), text_color=FIB_GOLD).pack(pady=50)

            def fetch_data():
                try:
                    engine = getattr(self, '_get_db_connection', lambda: None)()
                    if not engine:
                        raise Exception("لا يوجد اتصال بقاعدة البيانات.")

                    # 1️⃣ جلب كود الفرع من tbl_branches بناءً على اسم الفرع المختار
                    branch_code_query = """
                                        SELECT branchcode
                                        FROM [dbo].[tbl_branches] \
                                        WITH (NOLOCK)
                                        WHERE branchname = ? \
                                        """
                    df_branch = pd.read_sql(branch_code_query, engine, params=(branch_name,))

                    if df_branch.empty:
                        if hasattr(self, 'branch_mapping') and branch_name in self.branch_mapping:
                            b_info = self.branch_mapping[branch_name]
                            branch_code = b_info[0] if isinstance(b_info, tuple) else b_info
                        else:
                            raise Exception(f"تعذر العثور على كود الفرع لـ ({branch_name})")
                    else:
                        branch_code = str(df_branch.iloc[0]['branchcode']).strip()

                    # 2️⃣ استعلام سابقة التعاملات على جدول tbl_localrecruitmentprocesses
                    history_query = """
                                    SELECT IAMT18, \
                                           IAMT19, \
                                           IAMT21
                                    FROM [dbo].[tbl_localrecruitmentprocesses] \
                                    WITH (NOLOCK)
                                    WHERE IBR = ? AND ICLNT = ? \
                                    """
                    df_history = pd.read_sql(history_query, engine, params=(branch_code, account_no))

                    self.after(0, lambda d=df_history, b=branch_name, a=account_no: update_results_ui(d, b, a))
                except Exception as e:
                    err_msg = str(e)
                    logging.error(f"Error fetching client history: {err_msg}")
                    self.after(0, lambda err=err_msg: update_results_ui(pd.DataFrame(), branch_name, account_no,
                                                                        error=err))

            threading.Thread(target=fetch_data, daemon=True).start()

        # =========================================
        # 📑 عرض نتائج الواجهة والحسابات
        # =========================================
        def update_results_ui(df, branch_name, account_no, error=None):
            for widget in self.history_results_scroll.winfo_children():
                widget.destroy()

            if error:
                ctk.CTkLabel(self.history_results_scroll, text=f"❌ حدث خطأ أثناء الاستعلام:\n{error}",
                             font=("Segoe UI", 14, "bold"), text_color="#EF4444").pack(pady=40)
                return

            if df.empty:
                ctk.CTkLabel(self.history_results_scroll, text="✔️ لا توجد سابقة تعاملات مطابقة للبيانات المدخلة",
                             font=("Segoe UI", 18, "bold"), text_color=TEXT_MUTED).pack(pady=60)
                return

            # =========================================
            # 🧮 العمليات الحسابية الشروطية
            # =========================================
            iamt18_sum = 0.0
            iamt21_sum = 0.0
            active_operations_count = 0  # 👈 عداد عمليات IAMT18 التي تحققت فيها الشروط

            for _, row in df.iterrows():
                iamt18_val = safe_float(row.get('IAMT18'))
                iamt19_val = safe_float(row.get('IAMT19'))
                iamt21_val = safe_float(row.get('IAMT21'))

                # الشرط: IAMT19 بالسالب (أقل من صفر)
                if iamt19_val < 0:
                    iamt18_sum += iamt18_val
                    active_operations_count += 1  # 👈 زيادة العداد بمقدار 1 لكل عملية مطابقة

                # إجمالي المتأخرات (مجموع IAMT21)
                iamt21_sum += iamt21_val

            total_sum = iamt18_sum

            # =========================================
            # 🎨 عرض الكروت الإحصائية للنتائج
            # =========================================
            header_card = ctk.CTkFrame(self.history_results_scroll, fg_color=CARD_BG, corner_radius=12, border_width=1,
                                       border_color="#CBD5E1")
            header_card.pack(fill="x", padx=10, pady=(5, 15))

            top_row = ctk.CTkFrame(header_card, fg_color="transparent")
            top_row.pack(fill="x", padx=20, pady=15)

            ctk.CTkLabel(top_row, text=f"👤 سابقة تعاملات الحساب: {account_no}", font=("Segoe UI", 18, "bold"),
                         text_color=FIB_GREEN).pack(side="right")
            ctk.CTkLabel(top_row, text=f"الفرع: {branch_name}", font=("Segoe UI", 13, "bold"), text_color=TEXT_MUTED,
                         fg_color=BOX_BG, corner_radius=6).pack(side="left", ipadx=10, ipady=4)

            # كارت الملخص المالي
            summary_card = ctk.CTkFrame(self.history_results_scroll, fg_color=CARD_BG, corner_radius=12, border_width=1,
                                        border_color="#E2E8F0")
            summary_card.pack(fill="x", padx=10, pady=5)

            card_title = ctk.CTkFrame(summary_card, fg_color="transparent")
            card_title.pack(fill="x", padx=15, pady=(15, 5))
            ctk.CTkLabel(card_title, text="💰 ملخص الحسابات والتعاملات", font=("Segoe UI", 16, "bold"),
                         text_color=FIB_GREEN).pack(side="right")

            ctk.CTkFrame(summary_card, fg_color="#F1F5F9", height=2).pack(fill="x", padx=15, pady=5)

            stats_row = ctk.CTkFrame(summary_card, fg_color="transparent")
            stats_row.pack(fill="x", padx=15, pady=15)

            def create_stat_box(parent, title, value, v_color=TEXT_DARK, bg_color=BOX_BG, is_int=False):
                box = ctk.CTkFrame(parent, fg_color=bg_color, corner_radius=8)
                box.pack(side="right", fill="x", expand=True, padx=6)
                ctk.CTkLabel(box, text=title, font=("Segoe UI", 13, "bold"), text_color=TEXT_MUTED).pack(
                    anchor="center", pady=(10, 2))

                # إذا كان عدد صحيح نعرضه كما هو، وإذا كان مبلغا ننسقه بفاصلة عشرية
                val_str = str(value) if is_int else f"{value:,.2f}"
                ctk.CTkLabel(box, text=val_str, font=("Segoe UI", 18, "bold"), text_color=v_color).pack(anchor="center",
                                                                                                        pady=(0, 10))

            # عرض الكروت الإحصائية الأربعة مرتبة
            create_stat_box(stats_row, "عدد العمليات القائمة", active_operations_count, FIB_GOLD, is_int=True)
            create_stat_box(stats_row, "إجمالي سابقة التعاملات (IAMT18)", iamt18_sum, FIB_GREEN)
            create_stat_box(stats_row, "إجمالي المتأخرات (IAMT21)", iamt21_sum, "#DC2626")
            create_stat_box(stats_row, "الإجمالي العام", total_sum, FIB_GOLD)
    def setup_alphabetical_contributors_inquiry_ui(self, parent):
        import pandas as pd
        import customtkinter as ctk
        from tkinter import messagebox
        import threading
        import logging
        import re

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
    def setup_creditworthiness_inquiry_ui(self, parent):
        import pandas as pd
        import customtkinter as ctk
        from tkinter import messagebox
        import threading
        import logging
        import re

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
            header, text="الاستفسار عن عملاء الجدارة الائتمانية 🛡️",
            font=("Segoe UI", 22, "bold"), text_color=CARD_BG
        ).pack(side="right", padx=30, pady=15)

        # =========================================
        # 🔍 منطقة البحث (الفرع، رقم العميل، رقم المركزي)
        # =========================================
        search_frame = ctk.CTkFrame(main_container, fg_color=CARD_BG, corner_radius=15, border_width=1,
                                    border_color="#E2E8F0")
        search_frame.pack(fill="x", padx=20, pady=15)

        search_inner = ctk.CTkFrame(search_frame, fg_color="transparent")
        search_inner.pack(side="right", fill="y", padx=20, pady=15)

        # الأزرار
        btn_clear = ctk.CTkButton(search_inner, text="🧹 مسح", font=("Segoe UI", 14, "bold"), fg_color="#64748B",
                                  hover_color="#475569", width=80, height=40, corner_radius=8,
                                  command=lambda: clear_search())
        btn_clear.pack(side="left", padx=(5, 10))

        btn_search = ctk.CTkButton(search_inner, text="🔍 بحث", font=("Segoe UI", 15, "bold"), fg_color=FIB_GREEN,
                                   hover_color="#004426", width=100, height=40, corner_radius=8,
                                   command=lambda: execute_search())
        btn_search.pack(side="left", padx=5)

        # رقم العميل بالمركزي
        self.ent_credit_cclntm = ctk.CTkEntry(search_inner, font=("Segoe UI", 15, "bold"), justify="center",
                                              placeholder_text="العميل بالمركزي...", width=140, height=40,
                                              border_color="#CBD5E1")
        self.ent_credit_cclntm.pack(side="left", padx=10)
        ctk.CTkLabel(search_inner, text="رقم المركزي:", font=("Segoe UI", 14, "bold"), text_color=TEXT_DARK).pack(
            side="left", padx=(10, 2))

        # رقم العميل
        self.ent_credit_cust_no = ctk.CTkEntry(search_inner, font=("Segoe UI", 15, "bold"), justify="center",
                                               placeholder_text="رقم العميل...", width=130, height=40,
                                               border_color="#CBD5E1")
        self.ent_credit_cust_no.pack(side="left", padx=10)
        ctk.CTkLabel(search_inner, text="رقم العميل:", font=("Segoe UI", 14, "bold"), text_color=TEXT_DARK).pack(
            side="left", padx=(10, 2))

        # الفرع
        if hasattr(self, '_create_premium_select'):
            self.cmb_credit_branch_box, self.cmb_credit_branch = self._create_premium_select(search_inner,
                                                                                             values=["جاري التحميل..."],
                                                                                             default="جاري التحميل...",
                                                                                             title="اختر الفرع")
            self.cmb_credit_branch_box.pack(side="left", padx=10)
        else:
            self.cmb_credit_branch = ctk.CTkComboBox(search_inner, font=("Segoe UI", 14, "bold"), justify="right",
                                                     width=200, height=40, border_color="#CBD5E1")
            self.cmb_credit_branch.pack(side="left", padx=10)
        ctk.CTkLabel(search_inner, text="الفرع:", font=("Segoe UI", 14, "bold"), text_color=TEXT_DARK).pack(side="left",
                                                                                                            padx=(10,
                                                                                                                  2))

        # فريم نتائج البحث
        self.credit_results_scroll = ctk.CTkScrollableFrame(main_container, fg_color="transparent")
        self.credit_results_scroll.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        # =========================================
        # ⚙️ تحميل الفروع وإعداد الأحداث
        # =========================================
        def load_initial_data():
            if hasattr(self, 'branch_mapping') and self.branch_mapping:
                branches = list(self.branch_mapping.keys())
                self.cmb_credit_branch.configure(values=branches)
                self.cmb_credit_branch.set(branches[0])
            else:
                self.after(500, load_initial_data)

        self.after(500, load_initial_data)
        self.ent_credit_cust_no.bind("<Return>", lambda event: execute_search())
        self.ent_credit_cclntm.bind("<Return>", lambda event: execute_search())

        def clear_search():
            self.ent_credit_cust_no.delete(0, 'end')
            self.ent_credit_cclntm.delete(0, 'end')
            for widget in self.credit_results_scroll.winfo_children():
                widget.destroy()

        # =========================================
        # 🛠️ معالجة الاسم العربي الملتصق
        # =========================================
        def format_arabic_name(raw_name):
            if not raw_name or pd.isna(raw_name):
                return "غير مسجل"
            text = str(raw_name).strip()

            # إضافة مسافات إضافية بين مقاطع الكلمات الملتصقة في الأنظمة القديمة
            prefixes = ['عبد', 'ابن', 'أبو', 'بن', 'الله']
            for p in prefixes:
                text = re.sub(rf'({p})([أ-ي])', r'\1 \2', text)

            # إزالة أي مسافات مضاعفة متكررة
            return " ".join(text.split())

        # =========================================
        # 🚀 تنفيذ الاستعلام من قاعدة البيانات
        # =========================================
        def execute_search():
            branch_name = self.cmb_credit_branch.get().strip()
            cust_no = self.ent_credit_cust_no.get().strip()
            cclntm_no = self.ent_credit_cclntm.get().strip()

            if not cust_no and not cclntm_no:
                messagebox.showwarning("تنبيه", "يرجى إدخال رقم العميل أو رقم العميل بالمركزي")
                return

            if not hasattr(self, 'branch_mapping') or branch_name not in self.branch_mapping:
                messagebox.showerror("خطأ", "برجاء اختيار فرع صحيح")
                return

            branch_info = self.branch_mapping[branch_name]
            branch_code = branch_info[0] if isinstance(branch_info, tuple) else branch_info

            for widget in self.credit_results_scroll.winfo_children():
                widget.destroy()

            ctk.CTkLabel(self.credit_results_scroll, text="⚡ جاري جلب بيانات الجدارة الائتمانية...",
                         font=("Segoe UI", 16, "bold"), text_color=FIB_GOLD).pack(pady=50)

            def fetch_data():
                try:
                    engine = getattr(self, '_get_db_connection', lambda: None)()
                    if not engine:
                        raise Exception("لا يوجد اتصال بقاعدة البيانات.")

                    cust_str = cust_no.strip()
                    try:
                        cust_int_str = str(int(cust_str)) if cust_str else ""
                    except Exception:
                        cust_int_str = cust_str

                    # بناء كويري مطابقة العميل مع الربط بجدول الأكواد TBL_creditworthinessCodes
                    credit_query = f"""
                        SELECT 
                            L.INAME, L.ICLNTM, L.ICOD, 
                            C.INAMEC,
                            L.IAMT, L.IDAT1, L.IAMT1, 
                            L.IAMTD, L.IDAT2, L.IAMT2, 
                            L.IAMTY, L.IDAT3, L.IAMT3, 
                            L.IEE
                        FROM [dbo].[TBL_creditworthinessLimits] L WITH (NOLOCK)
                        LEFT JOIN [dbo].[TBL_creditworthinessCodes] C WITH (NOLOCK) ON L.ICOD = C.ICOD
                        WHERE L.IBR = '{branch_code}'
                          AND (
                               ('{cust_str}' <> '' AND (L.ICLNT = '{cust_str}' OR L.ICLNT = '{cust_int_str}'))
                               OR
                               ('{cclntm_no}' <> '' AND L.ICLNTM = '{cclntm_no}')
                          )
                    """
                    df = pd.read_sql(credit_query, engine)

                    self.after(0, lambda: update_results_ui(df, cust_no, cclntm_no, branch_name))
                except Exception as e:
                    logging.error(f"Error fetching creditworthiness data: {e}")
                    self.after(0,
                               lambda: update_results_ui(pd.DataFrame(), cust_no, cclntm_no, branch_name, error=str(e)))

            threading.Thread(target=fetch_data, daemon=True).start()

        # =========================================
        # 📑 عرض الواجهة
        # =========================================
        def update_results_ui(df, cust_no, cclntm_no, branch_name, error=None):
            for widget in self.credit_results_scroll.winfo_children():
                widget.destroy()

            if error:
                ctk.CTkLabel(self.credit_results_scroll, text=f"❌ حدث خطأ أثناء الاستعلام:\n{error}",
                             font=("Segoe UI", 14, "bold"), text_color="#EF4444").pack(pady=40)
                return

            if df.empty:
                ctk.CTkLabel(self.credit_results_scroll, text="✔️ لا توجد بيانات جدارة ائتمانية مطابقة",
                             font=("Segoe UI", 18, "bold"), text_color=TEXT_MUTED).pack(pady=60)
                return

            def format_money(val):
                try:
                    return "{:,.2f}".format(float(val))
                except:
                    return "0.00"

            def format_date(val):
                if pd.isna(val): return "—"
                try:
                    return pd.to_datetime(val).strftime('%Y-%m-%d')
                except:
                    return str(val)

            def create_stat_box(parent, title, value, v_color=TEXT_DARK, bg_color=BOX_BG):
                box = ctk.CTkFrame(parent, fg_color=bg_color, corner_radius=8)
                box.pack(side="right", fill="x", expand=True, padx=4)
                ctk.CTkLabel(box, text=title, font=("Segoe UI", 12, "bold"), text_color=TEXT_MUTED).pack(
                    anchor="center", pady=(8, 2))
                ctk.CTkLabel(box, text=str(value), font=("Segoe UI", 15, "bold"), text_color=v_color).pack(
                    anchor="center", pady=(0, 8))

            row = df.iloc[0]

            # 1. المعالجة وضبط البيانات الرئيسية
            formatted_name = format_arabic_name(row.get('INAME'))
            risk_level_name = row.get('INAMEC') if pd.notna(row.get('INAMEC')) else f"كود: {row.get('ICOD', '—')}"

            # 👤 كارت معلومات العميل
            header_card = ctk.CTkFrame(self.credit_results_scroll, fg_color=CARD_BG, corner_radius=12, border_width=1,
                                       border_color="#CBD5E1")
            header_card.pack(fill="x", padx=10, pady=(5, 15))

            top_row = ctk.CTkFrame(header_card, fg_color="transparent")
            top_row.pack(fill="x", padx=20, pady=15)

            # الجهة اليمنى: اسم العميل
            ctk.CTkLabel(top_row, text=f"👤 {formatted_name}", font=("Segoe UI", 20, "bold"), text_color=FIB_GREEN).pack(
                side="right")

            # الجهة اليسرى: الملاحظات الأساسية
            info_tags = ctk.CTkFrame(top_row, fg_color="transparent")
            info_tags.pack(side="left")

            ctk.CTkLabel(info_tags, text=f"الفرع: {branch_name}", font=("Segoe UI", 13, "bold"), text_color=TEXT_MUTED,
                         fg_color=BOX_BG, corner_radius=6).pack(side="left", padx=4, ipadx=8, ipady=3)
            ctk.CTkLabel(info_tags, text=f"المركزى: {row.get('ICLNTM', '—')}", font=("Segoe UI", 13, "bold"),
                         text_color=FIB_GOLD, fg_color=BOX_BG, corner_radius=6).pack(side="left", padx=4, ipadx=8,
                                                                                     ipady=3)
            ctk.CTkLabel(info_tags, text=f"كود الإلغاء (IEE): {row.get('IEE', '—')}", font=("Segoe UI", 13, "bold"),
                         text_color="#DC2626", fg_color="#FEE2E2", corner_radius=6).pack(side="left", padx=4, ipadx=8,
                                                                                         ipady=3)

            # شريط مستوى المخاطر
            risk_bar = ctk.CTkFrame(header_card, fg_color=BOX_BG, corner_radius=8)
            risk_bar.pack(fill="x", padx=20, pady=(0, 15))
            ctk.CTkLabel(risk_bar, text=f"مستوى المخاطر الائتمانية:  {risk_level_name}", font=("Segoe UI", 15, "bold"),
                         text_color="#B45309").pack(pady=8)

            # 📊 كارت مخصصات وتجنيب الجدارة (المراحل الثلاث)
            data_card = ctk.CTkFrame(self.credit_results_scroll, fg_color=CARD_BG, corner_radius=12, border_width=1,
                                     border_color="#E2E8F0")
            data_card.pack(fill="x", padx=10, pady=5)

            card_title = ctk.CTkFrame(data_card, fg_color="transparent")
            card_title.pack(fill="x", padx=15, pady=(15, 5))
            ctk.CTkLabel(card_title, text="💰 تفاصيل المبالغ المجنبة ومخصصات خسائر الاضمحلال",
                         font=("Segoe UI", 16, "bold"), text_color=FIB_GREEN).pack(side="right")

            ctk.CTkFrame(data_card, fg_color="#F1F5F9", height=2).pack(fill="x", padx=15, pady=5)

            # المرحلة الأولى
            stage1_frame = ctk.CTkFrame(data_card, fg_color="transparent")
            stage1_frame.pack(fill="x", padx=15, pady=8)
            create_stat_box(stage1_frame, "مخصص خسائر الاضمحلال (1)", format_money(row.get('IAMT1')), "#DC2626")
            create_stat_box(stage1_frame, "تاريخ التجنيب (1)", format_date(row.get('IDAT1')), TEXT_DARK)
            create_stat_box(stage1_frame, "المبلغ المجنب (IAMT)", format_money(row.get('IAMT')), FIB_GREEN)

            # المرحلة الثانية
            stage2_frame = ctk.CTkFrame(data_card, fg_color="transparent")
            stage2_frame.pack(fill="x", padx=15, pady=8)
            create_stat_box(stage2_frame, "مخصص خسائر الاضمحلال (2)", format_money(row.get('IAMT2')), "#DC2626")
            create_stat_box(stage2_frame, "تاريخ التجنيب (2)", format_date(row.get('IDAT2')), TEXT_DARK)
            create_stat_box(stage2_frame, "المبلغ المجنب (IAMTD)", format_money(row.get('IAMTD')), FIB_GOLD)

            # المرحلة الثالثة
            stage3_frame = ctk.CTkFrame(data_card, fg_color="transparent")
            stage3_frame.pack(fill="x", padx=15, pady=(8, 15))
            create_stat_box(stage3_frame, "مخصص خسائر الاضمحلال (3)", format_money(row.get('IAMT3')), "#DC2626")
            create_stat_box(stage3_frame, "تاريخ التجنيب (3)", format_date(row.get('IDAT3')), TEXT_DARK)
            create_stat_box(stage3_frame, "المبلغ المجنب (IAMTY)", format_money(row.get('IAMTY')), TEXT_DARK)
    def setup_guarantees_inquiry_ui(self, parent):
        import pandas as pd
        import customtkinter as ctk
        from tkinter import messagebox
        import threading
        import logging
        import datetime

        # =========================================
        # 🎨 الألوان والتنسيقات
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
            header, text="الاستفسار عن خطابات الضمان لعميل 📜",
            font=("Segoe UI", 22, "bold"), text_color=CARD_BG
        ).pack(side="right", padx=30, pady=15)

        # =========================================
        # 🔍 منطقة البحث (الفرع، العميل، السنة، العملة)
        # =========================================
        search_frame = ctk.CTkFrame(main_container, fg_color=CARD_BG, corner_radius=15, border_width=1,
                                    border_color="#E2E8F0")
        search_frame.pack(fill="x", padx=20, pady=15)

        search_inner = ctk.CTkFrame(search_frame, fg_color="transparent")
        search_inner.pack(side="right", fill="y", padx=20, pady=15)

        # أزرار البحث والمسح
        btn_clear = ctk.CTkButton(search_inner, text="🧹 مسح", font=("Segoe UI", 14, "bold"), fg_color="#64748B",
                                  hover_color="#475569", width=80, height=40, corner_radius=8,
                                  command=lambda: clear_search())
        btn_clear.pack(side="left", padx=(5, 10))

        btn_search = ctk.CTkButton(search_inner, text="🔍 بحث", font=("Segoe UI", 15, "bold"), fg_color=FIB_GREEN,
                                   hover_color="#004426", width=100, height=40, corner_radius=8,
                                   command=lambda: execute_search())
        btn_search.pack(side="left", padx=5)

        # العملة
        self.cmb_lg_currency = ctk.CTkComboBox(search_inner, font=("Segoe UI", 14, "bold"), justify="center", width=120,
                                               height=40, border_color="#CBD5E1")
        self.cmb_lg_currency.pack(side="left", padx=10)
        ctk.CTkLabel(search_inner, text="العملة:", font=("Segoe UI", 14, "bold"), text_color=TEXT_DARK).pack(
            side="left", padx=(10, 2))

        # سنة الإصدار
        current_year = datetime.datetime.now().year
        years_list = [str(y) for y in range(current_year, 1999, -1)]
        self.cmb_lg_year = ctk.CTkComboBox(search_inner, values=years_list, font=("Segoe UI", 14, "bold"),
                                           justify="center", width=100, height=40, border_color="#CBD5E1")
        self.cmb_lg_year.pack(side="left", padx=10)
        ctk.CTkLabel(search_inner, text="حتى سنة:", font=("Segoe UI", 14, "bold"), text_color=TEXT_DARK).pack(
            side="left", padx=(10, 2))

        # رقم العميل
        self.ent_lg_cust_no = ctk.CTkEntry(search_inner, font=("Segoe UI", 15, "bold"), justify="center",
                                           placeholder_text="رقم العميل...", width=140, height=40,
                                           border_color="#CBD5E1")
        self.ent_lg_cust_no.pack(side="left", padx=10)
        ctk.CTkLabel(search_inner, text="رقم العميل:", font=("Segoe UI", 14, "bold"), text_color=TEXT_DARK).pack(
            side="left", padx=(10, 2))

        # الفرع
        if hasattr(self, '_create_premium_select'):
            self.cmb_lg_branch_box, self.cmb_lg_branch = self._create_premium_select(search_inner,
                                                                                     values=["جاري التحميل..."],
                                                                                     default="جاري التحميل...",
                                                                                     title="اختر الفرع")
            self.cmb_lg_branch_box.pack(side="left", padx=10)
        else:
            self.cmb_lg_branch = ctk.CTkComboBox(search_inner, font=("Segoe UI", 14, "bold"), justify="right",
                                                 width=200, height=40, border_color="#CBD5E1")
            self.cmb_lg_branch.pack(side="left", padx=10)
        ctk.CTkLabel(search_inner, text="الفرع:", font=("Segoe UI", 14, "bold"), text_color=TEXT_DARK).pack(side="left",
                                                                                                            padx=(10,
                                                                                                                  2))

        # الفريم الخاص بالنتائج
        self.lg_results_scroll = ctk.CTkScrollableFrame(main_container, fg_color="transparent")
        self.lg_results_scroll.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        # =========================================
        # ⚙️ تحميل الداتا الأولية (الفروع والعملات)
        # =========================================
        def load_initial_data():
            # الفروع
            if hasattr(self, 'branch_mapping') and self.branch_mapping:
                branches = list(self.branch_mapping.keys())
                self.cmb_lg_branch.configure(values=branches)
                self.cmb_lg_branch.set(branches[0])

            # العملات
            if hasattr(self, 'currency_map_name_to_code') and self.currency_map_name_to_code:
                currencies = list(self.currency_map_name_to_code.keys())
                self.cmb_lg_currency.configure(values=currencies)
                if currencies: self.cmb_lg_currency.set(currencies[0])
            else:
                self.cmb_lg_currency.configure(values=["الجنيه المصري", "دولار أمريكي", "يورو"])

        self.after(500, load_initial_data)
        self.ent_lg_cust_no.bind("<Return>", lambda event: execute_search())

        def clear_search():
            self.ent_lg_cust_no.delete(0, 'end')
            for widget in self.lg_results_scroll.winfo_children():
                widget.destroy()

        # =========================================
        # 🚀 تنفيذ البحث وتجميع الداتا
        # =========================================
        def execute_search():
            branch_name = self.cmb_lg_branch.get().strip()
            cust_no = self.ent_lg_cust_no.get().strip()
            selected_year = self.cmb_lg_year.get().strip()
            currency_name = self.cmb_lg_currency.get().strip()

            if not cust_no:
                messagebox.showwarning("تنبيه", "يرجى إدخال رقم العميل")
                return

            if not hasattr(self, 'branch_mapping') or branch_name not in self.branch_mapping:
                messagebox.showerror("خطأ", "برجاء اختيار فرع صحيح")
                return

            branch_info = self.branch_mapping[branch_name]
            branch_code = branch_info[0] if isinstance(branch_info, tuple) else branch_info

            currency_code = getattr(self, 'currency_map_name_to_code', {}).get(currency_name,
                                                                               "1")  # افتراضي 1 لو غير موجود

            for widget in self.lg_results_scroll.winfo_children():
                widget.destroy()

            ctk.CTkLabel(self.lg_results_scroll, text="⚡ جاري البحث عن خطابات الضمان...", font=("Segoe UI", 16, "bold"),
                         text_color=FIB_GOLD).pack(pady=50)

            def fetch_data():
                try:
                    engine = getattr(self, '_get_db_connection', lambda: None)()
                    if not engine:
                        raise Exception("لا يوجد اتصال بقاعدة البيانات.")

                    cust_str = cust_no.strip()
                    try:
                        cust_int_str = str(int(cust_str))
                    except Exception:
                        cust_int_str = cust_str

                    # 1. جلب اسم الجدول للفرع
                    branch_query = f"SELECT TableName FROM [dbo].[TBL_Branches] WITH (NOLOCK) WHERE BranchCode = '{branch_code}'"
                    branch_df = pd.read_sql(branch_query, engine)

                    if not branch_df.empty and pd.notna(branch_df.iloc[0]['TableName']):
                        target_table = str(branch_df.iloc[0]['TableName']).strip()
                    else:
                        raise Exception("لم يتم العثور على جدول البيانات المربوط بهذا الفرع.")

                    # 2. جلب اسم العميل BNAME من جدول الفرع
                    name_query = f"SELECT BNAME FROM [dbo].[{target_table}] WITH (NOLOCK) WHERE BCLNT = '{cust_str}' OR BCLNT = '{cust_int_str}'"
                    name_df = pd.read_sql(name_query, engine)
                    client_name = str(name_df.iloc[0]['BNAME']).strip() if not name_df.empty else "غير مسجل"

                    # 3. الاستعلام عن خطابات الضمان
                    # افترضت أن كود العملة موجود في عمود LGCUR، يمكنك تعديله إذا كان مختلفاً
                    lg_query = f"""
                        SELECT LGNO, LGTYPE, LGVAL, LGCVRP, LGCVAL, LGCINV, LGIDAT, LGDUDT, LGBNAM
                        FROM [dbo].[TBL_gurantees] WITH (NOLOCK)
                        WHERE LGBR = '{branch_code}' 
                          AND (LGCNO = '{cust_str}' OR LGCNO = '{cust_int_str}')
                          AND LGCUR = '{currency_code}'
                          AND LGIDAT <= '{selected_year}-12-31'
                    """
                    df = pd.read_sql(lg_query, engine)

                    self.after(0, lambda: update_results_ui(df, client_name, cust_no, branch_name, currency_name))
                except Exception as e:
                    logging.error(f"Error fetching guarantees: {e}")
                    self.after(0, lambda: update_results_ui(pd.DataFrame(), "", cust_no, branch_name, currency_name,
                                                            error=str(e)))

            threading.Thread(target=fetch_data, daemon=True).start()

        # =========================================
        # 📑 عرض النتائج (الإجماليات ثم التفاصيل)
        # =========================================
        def update_results_ui(df, client_name, cust_no, branch_name, currency_name, error=None):
            for widget in self.lg_results_scroll.winfo_children():
                widget.destroy()

            if error:
                ctk.CTkLabel(self.lg_results_scroll, text=f"❌ حدث خطأ:\n{error}", font=("Segoe UI", 14, "bold"),
                             text_color="#EF4444").pack(pady=40)
                return

            if df.empty:
                ctk.CTkLabel(self.lg_results_scroll, text="✔️ لا توجد خطابات ضمان مطابقة للبحث",
                             font=("Segoe UI", 18, "bold"), text_color=TEXT_MUTED).pack(pady=60)
                return

            def format_money(val):
                try:
                    return "{:,.2f}".format(float(val))
                except:
                    return "0.00"

            def format_date(val):
                if pd.isna(val): return "—"
                try:
                    return pd.to_datetime(val).strftime('%Y-%m-%d')
                except:
                    return str(val)

            # حساب الإجماليات
            total_lgval = df['LGVAL'].apply(pd.to_numeric, errors='coerce').sum()
            total_lgcinv = df['LGCINV'].apply(pd.to_numeric, errors='coerce').sum()

            # =========================================
            # 💳 كارت الإجماليات (Top Summary Card)
            # =========================================
            summary_card = ctk.CTkFrame(self.lg_results_scroll, fg_color=FIB_GREEN, corner_radius=12)
            summary_card.pack(fill="x", padx=10, pady=(5, 20))

            summary_inner = ctk.CTkFrame(summary_card, fg_color="transparent")
            summary_inner.pack(fill="x", padx=20, pady=15)

            # اسم العميل وبياناته
            client_info = ctk.CTkFrame(summary_inner, fg_color="transparent")
            client_info.pack(side="right")
            ctk.CTkLabel(client_info, text=f"👤 {client_name}", font=("Segoe UI", 20, "bold"), text_color=CARD_BG).pack(
                anchor="e")
            ctk.CTkLabel(client_info, text=f"الفرع: {branch_name} | رقم العميل: {cust_no} | العملة: {currency_name}",
                         font=("Segoe UI", 14), text_color="#E2E8F0").pack(anchor="e")

            # بلوكات الإجماليات
            totals_frame = ctk.CTkFrame(summary_inner, fg_color="transparent")
            totals_frame.pack(side="left")

            tot_box1 = ctk.CTkFrame(totals_frame, fg_color=CARD_BG, corner_radius=8)
            tot_box1.pack(side="left", padx=10)
            ctk.CTkLabel(tot_box1, text="إجمالي قيم خطابات الضمان", font=("Segoe UI", 12, "bold"),
                         text_color=TEXT_MUTED).pack(padx=15, pady=(8, 0))
            ctk.CTkLabel(tot_box1, text=f"{format_money(total_lgval)}", font=("Segoe UI", 18, "bold"),
                         text_color=FIB_GREEN).pack(padx=15, pady=(0, 8))

            tot_box2 = ctk.CTkFrame(totals_frame, fg_color=CARD_BG, corner_radius=8)
            tot_box2.pack(side="left", padx=10)
            ctk.CTkLabel(tot_box2, text="إجمالي ضمان الاستثمار", font=("Segoe UI", 12, "bold"),
                         text_color=TEXT_MUTED).pack(padx=15, pady=(8, 0))
            ctk.CTkLabel(tot_box2, text=f"{format_money(total_lgcinv)}", font=("Segoe UI", 18, "bold"),
                         text_color=FIB_GOLD).pack(padx=15, pady=(0, 8))

            # =========================================
            # 📄 كروت خطابات الضمان (Records)
            # =========================================
            for idx, row in df.iterrows():
                record_card = ctk.CTkFrame(self.lg_results_scroll, fg_color=CARD_BG, corner_radius=10, border_width=1,
                                           border_color="#CBD5E1")
                record_card.pack(fill="x", padx=10, pady=5)

                # رأس الكارت (رقم الخطاب ونوعه والمستفيد)
                rec_header = ctk.CTkFrame(record_card, fg_color="transparent")
                rec_header.pack(fill="x", padx=15, pady=(10, 5))

                ctk.CTkLabel(rec_header, text=f"خطاب رقم: {row.get('LGNO', '—')}", font=("Segoe UI", 16, "bold"),
                             text_color=FIB_GREEN).pack(side="right")
                ctk.CTkLabel(rec_header, text=f"نوع الخطاب: {row.get('LGTYPE', '—')}", font=("Segoe UI", 14, "bold"),
                             text_color=TEXT_DARK, fg_color=BOX_BG, corner_radius=6).pack(side="right", padx=15,
                                                                                          ipadx=8, ipady=2)
                ctk.CTkLabel(rec_header, text=f"الجهة المستفيدة: {row.get('LGBNAM', '—')}",
                             font=("Segoe UI", 14, "bold"), text_color=FIB_GOLD).pack(side="left")

                ctk.CTkFrame(record_card, fg_color="#F1F5F9", height=2).pack(fill="x", padx=15, pady=5)

                # بيانات الكارت
                details_frame = ctk.CTkFrame(record_card, fg_color="transparent")
                details_frame.pack(fill="x", padx=10, pady=(5, 10))

                def create_detail_box(parent, title, value, v_color=TEXT_DARK):
                    box = ctk.CTkFrame(parent, fg_color=BOX_BG, corner_radius=6)
                    box.pack(side="right", fill="x", expand=True, padx=4)
                    ctk.CTkLabel(box, text=title, font=("Segoe UI", 12, "bold"), text_color=TEXT_MUTED).pack(
                        pady=(5, 0))
                    ctk.CTkLabel(box, text=str(value), font=("Segoe UI", 14, "bold"), text_color=v_color).pack(
                        pady=(0, 5))

                # الصف الأول
                row1 = ctk.CTkFrame(details_frame, fg_color="transparent")
                row1.pack(fill="x", pady=2)
                create_detail_box(row1, "قيمة خطاب الضمان (LGVAL)", format_money(row.get('LGVAL')), FIB_GREEN)
                create_detail_box(row1, "قيمة الغطاء (LGCVAL)", format_money(row.get('LGCVAL')), TEXT_DARK)
                create_detail_box(row1, "قيمة ضمان استثمار (LGCINV)", format_money(row.get('LGCINV')), FIB_GOLD)

                # الصف الثاني
                row2 = ctk.CTkFrame(details_frame, fg_color="transparent")
                row2.pack(fill="x", pady=2)
                create_detail_box(row2, "تاريخ الإصدار (LGIDAT)", format_date(row.get('LGIDAT')), TEXT_DARK)
                create_detail_box(row2, "تاريخ انتهاء الصلاحية (LGDUDT)", format_date(row.get('LGDUDT')),
                                  "#DC2626")  # أحمر للتنبيه
                create_detail_box(row2, "كود تحصيل الغطاء (LGCVRP)", row.get('LGCVRP', '—'), TEXT_MUTED)
    def setup_defaulting_client_ui(self, parent):
        import pandas as pd
        import customtkinter as ctk
        from tkinter import messagebox
        import threading
        import logging

        # =========================================
        # 🎨 الألوان والتنسيقات (نفس الثيم المعتمد)
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
            header, text="الاستفسار عن عميل متعثر ⚠️",
            font=("Segoe UI", 22, "bold"), text_color=CARD_BG
        ).pack(side="right", padx=30, pady=15)

        # =========================================
        # 🔍 منطقة البحث
        # =========================================
        search_frame = ctk.CTkFrame(main_container, fg_color=CARD_BG, corner_radius=15, border_width=1,
                                    border_color="#E2E8F0")
        search_frame.pack(fill="x", padx=20, pady=15)

        search_inner = ctk.CTkFrame(search_frame, fg_color="transparent")
        search_inner.pack(side="right", fill="y", padx=20, pady=15)

        btn_clear = ctk.CTkButton(search_inner, text="🧹 مسح", font=("Segoe UI", 14, "bold"), fg_color="#64748B",
                                  hover_color="#475569", width=90, height=40, corner_radius=8,
                                  command=lambda: clear_search())
        btn_clear.pack(side="left", padx=(5, 10))

        btn_search = ctk.CTkButton(search_inner, text="🔍 بحث", font=("Segoe UI", 15, "bold"), fg_color=FIB_GREEN,
                                   hover_color="#004426", width=110, height=40, corner_radius=8,
                                   command=lambda: execute_search())
        btn_search.pack(side="left", padx=5)

        self.ent_defaulter_cust_no = ctk.CTkEntry(search_inner, font=("Segoe UI", 15, "bold"), justify="center",
                                                  placeholder_text="رقم العميل...", width=160, height=40,
                                                  border_color="#CBD5E1")
        self.ent_defaulter_cust_no.pack(side="left", padx=10)
        ctk.CTkLabel(search_inner, text="رقم الحساب:", font=("Segoe UI", 14, "bold"), text_color=TEXT_DARK).pack(
            side="left", padx=(10, 2))

        if hasattr(self, '_create_premium_select'):
            self.cmb_defaulter_branch_box, self.cmb_defaulter_branch = self._create_premium_select(search_inner,
                                                                                                   values=[
                                                                                                       "جاري التحميل..."],
                                                                                                   default="جاري التحميل...",
                                                                                                   title="اختر الفرع")
            self.cmb_defaulter_branch_box.pack(side="left", padx=10)
        else:
            self.cmb_defaulter_branch = ctk.CTkComboBox(search_inner, font=("Segoe UI", 14, "bold"), justify="right",
                                                        width=220, height=40, border_color="#CBD5E1")
            self.cmb_defaulter_branch.pack(side="left", padx=10)
        ctk.CTkLabel(search_inner, text="الفرع:", font=("Segoe UI", 14, "bold"), text_color=TEXT_DARK).pack(side="left",
                                                                                                            padx=(10,
                                                                                                                  2))

        self.defaulter_results_scroll = ctk.CTkScrollableFrame(main_container, fg_color="transparent")
        self.defaulter_results_scroll.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        # =========================================
        # ⚙️ تحميل الداتا الأولية (الفروع والعملات)
        # =========================================
        def load_initial_data():
            if hasattr(self, 'branch_mapping') and self.branch_mapping:
                branches = list(self.branch_mapping.keys())
                self.cmb_defaulter_branch.configure(values=branches)
                self.cmb_defaulter_branch.set(branches[0])
            else:
                if hasattr(self, 'nuwairy_load_branches'):
                    self.nuwairy_load_branches()
                self.after(500, load_initial_data)

        load_initial_data()
        self.ent_defaulter_cust_no.bind("<Return>", lambda event: execute_search())

        def clear_search():
            self.ent_defaulter_cust_no.delete(0, 'end')
            for widget in self.defaulter_results_scroll.winfo_children():
                widget.destroy()

        # =========================================
        # 🚀 تنفيذ البحث
        # =========================================
        def execute_search():
            branch_name = self.cmb_defaulter_branch.get().strip()
            cust_no = self.ent_defaulter_cust_no.get().strip()

            if not cust_no:
                messagebox.showwarning("تنبيه", "يرجى إدخال رقم العميل")
                return

            if not hasattr(self, 'branch_mapping') or branch_name not in self.branch_mapping:
                messagebox.showerror("خطأ", "برجاء اختيار فرع صحيح")
                return

            branch_info = self.branch_mapping[branch_name]
            branch_code = branch_info[0] if isinstance(branch_info, tuple) else branch_info

            for widget in self.defaulter_results_scroll.winfo_children():
                widget.destroy()

            ctk.CTkLabel(self.defaulter_results_scroll, text="⚡ جاري البحث عن بيانات العميل المتعثر...",
                         font=("Segoe UI", 16, "bold"), text_color=FIB_GOLD).pack(pady=50)

            def fetch_data():
                try:
                    engine = getattr(self, '_get_db_connection', lambda: None)()
                    if not engine:
                        raise Exception("لا يوجد اتصال بقاعدة البيانات.")

                    cust_str = cust_no.strip()
                    try:
                        cust_int_str = str(int(cust_str))
                    except Exception:
                        cust_int_str = cust_str

                    # 1. جلب اسم الجدول الديناميكي من جدول الفروع
                    target_table = None
                    branch_query = f"SELECT TableName FROM [dbo].[TBL_Branches] WITH (NOLOCK) WHERE BranchCode = '{branch_code}'"
                    branch_df = pd.read_sql(branch_query, engine)

                    if not branch_df.empty and pd.notna(branch_df.iloc[0]['TableName']):
                        target_table = str(branch_df.iloc[0]['TableName']).strip()
                    else:
                        raise Exception("لم يتم العثور على جدول البيانات المربوط بهذا الفرع.")

                    # 2. الاستعلام من الجدول الهدف
                    client_query = f"""
                        SELECT Dcur, ddat, Dname, dcod, dtel1, dtel2, ddat1, ddat2, 
                               dno, damt1, damt2, damt3, damt4, damt5, damt6, damt7, damt8, damt9, damt10, dclntm
                        FROM [dbo].[tbl_defaulted_customers] WITH (NOLOCK)
                        WHERE DBR = '{branch_code}' 
                          AND (Dclnt = '{cust_str}' OR Dclnt = '{cust_int_str}')
                    """
                    df = pd.read_sql(client_query, engine)

                    self.after(0, lambda: update_results_ui(df, cust_no, branch_name))
                except Exception as e:
                    logging.error(f"Error fetching defaulter: {e}")
                    self.after(0, lambda: update_results_ui(pd.DataFrame(), cust_no, branch_name, error=str(e)))

            threading.Thread(target=fetch_data, daemon=True).start()

        # =========================================
        # 📑 عرض النتائج
        # =========================================
        def update_results_ui(df, cust_no, branch_name, error=None):
            for widget in self.defaulter_results_scroll.winfo_children():
                widget.destroy()

            if error:
                ctk.CTkLabel(self.defaulter_results_scroll, text=f"❌ حدث خطأ:\n{error}", font=("Segoe UI", 14, "bold"),
                             text_color="#EF4444").pack(pady=40)
                return

            if df.empty:
                ctk.CTkLabel(self.defaulter_results_scroll, text="✔️ لا توجد بيانات تعثر مطابقة لهذا العميل",
                             font=("Segoe UI", 18, "bold"), text_color=TEXT_MUTED).pack(pady=60)
                return

            # الدوال المساعدة للتنسيق
            def format_money(val):
                try:
                    return "{:,.2f}".format(float(val))
                except:
                    return "0.00"

            def format_date(val):
                if pd.isna(val): return "—"
                try:
                    return pd.to_datetime(val).strftime('%Y-%m-%d')
                except:
                    return str(val)

            def create_stat_box(parent_frame, title, value, v_color, bg_color=BOX_BG):
                box = ctk.CTkFrame(parent_frame, fg_color=bg_color, corner_radius=8)
                box.pack(side="right", fill="x", expand=True, padx=4)
                ctk.CTkLabel(box, text=title, font=("Segoe UI", 12, "bold"), text_color=TEXT_MUTED).pack(
                    anchor="center", pady=(8, 2))
                ctk.CTkLabel(box, text=str(value), font=("Segoe UI", 16, "bold"), text_color=v_color).pack(
                    anchor="center", pady=(0, 8))

            row = df.iloc[0]  # عرض أول نتيجة للعميل

            client_name = str(row.get('Dname', 'غير مسجل')).strip()
            currency_code = str(row.get('Dcur', '—')).strip()
            currency_name = getattr(self, 'currency_map_code_to_name', {}).get(currency_code, currency_code)

            # 1. كارت البيانات الأساسية
            main_card = ctk.CTkFrame(self.defaulter_results_scroll, fg_color=CARD_BG, corner_radius=12, border_width=1,
                                     border_color="#CBD5E1")
            main_card.pack(fill="x", padx=10, pady=(5, 15))

            top_info = ctk.CTkFrame(main_card, fg_color="transparent")
            top_info.pack(fill="x", padx=20, pady=12)

            ctk.CTkLabel(top_info, text=f"👤 {client_name}", font=("Segoe UI", 18, "bold"), text_color=FIB_GREEN).pack(
                side="right")
            ctk.CTkLabel(top_info, text=f"الفرع: {branch_name} | رقم العميل: {cust_no}", font=("Segoe UI", 13, "bold"),
                         text_color=TEXT_MUTED, fg_color=BOX_BG, corner_radius=6).pack(side="left", ipadx=10, ipady=3)

            ctk.CTkFrame(main_card, fg_color="#F1F5F9", height=2).pack(fill="x", padx=20, pady=5)

            # بيانات التواصل والهوية
            contact_frame = ctk.CTkFrame(main_card, fg_color="transparent")
            contact_frame.pack(fill="x", padx=15, pady=(5, 15))

            create_stat_box(contact_frame, "رقم بالمركزي", row.get('dclntm', '—'), TEXT_DARK)
            create_stat_box(contact_frame, "الشكل القانوني", row.get('dcod', '—'), TEXT_DARK)
            create_stat_box(contact_frame, "محمول", row.get('dtel2', '—'), FIB_GOLD)
            create_stat_box(contact_frame, "تليفون أرضي", row.get('dtel1', '—'), TEXT_MUTED)

            # التواريخ
            dates_frame = ctk.CTkFrame(main_card, fg_color="transparent")
            dates_frame.pack(fill="x", padx=15, pady=(0, 15))

            create_stat_box(dates_frame, "تاريخ الحركة", format_date(row.get('ddat')), TEXT_DARK)
            create_stat_box(dates_frame, "تاريخ التوقف", format_date(row.get('ddat2')), "#DC2626",
                            bg_color="#FEE2E2")  # لون أحمر خفيف
            create_stat_box(dates_frame, "تاريخ بدء التعامل", format_date(row.get('ddat1')), FIB_GREEN)
            create_stat_box(dates_frame, "عدد الجدولات", row.get('dno', '0'), TEXT_MUTED)

            # 2. كارت البيانات المالية (damt1 to damt10)
            fin_card = ctk.CTkFrame(self.defaulter_results_scroll, fg_color=CARD_BG, corner_radius=12, border_width=1,
                                    border_color="#E2E8F0")
            fin_card.pack(fill="x", padx=10, pady=8)

            fin_header = ctk.CTkFrame(fin_card, fg_color="transparent")
            fin_header.pack(fill="x", padx=15, pady=(15, 5))
            ctk.CTkLabel(fin_header, text=f"💰 الموقف المالي (العملة: {currency_name})", font=("Segoe UI", 16, "bold"),
                         text_color=FIB_GOLD).pack(side="right")

            ctk.CTkFrame(fin_card, fg_color="#F1F5F9", height=2).pack(fill="x", padx=15, pady=5)

            # الصف المالي الأول
            fin_row1 = ctk.CTkFrame(fin_card, fg_color="transparent")
            fin_row1.pack(fill="x", padx=15, pady=(5, 5))
            create_stat_box(fin_row1, "إجمالي الالتزامات (damt9)", format_money(row.get('damt9', 0)), "#DC2626")
            create_stat_box(fin_row1, "الرصيد المدين (damt7)", format_money(row.get('damt7', 0)), "#EA580C")
            create_stat_box(fin_row1, "إجمالي المسدد (damt4)", format_money(row.get('damt4', 0)), FIB_GREEN)
            create_stat_box(fin_row1, "إجمالي المتأخرات (damt5)", format_money(row.get('damt5', 0)), "#DC2626")

            # الصف المالي الثاني
            fin_row2 = ctk.CTkFrame(fin_card, fg_color="transparent")
            fin_row2.pack(fill="x", padx=15, pady=5)
            create_stat_box(fin_row2, "المخصص للمديونية (damt10)", format_money(row.get('damt10', 0)), TEXT_DARK)
            create_stat_box(fin_row2, "التزامات أخرى (damt8)", format_money(row.get('damt8', 0)), TEXT_MUTED)
            create_stat_box(fin_row2, "العوائد المعلقة (damt6)", format_money(row.get('damt6', 0)), TEXT_MUTED)
            create_stat_box(fin_row2, "التعويضات وعائد الجدولة (damt3)", format_money(row.get('damt3', 0)), FIB_GOLD)

            # الصف المالي الثالث
            fin_row3 = ctk.CTkFrame(fin_card, fg_color="transparent")
            fin_row3.pack(fill="x", padx=15, pady=(5, 15))
            create_stat_box(fin_row3, "عائد البنك للعمليات (damt2)", format_money(row.get('damt2', 0)), FIB_GREEN)
            create_stat_box(fin_row3, "تمويل البنك للعمليات (damt1)", format_money(row.get('damt1', 0)), TEXT_DARK)
    def setup_returned_cheques_ui(self, parent):
        import pandas as pd
        import customtkinter as ctk
        from tkinter import messagebox
        import threading
        import logging
        import re

        # =========================================
        # 🎨 الألوان والتنسيقات
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
            header, text="الاستفسار عن الشيكات المرتدة 📉",
            font=("Segoe UI", 22, "bold"), text_color=CARD_BG
        ).pack(side="right", padx=30, pady=15)

        # =========================================
        # 🔍 منطقة البحث
        # =========================================
        search_frame = ctk.CTkFrame(main_container, fg_color=CARD_BG, corner_radius=15, border_width=1,
                                    border_color="#E2E8F0")
        search_frame.pack(fill="x", padx=20, pady=15)

        search_inner = ctk.CTkFrame(search_frame, fg_color="transparent")
        search_inner.pack(side="right", fill="y", padx=20, pady=15)

        # أزرار البحث والمسح
        btn_clear = ctk.CTkButton(search_inner, text="🧹 مسح", font=("Segoe UI", 14, "bold"), fg_color="#64748B",
                                  hover_color="#475569", width=90, height=40, corner_radius=8,
                                  command=lambda: clear_search())
        btn_clear.pack(side="left", padx=(5, 10))

        btn_search = ctk.CTkButton(search_inner, text="🔍 بحث", font=("Segoe UI", 15, "bold"), fg_color=FIB_GREEN,
                                   hover_color="#004426", width=110, height=40, corner_radius=8,
                                   command=lambda: execute_search())
        btn_search.pack(side="left", padx=5)

        # إدخال رقم العميل
        self.ent_cheque_cust_no = ctk.CTkEntry(search_inner, font=("Segoe UI", 15, "bold"), justify="center",
                                               placeholder_text="رقم العميل...", width=160, height=40,
                                               border_color="#CBD5E1")
        self.ent_cheque_cust_no.pack(side="left", padx=10)
        ctk.CTkLabel(search_inner, text="رقم الحساب:", font=("Segoe UI", 14, "bold"), text_color=TEXT_DARK).pack(
            side="left", padx=(10, 2))

        # اختيار الفرع
        if hasattr(self, '_create_premium_select'):
            self.cmb_cheque_branch_box, self.cmb_cheque_branch = self._create_premium_select(search_inner,
                                                                                             values=["جاري التحميل..."],
                                                                                             default="جاري التحميل...",
                                                                                             title="اختر الفرع")
            self.cmb_cheque_branch_box.pack(side="left", padx=10)
        else:
            self.cmb_cheque_branch = ctk.CTkComboBox(search_inner, font=("Segoe UI", 14, "bold"), justify="right",
                                                     width=220, height=40, border_color="#CBD5E1")
            self.cmb_cheque_branch.pack(side="left", padx=10)
        ctk.CTkLabel(search_inner, text="الفرع:", font=("Segoe UI", 14, "bold"), text_color=TEXT_DARK).pack(side="left",
                                                                                                            padx=(10,
                                                                                                                  2))

        self.cheque_results_scroll = ctk.CTkScrollableFrame(main_container, fg_color="transparent")
        self.cheque_results_scroll.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        # =========================================
        # ⚙️ تحميل الداتا الأولية (الفروع والعملات)
        # =========================================
        self.currency_map_code_to_name = {}

        def load_initial_data():
            if hasattr(self, 'branch_mapping') and self.branch_mapping:
                branches = list(self.branch_mapping.keys())
                self.cmb_cheque_branch.configure(values=branches)
                self.cmb_cheque_branch.set(branches[0])
            else:
                if hasattr(self, 'nuwairy_load_branches'):
                    self.nuwairy_load_branches()
                self.after(500, load_initial_data)
                return

            def fetch_currencies():
                try:
                    engine = getattr(self, '_get_db_connection', lambda: None)()
                    if engine:
                        sql = "SELECT fcur, cnm FROM [dbo].[tbl_currency] WITH (NOLOCK) WHERE cnm IS NOT NULL"
                        df = pd.read_sql(sql, engine)
                        self.currency_map_code_to_name.clear()
                        for _, row in df.iterrows():
                            if pd.notna(row['fcur']) and pd.notna(row['cnm']):
                                k = str(row['fcur']).strip()
                                v = str(row['cnm']).strip()
                                self.currency_map_code_to_name[k] = v
                except Exception as e:
                    logging.error(f"Error loading currencies: {e}")

            threading.Thread(target=fetch_currencies, daemon=True).start()

        load_initial_data()
        self.ent_cheque_cust_no.bind("<Return>", lambda event: execute_search())

        def clear_search():
            self.ent_cheque_cust_no.delete(0, 'end')
            for widget in self.cheque_results_scroll.winfo_children():
                widget.destroy()

        def clean_arabic_name(name):
            if not isinstance(name, str) or not name.strip():
                return "—"
            cleaned = name.strip()
            cleaned = re.sub(r'[_+\-]', ' ', cleaned)
            cleaned = re.sub(r'\s+', ' ', cleaned)
            cleaned = re.sub(r'(\bابن|\bعبد|\bابو|\bأبو|\bام|\bأم)([أ-ي])', r'\1 \2', cleaned)
            cleaned = re.sub(r'([ةه])([أ-ي])', r'\1 \2', cleaned)
            cleaned = re.sub(r'([أ-ي])(للسياح|للتجار|للمقاول|للاستثمار|للخدمات|للتأمين|تراست|جروب|كومباني)', r'\1 \2',
                             cleaned)
            return re.sub(r'\s+', ' ', cleaned).strip()

        # =========================================
        # 🚀 تنفيذ البحث وتجميع البيانات
        # =========================================
        def execute_search():
            branch_name = self.cmb_cheque_branch.get().strip()
            cust_no = self.ent_cheque_cust_no.get().strip()

            if not cust_no:
                messagebox.showwarning("تنبيه", "يرجى إدخال رقم العميل")
                return

            if not hasattr(self, 'branch_mapping') or branch_name not in self.branch_mapping:
                messagebox.showerror("خطأ", "برجاء اختيار فرع صحيح")
                return

            branch_info = self.branch_mapping[branch_name]
            branch_code = branch_info[0] if isinstance(branch_info, tuple) else branch_info

            for widget in self.cheque_results_scroll.winfo_children():
                widget.destroy()

            ctk.CTkLabel(self.cheque_results_scroll, text="⚡ جاري سحب وتجميع بيانات الشيكات...",
                         font=("Segoe UI", 16, "bold"), text_color=FIB_GOLD).pack(pady=50)

            def fetch_data():
                try:
                    engine = getattr(self, '_get_db_connection', lambda: None)()
                    if not engine:
                        raise Exception("لا يوجد اتصال بقاعدة البيانات.")

                    cust_str = cust_no.strip()
                    try:
                        cust_int_str = str(int(cust_str))
                    except Exception:
                        cust_int_str = cust_str

                    # 1. جلب اسم العميل
                    target_table = None
                    try:
                        branch_query = f"SELECT TableName FROM [dbo].[TBL_Branches] WITH (NOLOCK) WHERE BranchCode = '{branch_code}'"
                        branch_df = pd.read_sql(branch_query, engine)
                        if not branch_df.empty and pd.notna(branch_df.iloc[0]['TableName']):
                            target_table = str(branch_df.iloc[0]['TableName']).strip()
                    except Exception:
                        pass

                    fetched_client_name = "غير مسجل"
                    if target_table:
                        try:
                            client_query = f"""
                                SELECT TOP 1 BNAME 
                                FROM [dbo].[{target_table}] WITH (NOLOCK) 
                                WHERE BCLNT = '{cust_str}' OR BCLNT = '{cust_int_str}'
                            """
                            client_df = pd.read_sql(client_query, engine)
                            if not client_df.empty and pd.notna(client_df.iloc[0].get('BNAME')):
                                fetched_client_name = clean_arabic_name(str(client_df.iloc[0].get('BNAME')).strip())
                        except Exception:
                            pass

                    # 2. الاستعلام عن الشيكات المرتدة (تم إلغاء التصفية بحالة الشيك)
                            # 2. الاستعلام عن الشيكات المرتدة (تم التعديل لاستخدام العمود المُفهرس)
                        sql_cheques = f"""
                                    SELECT ccur, camt1, camt9, camt7, camt8, cchno, cdat1, csub, cgl
                                    FROM [dbo].[tbl_refferedcheques] WITH (NOLOCK)
                                    WHERE cbr = '{branch_code}'
                                      AND (cclnt_indexed = '{cust_str}' OR cclnt_indexed = '{cust_int_str}')
                                """
                    df = pd.read_sql(sql_cheques, engine)

                    # 3. المعالجة والتجميع باستخدام Pandas
                    if not df.empty:
                        for col in ['camt1', 'camt9', 'camt7', 'camt8']:
                            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

                        df['CURR_NAME'] = df['ccur'].astype(str).str.strip().map(self.currency_map_code_to_name).fillna(
                            df['ccur'].astype(str))

                        summary_df = df.groupby('CURR_NAME').agg(
                            check_count=('camt1', 'count'),
                            total_camt1=('camt1', 'sum'),
                            total_camt9=('camt9', 'sum'),
                            total_camt7=('camt7', 'sum'),
                            total_camt8=('camt8', 'sum')
                        ).reset_index()
                    else:
                        summary_df = pd.DataFrame()

                    self.after(0, lambda: update_results_ui(df, summary_df, fetched_client_name, cust_no, branch_name))
                except Exception as e:
                    logging.error(f"Error fetching cheques: {e}")
                    self.after(0, lambda: update_results_ui(pd.DataFrame(), pd.DataFrame(), "غير مسجل", cust_no,
                                                            branch_name, error=str(e)))

            threading.Thread(target=fetch_data, daemon=True).start()

        # =========================================
        # 📑 عرض النتائج والتجميعات
        # =========================================
        def update_results_ui(df, summary_df, client_name, cust_no, branch_name, error=None):
            for widget in self.cheque_results_scroll.winfo_children():
                widget.destroy()

            if error:
                ctk.CTkLabel(self.cheque_results_scroll, text=f"❌ حدث خطأ:\n{error}", font=("Segoe UI", 14, "bold"),
                             text_color="#EF4444").pack(pady=40)
                return

            if summary_df.empty or df.empty:
                ctk.CTkLabel(self.cheque_results_scroll, text="✔️ لا توجد شيكات مرتدة مطابقة لبحثك",
                             font=("Segoe UI", 18, "bold"), text_color=TEXT_MUTED).pack(pady=60)
                return

            # --- 1. كارت بيانات العميل الرئيسي ---
            client_card = ctk.CTkFrame(self.cheque_results_scroll, fg_color=CARD_BG, corner_radius=12, border_width=1,
                                       border_color="#CBD5E1")
            client_card.pack(fill="x", padx=10, pady=(5, 15))

            client_inner = ctk.CTkFrame(client_card, fg_color="transparent")
            client_inner.pack(fill="x", padx=20, pady=12)

            ctk.CTkLabel(client_inner, text=f"👤 اسم العميل: {client_name}", font=("Segoe UI", 16, "bold"),
                         text_color=FIB_GREEN).pack(side="right")

            info_frame = ctk.CTkFrame(client_inner, fg_color="transparent")
            info_frame.pack(side="left")
            ctk.CTkLabel(info_frame, text=f"الفرع: {branch_name} | الحساب: {cust_no}", font=("Segoe UI", 13, "bold"),
                         text_color=TEXT_MUTED, fg_color=BOX_BG, corner_radius=6).pack(side="right", ipadx=10, ipady=3)

            # دالة لتنسيق المبالغ المالية
            def format_money(val):
                try:
                    return "{:,.2f}".format(float(val))
                except Exception:
                    return "0.00"

            # دالة مساعدة لإنشاء المربعات
            def create_stat_box(parent_frame, title, value, v_color):
                box = ctk.CTkFrame(parent_frame, fg_color=BOX_BG, corner_radius=8)
                box.pack(side="right", fill="x", expand=True, padx=4)
                ctk.CTkLabel(box, text=title, font=("Segoe UI", 12, "bold"), text_color=TEXT_MUTED).pack(
                    anchor="center", pady=(8, 2))
                ctk.CTkLabel(box, text=value, font=("Segoe UI", 16, "bold"), text_color=v_color).pack(anchor="center",
                                                                                                      pady=(0, 8))

            # =========================================
            # --- 2. رندر كروت الخلاصة (الإجماليات) ---
            # =========================================
            for index, row in summary_df.iterrows():
                card = ctk.CTkFrame(self.cheque_results_scroll, fg_color=CARD_BG, corner_radius=12, border_width=1,
                                    border_color="#E2E8F0")
                card.pack(fill="x", padx=10, pady=8)

                header_row = ctk.CTkFrame(card, fg_color="transparent")
                header_row.pack(fill="x", padx=15, pady=(15, 5))
                ctk.CTkLabel(header_row, text=f"📊 ملخص المبالغ بعُملة: {row.get('CURR_NAME', '')}",
                             font=("Segoe UI", 16, "bold"), text_color=FIB_GOLD).pack(side="right")

                ctk.CTkFrame(card, fg_color="#F1F5F9", height=2).pack(fill="x", padx=15, pady=5)

                stats_frame = ctk.CTkFrame(card, fg_color="transparent")
                stats_frame.pack(fill="x", padx=15, pady=(5, 15))

                create_stat_box(stats_frame, "إجمالي التعويض", format_money(row.get('total_camt8', 0)), "#DC2626")
                create_stat_box(stats_frame, "إجمالي المتأخرات", format_money(row.get('total_camt7', 0)), "#EA580C")
                create_stat_box(stats_frame, "إجمالي المسدد", format_money(row.get('total_camt9', 0)), "#2563EB")
                create_stat_box(stats_frame, "مجموع المبالغ", format_money(row.get('total_camt1', 0)), FIB_GREEN)
                create_stat_box(stats_frame, "عدد الشيكات", str(row.get('check_count', 0)), TEXT_DARK)

            # =========================================
            # --- فاصل بصري بين الخلاصة والتفاصيل ---
            # =========================================
            separator_frame = ctk.CTkFrame(self.cheque_results_scroll, fg_color="transparent")
            separator_frame.pack(fill="x", padx=10, pady=(20, 10))
            ctk.CTkLabel(separator_frame, text="📑 تفاصيل الشيكات (كل شيك على حدة)", font=("Segoe UI", 18, "bold"),
                         text_color=FIB_GREEN).pack(side="right")
            ctk.CTkFrame(separator_frame, fg_color="#CBD5E1", height=2).pack(side="right", fill="x", expand=True,
                                                                             padx=(20, 10))

            # =========================================
            # --- 3. رندر كروت التفاصيل (كل شيك لوحده) ---
            # =========================================
            for index, row in df.iterrows():
                detail_card = ctk.CTkFrame(self.cheque_results_scroll, fg_color=CARD_BG, corner_radius=12,
                                           border_width=1, border_color="#E2E8F0")
                detail_card.pack(fill="x", padx=10, pady=6)

                ctk.CTkFrame(detail_card, fg_color=FIB_GREEN, width=6, corner_radius=0).pack(side="right", fill="y",
                                                                                             pady=10)

                card_content = ctk.CTkFrame(detail_card, fg_color="transparent")
                card_content.pack(fill="both", expand=True, padx=15, pady=12)

                # رأس كارت الشيك
                detail_header = ctk.CTkFrame(card_content, fg_color="transparent")
                detail_header.pack(fill="x", pady=(0, 8))

                cchno_val = str(row.get('cchno', '—')).strip()
                if cchno_val in ['nan', 'None', '']: cchno_val = '—'

                curr_display = row.get('CURR_NAME', str(row.get('ccur', '—')))

                cdat1_val = row.get('cdat1')
                if pd.isna(cdat1_val):
                    cdat1_str = "—"
                else:
                    try:
                        cdat1_str = pd.to_datetime(cdat1_val).strftime('%Y-%m-%d')
                    except Exception:
                        cdat1_str = str(cdat1_val)

                ctk.CTkLabel(detail_header, text=f"رقم الشيك: {cchno_val}", font=("Segoe UI", 16, "bold"),
                             text_color=TEXT_DARK).pack(side="right")
                ctk.CTkLabel(detail_header, text=f"العملة: {curr_display}", font=("Segoe UI", 12, "bold"),
                             text_color="#FFFFFF", fg_color=TEXT_MUTED, corner_radius=6).pack(side="left", ipadx=8,
                                                                                              ipady=2)

                ctk.CTkFrame(card_content, fg_color="#F1F5F9", height=2).pack(fill="x", pady=4)

                # قيم الشيك الفردية والحسابات
                detail_stats = ctk.CTkFrame(card_content, fg_color="transparent")
                detail_stats.pack(fill="x", pady=(5, 0))

                cgl_val = str(row.get('cgl', '—')).strip()
                if cgl_val in ['nan', 'None', '']: cgl_val = '—'

                csub_val = str(row.get('csub', '—')).strip()
                if csub_val in ['nan', 'None', '']: csub_val = '—'

                create_stat_box(detail_stats, "قيمة الشيك", format_money(row.get('camt1', 0)), FIB_GREEN)
                create_stat_box(detail_stats, "المتأخرات", format_money(row.get('camt7', 0)), "#EA580C")
                create_stat_box(detail_stats, "تاريخ الاستحقاق", cdat1_str, TEXT_DARK)
                create_stat_box(detail_stats, "أستاذ عام", cgl_val, TEXT_MUTED)
                create_stat_box(detail_stats, "أستاذ فرعي", csub_val, TEXT_MUTED)
    def setup_sponsors_inquiry_ui(self, parent):
        import pandas as pd
        import customtkinter as ctk
        from tkinter import messagebox
        import threading
        import logging
        import re

        # =========================================
        # 🎨 1. Theme Colors
        # =========================================
        FIB_GREEN = "#005C34"
        FIB_GOLD = "#C5A059"
        BG_MAIN = "#F8FAFC"
        CARD_BG = "#FFFFFF"
        BOX_BG = "#F1F5F9"
        TEXT_DARK = "#0F172A"
        TEXT_MUTED = "#64748B"

        # حاويات الشاشة
        main_container = ctk.CTkFrame(parent, fg_color=BG_MAIN)
        main_container.pack(fill="both", expand=True)

        header = ctk.CTkFrame(main_container, fg_color=FIB_GREEN, height=65, corner_radius=0)
        header.pack(fill="x")
        header.pack_propagate(False)

        ctk.CTkFrame(main_container, fg_color=FIB_GOLD, height=4, corner_radius=0).pack(fill="x")

        ctk.CTkLabel(
            header, text="الاستفسار عن الكفلاء 🤝",
            font=("Segoe UI", 22, "bold"), text_color=CARD_BG
        ).pack(side="right", padx=30, pady=15)

        # =========================================
        # 🔍 2. Search Area
        # =========================================
        search_frame = ctk.CTkFrame(main_container, fg_color=CARD_BG, corner_radius=15, border_width=1,
                                    border_color="#E2E8F0")
        search_frame.pack(fill="x", padx=20, pady=15)

        search_inner = ctk.CTkFrame(search_frame, fg_color="transparent")
        search_inner.pack(side="right", fill="y", padx=20, pady=15)

        # أزرار البحث والمسح
        btn_clear = ctk.CTkButton(search_inner, text="🧹 مسح", font=("Segoe UI", 14, "bold"), fg_color="#64748B",
                                  hover_color="#475569", width=90, height=40, corner_radius=8,
                                  command=lambda: clear_search())
        btn_clear.pack(side="left", padx=(5, 10))

        btn_search = ctk.CTkButton(search_inner, text="🔍 بحث", font=("Segoe UI", 15, "bold"), fg_color=FIB_GREEN,
                                   hover_color="#004426", width=110, height=40, corner_radius=8,
                                   command=lambda: execute_search())
        btn_search.pack(side="left", padx=5)

        # اختيار العملة
        self.cmb_sponsor_currency = ctk.CTkComboBox(search_inner, font=("Segoe UI", 14, "bold"), justify="right",
                                                    width=150, height=40, border_color="#CBD5E1",
                                                    values=["جاري التحميل..."])
        self.cmb_sponsor_currency.pack(side="left", padx=10)
        ctk.CTkLabel(search_inner, text="العملة:", font=("Segoe UI", 14, "bold"), text_color=TEXT_DARK).pack(
            side="left", padx=(10, 2))

        # إدخال رقم العميل
        self.ent_sponsor_cust_no = ctk.CTkEntry(search_inner, font=("Segoe UI", 15, "bold"), justify="center",
                                                placeholder_text="رقم الحساب/العميل...", width=160, height=40,
                                                border_color="#CBD5E1")
        self.ent_sponsor_cust_no.pack(side="left", padx=10)
        ctk.CTkLabel(search_inner, text="رقم الحساب:", font=("Segoe UI", 14, "bold"), text_color=TEXT_DARK).pack(
            side="left", padx=(10, 2))

        # اختيار الفرع
        if hasattr(self, '_create_premium_select'):
            self.cmb_sponsor_branch_box, self.cmb_sponsor_branch = self._create_premium_select(search_inner, values=[
                "جاري التحميل..."], default="جاري التحميل...", title="اختر الفرع")
            self.cmb_sponsor_branch_box.pack(side="left", padx=10)
        else:
            self.cmb_sponsor_branch = ctk.CTkComboBox(search_inner, font=("Segoe UI", 14, "bold"), justify="right",
                                                      width=200, height=40, border_color="#CBD5E1")
            self.cmb_sponsor_branch.pack(side="left", padx=10)
        ctk.CTkLabel(search_inner, text="الفرع:", font=("Segoe UI", 14, "bold"), text_color=TEXT_DARK).pack(side="left",
                                                                                                            padx=(10,
                                                                                                                  2))

        self.sponsor_summary_lbl = ctk.CTkLabel(main_container, text="", font=("Segoe UI", 13, "bold"),
                                                text_color=TEXT_MUTED)
        self.sponsor_summary_lbl.pack(anchor="e", padx=25, pady=(0, 5))

        self.sponsor_results_scroll = ctk.CTkScrollableFrame(main_container, fg_color="transparent")
        self.sponsor_results_scroll.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        # =========================================
        # ⚙️ 3. Initialization & Helpers
        # =========================================
        self.currency_dict_name_to_code = {}  # { "جنيه مصري": "0", "دولار": "1" }

        def load_initial_data():
            # 1. تحميل الفروع
            if hasattr(self, 'branch_mapping') and self.branch_mapping:
                branches = list(self.branch_mapping.keys())
                self.cmb_sponsor_branch.configure(values=branches)
                self.cmb_sponsor_branch.set(branches[0])
            else:
                if hasattr(self, 'nuwairy_load_branches'):
                    self.nuwairy_load_branches()
                self.after(500, load_initial_data)
                return  # استنى الفروع تحمل الأول

            # 2. تحميل العملات من قاعدة البيانات (Thread)
            def fetch_currencies():
                try:
                    engine = getattr(self, '_get_db_connection', lambda: None)()
                    if engine:
                        sql = "SELECT fcur, cnm FROM [dbo].[tbl_currency] WITH (NOLOCK) WHERE cnm IS NOT NULL"
                        df = pd.read_sql(sql, engine)
                        curr_list = []
                        self.currency_dict_name_to_code.clear()

                        for _, row in df.iterrows():
                            c_code = str(row['fcur']).strip()
                            c_name = str(row['cnm']).strip()
                            if c_name:
                                curr_list.append(c_name)
                                self.currency_dict_name_to_code[c_name] = c_code

                        if curr_list:
                            self.after(0, lambda: [
                                self.cmb_sponsor_currency.configure(values=curr_list),
                                self.cmb_sponsor_currency.set(curr_list[0])
                            ])
                except Exception as e:
                    logging.error(f"Error loading currencies: {e}")

            threading.Thread(target=fetch_currencies, daemon=True).start()

        load_initial_data()
        self.ent_sponsor_cust_no.bind("<Return>", lambda event: execute_search())

        def clear_search():
            self.ent_sponsor_cust_no.delete(0, 'end')
            self.sponsor_summary_lbl.configure(text="")
            for widget in self.sponsor_results_scroll.winfo_children():
                widget.destroy()

        # دالة تنظيف الأسماء (تم إزالة الريجيكس اللي كان بيفصل الحروف)
        def clean_arabic_name(name):
            if not isinstance(name, str) or not name.strip():
                return "—"

            cleaned = name.strip()

            # 1. تنظيف الرموز والمسافات الزائدة
            cleaned = re.sub(r'[_+\-]', ' ', cleaned)
            cleaned = re.sub(r'\s+', ' ', cleaned)

            # 2. فصل البادئات الشهيرة في الأسماء (ابن / عبد / ابو / ام)
            # مثال: ابنعمر -> ابن عمر | ابنسالم -> ابن سالم | عبدالله -> عبد الله
            cleaned = re.sub(r'(\bابن|\bعبد|\bابو|\bأبو|\bام|\bأم)([أ-ي])', r'\1 \2', cleaned)

            # 3. فصل الكلمات الملتصقة بعد التاء المربوطة أو الهاء (خاص بأسماء الشركات)
            # مثال: السعوديهتراست -> السعوديه تراست
            cleaned = re.sub(r'([ةه])([أ-ي])', r'\1 \2', cleaned)

            # 4. فصل الكلمات التجارية والخدمية الشهيرة الملتصقة (زي: للسياحة، للمقاولات، تراست... إلخ)
            # مثال: تراستللسياحه -> تراست للسياحه
            cleaned = re.sub(r'([أ-ي])(للسياح|للتجار|للمقاول|للاستثمار|للخدمات|للتأمين|تراست|جروب|كومباني)', r'\1 \2',
                             cleaned)

            # 5. إعادة إزالة أي مسافات مضاعفة نتجت عن الفصل
            return re.sub(r'\s+', ' ', cleaned).strip()

        # =========================================
        # 🚀 4. Execute Search & DB Logic
        # =========================================
        def execute_search():
            branch_name = self.cmb_sponsor_branch.get().strip()
            cust_no = self.ent_sponsor_cust_no.get().strip()
            curr_name = self.cmb_sponsor_currency.get().strip()

            if not cust_no:
                messagebox.showwarning("تنبيه", "يرجى إدخال رقم الحساب/العميل أولاً")
                self.ent_sponsor_cust_no.focus()
                return

            if not hasattr(self, 'branch_mapping') or branch_name not in self.branch_mapping:
                messagebox.showerror("خطأ", "برجاء اختيار فرع صحيح")
                return

            # استخراج الأكواد من القواميس
            branch_info = self.branch_mapping[branch_name]
            branch_code = branch_info[0] if isinstance(branch_info, tuple) else branch_info

            # لو العملة مالهاش كود في القاموس، هنعتبر الكود هو الصفر كافتراضي
            curr_code = self.currency_dict_name_to_code.get(curr_name, "0")

            # تفريغ الشاشة وتحميل
            for widget in self.sponsor_results_scroll.winfo_children():
                widget.destroy()

            self.sponsor_summary_lbl.configure(text="")
            ctk.CTkLabel(self.sponsor_results_scroll, text="⚡ جاري الاستعلام عن الكفلاء...",
                         font=("Segoe UI", 16, "bold"), text_color=FIB_GOLD).pack(pady=50)

            def fetch_data():
                try:
                    engine = getattr(self, '_get_db_connection', lambda: None)()
                    if not engine:
                        raise Exception("لم يتم العثور على دالة الاتصال بقاعدة البيانات.")

                    # تجهيز الرقم لضمان تطابق الـ Index (نفس فكرة الشاشة السابقة)
                    cust_str = cust_no.strip()
                    try:
                        cust_int_str = str(int(cust_str))
                    except:
                        cust_int_str = cust_str

                    # 1. جلب اسم الجدول للفرع من TBL_Branches
                    target_table = None
                    try:
                        branch_query = f"SELECT TableName FROM [dbo].[TBL_Branches] WITH (NOLOCK) WHERE BranchCode = '{branch_code}'"
                        branch_df = pd.read_sql(branch_query, engine)
                        if not branch_df.empty and pd.notna(branch_df.iloc[0]['TableName']):
                            target_table = str(branch_df.iloc[0]['TableName']).strip()
                    except Exception as b_err:
                        logging.error(f"Error fetching TableName: {b_err}")

                    # 2. جلب اسم العميل (Bname) من جدول الفرع
                    fetched_client_name = "غير مسجل"
                    if target_table:
                        try:
                            client_query = f"""
                                SELECT TOP 1 BNAME 
                                FROM [dbo].[{target_table}] WITH (NOLOCK) 
                                WHERE BCLNT = '{cust_str}' OR BCLNT = '{cust_int_str}'
                            """
                            client_df = pd.read_sql(client_query, engine)
                            # التعديل هنا: تمرير اسم العميل لدالة التنظيف
                            if not client_df.empty and pd.notna(client_df.iloc[0].get('BNAME')):
                                raw_client_name = str(client_df.iloc[0].get('BNAME')).strip()
                                fetched_client_name = clean_arabic_name(raw_client_name)
                        except Exception as cl_err:
                            logging.warning(f"Could not fetch client name: {cl_err}")

                    # 3. جلب الكفلاء من tbl_sponsers (بناءً على fbr, fclnt, fcur) باستخدام الـ Index السريع
                    sql_sponsors = f"""
                        SELECT fclntk, fclntm, fnam
                        FROM [dbo].[tbl_sponsers] WITH (NOLOCK)
                        WHERE fbr = '{branch_code}'
                          AND fcur = '{curr_code}'
                          AND (fclnt = '{cust_str}' OR fclnt = '{cust_int_str}')
                    """
                    df_sponsors = pd.read_sql(sql_sponsors, engine)

                    self.after(0, lambda: update_results_ui(df_sponsors, fetched_client_name, cust_no, branch_name,
                                                            curr_name))
                except Exception as e:
                    logging.error(f"Error fetching sponsors: {e}")
                    self.after(0, lambda: update_results_ui(pd.DataFrame(), "غير مسجل", cust_no, branch_name, curr_name,
                                                            error=str(e)))

            threading.Thread(target=fetch_data, daemon=True).start()

        # =========================================
        # 📑 5. Update Results UI
        # =========================================
        def update_results_ui(df, client_name, cust_no, branch_name, curr_name, error=None):
            for widget in self.sponsor_results_scroll.winfo_children():
                widget.destroy()

            if error:
                self.sponsor_summary_lbl.configure(text="")
                ctk.CTkLabel(self.sponsor_results_scroll, text=f"❌ حدث خطأ:\n{error}", font=("Segoe UI", 14, "bold"),
                             text_color="#EF4444").pack(pady=40)
                return

            if df.empty:
                self.sponsor_summary_lbl.configure(text="")
                ctk.CTkLabel(self.sponsor_results_scroll, text="🔍 لا يوجد كفلاء مسجلين لهذا الحساب بهذه العملة",
                             font=("Segoe UI", 18, "bold"), text_color=TEXT_MUTED).pack(pady=60)
                return

            self.sponsor_summary_lbl.configure(text=f"إجمالي عدد الكفلاء: {len(df)}")

            # --- كارت بيانات العميل الرئيسي ---
            client_card = ctk.CTkFrame(self.sponsor_results_scroll, fg_color=CARD_BG, corner_radius=12, border_width=1,
                                       border_color="#CBD5E1")
            client_card.pack(fill="x", padx=10, pady=(5, 15))

            client_inner = ctk.CTkFrame(client_card, fg_color="transparent")
            client_inner.pack(fill="x", padx=20, pady=12)

            ctk.CTkLabel(client_inner, text=f"👤 اسم العميل المقترض: {client_name}", font=("Segoe UI", 16, "bold"),
                         text_color=FIB_GREEN).pack(side="right")

            info_frame = ctk.CTkFrame(client_inner, fg_color="transparent")
            info_frame.pack(side="left")
            ctk.CTkLabel(info_frame, text=f"العملة: {curr_name}", font=("Segoe UI", 13, "bold"), text_color="#FFFFFF",
                         fg_color=FIB_GOLD, corner_radius=6).pack(side="right", padx=5, ipadx=10, ipady=3)
            ctk.CTkLabel(info_frame, text=f"الفرع: {branch_name} | الحساب: {cust_no}", font=("Segoe UI", 13, "bold"),
                         text_color=TEXT_MUTED, fg_color=BOX_BG, corner_radius=6).pack(side="right", ipadx=10, ipady=3)

            # --- رندر كروت الكفلاء ---
            for index, row in df.iterrows():
                # تنظيف اسم الكفيل باستخدام الريجيكس
                raw_name = str(row.get('fnam', '—'))
                clean_name = clean_arabic_name(raw_name)

                card = ctk.CTkFrame(self.sponsor_results_scroll, fg_color=CARD_BG, corner_radius=12, border_width=1,
                                    border_color="#E2E8F0")
                card.pack(fill="x", padx=10, pady=8)

                # شريط جانبي
                ctk.CTkFrame(card, fg_color="#334155", width=6, corner_radius=0).pack(side="right", fill="y", pady=10)

                card_content = ctk.CTkFrame(card, fg_color="transparent")
                card_content.pack(fill="both", expand=True, padx=20, pady=15)

                # اسم الكفيل
                ctk.CTkLabel(card_content, text=f"كفيل رقم ({index + 1})", font=("Segoe UI", 12, "bold"),
                             text_color=TEXT_MUTED).pack(anchor="e", pady=(0, 2))
                ctk.CTkLabel(card_content, text=clean_name, font=("Segoe UI", 18, "bold"), text_color=TEXT_DARK).pack(
                    anchor="e", pady=(0, 10))

                # خط فاصل
                ctk.CTkFrame(card_content, fg_color="#F1F5F9", height=2).pack(fill="x", pady=6)

                # أرقام الكفيل
                nums_frame = ctk.CTkFrame(card_content, fg_color="transparent")
                nums_frame.pack(fill="x", pady=(5, 0))

                # رقم الكفيل العادي
                box1 = ctk.CTkFrame(nums_frame, fg_color=BOX_BG, corner_radius=8)
                box1.pack(side="right", fill="x", expand=True, padx=(0, 5))
                ctk.CTkLabel(box1, text="رقم الكفيل (الفرع)", font=("Segoe UI", 12, "bold"),
                             text_color=TEXT_MUTED).pack(anchor="center", pady=(6, 2))
                ctk.CTkLabel(box1, text=row.get('fclntk', '—'), font=("Segoe UI", 16, "bold"),
                             text_color=FIB_GREEN).pack(anchor="center", pady=(0, 6))

                # رقم الكفيل المركزي
                box2 = ctk.CTkFrame(nums_frame, fg_color=BOX_BG, corner_radius=8)
                box2.pack(side="left", fill="x", expand=True, padx=(5, 0))
                ctk.CTkLabel(box2, text="رقم الكفيل (المركزي)", font=("Segoe UI", 12, "bold"),
                             text_color=TEXT_MUTED).pack(anchor="center", pady=(6, 2))
                ctk.CTkLabel(box2, text=row.get('fclntm', '—'), font=("Segoe UI", 16, "bold"),
                             text_color=FIB_GOLD).pack(anchor="center", pady=(0, 6))
    def setup_local_recruitment_ui(self, parent):
        import pandas as pd
        import customtkinter as ctk
        from tkinter import messagebox
        import threading
        import logging
        import re

        # =========================================
        # 🎨 1. Theme Colors & Styles
        # =========================================
        FIB_GREEN = "#005C34"
        FIB_GOLD = "#C5A059"
        BG_MAIN = "#F8FAFC"
        CARD_BG = "#FFFFFF"
        BOX_BG = "#F1F5F9"
        TEXT_DARK = "#0F172A"
        TEXT_MUTED = "#64748B"

        # الحاوية الرئيسية
        main_container = ctk.CTkFrame(parent, fg_color=BG_MAIN)
        main_container.pack(fill="both", expand=True)

        # الهيدر العلوي
        header = ctk.CTkFrame(main_container, fg_color=FIB_GREEN, height=65, corner_radius=0)
        header.pack(fill="x")
        header.pack_propagate(False)

        ctk.CTkFrame(main_container, fg_color=FIB_GOLD, height=4, corner_radius=0).pack(fill="x")

        title_lbl = ctk.CTkLabel(
            header,
            text="بحث التوظيف المحلي للعملاء 💼",
            font=("Segoe UI", 22, "bold"),
            text_color=CARD_BG
        )
        title_lbl.pack(side="right", padx=30, pady=15)

        # =========================================
        # 🔍 2. Search Area
        # =========================================
        search_frame = ctk.CTkFrame(main_container, fg_color=CARD_BG, corner_radius=15, border_width=1,
                                    border_color="#E2E8F0")
        search_frame.pack(fill="x", padx=20, pady=15)

        search_inner = ctk.CTkFrame(search_frame, fg_color="transparent")
        search_inner.pack(side="right", fill="y", padx=20, pady=15)

        # --- زر مسح البيانات ---
        btn_clear = ctk.CTkButton(
            search_inner, text="🧹 مسح", font=("Segoe UI", 14, "bold"),
            fg_color="#64748B", hover_color="#475569", text_color="white",
            width=90, height=40, corner_radius=8, command=lambda: clear_search()
        )
        btn_clear.pack(side="left", padx=(5, 10))

        # --- زر البحث ---
        btn_search = ctk.CTkButton(
            search_inner, text="🔍 بحث", font=("Segoe UI", 15, "bold"),
            fg_color=FIB_GREEN, hover_color="#004426", text_color="white",
            width=110, height=40, corner_radius=8, command=lambda: execute_search()
        )
        btn_search.pack(side="left", padx=5)

        # --- إدخال رقم العميل ---
        self.ent_recruitment_cust_no = ctk.CTkEntry(
            search_inner, font=("Segoe UI", 15, "bold"),
            justify="center", placeholder_text="رقم العميل...",
            width=180, height=40, border_color="#CBD5E1"
        )
        self.ent_recruitment_cust_no.pack(side="left", padx=10)

        ctk.CTkLabel(search_inner, text="رقم العميل:", font=("Segoe UI", 14, "bold"), text_color=TEXT_DARK).pack(
            side="left", padx=(10, 2))

        # --- قائمة الفروع ---
        if hasattr(self, '_create_premium_select'):
            self.cmb_recruitment_branch_box, self.cmb_recruitment_branch = self._create_premium_select(
                search_inner,
                values=["جاري التحميل..."],
                default="جاري التحميل...",
                title="اختر الفرع"
            )
            self.cmb_recruitment_branch_box.pack(side="left", padx=10)
        else:
            self.cmb_recruitment_branch = ctk.CTkComboBox(
                search_inner, font=("Segoe UI", 14, "bold"), justify="right",
                width=230, height=40, border_color="#CBD5E1"
            )
            self.cmb_recruitment_branch.pack(side="left", padx=10)

        ctk.CTkLabel(search_inner, text="الفرع:", font=("Segoe UI", 14, "bold"), text_color=TEXT_DARK).pack(side="left",
                                                                                                            padx=(10,
                                                                                                                  2))

        # شريط ملخص النتائج / العداد
        self.recruitment_summary_lbl = ctk.CTkLabel(main_container, text="", font=("Segoe UI", 13, "bold"),
                                                    text_color=TEXT_MUTED)
        self.recruitment_summary_lbl.pack(anchor="e", padx=25, pady=(0, 5))

        # تحميل الفروع
        def load_branches_to_combo():
            if hasattr(self, 'branch_mapping') and self.branch_mapping:
                branches = list(self.branch_mapping.keys())
                self.cmb_recruitment_branch.configure(values=branches)
                self.cmb_recruitment_branch.set(branches[0])
            else:
                if hasattr(self, 'nuwairy_load_branches'):
                    self.nuwairy_load_branches()
                self.after(500, load_branches_to_combo)

        load_branches_to_combo()
        self.ent_recruitment_cust_no.bind("<Return>", lambda event: execute_search())

        # =========================================
        # 📜 3. Results Container
        # =========================================
        self.recruitment_results_scroll = ctk.CTkScrollableFrame(main_container, fg_color="transparent")
        self.recruitment_results_scroll.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        def clear_search():
            self.ent_recruitment_cust_no.delete(0, 'end')
            self.recruitment_summary_lbl.configure(text="")
            for widget in self.recruitment_results_scroll.winfo_children():
                widget.destroy()

        def format_money(val):
            try:
                if pd.isna(val) or val == "":
                    return "0.00"
                return f"{float(val):,.2f}"
            except:
                return str(val)

        # =========================================
        # ⚙️ 4. Search & Thread Execution
        # =========================================
        def execute_search():
            branch_name = self.cmb_recruitment_branch.get().strip()
            cust_no = self.ent_recruitment_cust_no.get().strip()

            if not cust_no:
                messagebox.showwarning("تنبيه", "يرجى إدخال رقم العميل أولاً")
                self.ent_recruitment_cust_no.focus()
                return

            if not hasattr(self, 'branch_mapping') or branch_name not in self.branch_mapping:
                messagebox.showerror("خطأ", "برجاء اختيار فرع صحيح")
                return

            branch_info = self.branch_mapping[branch_name]
            branch_code = branch_info[0] if isinstance(branch_info, tuple) else branch_info

            # تفريغ الواجهة لعرض أنيميشن التحميل
            for widget in self.recruitment_results_scroll.winfo_children():
                widget.destroy()

            self.recruitment_summary_lbl.configure(text="")
            lbl_loading = ctk.CTkLabel(
                self.recruitment_results_scroll,
                text="⚡ جاري الاستعلام عن التوظيف المحلي...",
                font=("Segoe UI", 16, "bold"), text_color=FIB_GOLD
            )
            lbl_loading.pack(pady=50)

            def fetch_data():
                try:
                    engine = getattr(self, '_get_db_connection', lambda: None)()
                    if not engine:
                        raise Exception("لم يتم العثور على دالة الاتصال بقاعدة البيانات.")

                    # --- تجهيز رقم العميل ---
                    cust_str = cust_no.strip()
                    try:
                        cust_int_str = str(int(cust_str))
                    except:
                        cust_int_str = cust_str

                    # 1. جلب خريطة العملات من tbl_currency (fcur -> cnm)
                    currency_map = {}
                    try:
                        curr_query = "SELECT fcur, cnm FROM [dbo].[tbl_currency] WITH (NOLOCK)"
                        curr_df = pd.read_sql(curr_query, engine)
                        if not curr_df.empty:
                            for _, crow in curr_df.iterrows():
                                if pd.notna(crow.get('fcur')) and pd.notna(crow.get('cnm')):
                                    k = str(crow['fcur']).strip()
                                    v = str(crow['cnm']).strip()
                                    currency_map[k] = v
                    except Exception as curr_err:
                        logging.warning(f"Error fetching currencies: {curr_err}")

                    # 2. جلب اسم الجدول من TBL_Branches
                    target_table = None
                    try:
                        branch_query = f"SELECT TableName FROM [dbo].[TBL_Branches] WITH (NOLOCK) WHERE BranchCode = '{branch_code}'"
                        branch_df = pd.read_sql(branch_query, engine)
                        if not branch_df.empty and pd.notna(branch_df.iloc[0]['TableName']):
                            target_table = str(branch_df.iloc[0]['TableName']).strip()
                    except Exception as b_err:
                        logging.error(f"Error fetching TableName: {b_err}")

                    # 3. جلب اسم العميل
                    fetched_client_name = "غير مسجل"
                    if target_table:
                        try:
                            client_query = f"""
                                SELECT TOP 1 BNAME 
                                FROM [dbo].[{target_table}] WITH (NOLOCK) 
                                WHERE BCLNT = '{cust_str}' OR BCLNT = '{cust_int_str}'
                            """
                            client_df = pd.read_sql(client_query, engine)
                            if not client_df.empty and pd.notna(client_df.iloc[0].get('BNAME')):
                                fetched_client_name = str(client_df.iloc[0].get('BNAME')).strip()
                        except Exception as cl_err:
                            logging.warning(f"Could not fetch client name: {cl_err}")

                    # 4. جلب بيانات التوظيف المحلي
                    sql = f"""
                        SELECT IGL, ISUB, ICUR, ICOD, IAMT17, IAMT19, IAMT20, IAMT21
                        FROM [dbo].[tbl_localrecruitmentprocesses] WITH (NOLOCK)
                        WHERE iclnt = '{cust_str}' OR iclnt = '{cust_int_str}'
                    """
                    df = pd.read_sql(sql, engine)

                    # 5. مطابقة كود العملة باسم العملة من tbl_currency
                    if not df.empty and 'ICUR' in df.columns:
                        df['CURRENCY_NAME'] = df['ICUR'].astype(str).str.strip().map(currency_map)
                        # لو الكود مش موجود في جدول العملات يرجع نفس الكود الأصلي
                        df['CURRENCY_NAME'] = df['CURRENCY_NAME'].fillna(df['ICUR'].astype(str))

                    self.after(0, lambda: update_results_ui(df, fetched_client_name, cust_no, branch_name))
                except Exception as e:
                    logging.error(f"Error fetching recruitment: {e}")
                    self.after(0, lambda: update_results_ui(pd.DataFrame(), "غير مسجل", cust_no, branch_name, error=str(e)))

            threading.Thread(target=fetch_data, daemon=True).start()

        def update_results_ui(df, client_name, cust_no, branch_name, error=None):
            for widget in self.recruitment_results_scroll.winfo_children():
                widget.destroy()

            if error:
                self.recruitment_summary_lbl.configure(text="")
                ctk.CTkLabel(
                    self.recruitment_results_scroll,
                    text=f"❌ حدث خطأ أثناء الاتصال بقاعدة البيانات:\n{error}",
                    font=("Segoe UI", 14, "bold"), text_color="#EF4444"
                ).pack(pady=40)
                return

            # =========================================
            # 🚀 التعديل الجديد: استبعاد العمليات الصفرية
            # =========================================
            if not df.empty and 'IAMT19' in df.columns:
                # تحويل عمود قيمة العملية لأرقام (ولو فيه خطأ يعتبره صفر)
                df['IAMT19_numeric'] = pd.to_numeric(df['IAMT19'], errors='coerce').fillna(0)
                # فلترة الداتا واختيار العمليات اللي قيمتها لا تساوي صفر فقط
                df = df[df['IAMT19_numeric'] != 0]

            if df.empty:
                self.recruitment_summary_lbl.configure(text="")
                ctk.CTkLabel(
                    self.recruitment_results_scroll,
                    text="🔍 لا توجد بيانات توظيف محلي مسجلة لهذا العميل (أو العمليات قيمتها صفر)",
                    font=("Segoe UI", 18, "bold"), text_color=TEXT_MUTED
                ).pack(pady=60)
                return

            # تحديث عداد النتائج (هيقرا العدد بعد استبعاد الأصفار)
            self.recruitment_summary_lbl.configure(text=f"إجمالي عدد العمليات: {len(df)}")

            # =========================================
            # 👤 كارت بيانات العميل الرئيسي
            # =========================================
            client_header_card = ctk.CTkFrame(self.recruitment_results_scroll, fg_color=CARD_BG, corner_radius=12,
                                              border_width=1, border_color="#CBD5E1")
            client_header_card.pack(fill="x", padx=10, pady=(5, 15))

            client_inner = ctk.CTkFrame(client_header_card, fg_color="transparent")
            client_inner.pack(fill="x", padx=20, pady=12)

            ctk.CTkLabel(client_inner, text=f"👤 اسم العميل: {client_name}", font=("Segoe UI", 16, "bold"),
                         text_color=FIB_GREEN).pack(side="right")
            ctk.CTkLabel(client_inner, text=f"الفرع: {branch_name} | رقم العميل: {cust_no}",
                         font=("Segoe UI", 13, "bold"), text_color=TEXT_MUTED, fg_color=BOX_BG, corner_radius=6).pack(
                side="left", ipadx=10, ipady=3)

            # =========================================
            # 📑 رندر كروت العمليات
            # =========================================
            for _, row in df.iterrows():
                # جسم الكارت
                card = ctk.CTkFrame(
                    self.recruitment_results_scroll, fg_color=CARD_BG, corner_radius=12,
                    border_width=1, border_color="#E2E8F0"
                )
                card.pack(fill="x", padx=10, pady=8)

                # شريط جانبي
                ctk.CTkFrame(card, fg_color=FIB_GOLD, width=6, corner_radius=0).pack(side="right", fill="y", pady=10)

                card_content = ctk.CTkFrame(card, fg_color="transparent")
                card_content.pack(fill="both", expand=True, padx=20, pady=15)

                # --- صف رأس الكارت (الأكواد الأساسية) ---
                header_row = ctk.CTkFrame(card_content, fg_color="transparent")
                header_row.pack(fill="x", pady=(0, 10))

                curr_display = row.get('CURRENCY_NAME', row.get('ICUR', '—'))

                ctk.CTkLabel(
                    header_row,
                    text=f"العملة: {curr_display}",
                    font=("Segoe UI", 13, "bold"),
                    text_color="#FFFFFF",
                    fg_color=FIB_GREEN,
                    corner_radius=6
                ).pack(side="left", ipadx=10, ipady=3)
                ctk.CTkLabel(header_row, text=f"الأستاذ الفرع (ISUB): {row.get('ISUB', '—')}",
                             font=("Segoe UI", 14, "bold"), text_color=TEXT_MUTED).pack(side="right", padx=15)
                ctk.CTkLabel(header_row, text=f"الأستاذ العام (IGL): {row.get('IGL', '—')}",
                             font=("Segoe UI", 14, "bold"), text_color=TEXT_MUTED).pack(side="right", padx=15)

                # خط فاصل
                ctk.CTkFrame(card_content, fg_color="#F1F5F9", height=2).pack(fill="x", pady=6)

                # --- شبكة القيم والمبالغ ---
                data_grid = ctk.CTkFrame(card_content, fg_color="transparent")
                data_grid.pack(fill="x", pady=5)
                data_grid.grid_columnconfigure((0, 1, 2, 3), weight=1)

                def create_info_box(parent, col_idx, title, value, val_color=TEXT_DARK):
                    box = ctk.CTkFrame(parent, fg_color=BOX_BG, corner_radius=8)
                    box.grid(row=0, column=col_idx, padx=5, pady=5, sticky="ew")
                    ctk.CTkLabel(box, text=title, font=("Segoe UI", 12, "bold"), text_color=TEXT_MUTED).pack(
                        anchor="center", pady=(6, 2))
                    ctk.CTkLabel(box, text=format_money(value), font=("Segoe UI", 16, "bold"),
                                 text_color=val_color).pack(anchor="center", pady=(0, 6))

                # المربعات (من اليمين لليسار في الجريد: col=3 لـ col=0)
                create_info_box(data_grid, 3, "قيمة العملية", row.get('IAMT17', 0), val_color=TEXT_DARK)
                create_info_box(data_grid, 2, "رصيد العملية", abs(float(row.get('IAMT19', 0) or 0)),
                                val_color=FIB_GREEN)
                create_info_box(data_grid, 1, "رصيد متناقص", abs(float(row.get('IAMT20', 0) or 0)), val_color=FIB_GOLD)
                create_info_box(data_grid, 0, "متأخرات", abs(float(row.get('IAMT21', 0) or 0)), val_color="#DC2626")
    def setup_instructions_ui(self, parent):
        import pandas as pd
        import customtkinter as ctk
        from tkinter import messagebox
        import threading
        import logging
        import re

        # =========================================
        # 🎨 1. Premium Theme Colors
        # =========================================
        FIB_GREEN = "#005C34"
        FIB_GOLD = "#C5A059"
        BG_MAIN = "#F8FAFC"
        CARD_BG = "#FFFFFF"
        BOX_BG = "#F1F5F9"
        TEXT_DARK = "#0F172A"
        TEXT_MUTED = "#64748B"

        # حاوية الشاشة الرئيسية
        main_container = ctk.CTkFrame(parent, fg_color=BG_MAIN)
        main_container.pack(fill="both", expand=True)

        # الهيدر العلوي
        header = ctk.CTkFrame(main_container, fg_color=FIB_GREEN, height=65, corner_radius=0)
        header.pack(fill="x")
        header.pack_propagate(False)

        ctk.CTkFrame(main_container, fg_color=FIB_GOLD, height=4, corner_radius=0).pack(fill="x")

        title_lbl = ctk.CTkLabel(
            header,
            text="الاستفسار عن تعليمات عميل 📜",
            font=("Segoe UI", 22, "bold"),
            text_color=CARD_BG
        )
        title_lbl.pack(side="right", padx=30, pady=15)

        # =========================================
        # 🔍 2. Search Area (الفرع ورقم العميل)
        # =========================================
        search_frame = ctk.CTkFrame(
            main_container,
            fg_color=CARD_BG,
            corner_radius=15,
            border_width=1,
            border_color="#E2E8F0"
        )
        search_frame.pack(fill="x", padx=20, pady=15)

        search_inner = ctk.CTkFrame(search_frame, fg_color="transparent")
        search_inner.pack(side="right", fill="y", padx=20, pady=15)

        # --- زر مسح البيانات ---
        btn_clear = ctk.CTkButton(
            search_inner,
            text="🧹 مسح",
            font=("Segoe UI", 14, "bold"),
            fg_color="#64748B",
            hover_color="#475569",
            text_color="white",
            width=90,
            height=40,
            corner_radius=8,
            command=lambda: clear_search()
        )
        btn_clear.pack(side="left", padx=(5, 10))

        # --- زر البحث ---
        btn_search = ctk.CTkButton(
            search_inner,
            text="🔍 بحث",
            font=("Segoe UI", 15, "bold"),
            fg_color=FIB_GREEN,
            hover_color="#004426",
            text_color="white",
            width=110,
            height=40,
            corner_radius=8,
            command=lambda: execute_search()
        )
        btn_search.pack(side="left", padx=5)

        # --- رقم العميل ---
        self.ent_instructions_cust_no = ctk.CTkEntry(
            search_inner,
            font=("Segoe UI", 15, "bold"),
            justify="center",
            placeholder_text="رقم العميل...",
            width=180,
            height=40,
            border_color="#CBD5E1"
        )
        self.ent_instructions_cust_no.pack(side="left", padx=10)

        ctk.CTkLabel(
            search_inner,
            text="رقم العميل:",
            font=("Segoe UI", 14, "bold"),
            text_color=TEXT_DARK
        ).pack(side="left", padx=(10, 2))

        # --- قائمة الفروع ---
        if hasattr(self, '_create_premium_select'):
            self.cmb_instructions_branch_box, self.cmb_instructions_branch = self._create_premium_select(
                search_inner,
                values=["جاري التحميل..."],
                default="جاري التحميل...",
                title="اختر الفرع"
            )
            self.cmb_instructions_branch_box.pack(side="left", padx=10)
        else:
            self.cmb_instructions_branch = ctk.CTkComboBox(
                search_inner,
                font=("Segoe UI", 14, "bold"),
                justify="right",
                width=230,
                height=40,
                border_color="#CBD5E1"
            )
            self.cmb_instructions_branch.pack(side="left", padx=10)

        ctk.CTkLabel(
            search_inner,
            text="الفرع:",
            font=("Segoe UI", 14, "bold"),
            text_color=TEXT_DARK
        ).pack(side="left", padx=(10, 2))

        # شريط ملخص النتائج / العداد (مثل التوكيلات)
        self.instructions_summary_lbl = ctk.CTkLabel(main_container, text="", font=("Segoe UI", 13, "bold"),
                                                     text_color=TEXT_MUTED)
        self.instructions_summary_lbl.pack(anchor="e", padx=25, pady=(0, 5))

        # تعبئة الفروع تلقائياً
        def load_branches_to_combo():
            if hasattr(self, 'branch_mapping') and self.branch_mapping:
                branches = list(self.branch_mapping.keys())
                self.cmb_instructions_branch.configure(values=branches)
                self.cmb_instructions_branch.set(branches[0])
            else:
                if hasattr(self, 'nuwairy_load_branches'):
                    self.nuwairy_load_branches()
                self.after(500, load_branches_to_combo)

        load_branches_to_combo()

        # ربط زر الـ Enter بالبحث
        self.ent_instructions_cust_no.bind("<Return>", lambda event: execute_search())

        # =========================================
        # 📜 3. Results Area (كروت التعليمات)
        # =========================================
        self.instructions_results_scroll = ctk.CTkScrollableFrame(main_container, fg_color="transparent")
        self.instructions_results_scroll.pack(fill="both", expand=True, padx=15, pady=(0, 20))

        # --- دالة تنظيف اسم العميل فقط ---
        def clean_arabic_name(raw_name):
            if pd.isna(raw_name) or not str(raw_name).strip():
                return "غير مسجل"
            text = str(raw_name).strip()
            text = re.sub(r'^\d+', '', text).strip()
            text = re.sub(r'\s+(يه|ية|ه|ة)\b', r'\1', text)
            previous_text = ""
            while text != previous_text:
                previous_text = text
                text = re.sub(r'([ةىء])([\u0621-\u064A])', r'\1 \2', text)
                text = re.sub(r'([\u0621-\u064A]{2,})((?:ب|ك|ف|و)?ال[\u0621-\u064A]{2,})', r'\1 \2', text)
                for p in ['عبد', 'ابو', 'أبو', 'ام', 'أم', 'بن', 'بنت', 'ذو', 'ذي']:
                    text = re.sub(f'(?<![\u0621-\u064A])({p})(?=[\u0621-\u064A])', r'\1 ', text)
                for s in ['الدين', 'مخمد', 'الله', 'الاسلام', 'الإسلام', 'الحق']:
                    text = re.sub(f'(?<=[\u0621-\u064A])({s})(?![\u0621-\u064A])', r' \1', text)
                text = re.sub(r'\s+', ' ', text).strip()
            return text

        # --- دالة تنسيق التاريخ ---
        def format_date_str(raw_date):
            if pd.isna(raw_date) or not str(raw_date).strip():
                return "—"
            d_str = str(raw_date).split()[0].split('.')[0].strip()
            if len(d_str) == 8 and d_str.isdigit():
                return f"{d_str[:4]}-{d_str[4:6]}-{d_str[6:]}"
            return d_str

        def clear_search():
            self.ent_instructions_cust_no.delete(0, 'end')
            self.instructions_summary_lbl.configure(text="")
            for widget in self.instructions_results_scroll.winfo_children():
                widget.destroy()

        # =========================================
        # ⚙️ 4. Search Engine Logic
        # =========================================
        def execute_search():
            branch_name = self.cmb_instructions_branch.get().strip()
            cust_no = self.ent_instructions_cust_no.get().strip()

            if not cust_no:
                messagebox.showwarning("تنبيه", "يرجى إدخال رقم العميل أولاً")
                self.ent_instructions_cust_no.focus()
                return

            # التحقق بنفس طريقة التوكيلات تماماً
            if not hasattr(self, 'branch_mapping') or branch_name not in self.branch_mapping:
                messagebox.showerror("خطأ", "برجاء اختيار فرع صحيح")
                return

            # جلب كود الفرع فقط من الـ mapping (لغينا محاولة جلب اسم الجدول من هنا)
            branch_info = self.branch_mapping[branch_name]
            branch_code = branch_info[0] if isinstance(branch_info, (tuple, list)) else branch_info

            for widget in self.instructions_results_scroll.winfo_children():
                widget.destroy()

            self.instructions_summary_lbl.configure(text="")
            lbl_loading = ctk.CTkLabel(
                self.instructions_results_scroll,
                text="⚡ جاري البحث عن تعليمات العميل...",
                font=("Segoe UI", 16, "bold"),
                text_color=FIB_GOLD
            )
            lbl_loading.pack(pady=50)

            def fetch_data():
                try:
                    engine = getattr(self, '_get_db_connection', lambda: None)()
                    if not engine:
                        raise Exception("لم يتم العثور على دالة الاتصال بقاعدة البيانات.")

                    # --- التعديل الجديد: جلب اسم الجدول من TBL_Branches ---
                    target_table = None
                    try:
                        # افترضنا هنا إن اسم حقل كود الفرع في الجدول هو BranchCode، راجع الاسم لو مختلف عندك
                        branch_query = f"SELECT TableName FROM [dbo].[TBL_Branches] WITH (NOLOCK) WHERE BranchCode = N'{branch_code}'"
                        branch_df = pd.read_sql(branch_query, engine)
                        if not branch_df.empty and pd.notna(branch_df.iloc[0]['TableName']):
                            target_table = str(branch_df.iloc[0]['TableName']).strip()
                    except Exception as b_err:
                        print(f"DEBUG Error fetching TableName from TBL_Branches: {b_err}")
                        logging.error(f"Error fetching TableName from TBL_Branches: {b_err}")
                    # --------------------------------------------------------

                    # 1. جلب اسم العميل مع طباعة أسباب عدم الظهور للتشخيص
                    fetched_client_name = "غير مسجل"

                    print(
                        f"DEBUG: target_table = '{target_table}', branch_code = '{branch_code}', cust_no = '{cust_no}'")

                    if target_table and pd.notna(target_table) and str(target_table).strip():
                        try:
                            tbl_str = str(target_table).strip()

                            # استعلام مرن يتعامل مع الأرقام سواء بأصفار على الشمال أو بدونها
                            client_query = f"""
                                SELECT TOP 1 BNAME 
                                FROM [dbo].[{tbl_str}] WITH (NOLOCK) 
                                WHERE LTRIM(RTRIM(BCLNT)) = N'{cust_no}' 
                                   OR TRY_CAST(BCLNT AS INT) = TRY_CAST(N'{cust_no}' AS INT)
                            """
                            client_df = pd.read_sql(client_query, engine)

                            if not client_df.empty:
                                raw_bname = client_df.iloc[0].get('BNAME')
                                print(f"DEBUG: Found Raw BNAME from DB = '{raw_bname}'")
                                if pd.notna(raw_bname) and str(raw_bname).strip():
                                    fetched_client_name = str(raw_bname).strip()
                            else:
                                print(f"DEBUG: No rows returned from [{tbl_str}] for cust_no '{cust_no}'")

                        except Exception as cl_err:
                            print(f"DEBUG Error in client_query: {cl_err}")
                            logging.warning(f"Could not fetch client name: {cl_err}")
                    else:
                        print(f"DEBUG: target_table is EMPTY or NONE for branch '{branch_name}'.")

                    # 2. الاستعلام الرئيسي المباشر من جدول تعليمات الحسابات
                    sql = f"""
                        SELECT tmm, tnm1, tnm2, tdat, tmh
                        FROM [dbo].[tbl_instructionsBankAccounts] WITH (NOLOCK)
                        WHERE (nbr = N'{branch_code}' OR tbr = N'{branch_code}') 
                          AND (nclnt = N'{cust_no}' OR tclnt = N'{cust_no}')
                    """
                    df = pd.read_sql(sql, engine)

                    self.after(0, lambda: update_results_ui(df, fetched_client_name, cust_no, branch_name))
                except Exception as e:
                    logging.error(f"Error fetching instructions: {e}")
                    self.after(0, lambda: update_results_ui(pd.DataFrame(), "غير مسجل", cust_no, branch_name,
                                                            error=str(e)))

            threading.Thread(target=fetch_data, daemon=True).start()

        def update_results_ui(df, client_name, cust_no, branch_name, error=None):
            for widget in self.instructions_results_scroll.winfo_children():
                widget.destroy()

            if error:
                self.instructions_summary_lbl.configure(text="")
                ctk.CTkLabel(
                    self.instructions_results_scroll,
                    text=f"❌ حدث خطأ أثناء البحث:\n{error}",
                    font=("Segoe UI", 14, "bold"),
                    text_color="#EF4444"
                ).pack(pady=40)
                return

            if df.empty:
                self.instructions_summary_lbl.configure(text="")
                ctk.CTkLabel(
                    self.instructions_results_scroll,
                    text="🔍 لا توجد تعليمات مسجلة لهذا العميل في هذا الفرع",
                    font=("Segoe UI", 18, "bold"),
                    text_color=TEXT_MUTED
                ).pack(pady=60)
                return

            # تحديث عداد النتائج
            self.instructions_summary_lbl.configure(text=f"إجمالي عدد التعليمات المضبوطة: {len(df)}")

            # تنظيف اسم العميل للعرض في أعلى النتائج
            cleaned_client_name = clean_arabic_name(client_name)

            # =========================================
            # 👤 1. كارت بيانات العميل الرئيسي
            # =========================================
            client_header_card = ctk.CTkFrame(
                self.instructions_results_scroll,
                fg_color=CARD_BG,
                corner_radius=12,
                border_width=1,
                border_color="#CBD5E1"
            )
            client_header_card.pack(fill="x", padx=10, pady=(5, 15))

            client_inner = ctk.CTkFrame(client_header_card, fg_color="transparent")
            client_inner.pack(fill="x", padx=20, pady=12)

            ctk.CTkLabel(
                client_inner,
                text=f"👤 اسم العميل: {cleaned_client_name}",
                font=("Segoe UI", 16, "bold"),
                text_color=FIB_GREEN
            ).pack(side="right")

            ctk.CTkLabel(
                client_inner,
                text=f"الفرع: {branch_name} | رقم العميل: {cust_no}",
                font=("Segoe UI", 13, "bold"),
                text_color=TEXT_MUTED,
                fg_color=BOX_BG,
                corner_radius=6
            ).pack(side="left", ipadx=10, ipady=3)

            # =========================================
            # 📑 2. إنشاء كارت لكل تعليمات
            # =========================================
            for _, row in df.iterrows():
                instruction_serial = str(row['tmm']).replace('.0', '') if pd.notna(row['tmm']) else "—"
                text1 = str(row['tnm1']).strip() if pd.notna(row['tnm1']) else ""
                text2 = str(row['tnm2']).strip() if pd.notna(row['tnm2']) else ""
                trans_date = format_date_str(row['tdat'])

                # كود الإلغاء tmh (1 = ملغي, 0 = ساري)
                tmh_val = str(row['tmh']).replace('.0', '').strip() if pd.notna(row['tmh']) else ""

                if tmh_val == '1':
                    status_text = "1"
                    status_color = "#DC2626"
                    status_bg = "#FEE2E2"
                elif tmh_val == '0':
                    status_text = "0"
                    status_color = "#005C34"
                    status_bg = "#DCFCE7"
                else:
                    status_text = f"غير محدد ({tmh_val})" if tmh_val else "غير محدد"
                    status_color = TEXT_MUTED
                    status_bg = BOX_BG

                card = ctk.CTkFrame(
                    self.instructions_results_scroll,
                    fg_color=CARD_BG,
                    corner_radius=12,
                    border_width=1,
                    border_color="#E2E8F0"
                )
                card.pack(fill="x", padx=10, pady=8)

                # شريط ملون جانبي يعبر عن الحالة
                stripe_color = status_color if tmh_val in ['0', '1'] else FIB_GOLD
                ctk.CTkFrame(card, fg_color=stripe_color, width=6, corner_radius=0).pack(side="right", fill="y",
                                                                                         pady=10)

                card_content = ctk.CTkFrame(card, fg_color="transparent")
                card_content.pack(fill="both", expand=True, padx=20, pady=12)

                # صف العنوان (مسلسل التعليمات والحالة)
                header_row = ctk.CTkFrame(card_content, fg_color="transparent")
                header_row.pack(fill="x", pady=(0, 8))

                ctk.CTkLabel(
                    header_row,
                    text=f"مسلسل التعليمات: {instruction_serial} 📜",
                    font=("Segoe UI", 16, "bold"),
                    text_color=TEXT_DARK
                ).pack(side="right")

                ctk.CTkLabel(
                    header_row,
                    text=f"كود الالغاء: {status_text}",
                    font=("Segoe UI", 13, "bold"),
                    text_color=status_color,
                    fg_color=status_bg,
                    corner_radius=6
                ).pack(side="left", ipadx=8, ipady=2)

                # صندوق نصوص التعليمات (tnm1 & tnm2)
                text_container = ctk.CTkFrame(
                    card_content,
                    fg_color=BOX_BG,
                    corner_radius=8,
                    border_width=1,
                    border_color="#E2E8F0"
                )
                text_container.pack(fill="x", pady=8, ipady=6)

                if text1:
                    ctk.CTkLabel(
                        text_container,
                        text=text1,
                        font=("Segoe UI", 14, "bold"),
                        text_color=TEXT_DARK,
                        justify="right",
                        anchor="e",
                        wraplength=750
                    ).pack(fill="x", padx=15, pady=(8, 4))

                if text2:
                    ctk.CTkLabel(
                        text_container,
                        text=text2,
                        font=("Segoe UI", 13),
                        text_color="#334155",
                        justify="right",
                        anchor="e",
                        wraplength=750
                    ).pack(fill="x", padx=15, pady=(2, 8))

                # صف تاريخ الحركة
                footer_row = ctk.CTkFrame(card_content, fg_color="transparent")
                footer_row.pack(fill="x", pady=(4, 0))

                ctk.CTkLabel(
                    footer_row,
                    text=f"تاريخ الحركة م: {trans_date} 📅",
                    font=("Segoe UI", 13, "bold"),
                    text_color=FIB_GREEN,
                    fg_color=BOX_BG,
                    corner_radius=6
                ).pack(side="left", ipadx=10, ipady=2)
    def setup_mandates_ui(self, parent):
        import pandas as pd
        import customtkinter as ctk
        from tkinter import messagebox
        import threading
        import logging
        import re

        # =========================================
        # 🎨 1. Premium Theme Colors
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

        title_lbl = ctk.CTkLabel(header, text="الاستفسار عن التوكيلات برقم العميل", font=("Segoe UI", 22, "bold"),
                                 text_color=CARD_BG)
        title_lbl.pack(side="right", padx=30, pady=15)

        # =========================================
        # 🔍 2. Search Area
        # =========================================
        search_frame = ctk.CTkFrame(main_container, fg_color=CARD_BG, corner_radius=15, border_width=1,
                                    border_color="#E2E8F0")
        search_frame.pack(fill="x", padx=20, pady=20)

        search_inner = ctk.CTkFrame(search_frame, fg_color="transparent")
        search_inner.pack(side="right", fill="y", padx=20, pady=15)

        btn_search = ctk.CTkButton(search_inner, text="🔍 بحث", font=("Segoe UI", 15, "bold"),
                                   fg_color=FIB_GREEN, hover_color="#004426", text_color="white",
                                   width=120, height=40, corner_radius=8, command=lambda: execute_search())
        btn_search.pack(side="left", padx=10)

        self.ent_mandates_cust_no = ctk.CTkEntry(search_inner, font=("Segoe UI", 15, "bold"),
                                                 justify="center", placeholder_text="رقم العميل...",
                                                 width=200, height=40, border_color="#CBD5E1")
        self.ent_mandates_cust_no.pack(side="left", padx=10)

        ctk.CTkLabel(search_inner, text="رقم العميل:", font=("Segoe UI", 14, "bold"), text_color=TEXT_DARK).pack(
            side="left", padx=(10, 2))

        if hasattr(self, '_create_premium_select'):
            self.cmb_mandates_branch_box, self.cmb_mandates_branch = self._create_premium_select(
                search_inner,
                values=["جاري التحميل..."],
                default="جاري التحميل...",
                title="اختر الفرع"
            )
            self.cmb_mandates_branch_box.pack(side="left", padx=10)
        else:
            self.cmb_mandates_branch = ctk.CTkComboBox(search_inner, font=("Segoe UI", 14, "bold"), justify="right",
                                                       width=250, height=40, border_color="#CBD5E1")
            self.cmb_mandates_branch.pack(side="left", padx=10)

        ctk.CTkLabel(search_inner, text="الفرع:", font=("Segoe UI", 14, "bold"), text_color=TEXT_DARK).pack(side="left",
                                                                                                            padx=(10,
                                                                                                                  2))

        def load_branches_to_combo():
            if hasattr(self, 'branch_mapping') and self.branch_mapping:
                branches = list(self.branch_mapping.keys())
                self.cmb_mandates_branch.configure(values=branches)
                self.cmb_mandates_branch.set(branches[0])
            else:
                if hasattr(self, 'nuwairy_load_branches'):
                    self.nuwairy_load_branches()
                self.after(500, load_branches_to_combo)

        load_branches_to_combo()
        self.ent_mandates_cust_no.bind("<Return>", lambda event: execute_search())

        # =========================================
        # 📜 3. Results Area
        # =========================================
        self.mandates_results_scroll = ctk.CTkScrollableFrame(main_container, fg_color="transparent")
        self.mandates_results_scroll.pack(fill="both", expand=True, padx=15, pady=(0, 20))

        # --- دالة تنظيف النصوص والأسماء ---
        def clean_arabic_name(raw_name):
            if pd.isna(raw_name) or not str(raw_name).strip():
                return "غير مسجل"
            text = str(raw_name).strip()
            # إزالة أي أرقام مسجلة في بداية الاسم (مثل 300083)
            text = re.sub(r'^\d+', '', text).strip()
            text = re.sub(r'\s+(يه|ية|ه|ة)\b', r'\1', text)
            previous_text = ""
            while text != previous_text:
                previous_text = text
                text = re.sub(r'([ةىء])([\u0621-\u064A])', r'\1 \2', text)
                text = re.sub(r'([\u0621-\u064A]{2,})((?:ب|ك|ف|و)?ال[\u0621-\u064A]{2,})', r'\1 \2', text)
                for p in ['عبد', 'ابو', 'أبو', 'ام', 'أم', 'بن', 'بنت', 'ذو', 'ذي']:
                    text = re.sub(f'(?<![\u0621-\u064A])({p})(?=[\u0621-\u064A])', r'\1 ', text)
                for s in ['الدين', 'مخمد', 'الله', 'الاسلام', 'الإسلام', 'الحق']:
                    text = re.sub(f'(?<=[\u0621-\u064A])({s})(?![\u0621-\u064A])', r' \1', text)
                text = re.sub(r'\s+', ' ', text).strip()
            return text

        # --- دالة تنسيق التاريخ من YYYYMMDD إلى YYYY-MM-DD ---
        def format_date_str(raw_date):
            if pd.isna(raw_date) or not str(raw_date).strip():
                return "—"
            d_str = str(raw_date).split()[0].split('.')[0].strip()
            if len(d_str) == 8 and d_str.isdigit():
                return f"{d_str[:4]}-{d_str[4:6]}-{d_str[6:]}"
            return d_str

        # =========================================
        # ⚙️ 4. Search Engine Logic
        # =========================================
        def execute_search():
            branch_name = self.cmb_mandates_branch.get()
            cust_no = self.ent_mandates_cust_no.get().strip()

            if not cust_no:
                messagebox.showwarning("تنبيه", "يرجى إدخال رقم العميل أولاً")
                self.ent_mandates_cust_no.focus()
                return

            if not hasattr(self, 'branch_mapping') or branch_name not in self.branch_mapping:
                messagebox.showerror("خطأ", "برجاء اختيار فرع صحيح")
                return

            branch_info = self.branch_mapping[branch_name]
            branch_code = branch_info[0] if isinstance(branch_info, tuple) else branch_info

            for widget in self.mandates_results_scroll.winfo_children():
                widget.destroy()

            lbl_loading = ctk.CTkLabel(self.mandates_results_scroll, text="⚡ جاري البحث عن التوكيلات...",
                                       font=("Segoe UI", 16, "bold"), text_color=FIB_GOLD)
            lbl_loading.pack(pady=50)

            def fetch_data():
                try:
                    engine = getattr(self, '_get_db_connection', lambda: None)()
                    if not engine:
                        raise Exception("لم يتم العثور على دالة الاتصال بقاعدة البيانات.")

                    # 1. جلب اسم الجدول الخاص بالفرع
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
                    sql = f"""
                        SELECT sname, sdatt, stknum, SEE
                        FROM [dbo].[tbl_BAMandates] WITH (NOLOCK)
                        WHERE SBR = N'{branch_code}' 
                          AND sclnt = N'{cust_no}'
                    """
                    df = pd.read_sql(sql, engine)

                    self.after(0, lambda: update_results_ui(df, fetched_client_name, cust_no, branch_name))
                except Exception as e:
                    logging.error(f"Error fetching mandates: {e}")
                    self.after(0, lambda: update_results_ui(pd.DataFrame(), "غير مسجل", cust_no, branch_name,
                                                            error=str(e)))

            threading.Thread(target=fetch_data, daemon=True).start()

        def update_results_ui(df, client_name, cust_no, branch_name, error=None):
            for widget in self.mandates_results_scroll.winfo_children():
                widget.destroy()

            if error:
                ctk.CTkLabel(self.mandates_results_scroll, text=f"❌ حدث خطأ أثناء البحث:\n{error}",
                             font=("Segoe UI", 14, "bold"), text_color="#EF4444").pack(pady=40)
                return

            if df.empty:
                ctk.CTkLabel(self.mandates_results_scroll, text="🔍 لا توجد توكيلات مسجلة لهذا العميل في هذا الفرع",
                             font=("Segoe UI", 18, "bold"), text_color=TEXT_MUTED).pack(pady=60)
                return

            cleaned_client_name = clean_arabic_name(client_name)

            # =========================================
            # 👤 1. كارت بيانات العميل الرئيسي (مرة واحدة بالفيو)
            # =========================================
            client_header_card = ctk.CTkFrame(self.mandates_results_scroll, fg_color=CARD_BG, corner_radius=12,
                                              border_width=1, border_color="#CBD5E1")
            client_header_card.pack(fill="x", padx=10, pady=(5, 15))

            client_inner = ctk.CTkFrame(client_header_card, fg_color="transparent")
            client_inner.pack(fill="x", padx=20, pady=12)

            # اسم العميل ورقم الحساب
            ctk.CTkLabel(client_inner, text=f"👤 اسم العميل: {cleaned_client_name}", font=("Segoe UI", 16, "bold"),
                         text_color=FIB_GREEN).pack(side="right")

            ctk.CTkLabel(client_inner, text=f"الفرع: {branch_name} | رقم العميل: {cust_no}",
                         font=("Segoe UI", 13, "bold"),
                         text_color=TEXT_MUTED, fg_color=BOX_BG, corner_radius=6).pack(side="left", ipadx=10, ipady=3)

            # =========================================
            # 📑 2. كروت التوكيلات الخاصة بالعميل
            # =========================================
            for _, row in df.iterrows():
                agent_name = clean_arabic_name(row['sname'])
                mandate_num = str(row['stknum']).replace('.0', '') if pd.notna(row['stknum']) else "—"
                mandate_date = format_date_str(row['sdatt'])

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

                card = ctk.CTkFrame(self.mandates_results_scroll, fg_color=CARD_BG, corner_radius=12,
                                    border_width=1, border_color="#E2E8F0")
                card.pack(fill="x", padx=10, pady=8)

                stripe_color = status_color if see_val in ['0', '1'] else FIB_GOLD
                ctk.CTkFrame(card, fg_color=stripe_color, width=5, corner_radius=0).pack(side="right", fill="y",
                                                                                         pady=10)

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
                             text_color=FIB_GREEN, fg_color=BOX_BG, corner_radius=6).pack(side="left", ipadx=10,
                                                                                          ipady=2)
    def stopped_cheques_fetch_data(self):
        """جلب بيانات الشيكات الموقوفة بسرعة فائقة وتطبيق الـ Regex على الاسم"""
        branch_val = self.cmb_stopped_branch.get().strip()
        acc_num = self.ent_stopped_acc.get().strip()

        if not branch_val or branch_val in ["جاري التحميل...", "- اختر الفرع -", "- لا توجد فروع -"]:
            # تنبيه باختيار الفرع
            return

        if not acc_num:
            # تنبيه بإدخال رقم الحساب
            return

        # استخراج كود الفرع من النص (على فرض المبدأ: "001 - اسم الفرع")
        branch_code = branch_val.split(" - ")[0].strip() if " - " in branch_val else branch_val

        # تشغيل البحث في Thread منفصل لعدم تجميد الواجهة
        def _background_search():
            try:
                # افتح اتصالك بالداتا بيز (استخدم طريقة الاتصال المعتمدة لديك)
                conn = self.get_db_connection()
                cursor = conn.cursor()

                # Query سريع جداً مع NOLOCK و N Prefix
                sql_query = f"""
                    SELECT 
                        ISNULL(c.BCHNO, '') AS BCHNO,
                        ISNULL(c.BDAT, '') AS BDAT,
                        ISNULL(c.BDAT1, '') AS BDAT1,
                        ISNULL(c.BCOD, '') AS BCOD,
                        ISNULL(cl.BNAME, N'غير محدد') AS BNAME
                    FROM [FIBTest].[dbo].[TBL_cheques] c WITH (NOLOCK)
                    LEFT JOIN [FIBTest].[dbo].[TBL_client_name] cl WITH (NOLOCK)
                        ON c.BCLNT = cl.BCLNT
                    WHERE c.BCHBR = N'{branch_code}' 
                      AND c.BCLNT = N'{acc_num}'
                """

                cursor.execute(sql_query)
                rows = cursor.fetchall()
                conn.close()

                formatted_data = []
                for row in rows:
                    bchno = str(row[0]).strip()
                    bdat = str(row[1]).strip()
                    bdat1 = str(row[2]).strip()
                    bcod = str(row[3]).strip()
                    raw_bname = str(row[4]).strip()

                    # --- تطهير وتنظيف الاسم بالـ Regex ---
                    # إزالة الأرقام والرموز والمسافات الزائدة والحفاظ على الحروف العربية فقط
                    clean_bname = re.sub(r'[^\u0600-\u06FF\s]', '', raw_bname)
                    clean_bname = re.sub(r'\s+', ' ', clean_bname).strip()
                    if not clean_bname:
                        clean_bname = raw_bname

                    # ترتيب الصف للجدول: [رقم الشيك, تاريخ الإيقاف, تاريخ الإلغاء, كود الإيقاف, اسم العميل]
                    formatted_data.append([bchno, bdat, bdat1, bcod, clean_bname])

                # تحديث الـ tksheet في الواجهة الرئيسية
                self.after(0, lambda: self._update_stopped_sheet(formatted_data))

            except Exception as e:
                print(f"Error fetching stopped cheques: {e}")

        threading.Thread(target=_background_search, daemon=True).start()

    def _update_stopped_sheet(self, data):
        """تحديث جدول الشيكات الموقوفة"""
        if hasattr(self, 'stopped_sheet'):
            try:
                self.stopped_sheet.set_sheet_data(data, reset_col_positions=False, reset_row_positions=True)
            except Exception as e:
                print(f"Sheet update error: {e}")

    def setup_stopped_cheques_ui(self, parent):
        import pandas as pd
        import customtkinter as ctk
        from tkinter import messagebox
        import threading
        import logging

        # =========================================
        # 🎨 1. Premium Theme Colors
        # =========================================
        FIB_GREEN = "#005C34"
        FIB_GOLD = "#C5A059"
        BG_MAIN = "#F8FAFC"
        CARD_BG = "#FFFFFF"
        BOX_BG = "#F1F5F9"
        TEXT_DARK = "#0F172A"
        TEXT_MUTED = "#64748B"
        STOP_COLOR = "#B45309"  # لون برتقالي/بني مميز للموقوفة

        # حاوية الشاشة الرئيسية
        main_container = ctk.CTkFrame(parent, fg_color=BG_MAIN)
        main_container.pack(fill="both", expand=True)

        # الهيدر العلوي
        header = ctk.CTkFrame(main_container, fg_color=FIB_GREEN, height=65, corner_radius=0)
        header.pack(fill="x")
        header.pack_propagate(False)

        ctk.CTkFrame(main_container, fg_color=FIB_GOLD, height=4, corner_radius=0).pack(fill="x")

        title_lbl = ctk.CTkLabel(header, text="استعلام الشيكات الموقوفة", font=("Segoe UI", 22, "bold"),
                                 text_color=CARD_BG)
        title_lbl.pack(side="right", padx=30, pady=15)

        # =========================================
        # 🔍 2. Search Area (الفرع ورقم الحساب)
        # =========================================
        search_frame = ctk.CTkFrame(main_container, fg_color=CARD_BG, corner_radius=15, border_width=1,
                                    border_color="#E2E8F0")
        search_frame.pack(fill="x", padx=20, pady=20)

        search_inner = ctk.CTkFrame(search_frame, fg_color="transparent")
        search_inner.pack(side="right", fill="y", padx=20, pady=15)

        # --- زر البحث ---
        btn_search = ctk.CTkButton(search_inner, text="🔍 بحث", font=("Segoe UI", 15, "bold"),
                                   fg_color=FIB_GREEN, hover_color="#004426", text_color="white",
                                   width=120, height=40, corner_radius=8, command=lambda: execute_search())
        btn_search.pack(side="left", padx=10)

        # --- رقم الحساب ---
        self.ent_stopped_acc = ctk.CTkEntry(search_inner, font=("Segoe UI", 15, "bold"),
                                            justify="center", placeholder_text="رقم الحساب...",
                                            width=200, height=40, border_color="#CBD5E1")
        self.ent_stopped_acc.pack(side="left", padx=10)

        ctk.CTkLabel(search_inner, text="رقم الحساب:", font=("Segoe UI", 14, "bold"), text_color=TEXT_DARK).pack(
            side="left", padx=(10, 2))

        # --- قائمة الفروع ---
        if hasattr(self, '_create_premium_select'):
            self.cmb_stopped_branch_box, self.cmb_stopped_branch = self._create_premium_select(
                search_inner,
                values=["جاري التحميل..."],
                default="جاري التحميل...",
                title="اختر الفرع"
            )
            self.cmb_stopped_branch_box.pack(side="left", padx=10)
        else:
            self.cmb_stopped_branch = ctk.CTkComboBox(search_inner, font=("Segoe UI", 14, "bold"), justify="right",
                                                      width=250, height=40, border_color="#CBD5E1")
            self.cmb_stopped_branch.pack(side="left", padx=10)

        ctk.CTkLabel(search_inner, text="الفرع:", font=("Segoe UI", 14, "bold"), text_color=TEXT_DARK).pack(side="left",
                                                                                                            padx=(10,
                                                                                                                  2))

        # 🔥 الحل الجذري لمشكلة عدم تحميل الفروع:
        def load_branches_to_combo():
            if hasattr(self, 'branch_mapping') and self.branch_mapping:
                # لو الفروع اتحملت، نعرضها فوراً
                branches = list(self.branch_mapping.keys())
                self.cmb_stopped_branch.configure(values=branches)
                self.cmb_stopped_branch.set(branches[0])
            else:
                # لو لسة، نطلب تحميلها ونشغل الدالة دي تاني بعد نص ثانية (500ms) تتأكد
                if hasattr(self, 'nuwairy_load_branches'):
                    self.nuwairy_load_branches()
                self.after(500, load_branches_to_combo)

        # استدعاء تعبئة الفروع
        load_branches_to_combo()

        # ربط زر الـ Enter بالبحث
        self.ent_stopped_acc.bind("<Return>", lambda event: execute_search())

        # =========================================
        # 📜 3. Results Area (كروت الشيكات)
        # =========================================
        self.stopped_results_scroll = ctk.CTkScrollableFrame(main_container, fg_color="transparent")
        self.stopped_results_scroll.pack(fill="both", expand=True, padx=15, pady=(0, 20))

        def fix_arabic_name(raw_name):
            import re
            if pd.isna(raw_name) or not str(raw_name).strip():
                return "غير مسجل"
            text = str(raw_name).strip()
            text = re.sub(r'\s+(يه|ية|ه|ة)\b', r'\1', text)
            previous_text = ""
            while text != previous_text:
                previous_text = text
                text = re.sub(r'([ةىء])([\u0621-\u064A])', r'\1 \2', text)
                text = re.sub(r'([\u0621-\u064A]{2,})((?:ب|ك|ف|و)?ال[\u0621-\u064A]{2,})', r'\1 \2', text)
                for p in ['عبد', 'ابو', 'أبو', 'ام', 'أم', 'بن', 'بنت', 'ذو', 'ذي']:
                    text = re.sub(f'(?<![\u0621-\u064A])({p})(?=[\u0621-\u064A])', r'\1 ', text)
                for s in ['الدين', 'مخمد', 'الله', 'الاسلام', 'الإسلام', 'الحق']:
                    text = re.sub(f'(?<=[\u0621-\u064A])({s})(?![\u0621-\u064A])', r' \1', text)
                text = re.sub(r'\s+', ' ', text).strip()
            return text

        # =========================================
        # ⚙️ 4. Search Engine Logic
        # =========================================
        def execute_search():
            branch_name = self.cmb_stopped_branch.get()
            acc_num = self.ent_stopped_acc.get().strip()

            if not acc_num:
                messagebox.showwarning("تنبيه", "يرجى إدخال رقم الحساب أولاً")
                self.ent_stopped_acc.focus()
                return

            if not hasattr(self, 'branch_mapping') or branch_name not in self.branch_mapping:
                messagebox.showerror("خطأ", "برجاء اختيار فرع صحيح")
                return

            branch_code = self.branch_mapping[branch_name]

            for widget in self.stopped_results_scroll.winfo_children():
                widget.destroy()

            lbl_loading = ctk.CTkLabel(self.stopped_results_scroll, text="⚡ جاري البحث في قاعدة البيانات...",
                                       font=("Segoe UI", 16, "bold"), text_color=FIB_GOLD)
            lbl_loading.pack(pady=50)

            def fetch_data():
                try:
                    engine = getattr(self, '_get_db_connection', lambda: None)()
                    if not engine:
                        raise Exception("لم يتم العثور على دالة الاتصال بقاعدة البيانات.")

                    # الكويري السريع المخصص للشيكات الموقوفة
                    sql = f"""
                            SELECT 
                                c.BCHNO, c.BDAT, c.BDAT1, c.BCOD,
                                cl.BNAME
                            FROM [dbo].[TBL_cheques] AS c WITH (NOLOCK)
                            LEFT JOIN [dbo].[TBL_client_name] AS cl WITH (NOLOCK) 
                                ON c.BCLNT = cl.BCLNT
                            WHERE c.BCHBR = N'{branch_code}' AND c.BCLNT = N'{acc_num}'
                        """
                    df = pd.read_sql(sql, engine)

                    self.after(0, lambda: update_results_ui(df))
                except Exception as e:
                    logging.error(f"Error fetching stopped cheques: {e}")
                    self.after(0, lambda: update_results_ui(pd.DataFrame(), error=str(e)))

            threading.Thread(target=fetch_data, daemon=True).start()

        def update_results_ui(df, error=None):
            for widget in self.stopped_results_scroll.winfo_children():
                widget.destroy()

            if error:
                ctk.CTkLabel(self.stopped_results_scroll, text=f"❌ حدث خطأ أثناء البحث:\n{error}",
                             font=("Segoe UI", 14, "bold"), text_color="#EF4444").pack(pady=40)
                return

            if df.empty:
                ctk.CTkLabel(self.stopped_results_scroll, text="🔍 لا توجد شيكات موقوفة لهذا الحساب في هذا الفرع",
                             font=("Segoe UI", 18, "bold"), text_color=TEXT_MUTED).pack(pady=60)
                return

            # إنشاء كارت مخصص لكل شيك
            for _, row in df.iterrows():
                chq_no = str(row['BCHNO']).replace('.0', '') if pd.notna(row['BCHNO']) else "غير معروف"
                stop_code = str(row['BCOD']).replace('.0', '') if pd.notna(row['BCOD']) else "—"
                cust_name = fix_arabic_name(row['BNAME'])

                stop_date = str(row['BDAT']).split()[0] if pd.notna(row['BDAT']) and str(row['BDAT']).strip() else "—"
                cancel_date = str(row['BDAT1']).split()[0] if pd.notna(row['BDAT1']) and str(
                    row['BDAT1']).strip() else "—"

                card = ctk.CTkFrame(self.stopped_results_scroll, fg_color=CARD_BG, corner_radius=12,
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

                def create_info_box(parent, row_idx, col_idx, title, value, val_color=TEXT_DARK):
                    box = ctk.CTkFrame(parent, fg_color=BOX_BG, corner_radius=8)
                    box.grid(row=row_idx, column=col_idx, padx=5, pady=5, sticky="ew")
                    ctk.CTkLabel(box, text=title, font=("Segoe UI", 12, "bold"), text_color=TEXT_MUTED).pack(
                        anchor="center", pady=(5, 0))
                    ctk.CTkLabel(box, text=value, font=("Segoe UI", 15, "bold"), text_color=val_color).pack(
                        anchor="center", pady=(0, 5))

                create_info_box(data_grid, 0, 1, "تاريخ الإيقاف", stop_date, val_color=STOP_COLOR)
                create_info_box(data_grid, 0, 0, "تاريخ الإلغاء", cancel_date, val_color=FIB_GREEN)
    def setup_rejected_cheques_ui(self, parent):

        # =========================================
        # 🎨 1. Premium Theme Colors
        # =========================================
        FIB_GREEN = "#005C34"
        FIB_GOLD = "#C5A059"
        BG_MAIN = "#F8FAFC"
        CARD_BG = "#FFFFFF"
        BOX_BG = "#F1F5F9"
        TEXT_DARK = "#0F172A"
        TEXT_MUTED = "#64748B"

        # حاوية الشاشة الرئيسية
        main_container = ctk.CTkFrame(parent, fg_color=BG_MAIN)
        main_container.pack(fill="both", expand=True)

        # الهيدر العلوي
        header = ctk.CTkFrame(main_container, fg_color=FIB_GREEN, height=65, corner_radius=0)
        header.pack(fill="x")
        header.pack_propagate(False)

        ctk.CTkFrame(main_container, fg_color=FIB_GOLD, height=4, corner_radius=0).pack(fill="x")

        title_lbl = ctk.CTkLabel(header, text="استعلام الشيكات المرفوضة", font=("Segoe UI", 22, "bold"),
                                 text_color=CARD_BG)
        title_lbl.pack(side="right", padx=30, pady=15)

        # =========================================
        # 🔍 2. Search Area (الفرع ورقم الحساب)
        # =========================================
        search_frame = ctk.CTkFrame(main_container, fg_color=CARD_BG, corner_radius=15, border_width=1, border_color="#E2E8F0")
        search_frame.pack(fill="x", padx=20, pady=20)

        # تفريغ منطقة البحث وجعل العناصر تصطف من اليمين لليسار
        search_inner = ctk.CTkFrame(search_frame, fg_color="transparent")
        search_inner.pack(side="right", fill="y", padx=20, pady=15)

        # --- زر البحث ---
        btn_search = ctk.CTkButton(search_inner, text="🔍 بحث", font=("Segoe UI", 15, "bold"),
                                   fg_color=FIB_GREEN, hover_color="#004426", text_color="white",
                                   width=120, height=40, corner_radius=8, command=lambda: execute_search())
        btn_search.pack(side="left", padx=10)

        # --- رقم الحساب ---
        self.ent_rej_acc = ctk.CTkEntry(search_inner, font=("Segoe UI", 15, "bold"),
                                        justify="center", placeholder_text="رقم الحساب...",
                                        width=200, height=40, border_color="#CBD5E1")
        self.ent_rej_acc.pack(side="left", padx=10)

        ctk.CTkLabel(search_inner, text="رقم الحساب:", font=("Segoe UI", 14, "bold"), text_color=TEXT_DARK).pack(side="left", padx=(10, 2))

        # --- قائمة الفروع ---
        # --- قائمة الفروع بالمركب البريميوم ---
        if hasattr(self, '_create_premium_select'):
            self.cmb_rej_branch_box, self.cmb_rej_branch = self._create_premium_select(
                search_inner,
                values=["جاري التحميل..."],
                default="جاري التحميل...",
                title="اختر الفرع"
            )
            self.cmb_rej_branch_box.pack(side="left", padx=10)
        else:
            # احتياطي في حال عدم وجود الدالة المساعدة
            self.cmb_rej_branch = ctk.CTkComboBox(search_inner, font=("Segoe UI", 14, "bold"), justify="right",
                                                  width=250, height=40, border_color="#CBD5E1")
            self.cmb_rej_branch.pack(side="left", padx=10)

        ctk.CTkLabel(search_inner, text="الفرع:", font=("Segoe UI", 14, "bold"), text_color=TEXT_DARK).pack(side="left",
                                                                                                            padx=(10,
                                                                                                                  2))
        # تعبئة الفروع (بالاعتماد على دالتك nuwairy_load_branches)
        def load_branches_to_combo():
            if not hasattr(self, 'branch_mapping') or not self.branch_mapping:
                # لو لم يتم تحميل الفروع، استدعِ الدالة الخاصة بك
                if hasattr(self, 'nuwairy_load_branches'):
                    self.nuwairy_load_branches()

            if hasattr(self, 'branch_mapping') and self.branch_mapping:
                branches = list(self.branch_mapping.keys())
                self.cmb_rej_branch.configure(values=branches)
                self.cmb_rej_branch.set(branches[0])
            else:
                self.cmb_rej_branch.configure(values=["- لا توجد فروع -"])
                self.cmb_rej_branch.set("- لا توجد فروع -")

        # استدعاء تعبئة الفروع
        load_branches_to_combo()

        # ربط زر الـ Enter بالبحث
        self.ent_rej_acc.bind("<Return>", lambda event: execute_search())

        # =========================================
        # 📜 3. Results Area (كروت الشيكات)
        # =========================================
        self.rej_results_scroll = ctk.CTkScrollableFrame(main_container, fg_color="transparent")
        self.rej_results_scroll.pack(fill="both", expand=True, padx=15, pady=(0, 20))

        def fix_arabic_name(raw_name):
            import re
            import pandas as pd

            if pd.isna(raw_name) or not str(raw_name).strip():
                return "غير مسجل"

            text = str(raw_name).strip()

            # 1. إصلاح المسافات الخاطئة قبل النهايات (مثل: الاسلام يه -> الاسلاميه)
            text = re.sub(r'\s+(يه|ية|ه|ة)\b', r'\1', text)

            previous_text = ""
            while text != previous_text:
                previous_text = text

                # 2. فصل الحروف التي لا تتصل بما بعدها (ة، ى، ء) إذا جاء بعدها حرف
                # مثال: الدولىللبنوك -> الدولى للبنوك
                text = re.sub(r'([ةىء])([\u0621-\u064A])', r'\1 \2', text)

                # 3. فصل أي كلمة تلتصق بـ "ال" المعرفة
                # مثال: الاتحادالدولى -> الاتحاد الدولى
                text = re.sub(r'([\u0621-\u064A]{2,})((?:ب|ك|ف|و)?ال[\u0621-\u064A]{2,})', r'\1 \2', text)

                # 4. فصل الأسماء المركبة المشهورة (السوابق)
                prefixes = ['عبد', 'ابو', 'أبو', 'ام', 'أم', 'بن', 'بنت', 'ذو', 'ذي']
                for p in prefixes:
                    text = re.sub(f'(?<![\u0621-\u064A])({p})(?=[\u0621-\u064A])', r'\1 ', text)

                # 5. فصل الأسماء المركبة المشهورة (اللواحق)
                suffixes = ['الدين','مخمد', 'الله', 'الاسلام', 'الإسلام', 'الحق']
                for s in suffixes:
                    text = re.sub(f'(?<=[\u0621-\u064A])({s})(?![\u0621-\u064A])', r' \1', text)

                # 6. تنظيف المسافات الزائدة
                text = re.sub(r'\s+', ' ', text).strip()

            return text
        # =========================================
        # ⚙️ 4. Search Engine Logic (التكملة)
        # =========================================
        def execute_search():
            branch_name = self.cmb_rej_branch.get()
            acc_num = self.ent_rej_acc.get().strip()

            if not acc_num:
                messagebox.showwarning("تنبيه", "يرجى إدخال رقم الحساب أولاً")
                self.ent_rej_acc.focus()
                return

            if not hasattr(self, 'branch_mapping') or branch_name not in self.branch_mapping:
                messagebox.showerror("خطأ", "برجاء اختيار فرع صحيح")
                return

            # جلب رقم الفرع (MBR) من الـ Mapping
            branch_code = self.branch_mapping[branch_name]

            # تنظيف الشاشة قبل البحث
            for widget in self.rej_results_scroll.winfo_children():
                widget.destroy()

            lbl_loading = ctk.CTkLabel(self.rej_results_scroll, text="⚡ جاري البحث في قاعدة البيانات...",
                                       font=("Segoe UI", 16, "bold"), text_color=FIB_GOLD)
            lbl_loading.pack(pady=50)

            def fetch_data():
                try:
                    engine = self._get_db_connection()

                    # 🔥 التعديل الأول: عملنا JOIN عشان نجيب BNAME من TBL_client_name
                    sql = f"""
                            SELECT 
                                c.MCHNO, c.MAMT1, c.MDAT1, c.MDAT2, c.MCOD, c.MBAL,
                                cl.BNAME
                            FROM [dbo].[TBL_cheques] AS c WITH (NOLOCK)
                            LEFT JOIN [dbo].[TBL_client_name] AS cl WITH (NOLOCK) 
                                ON c.MCLNT = cl.BCLNT
                            WHERE c.MBR = N'{branch_code}' AND c.MCLNT = N'{acc_num}'
                        """
                    df = pd.read_sql(sql, engine)

                    self.after(0, lambda: update_results_ui(df))
                except Exception as e:
                    logging.error(f"Error fetching rejected cheques: {e}")
                    self.after(0, lambda: update_results_ui(pd.DataFrame(), error=str(e)))

            threading.Thread(target=fetch_data, daemon=True).start()

        def update_results_ui(df, error=None):
            for widget in self.rej_results_scroll.winfo_children():
                widget.destroy()

            if error:
                ctk.CTkLabel(self.rej_results_scroll, text=f"❌ حدث خطأ أثناء البحث:\n{error}",
                             font=("Segoe UI", 14, "bold"), text_color="#EF4444").pack(pady=40)
                return

            if df.empty:
                ctk.CTkLabel(self.rej_results_scroll, text="🔍 لا توجد شيكات مرفوضة لهذا الحساب في هذا الفرع",
                             font=("Segoe UI", 18, "bold"), text_color=TEXT_MUTED).pack(pady=60)
                return

            # إنشاء كارت مخصص لكل شيك
            for _, row in df.iterrows():
                # معالجة البيانات
                chq_no = str(row['MCHNO']).replace('.0', '') if pd.notna(row['MCHNO']) else "غير معروف"
                reject_code = str(row['MCOD']).replace('.0', '') if pd.notna(row['MCOD']) else "—"

                # 🔥 التعديل الثاني: استخراج اسم العميل
                cust_name = fix_arabic_name(row['BNAME'])

                # تنسيق المبالغ المالية
                try:
                    amount = f"{float(row['MAMT1']):,.2f}" if pd.notna(row['MAMT1']) else "0.00"
                    balance = f"{float(row['MBAL']):,.2f}" if pd.notna(row['MBAL']) else "0.00"
                except:
                    amount = str(row['MAMT1'])
                    balance = str(row['MBAL'])

                # تنسيق التواريخ
                rej_date = str(row['MDAT1']).split()[0] if pd.notna(row['MDAT1']) else "—"
                due_date = str(row['MDAT2']).split()[0] if pd.notna(row['MDAT2']) else "—"

                # بناء الكارت
                card = ctk.CTkFrame(self.rej_results_scroll, fg_color=CARD_BG, corner_radius=12,
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

                # 🔥 التعديل الثالث: صف جديد لاسم العميل
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

                def create_info_box(parent, row_idx, col_idx, title, value, val_color=TEXT_DARK):
                    box = ctk.CTkFrame(parent, fg_color=BOX_BG, corner_radius=8)
                    box.grid(row=row_idx, column=col_idx, padx=5, pady=5, sticky="ew")
                    ctk.CTkLabel(box, text=title, font=("Segoe UI", 12, "bold"), text_color=TEXT_MUTED).pack(
                        anchor="center", pady=(5, 0))
                    ctk.CTkLabel(box, text=value, font=("Segoe UI", 15, "bold"), text_color=val_color).pack(
                        anchor="center", pady=(0, 5))

                # ترتيب العناصر من اليمين لليسار في الجريد
                create_info_box(data_grid, 0, 3, "مبلغ الشيك", f"{amount} EGP", val_color=FIB_GREEN)
                create_info_box(data_grid, 0, 2, "تاريخ الاستحقاق", due_date)
                create_info_box(data_grid, 0, 1, "تاريخ الرفض", rej_date, val_color="#EF4444")
                create_info_box(data_grid, 0, 0, "رصيد الحساب", f"{balance} EGP", val_color=TEXT_DARK)

    def setup_client_balances_ui(self, parent):
        import pandas as pd
        import customtkinter as ctk
        from tkinter import messagebox
        import threading
        import logging

        # =========================================
        # 🎨 1. الألوان والتنسيق
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
            header,
            text="💳 البحث بأرصدة وأنواع حسابات العميل",
            font=("Segoe UI", 22, "bold"),
            text_color=CARD_BG
        ).pack(side="right", padx=30, pady=15)

        # =========================================
        # 🔍 2. منطقة البحث
        # =========================================
        search_frame = ctk.CTkFrame(main_container, fg_color=CARD_BG, corner_radius=15, border_width=1,
                                    border_color="#E2E8F0")
        search_frame.pack(fill="x", padx=20, pady=20)

        search_inner = ctk.CTkFrame(search_frame, fg_color="transparent")
        search_inner.pack(side="right", fill="y", padx=20, pady=15)

        btn_search = ctk.CTkButton(
            search_inner, text="🔍 بحث", font=("Segoe UI", 15, "bold"),
            fg_color=FIB_GREEN, hover_color="#004426", text_color="white",
            width=120, height=40, corner_radius=8, command=lambda: execute_search()
        )
        btn_search.pack(side="left", padx=10)

        self.ent_bal_acc = ctk.CTkEntry(
            search_inner, font=("Segoe UI", 15, "bold"),
            justify="center", placeholder_text="رقم العميل...",
            width=200, height=40, border_color="#CBD5E1"
        )
        self.ent_bal_acc.pack(side="left", padx=10)

        ctk.CTkLabel(search_inner, text="رقم العميل:", font=("Segoe UI", 14, "bold"), text_color=TEXT_DARK).pack(
            side="left", padx=(10, 2))

        if hasattr(self, '_create_premium_select'):
            self.cmb_bal_branch_box, self.cmb_bal_branch = self._create_premium_select(
                search_inner, values=["جاري التحميل..."], default="جاري التحميل...", title="اختر الفرع"
            )
            self.cmb_bal_branch_box.pack(side="left", padx=10)
        else:
            self.cmb_bal_branch = ctk.CTkComboBox(
                search_inner, font=("Segoe UI", 14, "bold"), justify="right",
                width=250, height=40, border_color="#CBD5E1"
            )
            self.cmb_bal_branch.pack(side="left", padx=10)

        ctk.CTkLabel(search_inner, text="الفرع:", font=("Segoe UI", 14, "bold"), text_color=TEXT_DARK).pack(side="left",
                                                                                                            padx=(10,
                                                                                                                  2))

        def load_branches_to_combo():
            if hasattr(self, 'branch_mapping') and self.branch_mapping:
                branches = list(self.branch_mapping.keys())
                self.cmb_bal_branch.configure(values=branches)
                self.cmb_bal_branch.set(branches[0])
            else:
                if hasattr(self, 'nuwairy_load_branches'):
                    self.nuwairy_load_branches()
                self.after(500, load_branches_to_combo)

        load_branches_to_combo()
        self.ent_bal_acc.bind("<Return>", lambda event: execute_search())

        # =========================================
        # 📜 3. منطقة عرض النتائج
        # =========================================
        self.bal_results_scroll = ctk.CTkScrollableFrame(main_container, fg_color="transparent")
        self.bal_results_scroll.pack(fill="both", expand=True, padx=15, pady=(0, 20))

        # =========================================
        # ⚙️ 4. تنفيذ الاستعلام
        # =========================================
        def execute_search():
            branch_name = self.cmb_bal_branch.get().strip()
            acc_num = self.ent_bal_acc.get().strip()

            if not acc_num:
                messagebox.showwarning("تنبيه", "يرجى إدخال رقم العميل أولاً")
                self.ent_bal_acc.focus()
                return

            if not branch_name or branch_name == "جاري التحميل...":
                messagebox.showerror("خطأ", "برجاء اختيار فرع صحيح")
                return

            for widget in self.bal_results_scroll.winfo_children():
                widget.destroy()

            lbl_loading = ctk.CTkLabel(
                self.bal_results_scroll,
                text="⚡ جاري البحث واستعلام بيانات واسم العميل...",
                font=("Segoe UI", 16, "bold"), text_color=FIB_GOLD
            )
            lbl_loading.pack(pady=50)

            def fetch_data():
                try:
                    engine = getattr(self, '_get_db_connection', lambda: None)()
                    if not engine:
                        raise Exception("لم يتم العثور على دالة الاتصال بقاعدة البيانات.")

                    # 1. جلب اسم الجدول وكود الفرع
                    get_branch_info_sql = f"""
                        SELECT TOP 1 [BranchCode], [tablename]
                        FROM [dbo].[TBL_Branches] WITH (NOLOCK)
                        WHERE [branchName] = N'{branch_name}'
                    """

                    branch_df = pd.read_sql(get_branch_info_sql, engine)

                    if branch_df.empty:
                        raise Exception(f"لم يتم العثور على الفرع '{branch_name}' في جدول TBL_Branches.")

                    branch_code = str(branch_df.iloc[0]['BranchCode']).strip()
                    target_table = str(branch_df.iloc[0]['tablename']).strip()

                    if not target_table:
                        raise Exception("اسم الجدول (tablename) فارغ لهذا الفرع.")

                    # 2. الكويري المحدث بجدول العملات
                    sql = f"""
                        SELECT 
                            b.PGL,
                            ISNULL(a.CNM, N'غير معرف') AS AccTypeName,
                            b.PCLNT,
                            b.PCUR,
                            ISNULL(c.cnm, N'غير معرف') AS CurrencyName,
                            b.PBAL,
                            b.PAMTM,
                            b.BNAME 
                        FROM [dbo].[{target_table}] AS b WITH (NOLOCK)
                        LEFT JOIN [dbo].[TBL_AccTypes] AS a WITH (NOLOCK)
                            ON CAST(b.PGL AS NVARCHAR(50)) = CAST(a.ccod AS NVARCHAR(50))
                        LEFT JOIN [dbo].[tbl_currency] AS c WITH (NOLOCK)
                            ON CAST(b.PCUR AS NVARCHAR(50)) = CAST(c.fcur AS NVARCHAR(50))
                        WHERE (
                            CAST(b.BCLNT AS NVARCHAR(50)) = N'{acc_num}'
                            OR LTRIM(RTRIM(CAST(b.BCLNT AS NVARCHAR(50)))) = N'{acc_num}'
                            OR TRY_CAST(b.BCLNT AS BIGINT) = TRY_CAST(N'{acc_num}' AS BIGINT)
                            OR CAST(b.PCLNT AS NVARCHAR(50)) = N'{acc_num}'
                            OR LTRIM(RTRIM(CAST(b.PCLNT AS NVARCHAR(50)))) = N'{acc_num}'
                            OR TRY_CAST(b.PCLNT AS BIGINT) = TRY_CAST(N'{acc_num}' AS BIGINT)
                        )
                    """

                    df = pd.read_sql(sql, engine)
                    self.after(0, lambda: update_results_ui(df, target_table, branch_code))

                except Exception as e:
                    error_msg = str(e)
                    logging.error(f"Error fetching client balances: {error_msg}")
                    self.after(0, lambda msg=error_msg: update_results_ui(pd.DataFrame(), "", "", error=msg))

            threading.Thread(target=fetch_data, daemon=True).start()

        def update_results_ui(df, table_used, branch_code, error=None):
            for widget in self.bal_results_scroll.winfo_children():
                widget.destroy()

            if error:
                ctk.CTkLabel(
                    self.bal_results_scroll,
                    text=f"❌ حدث خطأ أثناء البحث:\n{error}",
                    font=("Segoe UI", 14, "bold"), text_color="#EF4444"
                ).pack(pady=40)
                return

            if df.empty:
                ctk.CTkLabel(
                    self.bal_results_scroll,
                    text=f"🔍 لا توجد نتائج لرقم العميل ({self.ent_bal_acc.get()}) في جدول [{table_used}]",
                    font=("Segoe UI", 18, "bold"), text_color=TEXT_MUTED
                ).pack(pady=60)
                return

            # 🔍 استخراج اسم العميل الموحد
            valid_cust_names = df[df['BNAME'].notna() & (df['BNAME'].astype(str).str.strip() != '')]['BNAME']
            global_cust_name = str(valid_cust_names.iloc[0]).strip() if not valid_cust_names.empty else "غير مدون"
            acc_num_val = self.ent_bal_acc.get().strip()

            # ============================================
            # 👑 كارت بيانات العميل الثابت (فوق خالص)
            # ============================================
            profile_frame = ctk.CTkFrame(self.bal_results_scroll, fg_color=FIB_GREEN, corner_radius=12)
            profile_frame.pack(fill="x", padx=10, pady=(0, 20))

            ctk.CTkLabel(
                profile_frame,
                text=f"👤 اسم العميل: {global_cust_name}    |    🔢 رقم العميل: {acc_num_val}",
                font=("Segoe UI", 18, "bold"), text_color="white"
            ).pack(pady=15)

            # حاوية الكروت لتجهيزها قبل العرض عشان نعد اللي هيظهر بس
            valid_cards = []

            for _, row in df.iterrows():
                pgl_code = str(row['PGL']).replace('.0', '') if pd.notna(row['PGL']) else "—"
                acc_type_name = str(row['AccTypeName']).strip()

                pcur_val = str(row['PCUR']).replace('.0', '') if pd.notna(row['PCUR']) else "—"
                curr_name = str(row['CurrencyName']).strip()

                # 🛑 الفلترة: تخطي السجل إذا كان ملوش عملة (أو غير معرفة) ولا ليه نوع حساب
                is_invalid_type = (acc_type_name == "غير معرف" or pgl_code in ["—", "0", "nan"])
                is_invalid_currency = (curr_name == "غير معرف" or pcur_val in ["—", "0", "nan"])

                if is_invalid_type and is_invalid_currency:
                    continue  # تجاهل الريكورد تماماً

                valid_cards.append(row)

            # شريط الملخص بالعدد الفعلي بعد الفلترة
            summary_bar = ctk.CTkFrame(self.bal_results_scroll, fg_color=CARD_BG, corner_radius=10)
            summary_bar.pack(fill="x", padx=10, pady=(0, 10))

            if len(valid_cards) == 0:
                ctk.CTkLabel(
                    summary_bar,
                    text="⚠️ العميل موجود ولكن لا توجد حسابات أو عملات مسجلة له لعرضها.",
                    font=("Segoe UI", 15, "bold"), text_color="#EF4444"
                ).pack(side="right", padx=15, pady=10)
                return
            else:
                ctk.CTkLabel(
                    summary_bar,
                    text=f"تم العثور على {len(valid_cards)} حساب/حسابات نشطة 📊",
                    font=("Segoe UI", 14, "bold"), text_color=FIB_GREEN
                ).pack(side="right", padx=15, pady=10)

            # ============================================
            # 🗂️ عرض الكروت الخاصة بالحسابات
            # ============================================
            for row in valid_cards:
                pgl_code = str(row['PGL']).replace('.0', '') if pd.notna(row['PGL']) else "—"
                acc_type_name = str(row['AccTypeName']).strip()
                pcur_val = str(row['PCUR']).replace('.0', '') if pd.notna(row['PCUR']) else "—"
                curr_name = str(row['CurrencyName']).strip()

                balance_val = "0.00"
                if 'PBAL' in row and pd.notna(row['PBAL']):
                    try:
                        balance_val = f"{float(row['PBAL']):,.2f}"
                    except:
                        balance_val = str(row['PBAL'])

                amtm_val = "0.00"
                if 'PAMTM' in row and pd.notna(row['PAMTM']):
                    try:
                        amtm_val = f"{float(row['PAMTM']):,.2f}"
                    except:
                        amtm_val = str(row['PAMTM'])

                card = ctk.CTkFrame(self.bal_results_scroll, fg_color=CARD_BG, corner_radius=12, border_width=1,
                                    border_color="#E2E8F0")
                card.pack(fill="x", padx=10, pady=8)

                ctk.CTkFrame(card, fg_color=FIB_GOLD, width=5, corner_radius=0).pack(side="right", fill="y", pady=10)

                card_content = ctk.CTkFrame(card, fg_color="transparent")
                card_content.pack(fill="both", expand=True, padx=20, pady=15)

                header_row = ctk.CTkFrame(card_content, fg_color="transparent")
                header_row.pack(fill="x", pady=(0, 5))

                ctk.CTkLabel(
                    header_row,
                    text=f"نوع الحساب: {acc_type_name} 🏷️",
                    font=("Segoe UI", 16, "bold"), text_color=FIB_GREEN
                ).pack(side="right")

                ctk.CTkLabel(
                    header_row,
                    text=f"العملة: {curr_name} 💰",
                    font=("Segoe UI", 14, "bold"), text_color=TEXT_DARK
                ).pack(side="left")

                ctk.CTkFrame(card_content, fg_color="#F1F5F9", height=2).pack(fill="x", pady=10)

                data_grid = ctk.CTkFrame(card_content, fg_color="transparent")
                data_grid.pack(fill="x")
                data_grid.grid_columnconfigure((0, 1, 2, 3), weight=1)

                def create_info_box(parent, col_idx, title, value, val_color=TEXT_DARK):
                    box = ctk.CTkFrame(parent, fg_color=BOX_BG, corner_radius=8)
                    box.grid(row=0, column=col_idx, padx=4, pady=5, sticky="ew")
                    ctk.CTkLabel(box, text=title, font=("Segoe UI", 11, "bold"), text_color=TEXT_MUTED).pack(
                        anchor="center", pady=(5, 0))
                    ctk.CTkLabel(box, text=value, font=("Segoe UI", 14, "bold"), text_color=val_color).pack(
                        anchor="center", pady=(0, 5))

                create_info_box(data_grid, 3, "الرصيد القائم (PBAL)", balance_val, val_color=FIB_GREEN)
                create_info_box(data_grid, 2, "المبلغ (PAMTM)", amtm_val, val_color=TEXT_DARK)
                create_info_box(data_grid, 1, "كود العملة (PCUR)", pcur_val, val_color=FIB_GOLD)
                create_info_box(data_grid, 0, "كود الحساب (PGL)", pgl_code)

    def setup_cancelled_certs_ui(self, parent):
        import pandas as pd
        import customtkinter as ctk
        from tkinter import messagebox
        import threading
        import logging

        # =========================================
        # 🎨 1. Premium Theme Colors
        # =========================================
        FIB_GREEN = "#005C34"
        FIB_GOLD = "#C5A059"
        BG_MAIN = "#F8FAFC"
        CARD_BG = "#FFFFFF"
        BOX_BG = "#F1F5F9"
        TEXT_DARK = "#0F172A"
        TEXT_MUTED = "#64748B"
        CANCEL_COLOR = "#DC2626"  # لون أحمر مميز للشهادات الملغاة

        # حاوية الشاشة الرئيسية
        main_container = ctk.CTkFrame(parent, fg_color=BG_MAIN)
        main_container.pack(fill="both", expand=True)

        # الهيدر العلوي
        header = ctk.CTkFrame(main_container, fg_color=FIB_GREEN, height=65, corner_radius=0)
        header.pack(fill="x")
        header.pack_propagate(False)

        ctk.CTkFrame(main_container, fg_color=FIB_GOLD, height=4, corner_radius=0).pack(fill="x")

        title_lbl = ctk.CTkLabel(header, text="استعلام الشهادات الملغاة برقم العميل", font=("Segoe UI", 22, "bold"),
                                 text_color=CARD_BG)
        title_lbl.pack(side="right", padx=30, pady=15)

        # =========================================
        # 🔍 2. Search Area (الفرع ورقم العميل)
        # =========================================
        search_frame = ctk.CTkFrame(main_container, fg_color=CARD_BG, corner_radius=15, border_width=1,
                                    border_color="#E2E8F0")
        search_frame.pack(fill="x", padx=20, pady=20)

        search_inner = ctk.CTkFrame(search_frame, fg_color="transparent")
        search_inner.pack(side="right", fill="y", padx=20, pady=15)

        # --- زر البحث ---
        btn_search = ctk.CTkButton(search_inner, text="🔍 بحث", font=("Segoe UI", 15, "bold"),
                                   fg_color=FIB_GREEN, hover_color="#004426", text_color="white",
                                   width=120, height=40, corner_radius=8, command=lambda: execute_search())
        btn_search.pack(side="left", padx=10)

        # --- رقم العميل ---
        self.ent_canc_cust_no = ctk.CTkEntry(search_inner, font=("Segoe UI", 15, "bold"),
                                             justify="center", placeholder_text="رقم العميل...",
                                             width=200, height=40, border_color="#CBD5E1")
        self.ent_canc_cust_no.pack(side="left", padx=10)

        ctk.CTkLabel(search_inner, text="رقم العميل:", font=("Segoe UI", 14, "bold"), text_color=TEXT_DARK).pack(
            side="left", padx=(10, 2))

        # --- قائمة الفروع ---
        if hasattr(self, '_create_premium_select'):
            self.cmb_canc_branch_box, self.cmb_canc_branch = self._create_premium_select(
                search_inner,
                values=["جاري التحميل..."],
                default="جاري التحميل...",
                title="اختر الفرع"
            )
            self.cmb_canc_branch_box.pack(side="left", padx=10)
        else:
            self.cmb_canc_branch = ctk.CTkComboBox(search_inner, font=("Segoe UI", 14, "bold"), justify="right",
                                                   width=250, height=40, border_color="#CBD5E1")
            self.cmb_canc_branch.pack(side="left", padx=10)

        ctk.CTkLabel(search_inner, text="الفرع:", font=("Segoe UI", 14, "bold"), text_color=TEXT_DARK).pack(side="left",
                                                                                                            padx=(10,
                                                                                                                  2))

        # تعبئة الفروع تلقائياً
        def load_branches_to_combo():
            if hasattr(self, 'branch_mapping') and self.branch_mapping:
                branches = list(self.branch_mapping.keys())
                self.cmb_canc_branch.configure(values=branches)
                self.cmb_canc_branch.set(branches[0])
            else:
                if hasattr(self, 'nuwairy_load_branches'):
                    self.nuwairy_load_branches()
                self.after(500, load_branches_to_combo)

        load_branches_to_combo()

        # ربط زر الـ Enter بالبحث
        self.ent_canc_cust_no.bind("<Return>", lambda event: execute_search())

        # =========================================
        # 📜 3. Results Area (كروت الشهادات)
        # =========================================
        self.canc_results_scroll = ctk.CTkScrollableFrame(main_container, fg_color="transparent")
        self.canc_results_scroll.pack(fill="both", expand=True, padx=15, pady=(0, 20))

        def fix_arabic_name(raw_name):
            import re
            if pd.isna(raw_name) or not str(raw_name).strip():
                return "غير مسجل"
            text = str(raw_name).strip()
            text = re.sub(r'\s+(يه|ية|ه|ة)\b', r'\1', text)
            previous_text = ""
            while text != previous_text:
                previous_text = text
                text = re.sub(r'([ةىء])([\u0621-\u064A])', r'\1 \2', text)
                text = re.sub(r'([\u0621-\u064A]{2,})((?:ب|ك|ف|و)?ال[\u0621-\u064A]{2,})', r'\1 \2', text)
                for p in ['عبد', 'ابو', 'أبو', 'ام', 'أم', 'بن', 'بنت', 'ذو', 'ذي']:
                    text = re.sub(f'(?<![\u0621-\u064A])({p})(?=[\u0621-\u064A])', r'\1 ', text)
                for s in ['الدين', 'مخمد', 'الله', 'الاسلام', 'الإسلام', 'الحق']:
                    text = re.sub(f'(?<=[\u0621-\u064A])({s})(?![\u0621-\u064A])', r' \1', text)
                text = re.sub(r'\s+', ' ', text).strip()
            return text

        # =========================================
        # ⚙️ 4. Search Engine Logic
        # =========================================
        def execute_search():
            branch_name = self.cmb_canc_branch.get()
            cust_no = self.ent_canc_cust_no.get().strip()

            if not cust_no:
                messagebox.showwarning("تنبيه", "يرجى إدخال رقم العميل أولاً")
                self.ent_canc_cust_no.focus()
                return

            if not hasattr(self, 'branch_mapping') or branch_name not in self.branch_mapping:
                messagebox.showerror("خطأ", "برجاء اختيار فرع صحيح")
                return

            # 1. الحصول على اسم الجدول وكود الفرع من المابنج بناءً على الشرح المطلوب
            branch_info = self.branch_mapping[branch_name]

            # دعم لو الـ branch_info عبارة عن tuple (كود الفرع, اسم الجدول) أو كود فقط
            if isinstance(branch_info, tuple):
                branch_code, target_table = branch_info
            else:
                branch_code = branch_info
                target_table = None

            # لو الجدول مش موجود في المابنج، نجيبه من جدول الفروع بالداتابيز كاحتياط
            for widget in self.canc_results_scroll.winfo_children():
                widget.destroy()

            lbl_loading = ctk.CTkLabel(self.canc_results_scroll, text="⚡ جاري البحث عن الشهادات الملغاة...",
                                       font=("Segoe UI", 16, "bold"), text_color=FIB_GOLD)
            lbl_loading.pack(pady=50)

            def fetch_data():
                try:
                    engine = getattr(self, '_get_db_connection', lambda: None)()
                    if not engine:
                        raise Exception("لم يتم العثور على دالة الاتصال بقاعدة البيانات.")

                    # بما أننا لدينا كود الفرع بالفعل (branch_code)،
                    # نحتاج فقط لمعرفة اسم الجدول الخاص بهذا الفرع من الـ branch_mapping أو جدول الفروع بطريقة صحيحة:

                    # يمكنك جلب اسم الجدول مباشرة بالبحث عن الفرع في جدول الفروع باستخدام كود الفرع (إذا كان العمود اسمه مثلاً BranchCode أو رقم الفرع)
                    branch_query = f"SELECT * FROM [dbo].[TBL_Branches] WHERE BranchCode = N'{branch_code}'"
                    branch_df = pd.read_sql(branch_query, engine)

                    if branch_df.empty:
                        raise Exception("لم يتم العثور على جدول هذا الفرع في قاعدة البيانات.")

                    # جلب اسم الجدول الفعلي من العمود المخصص (مثل GL_TableName أو TableName)
                    target_table = branch_df.iloc[0].get('GL_TableName') or branch_df.iloc[0].get('TableName')

                    if not target_table or pd.isna(target_table):
                        raise Exception("اسم الجدول الخاص بالفرع غير معرف في قاعدة البيانات.")

                    target_table = str(target_table).strip()

                    # الكويري المباشر للشهادات الملغاة باستخدام الجدول الخاص بالفرع وكود الفرع صحيحاً
                    sql = f"""
                        SELECT CCER, CNO, CAMT, CDAT1, CNAME, CDAT10
                        FROM [dbo].[{target_table}] WITH (NOLOCK)
                        WHERE CBR = N'{branch_code}' 
                          AND CCLNT = N'{cust_no}'
                          AND CDAT10 IS NOT NULL 
                          AND LTRIM(RTRIM(CDAT10)) <> ''
                          AND LTRIM(RTRIM(CDAT10)) <> '0'
                    """
                    df = pd.read_sql(sql, engine)

                    self.after(0, lambda: update_results_ui(df))
                except Exception as e:
                    logging.error(f"Error fetching cancelled certificates: {e}")
                    self.after(0, lambda: update_results_ui(pd.DataFrame(), error=str(e)))

            threading.Thread(target=fetch_data, daemon=True).start()

        def update_results_ui(df, error=None):
            for widget in self.canc_results_scroll.winfo_children():
                widget.destroy()

            if error:
                ctk.CTkLabel(self.canc_results_scroll, text=f"❌ حدث خطأ أثناء البحث:\n{error}",
                             font=("Segoe UI", 14, "bold"), text_color="#EF4444").pack(pady=40)
                return

            if df.empty:
                ctk.CTkLabel(self.canc_results_scroll, text="🔍 لا توجد شهادات ملغاة لهذا العميل في هذا الفرع",
                             font=("Segoe UI", 18, "bold"), text_color=TEXT_MUTED).pack(pady=60)
                return

            # إنشاء كارت مخصص لكل شهادة ملغاة
            for _, row in df.iterrows():
                ccer_val = str(row['CCER']).replace('.0', '') if pd.notna(row['CCER']) else "غير معروف"
                cno_val = str(row['CNO']).replace('.0', '') if pd.notna(row['CNO']) else "—"

                try:
                    camt_val = f"{float(row['CAMT']):,.2f}"
                except:
                    camt_val = "0.00"

                cust_name = fix_arabic_name(row['CNAME']) if pd.notna(row['CNAME']) else "غير مسجل"
                cdat1_val = str(row['CDAT1']).split()[0] if pd.notna(row['CDAT1']) and str(
                    row['CDAT1']).strip() else "—"
                cdat10_val = str(row['CDAT10']).split()[0] if pd.notna(row['CDAT10']) and str(
                    row['CDAT10']).strip() else "—"

                card = ctk.CTkFrame(self.canc_results_scroll, fg_color=CARD_BG, corner_radius=12,
                                    border_width=1, border_color="#E2E8F0")
                card.pack(fill="x", padx=10, pady=8)

                ctk.CTkFrame(card, fg_color=CANCEL_COLOR, width=5, corner_radius=0).pack(side="right", fill="y",
                                                                                         pady=10)

                card_content = ctk.CTkFrame(card, fg_color="transparent")
                card_content.pack(fill="both", expand=True, padx=20, pady=15)

                # صف العنوان (رقم الشهادة وقيمة الشهادة)
                header_row = ctk.CTkFrame(card_content, fg_color="transparent")
                header_row.pack(fill="x", pady=(0, 5))

                ctk.CTkLabel(header_row, text=f"شهادة رقم : {ccer_val} 📜", font=("Segoe UI", 18, "bold"),
                             text_color=FIB_GREEN).pack(side="right")
                ctk.CTkLabel(header_row, text=f"القيمة: {camt_val} 💰", font=("Segoe UI", 15, "bold"),
                             text_color=FIB_GOLD).pack(side="left")

                # صف اسم العميل ورقم أمر الشراء
                info_row = ctk.CTkFrame(card_content, fg_color="transparent")
                info_row.pack(fill="x", pady=(0, 10))
                ctk.CTkLabel(info_row, text=f"العميل: {cust_name} 👤", font=("Segoe UI", 15, "bold"),
                             text_color=TEXT_MUTED).pack(side="right")
                ctk.CTkLabel(info_row, text=f"رقم أمر الشراء: {cno_val}", font=("Segoe UI", 13, "bold"),
                             text_color=TEXT_MUTED).pack(side="left")

                # خط فاصل
                ctk.CTkFrame(card_content, fg_color="#F1F5F9", height=2).pack(fill="x", pady=5)

                # صف التواريخ (تاريخ الشراء وتاريخ الإلغاء)
                data_grid = ctk.CTkFrame(card_content, fg_color="transparent")
                data_grid.pack(fill="x", pady=10)
                data_grid.grid_columnconfigure((0, 1), weight=1)

                def create_info_box(parent, row_idx, col_idx, title, value, val_color=TEXT_DARK):
                    box = ctk.CTkFrame(parent, fg_color=BOX_BG, corner_radius=8)
                    box.grid(row=row_idx, column=col_idx, padx=5, pady=5, sticky="ew")
                    ctk.CTkLabel(box, text=title, font=("Segoe UI", 12, "bold"), text_color=TEXT_MUTED).pack(
                        anchor="center", pady=(5, 0))
                    ctk.CTkLabel(box, text=value, font=("Segoe UI", 15, "bold"), text_color=val_color).pack(
                        anchor="center", pady=(0, 5))

                create_info_box(data_grid, 0, 1, "تاريخ الشراء", cdat1_val, val_color=FIB_GREEN)
                create_info_box(data_grid, 0, 0, "تاريخ الإلغاء", cdat10_val, val_color=CANCEL_COLOR)


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
            align="e",  # 👈 التعديل الأول: محاذاة البيانات لليمين
            header_align="e",  # 👈 التعديل الثاني: محاذاة العناوين لليمين
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

        # 1. التعديل هنا: العنوان يروح يمين (right)
        title_wrap = ctk.CTkFrame(header_inner, fg_color="transparent")
        title_wrap.pack(side="right", fill="x", expand=True)

        ctk.CTkLabel(
            title_wrap,
            text="🔍 استعلام حركات العملاء",
            font=("Segoe UI", 22, "bold"),
            text_color=FIB_GREEN
        ).pack(anchor="e")  # المحاذاة يمين (e)

        ctk.CTkLabel(
            title_wrap,
            text="ابحث برقم العميل، اختر نوع الحساب والعملة، وحدد فترة التاريخ (اختياري).",
            font=("Segoe UI", 12),
            text_color="#6B7280"
        ).pack(anchor="e", pady=(4, 0))  # المحاذاة يمين (e)

        # 2. التعديل هنا: الزراير تروح شمال (left)
        actions = ctk.CTkFrame(header_inner, fg_color="transparent")
        actions.pack(side="left")

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

        # 3. التعديل هنا: ترتيب الزراير جوه الحاوية يبدأ من اليمين لليسار (side="right")
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
        self.btn_clear_nuwairy.pack(side="right", padx=(10, 0))  # عكسنا الـ padx

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
        self.btn_search_nuwairy.pack(side="right")

        # =========================
        # Filters Card (الـ Grid بتاعك هنا ممتاز جداً ومظبوط عربي)
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
        # 4. التعديل هنا: عكسنا الـ padx في المربعات عشان تدي مسافة من ناحية اليمين
        self.cmb_branch_box.grid(row=0, column=2, sticky="ew", pady=(0, 8), padx=(0, 10))

        ctk.CTkLabel(form, text="رقم العميل:", font=label_font, text_color=COLOR_TEXT_MAIN).grid(
            row=0, column=1, sticky="e", pady=(0, 8)
        )
        self.ent_client_no = ctk.CTkEntry(
            form,
            placeholder_text="اكتب رقم العميل واضغط Enter",
            justify="right",  # إضافة: الكتابة جوه المربع تبدأ من اليمين
            height=40,
            corner_radius=10
        )
        self.ent_client_no.grid(row=0, column=0, sticky="ew", pady=(0, 8), padx=(0, 10))
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
        self.cmb_acc_type_box.grid(row=1, column=2, sticky="ew", pady=(0, 8), padx=(0, 10))

        ctk.CTkLabel(form, text="العملة:", font=label_font, text_color=COLOR_TEXT_MAIN).grid(
            row=1, column=1, sticky="e", pady=(0, 8)
        )
        self.cmb_currency_box, self.cmb_currency = self._create_premium_select(
            form,
            values=["- أدخل العميل أولاً -"],
            default="- أدخل العميل أولاً -",
            title="اختر العملة"
        )
        self.cmb_currency_box.grid(row=1, column=0, sticky="ew", pady=(0, 8), padx=(0, 10))

        # Row 3 (Dates)
        ctk.CTkLabel(form, text="من تاريخ:", font=label_font, text_color=COLOR_TEXT_MAIN).grid(
            row=2, column=3, sticky="e"
        )
        self.ent_date_from = ctk.CTkEntry(
            form,
            placeholder_text="YYYY-MM-DD أو YYYYMMDD",
            justify="right",  # إضافة
            height=40,
            corner_radius=10
        )
        self.ent_date_from.grid(row=2, column=2, sticky="ew", padx=(0, 10))

        ctk.CTkLabel(form, text="إلى تاريخ:", font=label_font, text_color=COLOR_TEXT_MAIN).grid(
            row=2, column=1, sticky="e"
        )
        self.ent_date_to = ctk.CTkEntry(
            form,
            placeholder_text="YYYY-MM-DD أو YYYYMMDD",
            justify="right",  # إضافة
            height=40,
            corner_radius=10
        )
        self.ent_date_to.grid(row=2, column=0, sticky="ew", padx=(0, 10))

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

        # 5. التعديل هنا: محاذاة النص لليمين (anchor="e")
        ctk.CTkLabel(
            info_inner,
            text="بيانات العميل",
            font=("Segoe UI", 12, "bold"),
            text_color=COLOR_TEXT_MAIN
        ).pack(anchor="e")

        self.lbl_branch_info = ctk.CTkLabel(
            info_inner,
            text="—",
            font=("Segoe UI", 12),
            text_color="#4B5563",
            justify="right",  # التعديل هنا لليمين
            anchor="e",  # التعديل هنا لليمين
            wraplength=900
        )
        self.lbl_branch_info.pack(anchor="e", pady=(6, 0))

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

        # 6. التعديل هنا: شريط البحث يروح يمين
        self.ent_search = ctk.CTkEntry(toolbar, placeholder_text="بحث داخل النتائج…", justify="right", height=36,
                                       corner_radius=10)
        self.ent_search.pack(side="right", fill="x", expand=True, padx=(10, 0))

        # زراير التصدير تترص من اليمين للشمال
        btn_export = ctk.CTkButton(
            toolbar, text="🖨️ Export PDF",
            fg_color=FIB_GREEN, hover_color="#0B5C3A",
            height=36, corner_radius=10,
            font=("Segoe UI", 12, "bold"),
            command=self.nuwairy_export_pdf
        )
        btn_export.pack(side="right")

        btn_export_excel = ctk.CTkButton(
            toolbar, text="📊 Export Excel",
            fg_color=FIB_GREEN, hover_color="#0B5C3A",
            height=36, corner_radius=10,
            font=("Segoe UI", 12, "bold"),
            command=self.nuwairy_export_excel
        )
        btn_export_excel.pack(side="right", padx=(0, 10))

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
            align="e",  # 👈 التعديل الأول: محاذاة بيانات الخلايا لليمين
            header_align="e",  # 👈 التعديل الثاني: محاذاة عناوين الأعمدة لليمين
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

        # 1. العنوان والعنوان الفرعي لليمين
        title_wrap = ctk.CTkFrame(header_inner, fg_color="transparent")
        title_wrap.pack(side="right", fill="x", expand=True)  # التعديل هنا: side="right"

        ctk.CTkLabel(
            title_wrap,
            text="🔍 استعلام الأستاذ العام",
            font=("Segoe UI", 22, "bold"),
            text_color=FIB_GREEN
        ).pack(anchor="e")  # التعديل هنا: anchor="e"

        ctk.CTkLabel(
            title_wrap,
            text="ابحث بحساب الأستاذ العام، اختر الفرع والعملة، وحدد فترة التاريخ.",
            font=("Segoe UI", 12),
            text_color="#6B7280"
        ).pack(anchor="e", pady=(4, 0))  # التعديل هنا: anchor="e"

        # 2. أزرار الأكشن لليسار (وتترص من اليمين للشمال)
        actions = ctk.CTkFrame(header_inner, fg_color="transparent")
        actions.pack(side="left")  # التعديل هنا: side="left" (عكس الـ title_wrap)

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
        self.btn_clear_gl.pack(side="right", padx=(10, 0))  # التعديل هنا: side="right" وعكس الـ padx

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
        self.btn_search_gl.pack(side="right")  # التعديل هنا: side="right"

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
        self.cmb_gl_branch_box.grid(row=0, column=2, sticky="ew", pady=(0, 8), padx=(0, 10))  # عكس الـ padx

        ctk.CTkLabel(form, text="الأستاذ العام:", font=label_font, text_color=COLOR_TEXT_MAIN).grid(
            row=0, column=1, sticky="e", pady=(0, 8)
        )

        # 🌟 التعديل هنا: تعريف الدوال أولاً قبل استخدامها في الزرار 🌟 (لم يتم التعديل في المنطق)
        def set_gl_acc_value(selected_val):
            if hasattr(self, 'btn_gl_acc_select'):
                # إضافة: عكسنا السهم ليتناسب مع العربي (السهم على اليسار)
                self.btn_gl_acc_select.configure(text=f"🔽 {selected_val}")
                self.selected_gl_acc = selected_val
            else:
                print("تنبيه: زرار الأستاذ العام غير مسجل في الـ self")

        def open_gl_acc_popup_cmd():
            data = getattr(self, 'all_gl_codes', [])
            if not data:
                data = ["جاري تحميل البيانات، يرجى الانتظار ثانية..."]
            PremiumSearchPopup(self, "اختر الأستاذ العام", data, set_gl_acc_value)

        # ==========================================
        # زرار الأستاذ العام الأخضر (Solid Green)
        # ==========================================
        self.btn_gl_acc_select = ctk.CTkButton(
            form,
            text="🔽 - اختر الأستاذ العام -",  # التعديل هنا: السهم على اليسار
            font=("Segoe UI", 12, "bold"),
            text_color="white",
            fg_color=FIB_GREEN,
            hover_color="#08472C",
            border_width=0,
            height=40,
            corner_radius=10,
            anchor="e",  # النص يبدأ من اليمين
            command=open_gl_acc_popup_cmd
        )
        self.btn_gl_acc_select.grid(row=0, column=0, sticky="ew", pady=(0, 8), padx=(0, 10))  # عكس الـ padx

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
        self.cmb_gl_curr_box.grid(row=1, column=2, sticky="ew", pady=(0, 8), padx=(0, 10))  # عكس الـ padx

        ctk.CTkLabel(form, text="من تاريخ:", font=label_font, text_color=COLOR_TEXT_MAIN).grid(
            row=1, column=1, sticky="e", pady=(0, 8)
        )
        self.ent_gl_date_from = ctk.CTkEntry(
            form,
            placeholder_text="YYYY-MM-DD",
            justify="right",  # التعديل هنا: المؤشر يبدأ من اليمين
            height=40,
            corner_radius=10
        )
        self.ent_gl_date_from.grid(row=1, column=0, sticky="ew", pady=(0, 8), padx=(0, 10))  # عكس الـ padx

        # Row 3 (إلى تاريخ - زرار التحديث)
        ctk.CTkLabel(form, text="إلى تاريخ:", font=label_font, text_color=COLOR_TEXT_MAIN).grid(
            row=2, column=1, sticky="e"
        )
        self.ent_gl_date_to = ctk.CTkEntry(
            form,
            placeholder_text="YYYY-MM-DD",
            justify="right",  # التعديل هنا: المؤشر يبدأ من اليمين
            height=40,
            corner_radius=10
        )
        self.ent_gl_date_to.grid(row=2, column=0, sticky="ew", padx=(0, 10))  # عكس الـ padx

        def refresh_all_gl_data():
            if hasattr(self, 'sys_logger'):
                self.sys_logger.log("🔄 المستخدم طلب تحديث قوائم (الفرع، الأستاذ العام، العملات) يدوياً.")
            if hasattr(self, 'gl_load_codes'): self.gl_load_codes()
            if hasattr(self, 'nuwairy_load_branches'): self.nuwairy_load_branches()
            if hasattr(self, 'gl_load_currencies'): self.gl_load_currencies()

        self.btn_refresh_gl = ctk.CTkButton(
            form,
            text="تحديث القوائم 🔄",  # التعديل هنا: الأيقونة لليسار
            fg_color="#F3F4F6",
            text_color="#111827",
            hover_color="#E5E7EB",
            font=("Segoe UI", 12, "bold"),
            height=40,
            corner_radius=10,
            command=refresh_all_gl_data
        )
        self.btn_refresh_gl.grid(row=2, column=2, sticky="ew", padx=(0, 10))  # عكس الـ padx

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

        # 3. محاذاة كارت المعلومات لليمين
        ctk.CTkLabel(
            info_inner,
            text="بيانات الحساب",
            font=("Segoe UI", 12, "bold"),
            text_color=COLOR_TEXT_MAIN
        ).pack(anchor="e")  # التعديل هنا: anchor="e"

        self.lbl_gl_info = ctk.CTkLabel(
            info_inner,
            text="—",
            font=("Segoe UI", 12),
            text_color="#4B5563",
            justify="right",  # التعديل هنا: justify="right"
            anchor="e",  # التعديل هنا: anchor="e"
            wraplength=900
        )
        self.lbl_gl_info.pack(anchor="e", pady=(6, 0))  # التعديل هنا: anchor="e"

        # 👇👇 الإضافة الجديدة: مكان مخصص لعرض رصيد 31-03-2017
        self.lbl_gl_balance_2017 = ctk.CTkLabel(
            info_inner,
            text="الرصيد في 31-03-2017: 0.00",
            font=("Segoe UI", 13, "bold"),
            text_color="#10B981",  # لون أخضر مميز
            justify="right",
            anchor="e"
        )
        self.lbl_gl_balance_2017.pack(anchor="e", pady=(4, 0))
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

        # 4. شريط البحث وأزرار التصدير لليمين
        self.ent_gl_search = ctk.CTkEntry(
            toolbar,
            placeholder_text="بحث داخل النتائج…",
            justify="right",  # التعديل هنا: المؤشر يبدأ يمين
            height=36,
            corner_radius=10
        )
        self.ent_gl_search.pack(side="right", fill="x", expand=True,
                                padx=(10, 0))  # التعديل هنا: side="right" وعكس الـ padx

        btn_export = ctk.CTkButton(
            toolbar, text="🖨️ Export PDF",
            fg_color=FIB_GREEN, hover_color="#0B5C3A",
            height=36, corner_radius=10,
            font=("Segoe UI", 12, "bold"),
            command=self.gl_export_pdf
        )
        btn_export.pack(side="right")  # التعديل هنا: side="right"

        btn_export_excel = ctk.CTkButton(
            toolbar, text="📊 Export Excel",
            fg_color=FIB_GREEN, hover_color="#0B5C3A",
            height=36, corner_radius=10,
            font=("Segoe UI", 12, "bold"),
            command=self.gl_export_excel
        )
        btn_export_excel.pack(side="right", padx=(0, 10))  # التعديل هنا: side="right" وعكس الـ padx

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

        if hasattr(self, "gl_sheet"):
            loading_row = ["", "", "", "⏳ جاري سحب البيانات...", "", "", "", "", ""]
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

                # 4. حساب الرصيد التراكمي السابق (الافتتاحي)
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

                # =======================================================
                # 🌟 4.5 حساب رصيد 31-03-2017 المخصص (الإضافة الجديدة) 🌟
                # =======================================================
                balance_2017_val = 0.0
                try:
                    bal2017_query = f"SELECT AAMT, ACOD1 FROM [dbo].[{target_table}] WHERE AGL = '{target_sgl}' AND ASB = '{target_ssubb}' AND ADATM <= '20170331'"
                    if target_curr_code is not None:
                        bal2017_query += f" AND ACUR = '{target_curr_code}'"

                    bal2017_df = pd.read_sql(bal2017_query, engine)
                    for row in bal2017_df.itertuples(index=False):
                        t_scod = str(row.ACOD1).strip() if pd.notna(row.ACOD1) else ""
                        try:
                            t_amt = abs(float(row.AAMT))
                        except:
                            t_amt = 0.0

                        if t_scod in credit_codes:
                            balance_2017_val += t_amt
                        elif t_scod in debit_codes:
                            balance_2017_val -= t_amt
                        else:
                            if float(row.AAMT) > 0:
                                balance_2017_val += t_amt
                            else:
                                balance_2017_val -= t_amt
                except Exception as e:
                    if hasattr(self, 'sys_logger'):
                        self.sys_logger.log(f"⚠️ فشل حساب رصيد 2017 للأستاذ العام: {e}", "WARNING")
                # =======================================================

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

                if hasattr(self, 'sys_logger'):
                    self.sys_logger.log(f"تم سحب {len(results_df)} حركة.")

                formatted_data = []
                running_balance = opening_balance

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
                        aseq_val
                    ])

                if not formatted_data:
                    formatted_data = [["", "", "", "لا توجد حركات مطابقة لشروط البحث", "", "", "", "", ""]]

                # عرض البيانات في الشيت
                self.after(0, lambda: self.gl_sheet.set_sheet_data(formatted_data, reset_col_positions=False,
                                                                   reset_row_positions=True))

                # 🌟 تحديث واجهة المستخدم برصيد 2017 اللي ضفناه في الخطوة السابقة 🌟
                if hasattr(self, 'lbl_gl_balance_2017'):
                    self.after(0, lambda: self.lbl_gl_balance_2017.configure(
                        text=f"الرصيد في 31-03-2017: {balance_2017_val:,.2f}"))

                # 🌟 حفظ البيانات الخاصة بالتصدير للـ PDF (Meta Data) 🌟
                self.gl_last_meta = {
                    "gl_acc_name": gl_acc_name,
                    "branch_name": branch_name,
                    "currency": currency_name,
                    "date_from": date_from,
                    "date_to": date_to,
                    "opening_balance": f"{opening_balance:,.2f}",
                    "balance_2017": f"{balance_2017_val:,.2f}"
                }

                if hasattr(self, 'sys_logger'):
                    self.sys_logger.log("✅ تم سحب وعرض بيانات الأستاذ العام بنجاح.")

            except Exception as e:
                if hasattr(self, 'sys_logger'):
                    self.sys_logger.log(f"❌ خطأ أثناء البحث: {e}", "ERROR")
                self.after(0, lambda: messagebox.showerror("خطأ برمجي", f"حدث خطأ أثناء جلب البيانات:\n{e}"))
                self.after(0, lambda: self.gl_sheet.set_sheet_data([["", "", "", "❌ حدث خطأ", "", "", "", "", ""]]))

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
        """تصدير PDF بالتنسيق السليم واعتبار أول حركة هي الرصيد الافتتاحي مع إضافة رصيد 2017"""
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

        # ✅ قراءة رصيد الافتتاح من أول حركة في الشيت مباشرة
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

            # ========================================================
            # 🌟 إضافة رصيد 2017 إلى الـ Info Table في ملف الـ PDF 🌟
            # ========================================================
            right_lines = [f"حساب الأستاذ العام: {gl_acc_name}", f"الفرع: {branch_name}"]
            left_lines = [f"العملة: {currency_name}", period_text if period_text else "الفترة: غير محددة"]

            # بنجيب رصيد 2017 من الميتا داتا اللي حفظناها ونضيفه كسطر ثالث في اليمين
            if hasattr(self, 'gl_last_meta') and 'balance_2017' in self.gl_last_meta:
                bal_2017 = self.gl_last_meta['balance_2017']
                right_lines.append(f"الرصيد في 31-03-2017: {bal_2017}")
            # ========================================================

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
                formatted_date = raw_date.replace(" ", "<br/>")
                date_val = Paragraph(formatted_date, st_center_date)

                desc_val = str(r[4]).strip()
                aseq_val = str(r[8]).strip() if len(r) > 8 else ""

                if aseq_val and aseq_val not in ["None", "", "0"]:
                    desc_ar = ar(desc_val)
                    aseq_ar = ar(f"رقم النمارة: {aseq_val}")
                    final_desc_html = f"{desc_ar}<br/><font color='#5B6770' size='8'>{aseq_ar}</font>"
                else:
                    final_desc_html = ar(desc_val)

                desc_para = Paragraph(final_desc_html, st_right)

                debit_val = str(r[5])
                credit_val = str(r[6])
                bal_val = str(r[7])

                table_data.append([bal_val, credit_val, debit_val, desc_para, date_val])

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
            if hasattr(self, 'sys_logger'):
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
                    q3 = text(f"""
                                                        SELECT DISTINCT EBname, EBADRS3, EBADRS4
                                                        FROM {table_name}
                                                        WHERE EBCLNT = :client_no
                                                    """)
                    df3 = pd.read_sql(q2, engine, params={"client_no": client_no})
                    ebname = str(df2.iloc[0].get("EBname", "") or "")
                    ebadr3 = str(df2.iloc[0].get("EBADRS3", "") or "")
                    ebadr4 = str(df2.iloc[0].get("EBADRS4", "") or "")
                    ebself.lbl_branch_info.configure(text=f"اسم العميل: {ebname}\nالعنوان: {ebadr3}   {ebadr4}")
                    #self.lbl_branch_info.configure(text="لا توجد بيانات فرع/عنوان لهذا العميل.")

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

                    # print(f"🔴 DEBUG 1: تم تحميل عدد {len(self.add_code_to_name)} كود من جدول TBL_add_codes")
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

            # =========================================================
            # بداية التدخل الجراحي الموحد (PBAL + رصيد 2017 + الرصيد الافتتاحي)
            # =========================================================

            pbal_val = 0.0
            actual_opening_balance = 0.0
            balance_2017_val = 0.0

            # ✅ 1. استخراج الرصيد الثابت (PBAL) لتاريخ 30-06-2016
            try:
                # 🛑 تنبيه هام: غير 'TBL_Accounts_Master' لاسم الجدول الحقيقي عندك اللي فيه الـ PBAL
                pbal_query = text(f"""
                            SELECT ISNULL(PBAL, 0) 
                            FROM {table_name} 
                            WHERE NCLNT = :client_no AND ngl = :acc_code AND ncur = :curr_code
                        """)
                with engine.connect() as conn:
                    res = conn.execute(pbal_query, {"client_no": client_no, "acc_code": str(acc_type_code),
                                                    "curr_code": str(currency_code)}).fetchone()
                    if res:
                        pbal_val = float(res[0])
                        # 🔥 تعديل تصفير المكشوف: لو رصيد المنقول نفسه جاي بالسالب نصفره
                        if pbal_val < 0:
                            pbal_val = 0.0
            except Exception as e:
                if hasattr(self, 'sys_logger'):
                    self.sys_logger.log(f"⚠️ فشل جلب PBAL: {e}", "WARNING")

            # ✅ 2. حساب رصيد 2017 الصحيح (رصيد الافتتاح PBAL + الحركات لحد 31-03-2017)
            balance_2017_val = pbal_val
            try:
                bal_2017_query = f"""
                            SELECT ncod1, namt
                            FROM {table_name} WITH (NOLOCK)
                            WHERE NCLNT = :client_no 
                              AND ngl = :acc_code 
                              AND ncur = :curr_code 
                              AND ndatm > '20160630' 
                              AND ndatm <= '20170331'
                        """
                bal_2017_params = {"client_no": client_no, "acc_code": str(acc_type_code),
                                   "curr_code": str(currency_code)}
                with engine.connect() as conn:
                    bal_2017_df = pd.read_sql(text(bal_2017_query), conn, params=bal_2017_params)

                for r_bal in bal_2017_df.itertuples(index=False):
                    t_code = str(getattr(r_bal, "ncod1", "")).strip()
                    t_amt_raw = getattr(r_bal, "namt", 0.0)
                    t_amt = float(t_amt_raw if pd.notnull(t_amt_raw) else 0.0)
                    amt_abs = abs(t_amt)

                    if t_code in ("3", "4"):
                        balance_2017_val -= amt_abs
                    elif t_code in ("1", "2"):
                        balance_2017_val += amt_abs
                    else:
                        if t_amt < 0:
                            balance_2017_val -= amt_abs
                        else:
                            balance_2017_val += amt_abs
            except Exception as e:
                if hasattr(self, 'sys_logger'):
                    self.sys_logger.log(f"⚠️ فشل جلب رصيد 2017: {e}", "WARNING")

            # =========================================================
            # ✅ 3. حساب الرصيد الافتتاحي الفعلي + (ديباج / Debugging)
            # =========================================================
            if date_from_val:
                try:
                    # 🔥 تعديل: ضفنا ndatm للـ SELECT و ORDER BY عشان نحسب الرصيد حركة بحركة صح
                    bal_query = f"""
                                    SELECT ncod1, namt, ndatm
                                    FROM {table_name} WITH (NOLOCK)
                                    WHERE NCLNT = :client_no 
                                      AND ngl = :acc_code 
                                      AND ncur = :curr_code 
                                      AND ndatm < :date_from
                                    ORDER BY ndatm ASC
                                """
                    bal_params = {"client_no": client_no, "acc_code": str(acc_type_code),
                                  "curr_code": str(currency_code), "date_from": date_from_val}

                    with engine.connect() as conn:
                        bal_df = pd.read_sql(text(bal_query), conn, params=bal_params)

                    debug_total_in = 0.0
                    debug_total_out = 0.0

                    for r_bal in bal_df.itertuples(index=False):
                        t_code = str(getattr(r_bal, "ncod1", "")).strip()
                        t_amt = float(getattr(r_bal, "namt", 0.0) or 0.0)
                        t_ndatm = str(getattr(r_bal, "ndatm", "")).strip() # 🔥 استخراج التاريخ
                        amt_abs = abs(t_amt)

                        if t_code in ("3", "4"):  # خصم
                            actual_opening_balance -= amt_abs
                            debug_total_out += amt_abs
                        elif t_code in ("1", "2"):  # إضافة
                            actual_opening_balance += amt_abs
                            debug_total_in += amt_abs
                        else:
                            if t_amt < 0:
                                actual_opening_balance -= amt_abs
                                debug_total_out += amt_abs
                            else:
                                actual_opening_balance += amt_abs
                                debug_total_in += amt_abs

                        # 🔥 تعديل تصفير المكشوف: لو الرصيد الافتتاحي نزل سالب قبل أو في 30-6 بنصفره
                        if actual_opening_balance < 0 and t_ndatm <= '20160630':
                            actual_opening_balance = 0.0

                    if hasattr(self, 'sys_logger'):
                        self.sys_logger.log(
                            f"🔎 ديباج الرصيد الافتتاحي -> إضافات: {debug_total_in:,.2f} | خصومات: {debug_total_out:,.2f} | الرصيد النهائي: {actual_opening_balance:,.2f}")

                except Exception as e:
                    if hasattr(self, 'sys_logger'):
                        self.sys_logger.log(f"⚠️ فشل حساب الرصيد الافتتاحي: {e}", "WARNING")
            # =========================================================
            # نهاية التدخل الجراحي الموحد
            # =========================================================

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

            view_df["nbian"] = view_df["nbian"].fillna("").astype(str).str.strip()
            view_df["nbian"] = view_df["nbian"].replace(["nan", "NaN", "None"], "")

            view_df["ncod1"] = view_df["ncod1"].astype(str).str.strip()
            view_df["namt"] = pd.to_numeric(view_df["namt"], errors="coerce").fillna(0)

            if "ncod2" in view_df.columns:
                view_df["ncod2"] = view_df["ncod2"].fillna("").astype(str).str.strip()
                view_df["ncod2"] = view_df["ncod2"].replace(["nan", "NaN", "None", "<NA>"], "")
                view_df["ncod2"] = view_df["ncod2"].apply(lambda x: x[:-2] if str(x).endswith(".0") else x)

            trx_map = getattr(self, "trx_code_to_name", {})
            acc_map = getattr(self, "acc_code_to_name", {})
            add_map = getattr(self, "add_code_to_name", {})
            rows_data = []

            for r in view_df.itertuples(index=False):
                ndatm = str(getattr(r, "ndatm", "")).strip()
                ndatm_fmt = f"{ndatm[:4]}-{ndatm[4:6]}-{ndatm[6:]}" if len(ndatm) == 8 and ndatm.isdigit() else ndatm

                trx_code = str(getattr(r, "ncod1", "")).strip()
                trx_name = str(trx_map.get(trx_code, trx_code) or "").strip()
                ncod2_val = str(getattr(r, "ncod2", "")).strip()
                doc_name = str(add_map.get(ncod2_val, "")).strip()

                amt = float(getattr(r, "namt", 0.0))
                amt_abs = abs(amt)

                if trx_code in ("3", "4"):
                    credit, debit = 0.0, amt_abs
                elif trx_code in ("1", "2"):
                    credit, debit = amt_abs, 0.0
                else:
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
                    'doc_name': doc_name
                })

            rows_data.sort(key=lambda x: (
                x['ndatm_raw'],
                x['debit'] > 0,
                max(x['credit'], x['debit'])
            ))

            running_balance = actual_opening_balance
            passed_cutoff = True if (date_from_val and date_from_val > '20160630') else False

            final_rows_data = []

            for item in rows_data:
                if not passed_cutoff and item['ndatm_raw'] > '20160630':
                    settlement_row = {
                        'ndatm_raw': '20160630',
                        'ndatm_fmt': '2016-06-30',
                        'desc': 'رصيد منقول (PBAL)',
                        'credit': 0.0,
                        'debit': 0.0,
                        'trx_name': 'تسوية',
                        'gl_main_name': '',
                        'gl_sub': '',
                        'nseq': '',
                        'doc_name': '',
                        'balance': pbal_val
                    }
                    final_rows_data.append(settlement_row)
                    running_balance = pbal_val
                    passed_cutoff = True

                running_balance += item['credit'] - item['debit']

                # 🔥 تعديل تصفير المكشوف: لو الرصيد نزل بالسالب جوه كشف الحساب نفسه قبل 30-06-2016
                if running_balance < 0 and item['ndatm_raw'] <= '20160630':
                    running_balance = 0.0

                item['balance'] = running_balance
                final_rows_data.append(item)

            opening_balance = actual_opening_balance
            rows_data = final_rows_data

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
                    item['doc_name']
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

                desc_flow = []

                # 1. المستند الأول (لو موجود)
                if doc_name:
                    desc_flow.append(Paragraph(ar(f"{doc_name}"), st_right_small))

                # 2. البيان (أساسي)
                desc_flow.append(Paragraph(ar(t(desc) if desc else "—"), st_right))

                # 3. رقم النمارة (لو موجود)
                if nseq:
                    desc_flow.append(Paragraph(ar(f"{t('رقم النمارة:')} {nseq}"), st_right_small))
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
