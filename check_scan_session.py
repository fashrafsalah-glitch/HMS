"""
Check scan session and history
"""
import os
import sys
import django

# Set UTF-8 encoding for Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from maintenance.models import ScanSession, ScanHistory, OperationDefinition, OperationExecution

# Get latest session
latest_session = ScanSession.objects.order_by('-created_at').first()
if latest_session:
    print(f"Latest Session: {latest_session.session_id}")
    print(f"Status: {latest_session.status}")
    print(f"Created: {latest_session.created_at}")
    
    # Get scan history for this session
    scans = ScanHistory.objects.filter(session=latest_session).order_by('scanned_at')
    print(f"\nScans in session: {scans.count()}")
    for scan in scans:
        print(f"  - {scan.entity_type}: {scan.entity_id} (ID: {scan.id})")
    
    # Check if operations were executed
    executions = OperationExecution.objects.filter(session=latest_session)
    print(f"\nOperation Executions: {executions.count()}")
    for exec in executions:
        print(f"  - {exec.operation.code}: {exec.status}")
    
    # Test matching manually
    from maintenance.qr_operations import QROperationsManager
    ops_manager = QROperationsManager()
    
    # Get scanned entities
    entities = ops_manager.get_scanned_entities(latest_session)
    print(f"\nScanned Entities: {len(entities)}")
    for entity in entities:
        print(f"  - {entity['type']}: {entity['id']}")
    
    # Try to match operation
    matched_op = ops_manager.match_operation(entities)
    if matched_op:
        print(f"\nMatched Operation: {matched_op.code} - {matched_op.name}")
        print(f"  Auto Execute: {matched_op.auto_execute}")
        print(f"  Requires Confirmation: {matched_op.requires_confirmation}")
    else:
        print("\nNo operation matched!")
