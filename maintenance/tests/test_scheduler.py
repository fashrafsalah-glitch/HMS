# اختبارات نظام الجدولة للـ CMMS
# هنا بنختبر المهام المجدولة والـ scheduler

from django.test import TestCase
from django.contrib.auth.models import User, Group
from django.utils import timezone
from django.core.management import call_command
from unittest.mock import patch, MagicMock
from datetime import date, timedelta
from decimal import Decimal

from maintenance.models import Device
from maintenance.models_cmms import (
    ServiceRequest, WorkOrder, PreventiveMaintenanceSchedule, 
    JobPlan, SLA, SLAMatrix
)
from maintenance.models_spare_parts import SparePart, Supplier, Calibration
from maintenance.models_notifications import SystemNotification
from maintenance.scheduler import CMMSScheduler
from maintenance.permissions import setup_cmms_permissions


class CMMSSchedulerTest(TestCase):
    """اختبارات جدولة المهام"""
    
    def setUp(self):
        """إعداد البيانات للاختبار"""
        # إنشاء المستخدمين
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='testpass123',
            is_staff=True
        )
        
        self.technician_user = User.objects.create_user(
            username='technician',
            email='tech@example.com',
            password='testpass123'
        )
        
        # إعداد الصلاحيات
        setup_cmms_permissions()
        
        admin_group = Group.objects.get(name='CMMS_Admin')
        technician_group = Group.objects.get(name='CMMS_Technician')
        
        self.admin_user.groups.add(admin_group)
        self.technician_user.groups.add(technician_group)
        
        # إنشاء البيانات الأساسية
        self.device = Device.objects.create(
            name='جهاز اختبار',
            serial_number='TEST001',
            category='medical'
        )
        
        self.job_plan = JobPlan.objects.create(
            name='خطة صيانة وقائية',
            description='وصف خطة الصيانة',
            instructions='تعليمات الصيانة',
            estimated_duration=60,
            created_by=self.admin_user
        )
        
        self.sla = SLA.objects.create(
            name='SLA اختبار',
            response_time_hours=4,
            resolution_time_hours=24
        )
        
        SLAMatrix.objects.create(
            device_category='medical',
            priority='medium',
            request_type='preventive',
            sla=self.sla
        )
        
        self.scheduler = CMMSScheduler()
        
    def test_create_due_preventive_maintenance(self):
        """اختبار إنشاء الصيانة الوقائية المستحقة"""
        # إنشاء جدول صيانة وقائية مستحق
        pm_schedule = PreventiveMaintenanceSchedule.objects.create(
            device=self.device,
            job_plan=self.job_plan,
            frequency='monthly',
            next_due_date=date.today() - timedelta(days=1),  # مستحق أمس
            assigned_technician=self.technician_user,
            status='active'
        )
        
        # تشغيل المهمة
        self.scheduler.create_due_preventive_maintenance()
        
        # التحقق من إنشاء طلب الخدمة
        service_requests = ServiceRequest.objects.filter(
            device=self.device,
            request_type='preventive',
            is_auto_generated=True
        )
        
        self.assertEqual(service_requests.count(), 1)
        
        service_request = service_requests.first()
        self.assertEqual(service_request.assigned_to, self.technician_user)
        self.assertIsNotNone(service_request.sla)
        
        # التحقق من إنشاء أمر الشغل
        work_orders = WorkOrder.objects.filter(service_request=service_request)
        self.assertEqual(work_orders.count(), 1)
        
        work_order = work_orders.first()
        self.assertEqual(work_order.assigned_technician, self.technician_user)
        self.assertEqual(work_order.job_plan, self.job_plan)
        
        # التحقق من تحديث جدول الصيانة الوقائية
        pm_schedule.refresh_from_db()
        self.assertEqual(pm_schedule.last_completed_date, date.today())
        self.assertGreater(pm_schedule.next_due_date, date.today())
        
    def test_skip_existing_preventive_maintenance(self):
        """اختبار تجاهل الصيانة الوقائية الموجودة"""
        # إنشاء طلب صيانة وقائية موجود
        ServiceRequest.objects.create(
            title='صيانة وقائية موجودة',
            description='وصف',
            device=self.device,
            requested_by=self.admin_user,
            request_type='preventive',
            status='new'
        )
        
        # إنشاء جدول صيانة وقائية مستحق
        PreventiveMaintenanceSchedule.objects.create(
            device=self.device,
            job_plan=self.job_plan,
            frequency='monthly',
            next_due_date=date.today() - timedelta(days=1),
            assigned_technician=self.technician_user,
            status='active'
        )
        
        # تشغيل المهمة
        self.scheduler.create_due_preventive_maintenance()
        
        # يجب ألا يتم إنشاء طلب جديد
        auto_requests = ServiceRequest.objects.filter(
            device=self.device,
            request_type='preventive',
            is_auto_generated=True
        )
        
        self.assertEqual(auto_requests.count(), 0)
        
    def test_check_sla_violations(self):
        """اختبار فحص انتهاكات SLA"""
        # إنشاء طلب خدمة متأخر في الاستجابة
        overdue_time = timezone.now() - timedelta(hours=1)
        
        service_request = ServiceRequest.objects.create(
            title='طلب متأخر',
            description='وصف الطلب',
            device=self.device,
            requested_by=self.admin_user,
            status='new',
            sla=self.sla,
            response_due=overdue_time
        )
        
        # تشغيل فحص انتهاكات SLA
        with patch.object(self.scheduler.notification_manager, 'send_sla_violation_notification') as mock_notify:
            self.scheduler.check_sla_violations()
            
            # يجب أن يتم إرسال إشعار انتهاك
            mock_notify.assert_called_once_with(service_request, 'response')
            
    def test_check_due_calibrations(self):
        """اختبار فحص المعايرات المستحقة"""
        # إنشاء معايرة مستحقة خلال 30 يوم
        due_date = date.today() + timedelta(days=15)
        
        Calibration.objects.create(
            device=self.device,
            calibration_date=date.today() - timedelta(days=350),
            next_calibration_date=due_date,
            performed_by=self.admin_user,
            status='passed'
        )
        
        # تشغيل فحص المعايرات
        with patch.object(self.scheduler.notification_manager, 'send_calibration_due_notification') as mock_notify:
            self.scheduler.check_due_calibrations()
            
            # يجب أن يتم إرسال إشعار
            mock_notify.assert_called_once()
            
    def test_check_low_stock_spare_parts(self):
        """اختبار فحص قطع الغيار المنخفضة"""
        supplier = Supplier.objects.create(name='مورد اختبار')
        
        # قطعة غيار منخفضة
        low_stock_part = SparePart.objects.create(
            name='قطعة منخفضة',
            part_number='LOW001',
            supplier=supplier,
            quantity=2,
            minimum_stock=5
        )
        
        # قطعة غيار منتهية
        out_of_stock_part = SparePart.objects.create(
            name='قطعة منتهية',
            part_number='OUT001',
            supplier=supplier,
            quantity=0,
            minimum_stock=3
        )
        
        # تشغيل فحص قطع الغيار
        with patch.object(self.scheduler.notification_manager, 'send_spare_parts_low_notification') as mock_low:
            with patch.object(self.scheduler.notification_manager, 'send_spare_parts_out_notification') as mock_out:
                with patch.object(self.scheduler, '_get_maintenance_managers', return_value=[self.admin_user]):
                    self.scheduler.check_low_stock_spare_parts()
                    
                    # يجب أن يتم إرسال إشعارات
                    mock_low.assert_called_once_with(low_stock_part, self.admin_user)
                    mock_out.assert_called_once_with(out_of_stock_part, self.admin_user)
                    
    def test_update_overdue_work_orders(self):
        """اختبار تحديث أوامر الشغل المتأخرة"""
        # إنشاء طلب خدمة متأخر
        overdue_time = timezone.now() - timedelta(hours=2)
        
        service_request = ServiceRequest.objects.create(
            title='طلب متأخر',
            description='وصف الطلب',
            device=self.device,
            requested_by=self.admin_user,
            resolution_due=overdue_time
        )
        
        work_order = WorkOrder.objects.create(
            service_request=service_request,
            assigned_technician=self.technician_user,
            status='in_progress'
        )
        
        # تشغيل تحديث أوامر الشغل المتأخرة
        with patch.object(self.scheduler.notification_manager, 'send_work_order_overdue_notification') as mock_notify:
            self.scheduler.update_overdue_work_orders()
            
            # يجب أن يتم إرسال إشعار
            mock_notify.assert_called_once_with(work_order, self.technician_user)
            
    def test_calculate_next_due_date(self):
        """اختبار حساب تاريخ الاستحقاق التالي"""
        # إنشاء جدول صيانة وقائية
        pm_schedule = PreventiveMaintenanceSchedule.objects.create(
            device=self.device,
            job_plan=self.job_plan,
            frequency='weekly',
            next_due_date=date.today(),
            last_completed_date=date.today()
        )
        
        # حساب التاريخ التالي
        next_date = self.scheduler._calculate_next_due_date(pm_schedule)
        expected_date = date.today() + timedelta(weeks=1)
        
        self.assertEqual(next_date, expected_date)
        
        # اختبار التكرار الشهري
        pm_schedule.frequency = 'monthly'
        next_date = self.scheduler._calculate_next_due_date(pm_schedule)
        expected_date = date.today() + timedelta(days=30)
        
        self.assertEqual(next_date, expected_date)
        
        # اختبار التكرار المخصص
        pm_schedule.frequency = 'custom'
        pm_schedule.frequency_value = 14  # كل 14 يوم
        next_date = self.scheduler._calculate_next_due_date(pm_schedule)
        expected_date = date.today() + timedelta(days=14)
        
        self.assertEqual(next_date, expected_date)
        
    def test_get_appropriate_sla(self):
        """اختبار الحصول على SLA المناسب"""
        # يجب أن يجد SLA المناسب
        sla = self.scheduler._get_appropriate_sla(self.device, 'preventive', 'medium')
        self.assertEqual(sla, self.sla)
        
        # يجب أن يعيد None أو SLA افتراضي إذا لم يجد مطابقة
        sla = self.scheduler._get_appropriate_sla(self.device, 'breakdown', 'critical')
        # يجب أن يعيد SLA افتراضي أو None
        self.assertIsNotNone(sla)  # لأن لدينا SLA واحد نشط
        
    @patch('maintenance.scheduler.CMMSScheduler.create_due_preventive_maintenance')
    @patch('maintenance.scheduler.CMMSScheduler.check_sla_violations')
    @patch('maintenance.scheduler.CMMSScheduler.check_due_calibrations')
    @patch('maintenance.scheduler.CMMSScheduler.check_low_stock_spare_parts')
    @patch('maintenance.scheduler.CMMSScheduler.update_overdue_work_orders')
    @patch('maintenance.scheduler.CMMSScheduler.process_notification_queue')
    @patch('maintenance.scheduler.CMMSScheduler.cleanup_old_data')
    def test_run_all_scheduled_tasks(self, mock_cleanup, mock_queue, mock_overdue, 
                                   mock_spare_parts, mock_calibration, mock_sla, mock_pm):
        """اختبار تشغيل جميع المهام المجدولة"""
        self.scheduler.run_all_scheduled_tasks()
        
        # التحقق من استدعاء جميع المهام
        mock_pm.assert_called_once()
        mock_sla.assert_called_once()
        mock_calibration.assert_called_once()
        mock_spare_parts.assert_called_once()
        mock_overdue.assert_called_once()
        mock_queue.assert_called_once()
        mock_cleanup.assert_called_once()


class SchedulerManagementCommandTest(TestCase):
    """اختبارات أمر إدارة الجدولة"""
    
    def setUp(self):
        """إعداد البيانات للاختبار"""
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='testpass123',
            is_staff=True
        )
        
    @patch('maintenance.scheduler.CMMSScheduler.create_due_preventive_maintenance')
    def test_run_specific_task(self, mock_pm):
        """اختبار تشغيل مهمة محددة"""
        call_command('run_cmms_scheduler', '--task=pm')
        
        mock_pm.assert_called_once()
        
    @patch('maintenance.scheduler.CMMSScheduler.run_all_scheduled_tasks')
    def test_run_all_tasks(self, mock_all):
        """اختبار تشغيل جميع المهام"""
        call_command('run_cmms_scheduler')
        
        mock_all.assert_called_once()
        
    def test_dry_run_mode(self):
        """اختبار الوضع التجريبي"""
        # يجب ألا يحدث أي تغيير في الوضع التجريبي
        with patch('maintenance.scheduler.CMMSScheduler') as mock_scheduler:
            call_command('run_cmms_scheduler', '--dry-run')
            
            # يجب ألا يتم إنشاء scheduler في الوضع التجريبي
            mock_scheduler.assert_not_called()


class SchedulerConfigTest(TestCase):
    """اختبارات إعدادات الجدولة"""
    
    def test_scheduler_config_import(self):
        """اختبار استيراد إعدادات الجدولة"""
        from maintenance.scheduler_config import SCHEDULER_CONFIG, get_config
        
        # التحقق من وجود الإعدادات الأساسية
        self.assertIn('preventive_maintenance', SCHEDULER_CONFIG)
        self.assertIn('sla_violations', SCHEDULER_CONFIG)
        self.assertIn('notification_queue', SCHEDULER_CONFIG)
        
        # اختبار دالة get_config
        pm_config = get_config('preventive_maintenance.enabled')
        self.assertIsNotNone(pm_config)
        
        # اختبار قيمة افتراضية
        invalid_config = get_config('invalid.config', default='default_value')
        self.assertEqual(invalid_config, 'default_value')
        
    def test_working_hours_check(self):
        """اختبار فحص أوقات العمل"""
        from maintenance.scheduler_config import is_working_hours
        from datetime import time
        
        # محاكاة وقت العمل (10 صباحاً)
        with patch('maintenance.scheduler_config.timezone') as mock_timezone:
            mock_timezone.now.return_value.time.return_value = time(10, 0)
            mock_timezone.now.return_value.weekday.return_value = 1  # الثلاثاء
            
            # يجب أن يكون ضمن أوقات العمل
            self.assertTrue(is_working_hours())
            
        # محاكاة وقت خارج العمل (11 مساءً)
        with patch('maintenance.scheduler_config.timezone') as mock_timezone:
            mock_timezone.now.return_value.time.return_value = time(23, 0)
            mock_timezone.now.return_value.weekday.return_value = 1  # الثلاثاء
            
            # يجب أن يكون خارج أوقات العمل
            self.assertFalse(is_working_hours())
            
    def test_task_scheduling_check(self):
        """اختبار فحص ضرورة تشغيل المهمة"""
        from maintenance.scheduler_config import should_run_task
        
        # مهمة غير موجودة
        self.assertFalse(should_run_task('invalid_task'))
        
        # مهمة معطلة
        with patch('maintenance.scheduler_config.SCHEDULER_CONFIG', {
            'test_task': {'enabled': False}
        }):
            self.assertFalse(should_run_task('test_task'))
            
        # مهمة لم يتم تشغيلها من قبل
        with patch('maintenance.scheduler_config.SCHEDULER_CONFIG', {
            'test_task': {'enabled': True, 'interval': timedelta(hours=1)}
        }):
            self.assertTrue(should_run_task('test_task', last_run=None))


class SchedulerPerformanceTest(TestCase):
    """اختبارات الأداء للجدولة"""
    
    def setUp(self):
        """إعداد بيانات كبيرة للاختبار"""
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='testpass123'
        )
        
        # إنشاء عدد كبير من الأجهزة
        self.devices = []
        for i in range(100):
            device = Device.objects.create(
                name=f'جهاز {i+1}',
                serial_number=f'DEV{i+1:03d}',
                category='medical'
            )
            self.devices.append(device)
            
        self.scheduler = CMMSScheduler()
        
    def test_large_scale_pm_creation(self):
        """اختبار إنشاء صيانة وقائية على نطاق واسع"""
        job_plan = JobPlan.objects.create(
            name='خطة صيانة',
            description='وصف',
            instructions='تعليمات',
            estimated_duration=60,
            created_by=self.admin_user
        )
        
        # إنشاء جداول صيانة وقائية لجميع الأجهزة
        for device in self.devices:
            PreventiveMaintenanceSchedule.objects.create(
                device=device,
                job_plan=job_plan,
                frequency='monthly',
                next_due_date=date.today() - timedelta(days=1),
                status='active'
            )
            
        # قياس الوقت المستغرق
        import time
        start_time = time.time()
        
        self.scheduler.create_due_preventive_maintenance()
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # يجب أن يكتمل في وقت معقول (أقل من 30 ثانية)
        self.assertLess(execution_time, 30)
        
        # التحقق من إنشاء جميع طلبات الخدمة
        service_requests = ServiceRequest.objects.filter(
            request_type='preventive',
            is_auto_generated=True
        )
        
        self.assertEqual(service_requests.count(), 100)
        
    def test_memory_usage_optimization(self):
        """اختبار تحسين استخدام الذاكرة"""
        # إنشاء عدد كبير من الإشعارات القديمة
        old_date = timezone.now() - timedelta(days=35)
        
        for i in range(1000):
            SystemNotification.objects.create(
                user=self.admin_user,
                title=f'إشعار قديم {i+1}',
                message='رسالة قديمة',
                is_read=True,
                created_at=old_date
            )
            
        # تشغيل تنظيف البيانات
        import time
        start_time = time.time()
        
        self.scheduler.cleanup_old_data()
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # يجب أن يكتمل في وقت معقول
        self.assertLess(execution_time, 10)
        
        # التحقق من حذف الإشعارات القديمة
        remaining_notifications = SystemNotification.objects.filter(
            created_at__lt=timezone.now() - timedelta(days=30)
        )
        
        self.assertEqual(remaining_notifications.count(), 0)
