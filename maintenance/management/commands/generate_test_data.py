from django.core.management.base import BaseCommand
from datetime import datetime, timedelta, date
from decimal import Decimal
import random
import uuid
from faker import Faker

from maintenance.models import *
from manager.models import Department, Room, Bed, Patient
from django.contrib.auth import get_user_model

User = get_user_model()
fake = Faker(['ar_SA', 'en_US'])

class Command(BaseCommand):
    help = 'Generate comprehensive test data for CMMS system'

    def handle(self, *args, **options):
        self.stdout.write("🏥 Starting CMMS Test Data Generation...")
        
        # Create companies
        self.stdout.write("🏢 Creating Companies...")
        companies_data = [
            "Philips Healthcare", "GE Healthcare", "Siemens Healthineers", 
            "Medtronic", "Johnson & Johnson Medical", "Abbott Laboratories",
            "شركة الأجهزة الطبية المتقدمة", "مؤسسة التقنيات الصحية"
        ]
        
        companies = []
        for name in companies_data:
            company, created = Company.objects.get_or_create(name=name)
            companies.append(company)
            if created:
                self.stdout.write(f"   ✓ {company.name}")
        
        # Create device types
        self.stdout.write("🔧 Creating Device Types...")
        device_types_data = [
            "أجهزة التنفس الصناعي", "أجهزة مراقبة المرضى", "أجهزة الأشعة السينية",
            "أجهزة الموجات فوق الصوتية", "أجهزة المختبرات"
        ]
        
        device_types = []
        for type_name in device_types_data:
            device_type, created = DeviceType.objects.get_or_create(name=type_name)
            device_types.append(device_type)
        
        # Create device usages
        usage_data = ["تشخيص", "علاج", "مراقبة", "جراحة", "تصوير طبي"]
        usages = []
        for usage_name in usage_data:
            usage, created = DeviceUsage.objects.get_or_create(name=usage_name)
            usages.append(usage)
        
        # Create categories
        categories = []
        categories_data = [
            {"name": "أجهزة القلب والأوعية الدموية", "subcategories": ["أجهزة تخطيط القلب", "أجهزة مراقبة القلب"]},
            {"name": "أجهزة التنفس والرئة", "subcategories": ["أجهزة التنفس الصناعي", "أجهزة الأكسجين"]},
            {"name": "أجهزة التصوير الطبي", "subcategories": ["أجهزة الأشعة السينية", "أجهزة الموجات فوق الصوتية"]}
        ]
        
        for cat_data in categories_data:
            category, created = DeviceCategory.objects.get_or_create(name=cat_data["name"])
            categories.append(category)
            
            for subcat_name in cat_data["subcategories"]:
                DeviceSubCategory.objects.get_or_create(name=subcat_name, category=category)
        
        # Create users
        self.stdout.write("👥 Creating Users...")
        users_data = [
            {"username": "tech_1", "first_name": "سعد", "last_name": "الفني"},
            {"username": "tech_2", "first_name": "مريم", "last_name": "التقنية"},
            {"username": "supervisor_1", "first_name": "علي", "last_name": "المشرف"},
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
            users.append(user)
        
        # Create devices
        self.stdout.write("🏥 Creating Medical Devices...")
        departments = list(Department.objects.all())
        rooms = list(Room.objects.all())
        
        if departments and rooms:
            device_templates = [
                {"name": "جهاز التنفس الصناعي", "model": "V60", "count": 5},
                {"name": "جهاز مراقبة المريض", "model": "MX800", "count": 8},
                {"name": "جهاز الأشعة السينية", "model": "AMX4", "count": 3}
            ]
            
            devices = []
            for template in device_templates:
                for i in range(template["count"]):
                    department = random.choice(departments)
                    dept_rooms = [r for r in rooms if r.department == department]
                    room = random.choice(dept_rooms) if dept_rooms else random.choice(rooms)
                    
                    device = Device.objects.create(
                        name=f"{template['name']} #{i+1:02d}",
                        category=random.choice(categories),
                        brief_description=f"جهاز طبي من نوع {template['name']}",
                        manufacturer="Philips Healthcare",
                        model=template["model"],
                        serial_number=f"{template['model']}{random.randint(100000, 999999)}",
                        production_date=fake.date_between(start_date='-5y', end_date='-1y'),
                        department=department,
                        room=room,
                        manufacture_company=random.choice(companies),
                        device_type=random.choice(device_types),
                        device_usage=random.choice(usages),
                        status=random.choice(['working', 'needs_maintenance']),
                        clean_status=random.choice(['clean', 'needs_cleaning']),
                        sterilization_status=random.choice(['sterilized', 'needs_sterilization'])
                    )
                    devices.append(device)
            
            # Create service requests
            self.stdout.write("📋 Creating Service Requests...")
            for i in range(10):
                ServiceRequest.objects.create(
                    request_number=f"SR{datetime.now().year}{i+1:04d}",
                    title=f"بلاغ صيانة رقم {i+1}",
                    description=f"وصف المشكلة للبلاغ رقم {i+1}",
                    device=random.choice(devices),
                    requested_by=random.choice(users),
                    request_type=random.choice(['breakdown', 'preventive', 'calibration']),
                    priority=random.choice(['low', 'medium', 'high']),
                    status=random.choice(['new', 'assigned', 'in_progress'])
                )
        
        self.stdout.write(self.style.SUCCESS("✅ CMMS Test Data Generation Completed Successfully!"))
