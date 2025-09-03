import os
import sys
import django
from datetime import datetime, timedelta

# Set UTF-8 encoding for console output
sys.stdout.reconfigure(encoding='utf-8')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from maintenance.models import DeviceDowntime, WorkOrder, ServiceRequest, Device
from django.utils import timezone

def find_all_downtimes():
    """البحث عن جميع سجلات التوقف"""
    
    print("=== جميع سجلات التوقف ===\n")
    
    # البحث عن جميع سجلات التوقف
    all_downtimes = DeviceDowntime.objects.all().order_by('-id')
    
    print(f"إجمالي سجلات التوقف: {all_downtimes.count()}")
    
    for dt in all_downtimes:
        print(f"\n--- سجل التوقف {dt.id} ---")
        print(f"الجهاز: {dt.device.name}")
        print(f"بداية التوقف: {dt.start_time}")
        print(f"نهاية التوقف: {dt.end_time}")
        
        if dt.start_time:
            if dt.end_time:
                duration = dt.end_time - dt.start_time
                status = "منتهي"
            else:
                duration = timezone.now() - dt.start_time
                status = "نشط"
            hours = duration.total_seconds() / 3600
            print(f"مدة التوقف: {hours:.2f} ساعة - الحالة: {status}")
        
        if dt.work_order:
            wo = dt.work_order
            print(f"أمر الشغل: {wo.wo_number} - الحالة: {wo.status}")
        
        # فحص إذا كان هذا السجل يحتاج إنهاء
        if not dt.end_time:
            print("⚠️ سجل توقف نشط - يحتاج فحص!")
            
            # فحص أمر الشغل المرتبط
            if dt.work_order:
                wo = dt.work_order
                if wo.status in ['completed', 'cancelled', 'closed', 'resolved']:
                    end_time = wo.completed_at or wo.actual_end or timezone.now()
                    print(f"🔧 يجب إنهاؤه بتاريخ: {end_time}")
                    
                    # إنهاء السجل
                    dt.end_time = end_time
                    end_note = f"\n\nتم الإنهاء تلقائياً: أمر الشغل {wo.wo_number} مكتمل\nتاريخ النهاية: {end_time}"
                    if dt.description:
                        dt.description += end_note
                    else:
                        dt.description = f"تم الإنهاء تلقائياً: أمر الشغل {wo.wo_number} مكتمل"
                    
                    dt.save()
                    print(f"✅ تم إنهاء السجل {dt.id}")

if __name__ == "__main__":
    find_all_downtimes()
