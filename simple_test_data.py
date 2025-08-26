#!/usr/bin/env python
"""
Simple CMMS Test Data Generator
"""
import os
import sys
import django
from datetime import datetime, timedelta, date
from decimal import Decimal
import random

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth import get_user_model
from maintenance.models import *
from manager.models import Department, Room

User = get_user_model()

def create_test_data():
    print("🏥 Starting CMMS Test Data Generation...")
    
    # Create companies
    print("🏢 Creating Companies...")
    companies_data = [
        "Philips Healthcare", "GE Healthcare", "Siemens Healthineers", 
        "Medtronic", "شركة الأجهزة الطبية المتقدمة"
    ]
    
    companies = []
    for name in companies_data:
        company, created = Company.objects.get_or_create(name=name)
        companies.append(company)
        if created:
            print(f"   ✓ {company.name}")
    
    # Create device types
    print("🔧 Creating Device Types...")
    device_types_data = [
        "أجهزة التنفس الصناعي", "أجهزة مراقبة المرضى", 
        "أجهزة الأشعة السينية", "أجهزة المختبرات"
    ]
    
    device_types = []
    for type_name in device_types_data:
        device_type, created = DeviceType.objects.get_or_create(name=type_name)
        device_types.append(device_type)
        if created:
            print(f"   ✓ {device_type.name}")
    
    # Create device usages
    usage_data = ["تشخيص", "علاج", "مراقبة", "جراحة"]
    usages = []
    for usage_name in usage_data:
        usage, created = DeviceUsage.objects.get_or_create(name=usage_name)
        usages.append(usage)
    
    # Create categories
    print("📂 Creating Categories...")
    categories = []
    categories_data = [
        {"name": "أجهزة القلب والأوعية الدموية", "subcategories": ["أجهزة تخطيط القلب"]},
        {"name": "أجهزة التنفس والرئة", "subcategories": ["أجهزة التنفس الصناعي"]},
        {"name": "أجهزة التصوير الطبي", "subcategories": ["أجهزة الأشعة السينية"]}
    ]
    
    for cat_data in categories_data:
        category, created = DeviceCategory.objects.get_or_create(name=cat_data["name"])
        categories.append(category)
        if created:
            print(f"   ✓ {category.name}")
        
        for subcat_name in cat_data["subcategories"]:
            subcategory, created = DeviceSubCategory.objects.get_or_create(
                name=subcat_name, category=category
            )
            if created:
                print(f"     ↳ {subcategory.name}")
    
    # Create users
    print("👥 Creating Users...")
    users_data = [
        {"username": "tech_biomedical", "first_name": "سعد", "last_name": "الفني"},
        {"username": "tech_radiology", "first_name": "مريم", "last_name": "التقنية"},
        {"username": "supervisor_maintenance", "first_name": "علي", "last_name": "المشرف"},
        {"username": "nurse_icu", "first_name": "فاطمة", "last_name": "الممرضة"}
    ]
    
    users = []
    for user_data in users_data:
        user, created = User.objects.get_or_create(
            username=user_data["username"],
            defaults={
                'email': f"{user_data['username']}@hospital.com",
                'first_name': user_data["first_name"],
                'last_name': user_data["last_name"]
            }
        )
        if created:
            user.set_password('password123')
            user.save()
            print(f"   ✓ {user.get_full_name()} ({user.username})")
        users.append(user)
    
    # Create devices
    print("🏥 Creating Medical Devices...")
    departments = list(Department.objects.all())
    rooms = list(Room.objects.all())
    
    if departments and rooms:
        device_templates = [
            {"name": "جهاز التنفس الصناعي فيليبس", "model": "V60 Ventilator", "count": 8},
            {"name": "جهاز مراقبة المريض", "model": "IntelliVue MX800", "count": 12},
            {"name": "جهاز الأشعة السينية المحمول", "model": "AMX 4 Plus", "count": 5},
            {"name": "جهاز تحليل الدم", "model": "CELL-DYN Ruby", "count": 3}
        ]
        
        devices = []
        for template in device_templates:
            category = random.choice(categories)
            device_type = random.choice(device_types)
            usage = random.choice(usages)
            manufacturer = random.choice(companies)
            
            for i in range(template["count"]):
                department = random.choice(departments)
                dept_rooms = [r for r in rooms if r.department == department]
                room = random.choice(dept_rooms) if dept_rooms else random.choice(rooms)
                
                serial_number = f"{template['model'][:6].upper().replace(' ', '')}{random.randint(100000, 999999)}"
                production_date = date.today() - timedelta(days=random.randint(365, 3650))
                
                device = Device.objects.create(
                    name=f"{template['name']} #{i+1:02d}",
                    category=category,
                    brief_description=f"جهاز طبي متقدم من نوع {template['name']}",
                    manufacturer=template["model"].split()[0],
                    model=template["model"],
                    serial_number=serial_number,
                    production_date=production_date,
                    department=department,
                    room=room,
                    manufacture_company=manufacturer,
                    device_type=device_type,
                    device_usage=usage,
                    status=random.choice(['working', 'needs_maintenance', 'needs_check']),
                    clean_status=random.choice(['clean', 'needs_cleaning', 'unknown']),
                    sterilization_status=random.choice(['sterilized', 'needs_sterilization', 'unknown']),
                    availability=True
                )
                devices.append(device)
                
                if (i + 1) % 5 == 0:
                    print(f"   ✓ Created {i + 1} devices for {template['name']}")
        
        print(f"✅ Created {len(devices)} medical devices")
        
        # Create suppliers
        print("📦 Creating Suppliers...")
        suppliers_data = [
            {
                "name": "شركة قطع الغيار الطبية المتخصصة",
                "code": "MPS001",
                "contact_person": "أحمد محمد",
                "phone": "+966501234567",
                "email": "ahmed@medicalparts.com"
            },
            {
                "name": "مؤسسة التوريدات الطبية الشاملة",
                "code": "CMS002",
                "contact_person": "فاطمة علي", 
                "phone": "+966507654321",
                "email": "fatima@comprehensive.com"
            }
        ]
        
        suppliers = []
        for supplier_data in suppliers_data:
            supplier, created = Supplier.objects.get_or_create(
                code=supplier_data["code"],
                defaults=supplier_data
            )
            suppliers.append(supplier)
            if created:
                print(f"   ✓ {supplier.name}")
        
        # Create spare parts
        print("🔧 Creating Spare Parts...")
        spare_parts_data = [
            {
                "name": "فلتر هواء للتنفس الصناعي",
                "part_number": "VENT-FILTER-001",
                "description": "فلتر هواء عالي الكفاءة لأجهزة التنفس الصناعي",
                "unit_cost": Decimal("150.00"),
                "current_stock": 50,
                "minimum_stock": 10
            },
            {
                "name": "كابل تخطيط القلب",
                "part_number": "MON-ECG-004",
                "description": "كابل توصيل لتخطيط القلب",
                "unit_cost": Decimal("200.00"),
                "current_stock": 25,
                "minimum_stock": 5
            },
            {
                "name": "أنبوب الأشعة السينية",
                "part_number": "XRAY-TUBE-007",
                "description": "أنبوب توليد الأشعة السينية",
                "unit_cost": Decimal("5000.00"),
                "current_stock": 3,
                "minimum_stock": 1
            }
        ]
        
        spare_parts = []
        for part_data in spare_parts_data:
            spare_part, created = SparePart.objects.get_or_create(
                part_number=part_data["part_number"],
                defaults={
                    **part_data,
                    'supplier': random.choice(suppliers)
                }
            )
            if created:
                spare_part.compatible_devices.set(random.sample(devices, min(3, len(devices))))
                print(f"   ✓ {spare_part.name}")
            spare_parts.append(spare_part)
        
        # Create service requests
        print("📋 Creating Service Requests...")
        for i in range(15):
            device = random.choice(devices)
            reporter = random.choice(users)
            
            service_request, created = ServiceRequest.objects.get_or_create(
                request_number=f"SR{datetime.now().year}{i+1:04d}",
                defaults={
                    'title': f"بلاغ صيانة للجهاز {device.name}",
                    'description': f"يحتاج الجهاز إلى صيانة وفحص شامل",
                    'device': device,
                    'requested_by': reporter,
                    'request_type': random.choice(['breakdown', 'preventive', 'calibration', 'upgrade']),
                    'priority': random.choice(['low', 'medium', 'high', 'critical']),
                    'status': random.choice(['new', 'assigned', 'in_progress', 'completed']),
                    'created_at': datetime.now() - timedelta(days=random.randint(1, 30))
                }
            )
            
            if created and i % 5 == 0:
                print(f"   ✓ Created {i + 1} service requests")
        
        # Create work orders
        print("⚙️ Creating Work Orders...")
        service_requests = list(ServiceRequest.objects.all())
        technicians = [u for u in users if 'tech' in u.username]
        
        for i, sr in enumerate(random.sample(service_requests, min(10, len(service_requests)))):
            work_order, created = WorkOrder.objects.get_or_create(
                order_number=f"WO{datetime.now().year}{i+1:04d}",
                defaults={
                    'service_request': sr,
                    'title': sr.title,
                    'description': f"أمر شغل لمعالجة: {sr.title}",
                    'assigned_to': random.choice(technicians) if technicians else None,
                    'status': random.choice(['planned', 'new', 'assigned', 'in_progress', 'resolved']),
                    'created_at': sr.created_at + timedelta(hours=random.randint(1, 48))
                }
            )
            
            if created and i % 3 == 0:
                print(f"   ✓ Created {i + 1} work orders")
        
        print("\n" + "="*60)
        print("🎉 CMMS Test Data Generation Complete!")
        print(f"📊 Summary:")
        print(f"   • {len(companies)} Companies")
        print(f"   • {len(device_types)} Device Types")
        print(f"   • {len(categories)} Categories")
        print(f"   • {len(devices)} Medical Devices")
        print(f"   • {len(suppliers)} Suppliers")
        print(f"   • {len(spare_parts)} Spare Parts")
        print(f"   • {ServiceRequest.objects.count()} Service Requests")
        print(f"   • {WorkOrder.objects.count()} Work Orders")
        print("="*60)
        
    else:
        print("❌ Error: No departments or rooms found. Please create them first.")
        print("   Run: python manage.py loaddata initial_data.json")

if __name__ == "__main__":
    create_test_data()
