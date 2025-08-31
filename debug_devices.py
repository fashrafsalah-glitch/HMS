#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from maintenance.models import Device
from manager.models import Department

# Check department 5 (General Surgery)
try:
    dept = Department.objects.get(id=5)
    print(f"Department: {dept.name}")
    
    # Get all devices in this department
    devices = Device.objects.filter(department=dept)
    print(f"Total devices in department: {devices.count()}")
    
    if devices.exists():
        print("\nDevices found:")
        for device in devices:
            print(f"- ID: {device.id}, Name: {device.name}, Status: {device.status}, Room: {device.room}")
    else:
        print("No devices found in this department")
        
    # Check all devices and their departments
    print(f"\nAll devices in system:")
    all_devices = Device.objects.all()
    for device in all_devices:
        print(f"- ID: {device.id}, Name: {device.name}, Department: {device.department.name if device.department else 'None'}")
        
except Department.DoesNotExist:
    print("Department with ID 5 does not exist")
except Exception as e:
    print(f"Error: {e}")
