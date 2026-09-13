import pyodbc
import pandas as pd
from sqlalchemy import create_engine
import urllib


class AccessToSQL:
    # 👇 ضفنا logger_callback عشان نقدر نبعت الرسايل للواجهة
    def __init__(self, access_path, server, sql_db, logger_callback=None):
        self.access_path = access_path
        self.server = server
        self.sql_db = sql_db
        self.logger = logger_callback  # دي الدالة اللي هتكتب في الشاشة

        # إعداد الاتصال SQL Server
        params = urllib.parse.quote_plus(
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={server};DATABASE={sql_db};Trusted_Connection=yes;"
        )
        self.sql_engine = create_engine(f"mssql+pyodbc:///?odbc_connect={params}")

    def log(self, msg):
        """دالة مساعدة عشان لو مفيش واجهة يطبع في الكونسول"""
        if self.logger:
            self.logger(msg)
        else:
            print(msg)

    def get_access_tables(self):
        conn_str = (
            r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};"
            f"DBQ={self.access_path};"
        )

        try:
            conn = pyodbc.connect(conn_str)
            cursor = conn.cursor()

            table_list = []
            for row in cursor.tables():
                if row.table_type == 'TABLE' and 'MSys' not in row.table_name:
                    table_list.append(row.table_name)

            conn.close()
            return table_list, conn_str
        except Exception as e:
            self.log(f"❌ Error connecting to Access: {e}")
            return [], None

    def log(self, msg):
        """دالة للطباعة وتسجيل اللوج"""
        # 1. يبعت للشاشة لو الواجهة موجودة
        if self.logger:
            self.logger(msg)
        else:
            print(msg)

        # 2. يكتب في ملف اللوج
        try:
            import datetime, os
            log_path = os.path.join(os.getcwd(), "FibLogSystem.log")
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] [INFO] {msg}\n")
        except Exception:
            pass
    def migrate(self, mode='replace', target_table=None):
        """
        :param mode: 'replace' (يمسح القديم) or 'append' (يزود عليه)
        :param target_table: اسم الجدول المجمع (لو فاضي يبقى كل جدول لوحده)
        """
        self.log(f"🔍 Scanning Access File: {self.access_path}...")
        tables, conn_str = self.get_access_tables()

        if not tables:
            self.log("⚠️ No tables found or Connection failed.")
            return

        # 1️⃣ منطق التجهيز للدمج (Merge Logic)
        # لو المستخدم اختار دمج + استبدال: لازم نمسح الجدول الكبير مرة واحدة في الأول
        if target_table and mode == 'replace':
            self.log(f"🧹 Dropping target table [{target_table}] to start fresh...")
            try:
                from sqlalchemy import text
                with self.sql_engine.connect() as con:
                    # كود SQL لمسح الجدول لو موجود
                    con.execute(text(f"IF OBJECT_ID('{target_table}', 'U') IS NOT NULL DROP TABLE {target_table}"))
                    con.commit()
            except Exception as e:
                self.log(f"⚠️ Warning dropping table: {e}")

            # 💡 تركة مهمة: بنحول الوضع لـ append عشان لما اللوب يلف، يزود الداتا مش يمسح اللي قبله
            mode = 'append'

        try:
            acc_conn = pyodbc.connect(conn_str)
            msg = f"🚀 Merging {len(tables)} tables into [{target_table}]..." if target_table else f"🚀 Processing {len(tables)} tables separately..."
            self.log(msg)

            for tbl in tables:
                try:
                    self.log(f"🔄 Reading source: [{tbl}]...")

                    # قراءة الداتا من أكسس
                    query = f"SELECT * FROM [{tbl}]"
                    df = pd.read_sql(query, acc_conn)

                    # 2️⃣ تحديد الوجهة (Target Logic)
                    if target_table:
                        # لو دمج: بنزود عمود اسمه Source_Origin عشان نعرف الداتا دي جاية منين
                        df['Source_Origin'] = tbl
                        dest_name = target_table
                    else:
                        # لو عادي: الجدول ينزل بنفس اسمه
                        dest_name = tbl

                        # 3️⃣ الكتابة في السيكوال
                    df.to_sql(dest_name, self.sql_engine, if_exists=mode, index=False)

                    self.log(f"✅ Loaded data from [{tbl}] into SQL Table [{dest_name}] ({len(df)} rows).")

                except Exception as e:
                    self.log(f"❌ Failed to migrate [{tbl}]: {e}")

            acc_conn.close()
            self.log("🏁 Migration Completed Successfully!")

        except Exception as e:
            self.log(f"❌ Critical Error: {e}")