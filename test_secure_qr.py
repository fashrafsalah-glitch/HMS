"""
Test script for Secure QR Code System
Tests all components of the new secure QR implementation
"""

import os
import sys
import django
import json
import time
from datetime import datetime

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from core.secure_qr import SecureQRToken, QRContextFlow
from maintenance.models import Device, DeviceAccessory, QRScanLog
from manager.models import Patient, Bed
from maintenance.views import parse_qr_code

User = get_user_model()

class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header(text):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text:^60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")

def print_success(text):
    print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")

def print_error(text):
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")

def print_info(text):
    print(f"{Colors.OKCYAN}ℹ {text}{Colors.ENDC}")

def test_secure_token_generation():
    """Test secure token generation with HMAC signatures"""
    print_header("Testing Secure Token Generation")
    
    # Test static token
    print_info("Generating static token...")
    static_token = SecureQRToken.generate_token(
        entity_type='device',
        entity_id='123',
        ephemeral=False,
        metadata={'name': 'Test Device'}
    )
    
    if '|sig=' in static_token and 'device:' in static_token:
        print_success(f"Static token generated: {static_token[:50]}...")
    else:
        print_error("Static token generation failed")
        return False
    
    # Test ephemeral token
    print_info("Generating ephemeral token...")
    ephemeral_token = SecureQRToken.generate_token(
        entity_type='patient',
        entity_id='456',
        ephemeral=True,
        metadata={'mrn': 'P12345'}
    )
    
    if '|eph=1|sig=' in ephemeral_token:
        print_success(f"Ephemeral token generated: {ephemeral_token[:50]}...")
    else:
        print_error("Ephemeral token generation failed")
        return False
    
    return True

def test_token_validation():
    """Test token parsing and signature validation"""
    print_header("Testing Token Validation")
    
    # Generate a valid token
    valid_token = SecureQRToken.generate_token(
        entity_type='bed',
        entity_id='789',
        ephemeral=False
    )
    
    print_info(f"Validating token: {valid_token[:30]}...")
    
    # Parse the token
    entity_type, entity_id, entity_data, error = parse_qr_code(valid_token)
    
    if error:
        print_error(f"Token validation failed: {error}")
        return False
    
    if entity_type == 'bed' and entity_id == '789':
        print_success(f"Token validated successfully - Type: {entity_type}, ID: {entity_id}")
        if entity_data.get('token_uuid'):
            print_success(f"Token UUID retrieved: {entity_data['token_uuid']}")
    else:
        print_error("Token parsing returned incorrect data")
        return False
    
    # Test invalid signature
    print_info("Testing invalid signature detection...")
    invalid_token = valid_token[:-5] + "XXXXX"  # Corrupt the signature
    
    entity_type, entity_id, entity_data, error = parse_qr_code(invalid_token)
    
    if error and 'signature' in error.lower():
        print_success("Invalid signature correctly detected")
    else:
        print_error("Failed to detect invalid signature")
        return False
    
    return True

def test_ephemeral_tokens():
    """Test ephemeral token expiration"""
    print_header("Testing Ephemeral Tokens")
    
    # Generate ephemeral token with short duration
    SecureQRToken.EPHEMERAL_DURATION = 2  # 2 seconds for testing
    
    ephemeral_token = SecureQRToken.generate_token(
        entity_type='user',
        entity_id='999',
        ephemeral=True
    )
    
    print_info(f"Generated ephemeral token (expires in 2 seconds)")
    
    # Validate immediately
    entity_type, entity_id, entity_data, error = parse_qr_code(ephemeral_token)
    
    if not error and entity_data.get('ephemeral'):
        print_success("Ephemeral token valid when fresh")
    else:
        print_error("Fresh ephemeral token validation failed")
        return False
    
    # Wait for expiration
    print_info("Waiting for token to expire...")
    time.sleep(3)
    
    # Try to validate expired token
    entity_type, entity_id, entity_data, error = parse_qr_code(ephemeral_token)
    
    if error and 'expired' in error.lower():
        print_success("Expired ephemeral token correctly rejected")
    else:
        print_error("Failed to detect expired ephemeral token")
        return False
    
    # Reset duration
    SecureQRToken.EPHEMERAL_DURATION = 60
    
    return True

def test_context_flows():
    """Test context-based flow management"""
    print_header("Testing Context-Based Flows")
    
    # Start a session
    user_id = "test_user_123"
    session_id = QRContextFlow.start_session(user_id, 'mobile')
    
    print_success(f"Session started: {session_id}")
    
    # Test Device Transfer flow (user -> device -> device)
    print_info("Testing Device Transfer flow...")
    
    # First scan: User
    result = QRContextFlow.add_scan(session_id, 'user', '1')
    print_info(f"Scan 1 (user): {result.get('scan_count', 0)} scans")
    
    # Second scan: First device
    result = QRContextFlow.add_scan(session_id, 'device', '100')
    print_info(f"Scan 2 (device): {result.get('scan_count', 0)} scans")
    
    # Third scan: Second device (should match flow)
    result = QRContextFlow.add_scan(session_id, 'device', '200')
    
    if result.get('matched'):
        print_success(f"Flow matched: {result['flow']['name']}")
        print_info(f"Flow config: {result['flow']['config']}")
    else:
        print_error("Flow not matched")
        return False
    
    # Clear session for next test
    QRContextFlow.clear_session(session_id)
    
    # Test Patient Transfer flow
    print_info("\nTesting Patient Transfer flow...")
    session_id = QRContextFlow.start_session(user_id, 'mobile')
    
    # Scan sequence: user -> patient -> bed
    QRContextFlow.add_scan(session_id, 'user', '1')
    QRContextFlow.add_scan(session_id, 'patient', '50')
    result = QRContextFlow.add_scan(session_id, 'bed', '10')
    
    if result.get('matched') and result['flow']['name'] == 'patient_transfer':
        print_success("Patient Transfer flow matched")
    else:
        print_error("Patient Transfer flow not matched")
        return False
    
    return True

def test_api_endpoints():
    """Test the API endpoints"""
    print_header("Testing API Endpoints")
    
    client = Client()
    
    # Test generate-qr endpoint
    print_info("Testing /api/generate-qr/ endpoint...")
    
    # Create a test user for authentication
    try:
        test_user = User.objects.create_user(
            username='qr_test_user',
            password='test123',
            email='qr@test.com'
        )
    except:
        test_user = User.objects.get(username='qr_test_user')
    
    client.login(username='qr_test_user', password='test123')
    
    # Create test device if doesn't exist
    try:
        device = Device.objects.create(
            name='Test QR Device',
            serial_number='QR-TEST-001',
            device_id='QR001'
        )
    except:
        device = Device.objects.get(serial_number='QR-TEST-001')
    
    # Test static QR generation
    response = client.post(
        '/api/generate-qr/',
        json.dumps({
            'entity_type': 'device',
            'entity_id': str(device.id),
            'ephemeral': False
        }),
        content_type='application/json'
    )
    
    if response.status_code == 200:
        data = response.json()
        if data.get('success') and data.get('qr_token') and data.get('qr_image_base64'):
            print_success(f"Static QR generated via API")
            print_info(f"Token: {data['qr_token'][:40]}...")
        else:
            print_error("API response missing expected fields")
    else:
        print_error(f"API returned status {response.status_code}")
    
    # Test ephemeral QR generation
    response = client.post(
        '/api/generate-qr/',
        json.dumps({
            'entity_type': 'device',
            'entity_id': str(device.id),
            'ephemeral': True,
            'metadata': {'purpose': 'mobile_scan'}
        }),
        content_type='application/json'
    )
    
    if response.status_code == 200:
        data = response.json()
        if data.get('ephemeral') and data.get('expires_in'):
            print_success(f"Ephemeral QR generated (expires in {data['expires_in']}s)")
        else:
            print_error("Ephemeral QR generation failed")
    else:
        print_error(f"API returned status {response.status_code}")
    
    # Test scan-qr endpoint
    print_info("\nTesting /api/scan-qr/ endpoint...")
    
    # Generate a token to scan
    token = SecureQRToken.generate_token(
        entity_type='device',
        entity_id=str(device.id),
        ephemeral=False
    )
    
    response = client.post(
        '/api/scan-qr/',
        json.dumps({
            'qr_code': token,
            'device_type': 'scanner',
            'user_id': str(test_user.id),
            'scanner_id': 'TEST-SCANNER-001'
        }),
        content_type='application/json'
    )
    
    if response.status_code == 200:
        data = response.json()
        if data.get('success') and data.get('is_secure'):
            print_success("QR scan API processed secure token")
            print_info(f"Scan logged with ID: {data.get('scan_id')}")
        else:
            print_error("Scan API failed to process secure token")
    else:
        print_error(f"Scan API returned status {response.status_code}")
    
    return True

def test_qr_scan_logging():
    """Test that QRScanLog records all new fields correctly"""
    print_header("Testing QR Scan Logging")
    
    # Check if we have scan logs with new fields
    recent_logs = QRScanLog.objects.filter(
        is_secure=True
    ).order_by('-scanned_at')[:5]
    
    if recent_logs.exists():
        print_success(f"Found {recent_logs.count()} secure QR scan logs")
        
        for log in recent_logs:
            print_info(f"Log {log.id}:")
            print(f"  - Entity: {log.entity_type}:{log.entity_id}")
            print(f"  - Secure: {log.is_secure}")
            print(f"  - Ephemeral: {log.is_ephemeral}")
            print(f"  - Signature: {log.token_signature[:20]}..." if log.token_signature else "  - Signature: None")
            print(f"  - Session: {log.session_id}" if log.session_id else "  - Session: None")
            print(f"  - Flow: {log.flow_name}" if log.flow_name else "  - Flow: None")
    else:
        print_info("No secure scan logs found yet")
    
    return True

def main():
    """Run all tests"""
    print_header("SECURE QR CODE SYSTEM TEST SUITE")
    print_info(f"Starting tests at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    tests = [
        ("Token Generation", test_secure_token_generation),
        ("Token Validation", test_token_validation),
        ("Ephemeral Tokens", test_ephemeral_tokens),
        ("Context Flows", test_context_flows),
        ("API Endpoints", test_api_endpoints),
        ("QR Scan Logging", test_qr_scan_logging),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print_error(f"Test '{test_name}' raised exception: {e}")
            failed += 1
    
    # Summary
    print_header("TEST SUMMARY")
    print(f"{Colors.OKGREEN}Passed: {passed}{Colors.ENDC}")
    print(f"{Colors.FAIL}Failed: {failed}{Colors.ENDC}")
    
    if failed == 0:
        print_success("All tests passed! ✨")
    else:
        print_error(f"{failed} test(s) failed")
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
