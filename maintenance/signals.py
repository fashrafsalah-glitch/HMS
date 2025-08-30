from django.db.models.signals import post_save
from django.dispatch import receiver
from django.apps import apps
from core.qr_utils import QRCodeMixin


@receiver(post_save)
def generate_qr_code_on_save(sender, instance, created, **kwargs):
    """
    Auto-generate QR codes for models that inherit from QRCodeMixin
    """
    # Only process instances that inherit from QRCodeMixin
    if isinstance(instance, QRCodeMixin):
        # Only generate if it's a new instance or QR code doesn't exist
        if created or not instance.qr_token or not instance.qr_code:
            try:
                # Generate QR token and code
                if not instance.qr_token:
                    instance.qr_token = instance.generate_qr_token()
                
                # Generate QR code image
                if not instance.qr_code:
                    instance.generate_qr_code()
                    # Save without triggering signals again
                    instance.save(update_fields=['qr_code', 'qr_token'])
                    
            except Exception as e:
                print(f"Error generating QR code for {instance}: {e}")


# Specific signal handlers for each model
from manager.models import Patient, Bed
from hr.models import CustomUser
from maintenance.models import *


@receiver(post_save, sender=Patient)
def generate_patient_qr_code(sender, instance, created, **kwargs):
    """Generate QR code for patients with special format"""
    if created or not instance.qr_token:
        try:
            instance.qr_token = instance.generate_qr_token()
            instance.generate_qr_code()
            # Use update to avoid triggering signals again
            Patient.objects.filter(pk=instance.pk).update(
                qr_token=instance.qr_token
            )
            instance.save(update_fields=['qr_code'])
        except Exception as e:
            print(f"Error generating Patient QR code: {e}")


@receiver(post_save, sender=Bed)
def generate_bed_qr_code(sender, instance, created, **kwargs):
    """Generate QR code for beds"""
    if created or not instance.qr_token:
        try:
            instance.qr_token = instance.generate_qr_token()
            instance.generate_qr_code()
            Bed.objects.filter(pk=instance.pk).update(
                qr_token=instance.qr_token
            )
            instance.save(update_fields=['qr_code'])
        except Exception as e:
            print(f"Error generating Bed QR code: {e}")


@receiver(post_save, sender=CustomUser)
def generate_user_qr_code(sender, instance, created, **kwargs):
    """Generate QR code for users (doctors, nurses, staff)"""
    if created or not instance.qr_token:
        try:
            instance.qr_token = instance.generate_qr_token()
            instance.generate_qr_code()
            CustomUser.objects.filter(pk=instance.pk).update(
                qr_token=instance.qr_token
            )
            instance.save(update_fields=['qr_code'])
        except Exception as e:
            print(f"Error generating User QR code: {e}")


@receiver(post_save, sender=DeviceAccessory)
def generate_accessory_qr_code(sender, instance, created, **kwargs):
    """Generate QR code for device accessories"""
    if created or not instance.qr_token:
        try:
            instance.qr_token = instance.generate_qr_token()
            instance.generate_qr_code()
            DeviceAccessory.objects.filter(pk=instance.pk).update(
                qr_token=instance.qr_token
            )
            instance.save(update_fields=['qr_code'])
        except Exception as e:
            print(f"Error generating DeviceAccessory QR code: {e}")


# ═══════════════════════════════════════════════════════════════
# CMMS SIGNALS - التحويل التلقائي للبلاغات وأوامر الشغل
# ═══════════════════════════════════════════════════════════════

from datetime import date
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# AUTOMATIC PM WORK ORDER GENERATION - إنشاء أوامر الصيانة الوقائية تلقائياً
# ═══════════════════════════════════════════════════════════════

@receiver(post_save, sender=PreventiveMaintenanceSchedule)
def setup_pm_schedule_automation(sender, instance, created, **kwargs):
    """
    إعداد الجدولة التلقائية للصيانة الوقائية عند إنشاء جدول جديد
    لا ينشئ أوامر شغل فوراً - فقط يعد الجدول للفحص التلقائي
    """
    if created:
        try:
            # تعيين تاريخ الاستحقاق التالي إذا لم يكن محدداً
            if not instance.next_due_date:
                if instance.start_date:
                    instance.next_due_date = instance.start_date
                else:
                    instance.next_due_date = date.today()
                instance.save(update_fields=['next_due_date'])
            
            logger.info(f"تم إعداد جدول الصيانة الوقائية {instance.id} - الموعد التالي: {instance.next_due_date}")
            logger.info(f"سيتم إنشاء أمر الشغل تلقائياً في تاريخ الاستحقاق: {instance.next_due_date}")
            
        except Exception as e:
            logger.error(f"خطأ في إعداد جدول الصيانة الوقائية {instance.id}: {str(e)}")


def check_and_generate_pm_work_orders():
    """
    فحص وإنشاء أوامر الصيانة الوقائية المستحقة
    يتم استدعاء هذه الدالة تلقائياً كل ساعة
    """
    try:
        today = date.today()
        
        # إضافة logs للتشخيص
        total_schedules = PreventiveMaintenanceSchedule.objects.count()
        active_schedules = PreventiveMaintenanceSchedule.objects.filter(is_active=True).count()
        
        logger.info(f"إجمالي جداول الصيانة: {total_schedules}")
        logger.info(f"جداول الصيانة النشطة: {active_schedules}")
        
        # البحث عن جداول الصيانة المستحقة (فقط التي موعدها اليوم أو قبل اليوم)
        due_schedules = PreventiveMaintenanceSchedule.objects.filter(
            is_active=True,
            next_due_date__lte=today
        ).select_related('device', 'job_plan', 'created_by', 'assigned_to')
        
        logger.info(f"جداول الصيانة المستحقة اليوم ({today}): {due_schedules.count()}")
        
        # طباعة تفاصيل الجداول للتشخيص
        for schedule in due_schedules:
            logger.info(f"جدول مستحق: {schedule.device.name} - تاريخ الاستحقاق: {schedule.next_due_date}")
        
        created_count = 0
        
        for schedule in due_schedules:
            try:
                # التحقق من عدم وجود بلاغ صيانة وقائية مفتوح للجهاز
                existing_request = ServiceRequest.objects.filter(
                    device=schedule.device,
                    request_type='preventive',
                    status__in=['new', 'assigned', 'in_progress']
                ).exists()
                
                if existing_request:
                    logger.info(f"يوجد بلاغ صيانة وقائية مفتوح للجهاز {schedule.device.name} - تم التجاهل")
                    continue
                
                # إنشاء بلاغ الصيانة الوقائية
                service_request = ServiceRequest.objects.create(
                    device=schedule.device,
                    reporter=schedule.created_by,
                    title=f"صيانة وقائية - {schedule.device.name}",
                    description=f"صيانة وقائية مجدولة للجهاز {schedule.device.name} - {schedule.job_plan.name if schedule.job_plan else 'صيانة عامة'}",
                    request_type='preventive',
                    priority='medium',
                    status='new',
                    assigned_to=schedule.assigned_to,
                    estimated_hours=schedule.job_plan.estimated_hours if schedule.job_plan else 2.0
                )
                
                # إنشاء أمر الشغل (سيتم إنشاؤه تلقائياً بواسطة signal البلاغ)
                # لكن نتأكد من إنشاؤه يدوياً للتحكم الكامل
                wo = WorkOrder.objects.create(
                    service_request=service_request,
                    title=f"صيانة وقائية - {schedule.device.name}",
                    description=f"صيانة وقائية مجدولة للجهاز {schedule.device.name} حسب الخطة {schedule.job_plan.name}",
                    assignee=schedule.assignee,
                    priority='medium',
                    wo_type='preventive',
                    status='new',
                    created_by=service_request.created_by
                )
                
                # تحديث جدول الصيانة
                schedule.last_completed_date = today
                schedule.next_due_date = schedule.calculate_next_due_date()
                schedule.save(update_fields=['last_completed_date', 'next_due_date'])
                
                created_count += 1
                
                logger.info(f"تم إنشاء أمر صيانة وقائية {wo.wo_number} للجهاز {schedule.device.name}")
                
            except Exception as e:
                logger.error(f"خطأ في إنشاء أمر الصيانة الوقائية للجدول {schedule.id}: {str(e)}")
                continue
        
        if created_count > 0:
            logger.info(f"تم إنشاء {created_count} أمر صيانة وقائية جديد")
        
        return created_count
        
    except Exception as e:
        logger.error(f"خطأ عام في فحص الصيانة الوقائية: {str(e)}")
        return 0


@receiver(post_save, sender=ServiceRequest)
def auto_create_work_order(sender, instance, created, **kwargs):
    """
    التحويل التلقائي للبلاغ إلى أمر شغل
    هنا بنشوف لو البلاغ محتاج أمر شغل ونعمله تلقائياً
    """
    if created and instance.status == 'new':
        try:
            # التحقق من عدم وجود أمر شغل مسبق
            if not instance.work_orders.exists():
                
                # تحديد SLA المناسب من المصفوفة
                sla_definition = None
                try:
                    sla_matrix = SLAMatrix.objects.get(
                        device_category=instance.device.category,
                        severity=instance.severity,
                        impact=instance.impact,
                        priority=instance.priority,
                        is_active=True
                    )
                    sla_definition = sla_matrix.sla_definition
                except SLAMatrix.DoesNotExist:
                    # البحث عن SLA افتراضي
                    from .models import SLADefinition
                    sla_definition = SLADefinition.objects.filter(is_active=True).first()
                
                # تحديث البلاغ بمعلومات SLA
                if sla_definition:
                    instance.response_due = timezone.now() + timedelta(hours=sla_definition.response_time_hours)
                    instance.resolution_due = timezone.now() + timedelta(hours=sla_definition.resolution_time_hours)
                    instance.save(update_fields=['response_due', 'resolution_due'])
                
                # إنشاء أمر الشغل تلقائياً
                work_order = WorkOrder.objects.create(
                    service_request=instance,
                    title=f"أمر شغل - {instance.title}",
                    description=instance.description,
                    wo_type='corrective' if instance.request_type == 'breakdown' else 'preventive',
                    priority=instance.priority,
                    created_by=instance.reporter,
                    assignee=instance.assigned_to,
                    estimated_hours=instance.estimated_hours
                )
                
                # تحديث حالة البلاغ
                instance.status = 'assigned' if instance.assigned_to else 'new'
                instance.save(update_fields=['status'])
                
                logger.info(f"تم إنشاء أمر شغل تلقائي {work_order.wo_number} للبلاغ {instance.id}")
                
        except Exception as e:
            logger.error(f"خطأ في إنشاء أمر الشغل التلقائي للبلاغ {instance.id}: {str(e)}")


@receiver(post_save, sender=WorkOrder)
def update_service_request_status(sender, instance, created, **kwargs):
    """
    تحديث حالة البلاغ عند تغيير حالة أمر الشغل
    هنا بنخلي البلاغ يتابع حالة أمر الشغل
    """
    if not created:  # فقط عند التحديث، مش عند الإنشاء
        try:
            service_request = instance.service_request
            
            # ربط حالات أمر الشغل بحالات البلاغ
            status_mapping = {
                'new': 'new',
                'assigned': 'assigned', 
                'in_progress': 'in_progress',
                'wait_parts': 'in_progress',
                'on_hold': 'in_progress',
                'resolved': 'resolved',
                'qa_verified': 'resolved',
                'closed': 'closed',
                'cancelled': 'cancelled'
            }
            
            new_sr_status = status_mapping.get(instance.status, service_request.status)
            
            if service_request.status != new_sr_status:
                service_request.status = new_sr_status
                
                # تحديث تواريخ الحل والإغلاق
                if new_sr_status == 'resolved' and not service_request.resolved_at:
                    service_request.resolved_at = timezone.now()
                elif new_sr_status == 'closed' and not service_request.closed_at:
                    service_request.closed_at = timezone.now()
                
                service_request.save(update_fields=['status', 'resolved_at', 'closed_at'])
                
                logger.info(f"تم تحديث حالة البلاغ {service_request.id} إلى {new_sr_status}")
                
        except Exception as e:
            logger.error(f"خطأ في تحديث حالة البلاغ لأمر الشغل {instance.id}: {str(e)}")


@receiver(post_save, sender=DeviceUsageLog)
def auto_create_maintenance_request(sender, instance, created, **kwargs):
    """
    إنشاء بلاغ صيانة تلقائي عند اكتشاف مشاكل في التفقد اليومي
    هنا لو الفني لاقى مشكلة في الجهاز، بنعمل بلاغ تلقائي
    """
    if created and instance.maintenance_needed and instance.issues_found:
        try:
            # التحقق من عدم وجود بلاغ مفتوح للجهاز
            existing_request = ServiceRequest.objects.filter(
                device=instance.device,
                status__in=['new', 'assigned', 'in_progress'],
                request_type='breakdown'
            ).exists()
            
            if not existing_request:
                # تحديد درجة الخطورة حسب حالة التشغيل
                severity_mapping = {
                    'working': 'low',
                    'minor_issues': 'medium', 
                    'major_issues': 'high',
                    'not_working': 'critical'
                }
                
                severity = severity_mapping.get(instance.operational_status, 'medium')
                
                # إنشاء البلاغ التلقائي
                service_request = ServiceRequest.objects.create(
                    title=f"مشكلة مكتشفة في التفقد اليومي - {instance.device.name}",
                    description=f"تم اكتشاف المشاكل التالية أثناء التفقد اليومي:\n{instance.issues_found}",
                    device=instance.device,
                    request_type='breakdown',
                    severity=severity,
                    impact='moderate' if severity in ['low', 'medium'] else 'high',
                    priority='medium' if severity in ['low', 'medium'] else 'high',
                    reporter=instance.checked_by,
                    estimated_hours=2.0 if severity == 'low' else 4.0
                )
                
                logger.info(f"تم إنشاء بلاغ تلقائي {service_request.id} من التفقد اليومي للجهاز {instance.device.name}")
                
        except Exception as e:
            logger.error(f"خطأ في إنشاء بلاغ تلقائي من التفقد اليومي: {str(e)}")


@receiver(post_save, sender=DowntimeEvent)
def auto_create_downtime_request(sender, instance, created, **kwargs):
    """
    إنشاء بلاغ تلقائي عند بداية توقف الجهاز
    هنا لو الجهاز توقف، بنعمل بلاغ عاجل تلقائي
    """
    if created and instance.downtime_type in ['unplanned', 'emergency']:
        try:
            # التحقق من عدم وجود بلاغ مرتبط
            if not instance.related_work_order:
                
                # تحديد الأولوية حسب نوع التوقف
                priority = 'critical' if instance.downtime_type == 'emergency' else 'high'
                
                # إنشاء البلاغ التلقائي
                service_request = ServiceRequest.objects.create(
                    title=f"توقف الجهاز - {instance.device.name}",
                    description=f"توقف الجهاز عن العمل:\nالسبب: {instance.reason}\nالتأثير: {instance.impact_description}",
                    device=instance.device,
                    request_type='breakdown',
                    severity='critical',
                    impact='high',
                    priority=priority,
                    reporter=instance.reported_by,
                    estimated_hours=6.0 if priority == 'critical' else 4.0
                )
                
                # ربط حدث التوقف بأمر الشغل الذي سيتم إنشاؤه
                # (سيتم إنشاؤه تلقائياً بواسطة signal البلاغ)
                work_orders = service_request.work_orders.all()
                if work_orders.exists():
                    instance.related_work_order = work_orders.first()
                    instance.save(update_fields=['related_work_order'])
                
                logger.info(f"تم إنشاء بلاغ توقف تلقائي {service_request.id} للجهاز {instance.device.name}")
                
        except Exception as e:
            logger.error(f"خطأ في إنشاء بلاغ توقف تلقائي: {str(e)}")


# Signal لتحديث حالة الجهاز عند بداية ونهاية التوقف
@receiver(post_save, sender=DowntimeEvent)
def update_device_status_on_downtime(sender, instance, created, **kwargs):
    """
    تحديث حالة الجهاز عند بداية أو نهاية التوقف
    هنا بنخلي حالة الجهاز تتغير لما يتوقف أو يرجع يشتغل
    """
    try:
        device = instance.device
        
        if created and instance.end_time is None:
            # بداية التوقف - تحديث حالة الجهاز
            device.status = 'out_of_order'
            device.availability = False
            device.save(update_fields=['status', 'availability'])
            
            logger.info(f"تم تحديث حالة الجهاز {device.name} إلى خارج الخدمة")
            
        elif not created and instance.end_time and instance.is_ongoing() == False:
            # نهاية التوقف - إعادة تشغيل الجهاز
            device.status = 'needs_check'  # يحتاج فحص قبل العودة للخدمة
            device.availability = True
            device.save(update_fields=['status', 'availability'])
            
            logger.info(f"تم إنهاء توقف الجهاز {device.name} - يحتاج فحص")
            
    except Exception as e:
        logger.error(f"خطأ في تحديث حالة الجهاز عند التوقف: {str(e)}")
