"""
Test script for new scan session flow
Tests:
1. Start new session with user scan
2. Add device scan to same session  
3. Add patient scan to complete sequence
4. Verify DEVICE_USAGE operation execution
"""
import os
import sys
import django
import json

# Set UTF-8 encoding for Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from maintenance.models import ScanSession, ScanHistory, OperationDefinition, OperationExecution
from maintenance.qr_operations import QROperationsManager
from django.contrib.auth import get_user_model

User = get_user_model()

def test_scan_session_flow():
    print("=" * 80)
    print("TESTING SCAN SESSION FLOW")
    print("=" * 80)
    
    # Get test user
    test_user = User.objects.filter(is_superuser=True).first()
    if not test_user:
        test_user = User.objects.first()
    print(f"Test user: {test_user.username} (ID: {test_user.id})")
    
    # Clean up old test sessions
    ScanSession.objects.filter(user=test_user, status='active').update(status='cancelled')
    
    # Test 1: Create new session with user scan
    print("\n[TEST 1] Creating new session with user scan...")
    session = ScanSession.objects.create(
        user=test_user,
        status='active'
    )
    print(f"✓ Created session: {session.session_id}")
    
    # Record user scan
    user_data = {
        'username': test_user.username,
        'role': getattr(test_user, 'role', 'staff'),
        'full_name': str(test_user),
        'user_id': test_user.id
    }
    
    user_scan = ScanHistory.objects.create(
        session=session,
        scanned_code='user:test123',
        entity_type='user',
        entity_id=test_user.id,
        entity_data=json.dumps(user_data),
        is_valid=True
    )
    print(f"✓ Created user scan history: {user_scan.id}")
    
    # Verify user scan exists
    scans = ScanHistory.objects.filter(session=session).order_by('scanned_at')
    print(f"✓ Session has {scans.count()} scan(s)")
    for scan in scans:
        print(f"  - {scan.entity_type}: {scan.entity_id}")
    
    # Test 2: Add device scan
    print("\n[TEST 2] Adding device scan...")
    from maintenance.models import Device
    test_device = Device.objects.filter(status='available').first()
    if not test_device:
        test_device = Device.objects.first()
    
    if test_device:
        device_data = {
            'name': test_device.name,
            'model': test_device.model,
            'serial': test_device.serial_number
        }
        
        device_scan = ScanHistory.objects.create(
            session=session,
            scanned_code=f'device:{test_device.id}',
            entity_type='device',
            entity_id=test_device.id,
            entity_data=json.dumps(device_data),
            is_valid=True
        )
        print(f"✓ Created device scan history: {device_scan.id}")
        print(f"  Device: {test_device.name} (ID: {test_device.id})")
    
    # Test 3: Add patient scan  
    print("\n[TEST 3] Adding patient scan...")
    from manager.models import Patient
    test_patient = Patient.objects.first()
    
    if test_patient:
        patient_data = {
            'name': f"{test_patient.first_name} {test_patient.last_name}",
            'mrn': test_patient.medical_file_number
        }
        
        patient_scan = ScanHistory.objects.create(
            session=session,
            scanned_code=f'patient:{test_patient.id}',
            entity_type='patient',
            entity_id=test_patient.id,
            entity_data=json.dumps(patient_data),
            is_valid=True
        )
        print(f"✓ Created patient scan history: {patient_scan.id}")
        print(f"  Patient: {patient_data['name']} (ID: {test_patient.id})")
    
    # Verify full sequence
    print("\n[VERIFICATION] Checking scan sequence...")
    scans = ScanHistory.objects.filter(session=session).order_by('scanned_at')
    print(f"Session has {scans.count()} scans:")
    for i, scan in enumerate(scans):
        print(f"  {i+1}. {scan.entity_type}: {scan.entity_id}")
    
    # Test 4: Check operation matching
    print("\n[TEST 4] Testing operation matching...")
    ops_manager = QROperationsManager()
    
    # Get scanned entities
    entities = ops_manager.get_scanned_entities(session)
    print(f"Retrieved {len(entities)} entities:")
    for entity in entities:
        print(f"  - {entity['type']}: {entity['id']}")
    
    # Try to match operation
    matched_op = ops_manager.match_operation(entities)
    if matched_op:
        print(f"✓ Matched operation: {matched_op.code} - {matched_op.name}")
        print(f"  Auto Execute: {matched_op.auto_execute}")
        print(f"  Requires Confirmation: {matched_op.requires_confirmation}")
        
        # Test execution
        if test_device and test_patient:
            print("\n[TEST 5] Testing operation execution...")
            success, execution, message = ops_manager.execute_operation(
                matched_op,
                session,
                test_user,
                entities
            )
            
            if success:
                print(f"✓ Operation executed successfully!")
                print(f"  Execution ID: {execution.id}")
                print(f"  Status: {execution.status}")
                print(f"  Message: {message}")
                
                # Check if device status changed
                test_device.refresh_from_db()
                print(f"\n[RESULT] Device status: {test_device.status}")
                if test_device.current_patient:
                    print(f"  Linked to patient: {test_device.current_patient}")
            else:
                print(f"✗ Operation failed: {message}")
    else:
        print("✗ No operation matched!")
        
        # Check why no match
        print("\n[DEBUG] Checking available operations...")
        ops = OperationDefinition.objects.filter(is_active=True)
        for op in ops:
            steps = op.steps.order_by('order')
            print(f"  {op.code}: {steps.count()} steps")
            for step in steps:
                print(f"    - {step.order}: {step.entity_type} (required: {step.is_required})")
    
    print("\n" + "=" * 80)
    print("TEST COMPLETED")
    print("=" * 80)

if __name__ == "__main__":
    test_scan_session_flow()
