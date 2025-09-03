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

def check_all_active_downtimes():
    """فحص جميع سجلات التوقف النشطة"""
    
    print("=== فحص جميع سجلات التوقف النشطة ===\n")
    
    # البحث عن جميع سجلات التوقف النشطة
    active_downtimes = DeviceDowntime.objects.filter(
        end_time__isnull=True
    ).select_related('device', 'work_order')
    
    print(f"عدد سجلات التوقف النشطة: {active_downtimes.count()}")
    
    for dt in active_downtimes:
        print(f"\n--- سجل التوقف {dt.id} ---")
        print(f"الجهاز: {dt.device.name}")
        print(f"بداية التوقف: {dt.start_time}")
        print(f"نهاية التوقف: {dt.end_time}")
        
        # حساب مدة التوقف
        if dt.start_time:
            duration = timezone.now() - dt.start_time
            hours = duration.total_seconds() / 3600
            print(f"مدة التوقف الحالية: {hours:.2f} ساعة")
        
        if dt.work_order:
            wo = dt.work_order
            print(f"أمر الشغل: {wo.wo_number}")
            print(f"حالة أمر الشغل: {wo.status}")
            print(f"تاريخ الإكمال: {wo.completed_at}")
            print(f"النهاية الفعلية: {wo.actual_end}")
            
            # فحص إذا كان يجب إنهاء هذا التوقف
            if wo.status in ['completed', 'cancelled', 'closed', 'resolved']:
                print("⚠️ يجب إنهاء هذا التوقف - أمر الشغل مكتمل!")
                
                # تحديد تاريخ النهاية المناسب
                end_time = None
                if wo.completed_at:
                    end_time = wo.completed_at
                elif wo.actual_end:
                    end_time = wo.actual_end
                else:
                    end_time = timezone.now()
                
                print(f"تاريخ النهاية المقترح: {end_time}")
        
        # فحص طلبات الخدمة للجهاز
        active_srs = ServiceRequest.objects.filter(
            device=dt.device,
            status__in=['new', 'assigned', 'in_progress']
        )
        
        completed_srs = ServiceRequest.objects.filter(
            device=dt.device,
            status__in=['resolved', 'closed', 'completed']
        ).order_by('-resolved_at', '-closed_at', '-updated_at')
        
        print(f"طلبات خدمة نشطة: {active_srs.count()}")
        print(f"طلبات خدمة مكتملة: {completed_srs.count()}")
        
        if not active_srs.exists() and completed_srs.exists():
            latest_sr = completed_srs.first()
            print(f"آخر طلب خدمة مكتمل: SR-{latest_sr.id}")
            print(f"تاريخ الحل: {latest_sr.resolved_at}")
            print("⚠️ يجب إنهاء هذا التوقف - لا توجد أعمال نشطة!")

def manually_end_downtimes():
    """إنهاء سجلات التوقف يدوياً"""
    
    print("\n=== إنهاء سجلات التوقف يدوياً ===\n")
    
    active_downtimes = DeviceDowntime.objects.filter(
        end_time__isnull=True
    ).select_related('device', 'work_order')
    
    ended_count = 0
    
    for dt in active_downtimes:
        should_end = False
        end_time = timezone.now()
        end_reason = ""
        
        # فحص أمر الشغل
        if dt.work_order:
            wo = dt.work_order
            if wo.status in ['completed', 'cancelled', 'closed', 'resolved']:
                should_end = True
                end_reason = f"تم إنهاء أمر الشغل {wo.wo_number} - الحالة: {wo.status}"
                
                # استخدام تاريخ الإكمال الفعلي
                if wo.completed_at:
                    end_time = wo.completed_at
                elif wo.actual_end:
                    end_time = wo.actual_end
        
        # فحص طلبات الخدمة
        if not should_end:
            active_srs = ServiceRequest.objects.filter(
                device=dt.device,
                status__in=['new', 'assigned', 'in_progress']
            )
            
            if not active_srs.exists():
                completed_srs = ServiceRequest.objects.filter(
                    device=dt.device,
                    status__in=['resolved', 'closed', 'completed']
                ).order_by('-resolved_at', '-closed_at', '-updated_at')
                
                if completed_srs.exists():
                    should_end = True
                    end_reason = "لا توجد أعمال نشطة للجهاز"
                    
                    latest_sr = completed_srs.first()
                    if latest_sr.resolved_at:
                        end_time = latest_sr.resolved_at
                    elif latest_sr.closed_at:
                        end_time = latest_sr.closed_at
        
        # إنهاء التوقف
        if should_end:
            dt.end_time = end_time
            
            # إضافة ملاحظة الإنهاء
            end_note = f"\n\nتم الإنهاء يدوياً: {end_reason}\nتاريخ النهاية: {end_time}"
            if dt.description:
                dt.description += end_note
            else:
                dt.description = f"تم الإنهاء يدوياً: {end_reason}\nتاريخ النهاية: {end_time}"
            
            dt.save()
            ended_count += 1
            
            print(f"✅ تم إنهاء سجل التوقف {dt.id} للجهاز {dt.device.name}")
            print(f"   تاريخ النهاية: {end_time}")
            print(f"   السبب: {end_reason}")
    
    print(f"\nتم إنهاء {ended_count} سجل توقف")

if __name__ == "__main__":
    check_all_active_downtimes()
    
    # السؤال عن الإنهاء اليدوي
    print("\n" + "="*50)
    manually_end_downtimes()
