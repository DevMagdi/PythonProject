import os
import shutil
import threading
import time
import datetime
import gc
import re

import pandas as pd
import hashlib
import warnings

from sqlalchemy import text, event
from sqlalchemy.types import NVARCHAR
from utils import EnterpriseLogger, DataProcessor
from database import DatabaseEngine

warnings.filterwarnings("ignore")


class ETLOrchestrator:
    def __init__(self, server, db, user, password, root_folder, gui_log_callback):
        self.logger = EnterpriseLogger(gui_log_callback)
        self.root_folder = root_folder

        # ومررهم للـ DatabaseEngine 👇
        self.db = DatabaseEngine(server, db, user, password, self.logger)

        self._enable_fast_execution(self.db.engine)

        self.global_schema_map = {}
        self.table_name = ""
        self.stop_event = threading.Event()
        self._init_system_tables()
    # ---------------------------------------------------------
        # ---------------------------------------------------------
    # الدالة المساعدة للطباعة وتسجيل اللوج في ملف
    # ---------------------------------------------------------
    def _log(self, msg, level="INFO"):
        # 1. بيبعت الرسايل للشاشة (الواجهة)
        self.logger.log(msg)

        # 2. 🔥 التعديل الجديد: يكتب في ملف اللوج عشان العميل يلاقيه
        try:
            # نجيب مسار البرنامج الحالي عشان ملف اللوج ينزل جنب الـ exe
            log_path = os.path.join(os.getcwd(), "FibLogSystem.log")

            # نجيب الوقت الحالي
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # نفتح الملف ونضيف فيه السطر الجديد (a = append)
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] [{level}] {msg}\n")
        except Exception as e:
            pass  # نتجاهل الخطأ لو مقدرش يكتب عشان ميوقفش البرنامج

    def _enable_fast_execution(self, engine):
        @event.listens_for(engine, "before_cursor_execute")
        def receive_before_cursor_execute(conn, cursor, statement, params, context, executemany):
            if executemany:
                cursor.fast_executemany = True

    def _init_system_tables(self):
        try:
            with self.db.engine.begin() as conn:
                # 1. إنشاء جدول الهاش (منع التكرار)
                conn.execute(text(
                    "IF OBJECT_ID('SYS_MASTER_INDEX', 'U') IS NULL CREATE TABLE SYS_MASTER_INDEX (SYS_HASH CHAR(32) PRIMARY KEY WITH (IGNORE_DUP_KEY = ON));"))

                # 2. إنشاء جدول اللوج (اللي كان ناقص)
                conn.execute(text("""
                    IF OBJECT_ID('SYS_FILES_LOG', 'U') IS NULL 
                    CREATE TABLE SYS_FILES_LOG (
                        ID INT IDENTITY(1,1) PRIMARY KEY, 
                        FILE_NAME NVARCHAR(255), 
                        ROW_COUNT INT, 
                        STATUS NVARCHAR(50), 
                        PROCESSED_AT DATETIME DEFAULT GETDATE()
                    );
                """))
        except Exception as e:
            print(f"Init Error: {e}")
    def _clean_header(self, val):
        if pd.isna(val) or str(val).strip() == "": return "UNK"
        clean = re.sub(r'[^\w]+', '_', str(val).strip())
        return clean.strip('_')

    def read_file_chunks(self, file_path, chunk_size=100000):
        ext = file_path.lower().split('.')[-1]

        # 1. Excel
        if ext in ['xlsx', 'xls', 'xlsm']:
            try:
                # 🔥 التعديل: header=None
                df = pd.read_excel(file_path, header=None, dtype=str, engine='calamine')
            except ImportError:
                df = pd.read_excel(file_path, header=None, dtype=str)
            except Exception:
                df = pd.read_excel(file_path, header=None, dtype=str)

            total_rows = len(df)
            if total_rows == 0: return
            for start in range(0, total_rows, chunk_size):
                time.sleep(0.01)
                yield df.iloc[start:start + chunk_size].copy()
            del df
            gc.collect()

        # 2. CSV
        elif ext == 'csv':
            encodings = ['utf-8', 'utf-8-sig', 'cp1256', 'latin1']
            for enc in encodings:
                try:
                    # 🔥 التعديل: header=None (ده اللي هيمنع قراءة d,f,g كعناوين)
                    reader = pd.read_csv(file_path, header=None, chunksize=chunk_size, encoding=enc, dtype=str,
                                         on_bad_lines='skip')
                    for chunk in reader:
                        time.sleep(0.01)
                        yield chunk
                    break
                except:
                    continue
    # ---------------------------------------------------------
    # القارئ الموحد
    # ---------------------------------------------------------
    def _read_file_unified(self, file_path, nrows=None, skiprows=None, header=None):
        ext = file_path.lower().split('.')[-1]
        try:
            if ext in ['xlsx', 'xls', 'xlsm']:
                eng = 'openpyxl' if ext != 'xls' else 'xlrd'
                return pd.read_excel(file_path, nrows=nrows, skiprows=skiprows, header=header,
                                     dtype=str, keep_default_na=False, engine=eng)
            elif ext == 'csv':
                encodings = ['utf-8', 'utf-8-sig', 'cp1256', 'latin1']
                for enc in encodings:
                    try:
                        return pd.read_csv(file_path, nrows=nrows, skiprows=skiprows, header=header,
                                           encoding=enc, dtype=str, keep_default_na=False, on_bad_lines='skip')
                    except:
                        continue
                return pd.DataFrame()
            else:
                return pd.DataFrame()
        except Exception as e:
            return pd.DataFrame()

    # ---------------------------------------------------------
    # المرحلة 1: المسح الشامل
    # ---------------------------------------------------------
    def _phase_1_global_scan(self):
        self.logger.log("🔍 PHASE 1: Global Scan (Reading schema from ALL files)...")

        all_files = []
        for root, dirs, files in os.walk(self.root_folder):
            for f in files:
                if f.lower().endswith(('.xlsx', '.xls', '.csv')) and not f.startswith('~$'):
                    all_files.append(os.path.join(root, f))

        if not all_files:
            self.logger.log("❌ No files found!", "ERROR")
            return False

        files_scanned = 0
        for f_path in all_files:
            try:
                df_head = self._read_file_unified(f_path, nrows=2, header=None)
                if len(df_head) < 2: continue

                row_0 = df_head.iloc[0].tolist()
                row_1 = df_head.iloc[1].tolist()

                text_0 = "".join([str(x) for x in row_0])
                text_1 = "".join([str(x) for x in row_1])

                if len(re.findall(r'[a-zA-Z]', text_1)) > len(re.findall(r'[a-zA-Z]', text_0)):
                    cols_en = row_1
                    cols_ar = row_0
                else:
                    cols_en = row_0
                    cols_ar = row_1

                for i, en_col in enumerate(cols_en):
                    clean_en = self._clean_header(en_col)
                    ar_val = str(cols_ar[i]).strip() if i < len(cols_ar) else ""
                    if clean_en not in self.global_schema_map:
                        self.global_schema_map[clean_en] = ar_val

                files_scanned += 1
            except Exception:
                continue

        if not self.global_schema_map:
            self.logger.log("❌ Could not detect schema from any file.", "ERROR")
            return False

        folder_clean = re.sub(r'[^\w]+', '_', os.path.basename(self.root_folder))
        self.table_name = f"TBL_{folder_clean}"

        sorted_en_cols = sorted(list(self.global_schema_map.keys()))

        self.logger.log(f"🔨 Creating Master Table: {self.table_name} with {len(sorted_en_cols)} columns.")

        cols_sql = [f"[{c}] NVARCHAR(MAX)" for c in sorted_en_cols]
        cols_sql.extend([
            "[SYS_FOLDER] NVARCHAR(255)",
            "[SYS_FILE] NVARCHAR(255)",
            "[SYS_CREATED] DATETIME DEFAULT GETDATE()",
            "[SYS_HASH] CHAR(32)",
            "[SYS_ID] INT IDENTITY(1,1) PRIMARY KEY"
        ])

        create_sql = f"""
        IF OBJECT_ID('{self.table_name}', 'U') IS NULL
        BEGIN
            CREATE TABLE {self.table_name} ( {', '.join(cols_sql)} );
            CREATE INDEX IDX_{self.table_name}_HASH ON {self.table_name}(SYS_HASH);
        END
        """

        with self.db.engine.begin() as conn:
            conn.execute(text(create_sql))

            check_sql = text(f"SELECT COUNT(*) FROM {self.table_name}")
            count = conn.execute(check_sql).scalar()

            if count == 0:
                self.logger.log("   🎨 Inserting Arabic Header Row (Decor)...", indent=2)
                ar_row_values = []
                for en_col in sorted_en_cols:
                    ar_row_values.append(self.global_schema_map.get(en_col, ""))

                df_ar = pd.DataFrame([ar_row_values], columns=sorted_en_cols)
                df_ar['SYS_HASH'] = "HEADER_DECOR_ARABIC_ONLY"
                df_ar['SYS_FOLDER'] = "SYSTEM"
                df_ar['SYS_FILE'] = "HEADER"

                df_ar.to_sql(self.table_name, conn, if_exists='append', index=False)

        return True

    # ---------------------------------------------------------
    # الدالة الناقصة (حطها قبل def run مباشرة)
    # ---------------------------------------------------------
    def check_if_file_processed(self, filename):
        try:
            with self.db.engine.connect() as conn:
                # بتشوف هل الملف ده اتسجل قبل كده بـ status = COMPLETED ولا لأ
                sql = text("SELECT COUNT(*) FROM SYS_FILES_LOG WHERE FILE_NAME = :f AND STATUS = 'COMPLETED'")
                return conn.execute(sql, {"f": filename}).scalar() > 0
        except:
            return False


    # ---------------------------------------------------------
    # الدالة الناقصة (حطها قبل def run مباشرة)
    # ---------------------------------------------------------
    def _read_file_head(self, file_path, nrows=2):
        ext = file_path.lower().split('.')[-1]
        try:
            if ext in ['xlsx', 'xls']:
                return pd.read_excel(file_path, nrows=nrows, header=None, dtype=str)
            return pd.read_csv(file_path, nrows=nrows, header=None, dtype=str, encoding='utf-8-sig')
        except:
            return pd.DataFrame()

        # ---------------------------------------------------------
    # دالة الأرشفة الناقصة (حطها قبل def run مباشرة)
    # ---------------------------------------------------------
    def archive_file(self, file_path, status_folder):
        try:
            # نحدد اسم الفولدر (مثلاً Processed)
            dest_dir = os.path.join(self.root_folder, status_folder)

            # لو الفولدر مش موجود نعمله
            if not os.path.exists(dest_dir):
                os.makedirs(dest_dir)

            # نحدد المسار الجديد للملف
            file_name = os.path.basename(file_path)
            dest_path = os.path.join(dest_dir, file_name)

            # لو الملف موجود هناك، نزود عليه التاريخ عشان ميمسحش القديم
            if os.path.exists(dest_path):
                name, ext = os.path.splitext(file_name)
                timestamp = int(time.time())
                dest_path = os.path.join(dest_dir, f"{name}_{timestamp}{ext}")

            # نقل الملف
            shutil.move(file_path, dest_path)

        except Exception as e:
            self._log(f"⚠️ Archive Warning: {e}", "WARNING")

    #

    #
    def run(self):
        if not self._phase_1_global_scan(): return

        self.logger.log("=" * 60)
        self.logger.log("🚀 PHASE 2: Importing Data & Smart Name Splitting (V10 - Bug Fix)...")

        all_files = []
        for root, dirs, files in os.walk(self.root_folder):
            for f in files:
                if f.lower().endswith(('.xlsx', '.xls', '.csv')) and not f.startswith('~$'):
                    all_files.append(os.path.join(root, f))

        known_schema_cols = set(self.global_schema_map.keys())

        # =====================================================
        # 1. القائمة القياسية
        # =====================================================
        standard_ordered_cols = [
            "CBR", "CNO", "CCER", "CGL", "CSB", "CDATT", "CCLNT", "CTYP", "CNAME", "CAMT",
            "CDAT1", "CSEQ", "CCOD2", "CSNO1", "CDAT2", "CCOD3", "CCOD4", "CCOD5", "CDAT3",
            "CCOD6", "CCOD7", "CDAT4", "CDAT7", "CDAT8", "CCOD8", "CDAT5", "CDAT9", "CBRT",
            "CCLNTT", "CAMT1", "CAMT2", "CAMT3", "CDAT12", "CCOD10", "CDAT6", "CAMT4",
            "CAMT5", "CMCOD", "CCOD9", "CEE", "CDAT10", "CDAT11", "CFLR"
        ]

        import re

        def separate_stuck_names(text):
            if not text:
                return text
            text = str(text)

            # 1️⃣ توحيد المسافات (عشان نشتغل على نظافة)
            text = re.sub(r'\s+', ' ', text).strip()

            # =========================================================
            # 2️⃣ (الحل النهائي) فصل "تبرع من" و "ق" بالقوة
            # =========================================================

            # أولاً: نفصل حرف (ق) أو (م) لو جه قبل تبرع
            # بيحول "ق تبرع" أو "ق/تبرع" أو "ق/ تبرع" لشكل موحد ونظيف
            text = re.sub(r'(?<!\w)(ق|م)\s*(?=/|تبرع)', r'\1 ', text)
            text = re.sub(r'/\s*(ق|م)\s*تبرع', r'/ \1 تبرع', text)

            # ثانياً: المعادلة الشرسة لفصل "من" عن الاسم اللي بعدها
            # دي بتقول: لو لقيت "تبرع" + "من" + "حرف"، افصل الحرف عن "من"
            # بتعالج: "تبرع منجمال"، "تبرع منهبه"، "تبرع منرضا"
            text = re.sub(r'(تبرع)\s*(من)([ا-ي])', r'\1 \2 \3', text)

            # =========================================================
            # 3️⃣ المرحلة 8 (الجوكر): تصليح الألف قبل أي حاجة
            # =========================================================
            text = re.sub(r'([ا-ي]|^)\s*ا\s+([ا-ي]{3})(?=\s|/|:|$)', r'\1 ا\2', text)
            text = re.sub(r'(ة|ى)\s*ا\s+([ا-ي]{3})(?=\s|/|:|$)', r'\1 ا\2', text)

            text = re.sub(r'\s+', ' ', text).strip()

            # =========================================================
            # 4️⃣ التنظيفات الأساسية
            # =========================================================
            text = re.sub(r'\b([ا-ي]+)\s+(ة|ى)\b', r'\1\2', text)
            text = re.sub(r'منهالله', 'منه الله', text)
            text = re.sub(r'عبد\s+الله', 'عبدالله', text)
            text = re.sub(r'عبد\s+ال([ا-ي])', r'عبدال\1', text)

            # =========================================================
            # 5️⃣ قوائم الفصل الآمن (شغالة زي ما هي)
            # =========================================================
            names_to_split_after = [
                "منة", "علا", "منى", "سهى", "نهى", "مها", "رشا", "دنا", "جنا", "حلا",
                "منال", "جمال", "كمال", "نوال", "هلال", "دلال", "امال", "بلال", "جلال",
                "طلال", "نضال", "نهال", "ابتهال", "عبدالعال", "مثال", "وصال",
                "طلب", "حسن", "رابح", "اسماعيل", "كريم", "يامن", "سيف", "يحيي",
                "يوسف", "ابراهيم", "احمد", "محمد", "محمود", "مصطفى", "علي", "عبدالرحمن",
                "حسين", "سعيد", "عبدالله", "عبدالمنعم", "حساب", "خديجه", "فاطمه",
                "نسرين", "رضوان", "سهيله", "مروه", "تسنيم", "نادر",
                "عارف", "السايح", "عزب", "الفاتح", "رضوى", "عثمان", "حبيبه", "ياسين",
                "همام", "جنه", "اريج", "مرفت", "ساميه", "لطفى", "نفيسه", "سندس", "امام",
                "عبدالحكم", "صالح", "عبده", "رقيه", "منار", "مهاب", "كرم", "ياسمين",
                "فؤاد", "نصره", "سنا", "اسامه", "نجاه", "سيلفيا", "روضه", "منه الله",
                "الهام", "مريم", "صباح", "سلسبيل", "شحاته", "فهمى", "مياده", "قاصر",
                "تبرع", "اسراء", "فيفى", "كاشف", "سالم", "كنزى", "رباب", "اياد", "دنيا",
                "ريناد", "صهيب", "عاطف", "خلف", "طايع", "شاهين", "فضل", "فيروز", "شيرين",
                "نيفين", "امتثال", "عزه", "عبدالفتاح", "عليه", "خليل", "فاروق", "صلاح",
                "عبدالوهاب", "عبدالسلام", "عبدالمنعم", "عبدالعظيم", "عبدالغفار", "عبدالباقي",
                "عبدالخالق", "عبدالرحيم", "عبدالرحمن", "عبدالله", "عبدالعزيز", "عبدالقادر",
                "عبدالمجيد", "عبدالحليم", "عبدالحميد", "عبدالرزاق", "عبداللطيف", "عبدالمعطي",
                "عبدالهادي", "عبدالواحد", "عبدالصبور", "عبدالحكيم", "عبدالحفيظ", "عبدالمقصود",
                "طاهر", "اسلام", "وليد", "ياسر", "عمرو", "عمر", "السيد", "عادل", "طارق",
                "ماجد", "سامح", "ايهاب", "هاني", "هشام", "وائل", "رامي", "مجدي",
                "عصام", "جابر", "حامد", "رمضان", "شعبان", "عيد", "سليمان", "يحيى", "امين",
                "رزق", "منصور", "علاء", "عماد", "ممدوح", "حمدي", "حلمي", "رضا", "رجب",
                "عزت", "عوض", "فوزي", "فكري", "ايمن", "ادهم", "اكرم", "انور",
                "امير", "محسن", "مختار", "مدحت", "مراد", "مرسي", "معتز", "منتصر", "محفوظ",
                "مؤمن", "خالد", "زكريا", "طه", "سعد", "فرج", "نبيل", "حازم", "حسام", "جاد",
                "الدين", "سيد", "حافظ", "غريب", "مروان", "مازن", "فخرى", "نوير", "تامر",
                "هالة", "سارة", "نادية", "ايمان", "اسماء", "امينة", "عائشة", "زينب",
                "هدى", "وفاء", "حنان", "دعاء", "شيماء", "رانيا", "عبير", "داليا", "دينا",
                "ريهام", "غادة", "بسنت", "ايه", "جهاد", "منةالله", "سندس", "نورهان",
                "ساره", "رنا", "بسمه", "نجلاء", "هانم", "نادين", "رياب", "هدير",
                "هبه", "رحمه", "سوسن", "رابحه", "عين", "نوران", "ريتال", "ريماس"
            ]
            names_to_split_after.sort(key=len, reverse=True)
            pattern_after = r'(' + '|'.join(map(re.escape, names_to_split_after)) + r')(?=[^\s:،\.])'
            text = re.sub(pattern_after, r'\1 ', text)

            names_to_split_before = [
                "يوسف", "ابراهيم", "احمد", "محمد", "محمود", "مصطفى", "علي", "على", "السيد",
                "عبدالرحمن", "حسين", "حسنين", "عبدالله", "عبدالمنعم", "اسماعيل", "فرحات", "عثمان",
                "عرفات", "عبدالمطلب", "ابوالحسن", "الزغبى", "بشارى", "الجمال", "عبدالتواب",
                "بدوي", "زكي", "نصار", "مغربي", "بهنساوي", "عطية", "النيل", "السمان",
                "يونس", "ياقوت", "الجندي", "بدران", "حافظ", "غانم", "ابوجبل", "ابوالنيل",
                "ابوغانم", "راضي", "جاد", "وهبة", "ناصف", "بركات", "بكري", "بيومي", "توفيق",
                "ثابت", "جودة", "حجازي", "حرب", "حسني", "حقي", "حماد", "حمدان", "حنفي",
                "حيدر", "خيري", "درويش", "دياب", "راشد", "راغب", "رأفت", "رمزي", "زهران",
                "زيدان", "زاهر", "سرور", "سرحان", "سلطان", "سلامة", "سليم", "شادي", "شاهين",
                "شفيق", "شكري", "شلبي", "شوقي", "صادق", "صقر", "ضاحي", "طايل", "طلعت",
                "طلبة", "ظريف", "عامر", "عاشور", "عباس", "عدلي", "عربي", "عزام", "عزيز",
                "عساف", "عفيفي", "علام", "عليوة", "عمار", "عنتر", "عيسى", "غالي", "غريب",
                "فؤاد", "فايز", "فهمي", "قاسم", "قرني", "قنديل", "كامل", "كرم", "كريم",
                "لطفي", "لطفى", "لمعي", "لبيب", "ماهر", "مبارك", "متولي", "مخيمر", "مرعي", "مسعد",
                "مسلم", "مشرف", "مصباح", "مصلح", "مطاوع", "مظهر", "معوض", "مكرم", "مكي",
                "منير", "موسى", "ناجى", "نافع", "نحاس", "نديم", "نصر", "نصي", "نظمي", "نعيم",
                "هاشم", "هلال", "هيكل", "وصفي", "وطني", "وفيق", "وهبي", "يعقوب",
                "السنوسى", "السنوسي", "المتولى", "المتولي", "خلف", "خطيب", "موافي",
                "صالح", "غراب", "مهدى", "مهدي", "عادل", "طارق", "عيسى",
                "سعيد", "طلب", "حسن", "هنداوي", "الشرقاوي", "الشهاوي", "عصام"
            ]
            names_to_split_before.sort(key=len, reverse=True)
            pattern_before = r'(?<!\s)(?<!\u0627\u0644)(?<!\u0639\u0628\u062f)(?<!\u0627\u0628\u0648)(' + '|'.join(
                map(re.escape, names_to_split_before)) + r')'
            text = re.sub(pattern_before, r' \1', text)

            # =========================================================
            # 6️⃣ التظبيط النهائي
            # =========================================================
            text = re.sub(r'/', ' / ', text)
            text = re.sub(r':', ' : ', text)
            text = re.sub(r'\s+/\s+', ' / ', text)
            text = re.sub(r'(تبرع)', r' \1 ', text)
            text = re.sub(r'(قاصر)', r' \1', text)
            text = re.sub(r'(?<!\s)ال\s+([ا-ي])', r'ال\1', text)

            # تنظيف جمالي أخير
            text = re.sub(r'\s+/\s+ق\s+', ' / ق ', text)

            return re.sub(r'\s+', ' ', text).strip()


        def fix_and_split(text):
            if pd.isna(text) or str(text).strip() == '': return text
            original_text = str(text)

            # 1. لو هو أصلاً عربي، عالجه ورجعه
            if re.search(r'[\u0600-\u06FF]', original_text):
                return separate_stuck_names(original_text)

            # 2. لو مش عربي، حاول تفك التشفير
            decoded_text = original_text  # 🔥 (الإصلاح: عرفنا المتغير بقيمة افتراضية)
            try:
                try:
                    raw_bytes = original_text.encode('latin1')
                except:
                    raw_bytes = original_text.encode('cp1252')

                candidate = raw_bytes.decode('cp1256')

                # لو فك التشفير طلع عربي، اعتمد النتيجة الجديدة
                if re.search(r'[\u0600-\u06FF]', candidate):
                    decoded_text = candidate
            except:
                pass

            # 3. لو النتيجة النهائية (سواء الأصلية أو المفكوكة) فيها عربي، طبق المقص
            if re.search(r'[\u0600-\u06FF]', decoded_text):
                return separate_stuck_names(decoded_text)

            # 4. لو مفيش عربي خالص، رجع النص زي ما هو (إنجليزي أو أرقام)
            return decoded_text

        # =====================================================
        # 4. اللوب الرئيسي
        # =====================================================
        total_files = len(all_files)
        for i, f_path in enumerate(all_files):
            if self.stop_event.is_set(): break
            fname = os.path.basename(f_path)
            self._log(f"[{i + 1}/{total_files}] 📂 {fname}")
            rows_inserted = 0

            try:
                chunk_gen = self.read_file_chunks(f_path, chunk_size=100000)

                is_header_detected = False
                file_columns = []

                for idx, df_chunk in enumerate(chunk_gen):
                    if df_chunk.empty: continue

                    # -----------------------------------------------------
                    # منطق الهيدر (Header) والفلترة (Garbage Filter)
                    # -----------------------------------------------------
                    if not is_header_detected:
                        header_idx = -1
                        for r in range(min(20, len(df_chunk))):
                            row_vals = [self._clean_header(x) for x in df_chunk.iloc[r].tolist()]
                            matches = set(row_vals).intersection(known_schema_cols)
                            if len(matches) >= 1:
                                file_columns = row_vals
                                df_chunk = df_chunk.iloc[r + 1:].copy()
                                is_header_detected = True
                                header_idx = r
                                break

                        if not is_header_detected:
                            current_file_cols = df_chunk.shape[1]
                            fallback = list(standard_ordered_cols)
                            if current_file_cols > len(fallback):
                                df_chunk = df_chunk.iloc[:, :len(fallback)]
                                file_columns = fallback
                            elif current_file_cols < len(fallback):
                                file_columns = fallback[:len(df_chunk.columns)]
                            else:
                                file_columns = fallback

                            is_header_detected = True

                            # 🔥 فلتر التنظيف الشامل (يمنع الـ crash)
                            garbage_pattern = r'^[dD],[fF]|[fF][dD][wW]|^\?+|Code|^0$|^0\.0'
                            mask_garbage = df_chunk.iloc[:, 0].astype(str).str.contains(garbage_pattern, case=False,
                                                                                        na=False)
                            df_chunk = df_chunk[~mask_garbage]

                            if df_chunk.empty: continue

                    if len(df_chunk.columns) == len(file_columns):
                        df_chunk.columns = file_columns
                    else:
                        df_chunk.columns = [f"COL_{x}" for x in range(len(df_chunk.columns))]
                        continue

                    # تطبيق دالة الإصلاح (fix_and_split)
                    df_chunk = df_chunk.applymap(fix_and_split)

                    valid_cols = [c for c in df_chunk.columns if c in self.global_schema_map]
                    if not valid_cols: continue
                    df_final = df_chunk[valid_cols].copy()

                    for col in df_final.columns:
                        if 'date' in col.lower() or 'time' in col.lower():
                            try:
                                df_final[col] = pd.to_datetime(df_final[col], errors='coerce').dt.strftime('%Y-%m-%d')
                                df_final[col] = df_final[col].fillna('')
                            except:
                                pass

                    for col in df_final.columns:
                        if 'date' in col.lower(): continue
                        try:
                            original_nans = df_final[col].isna().sum()
                            s_numeric = pd.to_numeric(df_final[col], errors='coerce')
                            if s_numeric.isna().sum() <= original_nans:
                                if not s_numeric.isna().all(): df_final[col] = s_numeric.round(2)
                        except:
                            pass

                    str_sum = df_final.astype(str).apply(
                        lambda x: x.str.strip().str.upper().str.replace(r'\.0$', '', regex=True)).sum(
                        axis=1).str.encode('utf-8')
                    df_final['SYS_HASH'] = [hashlib.md5(v).hexdigest() for v in str_sum]
                    df_final['SYS_FOLDER'] = os.path.basename(os.path.dirname(f_path))
                    df_final['SYS_FILE'] = fname
                    df_final['SYS_CREATED'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    staging_table = "TBL_STAGING_TEMP"
                    df_final = df_final.loc[:, ~df_final.columns.duplicated()]

                    cols_list_str = "[" + "], [".join(df_final.columns) + "]"
                    dtype_mapping = {col: NVARCHAR(None) for col in df_final.columns}

                    with self.db.engine.begin() as conn:
                        # 1. Staging
                        df_final.to_sql(staging_table, conn, if_exists='replace', index=False, dtype=dtype_mapping,
                                        chunksize=5000)

                        # 2. Insert into Main Table
                        # 2. Insert into Main Table
                        conn.execute(text(f"""
                                                    INSERT INTO {self.table_name} ({cols_list_str})
                                                    SELECT DISTINCT {cols_list_str} FROM {staging_table} AS S
                                                    WHERE NOT EXISTS (SELECT 1 FROM SYS_MASTER_INDEX AS M WHERE M.SYS_HASH = S.SYS_HASH)
                                                """))

                        # 3. Update Index & Get Count
                        res = conn.execute(text(f"""
                            INSERT INTO SYS_MASTER_INDEX (SYS_HASH)
                            SELECT DISTINCT SYS_HASH FROM {staging_table} AS S
                            WHERE NOT EXISTS (SELECT 1 FROM SYS_MASTER_INDEX AS M WHERE M.SYS_HASH = S.SYS_HASH)
                        """))

                        # 🔥 التعديل هنا: نحفظ العدد في متغير عشان نطبعه
                        batch_added = res.rowcount
                        rows_inserted += batch_added

                    # 🔥 سطر اللوج اللي كان ناقصك:
                    self._log(f"    ➕ Batch processed. New unique records: {batch_added}")



                    gc.collect()

                self._log(f"✅ Finished {fname}: {rows_inserted} new rows.")

            except Exception as e:
                self._log(f"❌ Error {fname}: {e}", "ERROR")
                gc.collect()

        self.logger.log("\n🏁 JOB DONE.")