# هنا بنعمل نظام الإشعارات للـ CMMS عشان نبعت تنبيهات للمستخدمين عن SLA والصيانة
from django.core.mail import send_mail
from django.contrib.auth.models import User
from django.utils import timezone
from django.template.loader import render_to_string
from django.conf import settings
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

class NotificationManager:
    """
    مدير الإشعارات الرئيسي
    هنا بنتحكم في كل أنواع الإشعارات في النظام
    """
    
    @staticmethod
    def send_email_notification(subject, message, recipient_list, html_message=None):
        """
        إرسال إشعار بالإيميل
        """
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=recipient_list,
                html_message=html_message,
                fail_silently=False
            )
            logger.info(f"تم إرسال إيميل إلى: {recipient_list}")
            return True
        except Exception as e:
            logger.error(f"فشل في إرسال الإيميل: {str(e)}")
            return False
    
    @staticmethod
    def create_system_notification(user, title, message, notification_type='info', url=None):
        """
        إنشاء إشعار داخلي في النظام
        """
        from .models import SystemNotification
        
        try:
            notification = SystemNotification.objects.create(
                user=user,
                title=title,
                message=message,
                notification_type=notification_type,
                url=url
            )
            logger.info(f"تم إنشاء إشعار نظام للمستخدم: {user.username}")
            return notification
        except Exception as e:
            logger.error(f"فشل في إنشاء إشعار النظام: {str(e)}")
            return None
    
    @staticmethod
    def notify_sla_violation(service_request):
        """
        إشعار بانتهاك SLA
        """
        from .models import ServiceRequest
        
        # إشعار طالب الخدمة
        if service_request.requested_by:
            NotificationManager.create_system_notification(
                user=service_request.requested_by,
                title=f"تأخير في طلب الخدمة: {service_request.title}",
                message=f"طلب الخدمة الخاص بالجهاز {service_request.device.name} تأخر عن الموعد المحدد",
                notification_type='warning',
                url=f'/maintenance/service-request/{service_request.id}/'
            )
        
        # إشعار الفني المعين
        if service_request.assigned_to:
            NotificationManager.create_system_notification(
                user=service_request.assigned_to,
                title=f"طلب خدمة متأخر: {service_request.title}",
                message=f"طلب الخدمة المعين إليك تأخر عن موعد الـ SLA",
                notification_type='error',
                url=f'/maintenance/service-request/{service_request.id}/'
            )
            
            # إرسال إيميل للفني
            if service_request.assigned_to.email:
                subject = f"تنبيه: طلب خدمة متأخر - {service_request.title}"
                message = f"""
                مرحباً {service_request.assigned_to.get_full_name()},
                
                طلب الخدمة التالي تأخر عن الموعد المحدد:
                - العنوان: {service_request.title}
                - الجهاز: {service_request.device.name}
                - تاريخ الاستحقاق: {service_request.resolution_due}
                
                يرجى المتابعة فوراً.
                """
                
                NotificationManager.send_email_notification(
                    subject=subject,
                    message=message,
                    recipient_list=[service_request.assigned_to.email]
                )
        
        # إشعار المشرفين
        supervisors = User.objects.filter(groups__name='Supervisor')
        for supervisor in supervisors:
            NotificationManager.create_system_notification(
                user=supervisor,
                title=f"انتهاك SLA: {service_request.title}",
                message=f"طلب خدمة تأخر عن موعد الـ SLA - الجهاز: {service_request.device.name}",
                notification_type='error',
                url=f'/maintenance/service-request/{service_request.id}/'
            )
    
    @staticmethod
    def notify_preventive_maintenance_due(pm_schedule):
        """
        إشعار باستحقاق صيانة وقائية
        """
        # إشعار الفني المعين
        if pm_schedule.assigned_technician:
            NotificationManager.create_system_notification(
                user=pm_schedule.assigned_technician,
                title=f"صيانة وقائية مستحقة: {pm_schedule.device.name}",
                message=f"الجهاز {pm_schedule.device.name} يحتاج صيانة وقائية",
                notification_type='info',
                url=f'/maintenance/pm-schedule/{pm_schedule.id}/'
            )
            
            # إرسال إيميل
            if pm_schedule.assigned_technician.email:
                subject = f"تذكير: صيانة وقائية مستحقة - {pm_schedule.device.name}"
                message = f"""
                مرحباً {pm_schedule.assigned_technician.get_full_name()},
                
                الجهاز التالي يحتاج صيانة وقائية:
                - الجهاز: {pm_schedule.device.name}
                - القسم: {pm_schedule.device.department.name if hasattr(pm_schedule.device, 'department') else 'غير محدد'}
                - تاريخ الاستحقاق: {pm_schedule.next_due_date}
                - خطة العمل: {pm_schedule.job_plan.name if pm_schedule.job_plan else 'غير محددة'}
                
                يرجى جدولة الصيانة في أقرب وقت ممكن.
                """
                
                NotificationManager.send_email_notification(
                    subject=subject,
                    message=message,
                    recipient_list=[pm_schedule.assigned_technician.email]
                )
    
    @staticmethod
    def notify_calibration_due(device):
        """
        إشعار باستحقاق معايرة
        """
        # البحث عن الفنيين المختصين بالمعايرة
        calibration_technicians = User.objects.filter(
            groups__name__in=['Technician', 'Supervisor']
        )
        
        for technician in calibration_technicians:
            NotificationManager.create_system_notification(
                user=technician,
                title=f"معايرة مستحقة: {device.name}",
                message=f"الجهاز {device.name} يحتاج معايرة",
                notification_type='warning',
                url=f'/maintenance/device/{device.id}/'
            )
    
    @staticmethod
    def notify_spare_part_low_stock(spare_part):
        """
        إشعار بانخفاض مخزون قطعة غيار
        """
        # إشعار مديري المخازن والمشرفين
        managers = User.objects.filter(
            groups__name__in=['Supervisor', 'Admin']
        )
        
        for manager in managers:
            NotificationManager.create_system_notification(
                user=manager,
                title=f"مخزون منخفض: {spare_part.name}",
                message=f"قطعة الغيار {spare_part.name} وصلت للحد الأدنى من المخزون",
                notification_type='warning',
                url=f'/maintenance/spare-part/{spare_part.id}/'
            )
    
    @staticmethod
    def notify_spare_part_out_of_stock(spare_part):
        """
        إشعار بنفاد مخزون قطعة غيار
        """
        # إشعار مديري المخازن والمشرفين
        managers = User.objects.filter(
            groups__name__in=['Supervisor', 'Admin']
        )
        
        for manager in managers:
            NotificationManager.create_system_notification(
                user=manager,
                title=f"مخزون منتهي: {spare_part.name}",
                message=f"قطعة الغيار {spare_part.name} نفدت من المخزون",
                notification_type='error',
                url=f'/maintenance/spare-part/{spare_part.id}/'
            )
            
            # إرسال إيميل للحالات الحرجة
            if manager.email:
                subject = f"تنبيه عاجل: نفاد مخزون - {spare_part.name}"
                message = f"""
                مرحباً {manager.get_full_name()},
                
                قطعة الغيار التالية نفدت من المخزون:
                - الاسم: {spare_part.name}
                - رقم القطعة: {spare_part.part_number}
                - المورد: {spare_part.supplier.name if spare_part.supplier else 'غير محدد'}
                
                يرجى إعادة الطلب فوراً.
                """
                
                NotificationManager.send_email_notification(
                    subject=subject,
                    message=message,
                    recipient_list=[manager.email]
                )
    
    @staticmethod
    def notify_work_order_assigned(work_order):
        """
        إشعار بتعيين أمر شغل
        """
        if work_order.assigned_technician:
            NotificationManager.create_system_notification(
                user=work_order.assigned_technician,
                title=f"أمر شغل جديد: {work_order.service_request.title}",
                message=f"تم تعيين أمر شغل جديد لك - الجهاز: {work_order.service_request.device.name}",
                notification_type='info',
                url=f'/maintenance/work-order/{work_order.id}/'
            )
    
    @staticmethod
    def notify_work_order_completed(work_order):
        """
        إشعار بإكمال أمر شغل
        """
        # إشعار طالب الخدمة
        if work_order.service_request.requested_by:
            NotificationManager.create_system_notification(
                user=work_order.service_request.requested_by,
                title=f"تم إكمال الصيانة: {work_order.service_request.title}",
                message=f"تم إكمال صيانة الجهاز {work_order.service_request.device.name}",
                notification_type='success',
                url=f'/maintenance/work-order/{work_order.id}/'
            )
        
        # إشعار المشرف
        if work_order.supervisor:
            NotificationManager.create_system_notification(
                user=work_order.supervisor,
                title=f"أمر شغل مكتمل: {work_order.service_request.title}",
                message=f"تم إكمال أمر الشغل - يحتاج مراجعة",
                notification_type='info',
                url=f'/maintenance/work-order/{work_order.id}/'
            )
    
    @staticmethod
    def notify_device_out_of_service(device):
        """
        إشعار بخروج جهاز من الخدمة
        """
        # إشعار قسم الجهاز
        if hasattr(device, 'department') and device.department:
            department_users = User.objects.filter(
                # افتراض أن المستخدمين مرتبطين بالأقسام
                groups__name__in=['Doctor', 'Nurse']
            )
            
            for user in department_users:
                NotificationManager.create_system_notification(
                    user=user,
                    title=f"جهاز خارج الخدمة: {device.name}",
                    message=f"الجهاز {device.name} أصبح خارج الخدمة",
                    notification_type='error',
                    url=f'/maintenance/device/{device.id}/'
                )
        
        # إشعار فريق الصيانة
        maintenance_team = User.objects.filter(
            groups__name__in=['Technician', 'Supervisor']
        )
        
        for technician in maintenance_team:
            NotificationManager.create_system_notification(
                user=technician,
                title=f"جهاز يحتاج صيانة عاجلة: {device.name}",
                message=f"الجهاز {device.name} خارج الخدمة ويحتاج تدخل فوري",
                notification_type='error',
                url=f'/maintenance/device/{device.id}/'
            )

class NotificationScheduler:
    """
    مجدول الإشعارات
    هنا بنفحص النظام دورياً ونبعت الإشعارات المطلوبة
    """
    
    @staticmethod
    def check_sla_violations():
        """
        فحص انتهاكات SLA
        """
        from .models import ServiceRequest
        
        # البحث عن طلبات الخدمة المتأخرة
        overdue_requests = ServiceRequest.objects.filter(
            status__in=['new', 'assigned', 'in_progress'],
            resolution_due__lt=timezone.now()
        )
        
        for request in overdue_requests:
            # التحقق من عدم إرسال إشعار مسبق
            from .models import SystemNotification
            
            recent_notification = SystemNotification.objects.filter(
                title__icontains=f"تأخير في طلب الخدمة: {request.title}",
                created_at__gte=timezone.now() - timedelta(hours=1)
            ).exists()
            
            if not recent_notification:
                NotificationManager.notify_sla_violation(request)
        
        logger.info(f"تم فحص {overdue_requests.count()} طلب خدمة متأخر")
    
    @staticmethod
    def check_preventive_maintenance():
        """
        فحص الصيانة الوقائية المستحقة
        """
        from .models import PreventiveMaintenanceSchedule
        
        # البحث عن جداول الصيانة المستحقة خلال الأسبوع القادم
        due_schedules = PreventiveMaintenanceSchedule.objects.filter(
            status='active',
            next_due_date__lte=timezone.now().date() + timedelta(days=7),
            next_due_date__gte=timezone.now().date()
        )
        
        for schedule in due_schedules:
            # التحقق من عدم إرسال إشعار مسبق
            from .models import SystemNotification
            
            recent_notification = SystemNotification.objects.filter(
                title__icontains=f"صيانة وقائية مستحقة: {schedule.device.name}",
                created_at__gte=timezone.now() - timedelta(days=1)
            ).exists()
            
            if not recent_notification:
                NotificationManager.notify_preventive_maintenance_due(schedule)
        
        logger.info(f"تم فحص {due_schedules.count()} جدول صيانة وقائية")
    
    @staticmethod
    def check_calibration_due():
        """
        فحص المعايرة المستحقة
        """
        # Calibration model not yet implemented
        from .models import Device
        
        # البحث عن الأجهزة التي تحتاج معايرة
        devices_need_calibration = Device.objects.filter(
            calibration_records__next_calibration_date__lte=timezone.now().date() + timedelta(days=7),
            calibration_records__status='completed'
        ).distinct()
        
        for device in devices_need_calibration:
            # التحقق من عدم إرسال إشعار مسبق
            from .models import SystemNotification
            
            recent_notification = SystemNotification.objects.filter(
                title__icontains=f"معايرة مستحقة: {device.name}",
                created_at__gte=timezone.now() - timedelta(days=1)
            ).exists()
            
            if not recent_notification:
                NotificationManager.notify_calibration_due(device)
        
        logger.info(f"تم فحص {devices_need_calibration.count()} جهاز يحتاج معايرة")
    
    @staticmethod
    def check_spare_parts_stock():
        """
        فحص مخزون قطع الغيار
        """
        from .models import SparePart
        
        # قطع الغيار بمخزون منخفض
        low_stock_parts = SparePart.objects.filter(status='low_stock')
        
        for part in low_stock_parts:
            # التحقق من عدم إرسال إشعار مسبق
            from .models import SystemNotification
            
            recent_notification = SystemNotification.objects.filter(
                title__icontains=f"مخزون منخفض: {part.name}",
                created_at__gte=timezone.now() - timedelta(days=1)
            ).exists()
            
            if not recent_notification:
                NotificationManager.notify_spare_part_low_stock(part)
        
        # قطع الغيار المنتهية
        out_of_stock_parts = SparePart.objects.filter(status='out_of_stock')
        
        for part in out_of_stock_parts:
            # التحقق من عدم إرسال إشعار مسبق
            from .models import SystemNotification
            
            recent_notification = SystemNotification.objects.filter(
                title__icontains=f"مخزون منتهي: {part.name}",
                created_at__gte=timezone.now() - timedelta(hours=6)
            ).exists()
            
            if not recent_notification:
                NotificationManager.notify_spare_part_out_of_stock(part)
        
        logger.info(f"تم فحص {low_stock_parts.count()} قطعة غيار منخفضة و {out_of_stock_parts.count()} قطعة منتهية")
    
    @staticmethod
    def run_all_checks():
        """
        تشغيل جميع الفحوصات
        """
        logger.info("بدء فحص الإشعارات الدورية")
        
        try:
            NotificationScheduler.check_sla_violations()
            NotificationScheduler.check_preventive_maintenance()
            NotificationScheduler.check_calibration_due()
            NotificationScheduler.check_spare_parts_stock()
            
            logger.info("تم إكمال فحص الإشعارات الدورية بنجاح")
        except Exception as e:
            logger.error(f"خطأ في فحص الإشعارات: {str(e)}")

# دوال مساعدة للاستخدام في الـ Views والـ Signals
def send_sla_violation_alert(service_request):
    """دالة مساعدة لإرسال تنبيه انتهاك SLA"""
    NotificationManager.notify_sla_violation(service_request)

def send_pm_due_alert(pm_schedule):
    """دالة مساعدة لإرسال تنبيه صيانة وقائية"""
    NotificationManager.notify_preventive_maintenance_due(pm_schedule)

def send_work_order_notification(work_order, action):
    """دالة مساعدة لإرسال إشعارات أوامر الشغل"""
    if action == 'assigned':
        NotificationManager.notify_work_order_assigned(work_order)
    elif action == 'completed':
        NotificationManager.notify_work_order_completed(work_order)

def send_device_status_alert(device):
    """دالة مساعدة لإرسال تنبيه حالة الجهاز"""
    if device.status == 'out_of_service':
        NotificationManager.notify_device_out_of_service(device)

def send_spare_part_alert(spare_part):
    """دالة مساعدة لإرسال تنبيه قطع الغيار"""
    if spare_part.status == 'low_stock':
        NotificationManager.notify_spare_part_low_stock(spare_part)
    elif spare_part.status == 'out_of_stock':
        NotificationManager.notify_spare_part_out_of_stock(spare_part)
