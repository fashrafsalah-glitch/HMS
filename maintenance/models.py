from django.db import models
from manager.models import Department, Patient, Room

from django.contrib.auth import get_user_model
User = get_user_model()

from django.conf import settings

from manager.models import Bed




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

class Device(models.Model):

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
    related_name='devices_last_cleaned'  # ✅ اسم مميز
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
    related_name='devices_last_sterilized'  # ✅ اسم مميز
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
    related_name='devices_last_maintained'  # ✅ اسم مميز
)
    maintained_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Maintained by {self.maintained_by} on {self.maintained_at.strftime('%Y-%m-%d %H:%M')}"