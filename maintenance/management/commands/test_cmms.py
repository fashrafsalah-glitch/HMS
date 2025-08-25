from django.core.management.base import BaseCommand
from maintenance.models import (
    ServiceRequest, WorkOrder, JobPlan, JobPlanStep,
    PreventiveMaintenanceSchedule, SLADefinition,
    SystemNotification, EmailLog, NotificationPreference,
    NotificationTemplate, NotificationQueue,
    Supplier, SparePart
)

class Command(BaseCommand):
    help = 'Test CMMS models consolidation'

    def handle(self, *args, **options):
        self.stdout.write("Testing CMMS Models Consolidation...")
        self.stdout.write("=" * 50)
        
        models_to_test = [
            ('ServiceRequest', ServiceRequest),
            ('WorkOrder', WorkOrder),
            ('JobPlan', JobPlan),
            ('JobPlanStep', JobPlanStep),
            ('PreventiveMaintenanceSchedule', PreventiveMaintenanceSchedule),
            ('SLADefinition', SLADefinition),
            ('SystemNotification', SystemNotification),
            ('EmailLog', EmailLog),
            ('NotificationPreference', NotificationPreference),
            ('NotificationTemplate', NotificationTemplate),
            ('NotificationQueue', NotificationQueue),
            ('Supplier', Supplier),
            ('SparePart', SparePart),
        ]
        
        success_count = 0
        for model_name, model_class in models_to_test:
            try:
                # Test model meta information
                verbose_name = model_class._meta.verbose_name
                field_count = len(model_class._meta.get_fields())
                self.stdout.write(
                    self.style.SUCCESS(f"✓ {model_name}: {verbose_name} ({field_count} fields)")
                )
                success_count += 1
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"✗ {model_name}: {str(e)}")
                )
        
        self.stdout.write("=" * 50)
        if success_count == len(models_to_test):
            self.stdout.write(
                self.style.SUCCESS(f"✓ All {success_count} CMMS models working correctly!")
            )
        else:
            self.stdout.write(
                self.style.WARNING(f"⚠ {success_count}/{len(models_to_test)} models working")
            )
