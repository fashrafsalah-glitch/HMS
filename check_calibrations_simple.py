#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
django.setup()

from maintenance.models import CalibrationRecord, ServiceRequest, WorkOrder
from datetime import date
from django.utils import timezone

def check_calibrations():
    today = date.today()
    print(f"Today: {today}")
    
    # Get all calibrations
    all_cals = CalibrationRecord.objects.all()
    print(f"Total calibrations: {all_cals.count()}")
    
    for cal in all_cals:
        device_name = str(cal.device.name).encode('ascii', 'replace').decode('ascii')
        print(f"- Device: {device_name}")
        print(f"  Next due: {cal.next_calibration_date}")
        print(f"  Status: {cal.status}")
        
        # Check if due today
        if cal.next_calibration_date == today:
            print(f"  *** DUE TODAY! ***")
            
            # Check for existing requests
            existing_sr = ServiceRequest.objects.filter(
                device=cal.device,
                request_type='calibration',
                status__in=['new', 'assigned', 'in_progress']
            )
            print(f"  Existing SRs: {existing_sr.count()}")
            
            existing_wo = WorkOrder.objects.filter(
                service_request__device=cal.device,
                wo_type='calibration',
                status__in=['new', 'assigned', 'in_progress']
            )
            print(f"  Existing WOs: {existing_wo.count()}")
            
        elif cal.next_calibration_date < today:
            days_overdue = (today - cal.next_calibration_date).days
            print(f"  *** OVERDUE by {days_overdue} days! ***")
        
        print()

if __name__ == "__main__":
    check_calibrations()
