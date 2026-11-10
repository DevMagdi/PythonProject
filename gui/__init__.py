# -*- coding: utf-8 -*-
"""
FIB Data Integration Hub — حزمة الواجهة الرسومية (CustomTkinter).

تم تحويل gui.py (~11,800 سطر) إلى هذه الحزمة:

- constants.py         : الألوان والثوابت ومسارات الموارد.
- popup.py             : PremiumSearchPopup.
- base_inquiry_page.py : BaseInquiryPage — الكلاس الأساسي لكل شاشات الاستعلام.
- legacy_page.py       : LegacyInquiryPage — جسر ترحيل للشاشات القديمة.
- main_window.py       : MainWindow (المعروفة سابقاً بـ FGSApp) — النافذة الرئيسية والتنقل.
- pages/               : ملف مستقل لكل شاشة + PAGE_REGISTRY (Lazy Loading).
"""
from gui.main_window import FGSApp, MainWindow

__all__ = ["FGSApp", "MainWindow"]
__version__ = "2.1.0"
