import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from maintenance.models import OperationDefinition

# Check DEVICE_USAGE and END_DEVICE_USAGE
ops = OperationDefinition.objects.filter(code__in=['DEVICE_USAGE', 'END_DEVICE_USAGE']).order_by('id')
for op in ops:
    print(f"\n{op.code} (ID:{op.id}):")
    print(f"  auto_execute={op.auto_execute}")
    print(f"  requires_confirmation={op.requires_confirmation}")
    print(f"  Steps:")
    for step in op.steps.order_by('order'):
        print(f"    {step.order}: {step.entity_type} (required={step.is_required})")

# The problem: Both have same steps, so first match wins
# Solution: DEVICE_USAGE should be checked before END_DEVICE_USAGE
print("\n\nOrder in database:")
all_ops = OperationDefinition.objects.filter(is_active=True).order_by('id')
for op in all_ops:
    if op.steps.count() == 3:
        print(f"  {op.id}: {op.code}")
