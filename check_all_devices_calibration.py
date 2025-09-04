#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
django.setup()

from maintenance.models import Device, CalibrationRecord
from datetime import date

def check_all_devices_calibration():
    print("Checking if all devices have calibration records...")
    
    # Get all devices
    all_devices = Device.objects.all()
    print(f"Total devices: {all_devices.count()}")
    
    # Get devices with calibration records
    devices_with_calibration = Device.objects.filter(
        calibrationrecord__isnull=False
    ).distinct()
    print(f"Devices with calibration records: {devices_with_calibration.count()}")
    
    # Get devices without calibration records
    devices_without_calibration = Device.objects.filter(
        calibrationrecord__isnull=True
    )
    print(f"Devices WITHOUT calibration records: {devices_without_calibration.count()}")
    
    print("\n=== DEVICES WITH CALIBRATION ===")
    for device in devices_with_calibration:
        device_name = str(device.name).encode('ascii', 'replace').decode('ascii')
        calibrations = CalibrationRecord.objects.filter(device=device)
        print(f"- {device_name}: {calibrations.count()} calibration record(s)")
        
        for cal in calibrations:
            print(f"  * Next due: {cal.next_calibration_date}, Status: {cal.status}")
    
    if devices_without_calibration.exists():
        print("\n=== DEVICES WITHOUT CALIBRATION ===")
        for device in devices_without_calibration[:10]:  # Show first 10
            device_name = str(device.name).encode('ascii', 'replace').decode('ascii')
            print(f"- {device_name} (Category: {device.category})")
        
        if devices_without_calibration.count() > 10:
            print(f"... and {devices_without_calibration.count() - 10} more devices")
    
    print(f"\n=== SUMMARY ===")
    print(f"Total devices: {all_devices.count()}")
    print(f"With calibration: {devices_with_calibration.count()}")
    print(f"Without calibration: {devices_without_calibration.count()}")
    
    coverage_percentage = (devices_with_calibration.count() / all_devices.count()) * 100 if all_devices.count() > 0 else 0
    print(f"Calibration coverage: {coverage_percentage:.1f}%")

if __name__ == "__main__":
    check_all_devices_calibration()
