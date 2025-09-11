from django.db.models.signals import post_save
from django.dispatch import receiver
from django.apps import apps
from core.qr_utils import QRCodeMixin
from manager.models import Patient, Bed
from hr.models import CustomUser
from maintenance.models import *

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

from datetime import date, timedelta
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
                
                # إنشاء أمر الشغل تلقائياً مع المواعيد المجدولة
                work_order = WorkOrder.objects.create(
                    service_request=instance,
                    title=f"أمر شغل - {instance.title}",
                    description=instance.description,
                    wo_type='corrective' if instance.request_type == 'breakdown' else 'preventive',
                    priority=instance.priority,
                    created_by=instance.reporter,
                    assignee=instance.assigned_to,
                    estimated_hours=instance.estimated_hours,
                    # ربط المواعيد المجدولة من أوقات SLA
                    scheduled_start=instance.response_due,  # موعد البدء = موعد الاستجابة المطلوب
                    scheduled_end=instance.resolution_due   # موعد الانتهاء = موعد الحل المطلوب
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
    # Skip for DeviceUsageLog - only for DeviceUsageLogDaily
    if sender.__name__ == 'DeviceUsageLog':
        return
    
    if created and hasattr(instance, 'maintenance_needed') and instance.maintenance_needed and hasattr(instance, 'issues_found') and instance.issues_found:
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


# تم حذف دوال DowntimeEvent لأنها لم تعد مستخدمة
# النظام الآن يستخدم DeviceDowntime مع المراقبة التلقائية في tasks.py


# ═══════════════════════════════════════════════════════════════
# AUTOMATIC SLA MATRIX GENERATION - إنشاء مصفوفة SLA تلقائياً
# ═══════════════════════════════════════════════════════════════

@receiver(post_save, sender=DeviceCategory)
def auto_generate_sla_matrix_for_category(sender, instance, created, **kwargs):
    """
    إنشاء مصفوفة SLA تلقائياً عند إضافة فئة جهاز جديدة
    """
    if created:
        try:
            from .models import SLADefinition, SLAMatrix, SEVERITY_CHOICES, IMPACT_CHOICES, PRIORITY_CHOICES
            
            # الحصول على جميع تعريفات SLA الموجودة (المنشأة يدوياً)
            available_slas = list(SLADefinition.objects.all())
            
            if not available_slas:
                # إنشاء تعريفات SLA الأساسية إذا لم تكن موجودة
                sla_definitions = create_default_sla_definitions()
                available_slas = list(SLADefinition.objects.all())
            
            # إنشاء جميع التركيبات: عدد SLA × 4 severity × 4 impact × 4 priority
            severity_choices = [choice[0] for choice in SEVERITY_CHOICES]
            impact_choices = [choice[0] for choice in IMPACT_CHOICES]
            priority_choices = [choice[0] for choice in PRIORITY_CHOICES]
            
            created_count = 0
            
            # إنشاء مدخل لكل SLA مع كل تركيبة severity + impact بناءً على أولوية SLA
            for sla in available_slas:
                # تحديد الأولوية المرتبطة بهذا SLA
                sla_priority = sla.priority if sla.priority else 'medium'  # افتراضي متوسط
                
                for severity in severity_choices:
                    for impact in impact_choices:
                        # إنشاء مدخل فقط للأولوية المطابقة لأولوية SLA
                        matrix_entry, created_entry = SLAMatrix.objects.get_or_create(
                            device_category=instance,
                            severity=severity,
                            impact=impact,
                            priority=sla_priority,
                            sla_definition=sla
                        )
                        
                        if created_entry:
                            created_count += 1
            
            logger.info(f"تم إنشاء {created_count} مدخل في مصفوفة SLA للفئة الجديدة: {instance.name}")
            
        except Exception as e:
            logger.error(f"خطأ في إنشاء مصفوفة SLA للفئة الجديدة {instance.name}: {str(e)}")


def create_default_sla_definitions():
    """إنشاء تعريفات SLA الافتراضية"""
    from .models import SLADefinition
    
    sla_configs = [
        {
            'name': 'حرج - استجابة فورية',
            'description': 'للأجهزة الحرجة في العناية المركزة',
            'response_time_minutes': 5,
            'resolution_time_hours': 1,
            'escalation_time_minutes': 15,
        },
        {
            'name': 'عالي - استجابة سريعة',
            'description': 'للأجهزة عالية الأولوية',
            'response_time_minutes': 15,
            'resolution_time_hours': 4,
            'escalation_time_minutes': 30,
        },
        {
            'name': 'متوسط - استجابة عادية',
            'description': 'للأجهزة متوسطة الأولوية',
            'response_time_minutes': 60,
            'resolution_time_hours': 24,
            'escalation_time_minutes': 120,
        },
        {
            'name': 'منخفض - استجابة مؤجلة',
            'description': 'للأجهزة منخفضة الأولوية',
            'response_time_minutes': 240,
            'resolution_time_hours': 72,
            'escalation_time_minutes': 480,
        },
    ]
    
    sla_definitions = {}
    
    for config in sla_configs:
        sla_def, created = SLADefinition.objects.get_or_create(
            name=config['name'],
            defaults={
                'description': config['description'],
                'response_time_hours': config['response_time_minutes'] / 60,  # تحويل الدقائق إلى ساعات
                'resolution_time_hours': config['resolution_time_hours'],
                'escalation_time_hours': config['escalation_time_minutes'] / 60,
                'is_active': True,
                'device_category': None,  # SLA عام لجميع الفئات
            }
        )
        sla_definitions[config['name']] = sla_def
        
        if created:
            logger.info(f'تم إنشاء تعريف SLA: {config["name"]}')
    
    return sla_definitions


@receiver(post_save, sender=SLADefinition)
def auto_update_existing_matrix_entries(sender, instance, created, **kwargs):
    """
    تحديث مدخلات المصفوفة الموجودة عند تحديث تعريف SLA
    """
    if not created:  # فقط عند التحديث
        try:
            from .models import SLAMatrix
            
            # تحديث جميع مدخلات المصفوفة التي تستخدم هذا التعريف
            updated_count = SLAMatrix.objects.filter(sla_definition=instance).count()
            
            if updated_count > 0:
                logger.info(f"تم تحديث {updated_count} مدخل في مصفوفة SLA بعد تحديث التعريف: {instance.name}")
                
        except Exception as e:
            logger.error(f"خطأ في تحديث مدخلات المصفوفة بعد تحديث التعريف {instance.name}: {str(e)}")


def generate_sla_matrix_for_existing_categories():
    """
    إنشاء مصفوفة SLA للفئات الموجودة التي لا تحتوي على مصفوفة
    """
    try:
        from .models import DeviceCategory, SLADefinition, SLAMatrix, SEVERITY_CHOICES, IMPACT_CHOICES
        
        # الحصول على جميع تعريفات SLA الموجودة (المنشأة يدوياً)
        available_slas = list(SLADefinition.objects.all())
        
        if not available_slas:
            # إنشاء تعريفات SLA الأساسية إذا لم تكن موجودة
            sla_definitions = create_default_sla_definitions()
            available_slas = list(SLADefinition.objects.all())
        
        # الحصول على الفئات التي لا تحتوي على مصفوفة SLA
        categories_without_matrix = DeviceCategory.objects.filter(
            slamatrix__isnull=True
        ).distinct()
        
        if not categories_without_matrix.exists():
            logger.info("جميع فئات الأجهزة تحتوي على مصفوفة SLA")
            return 0
        
        # إنشاء جميع التركيبات الممكنة: 4 severity × 4 impact × 4 priority مع SLA ثابت لكل تركيبة
        severity_choices = [choice[0] for choice in SEVERITY_CHOICES]
        impact_choices = [choice[0] for choice in IMPACT_CHOICES]
        priority_choices = [choice[0] for choice in PRIORITY_CHOICES]
        
        sla_rules = []
        
        # إنشاء مدخل لكل SLA مع كل تركيبة severity + impact بناءً على أولوية SLA
        for sla in available_slas:
            # تحديد الأولوية المرتبطة بهذا SLA
            sla_priority = sla.priority if sla.priority else 'medium'  # افتراضي متوسط
            
            for severity in severity_choices:
                for impact in impact_choices:
                    # إنشاء مدخل فقط للأولوية المطابقة لأولوية SLA
                    sla_rules.append((severity, impact, sla_priority, sla))
        
        total_created = 0
        
        for category in categories_without_matrix:
            created_count = 0
            
            for severity, impact, priority, sla in sla_rules:
                matrix_entry, created_entry = SLAMatrix.objects.get_or_create(
                    device_category=category,
                    severity=severity,
                    impact=impact,
                    priority=priority,
                    sla_definition=sla
                )
                
                if created_entry:
                    created_count += 1
            
            total_created += created_count
            logger.info(f"تم إنشاء {created_count} مدخل في مصفوفة SLA للفئة: {category.name}")
        
        logger.info(f"تم إنشاء {total_created} مدخل إجمالي في مصفوفة SLA للفئات الموجودة")
        return total_created
        
    except Exception as e:
        logger.error(f"خطأ في إنشاء مصفوفة SLA للفئات الموجودة: {str(e)}")
        return 0
