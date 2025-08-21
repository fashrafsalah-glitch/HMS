# laboratory/models.py
import uuid
from io import BytesIO
from django.db import models
from django.conf import settings
from django.urls import reverse
from django.core.files.base import ContentFile
from django.utils import timezone

import qrcode
from django.db import models
from django.conf import settings
from django.utils import timezone

# افترض هذه الموديلات موجودة
# from .models import TestOrder, LabRequest, Test, Sample
# من مكانها نفسه

class TestResult(models.Model):
    STATUS_DRAFT     = "draft"
    STATUS_VERIFIED  = "verified"
    STATUS_CHOICES   = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_VERIFIED, "Verified"),
    ]

    patient   = models.ForeignKey("manager.Patient", on_delete=models.CASCADE, related_name="test_results")
    order     = models.ForeignKey("laboratory.TestOrder", on_delete=models.CASCADE, related_name="results", null=True, blank=True)
    request   = models.ForeignKey("laboratory.LabRequest", on_delete=models.CASCADE, related_name="results", null=True, blank=True)
    sample    = models.ForeignKey("laboratory.Sample", on_delete=models.SET_NULL, null=True, blank=True)
    test      = models.ForeignKey("laboratory.Test", on_delete=models.PROTECT)

    observed_at    = models.DateTimeField(default=timezone.now)
    observed_value = models.CharField(max_length=255, blank=True)  # نص
    value_num      = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # رقمي اختياري
    unit           = models.CharField(max_length=50, blank=True)
    ref_min        = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    ref_max        = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    result_file = models.FileField("Attached File", upload_to="lab_results/", blank=True, null=True)

    uploaded_at = models.DateTimeField("Uploaded At", auto_now_add=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="Uploaded By"
    )
    status      = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    notes       = models.TextField(blank=True)
    verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="verified_results")
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-observed_at", "-id"]

    def __str__(self):
        return f"{self.patient} - {self.test} - {self.observed_value or self.value_num or ''}"

    @property
    def is_abnormal(self):
        if self.value_num is None:
            return False
        low = (self.ref_min is not None and self.value_num < self.ref_min)
        high = (self.ref_max is not None and self.value_num > self.ref_max)
        return low or high




# -------- مرجع التحاليل والمجموعات --------
class TestGroup(models.Model):
    name = models.CharField(max_length=100, unique=True)
    tests = models.ManyToManyField("Test", blank=True, related_name="groups")

    def __str__(self):
        return self.name


class Test(models.Model):
    CATEGORY_CHOICES = [
        ("blood", "Blood"),
        ("urine", "Urine"),
        ("microbio", "Microbiology"),
        ("other", "Other"),
    ]
    RESULT_TYPE_NUMERIC = "numeric"
    RESULT_TYPE_BOOLEAN = "boolean"
    RESULT_TYPE_TEXT    = "text"
    RESULT_TYPE_CHOICES = [
        (RESULT_TYPE_NUMERIC, "Numeric"),
        (RESULT_TYPE_BOOLEAN, "Positive/Negative"),
        (RESULT_TYPE_TEXT,    "Text"),
    ]

    english_name = models.CharField(max_length=200)
    arabic_name = models.CharField(max_length=100, blank=True, null=True)  # ← أضف هذا السطر
    category     = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default="blood")
    group = models.ForeignKey(
        "TestGroup",
        on_delete=models.SET_NULL,
        related_name="test_items",  # ✅ بدلًا من "tests"
        blank=True,
        null=True,
        verbose_name="Test Group"
    )
    unit         = models.CharField(max_length=50, blank=True)
    ref_min      = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    ref_max      = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    result_type  = models.CharField(max_length=20, choices=RESULT_TYPE_CHOICES, default=RESULT_TYPE_NUMERIC)
    active       = models.BooleanField(default=True)

    class Meta:
        ordering = ["category", "english_name"]
        unique_together = [("english_name", "category")]

    def __str__(self):
        return self.english_name


# -------- طلب المختبر (الرأس) --------
class LabRequest(models.Model):

   @property
   def first_open_item(self):
        """
        أول عنصر (تحليل) غير مُعتمد – لاستخدامه في زر 'إدخال النتائج' من الداشبورد.
        """
        return self.items.exclude(status=LabRequestItem.STATUS_VERIFIED).order_by("id").first()
   STATUS_SUBMITTED  = "submitted"   # تم الطلب
   STATUS_ACCEPTED   = "accepted"    # تم قبول الطلب وتجهيز الأنابيب
   STATUS_COLLECTED  = "collected"   # تم سحب العينة
   STATUS_DISPATCHED = "dispatched"  # تم إرسال العينة للمعمل
   STATUS_RECEIVED   = "received"    # تم استلامها في المعمل
   STATUS_COMPLETED  = "completed"   # تم إدخال النتائج كلها
   STATUS_CHOICES = [
        (STATUS_SUBMITTED,  "Submitted"),
        (STATUS_ACCEPTED,   "Accepted"),
        (STATUS_COLLECTED,  "Collected"),
        (STATUS_DISPATCHED, "Dispatched"),
        (STATUS_RECEIVED,   "Received"),
        (STATUS_COMPLETED,  "Completed"),
    ]

   patient   = models.ForeignKey("manager.Patient", on_delete=models.CASCADE, related_name="lab_requests")
   group     = models.ForeignKey(TestGroup, on_delete=models.SET_NULL, null=True, blank=True)
   
   tests     = models.ManyToManyField('laboratory.Test', blank=True, related_name='lab_requests')

   status    = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_SUBMITTED)
   token     = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
   qr_code   = models.ImageField(upload_to="lab_request_qr/", blank=True)

   requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="lab_requests_created")
   requested_at = models.DateTimeField(auto_now_add=True)

    # طوابع مراحل عامة للطلب
   accepted_at   = models.DateTimeField(null=True, blank=True)
   accepted_by   = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="lab_requests_accepted")

   collected_at  = models.DateTimeField(null=True, blank=True)
   collected_by  = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="lab_requests_collected")

   dispatched_at = models.DateTimeField(null=True, blank=True)
   dispatched_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="lab_requests_dispatched")

   received_at   = models.DateTimeField(null=True, blank=True)
   received_by   = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="lab_requests_received")

   completed_at  = models.DateTimeField(null=True, blank=True)
   completed_by   = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="lab_requests_completed")

   class Meta:
        ordering = ["-requested_at"]

   def __str__(self):
        return f"LabRequest #{self.pk} for {self.patient}"

   def get_scan_url(self):
        return reverse("laboratory:lab_request_scan", args=[str(self.token)])

   def _generate_qr(self):
        img = qrcode.make(self.get_scan_url())
        buf = BytesIO(); img.save(buf, format="PNG")
        return ContentFile(buf.getvalue(), name=f"{self.token}.png")

def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new or not self.qr_code:
            self.qr_code.save(f"{self.token}.png", self._generate_qr(), save=False)
            super().save(update_fields=["qr_code"])

@property
def all_items_completed(self):
        return not self.items.exclude(status=LabRequestItem.STATUS_VERIFIED).exists()


# -------- عنصر طلب (تحليل واحد داخل الطلب) + تتبع/نتائج --------
class LabRequestItem(models.Model):
    STATUS_PENDING   = "pending"    # بانتظار التنفيذ/السحب
    STATUS_IN_LAB    = "in_lab"     # وصل للمعمل
    STATUS_MEASURING = "measuring"  # قيد القياس/التشغيل
    STATUS_REVIEW    = "review"     # قيد المراجعة
    STATUS_VERIFIED  = "verified"   # تم الاعتماد
    STATUS_CHOICES = [
        (STATUS_PENDING,   "Pending"),
        (STATUS_IN_LAB,    "In Lab"),
        (STATUS_MEASURING, "Measuring"),
        (STATUS_REVIEW,    "In Review"),
        (STATUS_VERIFIED,  "Verified"),
    ]

    request = models.ForeignKey(LabRequest, on_delete=models.CASCADE, related_name="items")
    test    = models.ForeignKey(Test, on_delete=models.PROTECT, related_name="request_items")

    # كود تتبع للأنبوب/العينة للعنصر
    sample_token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    sample_qr    = models.ImageField(upload_to="lab_samples_qr/", blank=True)

    # مراحل لكل عنصر (كمان نحتفظ بمن نفّذها)
    tube_prepared_at = models.DateTimeField(null=True, blank=True)
    tube_prepared_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="lab_items_tube_prep")

    sample_collected_at = models.DateTimeField(null=True, blank=True)
    sample_collected_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="lab_items_collected")

    sample_dispatched_at = models.DateTimeField(null=True, blank=True)
    sample_dispatched_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="lab_items_dispatched")

    sample_received_at = models.DateTimeField(null=True, blank=True)
    sample_received_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="lab_items_received")

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)

    # -------- النتيجة (حسب نوع التحليل) --------
    # Numeric
    value_num = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    ref_min   = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    ref_max   = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)

    # Boolean (+/-)
    value_bool = models.BooleanField(null=True, blank=True, default=None)  # True=Positive, False=Negative

    # Text
    value_text = models.TextField(blank=True)

    unit       = models.CharField(max_length=50, blank=True)
    notes      = models.TextField(blank=True)

    observed_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="lab_items_verified")
    verified_at = models.DateTimeField(null=True, blank=True)

    def get_absolute_url(self):
        return reverse("laboratory:lab_request_detail", args=[self.request_id])

    class Meta:
        ordering = ["test__english_name"]
        unique_together = [("request", "test")]

    def __str__(self):
        return f"{self.request_id} – {self.test.english_name}"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new or not self.sample_qr:
            img = qrcode.make(reverse("laboratory:sample_scan", args=[str(self.sample_token)]))
            buf = BytesIO(); img.save(buf, format="PNG")
            self.sample_qr.save(f"{self.sample_token}.png", ContentFile(buf.getvalue()), save=False)
            super().save(update_fields=["sample_qr"])

    @property
    def result_display(self):
        if self.test.result_type == Test.RESULT_TYPE_NUMERIC:
            if self.value_num is None:
                return "—"
            return f"{self.value_num} {self.unit or ''}".strip()
        if self.test.result_type == Test.RESULT_TYPE_BOOLEAN:
            if self.value_bool is None:
                return "—"
            return "Positive" if self.value_bool else "Negative"
        # TEXT
        return self.value_text or "—"

    @property
    def is_abnormal(self):
        if self.test.result_type != Test.RESULT_TYPE_NUMERIC or self.value_num is None:
            return False
        if self.ref_min is not None and self.value_num < self.ref_min:
            return True
        if self.ref_max is not None and self.value_num > self.ref_max:
            return True
        return False

    # مدد زمنية مبسّطة (مثال)
    def duration_to_collect(self):
        if self.request.accepted_at and self.sample_collected_at:
            return self.sample_collected_at - self.request.accepted_at
        return None
    @property
    def display_result(self):
        for name in ("result_display","result_text","result","observed_value","value_text"):
            val = getattr(self, name, None)
            if val:
                return val
        num = getattr(self, "result_num", None)
        if num is None:
            num = getattr(self, "value_num", None)
        if num is not None:
            unit = getattr(self, "unit", None) or getattr(self.test, "unit", "") or ""
            return f"{num} {unit}".strip()
        return "—"
    
class TestOrder(models.Model):
    patient = models.ForeignKey('manager.Patient', on_delete=models.CASCADE, related_name='test_orders')
    tube_type = models.CharField(max_length=50, blank=True)
    requested_at = models.DateTimeField(auto_now_add=True)
    # ...

class Sample(models.Model):
    test_order = models.ForeignKey(TestOrder, on_delete=models.CASCADE, related_name='samples')
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    tube_type = models.CharField(max_length=50, blank=True)
    requested_at = models.DateTimeField(auto_now_add=True)

class TestResult(models.Model):
    test_order = models.ForeignKey(
        'laboratory.TestOrder',
        on_delete=models.CASCADE,
        related_name='results',
        null=True, blank=True   # ← مهم
    )
    result = models.CharField(max_length=255, blank=True, default="")
    def __str__(self):
        return self.result
    
class TestResult(models.Model):
    STATUS_DRAFT    = "draft"
    STATUS_VERIFIED = "verified"
    STATUS_CHOICES  = [(STATUS_DRAFT, "Draft"), (STATUS_VERIFIED, "Verified")]

    patient   = models.ForeignKey("manager.Patient", on_delete=models.CASCADE, related_name="test_results")
    order     = models.ForeignKey("laboratory.TestOrder", on_delete=models.CASCADE, related_name="results", null=True, blank=True)
    request   = models.ForeignKey("laboratory.LabRequest", on_delete=models.CASCADE, related_name="results", null=True, blank=True)
    sample    = models.ForeignKey("laboratory.Sample", on_delete=models.SET_NULL, null=True, blank=True)
    test      = models.ForeignKey("laboratory.Test", on_delete=models.PROTECT)

    observed_at    = models.DateTimeField(default=timezone.now)
    observed_value = models.CharField(max_length=255, blank=True)               # نص
    value_num      = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # رقمي
    unit           = models.CharField(max_length=50, blank=True)
    ref_min        = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    ref_max        = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    status      = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    notes       = models.TextField(blank=True)
    verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="verified_results")
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-observed_at", "-id"]

    def __str__(self):
        disp = self.observed_value or (str(self.value_num) if self.value_num is not None else "")
        return f"{self.patient} - {self.test} - {disp}"

    @property
    def is_abnormal(self):
        if self.value_num is None:
            return False
        low  = (self.ref_min is not None and self.value_num < self.ref_min)
        high = (self.ref_max is not None and self.value_num > self.ref_max)
        return low or high