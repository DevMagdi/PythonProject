import hashlib
import base64
import datetime
import os
import json
import subprocess
import urllib.request
import urllib.error


class LicenseGuard:
    # 🔴 المفتاح السري بتاعك (لازم يكون نفس اللي في admin_keygen.py)
    SECRET_KEY = "MY_SUPER_SECRET_PROJECT_V1_SALT_KEY_@2025"

    # 🔴 حطينا الرابط بتاعك هنا 🔴
    ONLINE_DB_URL = "https://gist.githubusercontent.com/DevMagdi/60ff8a97aef52fb6b17fbda189ad477b/raw/licenses.json"
    @staticmethod
    def validate_license_string(license_key_input):
        try:
            parts = license_key_input.strip().split('-')

            # 1. فحص هيكل الكود (لازم 3 أجزاء)
            if len(parts) < 3:
                return False, "❌ Invalid license format."

            signature_part = parts[0]
            date_b64_part = parts[1]
            client_b64_part = parts[2]

            # 2. فك تشفير التاريخ واسم العميل
            expire_date_str = base64.b64decode(date_b64_part).decode()
            client_name = base64.b64decode(client_b64_part).decode()

            # 3. فحص التلاعب (هل حد غير حرف في الكود؟)
            raw_data = f"{client_name}|{expire_date_str}|{LicenseGuard.SECRET_KEY}"
            expected_signature = hashlib.sha256(raw_data.encode()).hexdigest()[:16].upper()

            if signature_part != expected_signature:
                return False, "❌ License Key is corrupted or fake."

            # 4. الاتصال بالإنترنت للتحقق الأخير
            return LicenseGuard._check_online_status(client_name, expire_date_str)

        except Exception as e:
            return False, f"❌ License Error: {str(e)}"

    @staticmethod
    def _check_online_status(client_name, offline_expiry_str):
        # ملف مخفي بنحفظ فيه آخر مرة البرنامج شاف فيها إنترنت
        current_dir = os.path.dirname(os.path.abspath(__file__))
        grace_file = os.path.join(current_dir, "sys_grace.dat")

        try:
            # محاولة جلب البيانات أونلاين
            req = urllib.request.Request(LicenseGuard.ONLINE_DB_URL, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode())

            # هل العميل مسجل في السيرفر؟
            if client_name not in data:
                return False, f"❌ Client '{client_name}' not found in online registry."

            client_data = data[client_name]

            # هل المبرمج وقف الترخيص يدوياً؟
            if not client_data.get("is_active", False):
                return False, f"🚫 License for '{client_name}' has been disabled by Admin."

            # هل انتهت الصلاحية أونلاين؟
            online_expiry_str = client_data.get("expiry_date", offline_expiry_str)
            online_expiry = datetime.datetime.strptime(online_expiry_str, "%Y-%m-%d")

            if datetime.datetime.now() > online_expiry:
                return False, f"⚠️ License Expired on {online_expiry_str}!"

            # ⬇️ لو كل حاجة تمام: احفظ تاريخ اليوم كـ Cache عشان لو النت قطع بكرة
            try:
                with open(grace_file, 'w') as f:
                    f.write(base64.b64encode(datetime.datetime.now().strftime("%Y-%m-%d").encode()).decode())
            except:
                pass

            return True, f"✅ Licensed until: {online_expiry_str} (Client: {client_name})"

        except (urllib.error.URLError, Exception):
            # ==========================================
            # ⚠️ حالة انقطاع الإنترنت (Offline Fallback)
            # ==========================================
            offline_expiry = datetime.datetime.strptime(offline_expiry_str, "%Y-%m-%d")
            if datetime.datetime.now() > offline_expiry:
                return False, f"⚠️ License Expired on {offline_expiry_str}!"

            # فحص فترة السماح (Grace Period) مسموح بـ 3 أيام كحد أقصى بدون نت
            if os.path.exists(grace_file):
                try:
                    with open(grace_file, 'r') as f:
                        last_check_str = base64.b64decode(f.read().strip()).decode()
                        last_check = datetime.datetime.strptime(last_check_str, "%Y-%m-%d")
                        days_offline = (datetime.datetime.now() - last_check).days

                        if days_offline > 3:
                            return False, "🌐 Internet required. You have been offline for more than 3 days."
                except:
                    pass
            else:
                # لو أول مرة يشغل البرنامج لازم نت
                return False, "🌐 Initial Activation requires Internet connection."

            return True, f"✅ Licensed until: {offline_expiry_str} (Offline Mode)"

    @staticmethod
    def get_machine_fingerprint():
        """جلب بصمة الجهاز (السيريال الخاص باللوحة الأم)"""
        try:
            # استخدام أمر الويندوز لجلب سيريال الجهاز (UUID)
            cmd = 'wmic csproduct get uuid'
            uuid = subprocess.check_output(cmd, shell=True).decode().split('\n')[1].strip()

            if not uuid:
                uuid = "UNKNOWN_PC"

            # تشفيره بـ MD5 عشان يكون كود قصير واحترافي
            return hashlib.md5(uuid.encode('utf-8')).hexdigest().upper()
        except Exception:
            # لو فشل يجيب السيريال (مثلاً مفيش صلاحيات)، نرجع كود افتراضي
            return "FGS-FALLBACK-ID-001"