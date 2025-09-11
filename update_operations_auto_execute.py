"""
Script to update all operations to auto-execute
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

from maintenance.models import OperationDefinition

# Update all operations to auto-execute
operations = OperationDefinition.objects.all()

for op in operations:
    print(f"Updating operation: {op.code} - {op.name}")
    op.auto_execute = True
    op.requires_confirmation = False  # تأكد من عدم طلب التأكيد
    op.save()
    print(f"  Updated: auto_execute={op.auto_execute}, requires_confirmation={op.requires_confirmation}")

print(f"\n✅ Updated {operations.count()} operations to auto-execute")

# Verify specific operations
important_ops = ['DEVICE_USAGE', 'END_DEVICE_USAGE', 'DEVICE_TRANSFER', 'DEVICE_HANDOVER']
for code in important_ops:
    try:
        op = OperationDefinition.objects.get(code=code)
        print(f"\n{code}: auto_execute={op.auto_execute}, requires_confirmation={op.requires_confirmation}")
    except OperationDefinition.DoesNotExist:
        print(f"\n⚠️ {code} operation not found!")
