"""
Quick script to generate test scan sessions
Run with: python manage.py shell -c "exec(open('quick_test_data.py').read())"
"""

from datetime import datetime, timedelta
import random
from django.contrib.auth import get_user_model
from maintenance.models import Device, ScanSession, ScanHistory
from manager.models import Patient
from hr.models import CustomUser
from superadmin.models import Hospital

print("🚀 إنشاء بيانات تجريبية سريعة...")

# Get or create hospital first
hospital, created = Hospital.objects.get_or_create(
    name="مستشفى تجريبي",
    defaults={
        "hospital_type": "general",
        "address": "عنوان تجريبي",
        "phone": "01000000000",
        "email": "info@test-hospital.com",
    }
)
if created:
    print(f"✅ تم إنشاء المستشفى: {hospital.name}")

# Get or create test user
user, created = CustomUser.objects.get_or_create(
    username="testdoctor",
    defaults={
        "first_name": "دكتور",
        "last_name": "تجريبي",
        "email": "test@hospital.com",
        "is_active": True
    }
)
if created:
    user.set_password("test123")
    user.save()
    print(f"✅ تم إنشاء المستخدم: {user.get_full_name()}")

# Get or create test patient
patient, created = Patient.objects.get_or_create(
    mrn="TEST001",
    defaults={
        "first_name": "مريض",
        "last_name": "تجريبي",
        "birth_year": 1990,
        "birth_month": 1,
        "birth_day": 1,
        "gender": "Male",
        "phone_number": "01000000000",
        "address": "عنوان تجريبي",
        "national_id": "12345678901234",
        "hospital": hospital,
    }
)
if created:
    print(f"✅ تم إنشاء المريض: {patient.get_full_name()}")

# Get or create test device
device, created = Device.objects.get_or_create(
    serial_number="TEST001",
    defaults={
        "name": "جهاز تجريبي",
        "device_type": "Test",
        "status": "working",
        "availability": True,
    }
)
if created:
    print(f"✅ تم إنشاء الجهاز: {device.name}")

# Create 3 test sessions
for i in range(3):
    session = ScanSession.objects.create(
        user=user,
        patient=patient,
        operation_type="usage",
        status='completed',
        context_json={'test_session': True, 'session_num': i+1}
    )
    
    # Create scan history
    scans = [
        {'type': 'user', 'id': user.id, 'code': f'user:{user.id}'},
        {'type': 'patient', 'id': patient.id, 'code': f'patient:{patient.id}|MRN:{patient.mrn}|Name:{patient.first_name}_{patient.last_name}|DOB:{patient.date_of_birth}'},
        {'type': 'device', 'id': device.id, 'code': f'device:{device.id}'},
    ]
    
    for j, scan in enumerate(scans):
        ScanHistory.objects.create(
            session=session,
            scanned_code=scan['code'],
            entity_type=scan['type'],
            entity_id=scan['id'],
            entity_data={
                'name': user.get_full_name() if scan['type'] == 'user' else 
                       patient.get_full_name() if scan['type'] == 'patient' else 
                       device.name,
                'timestamp': datetime.now().isoformat()
            },
            is_valid=True,
            scanned_at=datetime.now() - timedelta(minutes=j)
        )
    
    print(f"✅ جلسة {i+1}: {session.session_id}")

print(f"\n🎉 تم إنشاء {ScanSession.objects.filter(context_json__test_session=True).count()} جلسة تجريبية!")
print("🔗 اذهب إلى: http://localhost:8000/maintenance/scan/")
