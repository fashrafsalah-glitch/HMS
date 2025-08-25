# أمر Django لإنشاء مصفوفة SLA للأجهزة والأقسام
# ينشئ تعريفات SLA تلقائياً بناءً على نوع الجهاز والقسم والأولوية

import logging
from django.core.management.base import BaseCommand
from django.db import transaction
from maintenance.models import (
    Device, DeviceCategory, SLADefinition, SLAMatrix,
    SEVERITY_CHOICES, IMPACT_CHOICES, PRIORITY_CHOICES
)

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    """
    أمر لإنشاء مصفوفة SLA تلقائياً للأجهزة والأقسام
    
    الاستخدام:
    python manage.py generate_sla_matrix                    # إنشاء مصفوفة كاملة
    python manage.py generate_sla_matrix --department ICU   # قسم محدد
    python manage.py generate_sla_matrix --reset            # إعادة تعيين المصفوفة
    """
    
    help = 'إنشاء مصفوفة SLA تلقائياً بناءً على نوع الجهاز والقسم والأولوية'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--department',
            type=str,
            help='اسم القسم لإنشاء SLA له فقط',
        )
        
        parser.add_argument(
            '--reset',
            action='store_true',
            help='حذف جميع تعريفات SLA الموجودة وإعادة إنشائها',
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='تشغيل تجريبي بدون تنفيذ فعلي للتغييرات',
        )
        
    def handle(self, *args, **options):
        department = options.get('department')
        reset = options['reset']
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('تشغيل تجريبي - لن يتم تنفيذ أي تغييرات فعلية')
            )
        
        try:
            with transaction.atomic():
                if reset and not dry_run:
                    # حذف المصفوفة الموجودة
                    deleted_sla = SLAMatrix.objects.all().delete()[0]
                    deleted_def = SLADefinition.objects.all().delete()[0]
                    self.stdout.write(f'تم حذف {deleted_sla} مصفوفة SLA و {deleted_def} تعريف SLA')
                
                # إنشاء تعريفات SLA الأساسية
                sla_definitions = self.create_sla_definitions(dry_run)
                
                # إنشاء مصفوفة SLA
                self.create_sla_matrix(sla_definitions, department, dry_run)
                
                if dry_run:
                    transaction.set_rollback(True)
                
                self.stdout.write(
                    self.style.SUCCESS('تم إنشاء مصفوفة SLA بنجاح')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'خطأ في إنشاء مصفوفة SLA: {str(e)}')
            )
            logger.error(f'خطأ في إنشاء مصفوفة SLA: {str(e)}', exc_info=True)
            raise
    
    def create_sla_definitions(self, dry_run=False):
        """إنشاء تعريفات SLA الأساسية"""
        
        sla_configs = [
            # أجهزة حرجة - استجابة فورية
            {
                'name': 'حرج - استجابة فورية',
                'description': 'للأجهزة الحرجة في العناية المركزة',
                'response_time_minutes': 5,
                'resolution_time_hours': 1,
                'escalation_time_minutes': 15,
            },
            # أجهزة عالية الأولوية
            {
                'name': 'عالي - استجابة سريعة',
                'description': 'للأجهزة عالية الأولوية',
                'response_time_minutes': 15,
                'resolution_time_hours': 4,
                'escalation_time_minutes': 30,
            },
            # أجهزة متوسطة الأولوية
            {
                'name': 'متوسط - استجابة عادية',
                'description': 'للأجهزة متوسطة الأولوية',
                'response_time_minutes': 60,
                'resolution_time_hours': 24,
                'escalation_time_minutes': 120,
            },
            # أجهزة منخفضة الأولوية
            {
                'name': 'منخفض - استجابة مؤجلة',
                'description': 'للأجهزة منخفضة الأولوية',
                'response_time_minutes': 240,
                'resolution_time_hours': 72,
                'escalation_time_minutes': 480,
            },
        ]
        
        sla_definitions = {}
        
        for config in sla_configs:
            if not dry_run:
                sla_def, created = SLADefinition.objects.get_or_create(
                    name=config['name'],
                    defaults={
                        'description': config['description'],
                        'response_time_minutes': config['response_time_minutes'],
                        'resolution_time_hours': config['resolution_time_hours'],
                        'escalation_time_minutes': config['escalation_time_minutes'],
                        'is_active': True,
                    }
                )
                sla_definitions[config['name']] = sla_def
                
                if created:
                    self.stdout.write(f'تم إنشاء تعريف SLA: {config["name"]}')
                else:
                    self.stdout.write(f'تعريف SLA موجود: {config["name"]}')
            else:
                self.stdout.write(f'[تجريبي] سيتم إنشاء تعريف SLA: {config["name"]}')
                sla_definitions[config['name']] = None
        
        return sla_definitions
    
    def create_sla_matrix(self, sla_definitions, department_filter=None, dry_run=False):
        """إنشاء مصفوفة SLA للأجهزة"""
        
        # الحصول على فئات الأجهزة
        device_categories = DeviceCategory.objects.all()
        if department_filter:
            device_categories = device_categories.filter(
                devices__department__name__icontains=department_filter
            ).distinct()
        
        # قواعد تعيين SLA
        sla_rules = [
            # حرج + عالي + حرج = استجابة فورية
            ('critical', 'high', 'critical', 'حرج - استجابة فورية'),
            ('critical', 'high', 'high', 'حرج - استجابة فورية'),
            ('critical', 'medium', 'critical', 'حرج - استجابة فورية'),
            
            # عالي + عالي = استجابة سريعة
            ('high', 'high', 'high', 'عالي - استجابة سريعة'),
            ('high', 'high', 'medium', 'عالي - استجابة سريعة'),
            ('high', 'medium', 'high', 'عالي - استجابة سريعة'),
            
            # متوسط = استجابة عادية
            ('medium', 'medium', 'medium', 'متوسط - استجابة عادية'),
            ('medium', 'low', 'medium', 'متوسط - استجابة عادية'),
            ('low', 'medium', 'medium', 'متوسط - استجابة عادية'),
            
            # منخفض = استجابة مؤجلة
            ('low', 'low', 'low', 'منخفض - استجابة مؤجلة'),
        ]
        
        created_count = 0
        
        for category in device_categories:
            for severity, impact, priority, sla_name in sla_rules:
                if not dry_run:
                    sla_def = sla_definitions.get(sla_name)
                    if sla_def:
                        matrix_entry, created = SLAMatrix.objects.get_or_create(
                            device_category=category,
                            severity=severity,
                            impact=impact,
                            priority=priority,
                            defaults={'sla_definition': sla_def}
                        )
                        
                        if created:
                            created_count += 1
                            self.stdout.write(
                                f'تم إنشاء مصفوفة SLA: {category.name} - '
                                f'{severity}/{impact}/{priority} -> {sla_name}'
                            )
                else:
                    self.stdout.write(
                        f'[تجريبي] سيتم إنشاء مصفوفة SLA: {category.name} - '
                        f'{severity}/{impact}/{priority} -> {sla_name}'
                    )
                    created_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(f'تم إنشاء {created_count} مدخل في مصفوفة SLA')
        )
    
    def get_device_criticality(self, device):
        """تحديد مستوى أهمية الجهاز بناءً على القسم والنوع"""
        
        # الأقسام الحرجة
        critical_departments = ['icu', 'er', 'or', 'ccu']
        
        if device.department:
            dept_name = device.department.name.lower()
            for critical_dept in critical_departments:
                if critical_dept in dept_name:
                    return 'critical'
        
        # الأجهزة الحرجة
        critical_devices = ['ventilator', 'defibrillator', 'monitor']
        device_name = device.name.lower()
        
        for critical_device in critical_devices:
            if critical_device in device_name:
                return 'high'
        
        return 'medium'
