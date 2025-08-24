#!/usr/bin/env python
"""
Script to automatically create sample scan sessions for HMS QR/Barcode system
Run this script with: python manage.py shell < create_sample_sessions.py
"""

from datetime import datetime, timedelta
import random

from django.contrib.auth import get_user_model
from maintenance.models import Device, ScanSession, ScanHistory
from manager.models import Patient, Bed, Doctor
from hr.models import CustomUser

User = get_user_model()

def create_sample_sessions():
    """Create sample scan sessions with realistic data"""
    
    print("🚀 إنشاء جلسات مسح تجريبية...")
    
    # Sample data
    sample_users = [
        {"username": "doctor1", "first_name": "أحمد", "last_name": "محمد", "email": "doctor1@hospital.com"},
        {"username": "nurse1", "first_name": "فاطمة", "last_name": "علي", "email": "nurse1@hospital.com"},
        {"username": "tech1", "first_name": "محمد", "last_name": "أحمد", "email": "tech1@hospital.com"},
    ]
    
    sample_patients = [
        {"name": "أحمد محمد", "mrn": "P001", "dob": "1990-01-15"},
        {"name": "فاطمة علي", "mrn": "P002", "dob": "1985-05-20"},
        {"name": "محمد أحمد", "mrn": "P003", "dob": "1992-03-10"},
        {"name": "سارة حسن", "mrn": "P004", "dob": "1988-12-25"},
        {"name": "علي محمود", "mrn": "P005", "dob": "1995-08-30"},
    ]
    
    sample_devices = [
        {"name": "جهاز أشعة سينية", "serial_number": "XR001", "device_type": "X-Ray"},
        {"name": "جهاز الموجات فوق الصوتية", "serial_number": "US002", "device_type": "Ultrasound"},
        {"name": "جهاز تخطيط القلب", "serial_number": "ECG003", "device_type": "ECG"},
        {"name": "جهاز قياس الضغط", "serial_number": "BP004", "device_type": "Blood Pressure"},
        {"name": "جهاز السكر", "serial_number": "GLU005", "device_type": "Glucose Meter"},
    ]
    
    sample_beds = [
        {"name": "سرير 101", "room_number": "101"},
        {"name": "سرير 102", "room_number": "102"},
        {"name": "سرير 201", "room_number": "201"},
        {"name": "سرير 202", "room_number": "202"},
    ]
    
    operations = ["usage", "transfer", "patient_transfer", "handover", "clean", "sterilize", "maintenance"]
    
    # Create users
    print("👥 إنشاء المستخدمين...")
    created_users = []
    for user_data in sample_users:
        user, created = CustomUser.objects.get_or_create(
            username=user_data["username"],
            defaults={
                "first_name": user_data["first_name"],
                "last_name": user_data["last_name"],
                "email": user_data["email"],
                "is_active": True
            }
        )
        if created:
            user.set_password("password123")
            user.save()
            print(f"   ✅ تم إنشاء المستخدم: {user.get_full_name()}")
        created_users.append(user)
    
    # Create patients
    print("🏥 إنشاء المرضى...")
    created_patients = []
    for patient_data in sample_patients:
        patient, created = Patient.objects.get_or_create(
            mrn=patient_data["mrn"],
            defaults={
                "first_name": patient_data["name"].split()[0],
                "last_name": " ".join(patient_data["name"].split()[1:]),
                "date_of_birth": patient_data["dob"],
                "gender": random.choice(["M", "F"]),
                "phone": f"01{random.randint(100000000, 999999999)}",
            }
        )
        if created:
            print(f"   ✅ تم إنشاء المريض: {patient.get_full_name()} - {patient.mrn}")
        created_patients.append(patient)
    
    # Create devices
    print("🔧 إنشاء الأجهزة...")
    created_devices = []
    for device_data in sample_devices:
        device, created = Device.objects.get_or_create(
            serial_number=device_data["serial_number"],
            defaults={
                "name": device_data["name"],
                "device_type": device_data["device_type"],
                "status": "working",
                "availability": True,
                "clean_status": "clean",
                "sterilization_status": "sterilized",
            }
        )
        if created:
            print(f"   ✅ تم إنشاء الجهاز: {device.name} - {device.serial_number}")
        created_devices.append(device)
    
    # Create beds
    print("🛏️ إنشاء الأسرة...")
    created_beds = []
    for bed_data in sample_beds:
        bed, created = Bed.objects.get_or_create(
            name=bed_data["name"],
            defaults={
                "room_number": bed_data["room_number"],
                "status": "available",
                "bed_type": "standard",
            }
        )
        if created:
            print(f"   ✅ تم إنشاء السرير: {bed.name} - غرفة {bed.room_number}")
        created_beds.append(bed)
    
    # Create sample scan sessions
    print("📱 إنشاء جلسات المسح...")
    
    for i in range(10):  # Create 10 sample sessions
        # Pick random data
        user = random.choice(created_users)
        patient = random.choice(created_patients)
        device = random.choice(created_devices)
        bed = random.choice(created_beds) if random.choice([True, False]) else None
        operation = random.choice(operations)
        
        # Create session
        session = ScanSession.objects.create(
            user=user,
            patient=patient,
            bed=bed,
            operation_type=operation,
            status='completed',
            context_json={
                'operation_hint': operation,
                'created_by_script': True,
                'session_number': i + 1
            }
        )
        
        # Create scan history for this session
        scan_items = [
            {'entity_type': 'user', 'entity_id': user.id, 'entity_data': {'name': user.get_full_name()}},
            {'entity_type': 'patient', 'entity_id': patient.id, 'entity_data': {'name': patient.get_full_name(), 'mrn': patient.mrn}},
            {'entity_type': 'device', 'entity_id': device.id, 'entity_data': {'name': device.name, 'serial_number': device.serial_number}},
        ]
        
        if bed:
            scan_items.append({'entity_type': 'bed', 'entity_id': bed.id, 'entity_data': {'name': bed.name, 'room': bed.room_number}})
        
        # Add operation token
        scan_items.append({'entity_type': 'operation_token', 'entity_id': 0, 'entity_data': {'operation': operation}})
        
        for j, scan_item in enumerate(scan_items):
            ScanHistory.objects.create(
                session=session,
                scanned_code=f"{scan_item['entity_type']}:{scan_item['entity_id']}",
                entity_type=scan_item['entity_type'],
                entity_id=scan_item['entity_id'],
                entity_data=scan_item['entity_data'],
                is_valid=True,
                scanned_at=datetime.now() - timedelta(minutes=random.randint(1, 60))
            )
        
        print(f"   ✅ جلسة {i + 1}: {user.get_full_name()} → {patient.get_full_name()} → {device.name} ({operation})")
    
    print("\n🎉 تم إنشاء البيانات التجريبية بنجاح!")
    print(f"📊 الإحصائيات:")
    print(f"   👥 المستخدمين: {CustomUser.objects.count()}")
    print(f"   🏥 المرضى: {Patient.objects.count()}")
    print(f"   🔧 الأجهزة: {Device.objects.count()}")
    print(f"   🛏️ الأسرة: {Bed.objects.count()}")
    print(f"   📱 جلسات المسح: {ScanSession.objects.count()}")
    print(f"   📜 سجل المسح: {ScanHistory.objects.count()}")
    
    print("\n🔗 روابط مفيدة:")
    print("   📱 صفحة المسح: http://localhost:8000/maintenance/scan/")
    print("   📊 سجل الاستخدام: http://localhost:8000/maintenance/usage-logs/")
    print("   🧪 مسح المختبر: http://localhost:8000/laboratory/sample-scan/")

def clear_sample_data():
    """Clear all sample data created by this script"""
    print("🗑️ مسح البيانات التجريبية...")
    
    # Delete sessions created by script
    script_sessions = ScanSession.objects.filter(context_json__created_by_script=True)
    count = script_sessions.count()
    script_sessions.delete()
    print(f"   ✅ تم مسح {count} جلسة مسح")
    
    # Delete scan history
    orphaned_history = ScanHistory.objects.filter(session__isnull=True)
    count = orphaned_history.count()
    orphaned_history.delete()
    print(f"   ✅ تم مسح {count} سجل مسح")
    
    print("✅ تم مسح البيانات التجريبية")

# Auto-run when script is executed
print("🚀 بدء إنشاء البيانات التجريبية...")
create_sample_sessions()
