#!/usr/bin/env python
"""
CMMS Test Data Generator for HMS (Hospital Management System)
=============================================================

This script generates comprehensive, realistic test data for the CMMS system.

Usage:
    python manage.py shell < CMMS_Test_Data_Generator.py
"""

import os
import sys
import django
from datetime import datetime, timedelta, date
from decimal import Decimal
import random
import uuid
from faker import Faker

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

# Import all required models
from django.contrib.auth import get_user_model
from maintenance.models import *
from manager.models import Department, Room, Bed, Patient
from hr.models import CustomUser

# Initialize Faker
fake = Faker(['ar_SA', 'en_US'])
User = get_user_model()

class CMSTestDataGenerator:
    """Comprehensive test data generator for CMMS system"""
    
    def __init__(self):
        self.created_companies = []
        self.created_device_types = []
        self.created_device_usages = []
        self.created_categories = []
        self.created_subcategories = []
        self.created_devices = []
        self.created_suppliers = []
        self.created_spare_parts = []
        self.created_users = []
        self.created_service_requests = []
        self.created_work_orders = []
        self.created_job_plans = []
        
        print("🏥 CMMS Test Data Generator Initialized")

    def create_companies(self):
        """Create medical device companies"""
        print("\n🏢 Creating Companies...")
        
        companies_data = [
            "Philips Healthcare", "GE Healthcare", "Siemens Healthineers", 
            "Medtronic", "Johnson & Johnson Medical", "Abbott Laboratories",
            "شركة الأجهزة الطبية المتقدمة", "مؤسسة التقنيات الصحية",
            "شركة الرعاية الطبية الشاملة", "خدمات الصيانة الطبية المتخصصة"
        ]
        
        for name in companies_data:
            company = Company.objects.create(name=name)
            self.created_companies.append(company)
            print(f"   ✓ {company.name}")
        
        print(f"✅ Created {len(self.created_companies)} companies")

    def create_device_types_and_categories(self):
        """Create device types, categories, and subcategories"""
        print("\n🔧 Creating Device Types and Categories...")
        
        # Device Types
        device_types_data = [
            "أجهزة التنفس الصناعي", "أجهزة مراقبة المرضى", "أجهزة الأشعة السينية",
            "أجهزة الموجات فوق الصوتية", "أجهزة القسطرة القلبية", "أجهزة غسيل الكلى",
            "أجهزة التخدير", "أجهزة الليزر الطبي", "أجهزة المختبرات", "أجهزة الطوارئ"
        ]
        
        for type_name in device_types_data:
            device_type = DeviceType.objects.create(name=type_name)
            self.created_device_types.append(device_type)
        
        # Device Usages
        usage_data = [
            "تشخيص", "علاج", "مراقبة", "جراحة", "تصوير طبي",
            "تحاليل مختبرية", "إنعاش", "عناية مركزة", "طوارئ", "علاج طبيعي"
        ]
        
        for usage_name in usage_data:
            device_usage = DeviceUsage.objects.create(name=usage_name)
            self.created_device_usages.append(device_usage)
        
        # Device Categories with subcategories
        categories_data = [
            {"name": "أجهزة القلب والأوعية الدموية", "subcategories": [
                "أجهزة تخطيط القلب", "أجهزة قسطرة القلب", "أجهزة مراقبة القلب"
            ]},
            {"name": "أجهزة التنفس والرئة", "subcategories": [
                "أجهزة التنفس الصناعي", "أجهزة الأكسجين", "أجهزة قياس وظائف الرئة"
            ]},
            {"name": "أجهزة التصوير الطبي", "subcategories": [
                "أجهزة الأشعة السينية", "أجهزة الموجات فوق الصوتية", "أجهزة الرنين المغناطيسي"
            ]},
            {"name": "أجهزة المختبرات", "subcategories": [
                "أجهزة تحليل الدم", "أجهزة الكيمياء الحيوية", "أجهزة الميكروبيولوجي"
            ]},
            {"name": "أجهزة الجراحة", "subcategories": [
                "أجهزة التخدير", "أجهزة الكي الكهربائي", "أجهزة الليزر الجراحي"
            ]}
        ]
        
        for cat_data in categories_data:
            category = DeviceCategory.objects.create(name=cat_data["name"])
            self.created_categories.append(category)
            
            for subcat_name in cat_data["subcategories"]:
                subcategory = DeviceSubCategory.objects.create(
                    name=subcat_name, category=category
                )
                self.created_subcategories.append(subcategory)
        
        print(f"✅ Created device types, usages, and categories")

    def create_users(self):
        """Create test users with different roles"""
        print("\n👥 Creating Users...")
        
        users_data = [
            {"username": "admin", "first_name": "مدير", "last_name": "النظام", "is_superuser": True},
            {"username": "manager_1", "first_name": "أحمد", "last_name": "المدير", "role": "manager"},
            {"username": "supervisor_1", "first_name": "علي", "last_name": "المشرف", "role": "supervisor"},
            {"username": "tech_1", "first_name": "سعد", "last_name": "الفني", "role": "technician"},
            {"username": "tech_2", "first_name": "مريم", "last_name": "التقنية", "role": "technician"},
            {"username": "nurse_1", "first_name": "زينب", "last_name": "الممرضة", "role": "nurse"},
            {"username": "doctor_1", "first_name": "د. أحمد", "last_name": "الطبيب", "role": "doctor"},
        ]
        
        for user_data in users_data:
            if not User.objects.filter(username=user_data["username"]).exists():
                if user_data.get("is_superuser"):
                    user = User.objects.create_superuser(
                        username=user_data["username"],
                        email=f"{user_data['username']}@hospital.com",
                        password='admin123',
                        first_name=user_data["first_name"],
                        last_name=user_data["last_name"]
                    )
                else:
                    user = User.objects.create_user(
                        username=user_data["username"],
                        email=f"{user_data['username']}@hospital.com",
                        password='password123',
                        first_name=user_data["first_name"],
                        last_name=user_data["last_name"]
                    )
                self.created_users.append(user)
                print(f"   ✓ {user.get_full_name()} ({user.username})")
        
        print(f"✅ Created {len(self.created_users)} users")

    def create_devices(self):
        """Create medical devices"""
        print("\n🏥 Creating Medical Devices...")
        
        departments = list(Department.objects.all())
        rooms = list(Room.objects.all())
        
        if not departments or not rooms:
            print("❌ Error: No departments or rooms found")
            return
        
        device_templates = [
            {
                "name": "جهاز التنفس الصناعي فيليبس",
                "model": "V60 Ventilator",
                "manufacturer": "Philips Healthcare",
                "count": 15
            },
            {
                "name": "جهاز مراقبة المريض",
                "model": "IntelliVue MX800",
                "manufacturer": "Philips Healthcare",
                "count": 25
            },
            {
                "name": "جهاز الأشعة السينية المحمول",
                "model": "AMX 4 Plus",
                "manufacturer": "GE Healthcare",
                "count": 8
            },
            {
                "name": "جهاز الموجات فوق الصوتية",
                "model": "ACUSON X300",
                "manufacturer": "Siemens Healthineers",
                "count": 12
            }
        ]
        
        for template in device_templates:
            category = random.choice(self.created_categories)
            subcategory = random.choice(category.subcategories.all()) if category.subcategories.exists() else None
            device_type = random.choice(self.created_device_types)
            usage = random.choice(self.created_device_usages)
            manufacturer = next((c for c in self.created_companies if c.name == template["manufacturer"]), 
                              random.choice(self.created_companies))
            
            for i in range(template["count"]):
                serial_number = f"{template['model'][:6].upper()}{random.randint(100000, 999999)}"
                department = random.choice(departments)
                dept_rooms = [r for r in rooms if r.department == department]
                room = random.choice(dept_rooms) if dept_rooms else random.choice(rooms)
                production_date = fake.date_between(start_date='-10y', end_date='-1y')
                
                device = Device.objects.create(
                    name=f"{template['name']} #{i+1:02d}",
                    category=category,
                    subcategory=subcategory,
                    brief_description=f"جهاز طبي متقدم من نوع {template['name']}",
                    manufacturer=template["manufacturer"],
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
                    sterilization_status=random.choice(['sterilized', 'needs_sterilization', 'unknown'])
                )
                
                self.created_devices.append(device)
        
        print(f"✅ Created {len(self.created_devices)} medical devices")

    def create_suppliers_and_spare_parts(self):
        """Create suppliers and spare parts"""
        print("\n📦 Creating Suppliers and Spare Parts...")
        
        suppliers_data = [
            {
                "name": "شركة قطع الغيار الطبية",
                "code": "MPS001",
                "contact_person": "أحمد محمد",
                "phone": "+966501234567",
                "email": "ahmed@medicalparts.com"
            },
            {
                "name": "مؤسسة التوريدات الطبية",
                "code": "CMS002", 
                "contact_person": "فاطمة علي",
                "phone": "+966507654321",
                "email": "fatima@comprehensive.com"
            }
        ]
        
        for supplier_data in suppliers_data:
            supplier = Supplier.objects.create(**supplier_data)
            self.created_suppliers.append(supplier)
        
        spare_parts_data = [
            {
                "name": "فلتر هواء للتنفس الصناعي",
                "part_number": "VENT-FILTER-001",
                "description": "فلتر هواء عالي الكفاءة",
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
        
        for part_data in spare_parts_data:
            spare_part = SparePart.objects.create(
                supplier=random.choice(self.created_suppliers),
                **part_data
            )
            spare_part.compatible_devices.set(random.sample(self.created_devices, 
                                                          min(5, len(self.created_devices))))
            self.created_spare_parts.append(spare_part)
        
        print(f"✅ Created {len(self.created_suppliers)} suppliers and {len(self.created_spare_parts)} spare parts")

    def create_service_requests_and_work_orders(self):
        """Create service requests and work orders"""
        print("\n📋 Creating Service Requests and Work Orders...")
        
        if not self.created_devices or not self.created_users:
            print("❌ Error: No devices or users found")
            return
        
        # Create service requests
        for i in range(50):
            device = random.choice(self.created_devices)
            reporter = random.choice(self.created_users)
            
            service_request = ServiceRequest.objects.create(
                request_number=f"SR{datetime.now().year}{i+1:04d}",
                title=fake.sentence(nb_words=6),
                description=fake.text(max_nb_chars=200),
                device=device,
                requested_by=reporter,
                request_type=random.choice(['breakdown', 'preventive', 'calibration', 'upgrade']),
                priority=random.choice(['low', 'medium', 'high', 'critical']),
                status=random.choice(['new', 'assigned', 'in_progress', 'completed']),
                created_at=fake.date_time_between(start_date='-30d', end_date='now')
            )
            self.created_service_requests.append(service_request)
            
            # Create work order for some service requests
            if random.choice([True, False]):
                work_order = WorkOrder.objects.create(
                    service_request=service_request,
                    order_number=f"WO{datetime.now().year}{len(self.created_work_orders)+1:04d}",
                    title=service_request.title,
                    description=f"أمر شغل لمعالجة: {service_request.title}",
                    assigned_to=random.choice([u for u in self.created_users if 'tech' in u.username]),
                    status=random.choice(['planned', 'new', 'assigned', 'in_progress', 'resolved']),
                    created_at=service_request.created_at + timedelta(hours=random.randint(1, 24))
                )
                self.created_work_orders.append(work_order)
        
        print(f"✅ Created {len(self.created_service_requests)} service requests and {len(self.created_work_orders)} work orders")

    def create_job_plans_and_pm_schedules(self):
        """Create job plans and preventive maintenance schedules"""
        print("\n🔧 Creating Job Plans and PM Schedules...")
        
        job_plans_data = [
            {
                "name": "صيانة دورية لأجهزة التنفس الصناعي",
                "description": "فحص وصيانة شاملة لأجهزة التنفس الصناعي",
                "estimated_duration": timedelta(hours=2)
            },
            {
                "name": "معايرة أجهزة مراقبة المرضى",
                "description": "معايرة دقيقة لأجهزة مراقبة المرضى",
                "estimated_duration": timedelta(hours=1, minutes=30)
            },
            {
                "name": "فحص أمان أجهزة الأشعة",
                "description": "فحص شامل لأمان أجهزة الأشعة السينية",
                "estimated_duration": timedelta(hours=3)
            }
        ]
        
        for plan_data in job_plans_data:
            job_plan = JobPlan.objects.create(
                device_type=random.choice(self.created_device_types),
                created_by=random.choice(self.created_users),
                **plan_data
            )
            self.created_job_plans.append(job_plan)
            
            # Create job plan steps
            steps_data = [
                "فحص الاتصالات الكهربائية",
                "اختبار وظائف الجهاز الأساسية", 
                "تنظيف المكونات الداخلية",
                "فحص أنظمة الأمان",
                "توثيق النتائج"
            ]
            
            for step_num, step_desc in enumerate(steps_data, 1):
                JobPlanStep.objects.create(
                    job_plan=job_plan,
                    step_number=step_num,
                    description=step_desc,
                    estimated_time=timedelta(minutes=random.randint(15, 45))
                )
            
            # Create PM schedules for some devices
            compatible_devices = [d for d in self.created_devices 
                                if d.device_type == job_plan.device_type]
            
            for device in random.sample(compatible_devices, 
                                      min(3, len(compatible_devices))):
                PreventiveMaintenanceSchedule.objects.create(
                    device=device,
                    job_plan=job_plan,
                    frequency=random.choice(['monthly', 'quarterly', 'semi_annual', 'annual']),
                    next_due_date=fake.date_between(start_date='now', end_date='+90d'),
                    created_by=random.choice(self.created_users)
                )
        
        print(f"✅ Created {len(self.created_job_plans)} job plans and PM schedules")

    def create_notifications_and_logs(self):
        """Create notifications and activity logs"""
        print("\n🔔 Creating Notifications and Logs...")
        
        # Create system notifications
        for i in range(20):
            SystemNotification.objects.create(
                title=fake.sentence(nb_words=4),
                message=fake.text(max_nb_chars=150),
                notification_type=random.choice(['info', 'warning', 'alert', 'error']),
                user=random.choice(self.created_users),
                is_read=random.choice([True, False]),
                created_at=fake.date_time_between(start_date='-7d', end_date='now')
            )
        
        # Create device logs
        for device in random.sample(self.created_devices, min(20, len(self.created_devices))):
            # Cleaning logs
            for _ in range(random.randint(1, 5)):
                DeviceCleaningLog.objects.create(
                    device=device,
                    last_cleaned_by=random.choice(self.created_users),
                    cleaned_at=fake.date_time_between(start_date='-30d', end_date='now')
                )
            
            # Maintenance logs
            for _ in range(random.randint(1, 3)):
                DeviceMaintenanceLog.objects.create(
                    device=device,
                    last_maintained_by=random.choice([u for u in self.created_users if 'tech' in u.username]),
                    maintained_at=fake.date_time_between(start_date='-60d', end_date='now')
                )
        
        print("✅ Created notifications and activity logs")

    def run_all(self):
        """Run all data generation methods"""
        print("🚀 Starting comprehensive CMMS test data generation...")
        print("=" * 60)
        
        self.create_companies()
        self.create_device_types_and_categories()
        self.create_users()
        self.create_devices()
        self.create_suppliers_and_spare_parts()
        self.create_service_requests_and_work_orders()
        self.create_job_plans_and_pm_schedules()
        self.create_notifications_and_logs()
        
        print("\n" + "=" * 60)
        print("🎉 CMMS Test Data Generation Complete!")
        print(f"📊 Summary:")
        print(f"   • {len(self.created_companies)} Companies")
        print(f"   • {len(self.created_devices)} Medical Devices")
        print(f"   • {len(self.created_spare_parts)} Spare Parts")
        print(f"   • {len(self.created_service_requests)} Service Requests")
        print(f"   • {len(self.created_work_orders)} Work Orders")
        print(f"   • {len(self.created_job_plans)} Job Plans")
        print("=" * 60)

# Execute the generator
if __name__ == "__main__":
    generator = CMSTestDataGenerator()
    generator.run_all()
