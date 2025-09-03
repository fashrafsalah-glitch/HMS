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

def check_klm_downtime():
    """فحص سجل التوقف للجهاز klm"""
    
    print("=== فحص سجل التوقف للجهاز klm ===\n")
    
    # البحث عن الجهاز klm
    try:
        device = Device.objects.get(name="klm")
        print(f"تم العثور على الجهاز: {device.name}")
    except Device.DoesNotExist:
        print("لم يتم العثور على الجهاز klm")
        return
    
    # البحث عن سجلات التوقف النشطة
    active_downtimes = DeviceDowntime.objects.filter(
        device=device,
        end_time__isnull=True
    )
    
    print(f"سجلات التوقف النشطة: {active_downtimes.count()}")
    
    for dt in active_downtimes:
        print(f"\n--- سجل التوقف {dt.id} ---")
        print(f"بداية التوقف: {dt.start_time}")
        print(f"نهاية التوقف: {dt.end_time}")
        
        if dt.work_order:
            wo = dt.work_order
            print(f"أمر الشغل: {wo.wo_number}")
            print(f"حالة أمر الشغل: {wo.status}")
            print(f"تاريخ الإكمال: {wo.completed_at}")
            print(f"النهاية الفعلية: {wo.actual_end}")
            
            # فحص طلب الخدمة المرتبط
            if wo.service_request:
                sr = wo.service_request
                print(f"طلب الخدمة: SR-{sr.id}")
                print(f"حالة طلب الخدمة: {sr.status}")
                print(f"تاريخ الحل: {sr.resolved_at}")
                print(f"تاريخ الإغلاق: {sr.closed_at}")
        
        # حساب مدة التوقف
        if dt.start_time:
            duration = timezone.now() - dt.start_time
            hours = duration.total_seconds() / 3600
            print(f"مدة التوقف الحالية: {hours:.2f} ساعة")
        
        print(f"الوصف: {dt.description}")
    
    # فحص أوامر الشغل النشطة للجهاز
    print(f"\n=== أوامر الشغل للجهاز {device.name} ===")
    active_wos = WorkOrder.objects.filter(
        service_request__device=device
    ).order_by('-created_at')
    
    for wo in active_wos[:5]:  # آخر 5 أوامر
        print(f"\nأمر الشغل: {wo.wo_number}")
        print(f"الحالة: {wo.status}")
        print(f"تاريخ الإنشاء: {wo.created_at}")
        print(f"تاريخ الإكمال: {wo.completed_at}")
        if wo.service_request:
            print(f"طلب الخدمة: SR-{wo.service_request.id} - {wo.service_request.status}")
    
    # فحص طلبات الخدمة النشطة للجهاز
    print(f"\n=== طلبات الخدمة للجهاز {device.name} ===")
    active_srs = ServiceRequest.objects.filter(
        device=device
    ).order_by('-created_at')
    
    for sr in active_srs[:5]:  # آخر 5 طلبات
        print(f"\nطلب الخدمة: SR-{sr.id}")
        print(f"الحالة: {sr.status}")
        print(f"تاريخ الإنشاء: {sr.created_at}")
        print(f"تاريخ الحل: {sr.resolved_at}")
        print(f"تاريخ الإغلاق: {sr.closed_at}")

if __name__ == "__main__":
    check_klm_downtime()
