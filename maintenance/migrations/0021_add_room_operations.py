# Migration to add room-specific operations to the QR system

from django.db import migrations


def add_room_operations(apps, schema_editor):
    """Add room-specific operations to the system"""
    OperationDefinition = apps.get_model('maintenance', 'OperationDefinition')
    OperationStep = apps.get_model('maintenance', 'OperationStep')
    
    # Room Cleaning Operation
    room_cleaning = OperationDefinition.objects.create(
        name="تنظيف الغرفة",
        code="room_cleaning",
        description="تنظيف وتعقيم الغرفة",
        auto_execute=True,
        requires_confirmation=False,
        session_timeout_minutes=30,
        log_to_usage=False,
        log_to_transfer=False,
        log_to_handover=False,
        is_active=True
    )
    
    OperationStep.objects.create(
        operation=room_cleaning,
        order=1,
        entity_type='user',
        is_required=True,
        validation_rule={}
    )
    
    OperationStep.objects.create(
        operation=room_cleaning,
        order=2,
        entity_type='room',
        is_required=True,
        validation_rule={'status': ['available', 'occupied']}
    )
    
    # Room Maintenance Operation
    room_maintenance = OperationDefinition.objects.create(
        name="صيانة الغرفة",
        code="room_maintenance",
        description="صيانة مرافق الغرفة",
        auto_execute=False,
        requires_confirmation=True,
        session_timeout_minutes=60,
        log_to_usage=False,
        log_to_transfer=False,
        log_to_handover=False,
        is_active=True
    )
    
    OperationStep.objects.create(
        operation=room_maintenance,
        order=1,
        entity_type='user',
        is_required=True,
        validation_rule={}
    )
    
    OperationStep.objects.create(
        operation=room_maintenance,
        order=2,
        entity_type='room',
        is_required=True,
        validation_rule={'status': ['available', 'maintenance']}
    )
    
    # Room Status Update Operation
    room_status = OperationDefinition.objects.create(
        name="تحديث حالة الغرفة",
        code="room_status_update",
        description="تحديث حالة توفر الغرفة",
        auto_execute=True,
        requires_confirmation=False,
        session_timeout_minutes=15,
        log_to_usage=False,
        log_to_transfer=False,
        log_to_handover=False,
        is_active=True
    )
    
    OperationStep.objects.create(
        operation=room_status,
        order=1,
        entity_type='user',
        is_required=True,
        validation_rule={}
    )
    
    OperationStep.objects.create(
        operation=room_status,
        order=2,
        entity_type='room',
        is_required=True,
        validation_rule={}
    )
    
    # Room Inspection Operation
    room_inspection = OperationDefinition.objects.create(
        name="فحص الغرفة",
        code="room_inspection",
        description="فحص الغرفة للسلامة والامتثال",
        auto_execute=False,
        requires_confirmation=True,
        session_timeout_minutes=45,
        log_to_usage=False,
        log_to_transfer=False,
        log_to_handover=False,
        is_active=True
    )
    
    OperationStep.objects.create(
        operation=room_inspection,
        order=1,
        entity_type='user',
        is_required=True,
        validation_rule={}
    )
    
    OperationStep.objects.create(
        operation=room_inspection,
        order=2,
        entity_type='room',
        is_required=True,
        validation_rule={}
    )


def reverse_room_operations(apps, schema_editor):
    """Remove room operations"""
    OperationDefinition = apps.get_model('maintenance', 'OperationDefinition')
    
    # Delete room operations
    OperationDefinition.objects.filter(
        code__in=[
            "room_cleaning",
            "room_maintenance", 
            "room_status_update",
            "room_inspection"
        ]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('maintenance', '0020_alter_devicetransferrequest_options_and_more'),
        ('manager', '0020_add_room_qr_fields'),
    ]

    operations = [
        migrations.RunPython(add_room_operations, reverse_room_operations),
    ]
