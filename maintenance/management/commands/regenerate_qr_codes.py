"""
Django management command to regenerate all QR codes with new permanent format
Usage: python manage.py regenerate_qr_codes
"""

from django.core.management.base import BaseCommand
from django.apps import apps
from django.db import transaction
import time


class Command(BaseCommand):
    help = 'Regenerate all QR codes with new permanent format (entity_type:hash)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes',
        )
        parser.add_argument(
            '--model',
            type=str,
            help='Only regenerate for specific model (e.g., Device, Patient)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        specific_model = options['model']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        
        # Models that have QR codes
        models_to_update = [
            ('maintenance', 'Device'),
            ('manager', 'Patient'),
            ('manager', 'Bed'),
            ('hr', 'CustomUser'),
            ('maintenance', 'DeviceAccessory'),
            ('manager', 'Department'),
            ('manager', 'Doctor'),
        ]
        
        if specific_model:
            models_to_update = [(app, model) for app, model in models_to_update 
                              if model.lower() == specific_model.lower()]
            if not models_to_update:
                self.stdout.write(self.style.ERROR(f'Model {specific_model} not found'))
                return
        
        total_updated = 0
        
        for app_label, model_name in models_to_update:
            try:
                model_class = apps.get_model(app_label, model_name)
                
                # Check if model has QR code fields
                if not (hasattr(model_class, 'qr_code') and hasattr(model_class, 'qr_token')):
                    self.stdout.write(f'Skipping {model_name} - no QR fields')
                    continue
                
                # Get all instances
                instances = model_class.objects.all()
                count = instances.count()
                
                if count == 0:
                    self.stdout.write(f'No {model_name} instances found')
                    continue
                
                self.stdout.write(f'Processing {count} {model_name} instances...')
                
                updated_count = 0
                
                with transaction.atomic():
                    for i, instance in enumerate(instances, 1):
                        try:
                            if not dry_run:
                                # Generate new QR code
                                instance.generate_qr_code()
                                instance.save()
                            
                            updated_count += 1
                            
                            # Progress indicator
                            if i % 10 == 0 or i == count:
                                self.stdout.write(f'  Progress: {i}/{count}')
                                
                        except Exception as e:
                            self.stdout.write(
                                self.style.ERROR(f'Error updating {model_name} {instance.pk}: {e}')
                            )
                
                self.stdout.write(
                    self.style.SUCCESS(f'{model_name}: {updated_count} instances processed')
                )
                total_updated += updated_count
                
                # Small delay to prevent overwhelming the system
                time.sleep(0.1)
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error processing {model_name}: {e}')
                )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(f'DRY RUN: Would update {total_updated} QR codes')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'Successfully regenerated {total_updated} QR codes!')
            )
            self.stdout.write('New format: entity_type:hash (permanent, no domain)')
