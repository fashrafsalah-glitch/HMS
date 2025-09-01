#!/usr/bin/env python
"""
Test script for Room QR code integration
Tests QR generation, parsing, and operations for rooms
"""

import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from manager.models import Room, Department, Ward, Building, Floor
from maintenance.views import parse_qr_code
from maintenance.qr_operations import QROperationsManager
from superadmin.models import Hospital


def test_room_qr_integration():
    """Test complete room QR integration"""
    print("🏥 Testing Room QR Code Integration")
    print("=" * 50)
    
    # Get or create test data
    try:
        hospital = Hospital.objects.first()
        if not hospital:
            print("❌ No hospital found. Please create a hospital first.")
            return
            
        department = Department.objects.first()
        if not department:
            print("❌ No department found. Please create a department first.")
            return
            
        # Get or create building/floor/ward
        building, _ = Building.objects.get_or_create(
            name="Test Building",
            hospital=hospital,
            defaults={'location': 'Main Campus'}
        )
        
        floor, _ = Floor.objects.get_or_create(
            name="Ground Floor",
            building=building,
            defaults={'floor_number': 0}
        )
        
        ward, _ = Ward.objects.get_or_create(
            name="Test Ward",
            floor=floor,
            defaults={'description': 'Test ward for QR testing'}
        )
        
        # Create test room
        room, created = Room.objects.get_or_create(
            number="101",
            ward=ward,
            department=department,
            defaults={
                'room_type': 'patients_ROOM',
                'status': 'available',
                'capacity': 2
            }
        )
        
        if created:
            print(f"✅ Created test room: {room}")
        else:
            print(f"✅ Using existing room: {room}")
            
        # Test QR generation
        print("\n🔍 Testing QR Generation:")
        if not room.qr_token:
            room.generate_qr_code()
            room.save()
            print(f"✅ Generated QR token: {room.qr_token}")
        else:
            print(f"✅ Existing QR token: {room.qr_token}")
            
        # Test QR parsing
        print("\n🔍 Testing QR Parsing:")
        entity_type, entity_id, entity_data, error = parse_qr_code(room.qr_token)
        
        if error:
            print(f"❌ QR parsing failed: {error}")
        else:
            print(f"✅ Parsed entity type: {entity_type}")
            print(f"✅ Parsed entity ID: {entity_id}")
            print(f"✅ Entity data: {entity_data}")
            
        # Test operations manager
        print("\n🔍 Testing Operations Manager:")
        ops_manager = QROperationsManager()
        
        # Check if Room is properly imported
        if hasattr(ops_manager, 'Room'):
            print("✅ Room model imported in QROperationsManager")
            
            # Test room lookup
            try:
                test_room = ops_manager.Room.objects.get(pk=room.pk)
                print(f"✅ Room lookup successful: {test_room}")
            except Exception as e:
                print(f"❌ Room lookup failed: {e}")
        else:
            print("❌ Room model not imported in QROperationsManager")
            
        print("\n🔍 Testing Room Operations:")
        from maintenance.models import OperationDefinition
        
        room_operations = OperationDefinition.objects.filter(
            entity_types__contains=['room']
        )
        
        if room_operations.exists():
            print(f"✅ Found {room_operations.count()} room operations:")
            for op in room_operations:
                print(f"   - {op.name} ({op.name_ar})")
        else:
            print("❌ No room operations found")
            
        print("\n🎯 Room QR Integration Summary:")
        print(f"   Room ID: {room.pk}")
        print(f"   QR Token: {room.qr_token}")
        print(f"   QR Code: {'✅ Generated' if room.qr_code else '❌ Missing'}")
        print(f"   Parsing: {'✅ Working' if not error else '❌ Failed'}")
        print(f"   Operations: {'✅ Available' if room_operations.exists() else '❌ Missing'}")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_room_qr_integration()
