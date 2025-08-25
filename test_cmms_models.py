#!/usr/bin/env python
"""
Test script to verify CMMS models consolidation
"""
import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

def test_cmms_models():
    """Test importing and basic functionality of CMMS models"""
    try:
        # Test importing all consolidated models
        from maintenance.models import (
            ServiceRequest, WorkOrder, JobPlan, JobPlanStep,
            PreventiveMaintenanceSchedule, SLADefinition,
            SystemNotification, EmailLog, NotificationPreference,
            NotificationTemplate, NotificationQueue,
            Supplier, SparePart
        )
        print("✓ All CMMS models imported successfully")
        
        # Test model meta information
        print(f"✓ ServiceRequest model: {ServiceRequest._meta.verbose_name}")
        print(f"✓ WorkOrder model: {WorkOrder._meta.verbose_name}")
        print(f"✓ JobPlan model: {JobPlan._meta.verbose_name}")
        print(f"✓ PreventiveMaintenanceSchedule model: {PreventiveMaintenanceSchedule._meta.verbose_name}")
        print(f"✓ SLADefinition model: {SLADefinition._meta.verbose_name}")
        print(f"✓ SystemNotification model: {SystemNotification._meta.verbose_name}")
        print(f"✓ Supplier model: {Supplier._meta.verbose_name}")
        print(f"✓ SparePart model: {SparePart._meta.verbose_name}")
        
        # Test model relationships
        print(f"✓ ServiceRequest has {len(ServiceRequest._meta.get_fields())} fields")
        print(f"✓ WorkOrder has {len(WorkOrder._meta.get_fields())} fields")
        
        # Test choice fields
        sr_status_choices = dict(ServiceRequest._meta.get_field('status').choices)
        wo_status_choices = dict(WorkOrder._meta.get_field('status').choices)
        
        print(f"✓ ServiceRequest status choices: {len(sr_status_choices)} options")
        print(f"✓ WorkOrder status choices: {len(wo_status_choices)} options")
        
        return True
        
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def test_views_imports():
    """Test importing views that use the consolidated models"""
    try:
        from maintenance import views_cmms
        from maintenance import views_spare_parts
        from maintenance import views_dashboard
        print("✓ All CMMS views imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Views import error: {e}")
        return False
    except Exception as e:
        print(f"✗ Views error: {e}")
        return False

def test_admin_imports():
    """Test importing admin that uses the consolidated models"""
    try:
        from maintenance import admin
        print("✓ Admin module imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Admin import error: {e}")
        return False
    except Exception as e:
        print(f"✗ Admin error: {e}")
        return False

if __name__ == "__main__":
    print("Testing CMMS Models Consolidation...")
    print("=" * 50)
    
    success = True
    
    # Test models
    print("\n1. Testing Model Imports:")
    success &= test_cmms_models()
    
    # Test views
    print("\n2. Testing Views Imports:")
    success &= test_views_imports()
    
    # Test admin
    print("\n3. Testing Admin Imports:")
    success &= test_admin_imports()
    
    print("\n" + "=" * 50)
    if success:
        print("✓ All tests passed! CMMS models consolidation successful.")
    else:
        print("✗ Some tests failed. Please check the errors above.")
    
    print("=" * 50)
