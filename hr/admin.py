# hr/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth import get_user_model

User = get_user_model()

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    # اعرض حقول مفيدة في القائمة
    list_display = ("username", "email", "role", "hospital", "is_staff", "is_superuser", "is_active")
    list_filter  = ("is_staff", "is_superuser", "is_active", "role")
    search_fields = ("username", "email", "first_name", "last_name")
    ordering = ("username",)

    # لو عندك M2M مثل departments
    filter_horizontal = ("groups", "user_permissions", "departments",) if hasattr(User, "departments") else ("groups", "user_permissions")

    # حقول الإنشاء (add form)
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("username", "email", "password1", "password2", "role", "hospital", "is_staff", "is_superuser", "is_active"),
        }),
    )

    # حقول التعديل (change form)
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "email")}),
        ("Hospital info", {"fields": tuple(f for f in ("role","hospital","departments") if hasattr(User, f))}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )