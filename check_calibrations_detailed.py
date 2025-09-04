#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
django.setup()

from maintenance.models import CalibrationRecord, ServiceRequest, WorkOrder
from datetime import date, datetime, timedelta
from django.utils import timezone

def check_calibrations_detailed():
    today = date.today()
    print(f"Today: {today}")
    
    # Get all calibrations
    all_cals = CalibrationRecord.objects.all()
    print(f"Total calibrations: {all_cals.count()}")
    
    for cal in all_cals:
        device_name = str(cal.device.name).encode('ascii', 'replace').decode('ascii')
        print(f"\n- Device: {device_name}")
        print(f"  Next due: {cal.next_calibration_date}")
        print(f"  Status: {cal.status}")
        
        # Check if it should be processed by scheduler
        if cal.next_calibration_date <= today and cal.status in ['due', 'overdue']:
            print(f"  *** SHOULD BE PROCESSED BY SCHEDULER ***")
            
            # Check for existing requests
            existing_sr = ServiceRequest.objects.filter(
                device=cal.device,
                request_type='calibration',
                status__in=['new', 'assigned', 'in_progress']
            )
            print(f"  Existing open SRs: {existing_sr.count()}")
            
            if existing_sr.exists():
                for sr in existing_sr:
                    print(f"    - SR #{sr.id}: {sr.title} (Status: {sr.status})")
            
            # Check all calibration SRs for this device
            all_cal_srs = ServiceRequest.objects.filter(
                device=cal.device,
                request_type='calibration'
            ).order_by('-created_at')
            
            print(f"  All calibration SRs: {all_cal_srs.count()}")
            for sr in all_cal_srs[:3]:  # Show last 3
                print(f"    - SR #{sr.id}: {sr.title} (Status: {sr.status}, Created: {sr.created_at})")
        
        elif cal.next_calibration_date < today:
            days_overdue = (today - cal.next_calibration_date).days
            print(f"  *** OVERDUE by {days_overdue} days but status is {cal.status} ***")
        
        elif cal.next_calibration_date > today:
            days_future = (cal.next_calibration_date - today).days
            print(f"  Future calibration in {days_future} days")

if __name__ == "__main__":
    check_calibrations_detailed()
