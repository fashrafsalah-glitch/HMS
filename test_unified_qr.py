"""
Test script for Unified QR Code System
Tests URL-based QR codes for both scanners and mobile devices
"""

import os
import sys
import django
import json
from urllib.parse import urlparse, parse_qs

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from django.conf import settings
from core.secure_qr import SecureQRToken
from maintenance.models import Device
from maintenance.views import parse_qr_code

User = get_user_model()

def test_url_qr_generation():
    """Test QR code generation with full URLs"""
    print("🔗 Testing URL-based QR Generation...")
    
    # Create test device
    try:
        device = Device.objects.create(
            name='Test URL Device',
            serial_number='URL-TEST-001',
            device_id='URL001'
        )
    except:
        device = Device.objects.get(serial_number='URL-TEST-001')
    
    # Generate QR code (should now contain full URL)
    device.generate_qr_code()
    
    # Check if qr_token contains secure token
    if device.qr_token and '|sig=' in device.qr_token:
        print(f"✓ Secure token generated: {device.qr_token[:40]}...")
        
        # Generate URL
        qr_url = device.generate_qr_url(device.qr_token)
        expected_domain = settings.QR_DOMAIN
        
        if qr_url.startswith(expected_domain):
            print(f"✓ QR URL generated: {qr_url[:60]}...")
            return qr_url, device.qr_token
        else:
            print(f"✗ QR URL doesn't use correct domain: {qr_url}")
            return None, None
    else:
        print(f"✗ Secure token not generated properly")
        return None, None

def test_url_parsing():
    """Test parsing QR codes from URLs vs raw tokens"""
    print("\n📱 Testing URL vs Raw Token Parsing...")
    
    qr_url, raw_token = test_url_qr_generation()
    if not qr_url or not raw_token:
        return False
    
    # Test 1: Parse from full URL (mobile device scenario)
    print("Testing URL parsing (mobile device)...")
    entity_type, entity_id, entity_data, error = parse_qr_code(qr_url)
    
    if error:
        print(f"✗ URL parsing failed: {error}")
        return False
    
    if entity_type == 'device' and entity_data.get('token_uuid'):
        print(f"✓ URL parsed successfully - Type: {entity_type}, ID: {entity_id}")
    else:
        print(f"✗ URL parsing returned incorrect data")
        return False
    
    # Test 2: Parse from raw token (scanner device scenario)
    print("Testing raw token parsing (scanner device)...")
    entity_type2, entity_id2, entity_data2, error2 = parse_qr_code(raw_token)
    
    if error2:
        print(f"✗ Raw token parsing failed: {error2}")
        return False
    
    if entity_type2 == entity_type and entity_id2 == entity_id:
        print(f"✓ Raw token parsed successfully - Same result as URL")
        return True
    else:
        print(f"✗ Raw token parsing returned different data")
        return False

def test_api_with_urls():
    """Test API endpoints with URL-based QR codes"""
    print("\n🌐 Testing API with URL-based QR Codes...")
    
    client = Client()
    
    # Create test user
    try:
        test_user = User.objects.create_user(
            username='url_test_user',
            password='test123',
            email='url@test.com'
        )
    except:
        test_user = User.objects.get(username='url_test_user')
    
    client.login(username='url_test_user', password='test123')
    
    # Test generate-qr API
    device = Device.objects.first()
    if not device:
        print("✗ No device found for testing")
        return False
    
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
        qr_url = data.get('qr_url')
        
        if qr_url and qr_url.startswith(settings.QR_DOMAIN):
            print(f"✓ API generated QR URL: {qr_url[:50]}...")
            
            # Test scanning the generated URL
            scan_response = client.post(
                '/api/scan-qr/',
                json.dumps({
                    'qr_code': qr_url,  # Use full URL
                    'device_type': 'mobile',
                    'user_id': str(test_user.id)
                }),
                content_type='application/json'
            )
            
            if scan_response.status_code == 200:
                scan_data = scan_response.json()
                if scan_data.get('success') and scan_data.get('is_secure'):
                    print("✓ URL-based QR scan successful")
                    return True
                else:
                    print(f"✗ URL scan failed: {scan_data}")
            else:
                print(f"✗ Scan API error: {scan_response.status_code}")
        else:
            print(f"✗ Invalid QR URL generated: {qr_url}")
    else:
        print(f"✗ Generate API error: {response.status_code}")
    
    return False

def test_scanner_vs_mobile():
    """Test different behavior for scanner vs mobile devices"""
    print("\n📱📟 Testing Scanner vs Mobile Device Handling...")
    
    client = Client()
    test_user = User.objects.first()
    
    if not test_user:
        print("✗ No user found for testing")
        return False
    
    # Generate a QR URL
    device = Device.objects.first()
    if not device:
        print("✗ No device found for testing")
        return False
    
    token = device.generate_qr_token()
    qr_url = device.generate_qr_url(token)
    
    # Test 1: Scanner device (should get basic info)
    print("Testing scanner device response...")
    scanner_response = client.post(
        '/api/scan-qr/',
        json.dumps({
            'qr_code': qr_url,
            'device_type': 'scanner',
            'scanner_id': 'TEST-SCANNER-001'
        }),
        content_type='application/json'
    )
    
    if scanner_response.status_code == 200:
        scanner_data = scanner_response.json()
        if scanner_data.get('logged') and not scanner_data.get('flow_matched'):
            print("✓ Scanner device: Basic logging response")
        else:
            print(f"✗ Unexpected scanner response: {scanner_data}")
            return False
    else:
        print(f"✗ Scanner API error: {scanner_response.status_code}")
        return False
    
    # Test 2: Mobile device (should handle context flows)
    print("Testing mobile device response...")
    mobile_response = client.post(
        '/api/scan-qr/',
        json.dumps({
            'qr_code': qr_url,
            'device_type': 'mobile',
            'user_id': str(test_user.id)
        }),
        content_type='application/json'
    )
    
    if mobile_response.status_code == 200:
        mobile_data = mobile_response.json()
        if mobile_data.get('session_id'):
            print("✓ Mobile device: Session-based response with context flow")
            return True
        else:
            print(f"✗ Mobile response missing session: {mobile_data}")
    else:
        print(f"✗ Mobile API error: {mobile_response.status_code}")
    
    return False

def main():
    """Run all unified QR system tests"""
    print("🔄 UNIFIED QR CODE SYSTEM TEST")
    print(f"Domain: {settings.QR_DOMAIN}")
    print("=" * 50)
    
    tests = [
        ("URL QR Generation", test_url_qr_generation),
        ("URL vs Raw Parsing", test_url_parsing),
        ("API with URLs", test_api_with_urls),
        ("Scanner vs Mobile", test_scanner_vs_mobile),
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
            print(f"✗ Test '{test_name}' error: {e}")
            failed += 1
    
    print("\n" + "=" * 50)
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    
    if failed == 0:
        print("🎉 All tests passed! Unified QR system working correctly.")
        print("\n📋 System Summary:")
        print("• Scanners: Read QR → Extract token → Process")
        print("• Mobile: Scan QR → Open URL → Auto-process")
        print("• Unified domain-based approach implemented")
    else:
        print(f"⚠️  {failed} test(s) failed")
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
