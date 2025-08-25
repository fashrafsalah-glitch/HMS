# هنا بنعمل context processors عشان نخلي الصلاحيات متاحة في كل القوالب
from .permissions import PermissionChecker

def permissions_context(request):
    """
    إضافة فاحص الصلاحيات لكل القوالب
    """
    if request.user.is_authenticated:
        return {
            'perms_checker': PermissionChecker(request.user),
            'user_roles': request.user.groups.values_list('name', flat=True)
        }
    return {
        'perms_checker': None,
        'user_roles': []
    }
