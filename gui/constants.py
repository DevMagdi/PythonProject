# -*- coding: utf-8 -*-
"""
ثوابت الألوان ومسارات الموارد المشتركة في كل أجزاء التطبيق.

كانت هذه القيم مكررة داخل كل شاشة على حدة؛ هنا نعرّفها مرة واحدة فقط.
"""
import os
import sys

import customtkinter

# ========================================================
# 🎨 BRANDING & THEME
# ========================================================
customtkinter.set_appearance_mode("Light")
customtkinter.set_default_color_theme("green")

FIB_GREEN = "#00563B"        # Official Dark Green
FIB_GREEN_DARK = "#004426"   # Hover / emphasis green
FIB_GOLD = "#C5A059"         # Gold Accent
COLOR_BG = "#F4F6F8"         # Light Gray Background
COLOR_WHITE = "#FFFFFF"
COLOR_TEXT_MAIN = "#2D3436"

# ألوان الوضع الليلي للداتا (Monitor & History)
COLOR_DARK_BG = "#1A1A1A"    # خلفية قريبة من الأسود عشان الأخضر يبان
COLOR_TEXT_LITE = "#00FF41"  # أخضر Matrix
COLOR_RED_ALERT = "#E74C3C"

# ========================================================
# 🎨 Premium palette (used by all inquiry screens)
# كانت مكررة بداخل كل setup_xxx_ui — أصبحت هنا مرة واحدة
# ========================================================
BG_MAIN = "#F8FAFC"
CARD_BG = "#FFFFFF"
BOX_BG = "#F1F5F9"
TEXT_DARK = "#0F172A"
TEXT_MUTED = "#64748B"
STOP_COLOR = "#B45309"       # برتقالي/بني مميز للشيكات الموقوفة
ERROR_RED = "#EF4444"
SECTION_GREEN = "#005C34"    # الأخضر المعتمد داخل الشاشات الداخلية


# محاولة استدعاء pandas لتصدير الإكسل
try:
    import pandas  # noqa: F401
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for Nuitka onefile."""
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
    if getattr(sys, 'frozen', False) or '__compiled__' in globals():
        application_path = os.path.dirname(os.path.abspath(sys.argv[0]))
    else:
        # gui/constants.py → parent of the gui package is the application root
        application_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    return os.path.join(application_path, filename)


def get_resource_path(filename):
    """
    دي للملفات الثابتة زي الصور (للقراءة فقط)
    """
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS  # مسار الـ Temp بتاع PyInstaller
    else:
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, filename)
