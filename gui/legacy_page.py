# -*- coding: utf-8 -*-
"""
LegacyInquiryPage — جسر ترحيل للشاشات القديمة المنقولة من gui.py الأصلي.

الشاشات القديمة كانت كل منطقها داخل دالة واحدة عملاقة (setup_xxx_ui) وتصل إلى
حالة مشتركة على النافذة الرئيسية (self.branch_mapping, self._get_db_connection ...).
هذا الكلاس يسمح بنقل تلك الدوال إلى ملفات مستقلة دون تغيير سطر واحد من منطقها:

- ``USE_STANDARD_CHROME = False`` — الشاشة تبني هيكلها القديم بالكامل عبر ``build()``.
- ``__getattr__`` يفوّض أي attribute غير موجود (غير معرّف على الصفحة نفسها)
  إلى النافذة الرئيسية (MainWindow) — تماماً كما كان الحال عندما كان كل شيء
  داخل كلاس FGSApp واحد.

الشاشات الجديدة يجب أن ترث من BaseInquiryPage مباشرة (وليس من هذا الكلاس)
وتستخدم البنية القياسية (header + search + results).
"""
import logging

from gui.base_inquiry_page import BaseInquiryPage


class LegacyInquiryPage(BaseInquiryPage):
    """صفحة استعلام بالنمط القديم (مُرحّلة حرفياً من gui.py)."""

    USE_STANDARD_CHROME = False

    def __getattr__(self, name):
        # لا تُفوّض أبداً الـ dunder (حماية من مشاكل copy/pickle والفحص الداخلي)
        if name.startswith("__") and name.endswith("__"):
            raise AttributeError(name)
        app = self.__dict__.get("app")
        if app is not None:
            try:
                return getattr(app, name)
            except AttributeError:
                pass
        raise AttributeError(
            f"{type(self).__name__} object has no attribute {name!r} "
            f"(ولا في النافذة الرئيسية)"
        )

    def build(self):
        raise NotImplementedError("legacy pages must implement build()")

    def on_show(self):
        """نفس سلوك show_page القديم: إعادة تحميل الفروع عند فتح الشاشة إن لزم."""
        if self.LOAD_BRANCHES_ON_SHOW and self.app is not None:
            try:
                self.app.nuwairy_load_branches()
            except Exception as exc:
                logging.error("nuwairy_load_branches أثناء on_show فشلت: %s", exc)
