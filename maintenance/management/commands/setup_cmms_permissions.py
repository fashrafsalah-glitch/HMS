# هنا بنعمل command لإعداد الصلاحيات والأدوار للـ CMMS
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from maintenance.permissions import setup_roles_and_permissions, ROLES

class Command(BaseCommand):
    help = 'إعداد الأدوار والصلاحيات للـ CMMS'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='إعادة تعيين جميع الأدوار والصلاحيات',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('بدء إعداد أدوار وصلاحيات CMMS...')
        )

        if options['reset']:
            self.stdout.write('إعادة تعيين الأدوار والصلاحيات...')
            # حذف المجموعات الموجودة
            for role_name in ROLES.keys():
                try:
                    group = Group.objects.get(name=role_name)
                    group.delete()
                    self.stdout.write(f'تم حذف مجموعة: {role_name}')
                except Group.DoesNotExist:
                    pass

        # إعداد الأدوار والصلاحيات
        setup_roles_and_permissions()

        # عرض ملخص الأدوار المنشأة
        self.stdout.write('\n' + '='*50)
        self.stdout.write('ملخص الأدوار والصلاحيات:')
        self.stdout.write('='*50)

        for role_name, role_data in ROLES.items():
            try:
                group = Group.objects.get(name=role_name)
                permissions_count = group.permissions.count()
                users_count = group.user_set.count()
                
                self.stdout.write(f'\n📋 {role_name}:')
                self.stdout.write(f'   الوصف: {role_data["description"]}')
                self.stdout.write(f'   عدد الصلاحيات: {permissions_count}')
                self.stdout.write(f'   عدد المستخدمين: {users_count}')
                
                if users_count > 0:
                    users = group.user_set.all()[:5]  # أول 5 مستخدمين
                    user_names = [u.username for u in users]
                    self.stdout.write(f'   المستخدمين: {", ".join(user_names)}')
                    if users_count > 5:
                        self.stdout.write(f'   ... و {users_count - 5} آخرين')
                        
            except Group.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'خطأ: لم يتم العثور على مجموعة {role_name}')
                )

        self.stdout.write('\n' + '='*50)
        self.stdout.write('تعليمات الاستخدام:')
        self.stdout.write('='*50)
        self.stdout.write('1. لتعيين مستخدم لدور معين:')
        self.stdout.write('   python manage.py assign_user_role <username> <role_name>')
        self.stdout.write('\n2. الأدوار المتاحة:')
        for role_name, role_data in ROLES.items():
            self.stdout.write(f'   - {role_name}: {role_data["description"]}')

        self.stdout.write(
            self.style.SUCCESS('\n✅ تم إعداد أدوار وصلاحيات CMMS بنجاح!')
        )
