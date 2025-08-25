# أمر Django لإنشاء جداول الصيانة الوقائية للأجهزة
# يستخدم لإعداد الصيانة الوقائية لأجهزة جديدة أو إعادة جدولة الأجهزة الموجودة

import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from maintenance.models import Device, PreventiveMaintenanceSchedule, JobPlan
from datetime import timedelta

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    """
    أمر لإنشاء جداول الصيانة الوقائية للأجهزة
    
    الاستخدام:
    python manage.py generate_pm_schedules                     # جميع الأجهزة
    python manage.py generate_pm_schedules --device-id 123     # جهاز محدد
    python manage.py generate_pm_schedules --department ICU    # قسم محدد
    python manage.py generate_pm_schedules --overwrite         # إعادة كتابة الجداول الموجودة
    """
    
    help = 'إنشاء جداول الصيانة الوقائية للأجهزة بناءً على نوع الجهاز وخطط الصيانة'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--device-id',
            type=int,
            help='معرف الجهاز المحدد لإنشاء جدول صيانة له',
        )
        
        parser.add_argument(
            '--department',
            type=str,
            help='اسم القسم لإنشاء جداول الصيانة لجميع أجهزته',
        )
        
        parser.add_argument(
            '--overwrite',
            action='store_true',
            help='إعادة كتابة الجداول الموجودة (احذر: سيحذف الجداول القديمة)',
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='تشغيل تجريبي بدون تنفيذ فعلي للتغييرات',
        )
        
    def handle(self, *args, **options):
        device_id = options.get('device_id')
        department = options.get('department')
        overwrite = options['overwrite']
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('تشغيل تجريبي - لن يتم تنفيذ أي تغييرات فعلية')
            )
        
        try:
            with transaction.atomic():
                # تحديد الأجهزة المراد معالجتها
                devices = Device.objects.all()
                
                if device_id:
                    devices = devices.filter(id=device_id)
                    if not devices.exists():
                        self.stdout.write(
                            self.style.ERROR(f'لم يتم العثور على جهاز بالمعرف: {device_id}')
                        )
                        return
                        
                if department:
                    devices = devices.filter(department__name__icontains=department)
                    if not devices.exists():
                        self.stdout.write(
                            self.style.ERROR(f'لم يتم العثور على أجهزة في القسم: {department}')
                        )
                        return
                
                self.stdout.write(f'معالجة {devices.count()} جهاز...')
                
                created_count = 0
                updated_count = 0
                skipped_count = 0
                
                for device in devices:
                    result = self.create_pm_schedule_for_device(device, overwrite, dry_run)
                    if result == 'created':
                        created_count += 1
                    elif result == 'updated':
                        updated_count += 1
                    else:
                        skipped_count += 1
                
                if dry_run:
                    transaction.set_rollback(True)
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'انتهت المعالجة:\n'
                        f'- تم إنشاء: {created_count} جدول جديد\n'
                        f'- تم تحديث: {updated_count} جدول\n'
                        f'- تم تخطي: {skipped_count} جهاز'
                    )
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'خطأ في إنشاء جداول الصيانة: {str(e)}')
            )
            logger.error(f'خطأ في إنشاء جداول الصيانة: {str(e)}', exc_info=True)
            raise
    
    def create_pm_schedule_for_device(self, device, overwrite=False, dry_run=False):
        """إنشاء جدول صيانة وقائية لجهاز محدد"""
        
        # التحقق من وجود جدول صيانة موجود
        existing_schedule = PreventiveMaintenanceSchedule.objects.filter(device=device).first()
        
        if existing_schedule and not overwrite:
            self.stdout.write(f'تخطي {device.name} - يوجد جدول صيانة بالفعل')
            return 'skipped'
        
        # البحث عن خطة صيانة مناسبة لنوع الجهاز
        job_plan = self.find_suitable_job_plan(device)
        
        if not job_plan:
            self.stdout.write(
                self.style.WARNING(f'لم يتم العثور على خطة صيانة مناسبة للجهاز: {device.name}')
            )
            return 'skipped'
        
        # تحديد فترة الصيانة بناءً على نوع الجهاز
        frequency_days = self.get_maintenance_frequency(device)
        
        if not dry_run:
            if existing_schedule and overwrite:
                existing_schedule.delete()
                action = 'updated'
            else:
                action = 'created'
            
            # إنشاء جدول الصيانة الوقائية
            pm_schedule = PreventiveMaintenanceSchedule.objects.create(
                device=device,
                job_plan=job_plan,
                frequency_days=frequency_days,
                next_due_date=timezone.now().date() + timedelta(days=frequency_days),
                is_active=True,
                created_by_id=1,  # System user
                notes=f'تم إنشاؤه تلقائياً بواسطة أمر الإدارة'
            )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'{"تم تحديث" if action == "updated" else "تم إنشاء"} جدول صيانة للجهاز: {device.name} '
                    f'(كل {frequency_days} يوم)'
                )
            )
            
            return action
        else:
            self.stdout.write(f'[تجريبي] سيتم إنشاء جدول صيانة للجهاز: {device.name}')
            return 'created'
    
    def find_suitable_job_plan(self, device):
        """البحث عن خطة صيانة مناسبة للجهاز"""
        
        # البحث بناءً على نوع الجهاز أولاً
        if hasattr(device, 'device_type') and device.device_type:
            job_plan = JobPlan.objects.filter(
                device_category=device.device_type,
                is_active=True
            ).first()
            if job_plan:
                return job_plan
        
        # البحث بناءً على الشركة المصنعة
        if device.manufacturer:
            job_plan = JobPlan.objects.filter(
                title__icontains=device.manufacturer,
                is_active=True
            ).first()
            if job_plan:
                return job_plan
        
        # البحث عن خطة عامة
        job_plan = JobPlan.objects.filter(
            title__icontains='عام',
            is_active=True
        ).first()
        
        if not job_plan:
            # إنشاء خطة صيانة افتراضية إذا لم توجد
            job_plan = JobPlan.objects.create(
                title=f'صيانة عامة - {device.name}',
                description='خطة صيانة عامة تم إنشاؤها تلقائياً',
                estimated_duration_minutes=60,
                is_active=True,
                created_by_id=1
            )
        
        return job_plan
    
    def get_maintenance_frequency(self, device):
        """تحديد فترة الصيانة بناءً على نوع الجهاز"""
        
        # فترات الصيانة الافتراضية بناءً على نوع الجهاز
        frequency_map = {
            'ventilator': 30,      # أجهزة التنفس الصناعي - شهرياً
            'monitor': 90,         # أجهزة المراقبة - كل 3 أشهر
            'pump': 60,            # مضخات - كل شهرين
            'dialysis': 15,        # أجهزة الغسيل الكلوي - كل أسبوعين
            'xray': 180,           # أجهزة الأشعة - كل 6 أشهر
            'ultrasound': 90,      # أجهزة الموجات فوق الصوتية - كل 3 أشهر
            'ecg': 120,            # أجهزة رسم القلب - كل 4 أشهر
            'defibrillator': 30,   # أجهزة الصدمات - شهرياً
        }
        
        # محاولة تحديد النوع من اسم الجهاز
        device_name_lower = device.name.lower()
        
        for device_type, frequency in frequency_map.items():
            if device_type in device_name_lower:
                return frequency
        
        # إذا كان الجهاز حرج (في العناية المركزة مثلاً)
        if device.department and 'icu' in device.department.name.lower():
            return 30  # صيانة شهرية للأجهزة الحرجة
        
        # الافتراضي: كل 3 أشهر
        return 90
