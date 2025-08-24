#!/usr/bin/env python
"""
Data migration script to populate QR codes for existing records
Run this script after applying migrations to generate QR codes for all existing entities
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from manager.models import Patient, Bed
from hr.models import CustomUser
from maintenance.models import Device, DeviceAccessory


def populate_qr_codes():
    """Generate QR codes for all existing entities"""
    
    print("🔄 Starting QR code population for existing records...")
    
    # Patient QR codes
    print("\n📋 Processing Patients...")
    patients = Patient.objects.filter(qr_token__isnull=True)
    patient_count = 0
    for patient in patients:
        try:
            patient.qr_token = patient.generate_qr_token()
            patient.generate_qr_code()
            patient.save(update_fields=['qr_token', 'qr_code'])
            patient_count += 1
            print(f"  ✅ Patient {patient.id}: {patient.first_name} {patient.last_name}")
        except Exception as e:
            print(f"  ❌ Error with Patient {patient.id}: {e}")
    
    print(f"📋 Processed {patient_count} patients")
    
    # Bed QR codes
    print("\n🛏️ Processing Beds...")
    beds = Bed.objects.filter(qr_token__isnull=True)
    bed_count = 0
    for bed in beds:
        try:
            bed.qr_token = bed.generate_qr_token()
            bed.generate_qr_code()
            bed.save(update_fields=['qr_token', 'qr_code'])
            bed_count += 1
            print(f"  ✅ Bed {bed.id}: {bed}")
        except Exception as e:
            print(f"  ❌ Error with Bed {bed.id}: {e}")
    
    print(f"🛏️ Processed {bed_count} beds")
    
    # CustomUser QR codes
    print("\n👥 Processing Users...")
    users = CustomUser.objects.filter(qr_token__isnull=True)
    user_count = 0
    for user in users:
        try:
            user.qr_token = user.generate_qr_token()
            user.generate_qr_code()
            user.save(update_fields=['qr_token', 'qr_code'])
            user_count += 1
            print(f"  ✅ User {user.id}: {user.get_full_name()} ({user.role})")
        except Exception as e:
            print(f"  ❌ Error with User {user.id}: {e}")
    
    print(f"👥 Processed {user_count} users")
    
    # Device QR codes (existing ones that might not have QR)
    print("\n🔧 Processing Devices...")
    devices = Device.objects.filter(qr_token__isnull=True)
    device_count = 0
    for device in devices:
        try:
            device.qr_token = device.generate_qr_token()
            device.generate_qr_code()
            device.save(update_fields=['qr_token', 'qr_code'])
            device_count += 1
            print(f"  ✅ Device {device.id}: {device.name}")
        except Exception as e:
            print(f"  ❌ Error with Device {device.id}: {e}")
    
    print(f"🔧 Processed {device_count} devices")
    
    # DeviceAccessory QR codes
    print("\n🔩 Processing Device Accessories...")
    accessories = DeviceAccessory.objects.filter(qr_token__isnull=True)
    accessory_count = 0
    for accessory in accessories:
        try:
            accessory.qr_token = accessory.generate_qr_token()
            accessory.generate_qr_code()
            accessory.save(update_fields=['qr_token', 'qr_code'])
            accessory_count += 1
            print(f"  ✅ Accessory {accessory.id}: {accessory.name}")
        except Exception as e:
            print(f"  ❌ Error with Accessory {accessory.id}: {e}")
    
    print(f"🔩 Processed {accessory_count} accessories")
    
    # Summary
    total_processed = patient_count + bed_count + user_count + device_count + accessory_count
    print(f"\n🎉 QR Code Population Complete!")
    print(f"📊 Total records processed: {total_processed}")
    print(f"   📋 Patients: {patient_count}")
    print(f"   🛏️ Beds: {bed_count}")
    print(f"   👥 Users: {user_count}")
    print(f"   🔧 Devices: {device_count}")
    print(f"   🔩 Accessories: {accessory_count}")


if __name__ == '__main__':
    populate_qr_codes()
