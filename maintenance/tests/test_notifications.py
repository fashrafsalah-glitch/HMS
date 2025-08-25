# اختبارات نظام الإشعارات للـ CMMS
# هنا بنختبر إرسال الإشعارات والقوالب والتفضيلات

from django.test import TestCase
from django.contrib.auth.models import User
from django.core import mail
from django.utils import timezone
from unittest.mock import patch, MagicMock
from datetime import date, timedelta

from maintenance.models import Device
from maintenance.models_cmms import ServiceRequest, WorkOrder
from maintenance.models_spare_parts import SparePart, Supplier
from maintenance.models_notifications import (
    SystemNotification, EmailNotificationLog, 
    NotificationPreference, NotificationTemplate, NotificationQueue
)
from maintenance.notifications import NotificationManager


class NotificationManagerTest(TestCase):
    """اختبارات مدير الإشعارات"""
    
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
        
        self.service_request = ServiceRequest.objects.create(
            title='طلب اختبار',
            description='وصف الطلب',
            device=self.device,
            requested_by=self.user
        )
        
        self.notification_manager = NotificationManager()
        
        # إنشاء تفضيلات الإشعارات
        NotificationPreference.objects.create(
            user=self.user,
            sla_violations_email=True,
            sla_violations_system=True
        )
        
    def test_send_system_notification(self):
        """اختبار إرسال إشعار النظام"""
        self.notification_manager.send_system_notification(
            user=self.user,
            title='إشعار اختبار',
            message='رسالة الإشعار',
            notification_type='info'
        )
        
        # التحقق من إنشاء الإشعار
        notification = SystemNotification.objects.get(user=self.user)
        self.assertEqual(notification.title, 'إشعار اختبار')
        self.assertEqual(notification.message, 'رسالة الإشعار')
        self.assertEqual(notification.notification_type, 'info')
        self.assertFalse(notification.is_read)
        
    @patch('maintenance.notifications.send_mail')
    def test_send_email_notification(self, mock_send_mail):
        """اختبار إرسال إشعار الإيميل"""
        mock_send_mail.return_value = True
        
        result = self.notification_manager._send_email(
            recipient_email='test@example.com',
            subject='موضوع الاختبار',
            message='رسالة الاختبار'
        )
        
        self.assertTrue(result)
        mock_send_mail.assert_called_once()
        
        # التحقق من تسجيل الإيميل
        email_log = EmailNotificationLog.objects.get(recipient_email='test@example.com')
        self.assertEqual(email_log.subject, 'موضوع الاختبار')
        self.assertEqual(email_log.status, 'sent')
        
    @patch('maintenance.notifications.send_mail')
    def test_send_email_notification_failure(self, mock_send_mail):
        """اختبار فشل إرسال إشعار الإيميل"""
        mock_send_mail.side_effect = Exception('فشل الإرسال')
        
        result = self.notification_manager._send_email(
            recipient_email='test@example.com',
            subject='موضوع الاختبار',
            message='رسالة الاختبار'
        )
        
        self.assertFalse(result)
        
        # التحقق من تسجيل الفشل
        email_log = EmailNotificationLog.objects.get(recipient_email='test@example.com')
        self.assertEqual(email_log.status, 'failed')
        self.assertIn('فشل الإرسال', email_log.error_message)
        
    def test_sla_violation_notification(self):
        """اختبار إشعار انتهاك SLA"""
        self.notification_manager.send_sla_violation_notification(
            service_request=self.service_request,
            violation_type='response'
        )
        
        # التحقق من إنشاء الإشعار
        notification = SystemNotification.objects.get(user=self.user)
        self.assertIn('انتهاك SLA', notification.title)
        self.assertIn('جهاز اختبار', notification.message)
        
    def test_work_order_assignment_notification(self):
        """اختبار إشعار تعيين أمر شغل"""
        work_order = WorkOrder.objects.create(
            service_request=self.service_request,
            assigned_technician=self.user
        )
        
        self.notification_manager.send_work_order_assigned_notification(
            work_order=work_order,
            technician=self.user
        )
        
        # التحقق من إنشاء الإشعار
        notification = SystemNotification.objects.get(user=self.user)
        self.assertIn('أمر شغل جديد', notification.title)
        
    def test_spare_parts_low_notification(self):
        """اختبار إشعار قطع الغيار المنخفضة"""
        supplier = Supplier.objects.create(name='مورد اختبار')
        spare_part = SparePart.objects.create(
            name='قطعة اختبار',
            part_number='TEST001',
            supplier=supplier,
            quantity=2,
            minimum_stock=5
        )
        
        self.notification_manager.send_spare_parts_low_notification(
            spare_part=spare_part,
            user=self.user
        )
        
        # التحقق من إنشاء الإشعار
        notification = SystemNotification.objects.get(user=self.user)
        self.assertIn('مخزون منخفض', notification.title)
        self.assertIn('قطعة اختبار', notification.message)


class NotificationTemplateTest(TestCase):
    """اختبارات قوالب الإشعارات"""
    
    def setUp(self):
        """إعداد البيانات للاختبار"""
        self.template = NotificationTemplate.objects.create(
            name='قالب اختبار',
            subject='إشعار {device_name}',
            email_template='الجهاز: {device_name}\nالحالة: {status}',
            system_template='تحديث حالة {device_name}: {status}',
            notification_type='device_status'
        )
        
    def test_template_rendering(self):
        """اختبار عرض القالب"""
        context = {
            'device_name': 'جهاز اختبار',
            'status': 'خارج الخدمة'
        }
        
        rendered_subject = self.template.subject.format(**context)
        rendered_email = self.template.email_template.format(**context)
        rendered_system = self.template.system_template.format(**context)
        
        self.assertEqual(rendered_subject, 'إشعار جهاز اختبار')
        self.assertIn('جهاز اختبار', rendered_email)
        self.assertIn('خارج الخدمة', rendered_email)
        self.assertEqual(rendered_system, 'تحديث حالة جهاز اختبار: خارج الخدمة')
        
    def test_template_validation(self):
        """اختبار التحقق من صحة القالب"""
        # قالب بنوع إشعار غير صحيح
        with self.assertRaises(Exception):
            NotificationTemplate.objects.create(
                name='قالب خاطئ',
                subject='موضوع',
                email_template='قالب إيميل',
                system_template='قالب نظام',
                notification_type='invalid_type'
            )


class NotificationPreferenceTest(TestCase):
    """اختبارات تفضيلات الإشعارات"""
    
    def setUp(self):
        """إعداد البيانات للاختبار"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
    def test_default_preferences(self):
        """اختبار التفضيلات الافتراضية"""
        preferences = NotificationPreference.objects.create(user=self.user)
        
        # يجب أن تكون جميع الإشعارات مفعلة افتراضياً
        self.assertTrue(preferences.sla_violations_email)
        self.assertTrue(preferences.sla_violations_system)
        self.assertTrue(preferences.pm_due_email)
        self.assertTrue(preferences.pm_due_system)
        
    def test_custom_preferences(self):
        """اختبار التفضيلات المخصصة"""
        preferences = NotificationPreference.objects.create(
            user=self.user,
            sla_violations_email=False,
            pm_due_system=False,
            spare_parts_email=True
        )
        
        self.assertFalse(preferences.sla_violations_email)
        self.assertFalse(preferences.pm_due_system)
        self.assertTrue(preferences.spare_parts_email)
        
    def test_user_preference_check(self):
        """اختبار فحص تفضيلات المستخدم"""
        preferences = NotificationPreference.objects.create(
            user=self.user,
            sla_violations_email=False,
            sla_violations_system=True
        )
        
        notification_manager = NotificationManager()
        
        # يجب ألا يرسل إيميل لأن التفضيل معطل
        should_send_email = preferences.sla_violations_email
        self.assertFalse(should_send_email)
        
        # يجب أن يرسل إشعار نظام لأن التفضيل مفعل
        should_send_system = preferences.sla_violations_system
        self.assertTrue(should_send_system)


class NotificationQueueTest(TestCase):
    """اختبارات طابور الإشعارات"""
    
    def setUp(self):
        """إعداد البيانات للاختبار"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
    def test_queue_notification(self):
        """اختبار إضافة إشعار للطابور"""
        notification = NotificationQueue.objects.create(
            notification_type='email',
            recipient_user=self.user,
            recipient_email='test@example.com',
            subject='إشعار مؤجل',
            message='رسالة الإشعار المؤجل',
            priority='high',
            scheduled_at=timezone.now() + timedelta(minutes=30)
        )
        
        self.assertEqual(notification.status, 'pending')
        self.assertEqual(notification.priority, 'high')
        self.assertEqual(notification.attempts, 0)
        
    def test_queue_processing_order(self):
        """اختبار ترتيب معالجة الطابور"""
        # إنشاء إشعارات بأولويات مختلفة
        high_priority = NotificationQueue.objects.create(
            notification_type='email',
            recipient_user=self.user,
            recipient_email='test@example.com',
            subject='إشعار عاجل',
            message='رسالة عاجلة',
            priority='urgent',
            scheduled_at=timezone.now()
        )
        
        low_priority = NotificationQueue.objects.create(
            notification_type='email',
            recipient_user=self.user,
            recipient_email='test@example.com',
            subject='إشعار عادي',
            message='رسالة عادية',
            priority='low',
            scheduled_at=timezone.now()
        )
        
        # يجب أن يأتي الإشعار العاجل أولاً
        notifications = NotificationQueue.objects.filter(
            status='pending'
        ).order_by('priority', 'created_at')
        
        self.assertEqual(notifications.first().priority, 'urgent')
        
    def test_queue_retry_mechanism(self):
        """اختبار آلية إعادة المحاولة"""
        notification = NotificationQueue.objects.create(
            notification_type='email',
            recipient_user=self.user,
            recipient_email='test@example.com',
            subject='إشعار للاختبار',
            message='رسالة الاختبار',
            max_attempts=3
        )
        
        # محاكاة فشل الإرسال
        notification.status = 'failed'
        notification.attempts = 1
        notification.save()
        
        # يجب أن يكون قابل لإعادة المحاولة
        can_retry = notification.attempts < notification.max_attempts
        self.assertTrue(can_retry)
        
        # محاكاة الوصول للحد الأقصى
        notification.attempts = 3
        notification.save()
        
        can_retry = notification.attempts < notification.max_attempts
        self.assertFalse(can_retry)


class NotificationIntegrationTest(TestCase):
    """اختبارات التكامل للإشعارات"""
    
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
        
        # إنشاء قالب إشعار
        self.template = NotificationTemplate.objects.create(
            name='قالب SLA',
            subject='انتهاك SLA - {device_name}',
            email_template='تم انتهاك SLA للجهاز: {device_name}',
            system_template='انتهاك SLA: {device_name}',
            notification_type='sla_violation'
        )
        
        self.notification_manager = NotificationManager()
        
    @patch('maintenance.notifications.send_mail')
    def test_end_to_end_notification_flow(self, mock_send_mail):
        """اختبار التدفق الكامل للإشعارات"""
        mock_send_mail.return_value = True
        
        # إنشاء طلب خدمة
        service_request = ServiceRequest.objects.create(
            title='طلب اختبار',
            description='وصف الطلب',
            device=self.device,
            requested_by=self.user
        )
        
        # إرسال إشعار انتهاك SLA
        self.notification_manager.send_sla_violation_notification(
            service_request=service_request,
            violation_type='response'
        )
        
        # التحقق من إنشاء إشعار النظام
        system_notification = SystemNotification.objects.filter(user=self.user).first()
        self.assertIsNotNone(system_notification)
        self.assertIn('انتهاك SLA', system_notification.title)
        
        # التحقق من محاولة إرسال الإيميل
        email_log = EmailNotificationLog.objects.filter(
            recipient_email=self.user.email
        ).first()
        self.assertIsNotNone(email_log)
        
    def test_notification_with_preferences(self):
        """اختبار الإشعارات مع التفضيلات"""
        # إنشاء تفضيلات تعطل إشعارات الإيميل
        NotificationPreference.objects.create(
            user=self.user,
            sla_violations_email=False,
            sla_violations_system=True
        )
        
        service_request = ServiceRequest.objects.create(
            title='طلب اختبار',
            description='وصف الطلب',
            device=self.device,
            requested_by=self.user
        )
        
        self.notification_manager.send_sla_violation_notification(
            service_request=service_request,
            violation_type='response'
        )
        
        # يجب أن يتم إنشاء إشعار النظام فقط
        system_notifications = SystemNotification.objects.filter(user=self.user)
        self.assertEqual(system_notifications.count(), 1)
        
        # يجب ألا يتم إرسال إيميل
        email_logs = EmailNotificationLog.objects.filter(
            recipient_email=self.user.email
        )
        self.assertEqual(email_logs.count(), 0)
        
    def test_bulk_notification_sending(self):
        """اختبار إرسال إشعارات متعددة"""
        # إنشاء مستخدمين إضافيين
        users = []
        for i in range(5):
            user = User.objects.create_user(
                username=f'user{i}',
                email=f'user{i}@example.com',
                password='testpass123'
            )
            users.append(user)
            
        # إرسال إشعار لجميع المستخدمين
        for user in users:
            self.notification_manager.send_system_notification(
                user=user,
                title='إشعار جماعي',
                message='رسالة للجميع',
                notification_type='info'
            )
            
        # التحقق من إنشاء جميع الإشعارات
        notifications = SystemNotification.objects.filter(title='إشعار جماعي')
        self.assertEqual(notifications.count(), 5)
        
    def test_notification_cleanup(self):
        """اختبار تنظيف الإشعارات القديمة"""
        # إنشاء إشعارات قديمة
        old_date = timezone.now() - timedelta(days=35)
        
        SystemNotification.objects.create(
            user=self.user,
            title='إشعار قديم',
            message='رسالة قديمة',
            is_read=True,
            created_at=old_date,
            read_at=old_date + timedelta(days=1)
        )
        
        # إنشاء إشعار حديث
        SystemNotification.objects.create(
            user=self.user,
            title='إشعار حديث',
            message='رسالة حديثة',
            is_read=True
        )
        
        # تنظيف الإشعارات القديمة (أقدم من 30 يوم)
        cutoff_date = timezone.now() - timedelta(days=30)
        old_notifications = SystemNotification.objects.filter(
            is_read=True,
            created_at__lt=cutoff_date
        )
        
        self.assertEqual(old_notifications.count(), 1)
        
        # حذف الإشعارات القديمة
        deleted_count = old_notifications.count()
        old_notifications.delete()
        
        # التحقق من بقاء الإشعار الحديث
        remaining_notifications = SystemNotification.objects.filter(user=self.user)
        self.assertEqual(remaining_notifications.count(), 1)
        self.assertEqual(remaining_notifications.first().title, 'إشعار حديث')
