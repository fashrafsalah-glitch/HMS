# نظام الجدولة للمهام الدورية في CMMS
# هنا بنعمل scheduler يشتغل في الخلفية ويعمل المهام المطلوبة تلقائياً

import logging
from datetime import datetime, timedelta, date
from django.utils import timezone
from django.db import transaction
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.conf import settings

from django.db import models
from .models import Device
from .models import (
    ServiceRequest, WorkOrder, PreventiveMaintenanceSchedule, 
    JobPlan, SLADefinition, SparePart,
    SystemNotification, NotificationQueue, NotificationTemplate
)
from .notifications import NotificationManager

logger = logging.getLogger(__name__)

class CMMSScheduler:
    """
    جدولة المهام الدورية للـ CMMS
    يتولى إنشاء طلبات الصيانة الوقائية وإرسال الإشعارات
    """
    
    def __init__(self):
        self.notification_manager = NotificationManager()
        
    def run_all_scheduled_tasks(self):
        """
        تشغيل جميع المهام المجدولة
        """
        logger.info("بدء تشغيل المهام المجدولة للـ CMMS")
        
        try:
            # إنشاء طلبات الصيانة الوقائية المستحقة
            self.create_due_preventive_maintenance()
            
            # فحص انتهاكات SLA وإرسال تنبيهات
            self.check_sla_violations()
            
            # فحص المعايرات المستحقة
            self.check_due_calibrations()
            
            # فحص قطع الغيار المنخفضة
            self.check_low_stock_spare_parts()
            
            # تحديث حالة أوامر الشغل المتأخرة
            self.update_overdue_work_orders()
            
            # معالجة طابور الإشعارات
            self.process_notification_queue()
            
            # تنظيف البيانات القديمة
            self.cleanup_old_data()
            
            logger.info("انتهاء تشغيل المهام المجدولة بنجاح")
            
        except Exception as e:
            logger.error(f"خطأ في تشغيل المهام المجدولة: {str(e)}")
            
    def create_due_preventive_maintenance(self):
        """
        إنشاء طلبات الصيانة الوقائية المستحقة
        """
        logger.info("فحص الصيانة الوقائية المستحقة")
        
        today = date.today()
        due_schedules = PreventiveMaintenanceSchedule.objects.filter(
            status='active',
            next_due_date__lte=today
        ).select_related('device', 'job_plan', 'created_by')
        
        created_count = 0
        
        for schedule in due_schedules:
            try:
                with transaction.atomic():
                    # التحقق من عدم وجود طلب خدمة مفتوح للجهاز
                    existing_request = ServiceRequest.objects.filter(
                        device=schedule.device,
                        request_type='preventive',
                        status__in=['new', 'assigned', 'in_progress']
                    ).exists()
                    
                    if existing_request:
                        logger.info(f"يوجد طلب صيانة وقائية مفتوح للجهاز {schedule.device.name}")
                        continue
                    
                    # إنشاء طلب خدمة جديد
                    service_request = ServiceRequest.objects.create(
                        title=f"صيانة وقائية - {schedule.device.name}",
                        description=f"صيانة وقائية مجدولة للجهاز {schedule.device.name}",
                        device=schedule.device,
                        request_type='preventive',
                        priority='medium',
                        requested_by=schedule.created_by or self._get_system_user(),
                        assigned_to=schedule.created_by,
                        is_auto_generated=True
                    )
                    
                    # تحديد SLA المناسب
                    sla = self._get_appropriate_sla(schedule.device, 'preventive', 'medium')
                    if sla:
                        service_request.sla = sla
                        service_request.response_due = timezone.now() + timedelta(hours=sla.response_time_hours)
                        service_request.resolution_due = timezone.now() + timedelta(hours=sla.resolution_time_hours)
                        service_request.save()
                    
                    # إنشاء أمر شغل
                    work_order = WorkOrder.objects.create(
                        service_request=service_request,
                        assignee=schedule.created_by,
                        job_plan=schedule.job_plan
                    )
                    
                    # تحديث جدول الصيانة الوقائية
                    schedule.last_completed_date = today
                    schedule.next_due_date = self._calculate_next_due_date(schedule)
                    schedule.save()
                    
                    # إرسال إشعار
                    self.notification_manager.send_pm_due_notification(
                        schedule.device,
                        schedule.created_by or self._get_system_user(),
                        schedule.next_due_date
                    )
                    
                    created_count += 1
                    logger.info(f"تم إنشاء طلب صيانة وقائية للجهاز {schedule.device.name}")
                    
            except Exception as e:
                logger.error(f"خطأ في إنشاء طلب صيانة وقائية للجهاز {schedule.device.name}: {str(e)}")
        
        logger.info(f"تم إنشاء {created_count} طلب صيانة وقائية")
        
    def check_sla_violations(self):
        """
        فحص انتهاكات SLA وإرسال تنبيهات
        """
        logger.info("فحص انتهاكات SLA")
        
        now = timezone.now()
        
        # فحص انتهاكات وقت الاستجابة
        response_violations = ServiceRequest.objects.filter(
            status__in=['new', 'assigned'],
            response_due__lt=now,
            sla__isnull=False
        ).select_related('device', 'requested_by', 'assigned_to', 'sla')
        
        for request in response_violations:
            self.notification_manager.send_sla_violation_notification(
                request, 'response'
            )
            
        # فحص انتهاكات وقت الحل
        resolution_violations = ServiceRequest.objects.filter(
            status__in=['new', 'assigned', 'in_progress'],
            resolution_due__lt=now,
            sla__isnull=False
        ).select_related('device', 'requested_by', 'assigned_to', 'sla')
        
        for request in resolution_violations:
            self.notification_manager.send_sla_violation_notification(
                request, 'resolution'
            )
            
        logger.info(f"تم فحص {response_violations.count()} انتهاك استجابة و {resolution_violations.count()} انتهاك حل")
        
    def check_due_calibrations(self):
        """
        فحص المعايرات المستحقة
        """
        logger.info("فحص المعايرات المستحقة")
        
        today = date.today()
        warning_date = today + timedelta(days=30)  # تحذير قبل 30 يوم
        
        # الأجهزة التي تحتاج معايرة خلال 30 يوم
        devices_needing_calibration = Device.objects.filter(
            calibrations__next_calibration_date__lte=warning_date,
            calibrations__next_calibration_date__gte=today
        ).distinct()
        
        for device in devices_needing_calibration:
            latest_calibration = device.calibrations.filter(
                next_calibration_date__lte=warning_date
            ).order_by('-calibration_date').first()
            
            if latest_calibration:
                # البحث عن مسؤول الصيانة للجهاز
                responsible_user = self._get_device_responsible_user(device)
                
                self.notification_manager.send_calibration_due_notification(
                    device,
                    responsible_user,
                    latest_calibration.next_calibration_date
                )
                
        logger.info(f"تم فحص {devices_needing_calibration.count()} جهاز يحتاج معايرة")
        
    def check_low_stock_spare_parts(self):
        """
        فحص قطع الغيار المنخفضة أو المنتهية
        """
        logger.info("فحص قطع الغيار المنخفضة")
        
        # قطع الغيار المنخفضة
        low_stock_parts = SparePart.objects.filter(
            quantity__lte=models.F('minimum_stock'),
            quantity__gt=0
        )
        
        # قطع الغيار المنتهية
        out_of_stock_parts = SparePart.objects.filter(quantity=0)
        
        # إرسال إشعارات للمسؤولين
        maintenance_managers = self._get_maintenance_managers()
        
        for part in low_stock_parts:
            for manager in maintenance_managers:
                self.notification_manager.send_spare_parts_low_notification(
                    part, manager
                )
                
        for part in out_of_stock_parts:
            for manager in maintenance_managers:
                self.notification_manager.send_spare_parts_out_notification(
                    part, manager
                )
                
        logger.info(f"تم فحص {low_stock_parts.count()} قطعة منخفضة و {out_of_stock_parts.count()} قطعة منتهية")
        
    def update_overdue_work_orders(self):
        """
        تحديث حالة أوامر الشغل المتأخرة
        """
        logger.info("تحديث أوامر الشغل المتأخرة")
        
        now = timezone.now()
        
        # أوامر الشغل المتأخرة
        overdue_orders = WorkOrder.objects.filter(
            status__in=['new', 'assigned', 'in_progress'],
            service_request__resolution_due__lt=now
        ).select_related('service_request', 'assignee')
        
        for order in overdue_orders:
            # إرسال تذكير للفني المعين
            if order.assignee:
                self.notification_manager.send_work_order_overdue_notification(
                    order, order.assignee
                )
                
        logger.info(f"تم فحص {overdue_orders.count()} أمر شغل متأخر")
        
    def process_notification_queue(self):
        """
        معالجة طابور الإشعارات المؤجلة
        """
        logger.info("معالجة طابور الإشعارات")
        
        now = timezone.now()
        
        # الإشعارات المجدولة للإرسال
        pending_notifications = NotificationQueue.objects.filter(
            status='pending',
            scheduled_at__lte=now
        ).order_by('priority', 'created_at')[:50]  # معالجة 50 إشعار في المرة
        
        processed_count = 0
        
        for notification in pending_notifications:
            try:
                notification.status = 'processing'
                notification.save()
                
                if notification.notification_type == 'email':
                    # إرسال إيميل
                    success = self.notification_manager._send_email(
                        notification.recipient_email,
                        notification.subject,
                        notification.message
                    )
                elif notification.notification_type == 'system':
                    # إنشاء إشعار نظام
                    SystemNotification.objects.create(
                        user=notification.recipient_user,
                        title=notification.subject,
                        message=notification.message,
                        notification_type='info'
                    )
                    success = True
                else:
                    success = False
                    
                if success:
                    notification.status = 'sent'
                    notification.sent_at = now
                else:
                    notification.status = 'failed'
                    notification.attempts += 1
                    
                    # إعادة المحاولة إذا لم نصل للحد الأقصى
                    if notification.attempts < notification.max_attempts:
                        notification.status = 'pending'
                        notification.scheduled_at = now + timedelta(minutes=30)
                        
                notification.save()
                processed_count += 1
                
            except Exception as e:
                logger.error(f"خطأ في معالجة الإشعار {notification.id}: {str(e)}")
                notification.status = 'failed'
                notification.error_message = str(e)
                notification.attempts += 1
                notification.save()
                
        logger.info(f"تم معالجة {processed_count} إشعار")
        
    def cleanup_old_data(self):
        """
        تنظيف البيانات القديمة
        """
        logger.info("تنظيف البيانات القديمة")
        
        # حذف الإشعارات المقروءة الأقدم من 30 يوم
        old_notifications = SystemNotification.objects.filter(
            is_read=True,
            created_at__lt=timezone.now() - timedelta(days=30)
        )
        deleted_notifications = old_notifications.count()
        old_notifications.delete()
        
        # حذف سجلات الإيميل الأقدم من 90 يوم
        from .models_notifications import EmailNotificationLog
        old_email_logs = EmailNotificationLog.objects.filter(
            created_at__lt=timezone.now() - timedelta(days=90)
        )
        deleted_emails = old_email_logs.count()
        old_email_logs.delete()
        
        # حذف الإشعارات المرسلة من الطابور الأقدم من 7 أيام
        old_queue_items = NotificationQueue.objects.filter(
            status='sent',
            sent_at__lt=timezone.now() - timedelta(days=7)
        )
        deleted_queue = old_queue_items.count()
        old_queue_items.delete()
        
        logger.info(f"تم حذف {deleted_notifications} إشعار و {deleted_emails} سجل إيميل و {deleted_queue} عنصر من الطابور")
        
    def _calculate_next_due_date(self, schedule):
        """
        حساب تاريخ الاستحقاق التالي للصيانة الوقائية
        """
        if schedule.frequency == 'daily':
            return schedule.last_completed_date + timedelta(days=1)
        elif schedule.frequency == 'weekly':
            return schedule.last_completed_date + timedelta(weeks=1)
        elif schedule.frequency == 'monthly':
            return schedule.last_completed_date + timedelta(days=30)
        elif schedule.frequency == 'quarterly':
            return schedule.last_completed_date + timedelta(days=90)
        elif schedule.frequency == 'semi_annual':
            return schedule.last_completed_date + timedelta(days=180)
        elif schedule.frequency == 'annual':
            return schedule.last_completed_date + timedelta(days=365)
        elif schedule.frequency == 'custom' and schedule.frequency_value:
            return schedule.last_completed_date + timedelta(days=schedule.frequency_value)
        else:
            return schedule.last_completed_date + timedelta(days=30)  # افتراضي شهري
            
    def _get_appropriate_sla(self, device, request_type, priority):
        """
        الحصول على SLA المناسب للجهاز ونوع الطلب
        """
        try:
            sla_matrix = SLAMatrix.objects.get(
                device_category=device.category,
                request_type=request_type,
                priority=priority
            )
            return sla_matrix.sla
        except SLAMatrix.DoesNotExist:
            # البحث عن SLA افتراضي
            return SLA.objects.filter(is_active=True).first()
            
    def _get_system_user(self):
        """
        الحصول على مستخدم النظام للعمليات التلقائية
        """
        try:
            return User.objects.get(username='system')
        except User.DoesNotExist:
            return User.objects.filter(is_superuser=True).first()
            
    def _get_device_responsible_user(self, device):
        """
        الحصول على المسؤول عن الجهاز
        """
        # يمكن تطوير هذه الدالة لتحديد المسؤول بناءً على القسم أو نوع الجهاز
        return self._get_system_user()
        
    def _get_maintenance_managers(self):
        """
        الحصول على مدراء الصيانة
        """
        from django.contrib.auth.models import Group
        try:
            maintenance_group = Group.objects.get(name='CMMS_Admin')
            return maintenance_group.user_set.all()
        except Group.DoesNotExist:
            return User.objects.filter(is_superuser=True)


class SchedulerCommand(BaseCommand):
    """
    أمر Django لتشغيل المهام المجدولة
    يمكن تشغيله من cron job أو task scheduler
    """
    help = 'تشغيل المهام المجدولة للـ CMMS'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--task',
            type=str,
            help='تشغيل مهمة محددة (pm, sla, calibration, spare_parts, cleanup)',
        )
        
    def handle(self, *args, **options):
        scheduler = CMMSScheduler()
        
        task = options.get('task')
        
        if task == 'pm':
            scheduler.create_due_preventive_maintenance()
        elif task == 'sla':
            scheduler.check_sla_violations()
        elif task == 'calibration':
            scheduler.check_due_calibrations()
        elif task == 'spare_parts':
            scheduler.check_low_stock_spare_parts()
        elif task == 'cleanup':
            scheduler.cleanup_old_data()
        else:
            # تشغيل جميع المهام
            scheduler.run_all_scheduled_tasks()
            
        self.stdout.write(
            self.style.SUCCESS('تم تشغيل المهام المجدولة بنجاح')
        )
