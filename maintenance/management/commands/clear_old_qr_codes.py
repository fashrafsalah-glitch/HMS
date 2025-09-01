"""
Management command to clear all old QR codes from the entire HMS system
"""

from django.core.management.base import BaseCommand
from django.apps import apps
from django.db import transaction
import os

class Command(BaseCommand):
    help = 'مسح جميع رموز QR القديمة من النظام بالكامل (Clear all old QR codes from entire system)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--regenerate',
            action='store_true',
            help='إعادة توليد رموز QR آمنة جديدة بعد المسح (Regenerate new secure QR codes after clearing)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='عرض ما سيتم حذفه دون تنفيذ الحذف فعلياً (Show what would be deleted without actually deleting)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        regenerate = options['regenerate']
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('🔍 وضع المعاينة - لن يتم حذف أي شيء (DRY RUN - Nothing will be deleted)')
            )
        
        # Models that use QRCodeMixin
        qr_models = [
            ('maintenance', 'Device'),
            ('maintenance', 'DeviceAccessory'),
            ('manager', 'Patient'),
            ('manager', 'Bed'),
            ('hr', 'CustomUser'),
        ]
        
        total_cleared = 0
        total_regenerated = 0
        
        with transaction.atomic():
            for app_label, model_name in qr_models:
                try:
                    Model = apps.get_model(app_label, model_name)
                    
                    # Get all objects with QR codes
                    objects_with_qr = Model.objects.filter(
                        models.Q(qr_code__isnull=False) | models.Q(qr_token__isnull=False)
                    ).exclude(qr_code='').exclude(qr_token='')
                    
                    count = objects_with_qr.count()
                    
                    if count > 0:
                        self.stdout.write(f'\n📋 {model_name}: {count} كائن يحتوي على QR codes')
                        
                        if not dry_run:
                            # Clear old QR codes
                            for obj in objects_with_qr:
                                if hasattr(obj, 'qr_code') and obj.qr_code:
                                    # Delete the file
                                    try:
                                        obj.qr_code.delete(save=False)
                                    except:
                                        pass
                                
                                # Clear token
                                if hasattr(obj, 'qr_token'):
                                    obj.qr_token = None
                                
                                obj.save(update_fields=['qr_code', 'qr_token'])
                                total_cleared += 1
                                
                                # Regenerate if requested
                                if regenerate and hasattr(obj, 'generate_qr_code'):
                                    obj.generate_qr_code()
                                    obj.save(update_fields=['qr_code', 'qr_token'])
                                    total_regenerated += 1
                            
                            self.stdout.write(
                                self.style.SUCCESS(f'✅ تم مسح {count} رمز QR من {model_name}')
                            )
                            
                            if regenerate:
                                self.stdout.write(
                                    self.style.SUCCESS(f'🔄 تم إعادة توليد {count} رمز QR آمن لـ {model_name}')
                                )
                    else:
                        self.stdout.write(f'ℹ️  {model_name}: لا توجد رموز QR للمسح')
                        
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'❌ خطأ في معالجة {model_name}: {str(e)}')
                    )
        
        # Summary
        self.stdout.write('\n' + '='*60)
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(f'📊 المعاينة: سيتم مسح {total_cleared} رمز QR من النظام')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'✅ تم مسح {total_cleared} رمز QR من النظام بنجاح')
            )
            
            if regenerate:
                self.stdout.write(
                    self.style.SUCCESS(f'🔄 تم إعادة توليد {total_regenerated} رمز QR آمن')
                )
        
        # Clear QR code files from media directory
        if not dry_run:
            self.clear_qr_media_files()
    
    def clear_qr_media_files(self):
        """Clear orphaned QR code files from media directory"""
        from django.conf import settings
        
        qr_dirs = [
            'qr_codes',
            'lab_qrcodes',
            'lab_samples_qr'
        ]
        
        cleared_files = 0
        
        for qr_dir in qr_dirs:
            qr_path = os.path.join(settings.MEDIA_ROOT, qr_dir)
            
            if os.path.exists(qr_path):
                try:
                    for filename in os.listdir(qr_path):
                        if filename.endswith(('.png', '.jpg', '.jpeg')):
                            file_path = os.path.join(qr_path, filename)
                            os.remove(file_path)
                            cleared_files += 1
                    
                    self.stdout.write(
                        self.style.SUCCESS(f'🗑️  تم مسح {cleared_files} ملف QR من مجلد {qr_dir}')
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'❌ خطأ في مسح ملفات {qr_dir}: {str(e)}')
                    )
        
        if cleared_files > 0:
            self.stdout.write(
                self.style.SUCCESS(f'🧹 تم مسح {cleared_files} ملف QR إجمالي من مجلدات الوسائط')
            )
