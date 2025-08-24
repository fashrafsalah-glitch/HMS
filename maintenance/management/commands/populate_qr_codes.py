from django.core.management.base import BaseCommand
from django.db import transaction
from manager.models import Patient, Bed
from hr.models import CustomUser
from maintenance.models import Device, DeviceAccessory


class Command(BaseCommand):
    help = 'Populate QR codes for existing records in Step 2 implementation'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes',
        )
        parser.add_argument(
            '--entity',
            type=str,
            choices=['patient', 'bed', 'user', 'device', 'accessory', 'all'],
            default='all',
            help='Specify which entity type to process',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        entity_type = options['entity']
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('🔍 DRY RUN MODE - No changes will be made')
            )
        
        self.stdout.write('🔄 Starting QR code population for existing records...')
        
        total_processed = 0
        
        with transaction.atomic():
            if entity_type in ['patient', 'all']:
                total_processed += self.process_patients(dry_run)
            
            if entity_type in ['bed', 'all']:
                total_processed += self.process_beds(dry_run)
            
            if entity_type in ['user', 'all']:
                total_processed += self.process_users(dry_run)
            
            if entity_type in ['device', 'all']:
                total_processed += self.process_devices(dry_run)
            
            if entity_type in ['accessory', 'all']:
                total_processed += self.process_accessories(dry_run)
        
        self.stdout.write(
            self.style.SUCCESS(f'🎉 QR Code Population Complete! Total: {total_processed}')
        )

    def process_patients(self, dry_run=False):
        self.stdout.write('\n📋 Processing Patients...')
        patients = Patient.objects.filter(qr_token__isnull=True)
        count = 0
        
        for patient in patients:
            try:
                if not dry_run:
                    patient.qr_token = patient.generate_qr_token()
                    patient.generate_qr_code()
                    patient.save(update_fields=['qr_token', 'qr_code'])
                
                count += 1
                self.stdout.write(f"  ✅ Patient {patient.id}: {patient.first_name} {patient.last_name}")
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"  ❌ Error with Patient {patient.id}: {e}")
                )
        
        self.stdout.write(f"📋 Processed {count} patients")
        return count

    def process_beds(self, dry_run=False):
        self.stdout.write('\n🛏️ Processing Beds...')
        beds = Bed.objects.filter(qr_token__isnull=True)
        count = 0
        
        for bed in beds:
            try:
                if not dry_run:
                    bed.qr_token = bed.generate_qr_token()
                    bed.generate_qr_code()
                    bed.save(update_fields=['qr_token', 'qr_code'])
                
                count += 1
                self.stdout.write(f"  ✅ Bed {bed.id}: {bed}")
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"  ❌ Error with Bed {bed.id}: {e}")
                )
        
        self.stdout.write(f"🛏️ Processed {count} beds")
        return count

    def process_users(self, dry_run=False):
        self.stdout.write('\n👥 Processing Users...')
        users = CustomUser.objects.filter(qr_token__isnull=True)
        count = 0
        
        for user in users:
            try:
                if not dry_run:
                    user.qr_token = user.generate_qr_token()
                    user.generate_qr_code()
                    user.save(update_fields=['qr_token', 'qr_code'])
                
                count += 1
                self.stdout.write(f"  ✅ User {user.id}: {user.get_full_name()} ({user.role})")
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"  ❌ Error with User {user.id}: {e}")
                )
        
        self.stdout.write(f"👥 Processed {count} users")
        return count

    def process_devices(self, dry_run=False):
        self.stdout.write('\n🔧 Processing Devices...')
        devices = Device.objects.filter(qr_token__isnull=True)
        count = 0
        
        for device in devices:
            try:
                if not dry_run:
                    device.qr_token = device.generate_qr_token()
                    device.generate_qr_code()
                    device.save(update_fields=['qr_token', 'qr_code'])
                
                count += 1
                self.stdout.write(f"  ✅ Device {device.id}: {device.name}")
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"  ❌ Error with Device {device.id}: {e}")
                )
        
        self.stdout.write(f"🔧 Processed {count} devices")
        return count

    def process_accessories(self, dry_run=False):
        self.stdout.write('\n🔩 Processing Device Accessories...')
        accessories = DeviceAccessory.objects.filter(qr_token__isnull=True)
        count = 0
        
        for accessory in accessories:
            try:
                if not dry_run:
                    accessory.qr_token = accessory.generate_qr_token()
                    accessory.generate_qr_code()
                    accessory.save(update_fields=['qr_token', 'qr_code'])
                
                count += 1
                self.stdout.write(f"  ✅ Accessory {accessory.id}: {accessory.name}")
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"  ❌ Error with Accessory {accessory.id}: {e}")
                )
        
        self.stdout.write(f"🔩 Processed {count} accessories")
        return count
