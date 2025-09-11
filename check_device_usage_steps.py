"""
Check DEVICE_USAGE operation steps and settings
"""
import os
import sys
import django

# Set UTF-8 encoding for Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from maintenance.models import OperationDefinition, OperationStep

# Check DEVICE_USAGE operation
try:
    op = OperationDefinition.objects.get(code='DEVICE_USAGE')
    print(f"Operation: {op.name}")
    print(f"Code: {op.code}")
    print(f"Auto Execute: {op.auto_execute}")
    print(f"Requires Confirmation: {op.requires_confirmation}")
    print(f"Allow Multiple Executions: {op.allow_multiple_executions}")
    print(f"Log to Usage: {op.log_to_usage}")
    print(f"Is Active: {op.is_active}")
    
    print("\nSteps:")
    steps = op.steps.order_by('order')
    for step in steps:
        print(f"  Step {step.order}: {step.entity_type} - Required: {step.is_required} - {step.description}")
    
    if steps.count() < 3:
        print("\n⚠️ Missing steps! Creating them...")
        # Ensure we have all 3 steps
        OperationStep.objects.update_or_create(
            operation=op,
            entity_type='user',
            order=1,
            defaults={
                'is_required': True,
                'description': 'مسح بطاقة المستخدم'
            }
        )
        OperationStep.objects.update_or_create(
            operation=op,
            entity_type='device',
            order=2,
            defaults={
                'is_required': True,
                'description': 'مسح الجهاز المراد استخدامه'
            }
        )
        OperationStep.objects.update_or_create(
            operation=op,
            entity_type='patient',
            order=3,
            defaults={
                'is_required': True,
                'description': 'مسح المريض'
            }
        )
        print("✅ Steps created/updated")
        
        # Verify again
        steps = op.steps.order_by('order')
        print("\nSteps after update:")
        for step in steps:
            print(f"  Step {step.order}: {step.entity_type} - Required: {step.is_required}")
            
except OperationDefinition.DoesNotExist:
    print("❌ DEVICE_USAGE operation not found!")
