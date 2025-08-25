# أمر Django لترحيل بيانات CMMS وإعداد البيانات الأولية
# يستخدم لإعداد النظام بعد التثبيت أو ترحيل البيانات من نظام قديم

import logging
from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from maintenance.models import *
from datetime import datetime, timedelta
from django.utils import timezone

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    """
    أمر لترحيل وإعداد بيانات CMMS
    
    الاستخدام:
    python manage.py cmms_data_migration --setup-groups      # إعداد المجموعات والصلاحيات
    python manage.py cmms_data_migration --setup-defaults    # إعداد البيانات الافتراضية
    python manage.py cmms_data_migration --migrate-devices   # ترحيل بيانات الأجهزة
    python manage.py cmms_data_migration --all               # تشغيل جميع المهام
    """
    
    help = 'ترحيل وإعداد بيانات CMMS - المجموعات والصلاحيات والبيانات الافتراضية'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--setup-groups',
            action='store_true',
            help='إعداد مجموعات المستخدمين وصلاحياتهم',
        )
        
        parser.add_argument(
            '--setup-defaults',
            action='store_true',
            help='إعداد البيانات الافتراضية (SLA، خطط الصيانة، إلخ)',
        )
        
        parser.add_argument(
            '--migrate-devices',
            action='store_true',
            help='ترحيل بيانات الأجهزة وإعداد QR codes',
        )
        
        parser.add_argument(
            '--all',
            action='store_true',
            help='تشغيل جميع مهام الإعداد والترحيل',
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='تشغيل تجريبي بدون تنفيذ فعلي للتغييرات',
        )
        
    def handle(self, *args, **options):
        setup_groups = options['setup_groups']
        setup_defaults = options['setup_defaults']
        migrate_devices = options['migrate_devices']
        run_all = options['all']
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('تشغيل تجريبي - لن يتم تنفيذ أي تغييرات فعلية')
            )
        
        try:
            with transaction.atomic():
                if run_all or setup_groups:
                    self.setup_user_groups(dry_run)
                
                if run_all or setup_defaults:
                    self.setup_default_data(dry_run)
                
                if run_all or migrate_devices:
                    self.migrate_device_data(dry_run)
                
                if dry_run:
                    transaction.set_rollback(True)
                
                self.stdout.write(
                    self.style.SUCCESS('تم إكمال ترحيل وإعداد بيانات CMMS بنجاح')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'خطأ في ترحيل البيانات: {str(e)}')
            )
            logger.error(f'خطأ في ترحيل البيانات: {str(e)}', exc_info=True)
            raise
    
    def setup_user_groups(self, dry_run=False):
        """إعداد مجموعات المستخدمين وصلاحياتهم"""
        
        self.stdout.write('إعداد مجموعات المستخدمين...')
        
        # تعريف المجموعات وصلاحياتها
        groups_config = {
            'CMMS_Admin': {
                'description': 'مدير نظام CMMS - صلاحيات كاملة',
                'permissions': [
                    'maintenance.add_device',
                    'maintenance.change_device',
                    'maintenance.delete_device',
                    'maintenance.view_device',
                    'maintenance.add_servicerequest',
                    'maintenance.change_servicerequest',
                    'maintenance.delete_servicerequest',
                    'maintenance.view_servicerequest',
                    'maintenance.add_workorder',
                    'maintenance.change_workorder',
                    'maintenance.delete_workorder',
                    'maintenance.view_workorder',
                    'maintenance.add_sladefinition',
                    'maintenance.change_sladefinition',
                    'maintenance.view_sladefinition',
                ]
            },
            'CMMS_Technician': {
                'description': 'فني صيانة - تنفيذ أوامر الشغل',
                'permissions': [
                    'maintenance.view_device',
                    'maintenance.change_device',
                    'maintenance.view_servicerequest',
                    'maintenance.change_servicerequest',
                    'maintenance.view_workorder',
                    'maintenance.change_workorder',
                ]
            },
            'CMMS_Supervisor': {
                'description': 'مشرف صيانة - مراجعة وموافقة',
                'permissions': [
                    'maintenance.view_device',
                    'maintenance.change_device',
                    'maintenance.add_servicerequest',
                    'maintenance.change_servicerequest',
                    'maintenance.view_servicerequest',
                    'maintenance.add_workorder',
                    'maintenance.change_workorder',
                    'maintenance.view_workorder',
                ]
            },
            'CMMS_User': {
                'description': 'مستخدم عادي - إنشاء بلاغات فقط',
                'permissions': [
                    'maintenance.view_device',
                    'maintenance.add_servicerequest',
                    'maintenance.view_servicerequest',
                ]
            }
        }
        
        for group_name, config in groups_config.items():
            if not dry_run:
                group, created = Group.objects.get_or_create(name=group_name)
                
                if created:
                    self.stdout.write(f'تم إنشاء مجموعة: {group_name}')
                else:
                    self.stdout.write(f'مجموعة موجودة: {group_name}')
                
                # إضافة الصلاحيات
                for perm_codename in config['permissions']:
                    try:
                        app_label, codename = perm_codename.split('.')
                        permission = Permission.objects.get(
                            content_type__app_label=app_label,
                            codename=codename
                        )
                        group.permissions.add(permission)
                    except Permission.DoesNotExist:
                        self.stdout.write(
                            self.style.WARNING(f'صلاحية غير موجودة: {perm_codename}')
                        )
            else:
                self.stdout.write(f'[تجريبي] سيتم إنشاء مجموعة: {group_name}')
    
    def setup_default_data(self, dry_run=False):
        """إعداد البيانات الافتراضية"""
        
        self.stdout.write('إعداد البيانات الافتراضية...')
        
        # إنشاء فئات الأجهزة الافتراضية
        device_categories = [
            {'name': 'أجهزة التنفس الصناعي', 'description': 'أجهزة دعم التنفس'},
            {'name': 'أجهزة المراقبة', 'description': 'أجهزة مراقبة العلامات الحيوية'},
            {'name': 'أجهزة الأشعة', 'description': 'أجهزة التصوير الطبي'},
            {'name': 'أجهزة المختبر', 'description': 'أجهزة التحاليل الطبية'},
            {'name': 'أجهزة الجراحة', 'description': 'أجهزة العمليات الجراحية'},
        ]
        
        for category_data in device_categories:
            if not dry_run:
                category, created = DeviceCategory.objects.get_or_create(
                    name=category_data['name'],
                    defaults={'description': category_data['description']}
                )
                if created:
                    self.stdout.write(f'تم إنشاء فئة جهاز: {category_data["name"]}')
            else:
                self.stdout.write(f'[تجريبي] سيتم إنشاء فئة جهاز: {category_data["name"]}')
        
        # إنشاء تعريفات SLA افتراضية
        sla_definitions = [
            {
                'name': 'حرج - فوري',
                'description': 'للأجهزة الحرجة - استجابة فورية',
                'response_time_minutes': 5,
                'resolution_time_hours': 1,
                'escalation_time_minutes': 15,
            },
            {
                'name': 'عالي - سريع',
                'description': 'للأجهزة عالية الأولوية',
                'response_time_minutes': 30,
                'resolution_time_hours': 4,
                'escalation_time_minutes': 60,
            },
            {
                'name': 'عادي - قياسي',
                'description': 'للأجهزة عادية الأولوية',
                'response_time_minutes': 120,
                'resolution_time_hours': 24,
                'escalation_time_minutes': 240,
            }
        ]
        
        for sla_data in sla_definitions:
            if not dry_run:
                sla, created = SLADefinition.objects.get_or_create(
                    name=sla_data['name'],
                    defaults={
                        'description': sla_data['description'],
                        'response_time_minutes': sla_data['response_time_minutes'],
                        'resolution_time_hours': sla_data['resolution_time_hours'],
                        'escalation_time_minutes': sla_data['escalation_time_minutes'],
                        'is_active': True,
                    }
                )
                if created:
                    self.stdout.write(f'تم إنشاء تعريف SLA: {sla_data["name"]}')
            else:
                self.stdout.write(f'[تجريبي] سيتم إنشاء تعريف SLA: {sla_data["name"]}')
        
        # إنشاء خطط صيانة افتراضية
        job_plans = [
            {
                'title': 'صيانة وقائية عامة',
                'description': 'خطة صيانة وقائية عامة للأجهزة',
                'estimated_duration_minutes': 60,
                'steps': [
                    {'step_number': 1, 'title': 'فحص بصري', 'description': 'فحص الجهاز بصرياً للتأكد من سلامته', 'estimated_minutes': 10},
                    {'step_number': 2, 'title': 'تنظيف خارجي', 'description': 'تنظيف الجهاز من الخارج', 'estimated_minutes': 15},
                    {'step_number': 3, 'title': 'فحص الكابلات', 'description': 'فحص جميع الكابلات والوصلات', 'estimated_minutes': 10},
                    {'step_number': 4, 'title': 'اختبار التشغيل', 'description': 'اختبار تشغيل الجهاز والتأكد من عمله', 'estimated_minutes': 20},
                    {'step_number': 5, 'title': 'توثيق النتائج', 'description': 'توثيق نتائج الصيانة', 'estimated_minutes': 5},
                ]
            }
        ]
        
        for plan_data in job_plans:
            if not dry_run:
                job_plan, created = JobPlan.objects.get_or_create(
                    title=plan_data['title'],
                    defaults={
                        'description': plan_data['description'],
                        'estimated_duration_minutes': plan_data['estimated_duration_minutes'],
                        'is_active': True,
                        'created_by_id': 1,
                    }
                )
                
                if created:
                    self.stdout.write(f'تم إنشاء خطة صيانة: {plan_data["title"]}')
                    
                    # إضافة خطوات الصيانة
                    for step_data in plan_data['steps']:
                        JobPlanStep.objects.create(
                            job_plan=job_plan,
                            step_number=step_data['step_number'],
                            title=step_data['title'],
                            description=step_data['description'],
                            estimated_minutes=step_data['estimated_minutes']
                        )
            else:
                self.stdout.write(f'[تجريبي] سيتم إنشاء خطة صيانة: {plan_data["title"]}')
    
    def migrate_device_data(self, dry_run=False):
        """ترحيل بيانات الأجهزة وإعداد QR codes"""
        
        self.stdout.write('ترحيل بيانات الأجهزة...')
        
        devices = Device.objects.all()
        updated_count = 0
        
        for device in devices:
            needs_update = False
            
            # التحقق من وجود QR code
            if not device.qr_token:
                if not dry_run:
                    device.qr_token = f"device:{device.id}"
                    needs_update = True
                else:
                    self.stdout.write(f'[تجريبي] سيتم إنشاء QR token للجهاز: {device.name}')
            
            # تحديث حالة الجهاز إذا لم تكن محددة
            if not device.status:
                if not dry_run:
                    device.status = 'working'
                    needs_update = True
            
            # تحديث تاريخ آخر صيانة إذا لم يكن محدد
            if not device.last_maintenance:
                if not dry_run:
                    device.last_maintenance = timezone.now().date() - timedelta(days=30)
                    needs_update = True
            
            if needs_update and not dry_run:
                device.save()
                updated_count += 1
        
        if not dry_run:
            self.stdout.write(f'تم تحديث {updated_count} جهاز')
        else:
            self.stdout.write(f'[تجريبي] سيتم تحديث {devices.count()} جهاز')
