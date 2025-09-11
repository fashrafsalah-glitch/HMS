#!/usr/bin/env python
"""
Script to update all departments with QR codes
"""
import os
import sys
import django

# Add the project directory to the Python path
sys.path.append('E:\\HMS-main')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

# Setup Django
django.setup()

from manager.models import Department
import hashlib
import uuid
from django.utils import timezone

def update_departments_qr():
    """Update all departments with QR codes"""
    departments = Department.objects.all()
    updated_count = 0
    
    print(f"Found {departments.count()} departments")
    
    for dept in departments:
        # Generate unique QR code
        qr_data = f"department:{dept.pk}"
        qr_code = hashlib.sha256(f"{qr_data}:{dept.name}:{timezone.now()}:{uuid.uuid4().hex[:4]}".encode()).hexdigest()[:16]
        
        # Ensure uniqueness
        while Department.objects.filter(qr_code=qr_code).exists():
            qr_code = hashlib.sha256(f"{qr_data}:{dept.name}:{timezone.now()}:{uuid.uuid4().hex[:8]}".encode()).hexdigest()[:16]
        
        dept.qr_code = qr_code
        dept.save()
        updated_count += 1
        print(f"Updated department ID {dept.pk} with QR: {qr_code}")
    
    print(f"Successfully updated {updated_count} departments with QR codes")

if __name__ == "__main__":
    update_departments_qr()
