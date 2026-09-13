import os
import sys
import getpass
import datetime
import re
import hashlib


# 1️⃣ إضافة الدالة الناقصة لجلب المسار الحقيقي للبرنامج
def get_real_path():
    """دالة لمعرفة المسار الحقيقي للبرنامج سواء كان سكريبت أو EXE"""
    if getattr(sys, 'frozen', False) or '__compiled__' in globals():
        return os.path.dirname(os.path.abspath(sys.argv[0]))
    else:
        return os.path.dirname(os.path.abspath(__file__))


def get_user_data_dir():
    """إرجاع مجلد خاص بالمستخدم الحالي لحفظ الإعدادات واللوجات (Citrix Ready)"""
    app_data_dir = os.environ.get('LOCALAPPDATA', os.path.expanduser('~'))
    fgs_dir = os.path.join(app_data_dir, "FGS_Smart_ETL")
    os.makedirs(fgs_dir, exist_ok=True)
    return fgs_dir


def get_config_path(filename="config.json"):
    """قراءة الإعدادات من نفس مجلد البرنامج الرئيسي (Shared on Citrix)"""
    return os.path.join(get_real_path(), filename)


# 2️⃣ إزالة التكرار والاحتفاظ بنسخة واحدة ذكية ونظيفة
def get_log_path():
    """مسار ذكي لسيتركس: يحفظ اللوج في فولدر خاص بكل مستخدم"""
    try:
        username = getpass.getuser()
    except:
        username = os.environ.get('USERNAME', 'Unknown_User')

    # تنظيف اسم المستخدم من أي علامات زي \ بتاعت الدومين
    username = re.sub(r'[\\/*?:"<>|]', "_", username)

    return os.path.join(get_user_data_dir(), f"FIB_ETL_logs_{username}.log")


class EnterpriseLogger:
    def __init__(self, callback=None):
        self.callback = callback
        self.log_file = get_log_path()

        # 🔥 جلب اسم المستخدم الفعلي اللي فاتح الـ Session على Citrix
        try:
            self.current_user = getpass.getuser()
        except:
            self.current_user = os.environ.get('USERNAME', 'Unknown_User')

    def log(self, message, type="INFO", indent=0):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        prefix = " " * (indent * 4)

        # 🔥 إضافة اسم المستخدم في كل سطر لوج أوتوماتيكياً
        full_msg = f"[{timestamp}] [{type}] [User: {self.current_user}] {prefix}{message}"

        # 1. طباعة في الكونسول (للمبرمج)
        print(full_msg)

        # 2. إرسال للواجهة (للمستخدم)
        if self.callback:
            try:
                self.callback(full_msg + "\n", type)
            except:
                pass

        # 3. 📝 تسجيل في الملف الخاص بالمستخدم في LOCALAPPDATA
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(full_msg + "\n")
        except:
            pass


class DataProcessor:
    @staticmethod
    def clean_column_name(col_name):
        if not col_name: return "EMPTY_COL"
        col_name = str(col_name).strip().upper()
        # تنظيف الاسم والسماح بالحروف والأرقام فقط
        clean = re.sub(r'[^\w\u0600-\u06FF]+', '_', col_name)
        return clean.strip('_')

    @staticmethod
    def generate_row_hash(df):
        """
        🚀 Ultra-Fast Vectorized Hashing
        """
        # تحويل الداتا كلها لنصوص وتعبئة الفراغات
        # استخدام fillna مهم جداً عشان الـ Null ميبوظش الهاش
        df_str = df.astype(str).fillna("##NULL##")

        # دمج الأعمدة كلها في نص واحد طويل لكل صف
        # Axis=1 يعني ادمج بالعرض (الصف)
        combined = df_str.apply(lambda x: '|'.join(x), axis=1)

        # حساب MD5
        return combined.apply(lambda x: hashlib.md5(x.encode('utf-8')).hexdigest())