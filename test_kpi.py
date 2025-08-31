#!/usr/bin/env python
import os
import sys
import django

# إعداد Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
sys.path.append('.')
django.setup()

from maintenance.models import Device, ServiceRequest, WorkOrder
from maintenance.kpi_utils import calculate_mtbf, calculate_mttr, calculate_availability

def test_kpi_functions():
    print('=== فحص البيانات الموجودة ===')
    devices_count = Device.objects.count()
    sr_count = ServiceRequest.objects.count()
    wo_count = WorkOrder.objects.count()
    corrective_count = ServiceRequest.objects.filter(request_type='corrective').count()
    
    print(f'عدد الأجهزة: {devices_count}')
    print(f'عدد طلبات الخدمة: {sr_count}')
    print(f'عدد أوامر الشغل: {wo_count}')
    print(f'طلبات الأعطال (corrective): {corrective_count}')

    print('\n=== حالات الأجهزة ===')
    for status, label in Device.DEVICE_STATUS_CHOICES:
        count = Device.objects.filter(status=status).count()
        print(f'{label} ({status}): {count}')

    print('\n=== اختبار الدوال ===')
    if devices_count > 0:
        device = Device.objects.first()
        print(f'اختبار الجهاز: {device.name} (ID: {device.id})')
        
        # اختبار MTBF
        try:
            mtbf = calculate_mtbf(device_id=device.id)
            print(f'MTBF: {mtbf:.2f} ساعة')
        except Exception as e:
            print(f'خطأ MTBF: {e}')
        
        # اختبار MTTR
        try:
            mttr = calculate_mttr(device_id=device.id)
            print(f'MTTR: {mttr:.2f} ساعة')
        except Exception as e:
            print(f'خطأ MTTR: {e}')
        
        # اختبار Availability
        try:
            availability = calculate_availability(device_id=device.id)
            print(f'Availability: {availability:.2f}%')
        except Exception as e:
            print(f'خطأ Availability: {e}')
        
        # اختبار بدون device_id (للكل)
        print('\n=== اختبار للكل ===')
        try:
            mtbf_all = calculate_mtbf()
            mttr_all = calculate_mttr()
            availability_all = calculate_availability()
            print(f'MTBF (الكل): {mtbf_all:.2f} ساعة')
            print(f'MTTR (الكل): {mttr_all:.2f} ساعة')
            print(f'Availability (الكل): {availability_all:.2f}%')
        except Exception as e:
            print(f'خطأ في الحساب العام: {e}')
    else:
        print('لا توجد أجهزة في النظام!')

if __name__ == '__main__':
    test_kpi_functions()
