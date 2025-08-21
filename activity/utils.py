from django.contrib.contenttypes.models import ContentType
from .models import ActivityLog

def emit_activity(operation_key: str, *, instance=None, user=None, action: str = "", extra: dict | None = None, amount=None):
    """
    يسجّل حدثًا دقيقًا مرتبطًا بموديل معيّن (اختياري) مع تسعير تلقائي.
    """
    ct = obj_id = obj_repr = None
    if instance is not None:
        ct = ContentType.objects.get_for_model(instance.__class__)
        obj_id = getattr(instance, "pk", None)
        obj_repr = str(instance)[:200]

    if amount is None:
        amount = ActivityLog.price_for_key(operation_key)

    return ActivityLog.objects.create(
        user=user,
        operation_key=operation_key,
        action=action or "",
        content_type=ct,
        object_id=str(obj_id) if obj_id is not None else None,
        object_repr=obj_repr or "",
        amount=amount,
        extra=extra or {},
    )