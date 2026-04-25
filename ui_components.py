"""
UI Components Module
مكونات الواجهة الأساسية والـ Classes الرئيسية
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
from PIL import Image
import os
import sys

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
COLOR_DARK_BG = "#1A1A1A"
COLOR_TEXT_LITE = "#00FF41"
COLOR_RED_ALERT = "#E74C3C"


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for Nuitka onefile"""
    if "__compiled__" in globals():
        base_path = os.path.dirname(__file__)
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def get_config_path(filename="config.json"):
    """دالة ذكية لتحديد مسار حفظ الإعدادات متوافقة مع Nuitka."""
    import sys
    import os

    if getattr(sys, 'frozen', False) or '__compiled__' in globals():
        application_path = os.path.dirname(os.path.abspath(sys.argv[0]))
    else:
        application_path = os.path.dirname(os.path.abspath(__file__))

    return os.path.join(application_path, filename)


def get_resource_path(filename):
    """دي للملفات الثابتة زي الصور (للقراءة فقط)"""
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, filename)


class PremiumSearchPopup(ctk.CTkToplevel):
    """نافذة بحث فخمة مع تصفية وتحديد"""
    
    def __init__(self, parent, title, data_list, callback):
        super().__init__(parent)
        self.callback = callback
        self.all_data = data_list

        self.title(title)
        self.geometry("550x600")
        self.attributes("-topmost", True)
        self.overrideredirect(True)
        self.configure(fg_color="#0B5C3A")

        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() // 2) - (550 // 2)
        y = parent.winfo_rooty() + (parent.winfo_height() // 2) - (600 // 2)
        self.geometry(f"+{x}+{y}")

        main_container = ctk.CTkFrame(self, fg_color="#FFFFFF", corner_radius=12, border_width=2,
                                      border_color="#0B5C3A")
        main_container.pack(fill="both", expand=True, padx=2, pady=2)

        header = ctk.CTkFrame(main_container, fg_color="#0B5C3A", corner_radius=10)
        header.pack(fill="x", padx=5, pady=(5, 15))

        btn_close = ctk.CTkButton(header, text="✕", width=35, height=35, fg_color="#08472C",
                                  text_color="white", hover_color="#C62828", font=("Segoe UI", 16, "bold"),
                                  corner_radius=8, command=self.destroy)
        btn_close.pack(side="left", padx=10, pady=10)

        lbl_title = ctk.CTkLabel(header, text=f"✨ {title} ✨", text_color="white", font=("Segoe UI", 16, "bold"))
        lbl_title.pack(side="right", padx=15, pady=10)

        search_frame = ctk.CTkFrame(main_container, fg_color="transparent")
        search_frame.pack(fill="x", padx=20, pady=(0, 10))

        btn_clear = ctk.CTkButton(
            search_frame, text="مسح", width=60, height=45,
            fg_color="#F3F4F6", text_color="#4B5563", hover_color="#E5E7EB", font=("Segoe UI", 13, "bold"),
            corner_radius=10, command=self.clear_search
        )
        btn_clear.pack(side="left", padx=(0, 10))

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

        self.lbl_info = ctk.CTkLabel(main_container, text="", text_color="#6B7280", font=("Segoe UI", 11))
        self.lbl_info.pack(anchor="e", padx=25, pady=(0, 5))

        self.list_frame = ctk.CTkScrollableFrame(
            main_container,
            fg_color="#FFFFFF",
            corner_radius=10,
            border_width=1,
            border_color="#E5E7EB"
        )
        self.list_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

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
        for widget in self.list_frame.winfo_children():
            widget.destroy()

        max_display = 100
        display_data = data[:max_display]

        if len(data) > max_display:
            self.lbl_info.configure(text=f"يتم عرض أول {max_display} نتيجة. يرجى كتابة المزيد في البحث للتخصيص.")
        elif len(data) == 0:
            self.lbl_info.configure(text="لا توجد نتائج مطابقة.")
        else:
            self.lbl_info.configure(text=f"تم العثور على {len(data)} نتيجة.")

        for item in display_data:
            btn = ctk.CTkButton(
                self.list_frame,
                text=item,
                anchor="e",
                font=("Segoe UI", 14),
                fg_color="transparent",
                text_color="#111827",
                hover_color="#E8F5E9",
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
