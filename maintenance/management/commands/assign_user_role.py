# هنا بنعمل command لتعيين المستخدمين للأدوار المختلفة
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from maintenance.permissions import assign_user_to_role, remove_user_from_role, ROLES, get_user_roles

class Command(BaseCommand):
    help = 'تعيين أو إزالة مستخدم من دور معين'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='اسم المستخدم')
        parser.add_argument('role', type=str, help='اسم الدور')
        parser.add_argument(
            '--remove',
            action='store_true',
            help='إزالة المستخدم من الدور بدلاً من إضافته',
        )
        parser.add_argument(
            '--list-roles',
            action='store_true',
            help='عرض أدوار المستخدم الحالية',
        )

    def handle(self, *args, **options):
        username = options['username']
        role = options['role']

        # التحقق من وجود المستخدم
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f'المستخدم "{username}" غير موجود')

        # عرض الأدوار الحالية
        if options['list_roles']:
            current_roles = get_user_roles(user)
            self.stdout.write(f'الأدوار الحالية للمستخدم {username}:')
            if current_roles:
                for role_name in current_roles:
                    self.stdout.write(f'  - {role_name}')
            else:
                self.stdout.write('  لا توجد أدوار معينة')
            return

        # التحقق من صحة الدور
        if role not in ROLES:
            self.stdout.write(
                self.style.ERROR(f'الدور "{role}" غير صحيح')
            )
            self.stdout.write('الأدوار المتاحة:')
            for role_name, role_data in ROLES.items():
                self.stdout.write(f'  - {role_name}: {role_data["description"]}')
            return

        # تنفيذ العملية
        if options['remove']:
            success = remove_user_from_role(user, role)
            if success:
                self.stdout.write(
                    self.style.SUCCESS(f'تم إزالة المستخدم {username} من دور {role}')
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f'فشل في إزالة المستخدم من الدور')
                )
        else:
            success = assign_user_to_role(user, role)
            if success:
                self.stdout.write(
                    self.style.SUCCESS(f'تم تعيين المستخدم {username} لدور {role}')
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f'فشل في تعيين المستخدم للدور')
                )

        # عرض الأدوار الحالية بعد التغيير
        current_roles = get_user_roles(user)
        self.stdout.write(f'\nالأدوار الحالية للمستخدم {username}:')
        if current_roles:
            for role_name in current_roles:
                self.stdout.write(f'  - {role_name}')
        else:
            self.stdout.write('  لا توجد أدوار معينة')
