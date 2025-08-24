import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from datetime import datetime, timedelta
import random
from django.contrib.auth import get_user_model
from maintenance.models import Device, ScanSession, ScanHistory
from manager.models import Patient, Bed
from hr.models import CustomUser

def run():
    print("🚀 إنشاء جلسات مسح تجريبية...")
    
    # Create sample users
    users_data = [
        {"username": "doctor1", "first_name": "أحمد", "last_name": "محمد"},
        {"username": "nurse1", "first_name": "فاطمة", "last_name": "علي"},
        {"username": "tech1", "first_name": "محمد", "last_name": "أحمد"},
    ]
    
    created_users = []
    for user_data in users_data:
        user, created = CustomUser.objects.get_or_create(
            username=user_data["username"],
            defaults={
                "first_name": user_data["first_name"],
                "last_name": user_data["last_name"],
                "email": f"{user_data['username']}@hospital.com",
                "is_active": True
            }
        )
        if created:
            user.set_password("password123")
            user.save()
            print(f"   ✅ تم إنشاء المستخدم: {user.get_full_name()}")
        created_users.append(user)
    
    # Create sample patients
    patients_data = [
        {"name": "أحمد محمد", "mrn": "P001"},
        {"name": "فاطمة علي", "mrn": "P002"},
        {"name": "محمد أحمد", "mrn": "P003"},
        {"name": "سارة حسن", "mrn": "P004"},
    ]
    
    created_patients = []
    for patient_data in patients_data:
        patient, created = Patient.objects.get_or_create(
            mrn=patient_data["mrn"],
            defaults={
                "first_name": patient_data["name"].split()[0],
                "last_name": " ".join(patient_data["name"].split()[1:]),
                "date_of_birth": "1990-01-15",
                "gender": "M",
                "phone": "01234567890",
            }
        )
        if created:
            print(f"   ✅ تم إنشاء المريض: {patient.get_full_name()}")
        created_patients.append(patient)
    
    # Create sample devices
    devices_data = [
        {"name": "جهاز أشعة سينية", "serial": "XR001"},
        {"name": "جهاز الموجات فوق الصوتية", "serial": "US002"},
        {"name": "جهاز تخطيط القلب", "serial": "ECG003"},
    ]
    
    created_devices = []
    for device_data in devices_data:
        device, created = Device.objects.get_or_create(
            serial_number=device_data["serial"],
            defaults={
                "name": device_data["name"],
                "device_type": "Medical",
                "status": "working",
                "availability": True,
            }
        )
        if created:
            print(f"   ✅ تم إنشاء الجهاز: {device.name}")
        created_devices.append(device)
    
    # Create sample sessions
    operations = ["usage", "transfer", "maintenance", "clean"]
    
    for i in range(5):
        user = random.choice(created_users)
        patient = random.choice(created_patients)
        device = random.choice(created_devices)
        operation = random.choice(operations)
        
        session = ScanSession.objects.create(
            user=user,
            patient=patient,
            operation_type=operation,
            status='completed',
            context_json={'test_session': True}
        )
        
        # Create scan history
        scans = [
            {'type': 'user', 'id': user.id, 'data': {'name': user.get_full_name()}},
            {'type': 'patient', 'id': patient.id, 'data': {'name': patient.get_full_name(), 'mrn': patient.mrn}},
            {'type': 'device', 'id': device.id, 'data': {'name': device.name}},
        ]
        
        for scan in scans:
            ScanHistory.objects.create(
                session=session,
                scanned_code=f"{scan['type']}:{scan['id']}",
                entity_type=scan['type'],
                entity_id=scan['id'],
                entity_data=scan['data'],
                is_valid=True
            )
        
        print(f"   ✅ جلسة {i+1}: {user.get_full_name()} → {patient.get_full_name()} → {device.name}")
    
    print("\n🎉 تم إنشاء البيانات التجريبية!")
    print(f"📊 المستخدمين: {CustomUser.objects.count()}")
    print(f"📊 المرضى: {Patient.objects.count()}")
    print(f"📊 الأجهزة: {Device.objects.count()}")
    print(f"📊 الجلسات: {ScanSession.objects.count()}")

if __name__ == "__main__":
    run()
