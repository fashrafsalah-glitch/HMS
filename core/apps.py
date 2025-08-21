# core/apps.py أو داخل تطبيق icd
from django.apps import AppConfig
from django.conf import settings
from django.db.models.signals import post_migrate

def load_icd11_safe(sender, **kwargs):
    import os, zipfile
    from django.conf import settings
    path = os.path.join(settings.BASE_DIR, "static", "icd11.xlsx")
    if not os.path.exists(path):
        print("[ICD-11] skipped: file not found")
        return
    # تحقق أنه zip فعلاً (xlsx)
    if not zipfile.is_zipfile(path):
        print("[ICD-11] skipped: not a valid .xlsx (zip) file")
        return
    # TODO: افتح الملف بـ openpyxl واقرأ المحتوى، ثم أنشئ السجلات إن لزم

class CoreConfig(AppConfig):
    name = "core"
  

    def ready(self):
        # أوقف التحميل التلقائي دائمًا ما لم تفعّله صراحةً
        if not getattr(settings, "ENABLE_ICD11_BOOT_LOAD", False):
            return
    def ready(self):
        post_migrate.connect(load_icd11_safe, sender=self)