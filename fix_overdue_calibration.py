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

def fix_overdue_calibration():
    today = date.today()
    print(f"Today: {today}")
    
    # Find the calibration with status overdue but future date
    cal = CalibrationRecord.objects.filter(
        status='overdue',
        next_calibration_date__gt=today
    ).first()
    
    if cal:
        device_name = str(cal.device.name).encode('ascii', 'replace').decode('ascii')
        print(f"Found problematic calibration for device: {device_name}")
        print(f"Current next_calibration_date: {cal.next_calibration_date}")
        print(f"Current status: {cal.status}")
        
        # Set the date to yesterday to make it truly overdue
        yesterday = date(2025, 9, 3)  # One day before today
        cal.next_calibration_date = yesterday
        cal.save()
        
        print(f"Updated next_calibration_date to: {cal.next_calibration_date}")
        print("This calibration will now be processed by the scheduler!")
    else:
        print("No problematic calibration found")

if __name__ == "__main__":
    fix_overdue_calibration()
