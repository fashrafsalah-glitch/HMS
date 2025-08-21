from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.db import models
from django.utils import timezone
from decimal import Decimal

class OperationPrice(models.Model):
    """
    تسعير حسب مفتاح العملية الدقيق (مثال: 'patient.create')
    مع دعم fallback: 'patient.*' ثم '*'
    """
    operation_key = models.CharField(max_length=100, unique=True, help_text="مثال: patient.create / patient.* / *")
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))

    def __str__(self):
        return f"{self.operation_key} = {self.amount}"


class ActivityLog(models.Model):
    """
    سجل نشاط تفصيلي مرتبط بموديل معيّن ومفتاح عملية دقيق (Domain-aware).
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                             on_delete=models.SET_NULL, related_name="activity_logs")

    # مثال: patient.create / lab.test.delete / lab.result.update
    operation_key = models.CharField(max_length=100)

    # اختياري: CRUD عام لو حبيت الفلترة به (create/update/delete/login/logout)
    action = models.CharField(max_length=10, blank=True)

    timestamp = models.DateTimeField(default=timezone.now)

    content_type = models.ForeignKey(ContentType, null=True, blank=True, on_delete=models.SET_NULL)
    object_id = models.CharField(max_length=64, null=True, blank=True)
    content_object = GenericForeignKey("content_type", "object_id")
    object_repr = models.CharField(max_length=200, blank=True)

    amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    extra = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["user", "operation_key", "timestamp"]),
            models.Index(fields=["content_type", "object_id"]),
        ]

    def __str__(self):
        who = self.user or "System"
        return f"{who} {self.operation_key} @ {self.timestamp:%Y-%m-%d %H:%M}"

    @classmethod
    def price_for_key(cls, operation_key: str):
        """
        يبحث عن السعر بهذا الترتيب:
        1) exact: patient.create
        2) prefixes: patient.* (ثم الأقصر فالأقصر)
        3) global: *
        """
        from .models import OperationPrice
        # exact
        p = OperationPrice.objects.filter(operation_key=operation_key).first()
        if p:
            return p.amount
        # prefix.*
        parts = operation_key.split(".")
        while len(parts) > 0:
            pref = ".".join(parts) + ".*"
            p = OperationPrice.objects.filter(operation_key=pref).first()
            if p:
                return p.amount
            parts.pop()
        # global
        p = OperationPrice.objects.filter(operation_key="*").first()
        return p.amount if p else Decimal("0.00")