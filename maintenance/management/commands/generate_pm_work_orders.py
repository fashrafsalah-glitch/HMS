from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date
from maintenance.models import PreventiveMaintenanceSchedule


class Command(BaseCommand):
    help = 'Generate work orders for due preventive maintenance schedules'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be generated without actually creating work orders',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        # العثور على جداول الصيانة المستحقة
        due_schedules = PreventiveMaintenanceSchedule.objects.filter(
            is_active=True,
            next_due_date__lte=date.today()
        )
        
        self.stdout.write(f'Found {due_schedules.count()} due PM schedules')
        
        generated_count = 0
        
        for schedule in due_schedules:
            try:
                if dry_run:
                    self.stdout.write(
                        f'Would generate work order for: {schedule.name} - {schedule.device.name}'
                    )
                else:
                    work_order = schedule.generate_work_order()
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Generated work order {work_order.id} for: {schedule.name} - {schedule.device.name}'
                        )
                    )
                generated_count += 1
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f'Error generating work order for {schedule.name}: {str(e)}'
                    )
                )
        
        if dry_run:
            self.stdout.write(f'Dry run complete. Would generate {generated_count} work orders.')
        else:
            self.stdout.write(
                self.style.SUCCESS(f'Successfully generated {generated_count} work orders.')
            )
