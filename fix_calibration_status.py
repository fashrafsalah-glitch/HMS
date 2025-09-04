#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
django.setup()

from maintenance.models import CalibrationRecord
from datetime import date

def fix_calibration_status():
    today = date.today()
    print(f"Today: {today}")
    
    # Find calibration due on 2025-09-06 with completed status
    cal = CalibrationRecord.objects.filter(
        next_calibration_date=date(2025, 9, 6),
        status='completed'
    ).first()
    
    if cal:
        device_name = str(cal.device.name).encode('ascii', 'replace').decode('ascii')
        print(f"Found calibration for device: {device_name}")
        print(f"Current status: {cal.status}")
        print(f"Next due date: {cal.next_calibration_date}")
        
        # Change status to overdue since it's past due
        cal.status = 'overdue'
        cal.save()
        
        print(f"Updated status to: {cal.status}")
        print("Calibration will now be picked up by the scheduler!")
    else:
        print("No calibration found with the specified criteria")

if __name__ == "__main__":
    fix_calibration_status()
