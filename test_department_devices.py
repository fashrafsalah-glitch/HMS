#!/usr/bin/env python
"""
Test script to debug department devices display issue
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from maintenance.models import Device, DeviceTransferRequest
from manager.models import Department

def test_department_devices():
    print("=== Testing Department Devices Display ===")
    
    # Get department 5
    try:
        department = Department.objects.get(id=5)
        print(f"✅ Department found: {department.name}")
    except Department.DoesNotExist:
        print("❌ Department 5 not found")
        return
    
    # Check devices in this department
    all_devices = Device.objects.filter(department=department)
    print(f"📊 Total devices in department: {all_devices.count()}")
    
    for device in all_devices:
        print(f"  - {device.name} (ID: {device.id}, Status: {device.status})")
    
    # Check pending transfers
    pending_transfers = DeviceTransferRequest.objects.filter(
        to_department=department,
        is_approved=False
    ).select_related('device')
    
    print(f"📋 Pending transfers to this department: {pending_transfers.count()}")
    
    pending_devices_ids = [t.device.id for t in pending_transfers]
    print(f"🔄 Pending device IDs: {pending_devices_ids}")
    
    # Check actual devices (excluding pending)
    actual_devices = Device.objects.filter(
        department=department
    ).exclude(id__in=pending_devices_ids)
    
    print(f"✅ Actual devices (excluding pending): {actual_devices.count()}")
    
    for device in actual_devices:
        print(f"  - {device.name} (ID: {device.id})")
        print(f"    Status: {device.get_status_display()}")
        print(f"    Room: {device.room}")
        print(f"    Clean: {device.get_clean_status_display()}")
        print(f"    Sterilization: {device.get_sterilization_status_display()}")
        print(f"    Current Patient: {device.current_patient}")
        print(f"    In Use: {device.in_use}")
        print()

if __name__ == "__main__":
    test_department_devices()
