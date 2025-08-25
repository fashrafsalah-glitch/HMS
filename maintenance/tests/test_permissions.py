# اختبارات نظام الصلاحيات والـ RBAC للـ CMMS
# هنا بنختبر الأدوار والصلاحيات والتحكم في الوصول

from django.test import TestCase
from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.http import HttpRequest
from django.contrib.auth.models import AnonymousUser
from unittest.mock import Mock

from maintenance.models import Device
from maintenance.models_cmms import ServiceRequest, WorkOrder
from maintenance.permissions import (
    setup_cmms_permissions, assign_user_role, remove_user_role,
    has_cmms_permission, require_cmms_permission, PermissionChecker,
    get_user_roles, CMMS_ROLES
)


class CMMSPermissionsSetupTest(TestCase):
    """اختبارات إعداد صلاحيات CMMS"""
    
    def test_setup_cmms_permissions(self):
        """اختبار إعداد الصلاحيات والأدوار"""
        # تشغيل إعداد الصلاحيات
        setup_cmms_permissions()
        
        # التحقق من إنشاء المجموعات
        expected_groups = ['CMMS_Admin', 'CMMS_Supervisor', 'CMMS_Technician', 'CMMS_Clinician']
        
        for group_name in expected_groups:
            self.assertTrue(
                Group.objects.filter(name=group_name).exists(),
                f"المجموعة {group_name} غير موجودة"
            )
            
        # التحقق من إنشاء الصلاحيات المخصصة
        custom_permissions = [
            'view_cmms_dashboard',
            'manage_service_requests',
            'manage_work_orders',
            'manage_spare_parts',
            'view_reports'
        ]
        
        device_ct = ContentType.objects.get_for_model(Device)
        
        for perm_codename in custom_permissions:
            self.assertTrue(
                Permission.objects.filter(
                    codename=perm_codename,
                    content_type=device_ct
                ).exists(),
                f"الصلاحية {perm_codename} غير موجودة"
            )
            
    def test_admin_permissions(self):
        """اختبار صلاحيات المدير"""
        setup_cmms_permissions()
        
        admin_group = Group.objects.get(name='CMMS_Admin')
        
        # يجب أن يكون لدى المدير جميع الصلاحيات
        expected_permissions = [
            'view_cmms_dashboard',
            'manage_service_requests',
            'manage_work_orders',
            'manage_spare_parts',
            'manage_preventive_maintenance',
            'manage_calibrations',
            'view_reports',
            'manage_users'
        ]
        
        admin_permissions = admin_group.permissions.values_list('codename', flat=True)
        
        for perm in expected_permissions:
            self.assertIn(perm, admin_permissions, f"المدير لا يملك صلاحية {perm}")
            
    def test_technician_permissions(self):
        """اختبار صلاحيات الفني"""
        setup_cmms_permissions()
        
        technician_group = Group.objects.get(name='CMMS_Technician')
        
        # الصلاحيات المتوقعة للفني
        expected_permissions = [
            'view_cmms_dashboard',
            'view_service_requests',
            'update_work_orders',
            'view_spare_parts'
        ]
        
        # الصلاحيات التي لا يجب أن يملكها الفني
        forbidden_permissions = [
            'manage_users',
            'delete_service_requests',
            'manage_spare_parts'
        ]
        
        technician_permissions = technician_group.permissions.values_list('codename', flat=True)
        
        for perm in expected_permissions:
            self.assertIn(perm, technician_permissions, f"الفني لا يملك صلاحية {perm}")
            
        for perm in forbidden_permissions:
            self.assertNotIn(perm, technician_permissions, f"الفني يملك صلاحية محظورة {perm}")


class UserRoleManagementTest(TestCase):
    """اختبارات إدارة أدوار المستخدمين"""
    
    def setUp(self):
        """إعداد البيانات للاختبار"""
        setup_cmms_permissions()
        
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
    def test_assign_user_role(self):
        """اختبار تعيين دور للمستخدم"""
        # تعيين دور المدير
        result = assign_user_role(self.user, 'CMMS_Admin')
        self.assertTrue(result)
        
        # التحقق من إضافة المستخدم للمجموعة
        admin_group = Group.objects.get(name='CMMS_Admin')
        self.assertTrue(self.user.groups.filter(name='CMMS_Admin').exists())
        
        # اختبار تعيين دور غير موجود
        result = assign_user_role(self.user, 'NonExistentRole')
        self.assertFalse(result)
        
    def test_remove_user_role(self):
        """اختبار إزالة دور من المستخدم"""
        # تعيين دور أولاً
        assign_user_role(self.user, 'CMMS_Technician')
        self.assertTrue(self.user.groups.filter(name='CMMS_Technician').exists())
        
        # إزالة الدور
        result = remove_user_role(self.user, 'CMMS_Technician')
        self.assertTrue(result)
        
        # التحقق من إزالة المستخدم من المجموعة
        self.assertFalse(self.user.groups.filter(name='CMMS_Technician').exists())
        
    def test_get_user_roles(self):
        """اختبار الحصول على أدوار المستخدم"""
        # تعيين عدة أدوار
        assign_user_role(self.user, 'CMMS_Admin')
        assign_user_role(self.user, 'CMMS_Technician')
        
        roles = get_user_roles(self.user)
        
        self.assertIn('CMMS_Admin', roles)
        self.assertIn('CMMS_Technician', roles)
        self.assertEqual(len(roles), 2)
        
    def test_multiple_roles_assignment(self):
        """اختبار تعيين أدوار متعددة"""
        # يجب أن يتمكن المستخدم من الحصول على أدوار متعددة
        assign_user_role(self.user, 'CMMS_Supervisor')
        assign_user_role(self.user, 'CMMS_Technician')
        
        roles = get_user_roles(self.user)
        self.assertEqual(len(roles), 2)
        
        # التحقق من الصلاحيات المجمعة
        user_permissions = self.user.get_all_permissions()
        
        # يجب أن يكون لديه صلاحيات من كلا الدورين
        self.assertTrue(len(user_permissions) > 0)


class PermissionCheckTest(TestCase):
    """اختبارات فحص الصلاحيات"""
    
    def setUp(self):
        """إعداد البيانات للاختبار"""
        setup_cmms_permissions()
        
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='testpass123'
        )
        
        self.technician_user = User.objects.create_user(
            username='technician',
            email='tech@example.com',
            password='testpass123'
        )
        
        self.regular_user = User.objects.create_user(
            username='regular',
            email='regular@example.com',
            password='testpass123'
        )
        
        # تعيين الأدوار
        assign_user_role(self.admin_user, 'CMMS_Admin')
        assign_user_role(self.technician_user, 'CMMS_Technician')
        
    def test_has_cmms_permission_function(self):
        """اختبار دالة فحص الصلاحيات"""
        # المدير يجب أن يملك جميع الصلاحيات
        self.assertTrue(
            has_cmms_permission(self.admin_user, 'manage_service_requests')
        )
        
        # الفني يجب أن يملك صلاحيات محددة
        self.assertTrue(
            has_cmms_permission(self.technician_user, 'view_service_requests')
        )
        
        # الفني لا يجب أن يملك صلاحيات الإدارة
        self.assertFalse(
            has_cmms_permission(self.technician_user, 'manage_users')
        )
        
        # المستخدم العادي لا يجب أن يملك صلاحيات CMMS
        self.assertFalse(
            has_cmms_permission(self.regular_user, 'view_cmms_dashboard')
        )
        
    def test_permission_decorator(self):
        """اختبار decorator الصلاحيات"""
        @require_cmms_permission('manage_service_requests')
        def test_view(request):
            return "Success"
            
        # إنشاء طلب وهمي
        request = Mock()
        request.user = self.admin_user
        
        # المدير يجب أن يتمكن من الوصول
        result = test_view(request)
        self.assertEqual(result, "Success")
        
        # الفني لا يجب أن يتمكن من الوصول
        request.user = self.technician_user
        
        with self.assertRaises(Exception):  # يجب أن يرفع استثناء أو يعيد 403
            test_view(request)
            
    def test_anonymous_user_permissions(self):
        """اختبار صلاحيات المستخدم المجهول"""
        anonymous_user = AnonymousUser()
        
        # المستخدم المجهول لا يجب أن يملك أي صلاحيات
        self.assertFalse(
            has_cmms_permission(anonymous_user, 'view_cmms_dashboard')
        )
        
    def test_superuser_permissions(self):
        """اختبار صلاحيات المدير العام"""
        superuser = User.objects.create_user(
            username='superuser',
            email='super@example.com',
            password='testpass123',
            is_superuser=True
        )
        
        # المدير العام يجب أن يملك جميع الصلاحيات
        self.assertTrue(
            has_cmms_permission(superuser, 'manage_service_requests')
        )
        
        self.assertTrue(
            has_cmms_permission(superuser, 'manage_users')
        )


class PermissionCheckerTest(TestCase):
    """اختبارات فئة فحص الصلاحيات"""
    
    def setUp(self):
        """إعداد البيانات للاختبار"""
        setup_cmms_permissions()
        
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='testpass123'
        )
        
        assign_user_role(self.admin_user, 'CMMS_Admin')
        
    def test_permission_checker_initialization(self):
        """اختبار إنشاء فاحص الصلاحيات"""
        checker = PermissionChecker(self.admin_user)
        
        self.assertEqual(checker.user, self.admin_user)
        self.assertIsNotNone(checker.user_roles)
        
    def test_permission_checker_methods(self):
        """اختبار دوال فاحص الصلاحيات"""
        checker = PermissionChecker(self.admin_user)
        
        # اختبار فحص الدور
        self.assertTrue(checker.has_role('CMMS_Admin'))
        self.assertFalse(checker.has_role('CMMS_Technician'))
        
        # اختبار فحص الصلاحية
        self.assertTrue(checker.has_permission('manage_service_requests'))
        
        # اختبار فحص صلاحيات متعددة
        self.assertTrue(checker.has_any_permission([
            'manage_service_requests',
            'view_reports'
        ]))
        
        self.assertTrue(checker.has_all_permissions([
            'view_cmms_dashboard',
            'manage_service_requests'
        ]))
        
    def test_permission_checker_with_regular_user(self):
        """اختبار فاحص الصلاحيات مع مستخدم عادي"""
        regular_user = User.objects.create_user(
            username='regular',
            email='regular@example.com',
            password='testpass123'
        )
        
        checker = PermissionChecker(regular_user)
        
        # المستخدم العادي لا يجب أن يملك أدوار CMMS
        self.assertFalse(checker.has_role('CMMS_Admin'))
        self.assertFalse(checker.has_permission('manage_service_requests'))
        
        # لكن يجب أن يعمل الفاحص بدون أخطاء
        self.assertIsNotNone(checker.user_roles)
        self.assertEqual(len(checker.user_roles), 0)


class RoleHierarchyTest(TestCase):
    """اختبارات التسلسل الهرمي للأدوار"""
    
    def setUp(self):
        """إعداد البيانات للاختبار"""
        setup_cmms_permissions()
        
    def test_admin_has_all_permissions(self):
        """اختبار أن المدير يملك جميع الصلاحيات"""
        admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='testpass123'
        )
        
        assign_user_role(admin_user, 'CMMS_Admin')
        
        # قائمة بجميع الصلاحيات المتوقعة
        all_permissions = [
            'view_cmms_dashboard',
            'manage_service_requests',
            'manage_work_orders',
            'manage_spare_parts',
            'view_reports'
        ]
        
        for permission in all_permissions:
            self.assertTrue(
                has_cmms_permission(admin_user, permission),
                f"المدير لا يملك صلاحية {permission}"
            )
            
    def test_supervisor_permissions_subset(self):
        """اختبار أن صلاحيات المشرف مجموعة فرعية من المدير"""
        supervisor_user = User.objects.create_user(
            username='supervisor',
            email='supervisor@example.com',
            password='testpass123'
        )
        
        assign_user_role(supervisor_user, 'CMMS_Supervisor')
        
        # المشرف يجب أن يملك صلاحيات أكثر من الفني
        supervisor_permissions = [
            'view_cmms_dashboard',
            'manage_service_requests',
            'view_work_orders',
            'view_reports'
        ]
        
        for permission in supervisor_permissions:
            self.assertTrue(
                has_cmms_permission(supervisor_user, permission),
                f"المشرف لا يملك صلاحية {permission}"
            )
            
        # لكن لا يجب أن يملك صلاحيات إدارة المستخدمين
        self.assertFalse(
            has_cmms_permission(supervisor_user, 'manage_users')
        )
        
    def test_technician_limited_permissions(self):
        """اختبار الصلاحيات المحدودة للفني"""
        technician_user = User.objects.create_user(
            username='technician',
            email='technician@example.com',
            password='testpass123'
        )
        
        assign_user_role(technician_user, 'CMMS_Technician')
        
        # الفني يجب أن يملك صلاحيات محدودة
        allowed_permissions = [
            'view_cmms_dashboard',
            'view_service_requests',
            'update_work_orders'
        ]
        
        forbidden_permissions = [
            'manage_service_requests',
            'delete_work_orders',
            'manage_spare_parts',
            'manage_users'
        ]
        
        for permission in allowed_permissions:
            self.assertTrue(
                has_cmms_permission(technician_user, permission),
                f"الفني لا يملك صلاحية مسموحة {permission}"
            )
            
        for permission in forbidden_permissions:
            self.assertFalse(
                has_cmms_permission(technician_user, permission),
                f"الفني يملك صلاحية محظورة {permission}"
            )


class ContextProcessorTest(TestCase):
    """اختبارات معالج السياق للصلاحيات"""
    
    def setUp(self):
        """إعداد البيانات للاختبار"""
        setup_cmms_permissions()
        
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        assign_user_role(self.user, 'CMMS_Admin')
        
    def test_context_processor_import(self):
        """اختبار استيراد معالج السياق"""
        from maintenance.context_processors import cmms_permissions
        
        # إنشاء طلب وهمي
        request = Mock()
        request.user = self.user
        
        context = cmms_permissions(request)
        
        # التحقق من وجود البيانات المطلوبة في السياق
        self.assertIn('permission_checker', context)
        self.assertIn('user_roles', context)
        
        # التحقق من صحة البيانات
        self.assertEqual(context['user_roles'], ['CMMS_Admin'])
        self.assertIsInstance(context['permission_checker'], PermissionChecker)
        
    def test_context_processor_with_anonymous_user(self):
        """اختبار معالج السياق مع مستخدم مجهول"""
        from maintenance.context_processors import cmms_permissions
        
        request = Mock()
        request.user = AnonymousUser()
        
        context = cmms_permissions(request)
        
        # يجب أن يعمل بدون أخطاء مع المستخدم المجهول
        self.assertIn('permission_checker', context)
        self.assertIn('user_roles', context)
        self.assertEqual(context['user_roles'], [])
