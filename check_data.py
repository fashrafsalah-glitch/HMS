#!/usr/bin/env python
import os
import sys

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

import django
django.setup()

from maintenance.models import ServiceRequest, WorkOrder, SLADefinition, JobPlan, Device
from django.utils import timezone
from datetime import timedelta

print("=== فحص البيانات الفعلية في النظام ===\n")

# فحص الأجهزة وحالاتها
print("1. الأجهزة وحالاتها:")
devices = Device.objects.all()
for device in devices:
    print(f"   - {device.name}: {device.get_status_display()}")

print(f"\nإجمالي الأجهزة: {devices.count()}")

# فحص طلبات الخدمة
print("\n2. طلبات الخدمة:")
service_requests = ServiceRequest.objects.all()
for sr in service_requests:
    print(f"   - {sr.request_number}: {sr.title} - {sr.get_status_display()} - {sr.get_priority_display()}")

# فحص أوامر الشغل
print("\n3. أوامر الشغل:")
work_orders = WorkOrder.objects.all()
for wo in work_orders:
    print(f"   - {wo.work_order_number}: {wo.title} - {wo.get_status_display()}")
    if wo.actual_start and wo.actual_end:
        duration = wo.actual_end - wo.actual_start
        print(f"     المدة الفعلية: {duration}")
    else:
        print(f"     تاريخ الإنشاء: {wo.created_at}")

# فحص تعريفات SLA
print("\n4. تعريفات SLA:")
sla_definitions = SLADefinition.objects.all()
for sla in sla_definitions:
    print(f"   - {sla.name}")
    print(f"     وقت الاستجابة: {sla.response_time_hours} ساعة")
    print(f"     وقت الحل: {sla.resolution_time_hours} ساعة")
    if sla.device_category:
        print(f"     فئة الجهاز: {sla.device_category}")
    if sla.severity:
        print(f"     الخطورة: {sla.get_severity_display()}")

# فحص خطط العمل
print("\n5. خطط العمل:")
job_plans = JobPlan.objects.all()
for jp in job_plans:
    print(f"   - {jp.name}")
    if jp.estimated_duration:
        print(f"     المدة المقدرة: {jp.estimated_duration}")
    steps_count = jp.steps.count()
    print(f"     عدد الخطوات: {steps_count}")

# حساب إحصائيات فعلية
print("\n=== حساب الإحصائيات الفعلية ===")

# حساب MTTR من أوامر الشغل المكتملة
completed_work_orders = WorkOrder.objects.filter(
    status__in=['closed', 'qa_verified'],
    service_request__request_type='corrective'
)

total_repair_time = 0
valid_orders = 0

for wo in completed_work_orders:
    if wo.actual_start and wo.actual_end:
        repair_time = (wo.actual_end - wo.actual_start).total_seconds() / 3600
        total_repair_time += repair_time
        valid_orders += 1
        print(f"أمر شغل {wo.work_order_number}: {repair_time:.2f} ساعة")

if valid_orders > 0:
    mttr = total_repair_time / valid_orders
    print(f"\nMTTR الفعلي: {mttr:.2f} ساعة")
else:
    print("\nلا توجد أوامر شغل مكتملة بأوقات فعلية")

# حساب MTBF
corrective_requests = ServiceRequest.objects.filter(request_type='corrective')
print(f"\nعدد طلبات الصيانة التصحيحية: {corrective_requests.count()}")

# فحص SLA compliance
print("\n=== فحص الالتزام بـ SLA ===")
for sr in service_requests:
    # البحث عن SLA مناسب
    applicable_sla = None
    for sla in sla_definitions:
        if sla.applies_to_request(sr):
            applicable_sla = sla
            break
    
    if applicable_sla:
        print(f"طلب {sr.request_number}: SLA = {applicable_sla.name}")
        # حساب وقت الاستجابة
        if sr.assigned_to and sr.updated_at:
            response_time = (sr.updated_at - sr.created_at).total_seconds() / 3600
            print(f"  وقت الاستجابة الفعلي: {response_time:.2f} ساعة (المطلوب: {applicable_sla.response_time_hours})")
    else:
        print(f"طلب {sr.request_number}: لا يوجد SLA مناسب")

print("\n=== انتهى الفحص ===")
