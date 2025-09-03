import os
import sys
import django
from datetime import datetime, timedelta

# Set UTF-8 encoding for console output
sys.stdout.reconfigure(encoding='utf-8')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from maintenance.models import DeviceDowntime, WorkOrder, ServiceRequest, Device
from django.utils import timezone

def test_downtime_end_times():
    """Test downtime end times accuracy"""
    
    print("=== Testing Downtime End Times ===\n")
    
    # البحث عن سجلات التوقف المنتهية حديثاً
    recent_ended = DeviceDowntime.objects.filter(
        end_time__isnull=False,
        end_time__gte=timezone.now() - timedelta(hours=24)
    ).order_by('-end_time')
    
    print(f"Ended downtimes in last 24 hours: {recent_ended.count()}")
    
    for dt in recent_ended:
        print(f"\n--- Downtime Record {dt.id} ---")
        print(f"Device: {dt.device.name}")
        print(f"Start Time: {dt.start_time}")
        print(f"End Time: {dt.end_time}")
        
        if dt.work_order:
            wo = dt.work_order
            print(f"Work Order: {wo.wo_number}")
            print(f"WO Status: {wo.status}")
            print(f"Completed At: {wo.completed_at}")
            print(f"Actual End: {wo.actual_end}")
            
            # Check if end time matches completion time
            if wo.completed_at and dt.end_time == wo.completed_at:
                print("✅ End time matches completed_at")
            elif wo.actual_end and dt.end_time == wo.actual_end:
                print("✅ End time matches actual_end")
            else:
                print("⚠️ End time doesn't match WO dates")
        
        # Check related service requests
        related_srs = ServiceRequest.objects.filter(
            device=dt.device,
            status__in=['resolved', 'closed', 'completed']
        ).order_by('-resolved_at', '-closed_at', '-updated_at')
        
        if related_srs.exists():
            latest_sr = related_srs.first()
            print(f"Latest SR: SR-{latest_sr.id}")
            print(f"Resolved At: {latest_sr.resolved_at}")
            print(f"Closed At: {latest_sr.closed_at}")
            
            # Check if end time matches resolution time
            if latest_sr.resolved_at and dt.end_time == latest_sr.resolved_at:
                print("✅ End time matches resolved_at")
            elif latest_sr.closed_at and dt.end_time == latest_sr.closed_at:
                print("✅ End time matches closed_at")
        
        # Calculate downtime duration
        if dt.start_time and dt.end_time:
            duration = dt.end_time - dt.start_time
            hours = duration.total_seconds() / 3600
            print(f"Duration: {hours:.2f} hours")
        
        print(f"Description: {dt.description[-200:] if dt.description else 'None'}")

if __name__ == "__main__":
    test_downtime_end_times()
