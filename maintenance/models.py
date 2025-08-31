from django.db import models
from manager.models import Department, Patient, Room

from django.contrib.auth import get_user_model
User = get_user_model()

from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone
from io import BytesIO
import qrcode
import uuid

from manager.models import Bed
from core.qr_utils import QRCodeMixin


# ════════════ ═══════════════════════════════════════════════════════════════
# EXISTING MODELS
# ═══════════════════════════════════════════════════════════════════════════

# نموذج سجل استخدام الجهاز اليومي
class DeviceDailyUsageLog(models.Model):
    device = models.ForeignKey('Device', on_delete=models.CASCADE, related_name='daily_usage_logs_old')
    date = models.DateField(auto_now_add=True)
    total_usage_time = models.DurationField(default=timezone.timedelta)
    
    def __str__(self):
        return f"{self.device.name} - {self.date}"



# نموذج سجل تنظيف الجهاز
class DeviceCleaningLog(models.Model):
    device = models.ForeignKey('Device', on_delete=models.CASCADE, related_name='cleaning_logs')
    cleaned_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    cleaned_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.device.name} - {self.cleaned_at}"

# نموذج سجل تعقيم الجهاز
class DeviceSterilizationLog(models.Model):
    device = models.ForeignKey('Device', on_delete=models.CASCADE, related_name='sterilization_logs')
    sterilized_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    sterilized_at = models.DateTimeField(auto_now_add=True)
    method = models.CharField(max_length=100, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.device.name} - {self.sterilized_at}"

# نموذج سجل صيانة الجهاز
class DeviceMaintenanceLog(models.Model):
    device = models.ForeignKey('Device', on_delete=models.CASCADE, related_name='maintenance_logs')
    maintained_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    maintained_at = models.DateTimeField(auto_now_add=True)
    maintenance_type = models.CharField(max_length=50, choices=[
        ('preventive', 'صيانة وقائية'),
        ('corrective', 'صيانة تصحيحية'),
        ('calibration', 'معايرة'),
        ('inspection', 'فحص'),
    ], default='preventive')
    description = models.TextField(blank=True, null=True)
    parts_replaced = models.TextField(blank=True, null=True)
    cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    next_maintenance_date = models.DateField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.device.name} - {self.maintenance_type} - {self.maintained_at}"

# CMMS Models
# نموذج طلب الخدمة
class ServiceRequest(models.Model):
    STATUS_CHOICES = [
        ('new', 'جديد'),
        ('assigned', 'تم التعيين'),
        ('in_progress', 'قيد التنفيذ'),
        ('on_hold', 'معلق'),
        ('completed', 'مكتمل'),
        ('cancelled', 'ملغي'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'منخفض'),
        ('medium', 'متوسط'),
        ('high', 'عالي'),
        ('critical', 'حرج'),
    ]
    
    request_number = models.CharField(max_length=20, unique=True, default='')
    title = models.CharField(max_length=200, default='')
    description = models.TextField(blank=True, null=True)
    device = models.ForeignKey('Device', on_delete=models.CASCADE, related_name='service_requests')
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='service_requests')
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_service_requests')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    due_date = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.request_number} - {self.title}"

# WorkOrder model moved below - removing duplicate

# نموذج خطة العمل
class JobPlan(models.Model):
    name = models.CharField(max_length=200, default='')
    description = models.TextField(blank=True, null=True)
    device_type = models.ForeignKey('DeviceType', on_delete=models.CASCADE, related_name='job_plans')
    estimated_duration = models.DurationField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name

# نموذج خطوة خطة العمل
class JobPlanStep(models.Model):
    job_plan = models.ForeignKey('JobPlan', on_delete=models.CASCADE, related_name='steps')
    step_number = models.PositiveIntegerField(default=1)
    description = models.TextField(blank=True, null=True)
    estimated_time = models.DurationField(null=True, blank=True)
    tools_required = models.TextField(blank=True, null=True)
    safety_notes = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['step_number']
    
    def __str__(self):
        return f"{self.job_plan.name} - Step {self.step_number}"

# نموذج جدول الصيانة الوقائية
class PreventiveMaintenanceSchedule(models.Model):
    FREQUENCY_CHOICES = [
        ('daily', 'يومي'),
        ('weekly', 'أسبوعي'),
        ('monthly', 'شهري'),
        ('quarterly', 'ربع سنوي'),
        ('semi_annual', 'نصف سنوي'),
        ('annual', 'سنوي'),
        ('custom', 'مخصص'),
    ]
    
    device = models.ForeignKey('Device', on_delete=models.CASCADE, related_name='pm_schedules')
    job_plan = models.ForeignKey('JobPlan', on_delete=models.CASCADE)
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES)
    custom_days = models.PositiveIntegerField(null=True, blank=True, help_text='عدد الأيام إذا كان التكرار مخصصًا')
    next_due_date = models.DateField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.device.name} - {self.get_frequency_display()} PM"

# SLADefinition model moved below - removing duplicate

# نموذج المورد - تم نقله إلى قسم Spare Parts Models أدناه

# Old SparePart model removed - using the new comprehensive one below

# نموذج إشعار النظام
class SystemNotification(models.Model):
    TYPE_CHOICES = [
        ('info', 'معلومات'),
        ('warning', 'تحذير'),
        ('alert', 'تنبيه'),
        ('error', 'خطأ'),
    ]
    
    title = models.CharField(max_length=200, default='')
    message = models.TextField(blank=True, null=True)
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='info')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.title} - {self.user.username}"

# نموذج سجل البريد الإلكتروني
class EmailLog(models.Model):
    STATUS_CHOICES = [
        ('pending', 'قيد الانتظار'),
        ('sent', 'تم الإرسال'),
        ('failed', 'فشل'),
    ]
    
    recipient = models.EmailField(default='')
    subject = models.CharField(max_length=200, default='')
    body = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    error_message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.subject} - {self.recipient}"

# نموذج تفضيلات الإشعارات
class NotificationPreference(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notification_preferences')
    email_notifications = models.BooleanField(default=True)
    sms_notifications = models.BooleanField(default=False)
    push_notifications = models.BooleanField(default=True)
    maintenance_due_alerts = models.BooleanField(default=True)
    inventory_alerts = models.BooleanField(default=True)
    work_order_updates = models.BooleanField(default=True)
    
    def __str__(self):
        return f"Preferences for {self.user.username}"

# نموذج قالب الإشعارات
class NotificationTemplate(models.Model):
    name = models.CharField(max_length=100, default='')
    subject = models.CharField(max_length=200, default='')
    body = models.TextField(blank=True, null=True)
    variables = models.TextField(help_text='المتغيرات المتاحة في القالب، مفصولة بفواصل', blank=True, null=True)
    
    def __str__(self):
        return self.name

# نموذج قائمة انتظار الإشعارات
class NotificationQueue(models.Model):
    STATUS_CHOICES = [
        ('pending', 'قيد الانتظار'),
        ('processing', 'قيد المعالجة'),
        ('sent', 'تم الإرسال'),
        ('failed', 'فشل'),
    ]
    
    template = models.ForeignKey('NotificationTemplate', on_delete=models.CASCADE)
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    context_data = models.JSONField(default=dict)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    scheduled_time = models.DateTimeField(null=True, blank=True)
    processed_time = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.template.name} for {self.recipient.username}"

# نموذج المعايرة
class Calibration(models.Model):
    STATUS_CHOICES = [
        ('scheduled', 'مجدول'),
        ('in_progress', 'قيد التنفيذ'),
        ('completed', 'مكتمل'),
        ('failed', 'فشل'),
        ('cancelled', 'ملغي'),
    ]
    
    device = models.ForeignKey('Device', on_delete=models.CASCADE, related_name='device_calibrations')
    scheduled_date = models.DateField(null=True, blank=True)
    performed_date = models.DateField(null=True, blank=True)
    performed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='performed_calibrations')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    results = models.TextField(blank=True, null=True)
    next_calibration_date = models.DateField(null=True, blank=True)
    certificate_number = models.CharField(max_length=100, blank=True, null=True)
    certificate_file = models.FileField(upload_to='calibration_certificates/', null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.device.name} - {self.scheduled_date}"

# نموذج معيار المعايرة
class CalibrationStandard(models.Model):
    name = models.CharField(max_length=200, default='')
    description = models.TextField(blank=True, null=True)
    standard_number = models.CharField(max_length=100, unique=True, default='')
    issuing_body = models.CharField(max_length=200, default='')
    issue_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    document_file = models.FileField(upload_to='calibration_standards/', null=True, blank=True)
    
    def __str__(self):
        return self.name

# نموذج سجل توقف الجهاز عن العمل
class DeviceDowntime(models.Model):
    REASON_CHOICES = [
        ('breakdown', 'عطل'),
        ('maintenance', 'صيانة'),
        ('calibration', 'معايرة'),
        ('power_outage', 'انقطاع التيار'),
        ('operator_error', 'خطأ المشغل'),
        ('scheduled_downtime', 'توقف مجدول'),
        ('other', 'أخرى'),
    ]
    
    device = models.ForeignKey('Device', on_delete=models.CASCADE, related_name='downtimes')
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    reason = models.CharField(max_length=50, choices=REASON_CHOICES, default='other')
    description = models.TextField(blank=True, null=True)
    reported_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='device_reported_downtimes')
    resolved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='device_resolved_downtimes')
    resolution_notes = models.TextField(blank=True, null=True)
    work_order = models.ForeignKey('WorkOrder', on_delete=models.SET_NULL, null=True, blank=True, related_name='downtimes')
    
    def __str__(self):
        return f"{self.device.name} - {self.start_time}"
    
    @property
    def duration(self):
        if self.end_time and self.start_time:
            return self.end_time - self.start_time
        return None

# نموذج تقرير تحليل الأعطال
class FailureAnalysisReport(models.Model):
    device = models.ForeignKey('Device', on_delete=models.CASCADE, related_name='failure_reports')
    downtime = models.ForeignKey('DeviceDowntime', on_delete=models.CASCADE, related_name='analysis_reports')
    analyzed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    analysis_date = models.DateField(null=True, blank=True)
    failure_description = models.TextField(blank=True, null=True)
    root_cause = models.TextField(blank=True, null=True)
    corrective_actions = models.TextField(blank=True, null=True)
    preventive_measures = models.TextField(blank=True, null=True)
    attachments = models.FileField(upload_to='failure_analysis/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.device.name} - {self.analysis_date}"

# شركات
class Company(models.Model):
    name = models.CharField(max_length=255, verbose_name="اسم الشركة", default='')

    def __str__(self):
        return self.name

# نوع الجهاز
class DeviceType(models.Model):
    name = models.CharField(max_length=255, verbose_name="نوع الجهاز", default='')

    def __str__(self):
        return self.name
    
class DeviceUsage(models.Model):
    name = models.CharField(max_length=255, verbose_name="استخدام الجهاز", default='')

    def __str__(self):
        return self.name    




class DeviceTransferRequest(models.Model):
    """Enhanced Device Transfer Request with 3-stage workflow"""
    
    # Status choices for transfer workflow
    STATUS_CHOICES = [
        ('pending', 'معلق - في انتظار الموافقة'),
        ('approved', 'موافق عليه - في انتظار القبول'),
        ('accepted', 'مقبول - تم النقل'),
        ('rejected', 'مرفوض'),
        ('cancelled', 'ملغي'),
    ]
    
    # Transfer reason choices
    REASON_CHOICES = [
        ('patient_need', 'احتياج المريض'),
        ('maintenance', 'للصيانة'),
        ('emergency', 'حالة طارئة'),
        ('routine_transfer', 'نقل روتيني'),
        ('department_request', 'طلب القسم'),
        ('other', 'أخرى'),
    ]
    
    # Device information
    device = models.ForeignKey('Device', on_delete=models.CASCADE, related_name='transfer_requests')
    
    # From location
    from_department = models.ForeignKey(
        Department,
        related_name='device_transfer_requests_from',
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="من القسم"
    )
    from_room = models.ForeignKey(
        'manager.Room', 
        related_name='transfers_from', 
        on_delete=models.SET_NULL, 
        null=True,
        blank=True,
        verbose_name="من الغرفة"
    )
    from_bed = models.ForeignKey(
        'manager.Bed',
        related_name='device_transfer_requests_from',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="من السرير"
    )
    
    # To location
    to_department = models.ForeignKey(
        Department,
        related_name='device_transfer_requests_to',
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="إلى القسم"
    )
    to_room = models.ForeignKey(
        Room, 
        related_name='transfers_to',
        on_delete=models.SET_NULL, 
        null=True,
        blank=True,
        verbose_name="إلى الغرفة"
    )
    to_bed = models.ForeignKey(
        'manager.Bed',
        related_name='device_transfer_requests_to',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="إلى السرير"
    )
    
    # Patient information (if transfer is for specific patient)
    patient = models.ForeignKey(
        'manager.Patient',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='device_transfer_requests',
        verbose_name="المريض"
    )
    
    # Transfer details
    reason = models.CharField(
        max_length=50,
        choices=REASON_CHOICES,
        default='routine_transfer',
        verbose_name="سبب النقل"
    )
    reason_details = models.TextField(
        blank=True,
        null=True,
        verbose_name="تفاصيل السبب"
    )
    priority = models.CharField(
        max_length=20,
        choices=[('low', 'منخفض'), ('normal', 'عادي'), ('high', 'عالي'), ('urgent', 'عاجل')],
        default='normal',
        verbose_name="الأولوية"
    )
    
    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="الحالة"
    )
    
    # Stage 1: Request
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        related_name='transfer_requested_by', 
        on_delete=models.SET_NULL, 
        null=True,
        verbose_name="مقدم الطلب"
    )
    requested_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الطلب")
    
    # Stage 2: Approval (by current department)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        related_name='transfer_approved_by', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name="الموافق"
    )
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name="تاريخ الموافقة")
    approval_notes = models.TextField(blank=True, null=True, verbose_name="ملاحظات الموافقة")
    
    # Stage 3: Acceptance (by receiving department)
    accepted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='transfer_accepted_by',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="القابل"
    )
    accepted_at = models.DateTimeField(null=True, blank=True, verbose_name="تاريخ القبول")
    acceptance_notes = models.TextField(blank=True, null=True, verbose_name="ملاحظات القبول")
    
    # Rejection tracking
    rejected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='transfer_rejected_by',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="الرافض"
    )
    rejected_at = models.DateTimeField(null=True, blank=True, verbose_name="تاريخ الرفض")
    rejection_reason = models.TextField(blank=True, null=True, verbose_name="سبب الرفض")
    
    # Validation flags
    device_checked = models.BooleanField(default=False, verbose_name="تم فحص الجهاز")
    device_cleaned = models.BooleanField(default=False, verbose_name="تم تنظيف الجهاز")
    device_sterilized = models.BooleanField(default=False, verbose_name="تم تعقيم الجهاز")
    
    class Meta:
        verbose_name = "طلب نقل جهاز"
        verbose_name_plural = "طلبات نقل الأجهزة"
        ordering = ['-requested_at']
        indexes = [
            models.Index(fields=['status', 'requested_at']),
            models.Index(fields=['device', 'status']),
            models.Index(fields=['from_department', 'status']),
            models.Index(fields=['to_department', 'status']),
        ]
    
    def __str__(self):
        return f"{self.device.name} - {self.get_status_display()}"
    
    def can_approve(self, user):
        """Check if user can approve this transfer request"""
        # Must be pending and user must be from current department
        if self.status != 'pending':
            return False
        # Check if user is department manager or has permission
        return user.groups.filter(name='Department Managers').exists() or user.is_superuser
    
    def can_accept(self, user):
        """Check if user can accept this transfer request"""
        # Must be approved and user must be from receiving department
        if self.status != 'approved':
            return False
        # Check if user is from receiving department
        return user.groups.filter(name='Department Managers').exists() or user.is_superuser
    
    def approve(self, user, notes=''):
        """Approve the transfer request"""
        self.status = 'approved'
        self.approved_by = user
        self.approved_at = timezone.now()
        self.approval_notes = notes
        self.save()
        # Send notification placeholder
        self.send_notification('approved')
    
    def accept(self, user, notes=''):
        """Accept the transfer and execute it"""
        self.status = 'accepted'
        self.accepted_by = user
        self.accepted_at = timezone.now()
        self.acceptance_notes = notes
        self.save()
        
        # Execute the actual transfer
        self.execute_transfer()
        
        # Send notification placeholder
        self.send_notification('accepted')
    
    def reject(self, user, reason):
        """Reject the transfer request"""
        self.status = 'rejected'
        self.rejected_by = user
        self.rejected_at = timezone.now()
        self.rejection_reason = reason
        self.save()
        # Send notification placeholder
        self.send_notification('rejected')
    
    def execute_transfer(self):
        """Execute the actual device transfer"""
        # Update device location
        self.device.department = self.to_department
        self.device.room = self.to_room
        if self.to_bed:
            self.device.bed = self.to_bed
        if self.patient:
            self.device.current_patient = self.patient
        self.device.save()
        
        # Create transfer log
        DeviceTransferLog.objects.create(
            device=self.device,
            from_department=self.from_department,
            from_room=self.from_room,
            from_bed=self.from_bed,
            to_department=self.to_department,
            to_room=self.to_room,
            to_bed=self.to_bed,
            moved_by=self.accepted_by,
            note=f"Transfer Request #{self.id} - {self.get_reason_display()}"
        )
    
    def send_notification(self, action):
        """Placeholder for sending notifications"""
        # TODO: Implement actual notification system
        pass
    
    def check_device_eligibility(self):
        """Check if device is eligible for transfer"""
        errors = []
        device = self.device
        
        # Check device status
        if hasattr(device, 'status') and device.status != 'working':
            errors.append(f"الجهاز في حالة: {device.get_status_display()} - يجب أن يكون يعمل")
        
        # Check cleanliness
        if hasattr(device, 'clean_status') and device.clean_status != 'clean':
            errors.append("الجهاز يحتاج تنظيف قبل النقل")
        
        # Check sterilization
        if hasattr(device, 'sterilization_status') and device.sterilization_status != 'sterilized':
            errors.append("الجهاز يحتاج تعقيم قبل النقل")
        
        # Check availability
        if hasattr(device, 'availability') and not device.availability:
            errors.append("الجهاز غير متاح حالياً")
        
        # Check if device is in use by a patient
        if hasattr(device, 'current_patient') and device.current_patient:
            if not self.patient or self.patient.id != device.current_patient.id:
                errors.append(f"الجهاز مستخدم حالياً من قبل المريض: {device.current_patient}")
        
        return errors
class DeviceCategory(models.Model):
    name = models.CharField(max_length=100, default='')

    def __str__(self):
        return self.name


class DeviceSubCategory(models.Model):
    name = models.CharField(max_length=100, default='')
    category = models.ForeignKey('DeviceCategory', on_delete=models.CASCADE, related_name='subcategories')

    def __str__(self):
        return f"{self.category.name} - {self.name}"

class Device(QRCodeMixin, models.Model):
    # Device status choices
    DEVICE_STATUS_CHOICES = [
        ('working', 'يعمل'),
        ('needs_maintenance', 'يحتاج صيانة'),
        ('out_of_order', 'عطل دائم'),
        ('needs_check', 'يحتاج تفقد'),
    ]
    
    CLEAN_STATUS_CHOICES = [
        ('clean', 'نظيف'),
        ('needs_cleaning', 'يحتاج تنظيف'),
        ('unknown', 'غير معروف'),
    ]

    STERILIZATION_STATUS_CHOICES = [
        ('sterilized', 'معقم'),
        ('needs_sterilization', 'يحتاج تعقيم'),
        ('not_required', 'لا يحتاج تعقيم'),
    ]

    DEVICE_CLASSIFICATION_CHOICES = [
        ('Airway Support Device', 'Airway Support Device'),
        ('Respiratory Support Device', 'Respiratory Support Device'),
        ('Circulatory Support Device', 'Circulatory Support Device'),
        ('Renal Support Device', 'Renal Support Device'),
        ('Surgical Device', 'Surgical Device'),
        ('Surgical Equipment', 'Surgical Equipment'),
        ('Feeding Device', 'Feeding Device'),
        ('Other', 'Other'),
    ]

    device_classification = models.CharField(
        max_length=50,
        choices=DEVICE_CLASSIFICATION_CHOICES,
        default='Other'
    )

    # Basic Info (Required)
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=200, default='')
    category = models.ForeignKey('DeviceCategory', on_delete=models.CASCADE)
    subcategory = models.ForeignKey('DeviceSubCategory', on_delete=models.SET_NULL, null=True, blank=True)
    brief_description = models.TextField(blank=True, null=True)
    manufacturer = models.CharField(max_length=100, default='')
    model = models.CharField(max_length=100, default='')
    serial_number = models.CharField(max_length=100, default='')
    production_date = models.DateField(null=True, blank=True)

    # Status fields
    status = models.CharField(
        max_length=20,
        choices=DEVICE_STATUS_CHOICES,
        default='working',
        verbose_name="حالة الجهاز"
    )
    clean_status = models.CharField(
        max_length=20,
        choices=CLEAN_STATUS_CHOICES,
        default='unknown',
        verbose_name="حالة النظافة"
    )
    sterilization_status = models.CharField(
        max_length=20,
        choices=STERILIZATION_STATUS_CHOICES,
        default='not_required',
        verbose_name="حالة التعقيم"
    )
    availability = models.BooleanField(default=True, verbose_name="هل متاح؟")
    in_use = models.BooleanField(default=False, verbose_name="قيد الاستخدام؟")
    usage_start_time = models.DateTimeField(null=True, blank=True, verbose_name="بداية الاستخدام")

    # Maintenance tracking
    last_cleaned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='devices_cleaned'
    )
    last_cleaned_at = models.DateTimeField(null=True, blank=True)
    last_sterilized_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='devices_sterilized'
    )
    last_sterilized_at = models.DateTimeField(null=True, blank=True)
    last_maintained_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='devices_maintained'
    )
    last_maintained_at = models.DateTimeField(null=True, blank=True)

    # Company relationships
    manufacture_company = models.ForeignKey(
        Company,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='manufactured_devices',
        verbose_name="شركة التصنيع"
    )
    supplier_company = models.ForeignKey(
        Company,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='supplied_devices',
        verbose_name="شركة التوريد"
    )
    maintenance_company = models.ForeignKey(
        Company,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='maintained_devices',
        verbose_name="شركة الصيانة"
    )
    device_type = models.ForeignKey(
        DeviceType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="نوع الجهاز"
    )
    device_usage = models.ForeignKey(
        DeviceUsage,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="استخدام الجهاز"
    )

    # Location
    department = models.ForeignKey(
        'manager.Department',
        on_delete=models.CASCADE,
        related_name='devices'
    )
    room = models.ForeignKey(
        'manager.Room',
        on_delete=models.CASCADE,
        related_name='devices'
    )
    bed = models.ForeignKey(
        'manager.Bed',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    current_patient = models.ForeignKey(
        'manager.Patient',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="المريض الحالي"
    )

    # Optional Details
    technical_specifications = models.TextField(blank=True, null=True)
    classification = models.CharField(max_length=100, blank=True, null=True)
    uses = models.TextField(blank=True, null=True)
    complications_risks = models.TextField(blank=True, null=True)
    half_life = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإضافة")

    def end_usage(self):
        self.in_use = False
        self.current_patient = None
        self.usage_start_time = None
        self.availability = True
        self.clean_status = 'needs_cleaning'
        self.sterilization_status = 'needs_sterilization'
        self.status = 'needs_check'
        self.save()

    def __str__(self):
        return f"{self.id} - {self.model}"
    


# DeviceCleaningLog model removed - duplicate definition exists above

# DeviceSterilizationLog model removed - duplicate definition exists above

# DeviceMaintenanceLog model removed - duplicate definition exists above

# ═══════════════════════════════════════════════════════════════════════════
# QR/BARCODE INTEGRATION MODELS
# ═══════════════════════════════════════════════════════════════════════════

class DeviceUsageLog(models.Model):
    """Log for tracking device usage sessions via QR scanning"""
    OPERATION_CHOICES = [
        ('surgery', 'عملية جراحية'),
        ('transfer', 'نقل'),
        ('assignment', 'تخصيص'),
        ('maintenance', 'صيانة'),
        ('cleaning', 'تنظيف'),
        ('sterilization', 'تعقيم'),
        ('inspection', 'فحص'),
        ('procedure', 'إجراء طبي'),
        ('training', 'تدريب'),
        ('research', 'بحث'),
        ('other', 'أخرى'),
    ]
    
    USAGE_STATUS_CHOICES = [
        ('active', 'نشط'),
        ('completed', 'مكتمل'),
        ('cancelled', 'ملغي'),
        ('paused', 'متوقف مؤقتًا'),
    ]
    
    # Session info
    session_id = models.UUIDField(default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="المستخدم")

    
    # Context
    patient = models.ForeignKey(
        Patient,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="المريض"
    )
    bed = models.ForeignKey(
        Bed,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="السرير"
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="القسم"
    )
    room = models.ForeignKey(
        Room,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="الغرفة"
    )
    
    # Operation details
    operation_type = models.CharField(
        max_length=20,
        choices=OPERATION_CHOICES,
        default='other',
        verbose_name="نوع العملية"
    )
    procedure_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="اسم الإجراء"
    )
    notes = models.TextField(blank=True, null=True, verbose_name="ملاحظات")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="وقت الإنشاء")
    started_at = models.DateTimeField(null=True, blank=True, verbose_name="وقت البدء")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="وقت الإكمال")
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=USAGE_STATUS_CHOICES,
        default='active',
        verbose_name="الحالة"
    )
    is_completed = models.BooleanField(default=False, verbose_name="مكتملة؟")
    
    # Additional tracking
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_usage_logs',
        verbose_name="أنشئ بواسطة"
    )
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='completed_usage_logs',
        verbose_name="أكمل بواسطة"
    )
    
    class Meta:
        verbose_name = "سجل استخدام الأجهزة"
        verbose_name_plural = "سجلات استخدام الأجهزة"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Session {self.session_id} - {self.user.get_full_name()} - {self.get_operation_type_display()}"
        
    @property
    def duration(self):
        """حساب مدة الاستخدام بالساعات"""
        if self.completed_at and self.started_at:
            return (self.completed_at - self.started_at).total_seconds() / 3600
        return None


class DeviceUsageLogItem(models.Model):
    """Individual devices/accessories used in a session"""
    USAGE_STATUS_CHOICES = [
        ('in_use', 'قيد الاستخدام'),
        ('completed', 'تم الاستخدام'),
        ('cancelled', 'تم الإلغاء'),
        ('paused', 'متوقف مؤقتًا'),
    ]
    
    usage_log = models.ForeignKey(
        'DeviceUsageLog',
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name="سجل الاستخدام"
    )
    device = models.ForeignKey(
        Device,
        on_delete=models.CASCADE,
        verbose_name="الجهاز"
    )
    accessory = models.ForeignKey(
        'DeviceAccessory',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='usage_log_items',
        verbose_name="ملحق الجهاز"
    )
    
    # Timestamps
    scanned_at = models.DateTimeField(auto_now_add=True, verbose_name="وقت المسح")
    usage_start = models.DateTimeField(null=True, blank=True, verbose_name="وقت بدء الاستخدام")
    usage_end = models.DateTimeField(null=True, blank=True, verbose_name="وقت انتهاء الاستخدام")
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=USAGE_STATUS_CHOICES,
        default='in_use',
        verbose_name="حالة الاستخدام"
    )
    
    # Usage details
    used_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='device_usages',
        verbose_name="المستخدم"
    )
    notes = models.TextField(blank=True, null=True, verbose_name="ملاحظات")
    issues_reported = models.TextField(blank=True, null=True, verbose_name="مشاكل مبلغ عنها")
    
    class Meta:
        verbose_name = "عنصر سجل استخدام الجهاز"
        verbose_name_plural = "عناصر سجل استخدام الأجهزة"
        unique_together = ['usage_log', 'device']
        ordering = ['-scanned_at']
    
    def __str__(self):
        return f"{self.device} في {self.usage_log}"
    
    @property
    def duration_minutes(self):
        """حساب مدة استخدام الجهاز بالدقائق"""
        if self.usage_end and self.usage_start:
            return (self.usage_end - self.usage_start).total_seconds() / 60
        return None


class ScanSession(models.Model):
    """Active scanning session"""
    STATUS_CHOICES = [
        ('active', 'نشطة'),
        ('completed', 'مكتملة'),
        ('cancelled', 'ملغاة'),
    ]
    
    session_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="المستخدم"
    )
    patient = models.ForeignKey(
        Patient,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="المريض"
    )
    bed = models.ForeignKey(
        Bed,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="السرير"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active',
        verbose_name="الحالة"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "جلسة مسح"
        verbose_name_plural = "جلسات المسح"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Session {self.session_id} - {self.get_status_display()}"


class ScanHistory(models.Model):
    """History of scanned items in a session"""
    session = models.ForeignKey(
        ScanSession,
        on_delete=models.CASCADE,
        related_name='scan_history',
        verbose_name="الجلسة"
    )
    scanned_code = models.CharField(max_length=100, verbose_name="الكود الممسوح", default='')
    entity_type = models.CharField(max_length=50, verbose_name="نوع الكيان", default='')
    entity_id = models.IntegerField(verbose_name="معرف الكيان", default=0)
    entity_data = models.JSONField(default=dict, verbose_name="بيانات الكيان")
    scanned_at = models.DateTimeField(auto_now_add=True, verbose_name="وقت المسح")
    is_valid = models.BooleanField(default=True, verbose_name="صالح؟")
    error_message = models.CharField(max_length=255, blank=True, null=True, verbose_name="رسالة الخطأ")
    
    class Meta:
        verbose_name = "تاريخ المسح"
        verbose_name_plural = "تاريخ المسح"
        ordering = ['-scanned_at']
    
    def __str__(self):
        return f"{self.scanned_code} - {self.entity_type}:{self.entity_id}"


# ═══════════════════════════════════════════════════════════════════════════
# STEP 3: TRANSFER AND HANDOVER MODELS
# ═══════════════════════════════════════════════════════════════════════════

class DeviceTransferLog(models.Model):
    """Log for device transfers between departments/rooms/beds"""
    device = models.ForeignKey(
        Device,
        on_delete=models.CASCADE,
        related_name='transfer_logs',
        verbose_name="الجهاز"
    )
    
    # From location
    from_department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='device_transfer_logs_from',
        verbose_name="من القسم"
    )
    from_room = models.ForeignKey(
        Room,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='device_transfer_logs_from',
        verbose_name="من الغرفة"
    )
    from_bed = models.ForeignKey(
        Bed,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='device_transfer_logs_from',
        verbose_name="من السرير"
    )
    
    # To location
    to_department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='device_transfer_logs_to',
        verbose_name="إلى القسم"
    )
    to_room = models.ForeignKey(
        Room,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='device_transfer_logs_to',
        verbose_name="إلى الغرفة"
    )
    to_bed = models.ForeignKey(
        Bed,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='device_transfer_logs_to',
        verbose_name="إلى السرير"
    )
    
    moved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name="نُقل بواسطة"
    )
    moved_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ النقل")
    note = models.TextField(blank=True, null=True, verbose_name="ملاحظات")
    
    class Meta:
        verbose_name = "سجل نقل الجهاز"
        verbose_name_plural = "سجلات نقل الأجهزة"
        ordering = ['-moved_at']
    
    def __str__(self):
        return f"نقل {self.device} من {self.from_department or self.from_room} إلى {self.to_department or self.to_room}"


class PatientTransferLog(models.Model):
    """Log for patient transfers between departments/rooms/beds"""
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name='transfer_logs',
        verbose_name="المريض"
    )
    
    # From location
    from_department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='patient_transfers_from',
        verbose_name="من القسم"
    )
    from_room = models.ForeignKey(
        Room,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='patient_transfers_from',
        verbose_name="من الغرفة"
    )
    from_bed = models.ForeignKey(
        Bed,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='patient_transfers_from',
        verbose_name="من السرير"
    )
    
    # To location
    to_department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='patient_transfers_to',
        verbose_name="إلى القسم"
    )
    to_room = models.ForeignKey(
        Room,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='patient_transfers_to',
        verbose_name="إلى الغرفة"
    )
    to_bed = models.ForeignKey(
        Bed,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='patient_transfers_to',
        verbose_name="إلى السرير"
    )
    
    moved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name="نُقل بواسطة"
    )
    moved_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ النقل")
    note = models.TextField(blank=True, null=True, verbose_name="ملاحظات")
    
    class Meta:
        verbose_name = "سجل نقل المريض"
        verbose_name_plural = "سجلات نقل المرضى"
        ordering = ['-moved_at']
    
    def __str__(self):
        return f"نقل {self.patient} من {self.from_bed or self.from_room} إلى {self.to_bed or self.to_room}"


class DeviceHandoverLog(models.Model):
    """Log for device handovers between users"""
    device = models.ForeignKey(
        Device,
        on_delete=models.CASCADE,
        related_name='handover_logs',
        verbose_name="الجهاز"
    )
    from_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='device_handovers_from',
        verbose_name="من المستخدم"
    )
    to_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='device_handovers_to',
        verbose_name="إلى المستخدم"
    )
    handed_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ التسليم")
    note = models.TextField(blank=True, null=True, verbose_name="ملاحظات")
    
    class Meta:
        verbose_name = "سجل تسليم الجهاز"
        verbose_name_plural = "سجلات تسليم الأجهزة"
        ordering = ['-handed_at']
    
    def __str__(self):
        from_str = str(self.from_user) if self.from_user else "غير محدد"
        return f"تسليم {self.device} من {from_str} إلى {self.to_user}"


# ═══════════════════════════════════════════════════════════════════════════
# DEVICE ACCESSORY MODEL
# ═══════════════════════════════════════════════════════════════════════════

class DeviceAccessory(QRCodeMixin, models.Model):
    """Model for device accessories with QR code functionality"""
    name = models.CharField(max_length=255, verbose_name="اسم الملحق", default='')
    description = models.TextField(blank=True, null=True, verbose_name="الوصف")
    device = models.ForeignKey(
        Device,
        on_delete=models.CASCADE,
        related_name='accessories',
        verbose_name="الجهاز"
    )
    serial_number = models.CharField(max_length=100, unique=True, blank=True, null=True, verbose_name="الرقم التسلسلي")
    model = models.CharField(max_length=100, blank=True, null=True, verbose_name="الموديل")
    manufacturer = models.CharField(max_length=100, blank=True, null=True, verbose_name="الشركة المصنعة")
    purchase_date = models.DateField(blank=True, null=True, verbose_name="تاريخ الشراء")
    warranty_expiry = models.DateField(blank=True, null=True, verbose_name="انتهاء الضمان")
    
    STATUS_CHOICES = [
        ('available', 'متاح'),
        ('in_use', 'قيد الاستخدام'),
        ('maintenance', 'تحت الصيانة'),
        ('damaged', 'تالف'),
        ('lost', 'مفقود'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='available',
        verbose_name="الحالة"
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")
    
    class Meta:
        verbose_name = "ملحق الجهاز"
        verbose_name_plural = "ملحقات الأجهزة"
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} - {self.device.name}"


class DeviceAccessoryUsageLog(models.Model):
    """Log for accessory usage in sessions"""
    usage_log = models.ForeignKey(
        'DeviceUsageLog',
        on_delete=models.CASCADE,
        related_name='accessory_items',
        verbose_name="سجل الاستخدام"
    )
    accessory = models.ForeignKey(
        'DeviceAccessory',
        on_delete=models.CASCADE,
        verbose_name="الملحق"
    )
    scanned_at = models.DateTimeField(auto_now_add=True, verbose_name="وقت المسح")
    notes = models.CharField(max_length=255, blank=True, null=True, verbose_name="ملاحظات")
    
    class Meta:
        verbose_name = "عنصر ملحق في سجل الاستخدام"
        verbose_name_plural = "عناصر الملحقات في سجل الاستخدام"
        unique_together = ['usage_log', 'accessory']
    
    def __str__(self):
        return f"{self.accessory} في {self.usage_log}"


class AccessoryTransaction(models.Model):
    """Model for tracking accessory handover/receipt/transfer operations"""
    TRANSACTION_TYPES = [
        ('handover', 'تسليم'),
        ('receipt', 'استلام'),
        ('transfer', 'نقل'),
        ('maintenance', 'صيانة'),
        ('return', 'إرجاع'),
    ]
    
    accessory = models.ForeignKey(
        DeviceAccessory,
        on_delete=models.CASCADE,
        related_name='transactions',
        verbose_name="الملحق"
    )
    transaction_type = models.CharField(
        max_length=20,
        choices=TRANSACTION_TYPES,
        default='handover',
        verbose_name="نوع العملية"
    )
    from_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='accessory_transactions_from',
        verbose_name="من المستخدم"
    )
    to_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='accessory_transactions_to',
        verbose_name="إلى المستخدم"
    )
    from_department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='accessory_transactions_from',
        verbose_name="من القسم"
    )
    to_department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='accessory_transactions_to',
        verbose_name="إلى القسم"
    )
    notes = models.TextField(blank=True, null=True, verbose_name="ملاحظات")
    scanned_barcode = models.CharField(max_length=200, blank=True, null=True, verbose_name="الباركود الممسوح")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ العملية")
    is_confirmed = models.BooleanField(default=False, verbose_name="مؤكدة؟")
    confirmed_at = models.DateTimeField(null=True, blank=True, verbose_name="تاريخ التأكيد")
    
    class Meta:
        verbose_name = "معاملة ملحق"
        verbose_name_plural = "معاملات الملحقات"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_transaction_type_display()} - {self.accessory.name} - {self.created_at.strftime('%Y-%m-%d')}"


# ═══════════════════════════════════════════════════════════════════════════
# ACCESSORY TRANSFER MODELS
# ═══════════════════════════════════════════════════════════════════════════

class AccessoryTransferRequest(models.Model):
    """Model for accessory transfer requests that need approval"""
    accessory = models.ForeignKey(
        DeviceAccessory,
        on_delete=models.CASCADE,
        related_name='transfer_requests',
        verbose_name="الملحق"
    )
    
    # From location/device
    from_device = models.ForeignKey(
        Device,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='accessory_transfers_from',
        verbose_name="من الجهاز"
    )
    from_department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='accessory_transfer_requests_from',
        verbose_name="من القسم"
    )
    from_room = models.ForeignKey(
        Room,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='accessory_transfers_from',
        verbose_name="من الغرفة"
    )
    
    # To location/device
    to_device = models.ForeignKey(
        Device,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='accessory_transfers_to',
        verbose_name="إلى الجهاز"
    )
    to_department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='accessory_transfer_requests_to',
        verbose_name="إلى القسم"
    )
    to_room = models.ForeignKey(
        Room,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='accessory_transfers_to',
        verbose_name="إلى الغرفة"
    )
    
    # Request details
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='accessory_transfer_requested_by',
        verbose_name="طلب بواسطة"
    )
    requested_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الطلب")
    reason = models.TextField(blank=True, null=True, verbose_name="سبب النقل")
    
    # Approval details
    is_approved = models.BooleanField(default=False, verbose_name="موافق عليه؟")
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='accessory_transfer_approved_by',
        verbose_name="وافق عليه"
    )
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name="تاريخ الموافقة")
    rejection_reason = models.TextField(blank=True, null=True, verbose_name="سبب الرفض")
    
    class Meta:
        verbose_name = "طلب نقل ملحق"
        verbose_name_plural = "طلبات نقل الملحقات"
        ordering = ['-requested_at']
    
    def __str__(self):
        device_info = f"من {self.from_device}" if self.from_device else f"من {self.from_department}"
        to_info = f"إلى {self.to_device}" if self.to_device else f"إلى {self.to_department}"
        return f"نقل {self.accessory.name} {device_info} {to_info} (موافق: {self.is_approved})"


class AccessoryTransferLog(models.Model):
    """Log for completed accessory transfers"""
    accessory = models.ForeignKey(
        DeviceAccessory,
        on_delete=models.CASCADE,
        related_name='transfer_logs',
        verbose_name="الملحق"
    )
    
    # From location/device
    from_device = models.ForeignKey(
        Device,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='accessory_transfer_logs_from',
        verbose_name="من الجهاز"
    )
    from_department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='accessory_transfer_logs_from',
        verbose_name="من القسم"
    )
    from_room = models.ForeignKey(
        Room,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='accessory_transfer_logs_from',
        verbose_name="من الغرفة"
    )
    
    # To location/device
    to_device = models.ForeignKey(
        Device,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='accessory_transfer_logs_to',
        verbose_name="إلى الجهاز"
    )
    to_department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='accessory_transfer_logs_to',
        verbose_name="إلى القسم"
    )
    to_room = models.ForeignKey(
        Room,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='accessory_transfer_logs_to',
        verbose_name="إلى الغرفة"
    )
    
    # Transfer details
    transferred_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name="نُقل بواسطة"
    )
    transferred_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ النقل")
    notes = models.TextField(blank=True, null=True, verbose_name="ملاحظات")
    
    class Meta:
        verbose_name = "سجل نقل ملحق"
        verbose_name_plural = "سجلات نقل الملحقات"
        ordering = ['-transferred_at']
    
    def __str__(self):
        from_info = str(self.from_device) if self.from_device else str(self.from_department or self.from_room)
        to_info = str(self.to_device) if self.to_device else str(self.to_department or self.to_room)
        return f"نقل {self.accessory.name} من {from_info} إلى {to_info}"


# ===== CMMS Models =====

# CMMS Status and Type Choices
SR_STATUS_CHOICES = [
    ('new', 'جديد'),
    ('in_progress', 'جاري العمل'),
    ('on_hold', 'معلق'),
    ('resolved', 'تم الحل'),
    ('closed', 'مغلق'),
    ('cancelled', 'ملغي'),
]

WO_STATUS_CHOICES = [
    ('new', 'جديد'),
    ('assigned', 'تم التعيين'),
    ('in_progress', 'جاري العمل'),
    ('wait_parts', 'انتظار قطع غيار'),
    ('on_hold', 'معلق'),
    ('resolved', 'تم الحل'),
    ('qa_verified', 'تم التحقق'),
    ('closed', 'مغلق'),
    ('cancelled', 'ملغي'),
]

SEVERITY_CHOICES = [
    ('critical', 'حرج'),
    ('high', 'عالي'),
    ('medium', 'متوسط'),
    ('low', 'منخفض'),
]

IMPACT_CHOICES = [
    ('extensive', 'واسع'),
    ('significant', 'كبير'),
    ('moderate', 'متوسط'),
    ('minor', 'بسيط'),
]

SR_TYPE_CHOICES = [
    ('breakdown', 'عطل'),
    ('preventive', 'صيانة وقائية'),
    ('inspection', 'فحص'),
    ('upgrade', 'ترقية'),
    ('installation', 'تركيب'),
    ('other', 'أخرى'),
]

WO_TYPE_CHOICES = [
    ('corrective', 'صيانة تصحيحية'),
    ('preventive', 'صيانة وقائية'),
    ('inspection', 'فحص'),
    ('calibration', 'معايرة'),
    ('upgrade', 'ترقية'),
    ('installation', 'تركيب'),
    ('other', 'أخرى'),
]

PRIORITY_CHOICES = [
    ('urgent', 'عاجل'),
    ('high', 'عالي'),
    ('medium', 'متوسط'),
    ('low', 'منخفض'),
]

SLA_TYPE_CHOICES = [
    ('response', 'وقت الاستجابة'),
    ('resolution', 'وقت الحل'),
]

FREQUENCY_CHOICES = [
    ('daily', 'يومي'),
    ('weekly', 'أسبوعي'),
    ('monthly', 'شهري'),
    ('quarterly', 'ربع سنوي'),
    ('semi_annual', 'نصف سنوي'),
    ('annual', 'سنوي'),
    ('custom', 'مخصص'),
]

NOTIFICATION_TYPE_CHOICES = [
    ('service_request', 'طلب خدمة'),
    ('work_order', 'أمر عمل'),
    ('preventive_maintenance', 'صيانة وقائية'),
    ('sla_breach', 'خرق اتفاقية مستوى الخدمة'),
    ('system', 'نظام'),
]

NOTIFICATION_STATUS_CHOICES = [
    ('pending', 'في الانتظار'),
    ('sent', 'تم الإرسال'),
    ('read', 'تم القراءة'),
    ('failed', 'فشل'),
]

EMAIL_STATUS_CHOICES = [
    ('pending', 'في الانتظار'),
    ('sent', 'تم الإرسال'),
    ('failed', 'فشل'),
    ('bounced', 'مرتد'),
]

SUPPLIER_STATUS_CHOICES = [
    ('active', 'نشط'),
    ('inactive', 'غير نشط'),
    ('suspended', 'معلق'),
]

SPARE_PART_STATUS_CHOICES = [
    ('available', 'متوفر'),
    ('low_stock', 'مخزون منخفض'),
    ('out_of_stock', 'نفد المخزون'),
    ('discontinued', 'متوقف'),
]

UNIT_CHOICES = [
    ('piece', 'قطعة'),
    ('meter', 'متر'),
    ('liter', 'لتر'),
    ('kilogram', 'كيلوجرام'),
    ('box', 'صندوق'),
    ('pack', 'عبوة'),
]

CALIBRATION_STATUS_CHOICES = [
    ('due', 'مستحق'),
    ('overdue', 'متأخر'),
    ('completed', 'مكتمل'),
    ('not_required', 'غير مطلوب'),
]

DOWNTIME_TYPE_CHOICES = [
    ('planned', 'مخطط'),
    ('unplanned', 'غير مخطط'),
    ('emergency', 'طوارئ'),
]


class ServiceRequest(models.Model):
    """نموذج طلب الخدمة"""
    device = models.ForeignKey('Device', on_delete=models.CASCADE, related_name='service_requests', verbose_name="الجهاز")
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reported_requests', verbose_name="مقدم البلاغ")
    title = models.CharField(max_length=200, verbose_name="عنوان البلاغ", default='')
    description = models.TextField(verbose_name="وصف المشكلة", blank=True, null=True)
    request_type = models.CharField(max_length=20, choices=SR_TYPE_CHOICES, default='breakdown', verbose_name="نوع البلاغ")
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='medium', verbose_name="درجة الخطورة")
    impact = models.CharField(max_length=20, choices=IMPACT_CHOICES, default='moderate', verbose_name="التأثير")
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium', verbose_name="الأولوية")
    status = models.CharField(max_length=20, choices=SR_STATUS_CHOICES, default='new', verbose_name="الحالة")
    
    # SLA fields
    response_due = models.DateTimeField(null=True, blank=True, verbose_name="موعد الاستجابة المطلوب")
    resolution_due = models.DateTimeField(null=True, blank=True, verbose_name="موعد الحل المطلوب")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")
    resolved_at = models.DateTimeField(null=True, blank=True, verbose_name="تاريخ الحل")
    closed_at = models.DateTimeField(null=True, blank=True, verbose_name="تاريخ الإغلاق")
    
    # Additional fields
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='assigned_requests',
        verbose_name="مُعين إلى"
    )
    estimated_hours = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name="الساعات المقدرة")
    actual_hours = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name="الساعات الفعلية")
    cost_estimate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="التكلفة المقدرة")
    actual_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="التكلفة الفعلية")
    
    class Meta:
        verbose_name = "طلب خدمة"
        verbose_name_plural = "طلبات الخدمة"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.device.name}"
    
    def is_overdue_response(self):
        """التحقق من تجاوز وقت الاستجابة"""
        if self.response_due and timezone.now() > self.response_due and self.status == 'new':
            return True
        return False
    
    def is_overdue_resolution(self):
        """التحقق من تجاوز وقت الحل"""
        if self.resolution_due and timezone.now() > self.resolution_due and self.status not in ['resolved', 'closed']:
            return True
        return False
    
    def get_sla_status(self):
        """الحصول على حالة اتفاقية مستوى الخدمة"""
        if self.is_overdue_resolution():
            return 'overdue_resolution'
        elif self.is_overdue_response():
            return 'overdue_response'
        elif self.status in ['resolved', 'closed']:
            return 'met'
        else:
            return 'on_track'
    
    def calculate_response_time(self):
        """حساب وقت الاستجابة"""
        if self.status != 'new':
            # Find first work order or status change
            first_wo = self.work_orders.first()
            if first_wo:
                return (first_wo.created_at - self.created_at).total_seconds() / 3600
        return None
    
    def calculate_resolution_time(self):
        """حساب وقت الحل"""
        if self.resolved_at:
            return (self.resolved_at - self.created_at).total_seconds() / 3600
        return None


class SLAMatrix(models.Model):
    """
    مصفوفة اتفاقيات مستوى الخدمة
    هنا بنحدد SLA حسب نوع الجهاز ودرجة الخطورة والتأثير
    """
    device_category = models.ForeignKey('DeviceCategory', on_delete=models.CASCADE, verbose_name="فئة الجهاز")
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, verbose_name="درجة الخطورة", default='medium')
    impact = models.CharField(max_length=20, choices=IMPACT_CHOICES, verbose_name="التأثير", default='moderate')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, verbose_name="الأولوية", default='medium')
    sla_definition = models.ForeignKey('SLADefinition', on_delete=models.CASCADE, verbose_name="تعريف SLA")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")
    is_active = models.BooleanField(default=True, verbose_name="نشط")
    
    class Meta:
        verbose_name = "مصفوفة SLA"
        verbose_name_plural = "مصفوفات SLA"
        unique_together = ['device_category', 'severity', 'impact', 'priority']
        
    def __str__(self):
        return f"{self.device_category.name} - {self.get_severity_display()} - {self.get_impact_display()}"


class CalibrationRecord(models.Model):
    """
    سجل المعايرة للأجهزة
    هنا بنتتبع معايرات الأجهزة وتواريخ الاستحقاق
    """
    device = models.ForeignKey('Device', on_delete=models.CASCADE, related_name='calibration_records', verbose_name="الجهاز")
    calibration_date = models.DateField(verbose_name="تاريخ المعايرة", null=True, blank=True)
    next_calibration_date = models.DateField(verbose_name="تاريخ المعايرة التالية", null=True, blank=True)
    calibration_interval_months = models.PositiveIntegerField(default=12, verbose_name="فترة المعايرة بالشهور")
    
    calibrated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='calibrations_performed',
        verbose_name="تم المعايرة بواسطة"
    )
    
    certificate_number = models.CharField(max_length=100, blank=True, verbose_name="رقم الشهادة")
    calibration_agency = models.CharField(max_length=200, blank=True, verbose_name="جهة المعايرة")
    
    status = models.CharField(
        max_length=20, 
        choices=CALIBRATION_STATUS_CHOICES, 
        default='completed',
        verbose_name="حالة المعايرة"
    )
    
    notes = models.TextField(blank=True, verbose_name="ملاحظات")
    certificate_file = models.FileField(
        upload_to='calibration_certificates/', 
        blank=True, 
        null=True,
        verbose_name="ملف الشهادة"
    )
    
    cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="التكلفة")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")
    
    class Meta:
        verbose_name = "سجل معايرة"
        verbose_name_plural = "سجلات المعايرة"
        ordering = ['-calibration_date']
        
    def __str__(self):
        return f"{self.device.name} - {self.calibration_date}"
    
    def is_due_soon(self, days=30):
        """التحقق من قرب موعد المعايرة"""
        from datetime import date, timedelta
        return self.next_calibration_date <= date.today() + timedelta(days=days)
    
    def is_overdue(self):
        """التحقق من تأخر المعايرة"""
        from datetime import date
        return self.next_calibration_date < date.today()


class DowntimeEvent(models.Model):
    """
    أحداث التوقف للأجهزة
    هنا بنتتبع فترات توقف الأجهزة عن العمل
    """
    DOWNTIME_TYPE_CHOICES = [
        ('planned', 'مخطط'),
        ('unplanned', 'غير مخطط'),
        ('emergency', 'طوارئ'),
    ]
    
    device = models.ForeignKey('Device', on_delete=models.CASCADE, related_name='downtime_events', verbose_name="الجهاز")
    start_time = models.DateTimeField(verbose_name="وقت بداية التوقف", null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True, verbose_name="وقت نهاية التوقف")
    
    downtime_type = models.CharField(
        max_length=20, 
        choices=DOWNTIME_TYPE_CHOICES, 
        default='unplanned',
        verbose_name="نوع التوقف"
    )
    
    reason = models.TextField(verbose_name="سبب التوقف", blank=True, null=True)
    impact_description = models.TextField(blank=True, verbose_name="وصف التأثير")
    
    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='event_reported_downtimes',
        verbose_name="تم الإبلاغ بواسطة"
    )
    
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='event_resolved_downtimes',
        verbose_name="تم الحل بواسطة"
    )
    
    related_work_order = models.ForeignKey(
        'WorkOrder', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='related_downtime_events',
        verbose_name="أمر الشغل المرتبط"
    )
    
    cost_impact = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        verbose_name="التأثير المالي"
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")
    
    class Meta:
        verbose_name = "حدث توقف"
        verbose_name_plural = "أحداث التوقف"
        ordering = ['-start_time']
        
    def __str__(self):
        return f"{self.device.name} - {self.start_time.strftime('%Y-%m-%d %H:%M')}"
    
    def duration_hours(self):
        """حساب مدة التوقف بالساعات"""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds() / 3600
        else:
            from django.utils import timezone
            return (timezone.now() - self.start_time).total_seconds() / 3600
    
    def is_ongoing(self):
        """التحقق من استمرار التوقف"""
        return self.end_time is None


# تم نقل هذا النموذج إلى تعريف آخر في الملف
class DeviceUsageLogDaily(models.Model):
    """
    سجل الاستخدام اليومي للأجهزة
    هنا بنتتبع استخدام الأجهزة والتفقد اليومي
    """
    device = models.ForeignKey('Device', on_delete=models.CASCADE, related_name='daily_usage_logs', verbose_name="الجهاز")
    date = models.DateField(verbose_name="التاريخ", null=True, blank=True)
    shift = models.CharField(
        max_length=20,
        choices=[
            ('morning', 'صباحي'),
            ('evening', 'مسائي'),
            ('night', 'ليلي'),
        ],
        default='morning',
        verbose_name="الوردية"
    )
    
    checked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True,
        verbose_name="تم التفقد بواسطة"
    )
    
    pre_use_check = models.BooleanField(default=False, verbose_name="تفقد ما قبل الاستخدام")
    post_use_check = models.BooleanField(default=False, verbose_name="تفقد ما بعد الاستخدام")
    
    operational_status = models.CharField(
        max_length=20,
        choices=[
            ('working', 'يعمل بشكل طبيعي'),
            ('minor_issues', 'مشاكل بسيطة'),
            ('major_issues', 'مشاكل كبيرة'),
            ('not_working', 'لا يعمل'),
        ],
        default='working',
        verbose_name="حالة التشغيل"
    )
    
    usage_hours = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        null=True, 
        blank=True,
        verbose_name="ساعات الاستخدام"
    )
    
    patient_count = models.PositiveIntegerField(null=True, blank=True, verbose_name="عدد المرضى")
    
    issues_found = models.TextField(blank=True, verbose_name="المشاكل المكتشفة")
    maintenance_needed = models.BooleanField(default=False, verbose_name="يحتاج صيانة")
    cleaning_done = models.BooleanField(default=False, verbose_name="تم التنظيف")
    sterilization_done = models.BooleanField(default=False, verbose_name="تم التعقيم")
    
    notes = models.TextField(blank=True, verbose_name="ملاحظات")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")
    
    class Meta:
        verbose_name = "سجل استخدام"
        verbose_name_plural = "سجلات الاستخدام"
        unique_together = ['device', 'date', 'shift']
        ordering = ['-date', '-shift']
        
    def __str__(self):
        return f"{self.device.name} - {self.date} - {self.get_shift_display()}"


class WorkOrderPart(models.Model):
    """
    ربط قطع الغيار بأوامر الشغل
    هنا بنتتبع قطع الغيار المستخدمة في كل أمر شغل
    """
    work_order = models.ForeignKey('WorkOrder', on_delete=models.CASCADE, related_name='parts_used', verbose_name="أمر الشغل")
    spare_part = models.ForeignKey('SparePart', on_delete=models.CASCADE, verbose_name="قطعة الغيار")
    quantity_requested = models.PositiveIntegerField(verbose_name="الكمية المطلوبة", default=1)
    quantity_used = models.PositiveIntegerField(default=0, verbose_name="الكمية المستخدمة")
    
    status = models.CharField(
        max_length=20,
        choices=[
            ('requested', 'مطلوبة'),
            ('reserved', 'محجوزة'),
            ('issued', 'مصروفة'),
            ('returned', 'مرتجعة'),
        ],
        default='requested',
        verbose_name="الحالة"
    )
    
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="تكلفة الوحدة", default=0)
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="التكلفة الإجمالية", default=0)
    
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='parts_requested',
        verbose_name="طلبت بواسطة"
    )
    
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='parts_issued',
        verbose_name="صرفت بواسطة"
    )
    
    requested_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الطلب")
    issued_at = models.DateTimeField(null=True, blank=True, verbose_name="تاريخ الصرف")
    
    notes = models.TextField(blank=True, verbose_name="ملاحظات")
    
    class Meta:
        verbose_name = "قطعة غيار في أمر شغل"
        verbose_name_plural = "قطع غيار في أوامر الشغل"
        
    def __str__(self):
        return f"{self.work_order.wo_number} - {self.spare_part.name}"
    
    def save(self, *args, **kwargs):
        # حساب التكلفة الإجمالية تلقائياً
        self.total_cost = self.quantity_used * self.unit_cost
        super().save(*args, **kwargs)


class WorkOrder(models.Model):
    """نموذج أمر العمل"""
    service_request = models.ForeignKey('ServiceRequest', on_delete=models.CASCADE, related_name='work_orders', verbose_name="البلاغ")
    wo_number = models.CharField(max_length=50, unique=True, verbose_name="رقم أمر العمل", default='')
    title = models.CharField(max_length=200, verbose_name="عنوان أمر العمل", default='')
    description = models.TextField(verbose_name="وصف العمل", blank=True, null=True)
    wo_type = models.CharField(max_length=20, choices=WO_TYPE_CHOICES, default='corrective', verbose_name="نوع أمر العمل")
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium', verbose_name="الأولوية")
    status = models.CharField(max_length=20, choices=WO_STATUS_CHOICES, default='new', verbose_name="الحالة")
    
    # Assignment
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_work_orders', verbose_name="تم الإنشاء بواسطة")
    assignee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_work_orders', verbose_name="المسؤول")
    
    # Scheduling
    scheduled_start = models.DateTimeField(null=True, blank=True, verbose_name="موعد البدء المجدول")
    scheduled_end = models.DateTimeField(null=True, blank=True, verbose_name="موعد الانتهاء المجدول")
    actual_start = models.DateTimeField(null=True, blank=True, verbose_name="وقت البدء الفعلي")
    actual_end = models.DateTimeField(null=True, blank=True, verbose_name="وقت الانتهاء الفعلي")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="تاريخ الإنجاز")
    
    # Cost and time tracking
    estimated_hours = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name="الساعات المقدرة")
    actual_hours = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name="الساعات الفعلية")
    labor_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="تكلفة العمالة")
    parts_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="تكلفة القطع")
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="التكلفة الإجمالية")
    
    # Quality assurance
    qa_required = models.BooleanField(default=False, verbose_name="يتطلب ضمان الجودة")
    qa_verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='qa_verified_work_orders',
        verbose_name="تم التحقق بواسطة"
    )
    qa_verified_at = models.DateTimeField(null=True, blank=True, verbose_name="تاريخ التحقق")
    qa_notes = models.TextField(blank=True, verbose_name="ملاحظات ضمان الجودة")
    
    # Additional fields
    completion_notes = models.TextField(blank=True, verbose_name="ملاحظات الإنجاز")
    
    class Meta:
        verbose_name = "أمر عمل"
        verbose_name_plural = "أوامر العمل"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.wo_number} - {self.title}"
    
    def save(self, *args, **kwargs):
        if not self.wo_number:
            # Generate work order number
            from datetime import datetime
            year = datetime.now().year
            month = datetime.now().month
            count = WorkOrder.objects.filter(created_at__year=year, created_at__month=month).count() + 1
            self.wo_number = f"WO-{year}{month:02d}-{count:04d}"
        super().save(*args, **kwargs)
    
    def calculate_duration(self):
        """حساب مدة العمل"""
        if self.actual_start and self.actual_end:
            return (self.actual_end - self.actual_start).total_seconds() / 3600
        return None
    
    def is_overdue(self):
        """التحقق من تجاوز الموعد المحدد"""
        if self.scheduled_end and timezone.now() > self.scheduled_end and self.status not in ['completed', 'closed']:
            return True
        return False


class JobPlan(models.Model):
    """نموذج خطة العمل"""
    name = models.CharField(max_length=200, verbose_name="اسم خطة العمل", default='')
    description = models.TextField(verbose_name="وصف خطة العمل", blank=True, null=True)
    device_category = models.ForeignKey('DeviceCategory', on_delete=models.CASCADE, related_name='job_plans', verbose_name="فئة الجهاز")
    job_type = models.CharField(max_length=20, choices=WO_TYPE_CHOICES, verbose_name="نوع العمل")
    estimated_hours = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="الساعات المقدرة", default=0)
    
    # Instructions
    instructions = models.TextField(verbose_name="تعليمات العمل", blank=True, null=True)
    safety_notes = models.TextField(blank=True, verbose_name="ملاحظات السلامة")
    
    # Status
    is_active = models.BooleanField(default=True, verbose_name="نشط")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="تم الإنشاء بواسطة")
    
    class Meta:
        verbose_name = "خطة عمل"
        verbose_name_plural = "خطط العمل"
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} - {self.device_category.name}"


class JobPlanStep(models.Model):
    """نموذج خطوة خطة العمل"""
    job_plan = models.ForeignKey(JobPlan, on_delete=models.CASCADE, related_name='steps', verbose_name="خطة العمل")
    step_number = models.PositiveIntegerField(verbose_name="رقم الخطوة", default=1)
    title = models.CharField(max_length=200, verbose_name="عنوان الخطوة", default='')
    description = models.TextField(verbose_name="وصف الخطوة", blank=True, null=True)
    estimated_minutes = models.PositiveIntegerField(default=0, verbose_name="الدقائق المقدرة")
    
    class Meta:
        verbose_name = "خطوة خطة العمل"
        verbose_name_plural = "خطوات خطط العمل"
        ordering = ['job_plan', 'step_number']
        unique_together = ['job_plan', 'step_number']
    
    def __str__(self):
        return f"{self.job_plan.name} - الخطوة {self.step_number}: {self.title}"


class PreventiveMaintenanceSchedule(models.Model):
    """نموذج جدولة الصيانة الوقائية"""
    name = models.CharField(max_length=200, verbose_name="اسم الجدولة", default='')
    description = models.TextField(blank=True, verbose_name="الوصف")
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='pm_schedules', verbose_name="الجهاز")
    job_plan = models.ForeignKey(JobPlan, on_delete=models.CASCADE, related_name='pm_schedules', verbose_name="خطة العمل")
    
    # Scheduling
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, verbose_name="التكرار")
    interval_days = models.PositiveIntegerField(null=True, blank=True, verbose_name="الفترة بالأيام")
    start_date = models.DateField(verbose_name="تاريخ البدء", null=True, blank=True)
    end_date = models.DateField(null=True, blank=True, verbose_name="تاريخ الانتهاء")
    
    # Next occurrence
    next_due_date = models.DateField(verbose_name="تاريخ الاستحقاق التالي", null=True, blank=True)
    last_completed_date = models.DateField(verbose_name="تاريخ آخر إنجاز", null=True, blank=True)
    
    # Assignment
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='pm_schedules',
        verbose_name="مُعين إلى"
    )
    
    # Status
    is_active = models.BooleanField(default=True, verbose_name="نشط")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="تم الإنشاء بواسطة")
    
    class Meta:
        verbose_name = "جدولة صيانة وقائية"
        verbose_name_plural = "جدولة الصيانة الوقائية"
        ordering = ['next_due_date']
    
    def __str__(self):
        return f"{self.name} - {self.device.name}"
    
    def calculate_next_due_date(self):
        """حساب تاريخ الاستحقاق التالي بناءً على التاريخ الحالي وليس التاريخ السابق"""
        from datetime import timedelta, date
        import calendar
        
        # استخدم التاريخ الحالي كنقطة بداية لحساب التاريخ التالي
        today = date.today()
        base_date = self.last_completed_date or today
        
        if self.frequency == 'daily':
            return base_date + timedelta(days=1)
        elif self.frequency == 'weekly':
            return base_date + timedelta(weeks=1)
        elif self.frequency == 'monthly':
            # Add one month
            year = base_date.year
            month = base_date.month
            day = base_date.day
            
            if month == 12:
                year += 1
                month = 1
            else:
                month += 1
            
            # Handle end of month dates
            max_day = calendar.monthrange(year, month)[1]
            if day > max_day:
                day = max_day
            
            return date(year, month, day)
        elif self.frequency == 'quarterly':
            return base_date + timedelta(days=90)
        elif self.frequency == 'semi_annual':
            return base_date + timedelta(days=180)
        elif self.frequency == 'annual':
            return base_date + timedelta(days=365)
        elif self.frequency == 'custom' and self.interval_days:
            return base_date + timedelta(days=self.interval_days)
        
        return base_date + timedelta(days=1)  # افتراضي يومي
    
    def is_due(self):
        """التحقق من استحقاق الصيانة"""
        from datetime import date
        return self.next_due_date <= date.today()
    
    def is_overdue(self):
        """التحقق من تجاوز موعد الصيانة"""
        from datetime import date
        return self.next_due_date < date.today()
    
    def generate_work_order(self):
        """إنشاء أمر عمل للصيانة الوقائية"""
        # Create service request first
        service_request = ServiceRequest.objects.create(
            device=self.device,
            reporter=self.created_by,
            title=f"صيانة وقائية - {self.device.name}",
            description=f"صيانة وقائية مجدولة للجهاز {self.device.name}",
            request_type='preventive',
            priority='medium',
            status='new'
        )
        
        # Create work order
        wo = WorkOrder.objects.create(
            service_request=service_request,
            title=f"صيانة وقائية - {self.device.name}",
            description=self.job_plan.instructions if self.job_plan else "صيانة وقائية عامة",
            wo_type='preventive',
            priority='medium',
            created_by=self.created_by,
            assignee=self.assigned_to,
            estimated_hours=self.job_plan.estimated_hours if self.job_plan else 2.0
        )
        
        # Update last completed date and next due date
        from datetime import date
        self.last_completed_date = date.today()
        self.next_due_date = self.calculate_next_due_date()
        self.save(update_fields=['last_completed_date', 'next_due_date'])
        
        return wo


class SLADefinition(models.Model):
    """نموذج تعريف اتفاقية مستوى الخدمة"""
    name = models.CharField(max_length=200, verbose_name="اسم الاتفاقية", default='')
    description = models.TextField(blank=True, verbose_name="الوصف")
    
    # Criteria
    device_category = models.ForeignKey(DeviceCategory, on_delete=models.CASCADE, null=True, blank=True, verbose_name="فئة الجهاز")
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, null=True, blank=True, verbose_name="درجة الخطورة")
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, null=True, blank=True, verbose_name="الأولوية")
    
    # SLA times (in hours)
    response_time_hours = models.PositiveIntegerField(verbose_name="وقت الاستجابة (ساعات)", default=24)
    resolution_time_hours = models.PositiveIntegerField(verbose_name="وقت الحل (ساعات)", default=72)
    
    # Status
    is_active = models.BooleanField(default=True, verbose_name="نشط")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")
    
    class Meta:
        verbose_name = "تعريف اتفاقية مستوى الخدمة"
        verbose_name_plural = "تعريفات اتفاقيات مستوى الخدمة"
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def applies_to_request(self, service_request):
        """التحقق من انطباق الاتفاقية على طلب الخدمة"""
        if self.device_category and service_request.device.category != self.device_category:
            return False
        if self.severity and service_request.severity != self.severity:
            return False
        if self.priority and service_request.priority != self.priority:
            return False
        return True


# ===== Notification Models =====

class SystemNotification(models.Model):
    """نموذج إشعارات النظام"""
    title = models.CharField(max_length=200, verbose_name="العنوان", default='')
    message = models.TextField(verbose_name="الرسالة", blank=True, null=True)
    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPE_CHOICES, verbose_name="نوع الإشعار")
    
    # Recipients
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='notifications',
        verbose_name="المستقبل"
    )
    
    # Related objects
    service_request = models.ForeignKey(
        ServiceRequest, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='notifications',
        verbose_name="طلب الخدمة"
    )
    work_order = models.ForeignKey(
        WorkOrder, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='notifications',
        verbose_name="أمر العمل"
    )
    pm_schedule = models.ForeignKey(
        PreventiveMaintenanceSchedule, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='notifications',
        verbose_name="جدولة الصيانة الوقائية"
    )
    
    # Status and timestamps
    status = models.CharField(max_length=20, choices=NOTIFICATION_STATUS_CHOICES, default='pending', verbose_name="الحالة")
    is_read = models.BooleanField(default=False, verbose_name="تم القراءة")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    read_at = models.DateTimeField(null=True, blank=True, verbose_name="تاريخ القراءة")
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name="تاريخ الإرسال")
    
    # Priority and expiry
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium', verbose_name="الأولوية")
    expires_at = models.DateTimeField(null=True, blank=True, verbose_name="تاريخ الانتهاء")
    
    class Meta:
        verbose_name = "إشعار النظام"
        verbose_name_plural = "إشعارات النظام"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['notification_type', 'status']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.recipient.username}"
    
    def mark_as_read(self):
        """تحديد الإشعار كمقروء"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.status = 'read'
            self.save()
    
    def is_expired(self):
        """التحقق من انتهاء صلاحية الإشعار"""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False


class EmailLog(models.Model):
    """نموذج سجل الإيميلات"""
    recipient_email = models.EmailField(verbose_name="بريد المستقبل", default='')
    recipient_name = models.CharField(max_length=200, blank=True, verbose_name="اسم المستقبل")
    subject = models.CharField(max_length=300, verbose_name="الموضوع", default='')
    body = models.TextField(verbose_name="محتوى الرسالة", blank=True, null=True)
    
    # Related notification
    notification = models.ForeignKey(
        SystemNotification, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='email_logs',
        verbose_name="الإشعار"
    )
    
    # Status and tracking
    status = models.CharField(max_length=20, choices=EMAIL_STATUS_CHOICES, default='pending', verbose_name="الحالة")
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name="تاريخ الإرسال")
    error_message = models.TextField(blank=True, verbose_name="رسالة الخطأ")
    
    # Email provider tracking
    message_id = models.CharField(max_length=200, blank=True, verbose_name="معرف الرسالة")
    provider_response = models.TextField(blank=True, verbose_name="رد مقدم الخدمة")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")
    
    class Meta:
        verbose_name = "سجل إيميل"
        verbose_name_plural = "سجلات الإيميلات"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['recipient_email']),
        ]
    
    def __str__(self):
        return f"{self.subject} - {self.recipient_email}"


class NotificationPreference(models.Model):
    """نموذج تفضيلات الإشعارات"""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='notification_preferences',
        verbose_name="المستخدم"
    )
    
    # Email preferences
    email_enabled = models.BooleanField(default=True, verbose_name="تفعيل الإيميل")
    email_service_requests = models.BooleanField(default=True, verbose_name="طلبات الخدمة عبر الإيميل")
    email_work_orders = models.BooleanField(default=True, verbose_name="أوامر العمل عبر الإيميل")
    email_preventive_maintenance = models.BooleanField(default=True, verbose_name="الصيانة الوقائية عبر الإيميل")
    email_sla_breaches = models.BooleanField(default=True, verbose_name="خرق اتفاقيات الخدمة عبر الإيميل")
    
    # In-app preferences
    app_enabled = models.BooleanField(default=True, verbose_name="تفعيل إشعارات التطبيق")
    app_service_requests = models.BooleanField(default=True, verbose_name="طلبات الخدمة في التطبيق")
    app_work_orders = models.BooleanField(default=True, verbose_name="أوامر العمل في التطبيق")
    app_preventive_maintenance = models.BooleanField(default=True, verbose_name="الصيانة الوقائية في التطبيق")
    app_sla_breaches = models.BooleanField(default=True, verbose_name="خرق اتفاقيات الخدمة في التطبيق")
    
    # Frequency settings
    digest_frequency = models.CharField(
        max_length=20, 
        choices=[
            ('immediate', 'فوري'),
            ('hourly', 'كل ساعة'),
            ('daily', 'يومي'),
            ('weekly', 'أسبوعي'),
        ],
        default='immediate',
        verbose_name="تكرار الملخص"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")
    
    class Meta:
        verbose_name = "تفضيلات الإشعارات"
        verbose_name_plural = "تفضيلات الإشعارات"
    
    def __str__(self):
        return f"تفضيلات {self.user.username}"


class NotificationTemplate(models.Model):
    """نموذج قوالب الإشعارات"""
    name = models.CharField(max_length=200, verbose_name="اسم القالب", default='')
    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPE_CHOICES, verbose_name="نوع الإشعار")
    
    # Template content
    subject_template = models.CharField(max_length=300, verbose_name="قالب الموضوع", default='')
    body_template = models.TextField(verbose_name="قالب المحتوى", blank=True, null=True)
    
    # Language and formatting
    language = models.CharField(
        max_length=10, 
        choices=[('ar', 'العربية'), ('en', 'English')], 
        default='ar',
        verbose_name="اللغة"
    )
    is_html = models.BooleanField(default=False, verbose_name="HTML")
    
    # Status
    is_active = models.BooleanField(default=True, verbose_name="نشط")
    is_default = models.BooleanField(default=False, verbose_name="افتراضي")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="تم الإنشاء بواسطة")
    
    class Meta:
        verbose_name = "قالب إشعار"
        verbose_name_plural = "قوالب الإشعارات"
        ordering = ['notification_type', 'name']
        unique_together = ['notification_type', 'language', 'is_default']
    
    def __str__(self):
        return f"{self.name} ({self.get_notification_type_display()})"
    
    def render(self, context):
        """تحويل القالب باستخدام السياق المعطى"""
        from django.template import Template, Context
        
        subject_template = Template(self.subject_template)
        body_template = Template(self.body_template)
        
        django_context = Context(context)
        
        return {
            'subject': subject_template.render(django_context),
            'body': body_template.render(django_context)
        }


class NotificationQueue(models.Model):
    """نموذج قائمة انتظار الإشعارات"""
    notification = models.ForeignKey(
        SystemNotification, 
        on_delete=models.CASCADE, 
        related_name='queue_entries',
        verbose_name="الإشعار"
    )
    
    # Processing details
    scheduled_for = models.DateTimeField(verbose_name="مجدول لـ", null=True, blank=True)
    attempts = models.PositiveIntegerField(default=0, verbose_name="المحاولات")
    max_attempts = models.PositiveIntegerField(default=3, verbose_name="أقصى محاولات")
    
    # Status
    status = models.CharField(
        max_length=20, 
        choices=[
            ('pending', 'في الانتظار'),
            ('processing', 'جاري المعالجة'),
            ('completed', 'مكتمل'),
            ('failed', 'فشل'),
            ('cancelled', 'ملغي'),
        ],
        default='pending',
        verbose_name="الحالة"
    )
    
    # Error tracking
    last_error = models.TextField(blank=True, verbose_name="آخر خطأ")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")
    processed_at = models.DateTimeField(null=True, blank=True, verbose_name="تاريخ المعالجة")
    
    class Meta:
        verbose_name = "قائمة انتظار الإشعارات"
        verbose_name_plural = "قوائم انتظار الإشعارات"
        ordering = ['scheduled_for']
        indexes = [
            models.Index(fields=['status', 'scheduled_for']),
        ]
    
    def __str__(self):
        return f"قائمة انتظار: {self.notification.title}"
    
    def can_retry(self):
        """التحقق من إمكانية إعادة المحاولة"""
        return self.attempts < self.max_attempts and self.status == 'failed'


# ===== Spare Parts Models =====

class Supplier(models.Model):
    """نموذج المورد"""
    name = models.CharField(max_length=200, verbose_name="اسم المورد", default='')
    code = models.CharField(max_length=50, unique=True, verbose_name="كود المورد", default='')
    
    # Contact information
    contact_person = models.CharField(max_length=200, blank=True, verbose_name="الشخص المسؤول")
    phone = models.CharField(max_length=20, blank=True, verbose_name="الهاتف")
    email = models.EmailField(blank=True, verbose_name="البريد الإلكتروني")
    website = models.URLField(blank=True, verbose_name="الموقع الإلكتروني")
    
    # Address
    address = models.TextField(blank=True, verbose_name="العنوان")
    city = models.CharField(max_length=100, blank=True, verbose_name="المدينة")
    country = models.CharField(max_length=100, blank=True, verbose_name="البلد")
    postal_code = models.CharField(max_length=20, blank=True, verbose_name="الرمز البريدي")
    
    # Business details
    tax_number = models.CharField(max_length=50, blank=True, verbose_name="الرقم الضريبي")
    commercial_register = models.CharField(max_length=50, blank=True, verbose_name="السجل التجاري")
    
    # Status and ratings
    status = models.CharField(max_length=20, choices=SUPPLIER_STATUS_CHOICES, default='active', verbose_name="الحالة")
    rating = models.PositiveIntegerField(
        choices=[(i, str(i)) for i in range(1, 6)], 
        null=True, 
        blank=True,
        verbose_name="التقييم"
    )
    
    # Financial terms
    payment_terms = models.CharField(max_length=200, blank=True, verbose_name="شروط الدفع")
    credit_limit = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, verbose_name="حد الائتمان")
    
    # Notes
    notes = models.TextField(blank=True, verbose_name="ملاحظات")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="تم الإنشاء بواسطة")
    
    class Meta:
        verbose_name = "مورد"
        verbose_name_plural = "الموردين"
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.code})"


class SparePart(models.Model):
    """نموذج قطعة الغيار"""
    name = models.CharField(max_length=200, verbose_name="اسم قطعة الغيار", default='')
    part_number = models.CharField(max_length=100, unique=True, verbose_name="رقم القطعة", default='')
    description = models.TextField(blank=True, verbose_name="الوصف")
    
    # Categorization
    device_category = models.ForeignKey(
        DeviceCategory, 
        on_delete=models.CASCADE, 
        related_name='spare_parts',
        verbose_name="فئة الجهاز"
    )
    manufacturer = models.CharField(max_length=200, blank=True, verbose_name="الشركة المصنعة")
    model_number = models.CharField(max_length=100, blank=True, verbose_name="رقم الموديل")
    
    # Inventory details
    unit = models.CharField(max_length=20, choices=UNIT_CHOICES, default='piece', verbose_name="الوحدة")
    current_stock = models.PositiveIntegerField(default=0, verbose_name="المخزون الحالي")
    minimum_stock = models.PositiveIntegerField(default=1, verbose_name="الحد الأدنى للمخزون")
    maximum_stock = models.PositiveIntegerField(null=True, blank=True, verbose_name="الحد الأقصى للمخزون")
    reorder_point = models.PositiveIntegerField(null=True, blank=True, verbose_name="نقطة إعادة الطلب")
    
    # Pricing
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="تكلفة الوحدة")
    last_purchase_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="آخر سعر شراء")
    
    # Supplier information
    primary_supplier = models.ForeignKey(
        Supplier, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='primary_parts',
        verbose_name="المورد الأساسي"
    )
    alternative_suppliers = models.ManyToManyField(
        'Supplier', 
        blank=True,
        related_name='alternative_parts_v2',
        verbose_name="الموردين البديلين"
    )
    
    # Location and storage
    storage_location = models.CharField(max_length=200, blank=True, verbose_name="موقع التخزين")
    shelf_life_months = models.PositiveIntegerField(null=True, blank=True, verbose_name="مدة الصلاحية (شهور)")
    
    # Status and flags
    status = models.CharField(max_length=20, choices=SPARE_PART_STATUS_CHOICES, default='available', verbose_name="الحالة")
    is_critical = models.BooleanField(default=False, verbose_name="حرج")
    is_consumable = models.BooleanField(default=False, verbose_name="مستهلك")
    
    # Compatibility
    compatible_devices = models.ManyToManyField(
        'Device', 
        blank=True,
        related_name='compatible_spare_parts',
        verbose_name="الأجهزة المتوافقة"
    )
    
    # Images and documents
    image = models.ImageField(upload_to='spare_parts/', blank=True, null=True, verbose_name="الصورة")
    datasheet = models.FileField(upload_to='spare_parts/datasheets/', blank=True, null=True, verbose_name="ورقة البيانات")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="تم الإنشاء بواسطة")
    
    class Meta:
        verbose_name = "قطعة غيار"
        verbose_name_plural = "قطع الغيار"
        ordering = ['name']
        indexes = [
            models.Index(fields=['part_number']),
            models.Index(fields=['status', 'current_stock']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.part_number})"
    
    def is_low_stock(self):
        """التحقق من انخفاض المخزون"""
        return self.current_stock <= self.minimum_stock
    
    def is_out_of_stock(self):
        """التحقق من نفاد المخزون"""
        return self.current_stock == 0
    
    def update_status(self):
        """تحديث حالة قطعة الغيار بناءً على المخزون"""
        if self.is_out_of_stock():
            self.status = 'out_of_stock'
        elif self.is_low_stock():
            self.status = 'low_stock'
        else:
            self.status = 'available'
        self.save()
    
    def get_total_value(self):
        """حساب القيمة الإجمالية للمخزون"""
        if self.unit_cost:
            return self.current_stock * self.unit_cost
        return 0


class SparePartTransaction(models.Model):
    """نموذج معاملات قطع الغيار"""
    TRANSACTION_TYPES = [
        ('in', 'وارد'),
        ('out', 'صادر'),
        ('adjustment', 'تعديل'),
        ('return', 'إرجاع'),
    ]
    
    spare_part = models.ForeignKey(
        SparePart, 
        on_delete=models.CASCADE, 
        related_name='transactions',
        verbose_name="قطعة الغيار"
    )
    transaction_type = models.CharField(
        max_length=20, 
        choices=TRANSACTION_TYPES,
        verbose_name="نوع المعاملة"
    )
    quantity = models.PositiveIntegerField(verbose_name="الكمية")
    reference_number = models.CharField(
        max_length=100, 
        blank=True, 
        verbose_name="رقم المرجع"
    )
    notes = models.TextField(blank=True, verbose_name="ملاحظات")
    
    # Optional relationships
    work_order = models.ForeignKey(
        'WorkOrder', 
        on_delete=models.SET_NULL, 
        null=True, blank=True,
        related_name='spare_part_transactions',
        verbose_name="أمر العمل"
    )
    device = models.ForeignKey(
        'Device', 
        on_delete=models.SET_NULL, 
        null=True, blank=True,
        related_name='spare_part_transactions',
        verbose_name="الجهاز"
    )
    
    # Stock levels before and after transaction
    stock_before = models.PositiveIntegerField(verbose_name="المخزون قبل المعاملة")
    stock_after = models.PositiveIntegerField(verbose_name="المخزون بعد المعاملة")
    
    # Timestamps and user tracking
    transaction_date = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ المعاملة")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        verbose_name="تم بواسطة"
    )
    
    class Meta:
        verbose_name = "معاملة قطعة غيار"
        verbose_name_plural = "معاملات قطع الغيار"
        ordering = ['-transaction_date']
        indexes = [
            models.Index(fields=['spare_part', '-transaction_date']),
            models.Index(fields=['transaction_type', '-transaction_date']),
        ]
    
    def __str__(self):
        return f"{self.spare_part.name} - {self.get_transaction_type_display()} ({self.quantity})"


class SparePartRequest(models.Model):
    """نموذج طلبات قطع الغيار من الفنيين"""
    STATUS_CHOICES = [
        ('pending', 'في الانتظار'),
        ('approved', 'موافق عليه'),
        ('rejected', 'مرفوض'),
        ('fulfilled', 'تم التنفيذ'),
        ('cancelled', 'ملغي'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'منخفض'),
        ('medium', 'متوسط'),
        ('high', 'عالي'),
        ('urgent', 'عاجل'),
    ]
    
    # Basic information
    request_number = models.CharField(max_length=20, unique=True, verbose_name="رقم الطلب")
    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='spare_part_requests',
        verbose_name="مقدم الطلب"
    )
    
    # Request details
    spare_part = models.ForeignKey(
        SparePart,
        on_delete=models.CASCADE,
        related_name='requests',
        verbose_name="قطعة الغيار"
    )
    quantity_requested = models.PositiveIntegerField(verbose_name="الكمية المطلوبة")
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='medium',
        verbose_name="الأولوية"
    )
    
    # Work context
    work_order = models.ForeignKey(
        'WorkOrder',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='spare_part_requests',
        verbose_name="أمر العمل"
    )
    device = models.ForeignKey(
        'Device',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='spare_part_requests',
        verbose_name="الجهاز"
    )
    
    # Request justification
    reason = models.TextField(verbose_name="سبب الطلب")
    notes = models.TextField(blank=True, verbose_name="ملاحظات إضافية")
    
    # Status and approval
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="حالة الطلب"
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='approved_spare_part_requests',
        verbose_name="تمت الموافقة بواسطة"
    )
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name="تاريخ الموافقة")
    approval_notes = models.TextField(blank=True, verbose_name="ملاحظات الموافقة")
    
    # Fulfillment
    quantity_approved = models.PositiveIntegerField(null=True, blank=True, verbose_name="الكمية المعتمدة")
    fulfilled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='fulfilled_spare_part_requests',
        verbose_name="تم التنفيذ بواسطة"
    )
    fulfilled_at = models.DateTimeField(null=True, blank=True, verbose_name="تاريخ التنفيذ")
    
    # Related transaction
    transaction = models.OneToOneField(
        SparePartTransaction,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='request',
        verbose_name="المعاملة المرتبطة"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")
    
    class Meta:
        verbose_name = "طلب قطعة غيار"
        verbose_name_plural = "طلبات قطع الغيار"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['priority', '-created_at']),
            models.Index(fields=['requester', '-created_at']),
        ]
    
    def __str__(self):
        return f"طلب {self.request_number} - {self.spare_part.name}"
    
    def save(self, *args, **kwargs):
        if not self.request_number:
            # Generate unique request number
            from django.utils import timezone
            today = timezone.now().strftime('%Y%m%d')
            last_request = SparePartRequest.objects.filter(
                request_number__startswith=f'REQ-{today}'
            ).order_by('-request_number').first()
            
            if last_request:
                last_num = int(last_request.request_number.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1
            
            self.request_number = f'REQ-{today}-{new_num:03d}'
        
        super().save(*args, **kwargs)
    
    def can_approve(self):
        """التحقق من إمكانية الموافقة على الطلب"""
        return self.status == 'pending'
    
    def can_fulfill(self):
        """التحقق من إمكانية تنفيذ الطلب"""
        return self.status in ['pending', 'approved']
    
    def get_priority_color(self):
        """إرجاع لون الأولوية للعرض"""
        colors = {
            'low': 'success',
            'medium': 'info',
            'high': 'warning',
            'urgent': 'danger'
        }
        return colors.get(self.priority, 'secondary')


# ================================================================
# COMPLEMENTARY MODELS FOR FORMS COMPATIBILITY
# ================================================================

# WorkOrder extra fields used in forms
if not hasattr(WorkOrder, 'assignee'):
    WorkOrder.add_to_class('assignee', models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='workorders_assigned'
    ))

if not hasattr(WorkOrder, 'completion_notes'):
    WorkOrder.add_to_class('completion_notes', models.TextField(blank=True, null=True))

if not hasattr(WorkOrder, 'qa_notes'):
    WorkOrder.add_to_class('qa_notes', models.TextField(blank=True, null=True))


class WorkOrderComment(models.Model):
    """تعليقات على أوامر الشغل"""
    work_order = models.ForeignKey(WorkOrder, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment by {self.user} on {self.work_order}"


# Extend SLADefinition to match form
if not hasattr(SLADefinition, 'severity'):
    SLADefinition.add_to_class('severity', models.CharField(
        max_length=20,
        choices=[
            ('critical', 'حرج'),
            ('high', 'عالي'),
            ('medium', 'متوسط'),
            ('low', 'منخفض'),
        ],
        default='medium'
    ))
if not hasattr(SLADefinition, 'device_category'):
    SLADefinition.add_to_class('device_category', models.ForeignKey(
        'DeviceCategory', on_delete=models.SET_NULL, null=True, blank=True
    ))


# Extend JobPlan to match form
if not hasattr(JobPlan, 'job_type'):
    JobPlan.add_to_class('job_type', models.CharField(max_length=100, blank=True, null=True))
if not hasattr(JobPlan, 'estimated_hours'):
    JobPlan.add_to_class('estimated_hours', models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True))
if not hasattr(JobPlan, 'instructions'):
    JobPlan.add_to_class('instructions', models.TextField(blank=True, null=True))


# Extend PreventiveMaintenanceSchedule to match form
if not hasattr(PreventiveMaintenanceSchedule, 'name'):
    PreventiveMaintenanceSchedule.add_to_class('name', models.CharField(max_length=200, default='PM Schedule'))
if not hasattr(PreventiveMaintenanceSchedule, 'description'):
    PreventiveMaintenanceSchedule.add_to_class('description', models.TextField(blank=True, null=True))
if not hasattr(PreventiveMaintenanceSchedule, 'interval_days'):
    PreventiveMaintenanceSchedule.add_to_class('interval_days', models.PositiveIntegerField(default=30))
if not hasattr(PreventiveMaintenanceSchedule, 'start_date'):
    PreventiveMaintenanceSchedule.add_to_class('start_date', models.DateField(null=True, blank=True))
if not hasattr(PreventiveMaintenanceSchedule, 'end_date'):
    PreventiveMaintenanceSchedule.add_to_class('end_date', models.DateField(null=True, blank=True))
if not hasattr(PreventiveMaintenanceSchedule, 'assignee'):
    PreventiveMaintenanceSchedule.add_to_class('assignee', models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='pm_assigned'
    ))
if not hasattr(PreventiveMaintenanceSchedule, 'day_of_week'):
    PreventiveMaintenanceSchedule.add_to_class('day_of_week', models.CharField(max_length=20, blank=True, null=True))
if not hasattr(PreventiveMaintenanceSchedule, 'day_of_month'):
    PreventiveMaintenanceSchedule.add_to_class('day_of_month', models.PositiveIntegerField(null=True, blank=True))


# Extend Supplier to match form
if not hasattr(Supplier, 'website'):
    Supplier.add_to_class('website', models.URLField(blank=True, null=True))


# Extend SparePart to match form
if not hasattr(SparePart, 'storage_location'):
    SparePart.add_to_class('storage_location', models.CharField(max_length=200, blank=True, null=True))
if not hasattr(SparePart, 'image'):
    SparePart.add_to_class('image', models.ImageField(upload_to="spare_parts/", blank=True, null=True))
if not hasattr(SparePart, 'device_category'):
    SparePart.add_to_class('device_category', models.ForeignKey(
        'DeviceCategory', on_delete=models.SET_NULL, null=True, blank=True
    ))


# DeviceTransfer alias for forms
class DeviceTransfer(DeviceTransferLog):
    class Meta:
        proxy = True


# ═══════════════════════════════════════════════════════════════════════════
# DYNAMIC QR OPERATION SYSTEM MODELS
# ═══════════════════════════════════════════════════════════════════════════

class OperationDefinition(models.Model):
    """Define reusable operations that can be triggered by QR scan sequences"""
    name = models.CharField(max_length=100, unique=True, verbose_name="اسم العملية")
    code = models.CharField(max_length=50, unique=True, verbose_name="رمز العملية")
    description = models.TextField(blank=True, verbose_name="الوصف")
    is_active = models.BooleanField(default=True, verbose_name="نشط")
    
    # Operation behavior
    auto_execute = models.BooleanField(default=True, verbose_name="تنفيذ تلقائي")
    requires_confirmation = models.BooleanField(default=False, verbose_name="يتطلب تأكيد")
    
    # Session settings
    session_timeout_minutes = models.PositiveIntegerField(default=10, verbose_name="مهلة الجلسة (دقائق)")
    allow_multiple_executions = models.BooleanField(default=True, verbose_name="السماح بتنفيذ متعدد")
    
    # Logging settings
    log_to_usage = models.BooleanField(default=False, verbose_name="تسجيل في سجل الاستخدام")
    log_to_transfer = models.BooleanField(default=False, verbose_name="تسجيل في سجل النقل")
    log_to_handover = models.BooleanField(default=False, verbose_name="تسجيل في سجل التسليم")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "تعريف العملية"
        verbose_name_plural = "تعريفات العمليات"
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.code})"


class OperationStep(models.Model):
    """Define the sequence of entity types required for an operation"""
    ENTITY_TYPE_CHOICES = [
        ('user', 'مستخدم'),
        ('patient', 'مريض'),
        ('device', 'جهاز'),
        ('accessory', 'ملحق'),
        ('bed', 'سرير'),
        ('department', 'قسم'),
        ('room', 'غرفة'),
        ('lab_tube', 'أنبوب مختبر'),
    ]
    
    operation = models.ForeignKey(
        OperationDefinition,
        on_delete=models.CASCADE,
        related_name='steps',
        verbose_name="العملية"
    )
    order = models.PositiveIntegerField(verbose_name="الترتيب")
    entity_type = models.CharField(
        max_length=50,
        choices=ENTITY_TYPE_CHOICES,
        verbose_name="نوع الكيان"
    )
    is_required = models.BooleanField(default=True, verbose_name="مطلوب")
    
    # Validation rules (JSON field for flexibility)
    validation_rule = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="قواعد التحقق",
        help_text="JSON rules for validating the scanned entity"
    )
    
    # Optional: specify exact entity IDs or patterns
    allowed_entity_ids = models.JSONField(
        default=list,
        blank=True,
        verbose_name="معرفات الكيانات المسموحة",
        help_text="List of specific entity IDs allowed for this step"
    )
    
    description = models.CharField(max_length=255, blank=True, verbose_name="وصف الخطوة")
    
    class Meta:
        verbose_name = "خطوة العملية"
        verbose_name_plural = "خطوات العملية"
        ordering = ['operation', 'order']
        unique_together = [['operation', 'order'], ['operation', 'entity_type']]
    
    def __str__(self):
        return f"{self.operation.code} - Step {self.order}: {self.entity_type}"


class OperationExecution(models.Model):
    """Track execution of operations triggered by QR scans"""
    STATUS_CHOICES = [
        ('pending', 'معلق'),
        ('in_progress', 'قيد التنفيذ'),
        ('completed', 'مكتمل'),
        ('failed', 'فشل'),
        ('cancelled', 'ملغي'),
    ]
    
    operation = models.ForeignKey(
        OperationDefinition,
        on_delete=models.CASCADE,
        related_name='executions',
        verbose_name="العملية"
    )
    session = models.ForeignKey(
        ScanSession,
        on_delete=models.CASCADE,
        related_name='operation_executions',
        verbose_name="جلسة المسح"
    )
    executed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="منفذ العملية"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="الحالة"
    )
    
    # Store the scanned entities for this execution
    scanned_entities = models.JSONField(
        default=dict,
        verbose_name="الكيانات الممسوحة",
        help_text="Map of entity_type to entity data"
    )
    
    # Execution metadata
    started_at = models.DateTimeField(auto_now_add=True, verbose_name="وقت البدء")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="وقت الإكمال")
    
    # Results and logs
    result_data = models.JSONField(default=dict, blank=True, verbose_name="بيانات النتيجة")
    error_message = models.TextField(blank=True, verbose_name="رسالة الخطأ")
    
    # References to created logs
    created_logs = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="السجلات المنشأة",
        help_text="References to logs created by this execution"
    )
    
    class Meta:
        verbose_name = "تنفيذ العملية"
        verbose_name_plural = "تنفيذات العمليات"
        ordering = ['-started_at']
    
    def __str__(self):
        return f"{self.operation.name} - {self.get_status_display()} - {self.started_at}"
    
    def complete(self):
        """Mark execution as completed"""
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.save()
    
    def fail(self, error_message):
        """Mark execution as failed"""
        self.status = 'failed'
        self.error_message = error_message
        self.completed_at = timezone.now()
        self.save()


# Extend ScanSession with operation tracking
if not hasattr(ScanSession, 'context_json'):
    ScanSession.add_to_class('context_json', models.JSONField(default=dict, blank=True, verbose_name="سياق الجلسة"))
if not hasattr(ScanSession, 'last_activity'):
    ScanSession.add_to_class('last_activity', models.DateTimeField(auto_now=True, verbose_name="آخر نشاط"))
if not hasattr(ScanSession, 'current_operation'):
    ScanSession.add_to_class('current_operation', models.ForeignKey(
        OperationDefinition,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='active_sessions',
        verbose_name="العملية الحالية"
    ))
