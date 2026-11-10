# -*- coding: utf-8 -*-
"""
سجل الشاشات (Lazy Registry) — المكان الوحيد الذي يربط مفتاح الشاشة بملفها وكلاسها.

إضافة شاشة جديدة = إضافة سطر واحد هنا (بالإضافة لسطر واحد في MENU_STRUCTURE
داخل main_window.py وسطر في قائمة Factory غير مطلوب — هذا الملف هو الـ factory).

القيمة: "module.path:ClassName" — يتم استيرادها عند أول فتح للشاشة فقط (Lazy Loading).
"""
PAGE_REGISTRY = {
    # 📂 الحسابات العامة
    "nuwairy": "gui.pages.nuwairy:NuwairyPage",
    "gl_inquiry": "gui.pages.gl_inquiry:GLInquiryPage",
    # 👥 خدمة العملاء
    "customer": "gui.pages.customer:CustomerInquiryPage",
    "customer_balance": "gui.pages.customer_balance:CustomerBalancePage",
    "cancelled_certs": "gui.pages.cancelled_certs:CancelledCertsPage",
    "mandates": "gui.pages.mandates:MandatesPage",
    "instructions": "gui.pages.instructions:InstructionsPage",
    "stopped_cheques": "gui.pages.stopped_cheques:StoppedChequesPage",
    "rejected_cheques": "gui.pages.rejected_cheques:RejectedChequesPage",
    # 📄 التوظيف
    "local_recruitment": "gui.pages.local_recruitment:LocalRecruitmentPage",
    "returned_cheques": "gui.pages.returned_cheques:ReturnedChequesPage",
    "defaulted_clients": "gui.pages.defaulted_clients:DefaultingClientPage",
    "guarantees": "gui.pages.guarantees:GuaranteesInquiryPage",
    "creditworthiness": "gui.pages.creditworthiness:CreditworthinessInquiryPage",
    "total_liabilities_inquiry": "gui.pages.total_liabilities_inquiry:TotalLiabilitiesInquiryPage",
    "customer_collaterals_inquiry": "gui.pages.customer_collaterals_inquiry:CustomerCollateralsInquiryPage",
    "sponsors_inquiry": "gui.pages.sponsors_inquiry:SponsorsInquiryPage",
    "client_history": "gui.pages.client_history:ClientHistoryInquiryPage",
    # 📄 الارباح والمساهمين
    "contributing_clients": "gui.pages.contributing_clients:ContributingClientsInquiryPage",
    # العلاج الطبي
    "alphabetical_employees_families": "gui.pages.alphabetical_employees_families:AlphabeticalEmployeesFamiliesPage",
    "medical_balances_inquiry": "gui.pages.medical_balances_inquiry:MedicalBalancesInquiryPage",
    "medical_bills_movement": "gui.pages.medical_bills_movement:MedicalBillsMovementPage",
    # الاجازات والاستحقاقات
    "previous_leaves_inquiry": "gui.pages.previous_leaves_inquiry:PreviousLeavesInquiryPage",
    "leaves_movement": "gui.pages.leaves_movement:LeavesMovementPage",
    "entitlements_basic_data": "gui.pages.entitlements_basic_data:EntitlementsBasicDataPage",
    # شاشات داخلية غير معروضة في السايد بار (كانت موجودة في الكود القديم وغير مربوطة)
    "dashboard": "gui.pages.dashboard:DashboardPage",
    "config_page": "gui.pages.config_page:ConfigPage",
    "reports": "gui.pages.reports:ReportsPage",
}
