"""
Script to create missing QR operations with correct steps
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

# Dictionary of operations to create/update
operations_config = {
    'END_DEVICE_USAGE': {
        'name': 'إنهاء استخدام الجهاز',
        'description': 'إنهاء ربط جهاز بمريض وتحرير الجهاز',
        'auto_execute': True,
        'requires_confirmation': False,
        'log_to_usage': True,
        'steps': [
            {'entity_type': 'user', 'order': 1, 'is_required': True, 'description': 'مسح بطاقة المستخدم'},
            {'entity_type': 'device', 'order': 2, 'is_required': True, 'description': 'مسح الجهاز المراد إنهاء استخدامه'},
            {'entity_type': 'patient', 'order': 3, 'is_required': True, 'description': 'مسح المريض المرتبط بالجهاز'}
        ]
    },
    'MAINTENANCE_OPEN': {
        'name': 'فتح أمر صيانة',
        'description': 'فتح أمر صيانة جديد للجهاز',
        'auto_execute': True,
        'requires_confirmation': False,
        'log_to_handover': False,
        'steps': [
            {'entity_type': 'user', 'order': 1, 'is_required': True, 'description': 'مسح بطاقة الفني'},
            {'entity_type': 'device', 'order': 2, 'is_required': True, 'description': 'مسح الجهاز المعطل'}
        ]
    },
    'MAINTENANCE_CLOSE': {
        'name': 'إغلاق أمر صيانة',
        'description': 'إغلاق أمر صيانة مفتوح',
        'auto_execute': True,
        'requires_confirmation': False,
        'log_to_handover': False,
        'steps': [
            {'entity_type': 'user', 'order': 1, 'is_required': True, 'description': 'مسح بطاقة الفني'},
            {'entity_type': 'device', 'order': 2, 'is_required': True, 'description': 'مسح الجهاز المُصلح'}
        ]
    },
    'DEVICE_LENDING': {
        'name': 'إعارة جهاز',
        'description': 'إعارة جهاز إلى قسم أو مستخدم آخر',
        'auto_execute': True,
        'requires_confirmation': False,
        'log_to_transfer': True,
        'steps': [
            {'entity_type': 'user', 'order': 1, 'is_required': True, 'description': 'مسح بطاقة المعير'},
            {'entity_type': 'device', 'order': 2, 'is_required': True, 'description': 'مسح الجهاز المُعار'},
            {'entity_type': 'user', 'order': 3, 'is_required': False, 'description': 'مسح بطاقة المستعير أو القسم'}
        ]
    },
    'OUT_OF_SERVICE': {
        'name': 'إخراج من الخدمة',
        'description': 'إخراج جهاز من الخدمة نهائياً',
        'auto_execute': True,
        'requires_confirmation': True,  # هذه العملية تحتاج تأكيد
        'log_to_handover': False,
        'steps': [
            {'entity_type': 'user', 'order': 1, 'is_required': True, 'description': 'مسح بطاقة المشرف'},
            {'entity_type': 'user', 'order': 2, 'is_required': True, 'description': 'مسح بطاقة موظف آخر للتأكيد'},
            {'entity_type': 'device', 'order': 3, 'is_required': True, 'description': 'مسح الجهاز المراد إخراجه'}
        ]
    },
    'INSPECTION': {
        'name': 'تفقد الجهاز',
        'description': 'تفقد دوري للجهاز',
        'auto_execute': True,
        'requires_confirmation': False,
        'log_to_handover': False,
        'steps': [
            {'entity_type': 'user', 'order': 1, 'is_required': True, 'description': 'مسح بطاقة المفتش'},
            {'entity_type': 'device', 'order': 2, 'is_required': True, 'description': 'مسح الجهاز المراد تفقده'}
        ]
    },
    'AUDIT_REPORT': {
        'name': 'تدقيق وتقرير',
        'description': 'إنشاء تقرير تدقيق للجهاز',
        'auto_execute': True,
        'requires_confirmation': False,
        'log_to_handover': False,
        'steps': [
            {'entity_type': 'user', 'order': 1, 'is_required': True, 'description': 'مسح بطاقة المدقق'},
            {'entity_type': 'device', 'order': 2, 'is_required': True, 'description': 'مسح الجهاز المراد تدقيقه'}
        ]
    }
}

# Create or update operations
for code, config in operations_config.items():
    # Get or create operation
    operation, created = OperationDefinition.objects.get_or_create(
        code=code,
        defaults={
            'name': config['name'],
            'description': config['description'],
            'auto_execute': config['auto_execute'],
            'requires_confirmation': config['requires_confirmation'],
            'log_to_usage': config.get('log_to_usage', False),
            'log_to_transfer': config.get('log_to_transfer', False),
            'log_to_handover': config.get('log_to_handover', False),
            'is_active': True
        }
    )
    
    if not created:
        # Update existing operation
        operation.name = config['name']
        operation.description = config['description']
        operation.auto_execute = config['auto_execute']
        operation.requires_confirmation = config['requires_confirmation']
        operation.log_to_usage = config.get('log_to_usage', False)
        operation.log_to_transfer = config.get('log_to_transfer', False)
        operation.log_to_handover = config.get('log_to_handover', False)
        operation.is_active = True
        operation.save()
        print(f"Updated operation: {code}")
    else:
        print(f"Created operation: {code}")
    
    # Create steps (don't delete existing ones to avoid constraint issues)
    for step_config in config['steps']:
        try:
            # Try to create or update step
            step, created = OperationStep.objects.update_or_create(
                operation=operation,
                entity_type=step_config['entity_type'],
                order=step_config['order'],
                defaults={
                    'is_required': step_config['is_required'],
                    'description': step_config['description']
                }
            )
            print(f"  - Step {step.order}: {step.entity_type} ({step.description})")
        except Exception as e:
            print(f"  ⚠️ Error with step {step_config['order']}: {e}")

print("\n✅ All missing operations created/updated successfully!")

# Verify DEVICE_USAGE operation has correct steps
try:
    device_usage = OperationDefinition.objects.get(code='DEVICE_USAGE')
    if device_usage.steps.count() == 0:
        # Create steps for DEVICE_USAGE
        OperationStep.objects.create(
            operation=device_usage,
            entity_type='user',
            order=1,
            is_required=True,
            description='مسح بطاقة المستخدم'
        )
        OperationStep.objects.create(
            operation=device_usage,
            entity_type='device',
            order=2,
            is_required=True,
            description='مسح الجهاز المراد استخدامه'
        )
        OperationStep.objects.create(
            operation=device_usage,
            entity_type='patient',
            order=3,
            is_required=True,
            description='مسح المريض'
        )
        print("\n✅ Added steps for DEVICE_USAGE operation")
except OperationDefinition.DoesNotExist:
    print("\n⚠️ DEVICE_USAGE operation not found!")

# List all active operations
print("\n📋 All Active Operations:")
all_ops = OperationDefinition.objects.filter(is_active=True)
for op in all_ops:
    steps_count = op.steps.count()
    print(f"  - {op.code}: {op.name} ({steps_count} steps, auto={op.auto_execute})")
