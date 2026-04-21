import sys
import os
import json
from tkinter import messagebox
import warnings
import traceback
import datetime
import tkinter as tk
import getpass

# =========================================================
# 🛠️ تحديد مسار البرنامج المباشر
# =========================================================
def get_real_path():
    """دالة لمعرفة المسار الحقيقي للبرنامج سواء كان سكريبت أو EXE"""
    if getattr(sys, 'frozen', False) or '__compiled__' in globals():
        return os.path.dirname(os.path.abspath(sys.argv[0]))
    else:
        return os.path.dirname(os.path.abspath(__file__))

REAL_PATH = get_real_path()
os.chdir(REAL_PATH)

# =========================================================

def global_exception_handler(exctype, value, tb):
    """التقاط الانهيارات وتسجيلها في نفس مسار البرنامج"""
    try:
        username = getpass.getuser()
    except:
        username = os.environ.get('USERNAME', 'Unknown_User')

    import re
    username = re.sub(r'[\\/*?:"<>|]', "_", username)

    # حفظ ملف اللوج جنب الـ EXE مباشرة
    log_path = os.path.join(REAL_PATH, f"FIB_ETL_logs_{username}.log")
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    error_msg = "".join(traceback.format_exception(exctype, value, tb))
    error_root = tk.Tk()
    error_root.withdraw()

    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"\n[{timestamp}] [CRITICAL ERROR] App Crashed:\n")
            f.write(error_msg + "\n")
            f.write("=" * 50 + "\n")
        error_root.iconbitmap(os.path.join(REAL_PATH, "logo.ico"))
    except Exception as e:
        print(f"Failed to write crash log: {e}")

    messagebox.showerror("Fatal Error", f"حدث خطأ غير متوقع وتم إغلاق البرنامج.\nتم حفظ الخطأ في:\n{log_path}",
                         parent=error_root)
    error_root.destroy()

sys.excepthook = global_exception_handler

# استدعاء الواجهة
try:
    from gui import FGSApp
except ImportError as e:
    messagebox.showerror("Critical Error", f"Failed to load GUI Module:\n{e}")
    sys.exit(1)

# استدعاء نظام الحماية
try:
    from license_guard import LicenseGuard
except ImportError:
    LicenseGuard = None

warnings.filterwarnings("ignore")

if __name__ == "__main__":

    # 1. تجهيز بيانات الرخصة الافتراضية
    license_data_package = {
        "active": False,
        "mid": "LOADING...",
        "expiry": "DEMO MODE",
        "key_str": ""
    }

    # 2. محاولة جلب رقم الجهاز
    if LicenseGuard:
        try:
            real_machine_id = LicenseGuard.get_machine_fingerprint()
            license_data_package["mid"] = real_machine_id
        except Exception as e:
            license_data_package["mid"] = "ID-ERROR"
            print(f"ID Error: {e}")

        # 🔥 قراءة الكونفيج مباشرة من نفس الفولدر اللي فيه البرنامج
        config_path = os.path.join(REAL_PATH, "config.json")
        saved_key = ""

        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if "license_info" in data and "key" in data["license_info"]:
                        saved_key = data["license_info"]["key"]
            except Exception as e:
                print(f"Config Load Error: {e}")

        # 4. لو لقينا كود محفوظ، نفحصه فوراً
        if saved_key:
            license_data_package["key_str"] = saved_key
            is_valid, msg = LicenseGuard.validate_license_string(saved_key)

            if is_valid:
                expiry_date = msg.replace("✅ Licensed until:", "").strip()
                license_data_package["active"] = True
                license_data_package["expiry"] = expiry_date
            else:
                license_data_package["active"] = False
                license_data_package["expiry"] = "EXPIRED / INVALID"

    # 5. تشغيل التطبيق
    try:
        app = FGSApp(license_data=license_data_package)
        app.mainloop()
    except Exception as e:
        messagebox.showerror("Crash", f"Application Crashed:\n{e}")