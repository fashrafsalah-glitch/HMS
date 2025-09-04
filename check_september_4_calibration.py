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

def check_september_4_calibration():
    target_date = date(2025, 9, 4)
    today = date.today()
    print(f"Today: {today}")
    print(f"Looking for calibrations due on: {target_date}")
    
    # Find calibration due on September 4, 2025
    cal = CalibrationRecord.objects.filter(
        next_calibration_date=target_date
    ).first()
    
    if cal:
        device_name = str(cal.device.name).encode('ascii', 'replace').decode('ascii')
        print(f"\nFound calibration for device: {device_name}")
        print(f"Next due date: {cal.next_calibration_date}")
        print(f"Status: {cal.status}")
        print(f"Calibrated by: {cal.calibrated_by}")
        
        # Check if it should be processed (due today and status is due/overdue)
        should_be_processed = (cal.next_calibration_date <= today and 
                             cal.status in ['due', 'overdue'])
        print(f"Should be processed by scheduler: {should_be_processed}")
        
        if should_be_processed:
            print("*** THIS SHOULD CREATE SR/WO ***")
        else:
            print(f"*** NOT PROCESSED because:")
            if cal.next_calibration_date > today:
                print(f"    - Date is in future ({cal.next_calibration_date} > {today})")
            if cal.status not in ['due', 'overdue']:
                print(f"    - Status is '{cal.status}' (needs to be 'due' or 'overdue')")
        
        # Check for existing Service Requests
        existing_srs = ServiceRequest.objects.filter(
            device=cal.device,
            request_type='calibration'
        ).order_by('-created_at')
        
        print(f"\nExisting Service Requests for this device: {existing_srs.count()}")
        for sr in existing_srs:
            print(f"  - SR #{sr.id}: {sr.title}")
            print(f"    Status: {sr.status}, Created: {sr.created_at}")
        
        # Check for existing Work Orders
        existing_wos = WorkOrder.objects.filter(
            service_request__device=cal.device,
            wo_type='calibration'
        ).order_by('-created_at')
        
        print(f"\nExisting Work Orders for this device: {existing_wos.count()}")
        for wo in existing_wos:
            print(f"  - WO #{wo.wo_number}: {wo.title or 'No title'}")
            print(f"    Status: {wo.status}, Created: {wo.created_at}")
        
        # Check for open requests that would prevent new creation
        open_srs = ServiceRequest.objects.filter(
            device=cal.device,
            request_type='calibration',
            status__in=['new', 'assigned', 'in_progress']
        )
        
        if open_srs.exists():
            print(f"\n*** REASON FOR NO NEW SR/WO: {open_srs.count()} open calibration request(s) exist ***")
            for sr in open_srs:
                print(f"  - Open SR #{sr.id}: {sr.status}")
        else:
            print(f"\n*** NO OPEN REQUESTS - SCHEDULER SHOULD CREATE NEW ONES ***")
    
    else:
        print("No calibration found for September 4, 2025")
        
        # Check all calibrations to see what dates exist
        all_cals = CalibrationRecord.objects.all().order_by('next_calibration_date')
        print(f"\nAll calibrations in system ({all_cals.count()}):")
        for cal in all_cals:
            device_name = str(cal.device.name).encode('ascii', 'replace').decode('ascii')
            print(f"  - {device_name}: {cal.next_calibration_date} (Status: {cal.status})")

if __name__ == "__main__":
    check_september_4_calibration()
