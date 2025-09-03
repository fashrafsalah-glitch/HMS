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

def check_downtime_6_and_wo_85():
    """فحص سجل التوقف رقم 6 وأمر الشغل رقم 85"""
    
    print("=== فحص سجل التوقف رقم 6 وأمر الشغل 85 ===\n")
    
    # فحص سجل التوقف رقم 6
    try:
        dt = DeviceDowntime.objects.get(id=6)
        print(f"✅ تم العثور على سجل التوقف {dt.id}")
        print(f"الجهاز: {dt.device.name}")
        print(f"بداية التوقف: {dt.start_time}")
        print(f"نهاية التوقف: {dt.end_time}")
        print(f"السبب: {dt.reason}")
        print(f"نوع التوقف: {dt.downtime_type}")
        
        # حساب مدة التوقف
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
            print(f"أمر الشغل المرتبط: {dt.work_order.wo_number}")
        else:
            print("لا يوجد أمر شغل مرتبط")
            
        print(f"الوصف: {dt.description}")
        
    except DeviceDowntime.DoesNotExist:
        print("❌ لم يتم العثور على سجل التوقف رقم 6")
        dt = None
    
    print("\n" + "="*50)
    
    # فحص أمر الشغل رقم 85
    try:
        # البحث عن أمر الشغل بالرقم 85
        wo = WorkOrder.objects.filter(wo_number__contains='85').first()
        if not wo:
            # البحث بـ ID
            wo = WorkOrder.objects.get(id=85)
        
        print(f"✅ تم العثور على أمر الشغل: {wo.wo_number}")
        print(f"ID: {wo.id}")
        print(f"الحالة: {wo.status}")
        print(f"تاريخ الإنشاء: {wo.created_at}")
        print(f"تاريخ الإكمال: {wo.completed_at}")
        print(f"النهاية الفعلية: {wo.actual_end}")
        print(f"العنوان: {wo.title}")
        print(f"الوصف: {wo.description}")
        
        if wo.service_request:
            sr = wo.service_request
            print(f"\nطلب الخدمة المرتبط: SR-{sr.id}")
            print(f"حالة طلب الخدمة: {sr.status}")
            print(f"الجهاز: {sr.device.name if sr.device else 'غير محدد'}")
            print(f"تاريخ الحل: {sr.resolved_at}")
            print(f"تاريخ الإغلاق: {sr.closed_at}")
        
    except WorkOrder.DoesNotExist:
        print("❌ لم يتم العثور على أمر الشغل رقم 85")
        wo = None
    
    print("\n" + "="*50)
    
    # تحليل العلاقة بين سجل التوقف وأمر الشغل
    if dt and wo:
        print("=== تحليل العلاقة ===")
        
        if dt.work_order and dt.work_order.id == wo.id:
            print("✅ سجل التوقف مرتبط بأمر الشغل")
        else:
            print("⚠️ سجل التوقف غير مرتبط بأمر الشغل")
            if dt.work_order:
                print(f"سجل التوقف مرتبط بأمر الشغل: {dt.work_order.wo_number}")
        
        # فحص إذا كان يجب إنهاء التوقف
        if not dt.end_time and wo.status in ['completed', 'cancelled', 'closed', 'resolved']:
            print(f"\n⚠️ يجب إنهاء سجل التوقف - أمر الشغل {wo.status}")
            
            # تحديد تاريخ النهاية
            end_time = wo.completed_at or wo.actual_end or timezone.now()
            print(f"تاريخ النهاية المقترح: {end_time}")
            
            # إنهاء التوقف
            dt.end_time = end_time
            end_reason = f"تم إنهاء أمر الشغل {wo.wo_number} - الحالة: {wo.status}"
            end_note = f"\n\nتم الإنهاء تلقائياً: {end_reason}\nتاريخ النهاية: {end_time}"
            
            if dt.description:
                dt.description += end_note
            else:
                dt.description = f"تم الإنهاء تلقائياً: {end_reason}"
            
            dt.save()
            print(f"✅ تم إنهاء سجل التوقف {dt.id} بنجاح!")
        
        elif dt.end_time:
            print(f"✅ سجل التوقف منتهي بالفعل في: {dt.end_time}")
        
        elif wo.status in ['new', 'assigned', 'in_progress']:
            print(f"ℹ️ سجل التوقف نشط - أمر الشغل لا يزال {wo.status}")

if __name__ == "__main__":
    check_downtime_6_and_wo_85()
