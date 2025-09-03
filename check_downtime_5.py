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

def check_downtime_5():
    """فحص سجل التوقف رقم 5"""
    
    print("=== فحص سجل التوقف رقم 5 ===\n")
    
    try:
        dt = DeviceDowntime.objects.get(id=5)
        print(f"سجل التوقف {dt.id}")
        print(f"الجهاز: {dt.device.name}")
        print(f"بداية التوقف: {dt.start_time}")
        print(f"نهاية التوقف: {dt.end_time}")
        
        # حساب مدة التوقف
        if dt.start_time:
            if dt.end_time:
                duration = dt.end_time - dt.start_time
            else:
                duration = timezone.now() - dt.start_time
            hours = duration.total_seconds() / 3600
            print(f"مدة التوقف: {hours:.2f} ساعة")
        
        print(f"السبب: {dt.reason}")
        print(f"نوع التوقف: {dt.downtime_type}")
        print(f"الوصف: {dt.description}")
        
        if dt.work_order:
            wo = dt.work_order
            print(f"\nأمر الشغل: {wo.wo_number}")
            print(f"حالة أمر الشغل: {wo.status}")
            print(f"تاريخ الإكمال: {wo.completed_at}")
            print(f"النهاية الفعلية: {wo.actual_end}")
            
            if wo.service_request:
                sr = wo.service_request
                print(f"طلب الخدمة: SR-{sr.id}")
                print(f"حالة طلب الخدمة: {sr.status}")
                print(f"تاريخ الحل: {sr.resolved_at}")
                print(f"تاريخ الإغلاق: {sr.closed_at}")
        
        # فحص إذا كان يجب إنهاء هذا التوقف
        should_end = False
        end_time = None
        end_reason = ""
        
        if dt.work_order:
            wo = dt.work_order
            if wo.status in ['completed', 'cancelled', 'closed', 'resolved']:
                should_end = True
                end_reason = f"تم إنهاء أمر الشغل {wo.wo_number} - الحالة: {wo.status}"
                
                if wo.completed_at:
                    end_time = wo.completed_at
                elif wo.actual_end:
                    end_time = wo.actual_end
                else:
                    end_time = timezone.now()
        
        if not should_end:
            # فحص طلبات الخدمة النشطة
            active_srs = ServiceRequest.objects.filter(
                device=dt.device,
                status__in=['new', 'assigned', 'in_progress']
            )
            
            if not active_srs.exists():
                # فحص أوامر الشغل النشطة
                active_wos = WorkOrder.objects.filter(
                    service_request__device=dt.device,
                    status__in=['new', 'assigned', 'in_progress']
                )
                
                if not active_wos.exists():
                    should_end = True
                    end_reason = "لا توجد أعمال نشطة للجهاز"
                    
                    # البحث عن آخر طلب خدمة مكتمل
                    completed_srs = ServiceRequest.objects.filter(
                        device=dt.device,
                        status__in=['resolved', 'closed', 'completed']
                    ).order_by('-resolved_at', '-closed_at', '-updated_at')
                    
                    if completed_srs.exists():
                        latest_sr = completed_srs.first()
                        if latest_sr.resolved_at:
                            end_time = latest_sr.resolved_at
                        elif latest_sr.closed_at:
                            end_time = latest_sr.closed_at
                        else:
                            end_time = timezone.now()
                    else:
                        end_time = timezone.now()
        
        if should_end and not dt.end_time:
            print(f"\n⚠️ يجب إنهاء هذا التوقف!")
            print(f"السبب: {end_reason}")
            print(f"تاريخ النهاية المقترح: {end_time}")
            
            # إنهاء التوقف
            dt.end_time = end_time
            
            # إضافة ملاحظة الإنهاء
            end_note = f"\n\nتم الإنهاء تلقائياً: {end_reason}\nتاريخ النهاية: {end_time}"
            if dt.description:
                dt.description += end_note
            else:
                dt.description = f"تم الإنهاء تلقائياً: {end_reason}\nتاريخ النهاية: {end_time}"
            
            dt.save()
            
            print(f"✅ تم إنهاء سجل التوقف {dt.id} بنجاح!")
            print(f"تاريخ النهاية: {dt.end_time}")
        
        elif dt.end_time:
            print(f"\n✅ سجل التوقف منتهي بالفعل في: {dt.end_time}")
        
        else:
            print(f"\n⚠️ سجل التوقف لا يزال نشطاً - هناك أعمال نشطة للجهاز")
            
    except DeviceDowntime.DoesNotExist:
        print("لم يتم العثور على سجل التوقف رقم 5")

if __name__ == "__main__":
    check_downtime_5()
