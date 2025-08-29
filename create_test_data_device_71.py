#!/usr/bin/env python
"""
سكريبت لإنشاء بيانات تجريبية شاملة للجهاز رقم 71
يشمل خطط العمل، الصيانات المجدولة، سجل الصيانة، وأوامر العمل
"""

import os
import sys
import django
from datetime import datetime, timedelta, date
from django.utils import timezone

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from maintenance.models import (
    Device, JobPlan, JobPlanStep, PreventiveMaintenanceSchedule,
    DeviceMaintenanceLog, ServiceRequest, WorkOrder
)
from django.contrib.auth import get_user_model

User = get_user_model()

def create_test_data_for_device_71():
    """إنشاء بيانات تجريبية شاملة للجهاز رقم 71"""
    
    try:
        # الحصول على الجهاز رقم 71
        device = Device.objects.get(id=71)
        print(f"✅ تم العثور على الجهاز: {device.name}")
        
        # الحصول على مستخدم للاختبار (أول مستخدم متاح)
        user = User.objects.first()
        if not user:
            print("❌ لا يوجد مستخدمون في النظام")
            return
            
        print(f"✅ سيتم استخدام المستخدم: {user.username}")
        
        # الحصول على فئة الجهاز
        device_category = device.category
        if not device_category:
            print("❌ الجهاز لا يحتوي على فئة محددة")
            return

        # 1. إنشاء خطط العمل المختلفة
        job_plans_data = [
            {
                'name': 'صيانة وقائية شاملة',
                'description': 'فحص شامل للجهاز وتنظيف وتشحيم الأجزاء المتحركة',
                'estimated_hours': 2.0,
                'job_type': 'preventive',
                'steps': [
                    'فحص الأجزاء الخارجية والتأكد من سلامتها',
                    'تنظيف الجهاز من الداخل والخارج',
                    'فحص الكابلات والتوصيلات الكهربائية',
                    'تشحيم الأجزاء المتحركة',
                    'اختبار وظائف الجهاز الأساسية',
                    'توثيق النتائج والملاحظات'
                ]
            },
            {
                'name': 'معايرة دقيقة',
                'description': 'معايرة الجهاز وفقاً للمعايير الدولية',
                'estimated_hours': 1.5,
                'job_type': 'calibration',
                'steps': [
                    'إعداد معدات المعايرة المطلوبة',
                    'فحص دقة القياسات الحالية',
                    'تعديل إعدادات المعايرة',
                    'اختبار الدقة بعد المعايرة',
                    'توثيق شهادة المعايرة'
                ]
            },
            {
                'name': 'فحص دوري سريع',
                'description': 'فحص سريع للتأكد من سلامة الجهاز',
                'estimated_hours': 0.5,
                'job_type': 'inspection',
                'steps': [
                    'فحص بصري للجهاز',
                    'اختبار التشغيل الأساسي',
                    'فحص مؤشرات الأمان',
                    'توثيق الحالة العامة'
                ]
            },
            {
                'name': 'صيانة طارئة',
                'description': 'إصلاح الأعطال الطارئة',
                'estimated_hours': 3.0,
                'job_type': 'corrective',
                'steps': [
                    'تشخيص العطل',
                    'تحديد القطع المطلوب استبدالها',
                    'تنفيذ الإصلاح',
                    'اختبار الجهاز بعد الإصلاح',
                    'توثيق الأعمال المنجزة'
                ]
            }
        ]
        
        created_job_plans = []
        for plan_data in job_plans_data:
            job_plan, created = JobPlan.objects.get_or_create(
                name=plan_data['name'],
                defaults={
                    'description': plan_data['description'],
                    'device_category': device_category,
                    'job_type': plan_data['job_type'],
                    'estimated_hours': plan_data['estimated_hours'],
                    'created_by': user
                }
            )
            
            if created:
                print(f"✅ تم إنشاء خطة العمل: {job_plan.name}")
                
                # إضافة خطوات العمل
                for i, step_desc in enumerate(plan_data['steps'], 1):
                    JobPlanStep.objects.create(
                        job_plan=job_plan,
                        step_number=i,
                        title=f"الخطوة {i}",
                        description=step_desc,
                        estimated_minutes=int((plan_data['estimated_hours'] * 60) / len(plan_data['steps']))
                    )
            else:
                print(f"ℹ️ خطة العمل موجودة مسبقاً: {job_plan.name}")
                
            created_job_plans.append(job_plan)
        
        # 2. إنشاء جدولة الصيانة الوقائية
        schedules_data = [
            {
                'job_plan': created_job_plans[0],  # صيانة وقائية شاملة
                'frequency': 'monthly',
                'next_due_date': date.today() + timedelta(days=15)
            },
            {
                'job_plan': created_job_plans[1],  # معايرة دقيقة
                'frequency': 'quarterly',
                'next_due_date': date.today() + timedelta(days=45)
            },
            {
                'job_plan': created_job_plans[2],  # فحص دوري سريع
                'frequency': 'weekly',
                'next_due_date': date.today() + timedelta(days=7)
            }
        ]
        
        for schedule_data in schedules_data:
            schedule, created = PreventiveMaintenanceSchedule.objects.get_or_create(
                device=device,
                job_plan=schedule_data['job_plan'],
                defaults={
                    'frequency': schedule_data['frequency'],
                    'next_due_date': schedule_data['next_due_date'],
                    'created_by': user
                }
            )
            
            if created:
                print(f"✅ تم إنشاء جدولة صيانة: {schedule.job_plan.name} - {schedule.get_frequency_display()}")
            else:
                print(f"ℹ️ جدولة الصيانة موجودة مسبقاً: {schedule.job_plan.name}")
        
        # 3. إنشاء سجل صيانة سابقة
        maintenance_logs_data = [
            {
                'maintenance_type': 'preventive',
                'maintained_at': timezone.now() - timedelta(days=30),
                'description': 'صيانة وقائية شاملة - تم تنظيف الجهاز وفحص جميع المكونات',
                'cost': 150.00,
                'parts_replaced': 'فلتر الهواء، زيت التشحيم'
            },
            {
                'maintenance_type': 'calibration',
                'maintained_at': timezone.now() - timedelta(days=90),
                'description': 'معايرة دقيقة للجهاز وفقاً للمعايير الدولية',
                'cost': 200.00,
                'parts_replaced': ''
            },
            {
                'maintenance_type': 'corrective',
                'maintained_at': timezone.now() - timedelta(days=60),
                'description': 'إصلاح عطل في نظام التحكم الإلكتروني',
                'cost': 350.00,
                'parts_replaced': 'لوحة التحكم الرئيسية'
            },
            {
                'maintenance_type': 'inspection',
                'maintained_at': timezone.now() - timedelta(days=15),
                'description': 'فحص دوري سريع - الجهاز في حالة جيدة',
                'cost': 50.00,
                'parts_replaced': ''
            },
            {
                'maintenance_type': 'preventive',
                'maintained_at': timezone.now() - timedelta(days=7),
                'description': 'تنظيف وتشحيم الأجزاء المتحركة',
                'cost': 75.00,
                'parts_replaced': 'شحم متخصص'
            }
        ]
        
        for log_data in maintenance_logs_data:
            DeviceMaintenanceLog.objects.create(
                device=device,
                maintenance_type=log_data['maintenance_type'],
                maintained_at=log_data['maintained_at'],
                maintained_by=user,
                description=log_data['description'],
                cost=log_data['cost'],
                parts_replaced=log_data['parts_replaced']
            )
            print(f"✅ تم إنشاء سجل صيانة: {log_data['maintenance_type']} - {log_data['maintained_at'].date()}")
        
        # 4. إنشاء طلبات خدمة وأوامر عمل
        service_requests_data = [
            {
                'title': 'عطل في نظام العرض',
                'description': 'الشاشة لا تعرض البيانات بوضوح',
                'priority': 'high',
                'request_type': 'corrective',
                'status': 'closed'
            },
            {
                'title': 'صيانة وقائية مجدولة',
                'description': 'صيانة وقائية شهرية حسب الجدولة',
                'priority': 'medium',
                'request_type': 'preventive',
                'status': 'in_progress'
            },
            {
                'title': 'طلب معايرة',
                'description': 'معايرة الجهاز قبل انتهاء صلاحية الشهادة',
                'priority': 'medium',
                'request_type': 'calibration',
                'status': 'open'
            }
        ]
        
        for i, sr_data in enumerate(service_requests_data, 1):
            # إنشاء طلب الخدمة
            service_request = ServiceRequest.objects.create(
                title=sr_data['title'],
                description=sr_data['description'],
                device=device,
                reporter=user,
                priority=sr_data['priority'],
                request_type=sr_data['request_type'],
                status=sr_data['status'],
                created_at=timezone.now() - timedelta(days=i*5)
            )
            print(f"✅ تم إنشاء طلب خدمة: {service_request.title}")
            
            # إنشاء أمر عمل مرتبط
            work_order = WorkOrder.objects.create(
                wo_number=f"WO-{device.id}-{timezone.now().year}-{i:03d}",
                title=f"أمر عمل: {sr_data['title']}",
                description=f"تنفيذ {sr_data['description']}",
                service_request=service_request,
                priority=sr_data['priority'],
                status=sr_data['status'],
                assignee=user,
                created_by=user,
                created_at=timezone.now() - timedelta(days=i*5)
            )
            print(f"✅ تم إنشاء أمر عمل: {work_order.wo_number}")
        
        print(f"\n🎉 تم إنشاء جميع البيانات التجريبية للجهاز {device.name} بنجاح!")
        print("\n📊 ملخص البيانات المنشأة:")
        print(f"- خطط العمل: {len(created_job_plans)}")
        print(f"- جدولة الصيانة: {len(schedules_data)}")
        print(f"- سجلات الصيانة: {len(maintenance_logs_data)}")
        print(f"- طلبات الخدمة: {len(service_requests_data)}")
        print(f"- أوامر العمل: {len(service_requests_data)}")
        
    except Device.DoesNotExist:
        print("❌ الجهاز رقم 71 غير موجود في قاعدة البيانات")
    except Exception as e:
        print(f"❌ حدث خطأ: {str(e)}")

if __name__ == "__main__":
    create_test_data_for_device_71()
