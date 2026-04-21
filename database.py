import urllib
from sqlalchemy import create_engine

class DatabaseEngine:
    # خلينا المتغيرات (user, password, logger) اختيارية بقيم افتراضية None
    def __init__(self, server, database, user=None, password=None, logger=None):
        self.server = server
        self.database = database
        self.user = user
        self.password = password
        self.logger = logger
        self.engine = self._create_engine()

    def _create_engine(self):
        try:
            # ⛔ منع الاتصال لو البيانات لسه متسجلتش (عشان نلغي السطر اللي بيضايقك)
            if not self.server or self.server.strip() == "":
                return None

            driver = 'ODBC Driver 17 for SQL Server'
            log_func = self.logger.log if self.logger else print

            # ✅ التحقق: لو فيه يوزر وباسورد، استخدم SQL Auth علطول
            if self.user and self.password:
                params = urllib.parse.quote_plus(
                    f"DRIVER={{{driver}}};SERVER={self.server};DATABASE={self.database};UID={self.user};PWD={self.password};"
                )
                #log_func(f"🔌 Connecting to {self.server} (SQL Auth)...")
            else:
                # لو مفيش، استخدم Windows Auth (كحل أخير فقط)
                params = urllib.parse.quote_plus(
                    f"DRIVER={{{driver}}};SERVER={self.server};DATABASE={self.database};Trusted_Connection=yes;"
                )
                #log_func(f"🔌 Connecting to {self.server} (Windows Auth)...")

            conn_str = f"mssql+pyodbc:///?odbc_connect={params}"
            engine = create_engine(conn_str, fast_executemany=True)

            # اختبار سريع للاتصال
            with engine.connect() as conn:
                pass
            return engine

        except Exception as e:
            if self.logger:
                self.logger.log(f"❌ Database Connection Error: {e}", "ERROR")
            return None