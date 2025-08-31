#!/usr/bin/env python
"""
اختبار نظام طلبات الخدمة الطارئة مع SLA و Job Plans
"""
import os
import sys
import django
from datetime import datetime, timedelta

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from maintenance.models import (
    Device, ServiceRequest, SLADefinition, SLAMatrix, JobPlan,
    DeviceCategory, WorkOrder
)
from hr.models import CustomUser
from manager.models import Department
from django.utils import timezone

def test_emergency_request_system():
    """اختبار نظام طلبات الخدمة الطارئة"""
    
    print("=" * 60)
    print("🚨 اختبار نظام طلبات الخدمة الطارئة")
    print("=" * 60)
    
    # 1. فحص البيانات الموجودة
    print("\n📊 فحص البيانات الموجودة:")
    print(f"عدد الأجهزة: {Device.objects.count()}")
    print(f"عدد تعريفات SLA: {SLADefinition.objects.count()}")
    print(f"عدد مصفوفات SLA: {SLAMatrix.objects.count()}")
    print(f"عدد خطط العمل: {JobPlan.objects.count()}")
    print(f"عدد المستخدمين: {CustomUser.objects.count()}")
    
    # 2. اختيار جهاز للاختبار
    device = Device.objects.first()
    if not device:
        print("❌ لا توجد أجهزة في النظام!")
        return
    
    print(f"\n🔧 الجهاز المختار للاختبار: {device.name}")
    print(f"   الفئة: {device.category.name if device.category else 'غير محدد'}")
    print(f"   القسم: {device.department.name if device.department else 'غير محدد'}")
    
    # 3. اختيار مستخدم للاختبار
    user = CustomUser.objects.filter(is_active=True).first()
    if not user:
        print("❌ لا توجد مستخدمين نشطين!")
        return
    
    print(f"\n👤 المستخدم: {user.get_full_name() or user.username}")
    
    # 4. فحص SLA المتاح للجهاز
    print(f"\n🎯 فحص SLA للجهاز:")
    if device.category:
        sla_matrices = SLAMatrix.objects.filter(
            device_category=device.category,
            is_active=True
        )
        print(f"   مصفوفات SLA للفئة: {sla_matrices.count()}")
        
        for matrix in sla_matrices:
            print(f"   - {matrix.get_severity_display()} / {matrix.get_impact_display()}: "
                  f"استجابة {matrix.sla_definition.response_time_hours}س، "
                  f"حل {matrix.sla_definition.resolution_time_hours}س")
    
    # 5. فحص Job Plans المتاحة
    print(f"\n📋 فحص خطط العمل:")
    if device.category:
        job_plans = JobPlan.objects.filter(
            device_category=device.category,
            is_active=True
        )
        print(f"   خطط العمل للفئة: {job_plans.count()}")
        
        for plan in job_plans:
            print(f"   - {plan.name}: {plan.estimated_hours} ساعة ({plan.get_job_type_display()})")
    
    # 6. إنشاء طلب خدمة طارئة
    print(f"\n🚨 إنشاء طلب خدمة طارئة...")
    
    try:
        # حفظ الوقت قبل الإنشاء
        start_time = timezone.now()
        
        service_request = ServiceRequest.objects.create(
            device=device,
            reporter=user,
            title=f"طلب صيانة مستعجلة - {device.name}",
            description="عطل مفاجئ في الجهاز يتطلب تدخل فوري",
            request_type='emergency',
            severity='high',
            impact='high',
            priority='high'
        )
        
        print(f"✅ تم إنشاء طلب الخدمة رقم: {service_request.id}")
        print(f"   العنوان: {service_request.title}")
        print(f"   النوع: {service_request.get_request_type_display()}")
        print(f"   الخطورة: {service_request.get_severity_display()}")
        print(f"   التأثير: {service_request.get_impact_display()}")
        
        # 7. فحص حساب SLA
        print(f"\n⏰ فحص حساب SLA:")
        if service_request.response_due:
            response_hours = (service_request.response_due - start_time).total_seconds() / 3600
            print(f"   موعد الاستجابة: {service_request.response_due.strftime('%Y-%m-%d %H:%M')}")
            print(f"   مدة الاستجابة: {response_hours:.1f} ساعة")
        else:
            print("   ❌ لم يتم حساب موعد الاستجابة!")
        
        if service_request.resolution_due:
            resolution_hours = (service_request.resolution_due - start_time).total_seconds() / 3600
            print(f"   موعد الحل: {service_request.resolution_due.strftime('%Y-%m-%d %H:%M')}")
            print(f"   مدة الحل: {resolution_hours:.1f} ساعة")
        else:
            print("   ❌ لم يتم حساب موعد الحل!")
        
        # 8. فحص الساعات المقدرة من Job Plan
        print(f"\n📊 فحص الساعات المقدرة:")
        if service_request.estimated_hours:
            print(f"   الساعات المقدرة: {service_request.estimated_hours} ساعة")
        else:
            print("   ❌ لم يتم تحديد الساعات المقدرة!")
        
        # 9. فحص إنشاء أمر الشغل التلقائي
        print(f"\n🔧 فحص أمر الشغل التلقائي:")
        work_orders = service_request.work_orders.all()
        if work_orders.exists():
            wo = work_orders.first()
            print(f"   ✅ تم إنشاء أمر الشغل: {wo.wo_number}")
            print(f"   العنوان: {wo.title}")
            print(f"   النوع: {wo.get_wo_type_display()}")
            print(f"   الحالة: {wo.get_status_display()}")
            if wo.estimated_hours:
                print(f"   الساعات المقدرة: {wo.estimated_hours} ساعة")
        else:
            print("   ❌ لم يتم إنشاء أمر شغل تلقائي!")
        
        # 10. فحص حالة SLA
        print(f"\n📈 فحص حالة SLA:")
        sla_status = service_request.get_sla_status()
        print(f"   حالة SLA: {sla_status}")
        
        if service_request.is_overdue_response():
            print("   ⚠️ تجاوز وقت الاستجابة!")
        else:
            print("   ✅ ضمن وقت الاستجابة")
        
        if service_request.is_overdue_resolution():
            print("   ⚠️ تجاوز وقت الحل!")
        else:
            print("   ✅ ضمن وقت الحل")
        
        # 11. ملخص النتائج
        print(f"\n📋 ملخص النتائج:")
        print("=" * 40)
        
        success_count = 0
        total_tests = 4
        
        if service_request.response_due:
            print("✅ حساب موعد الاستجابة")
            success_count += 1
        else:
            print("❌ حساب موعد الاستجابة")
        
        if service_request.resolution_due:
            print("✅ حساب موعد الحل")
            success_count += 1
        else:
            print("❌ حساب موعد الحل")
        
        if service_request.estimated_hours:
            print("✅ ربط Job Plan والساعات المقدرة")
            success_count += 1
        else:
            print("❌ ربط Job Plan والساعات المقدرة")
        
        if work_orders.exists():
            print("✅ إنشاء أمر الشغل التلقائي")
            success_count += 1
        else:
            print("❌ إنشاء أمر الشغل التلقائي")
        
        print("=" * 40)
        print(f"النتيجة النهائية: {success_count}/{total_tests} ({(success_count/total_tests)*100:.0f}%)")
        
        if success_count == total_tests:
            print("🎉 النظام يعمل بشكل مثالي!")
        elif success_count >= total_tests * 0.75:
            print("✅ النظام يعمل بشكل جيد مع بعض التحسينات المطلوبة")
        else:
            print("⚠️ النظام يحتاج إلى إصلاحات")
        
        return service_request
        
    except Exception as e:
        print(f"❌ خطأ في إنشاء طلب الخدمة: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def test_sla_calculations():
    """اختبار حسابات SLA المختلفة"""
    
    print("\n" + "=" * 60)
    print("⏰ اختبار حسابات SLA للخطورات المختلفة")
    print("=" * 60)
    
    device = Device.objects.first()
    user = CustomUser.objects.filter(is_active=True).first()
    
    if not device or not user:
        print("❌ لا توجد بيانات كافية للاختبار!")
        return
    
    severities = ['low', 'medium', 'high', 'critical']
    
    for severity in severities:
        print(f"\n🔍 اختبار الخطورة: {severity}")
        
        try:
            sr = ServiceRequest.objects.create(
                device=device,
                reporter=user,
                title=f"اختبار {severity}",
                description=f"اختبار طلب خدمة بخطورة {severity}",
                request_type='emergency',
                severity=severity,
                impact='moderate',
                priority='medium'
            )
            
            if sr.response_due and sr.resolution_due:
                response_hours = (sr.response_due - sr.created_at).total_seconds() / 3600
                resolution_hours = (sr.resolution_due - sr.created_at).total_seconds() / 3600
                
                print(f"   استجابة: {response_hours:.1f} ساعة")
                print(f"   حل: {resolution_hours:.1f} ساعة")
            else:
                print("   ❌ فشل في حساب SLA")
            
            # حذف الطلب التجريبي
            sr.delete()
            
        except Exception as e:
            print(f"   ❌ خطأ: {str(e)}")

if __name__ == "__main__":
    print("🚀 بدء اختبار نظام طلبات الخدمة الطارئة...")
    
    # اختبار النظام الأساسي
    service_request = test_emergency_request_system()
    
    # اختبار حسابات SLA
    test_sla_calculations()
    
    print("\n" + "=" * 60)
    print("✅ انتهى الاختبار")
    print("=" * 60)
