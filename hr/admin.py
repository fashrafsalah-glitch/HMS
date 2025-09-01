# hr/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth import get_user_model
from .models import (
    Certificate, ProfessionalPracticePermit, HealthInsurance,
    ShiftType, WorkArea, Schedule, StaffDailyAvailability,
    ShiftAssignment, ShiftSwapRequest, Attendance, DeductionType,
    BonusType, Payroll, Deduction, Bonus, VacationPolicy,
    VacationBalance, LeaveRequest, StaffTask
)

User = get_user_model()

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    actions = ['clear_old_qr_codes', 'regenerate_qr_codes']
    
    @admin.action(description='مسح جميع رموز QR القديمة (Clear all old QR codes)')
    def clear_old_qr_codes(self, request, queryset):
        updated_count = 0
        for user in queryset:
            if user.qr_code:
                user.qr_code.delete(save=False)
            user.qr_token = None
            user.save(update_fields=['qr_code', 'qr_token'])
            updated_count += 1
        
        self.message_user(
            request,
            f'تم مسح رموز QR من {updated_count} مستخدم بنجاح (Cleared QR codes from {updated_count} users)'
        )
    
    @admin.action(description='إعادة توليد رموز QR آمنة (Regenerate secure QR codes)')
    def regenerate_qr_codes(self, request, queryset):
        updated_count = 0
        for user in queryset:
            if user.qr_code:
                user.qr_code.delete(save=False)
            user.generate_qr_code()
            user.save(update_fields=['qr_code', 'qr_token'])
            updated_count += 1
        
        self.message_user(
            request,
            f'تم إعادة توليد رموز QR آمنة لـ {updated_count} مستخدم (Regenerated secure QR codes for {updated_count} users)'
        )

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

# HR Models
@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ['staff', 'certificate_type', 'location_obtained', 'date_obtained']
    list_filter = ['certificate_type', 'date_obtained']
    search_fields = ['staff__username', 'certificate_type', 'location_obtained']

@admin.register(ProfessionalPracticePermit)
class ProfessionalPracticePermitAdmin(admin.ModelAdmin):
    list_display = ['staff', 'date_obtained', 'expiry_date', 'is_expired']
    list_filter = ['date_obtained', 'expiry_date']
    search_fields = ['staff__username']
    
    def is_expired(self, obj):
        from django.utils import timezone
        return obj.expiry_date < timezone.now().date()
    is_expired.boolean = True
    is_expired.short_description = 'Expired'

@admin.register(HealthInsurance)
class HealthInsuranceAdmin(admin.ModelAdmin):
    list_display = ['staff', 'issuing_authority', 'date_obtained', 'expiry_date']
    list_filter = ['issuing_authority', 'date_obtained', 'expiry_date']
    search_fields = ['staff__username', 'issuing_authority']

@admin.register(ShiftType)
class ShiftTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'start_time', 'end_time']
    search_fields = ['name']

@admin.register(WorkArea)
class WorkAreaAdmin(admin.ModelAdmin):
    list_display = ['get_name_display', 'department']
    list_filter = ['name', 'department']
    search_fields = ['department__name']

@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ['department', 'schedule_type', 'start_date', 'end_date']
    list_filter = ['schedule_type', 'start_date', 'department']
    search_fields = ['department__name']

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ['staff', 'date', 'entry_time', 'exit_time']
    list_filter = ['date']
    search_fields = ['staff__username', 'staff__first_name', 'staff__last_name']

@admin.register(Payroll)
class PayrollAdmin(admin.ModelAdmin):
    list_display = ['staff', 'period_start', 'period_end', 'base_salary', 'net_salary']
    list_filter = ['period_start']
    search_fields = ['staff__username', 'staff__first_name', 'staff__last_name']

@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ['staff', 'leave_type', 'start_date', 'end_date', 'status']
    list_filter = ['leave_type', 'status', 'start_date']
    search_fields = ['staff__username', 'staff__first_name', 'staff__last_name']

# Register remaining models
admin.site.register(StaffDailyAvailability)
admin.site.register(ShiftAssignment)
admin.site.register(ShiftSwapRequest)
admin.site.register(DeductionType)
admin.site.register(BonusType)
admin.site.register(Deduction)
admin.site.register(Bonus)
admin.site.register(VacationPolicy)
admin.site.register(VacationBalance)
admin.site.register(StaffTask)