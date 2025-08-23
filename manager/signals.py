# manager/
from django.db.models.signals import post_save
from django.dispatch          import receiver
from django.utils             import timezone

from .models import Patient, Department, Visit, Bed
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Department, SurgicalOperationsDepartment
from superadmin.models import Hospital  # ← الاستيراد الصحيح

@receiver(post_save, sender=Hospital)
def create_main_surgical_department(sender, instance, created, **kwargs):
    if created:
        # أنشئ قسم العمليات الرئيسي
        main_dept = Department.objects.create(
            name='قسم العمليات الجراحية',
            hospital=instance,
            parent=None  # رئيسي
        )

        # اربطه بوحدة غرف العمليات
        SurgicalOperationsDepartment.objects.create(
            name='غرف العمليات',
            surgical_type='عام',
            location='الدور الأرضي',
            hospital=instance,
            department=main_dept
        )


@receiver(post_save, sender=Patient)
def create_opd_visit(sender, instance, created, **kwargs):
    """
    Every brand-new patient gets an OPEN *out-patient* Visit in the hospital’s
    “OPD” department.  If the hospital doesn’t yet have that department,
    create it on the fly.
    """
    if not created:
        return                                # only run on first save

    # 1️⃣  make sure the hospital has an “OPD” department
    opd_dept, _ = Department.objects.get_or_create(
        hospital       = instance.hospital,
        name           = "OPD",
        defaults       = {
            "department_type": "department",   # or "unit" – up to you
            "is_active":      True,
        },
    )

    # 2️⃣  create the Visit
    Visit.objects.create(
        patient     = instance,
        hospital    = instance.hospital,
        department  = opd_dept,
        visit_type  = "outpatient",
        visit_date  = timezone.now(),
        status      = "active",
    )


# ───────────────────────────  AUTO QR FOR BEDS  ───────────────────────────
@receiver(post_save, sender=Bed, dispatch_uid="bed_generate_qr_on_create")
def bed_generate_qr_on_create(sender, instance, created, **kwargs):
    """
    Ensure every Bed has a QR code.
    - On creation: generate immediately if missing.
    - On update: backfill if qr_code/qr_token are missing.
    """
    # Avoid unnecessary second saves
    needs_qr = (instance.qr_code is None or not getattr(instance.qr_code, "name", None) or not instance.qr_token)
    if created and needs_qr:
        try:
            instance.generate_qr_code()
            # save only the QR fields to avoid recursion/extra work
            instance.save(update_fields=["qr_code", "qr_token"])
        except Exception:
            # Fail silently to not block bed creation; admins can regenerate via UI/API
            pass
    elif (not created) and needs_qr:
        try:
            instance.generate_qr_code()
            instance.save(update_fields=["qr_code", "qr_token"])
        except Exception:
            pass
