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

def check_created_requests():
    today = date.today()
    print(f"Today: {today}")
    
    # Get the overdue calibration
    overdue_cal = CalibrationRecord.objects.filter(
        next_calibration_date__lt=today,
        status='overdue'
    ).first()
    
    if overdue_cal:
        device_name = str(overdue_cal.device.name).encode('ascii', 'replace').decode('ascii')
        print(f"Found overdue calibration for device: {device_name}")
        print(f"Due date: {overdue_cal.next_calibration_date}")
        print(f"Status: {overdue_cal.status}")
        
        # Check for Service Requests
        calibration_srs = ServiceRequest.objects.filter(
            device=overdue_cal.device,
            request_type='calibration'
        ).order_by('-created_at')
        
        print(f"\nService Requests for this device (calibration type): {calibration_srs.count()}")
        for sr in calibration_srs:
            print(f"  - SR #{sr.id}: {sr.title}")
            print(f"    Status: {sr.status}")
            print(f"    Created: {sr.created_at}")
            print(f"    Auto-generated: {getattr(sr, 'is_auto_generated', 'N/A')}")
        
        # Check for Work Orders
        calibration_wos = WorkOrder.objects.filter(
            service_request__device=overdue_cal.device,
            wo_type='calibration'
        ).order_by('-created_at')
        
        print(f"\nWork Orders for this device (calibration type): {calibration_wos.count()}")
        for wo in calibration_wos:
            print(f"  - WO #{wo.wo_number}: {wo.title or 'No title'}")
            print(f"    Status: {wo.status}")
            print(f"    Created: {wo.created_at}")
            print(f"    Service Request: #{wo.service_request.id if wo.service_request else 'None'}")
        
        # Check recent activity (last 5 minutes)
        recent_time = timezone.now() - timedelta(minutes=5)
        recent_srs = ServiceRequest.objects.filter(
            device=overdue_cal.device,
            request_type='calibration',
            created_at__gte=recent_time
        )
        
        recent_wos = WorkOrder.objects.filter(
            service_request__device=overdue_cal.device,
            wo_type='calibration',
            created_at__gte=recent_time
        )
        
        print(f"\nRecent activity (last 5 minutes):")
        print(f"  New SRs: {recent_srs.count()}")
        print(f"  New WOs: {recent_wos.count()}")
        
        if recent_srs.exists() or recent_wos.exists():
            print("  SUCCESS: Scheduler created requests!")
        else:
            print("  No recent activity - scheduler may not have run yet")
    
    else:
        print("No overdue calibrations found")

if __name__ == "__main__":
    check_created_requests()
