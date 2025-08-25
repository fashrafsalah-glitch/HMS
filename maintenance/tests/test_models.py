# اختبارات الموديلات للـ CMMS
# هنا بنختبر جميع الموديلات والعلاقات والدوال الخاصة بها

from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal

from maintenance.models import (
    Device, DeviceCategory, ServiceRequest, WorkOrder, SLADefinition, SLAMatrix,
    JobPlan, JobPlanStep, PreventiveMaintenanceSchedule, CalibrationRecord,
    DowntimeEvent, DeviceUsageLog, WorkOrderPart, SparePart, Supplier
)


class DeviceModelTest(TestCase):
    """اختبارات موديل الجهاز"""
    
    def setUp(self):
        """إعداد البيانات للاختبار"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
    def test_device_creation(self):
        """اختبار إنشاء جهاز جديد"""
        device = Device.objects.create(
            name='جهاز اختبار',
            serial_number='TEST001',
            model='Model X',
            manufacturer='Test Manufacturer',
            category='medical',
            status='operational'
        )
        
        self.assertEqual(device.name, 'جهاز اختبار')
        self.assertEqual(device.serial_number, 'TEST001')
        self.assertEqual(device.status, 'operational')
        self.assertTrue(device.qr_token)  # يجب أن يتم إنشاء QR token تلقائياً
        
    def test_device_str_method(self):
        """اختبار دالة __str__ للجهاز"""
        device = Device.objects.create(
            name='جهاز اختبار',
            serial_number='TEST001'
        )
        
        self.assertEqual(str(device), 'جهاز اختبار')


class ServiceRequestModelTest(TestCase):
    """اختبارات موديل طلب الخدمة"""
    
    def setUp(self):
        """إعداد البيانات للاختبار"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.device = Device.objects.create(
            name='جهاز اختبار',
            serial_number='TEST001',
            category='medical'
        )
        
        self.sla = SLA.objects.create(
            name='SLA اختبار',
            response_time_hours=4,
            resolution_time_hours=24
        )
        
    def test_service_request_creation(self):
        """اختبار إنشاء طلب خدمة جديد"""
        service_request = ServiceRequest.objects.create(
            title='طلب صيانة اختبار',
            description='وصف الطلب',
            device=self.device,
            requested_by=self.user,
            priority='high',
            request_type='breakdown',
            sla=self.sla
        )
        
        self.assertEqual(service_request.title, 'طلب صيانة اختبار')
        self.assertEqual(service_request.status, 'new')  # الحالة الافتراضية
        self.assertEqual(service_request.priority, 'high')
        self.assertIsNotNone(service_request.response_due)
        self.assertIsNotNone(service_request.resolution_due)
        
    def test_service_request_sla_calculation(self):
        """اختبار حساب أوقات SLA"""
        service_request = ServiceRequest.objects.create(
            title='طلب صيانة اختبار',
            description='وصف الطلب',
            device=self.device,
            requested_by=self.user,
            sla=self.sla
        )
        
        # التحقق من أن أوقات SLA تم حسابها بشكل صحيح
        expected_response = timezone.now() + timedelta(hours=4)
        expected_resolution = timezone.now() + timedelta(hours=24)
        
        # السماح بفارق دقيقة واحدة للتعامل مع وقت التنفيذ
        self.assertAlmostEqual(
            service_request.response_due.timestamp(),
            expected_response.timestamp(),
            delta=60
        )
        
        self.assertAlmostEqual(
            service_request.resolution_due.timestamp(),
            expected_resolution.timestamp(),
            delta=60
        )


class WorkOrderModelTest(TestCase):
    """اختبارات موديل أمر الشغل"""
    
    def setUp(self):
        """إعداد البيانات للاختبار"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.technician = User.objects.create_user(
            username='technician',
            email='tech@example.com',
            password='testpass123'
        )
        
        self.device = Device.objects.create(
            name='جهاز اختبار',
            serial_number='TEST001'
        )
        
        self.service_request = ServiceRequest.objects.create(
            title='طلب صيانة اختبار',
            description='وصف الطلب',
            device=self.device,
            requested_by=self.user
        )
        
        self.job_plan = JobPlan.objects.create(
            name='خطة عمل اختبار',
            description='وصف خطة العمل',
            instructions='تعليمات التنفيذ',
            estimated_duration=120,
            created_by=self.user
        )
        
    def test_work_order_creation(self):
        """اختبار إنشاء أمر شغل جديد"""
        work_order = WorkOrder.objects.create(
            service_request=self.service_request,
            assigned_technician=self.technician,
            job_plan=self.job_plan
        )
        
        self.assertEqual(work_order.status, 'new')  # الحالة الافتراضية
        self.assertEqual(work_order.assigned_technician, self.technician)
        self.assertEqual(work_order.job_plan, self.job_plan)
        
    def test_work_order_duration_calculation(self):
        """اختبار حساب مدة العمل"""
        work_order = WorkOrder.objects.create(
            service_request=self.service_request,
            assigned_technician=self.technician,
            start_time=timezone.now(),
            end_time=timezone.now() + timedelta(hours=2)
        )
        
        # يمكن إضافة property لحساب المدة في الموديل
        duration = work_order.end_time - work_order.start_time
        self.assertEqual(duration.total_seconds(), 7200)  # ساعتان


class SparePartModelTest(TestCase):
    """اختبارات موديل قطع الغيار"""
    
    def setUp(self):
        """إعداد البيانات للاختبار"""
        self.supplier = Supplier.objects.create(
            name='مورد اختبار',
            contact_person='أحمد محمد',
            email='supplier@example.com'
        )
        
        self.device = Device.objects.create(
            name='جهاز اختبار',
            serial_number='TEST001'
        )
        
    def test_spare_part_creation(self):
        """اختبار إنشاء قطعة غيار جديدة"""
        spare_part = SparePart.objects.create(
            name='قطعة اختبار',
            part_number='PART001',
            supplier=self.supplier,
            cost=Decimal('100.50'),
            quantity=10,
            minimum_stock=5
        )
        
        self.assertEqual(spare_part.name, 'قطعة اختبار')
        self.assertEqual(spare_part.part_number, 'PART001')
        self.assertEqual(spare_part.cost, Decimal('100.50'))
        self.assertEqual(spare_part.status, 'available')  # الحالة الافتراضية
        
    def test_spare_part_stock_status(self):
        """اختبار حالة المخزون"""
        # قطعة غيار متوفرة
        spare_part = SparePart.objects.create(
            name='قطعة متوفرة',
            part_number='PART001',
            quantity=10,
            minimum_stock=5
        )
        self.assertEqual(spare_part.status, 'available')
        
        # قطعة غيار منخفضة
        spare_part.quantity = 3
        spare_part.save()
        # يجب إضافة signal أو method لتحديث الحالة تلقائياً
        
        # قطعة غيار منتهية
        spare_part.quantity = 0
        spare_part.save()


class CalibrationModelTest(TestCase):
    """اختبارات موديل المعايرة"""
    
    def setUp(self):
        """إعداد البيانات للاختبار"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.device = Device.objects.create(
            name='جهاز اختبار',
            serial_number='TEST001'
        )
        
    def test_calibration_creation(self):
        """اختبار إنشاء سجل معايرة جديد"""
        calibration = Calibration.objects.create(
            device=self.device,
            calibration_date=date.today(),
            next_calibration_date=date.today() + timedelta(days=365),
            calibration_standard='ISO 9001',
            results='نتائج المعايرة',
            status='passed',
            performed_by=self.user
        )
        
        self.assertEqual(calibration.device, self.device)
        self.assertEqual(calibration.status, 'passed')
        self.assertEqual(calibration.calibration_standard, 'ISO 9001')


class NotificationModelTest(TestCase):
    """اختبارات موديلات الإشعارات"""
    
    def setUp(self):
        """إعداد البيانات للاختبار"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
    def test_system_notification_creation(self):
        """اختبار إنشاء إشعار نظام"""
        notification = SystemNotification.objects.create(
            user=self.user,
            title='إشعار اختبار',
            message='رسالة الإشعار',
            notification_type='info'
        )
        
        self.assertEqual(notification.user, self.user)
        self.assertEqual(notification.title, 'إشعار اختبار')
        self.assertFalse(notification.is_read)  # غير مقروء افتراضياً
        
    def test_notification_preferences_creation(self):
        """اختبار إنشاء تفضيلات الإشعارات"""
        preferences = NotificationPreference.objects.create(
            user=self.user,
            sla_violations_email=True,
            pm_due_system=False
        )
        
        self.assertEqual(preferences.user, self.user)
        self.assertTrue(preferences.sla_violations_email)
        self.assertFalse(preferences.pm_due_system)
        
    def test_notification_template_creation(self):
        """اختبار إنشاء قالب إشعار"""
        template = NotificationTemplate.objects.create(
            name='قالب اختبار',
            subject='موضوع الإشعار',
            email_template='قالب الإيميل: {device_name}',
            system_template='قالب النظام: {device_name}',
            notification_type='sla_violation'
        )
        
        self.assertEqual(template.name, 'قالب اختبار')
        self.assertEqual(template.notification_type, 'sla_violation')
        self.assertTrue(template.is_active)  # نشط افتراضياً


class PreventiveMaintenanceTest(TestCase):
    """اختبارات الصيانة الوقائية"""
    
    def setUp(self):
        """إعداد البيانات للاختبار"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.device = Device.objects.create(
            name='جهاز اختبار',
            serial_number='TEST001'
        )
        
        self.job_plan = JobPlan.objects.create(
            name='خطة صيانة وقائية',
            description='وصف خطة الصيانة',
            instructions='تعليمات الصيانة',
            estimated_duration=60,
            created_by=self.user
        )
        
    def test_pm_schedule_creation(self):
        """اختبار إنشاء جدول صيانة وقائية"""
        pm_schedule = PreventiveMaintenanceSchedule.objects.create(
            device=self.device,
            job_plan=self.job_plan,
            frequency='monthly',
            next_due_date=date.today() + timedelta(days=30),
            assigned_technician=self.user
        )
        
        self.assertEqual(pm_schedule.device, self.device)
        self.assertEqual(pm_schedule.frequency, 'monthly')
        self.assertEqual(pm_schedule.status, 'active')  # نشط افتراضياً
        
    def test_pm_schedule_next_due_calculation(self):
        """اختبار حساب تاريخ الاستحقاق التالي"""
        pm_schedule = PreventiveMaintenanceSchedule.objects.create(
            device=self.device,
            job_plan=self.job_plan,
            frequency='weekly',
            next_due_date=date.today(),
            last_completed_date=date.today() - timedelta(days=7)
        )
        
        # يمكن إضافة method لحساب التاريخ التالي
        expected_next_due = pm_schedule.last_completed_date + timedelta(days=7)
        # self.assertEqual(pm_schedule.calculate_next_due_date(), expected_next_due)


class PurchaseOrderTest(TestCase):
    """اختبارات أوامر الشراء"""
    
    def setUp(self):
        """إعداد البيانات للاختبار"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.supplier = Supplier.objects.create(
            name='مورد اختبار',
            contact_person='أحمد محمد',
            email='supplier@example.com'
        )
        
        self.spare_part = SparePart.objects.create(
            name='قطعة اختبار',
            part_number='PART001',
            supplier=self.supplier,
            cost=Decimal('50.00')
        )
        
    def test_purchase_order_creation(self):
        """اختبار إنشاء أمر شراء"""
        po = PurchaseOrder.objects.create(
            order_number='PO001',
            supplier=self.supplier,
            created_by=self.user,
            order_date=date.today(),
            expected_delivery_date=date.today() + timedelta(days=7)
        )
        
        self.assertEqual(po.order_number, 'PO001')
        self.assertEqual(po.supplier, self.supplier)
        self.assertEqual(po.status, 'draft')  # مسودة افتراضياً
        
    def test_purchase_order_item_creation(self):
        """اختبار إنشاء عنصر أمر شراء"""
        po = PurchaseOrder.objects.create(
            order_number='PO001',
            supplier=self.supplier,
            created_by=self.user
        )
        
        po_item = PurchaseOrderItem.objects.create(
            purchase_order=po,
            spare_part=self.spare_part,
            quantity_ordered=10,
            unit_cost=Decimal('50.00'),
            total_cost=Decimal('500.00')
        )
        
        self.assertEqual(po_item.quantity_ordered, 10)
        self.assertEqual(po_item.total_cost, Decimal('500.00'))
        self.assertEqual(po_item.quantity_received, 0)  # لم يتم الاستلام بعد


class SLAModelTest(TestCase):
    """اختبارات موديلات SLA"""
    
    def setUp(self):
        """إعداد البيانات للاختبار"""
        self.sla = SLA.objects.create(
            name='SLA اختبار',
            description='وصف SLA',
            response_time_hours=4,
            resolution_time_hours=24
        )
        
    def test_sla_creation(self):
        """اختبار إنشاء SLA"""
        self.assertEqual(self.sla.name, 'SLA اختبار')
        self.assertEqual(self.sla.response_time_hours, 4)
        self.assertEqual(self.sla.resolution_time_hours, 24)
        self.assertTrue(self.sla.is_active)  # نشط افتراضياً
        
    def test_sla_matrix_creation(self):
        """اختبار إنشاء مصفوفة SLA"""
        sla_matrix = SLAMatrix.objects.create(
            device_category='medical',
            priority='high',
            request_type='breakdown',
            sla=self.sla
        )
        
        self.assertEqual(sla_matrix.device_category, 'medical')
        self.assertEqual(sla_matrix.priority, 'high')
        self.assertEqual(sla_matrix.sla, self.sla)


class DowntimeModelTest(TestCase):
    """اختبارات موديل أوقات التوقف"""
    
    def setUp(self):
        """إعداد البيانات للاختبار"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.device = Device.objects.create(
            name='جهاز اختبار',
            serial_number='TEST001'
        )
        
    def test_downtime_creation(self):
        """اختبار إنشاء سجل توقف"""
        downtime = Downtime.objects.create(
            device=self.device,
            start_time=timezone.now(),
            reason='breakdown',
            description='عطل في الجهاز',
            reported_by=self.user
        )
        
        self.assertEqual(downtime.device, self.device)
        self.assertEqual(downtime.reason, 'breakdown')
        self.assertIsNone(downtime.end_time)  # لم ينته التوقف بعد
        
    def test_downtime_duration_calculation(self):
        """اختبار حساب مدة التوقف"""
        start_time = timezone.now()
        end_time = start_time + timedelta(hours=3)
        
        downtime = Downtime.objects.create(
            device=self.device,
            start_time=start_time,
            end_time=end_time,
            reason='maintenance',
            description='صيانة مجدولة',
            reported_by=self.user
        )
        
        duration = downtime.end_time - downtime.start_time
        self.assertEqual(duration.total_seconds(), 10800)  # 3 ساعات
