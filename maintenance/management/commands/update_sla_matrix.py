from django.core.management.base import BaseCommand
from maintenance.models import SLAMatrix

class Command(BaseCommand):
    help = 'Update existing SLA matrix entries with corrected calculation'

    def handle(self, *args, **options):
        updated_count = 0
        
        for matrix in SLAMatrix.objects.all():
            old_response = matrix.response_time_hours
            old_resolution = matrix.resolution_time_hours
            
            # Recalculate using the corrected method
            new_response, new_resolution = matrix.calculate_sla_times()
            
            if old_response != new_response or old_resolution != new_resolution:
                matrix.response_time_hours = new_response
                matrix.resolution_time_hours = new_resolution
                matrix.save()
                updated_count += 1
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Updated {matrix.device_category.name} - {matrix.severity}/{matrix.impact}/{matrix.priority}: '
                        f'{old_response}h/{old_resolution}h → {new_response}h/{new_resolution}h'
                    )
                )
        
        if updated_count == 0:
            self.stdout.write(self.style.WARNING('No SLA matrix entries needed updating'))
        else:
            self.stdout.write(
                self.style.SUCCESS(f'Successfully updated {updated_count} SLA matrix entries')
            )
