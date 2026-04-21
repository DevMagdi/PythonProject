import os
from dotenv import load_dotenv

load_dotenv()


class SystemConfig:
    IS_ADMIN_VERSION = False
    APP_NAME = os.getenv("APP_NAME", "FGS Smart ETL Integrator")
    COMPANY_NAME = os.getenv("COMPANY_NAME", "First Gulf Solutions")
    VERSION = os.getenv("APP_VERSION", "3.5.0")
    SECRET_SALT = os.getenv("SECRET_SALT", "DEFAULT_SALT")
    SECRET_SALT = "FGS_SECURE_HASH_KEY_2025_X99"

    BATCH_SIZE = int(os.getenv("BATCH_SIZE", 100000))
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", 3))
    RETRY_DELAY = int(os.getenv("RETRY_DELAY", 5))
    LOG_FILE = os.getenv("LOG_FILE", "sys.log")

    DEFAULT_SERVER = os.getenv("DEFAULT_DB_SERVER", ".")
    DEFAULT_DB = os.getenv("DEFAULT_DB_NAME", "DW")

    # ألوان الهوية البصرية المستخرجة من اللوجو
    COLOR_PRIMARY = "#483D8B"  # بنفسجي غامق (Purple)
    COLOR_ACCENT = "#F58220"  # برتقالي (Orange)
    COLOR_BG = "#F4F6F9"  # رمادي فاتح للخلفية
    COLOR_WHITE = "#FFFFFF"
    # 🔴 وضع الرفع الأولي (Initial Load)
    # True = سرعة قصوى (بدون فحص تكرار وبدون فهارس) -> يستخدم لأول مرة فقط
    # False = الوضع الطبيعي (أمان وفهارس) -> يستخدم للشغل اليومي
    IS_INITIAL_LOAD_MODE = True
