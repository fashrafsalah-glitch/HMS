from django.db import models
from manager.models import Department, Patient, Room

from django.contrib.auth import get_user_model
User = get_user_model()

from django.conf import settings
from django.core.files.base import ContentFile
from io import BytesIO
import qrcode
import uuid

from manager.models import Bed
from core.qr_utils import QRCodeMixin


# ═══════════════════════════════════════════════════════════════════════════
# EXISTING MODELS
# ═══════════════════════════════════════════════════════════════════════════

# شركات
class Company(models.Model):
    name = models.CharField(max_length=255, verbose_name="اسم الشركة")

    def __str__(self):
        return self.name

# نوع الجهاز
class DeviceType(models.Model):
    name = models.CharField(max_length=255, verbose_name="نوع الجهاز")

    def __str__(self):
        return self.name
    
class DeviceUsage(models.Model):
    name = models.CharField(max_length=255, verbose_name="استخدام الجهاز")

    def __str__(self):
        return self.name    

 # خصائص الحالة
    status = models.CharField(
        max_length=20,
        choices=[
            ('working', 'يعمل'),
            ('needs_maintenance', 'يحتاج صيانة'),
            ('out_of_order', 'عطل دائم'),
            ('needs_check', 'يحتاج تفقد')
        ],
        default='working',
        verbose_name='حالة الجهاز'
    )
    
    availability = models.BooleanField(default=True, verbose_name="متوفر؟")
    
    clean_status = models.CharField(
        max_length=20,
        choices=[
            ('clean', 'نظيف'),
            ('needs_cleaning', 'يحتاج تنظيف'),
            ('unknown', 'غير محدد')
        ],
        default='unknown',
        verbose_name='النظافة'
    )

    sterilization_status = models.CharField(
        max_length=20,
        choices=[
            ('sterilized', 'معقم'),
            ('needs_sterilization', 'يحتاج تعقيم'),
            ('not_required', 'لا يحتاج تعقيم')
        ],
        default='not_required',
        verbose_name='التعقيم'
    )

    # الحقول المرتبطة باستخدام المريض
    in_use = models.BooleanField(default=False, verbose_name="قيد الاستخدام؟")
    current_patient = models.ForeignKey(Patient, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="المريض الحالي", related_name="devices_in_use")
    usage_start_time = models.DateTimeField(null=True, blank=True, verbose_name="بداية الاستخدام")

    def end_usage(self):
        self.in_use = False
        self.current_patient = None
        self.usage_start_time = None
        self.availability = True
        self.clean_status = 'needs_cleaning'
        self.sterilization_status = 'needs_sterilization'
        self.status = 'needs_check'
        self.save()




class DeviceTransferRequest(models.Model):
    device = models.ForeignKey('Device', on_delete=models.CASCADE) 
    from_department = models.ForeignKey(
    Department,
    related_name='device_transfer_requests_from',
    on_delete=models.SET_NULL,
    null=True
)

    to_department = models.ForeignKey(
    Department,
    related_name='device_transfer_requests_to',
    on_delete=models.SET_NULL,
    null=True
)
    from_room = models.ForeignKey(Room, related_name='transfers_from', on_delete=models.CASCADE, null=True, blank=True)
    to_room = models.ForeignKey(Room, on_delete=models.SET_NULL, null=True)
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='transfer_requested_by', on_delete=models.SET_NULL, null=True)
    requested_at = models.DateTimeField(auto_now_add=True)

    is_approved = models.BooleanField(default=False)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='transfer_approved_by', on_delete=models.SET_NULL, null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.device.name} to {self.to_department.name} (approved: {self.is_approved})"



class DeviceCategory(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class DeviceSubCategory(models.Model):
    name = models.CharField(max_length=100)
    category = models.ForeignKey(DeviceCategory, on_delete=models.CASCADE, related_name='subcategories')

    def __str__(self):
        return f"{self.category.name} - {self.name}"

class Device(QRCodeMixin, models.Model):

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

# قائمة خيارات حالة الجهاز
    DEVICE_STATUS_CHOICES = [
    ('working', 'يعمل'),
    ('needs_maintenance', 'يحتاج صيانة'),
    ('out_of_order', 'عطل دائم'),
    ('needs_check', 'يحتاج تفقد'),
]
    
    status = models.CharField(
    max_length=20,
    choices=DEVICE_STATUS_CHOICES,
    default='working',
    verbose_name="حالة الجهاز"
) 
    
    CLEAN_STATUS_CHOICES = [
    ('clean', 'نظيف'),
    ('needs_cleaning', 'يحتاج تنظيف'),
    ('unknown', 'غير معروف'),
]

    STERILIZATION_STATUS_CHOICES = [
    ('sterilized', 'معقم'),
    ('needs_sterilization', 'يحتاج تعقيم'),
    ('unknown', 'غير معروف'),
]

    clean_status = models.CharField(
    max_length=20,
    choices=CLEAN_STATUS_CHOICES,
    default='unknown',
    verbose_name="حالة النظافة"
)

    sterilization_status = models.CharField( 
    max_length=20,
    choices=STERILIZATION_STATUS_CHOICES,
    default='unknown',
    verbose_name="حالة التعقيم"
)   
    # Basic Info (Required)
    id = models.AutoField(primary_key=True)  # ← رقم تسلسلي تلقائي

    name = models.CharField(max_length=200)  # ← اسم الجهاز الجديد

    category = models.ForeignKey(DeviceCategory, on_delete=models.CASCADE)
    subcategory = models.ForeignKey(DeviceSubCategory, on_delete=models.SET_NULL, null=True, blank=True)
    brief_description = models.TextField()
    manufacturer = models.CharField(max_length=100)
    model = models.CharField(max_length=100)
    serial_number = models.CharField(max_length=100)

    last_cleaned_by = models.ForeignKey( settings.AUTH_USER_MODEL,  on_delete=models.SET_NULL, null=True,
        blank=True,related_name='devices_cleaned' )
    last_cleaned_at = models.DateTimeField(null=True, blank=True)

    last_sterilized_by = models.ForeignKey( settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        blank=True,  related_name='devices_sterilized')
    last_sterilized_at = models.DateTimeField(null=True, blank=True)

    last_maintained_by = models.ForeignKey( settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        blank=True, related_name='devices_maintained'  )

    last_maintained_at = models.DateTimeField(null=True, blank=True)


    # العلاقات الأساسية
    manufacture_company = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True, blank=True, related_name='manufactured_devices', verbose_name="شركة التصنيع")
    supplier_company = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True, blank=True, related_name='supplied_devices', verbose_name="شركة التوريد")
    maintenance_company = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True, blank=True, related_name='maintained_devices', verbose_name="شركة الصيانة")
    device_type = models.ForeignKey(DeviceType, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="نوع الجهاز")
    device_usage = models.ForeignKey(DeviceUsage, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="استخدام الجهاز")

    # خصائص ديناميكية
    status = models.CharField(max_length=20, choices=DEVICE_STATUS_CHOICES, default='working', verbose_name="حالة الجهاز")
    availability = models.BooleanField(default=True, verbose_name="هل متاح؟")
    clean_status = models.CharField(max_length=20, choices=CLEAN_STATUS_CHOICES, default='unknown', verbose_name="حالة النظافة")
    sterilization_status = models.CharField(max_length=20, choices=STERILIZATION_STATUS_CHOICES, default='not_required', verbose_name="حالة التعقيم")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإضافة")

    
    production_date = models.DateField()
    

    # الموقع الحالي للجهاز (مطلوب)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='devices')
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='devices')
    bed = models.ForeignKey(Bed, on_delete=models.SET_NULL, null=True, blank=True)  # حقل اختياري
    current_patient = models.ForeignKey(
    Patient,
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    verbose_name="المريض الحالي"
)

    # Optional Details - to be added later
    technical_specifications = models.TextField(blank=True, null=True)
    classification = models.CharField(max_length=100, blank=True, null=True)
    uses = models.TextField(blank=True, null=True)
    complications_risks = models.TextField(blank=True, null=True)
    half_life = models.CharField(max_length=100, blank=True, null=True)
   
    def __str__(self):
     return f"{self.id} - {self.model}"
    
current_patient = models.ForeignKey(
    'patients.Patient',
    on_delete=models.SET_NULL,
    null=True,
    blank=True
)


class DeviceCleaningLog(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='cleaning_logs')
    last_cleaned_by = models.ForeignKey(
    settings.AUTH_USER_MODEL,
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name='devices_last_cleaned'  # اسم مميز
)
    cleaned_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Cleaned by {self.last_cleaned_by} on {self.cleaned_at.strftime('%Y-%m-%d %H:%M')}"

class DeviceSterilizationLog(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='sterilization_logs')
    last_sterilized_by = models.ForeignKey(
    settings.AUTH_USER_MODEL,
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name='devices_last_sterilized'  # اسم مميز
)
    sterilized_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Sterilized by {self.sterilized_by} on {self.sterilized_at.strftime('%Y-%m-%d %H:%M')}"

class DeviceMaintenanceLog(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='maintenance_logs')
    last_maintained_by = models.ForeignKey(
    settings.AUTH_USER_MODEL,
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name='devices_last_maintained'  # اسم مميز
)
    maintained_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Maintained by {self.last_maintained_by} on {self.maintained_at.strftime('%Y-%m-%d %H:%M')}"

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
        ('other', 'أخرى'),
    ]
    
    # Session info
    session_id = models.UUIDField(default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name="المستخدم"
    )
    
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
    
    # Operation details
    operation_type = models.CharField(
        max_length=20,
        choices=OPERATION_CHOICES,
        default='other',
        verbose_name="نوع العملية"
    )
    notes = models.TextField(blank=True, null=True, verbose_name="ملاحظات")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="وقت الإنشاء")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="وقت الإكمال")
    
    # Status
    is_completed = models.BooleanField(default=False, verbose_name="مكتملة؟")
    
    class Meta:
        verbose_name = "سجل استخدام الأجهزة"
        verbose_name_plural = "سجلات استخدام الأجهزة"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Session {self.session_id} - {self.user.get_full_name()} - {self.get_operation_type_display()}"


class DeviceUsageLogItem(models.Model):
    """Individual devices/accessories used in a session"""
    usage_log = models.ForeignKey(
        DeviceUsageLog,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name="سجل الاستخدام"
    )
    device = models.ForeignKey(
        Device,
        on_delete=models.CASCADE,
        verbose_name="الجهاز"
    )
    scanned_at = models.DateTimeField(auto_now_add=True, verbose_name="وقت المسح")
    notes = models.CharField(max_length=255, blank=True, null=True, verbose_name="ملاحظات")
    
    class Meta:
        verbose_name = "عنصر سجل استخدام الجهاز"
        verbose_name_plural = "عناصر سجل استخدام الأجهزة"
        unique_together = ['usage_log', 'device']
    
    def __str__(self):
        return f"{self.device} في {self.usage_log}"


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
    scanned_code = models.CharField(max_length=100, verbose_name="الكود الممسوح")
    entity_type = models.CharField(max_length=50, verbose_name="نوع الكيان")
    entity_id = models.IntegerField(verbose_name="معرف الكيان")
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
        related_name='device_transfers_from',
        verbose_name="من القسم"
    )
    from_room = models.ForeignKey(
        Room,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='device_transfers_from',
        verbose_name="من الغرفة"
    )
    from_bed = models.ForeignKey(
        Bed,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='device_transfers_from',
        verbose_name="من السرير"
    )
    
    # To location
    to_department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='device_transfers_to',
        verbose_name="إلى القسم"
    )
    to_room = models.ForeignKey(
        Room,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='device_transfers_to',
        verbose_name="إلى الغرفة"
    )
    to_bed = models.ForeignKey(
        Bed,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='device_transfers_to',
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
    name = models.CharField(max_length=255, verbose_name="اسم الملحق")
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
        DeviceUsageLog,
        on_delete=models.CASCADE,
        related_name='accessory_items',
        verbose_name="سجل الاستخدام"
    )
    accessory = models.ForeignKey(
        DeviceAccessory,
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