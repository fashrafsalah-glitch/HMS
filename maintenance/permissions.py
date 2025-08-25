# هنا بنعمل نظام الصلاحيات للـ CMMS عشان نتحكم في مين يقدر يعمل إيه
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import Group, Permission
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps

# تعريف الأدوار الأساسية في النظام
ROLES = {
    'Admin': {
        'description': 'مدير النظام - صلاحيات كاملة',
        'permissions': [
            'add_device', 'change_device', 'delete_device', 'view_device',
            'add_servicerequest', 'change_servicerequest', 'delete_servicerequest', 'view_servicerequest',
            'add_workorder', 'change_workorder', 'delete_workorder', 'view_workorder',
            'add_sparepart', 'change_sparepart', 'delete_sparepart', 'view_sparepart',
            'add_purchaseorder', 'change_purchaseorder', 'delete_purchaseorder', 'view_purchaseorder',
            'view_dashboard', 'view_reports', 'manage_users', 'manage_settings'
        ]
    },
    'Supervisor': {
        'description': 'مشرف الصيانة - إدارة الفرق والمراجعة',
        'permissions': [
            'view_device', 'change_device',
            'add_servicerequest', 'change_servicerequest', 'view_servicerequest',
            'add_workorder', 'change_workorder', 'view_workorder',
            'view_sparepart', 'change_sparepart',
            'add_purchaseorder', 'change_purchaseorder', 'view_purchaseorder',
            'view_dashboard', 'view_reports', 'assign_work_orders', 'approve_work_orders'
        ]
    },
    'Technician': {
        'description': 'فني الصيانة - تنفيذ أوامر الشغل',
        'permissions': [
            'view_device', 'change_device',
            'add_servicerequest', 'view_servicerequest',
            'view_workorder', 'change_workorder',
            'view_sparepart', 'use_spare_parts',
            'view_dashboard'
        ]
    },
    'Clinician': {
        'description': 'طبيب/ممرض - طلب الخدمات والاستعلام',
        'permissions': [
            'view_device',
            'add_servicerequest', 'view_servicerequest',
            'view_workorder'
        ]
    }
}

def has_role(user, role_name):
    """
    التحقق من أن المستخدم له دور معين
    """
    if user.is_superuser:
        return True
    return user.groups.filter(name=role_name).exists()

def has_any_role(user, role_names):
    """
    التحقق من أن المستخدم له أي من الأدوار المحددة
    """
    if user.is_superuser:
        return True
    return user.groups.filter(name__in=role_names).exists()

def has_permission(user, permission_name):
    """
    التحقق من أن المستخدم له صلاحية معينة
    """
    if user.is_superuser:
        return True
    return user.has_perm(f'maintenance.{permission_name}')

def can_view_device(user, device=None):
    """
    التحقق من صلاحية عرض الجهاز
    """
    if user.is_superuser:
        return True
    
    # الجميع يمكنهم عرض الأجهزة
    if has_any_role(user, ['Admin', 'Supervisor', 'Technician', 'Clinician']):
        return True
    
    return False

def can_edit_device(user, device=None):
    """
    التحقق من صلاحية تعديل الجهاز
    """
    if user.is_superuser:
        return True
    
    # المديرين والمشرفين والفنيين يمكنهم تعديل الأجهزة
    return has_any_role(user, ['Admin', 'Supervisor', 'Technician'])

def can_create_service_request(user, device=None):
    """
    التحقق من صلاحية إنشاء طلب خدمة
    """
    if user.is_superuser:
        return True
    
    # الجميع يمكنهم إنشاء طلبات الخدمة
    return has_any_role(user, ['Admin', 'Supervisor', 'Technician', 'Clinician'])

def can_assign_service_request(user, service_request=None):
    """
    التحقق من صلاحية تعيين طلب خدمة
    """
    if user.is_superuser:
        return True
    
    # المديرين والمشرفين فقط يمكنهم تعيين طلبات الخدمة
    return has_any_role(user, ['Admin', 'Supervisor'])

def can_view_work_order(user, work_order=None):
    """
    التحقق من صلاحية عرض أمر الشغل
    """
    if user.is_superuser:
        return True
    
    # إذا كان المستخدم هو الفني المعين أو طالب الخدمة
    if work_order:
        if (work_order.assigned_technician == user or 
            work_order.service_request.requested_by == user):
            return True
    
    # المديرين والمشرفين يمكنهم عرض جميع أوامر الشغل
    return has_any_role(user, ['Admin', 'Supervisor'])

def can_edit_work_order(user, work_order=None):
    """
    التحقق من صلاحية تعديل أمر الشغل
    """
    if user.is_superuser:
        return True
    
    # إذا كان المستخدم هو الفني المعين
    if work_order and work_order.assigned_technician == user:
        return True
    
    # المديرين والمشرفين يمكنهم تعديل جميع أوامر الشغل
    return has_any_role(user, ['Admin', 'Supervisor'])

def can_approve_work_order(user, work_order=None):
    """
    التحقق من صلاحية اعتماد أمر الشغل
    """
    if user.is_superuser:
        return True
    
    # المديرين والمشرفين فقط يمكنهم اعتماد أوامر الشغل
    return has_any_role(user, ['Admin', 'Supervisor'])

def can_manage_spare_parts(user):
    """
    التحقق من صلاحية إدارة قطع الغيار
    """
    if user.is_superuser:
        return True
    
    # المديرين والمشرفين يمكنهم إدارة قطع الغيار
    return has_any_role(user, ['Admin', 'Supervisor'])

def can_use_spare_parts(user):
    """
    التحقق من صلاحية استخدام قطع الغيار
    """
    if user.is_superuser:
        return True
    
    # المديرين والمشرفين والفنيين يمكنهم استخدام قطع الغيار
    return has_any_role(user, ['Admin', 'Supervisor', 'Technician'])

def can_view_dashboard(user):
    """
    التحقق من صلاحية عرض الداشبورد
    """
    if user.is_superuser:
        return True
    
    # الجميع ما عدا الأطباء العاديين يمكنهم عرض الداشبورد
    return has_any_role(user, ['Admin', 'Supervisor', 'Technician'])

def can_view_reports(user):
    """
    التحقق من صلاحية عرض التقارير
    """
    if user.is_superuser:
        return True
    
    # المديرين والمشرفين يمكنهم عرض التقارير
    return has_any_role(user, ['Admin', 'Supervisor'])

def can_manage_users(user):
    """
    التحقق من صلاحية إدارة المستخدمين
    """
    if user.is_superuser:
        return True
    
    # المديرين فقط يمكنهم إدارة المستخدمين
    return has_role(user, 'Admin')

# ديكوريتر للتحقق من الأدوار
def role_required(*roles):
    """
    ديكوريتر للتحقق من أن المستخدم له أحد الأدوار المحددة
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.error(request, 'يجب تسجيل الدخول أولاً')
                return redirect('login')
            
            if not has_any_role(request.user, roles):
                messages.error(request, 'ليس لديك صلاحية للوصول لهذه الصفحة')
                return redirect('dashboard')
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator

def permission_required(permission):
    """
    ديكوريتر للتحقق من صلاحية معينة
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.error(request, 'يجب تسجيل الدخول أولاً')
                return redirect('login')
            
            if not has_permission(request.user, permission):
                messages.error(request, 'ليس لديك صلاحية لتنفيذ هذا الإجراء')
                return redirect('dashboard')
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator

def object_permission_required(permission_func):
    """
    ديكوريتر للتحقق من صلاحية على كائن معين
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.error(request, 'يجب تسجيل الدخول أولاً')
                return redirect('login')
            
            # تمرير المعاملات لدالة التحقق من الصلاحية
            if not permission_func(request.user, *args, **kwargs):
                messages.error(request, 'ليس لديك صلاحية لتنفيذ هذا الإجراء')
                return redirect('dashboard')
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator

# دوال مساعدة لإعداد الأدوار والصلاحيات
def setup_roles_and_permissions():
    """
    إعداد الأدوار والصلاحيات الأساسية في النظام
    """
    from django.contrib.contenttypes.models import ContentType
    from .models import Device
    from .models import ServiceRequest, WorkOrder, SparePart
    
    # إنشاء الصلاحيات المخصصة
    custom_permissions = [
        ('view_dashboard', 'يمكن عرض الداشبورد'),
        ('view_reports', 'يمكن عرض التقارير'),
        ('assign_work_orders', 'يمكن تعيين أوامر الشغل'),
        ('approve_work_orders', 'يمكن اعتماد أوامر الشغل'),
        ('use_spare_parts', 'يمكن استخدام قطع الغيار'),
        ('manage_users', 'يمكن إدارة المستخدمين'),
        ('manage_settings', 'يمكن إدارة الإعدادات'),
    ]
    
    # إنشاء الصلاحيات المخصصة
    device_ct = ContentType.objects.get_for_model(Device)
    for codename, name in custom_permissions:
        Permission.objects.get_or_create(
            codename=codename,
            name=name,
            content_type=device_ct
        )
    
    # إنشاء المجموعات والأدوار
    for role_name, role_data in ROLES.items():
        group, created = Group.objects.get_or_create(name=role_name)
        
        if created:
            print(f"تم إنشاء مجموعة: {role_name}")
        
        # إضافة الصلاحيات للمجموعة
        for permission_codename in role_data['permissions']:
            try:
                # البحث عن الصلاحية في جميع التطبيقات
                permission = Permission.objects.filter(
                    codename=permission_codename
                ).first()
                
                if permission:
                    group.permissions.add(permission)
                else:
                    print(f"تحذير: لم يتم العثور على الصلاحية {permission_codename}")
            except Exception as e:
                print(f"خطأ في إضافة الصلاحية {permission_codename}: {str(e)}")

def assign_user_to_role(user, role_name):
    """
    تعيين مستخدم لدور معين
    """
    try:
        group = Group.objects.get(name=role_name)
        user.groups.add(group)
        return True
    except Group.DoesNotExist:
        return False

def remove_user_from_role(user, role_name):
    """
    إزالة مستخدم من دور معين
    """
    try:
        group = Group.objects.get(name=role_name)
        user.groups.remove(group)
        return True
    except Group.DoesNotExist:
        return False

def get_user_roles(user):
    """
    جلب أدوار المستخدم
    """
    if user.is_superuser:
        return ['SuperUser']
    
    return list(user.groups.values_list('name', flat=True))

def get_role_permissions(role_name):
    """
    جلب صلاحيات دور معين
    """
    if role_name in ROLES:
        return ROLES[role_name]['permissions']
    return []

# كلاس مساعد للتحقق من الصلاحيات في الـ Templates
class PermissionChecker:
    """
    كلاس مساعد للتحقق من الصلاحيات في القوالب
    """
    def __init__(self, user):
        self.user = user
    
    def has_role(self, role_name):
        return has_role(self.user, role_name)
    
    def has_any_role(self, role_names):
        return has_any_role(self.user, role_names)
    
    def can_view_device(self, device=None):
        return can_view_device(self.user, device)
    
    def can_edit_device(self, device=None):
        return can_edit_device(self.user, device)
    
    def can_create_service_request(self, device=None):
        return can_create_service_request(self.user, device)
    
    def can_assign_service_request(self, service_request=None):
        return can_assign_service_request(self.user, service_request)
    
    def can_view_work_order(self, work_order=None):
        return can_view_work_order(self.user, work_order)
    
    def can_edit_work_order(self, work_order=None):
        return can_edit_work_order(self.user, work_order)
    
    def can_approve_work_order(self, work_order=None):
        return can_approve_work_order(self.user, work_order)
    
    def can_manage_spare_parts(self):
        return can_manage_spare_parts(self.user)
    
    def can_use_spare_parts(self):
        return can_use_spare_parts(self.user)
    
    def can_view_dashboard(self):
        return can_view_dashboard(self.user)
    
    def can_view_reports(self):
        return can_view_reports(self.user)
    
    def can_manage_users(self):
        return can_manage_users(self.user)
