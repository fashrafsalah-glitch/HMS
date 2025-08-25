# أمر Django لتشغيل المهام المجدولة للـ CMMS
# يمكن تشغيله من cron job أو Windows Task Scheduler

import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from maintenance.scheduler import CMMSScheduler

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    """
    أمر لتشغيل المهام المجدولة للـ CMMS
    
    الاستخدام:
    python manage.py run_cmms_scheduler                    # تشغيل جميع المهام
    python manage.py run_cmms_scheduler --task pm          # الصيانة الوقائية فقط
    python manage.py run_cmms_scheduler --task sla         # فحص SLA فقط
    python manage.py run_cmms_scheduler --task calibration # فحص المعايرة فقط
    python manage.py run_cmms_scheduler --task spare_parts # فحص قطع الغيار فقط
    python manage.py run_cmms_scheduler --task cleanup     # تنظيف البيانات فقط
    python manage.py run_cmms_scheduler --verbose          # مع تفاصيل أكثر
    """
    
    help = 'تشغيل المهام المجدولة للـ CMMS - الصيانة الوقائية والإشعارات والتنظيف'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--task',
            type=str,
            choices=['pm', 'sla', 'calibration', 'spare_parts', 'notifications', 'cleanup', 'all'],
            default='all',
            help='نوع المهمة المراد تشغيلها (افتراضي: all)',
        )
        
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='عرض تفاصيل أكثر أثناء التشغيل',
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='تشغيل تجريبي بدون تنفيذ فعلي للتغييرات',
        )
        
    def handle(self, *args, **options):
        start_time = timezone.now()
        task = options['task']
        verbose = options['verbose']
        dry_run = options['dry_run']
        
        if verbose:
            logging.basicConfig(level=logging.INFO)
            
        if dry_run:
            self.stdout.write(
                self.style.WARNING('تشغيل تجريبي - لن يتم تنفيذ أي تغييرات فعلية')
            )
            
        self.stdout.write(
            self.style.SUCCESS(f'بدء تشغيل المهام المجدولة للـ CMMS - {start_time.strftime("%Y-%m-%d %H:%M:%S")}')
        )
        
        try:
            scheduler = CMMSScheduler()
            
            if task == 'pm':
                self.stdout.write('تشغيل مهمة الصيانة الوقائية...')
                if not dry_run:
                    scheduler.create_due_preventive_maintenance()
                    
            elif task == 'sla':
                self.stdout.write('تشغيل مهمة فحص انتهاكات SLA...')
                if not dry_run:
                    scheduler.check_sla_violations()
                    
            elif task == 'calibration':
                self.stdout.write('تشغيل مهمة فحص المعايرات المستحقة...')
                if not dry_run:
                    scheduler.check_due_calibrations()
                    
            elif task == 'spare_parts':
                self.stdout.write('تشغيل مهمة فحص قطع الغيار...')
                if not dry_run:
                    scheduler.check_low_stock_spare_parts()
                    
            elif task == 'notifications':
                self.stdout.write('تشغيل مهمة معالجة الإشعارات...')
                if not dry_run:
                    scheduler.process_notification_queue()
                    
            elif task == 'cleanup':
                self.stdout.write('تشغيل مهمة تنظيف البيانات القديمة...')
                if not dry_run:
                    scheduler.cleanup_old_data()
                    
            else:  # all
                self.stdout.write('تشغيل جميع المهام المجدولة...')
                if not dry_run:
                    scheduler.run_all_scheduled_tasks()
                    
            end_time = timezone.now()
            duration = end_time - start_time
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'انتهاء تشغيل المهام بنجاح - المدة: {duration.total_seconds():.2f} ثانية'
                )
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'خطأ في تشغيل المهام المجدولة: {str(e)}')
            )
            logger.error(f'خطأ في تشغيل المهام المجدولة: {str(e)}', exc_info=True)
            raise
