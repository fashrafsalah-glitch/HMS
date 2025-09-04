from django.contrib import admin
from .models import (
    Device, DeviceCategory, DeviceSubCategory, Company, DeviceType, DeviceUsage,
    DeviceDailyUsageLog, DeviceUsageLogItem, ScanSession, ScanHistory,
    DeviceTransferLog, PatientTransferLog, DeviceHandoverLog, DeviceAccessory, DeviceAccessoryUsageLog,
    DeviceTransferRequest, DeviceCleaningLog, DeviceSterilizationLog, DeviceMaintenanceLog,
    OperationDefinition, OperationStep, OperationExecution, CalibrationRecord
)

from .models import (
    ServiceRequest, WorkOrder, JobPlan, JobPlanStep, PreventiveMaintenanceSchedule,
    SLADefinition, Supplier, SparePart, SystemNotification, EmailLog,
    NotificationPreference, NotificationTemplate, NotificationQueue
)
from django.contrib import messages

@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ['name', 'model', 'serial_number', 'status', 'availability', 'department', 'room', 'in_use', 'has_qr_code']
    list_filter = ['status', 'availability', 'clean_status', 'sterilization_status', 'department', 'room', 'in_use']
    search_fields = ['name', 'model', 'serial_number', 'qr_token']
    readonly_fields = ['qr_code', 'qr_token', 'created_at']
    actions = ['clear_old_qr_codes', 'regenerate_qr_codes']
    
    def has_qr_code(self, obj):
        return bool(obj.qr_code)
    has_qr_code.boolean = True
    has_qr_code.short_description = 'QR Code'
    
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # Generate QR code if not exists
        if not obj.qr_code or not obj.qr_token:
            obj.generate_qr_code()
            obj.save(update_fields=['qr_code', 'qr_token'])
    
    @admin.action(description='مسح جميع رموز QR القديمة (Clear all old QR codes)')
    def clear_old_qr_codes(self, request, queryset):
        """
        مسح جميع رموز QR القديمة من الأجهزة المحددة
        Clear all old QR codes from selected devices
        """
        updated_count = 0
        for device in queryset:
            # Clear old QR data
            if device.qr_code:
                device.qr_code.delete(save=False)
            device.qr_token = None
            device.save(update_fields=['qr_code', 'qr_token'])
            updated_count += 1
        
        self.message_user(
            request,
            f'تم مسح رموز QR من {updated_count} جهاز بنجاح (Cleared QR codes from {updated_count} devices)'
        )
    
    @admin.action(description='إعادة توليد رموز QR آمنة (Regenerate secure QR codes)')
    def regenerate_qr_codes(self, request, queryset):
        """
        إعادة توليد رموز QR آمنة للأجهزة المحددة
        Regenerate secure QR codes for selected devices
        """
        updated_count = 0
        for device in queryset:
            # Clear old QR first
            if device.qr_code:
                device.qr_code.delete(save=False)
            
            # Generate new secure QR
            device.generate_qr_code()
            device.save(update_fields=['qr_code', 'qr_token'])
            updated_count += 1
        
        self.message_user(
            request,
            f'تم إعادة توليد رموز QR آمنة لـ {updated_count} جهاز (Regenerated secure QR codes for {updated_count} devices)'
        )

@admin.register(DeviceDailyUsageLog)
class DeviceDailyUsageLogAdmin(admin.ModelAdmin):
    list_display = ['device', 'date', 'total_usage_time']
    list_filter = ['date']
    search_fields = ['device__name']

@admin.register(DeviceUsageLogItem)
class DeviceUsageLogItemAdmin(admin.ModelAdmin):
    list_display = ['usage_log', 'device', 'scanned_at']
    list_filter = ['scanned_at']
    search_fields = ['device__name', 'device__model']

@admin.register(ScanSession)
class ScanSessionAdmin(admin.ModelAdmin):
    list_display = ['session_id', 'user', 'patient', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    readonly_fields = ['session_id', 'created_at', 'updated_at']

@admin.register(ScanHistory)
class ScanHistoryAdmin(admin.ModelAdmin):
    list_display = ['session', 'scanned_code', 'entity_type', 'entity_id', 'scanned_at', 'is_valid']
    list_filter = ['entity_type', 'is_valid', 'scanned_at']
    search_fields = ['scanned_code', 'entity_type']

@admin.register(DeviceCategory)
class DeviceCategoryAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']

@admin.register(DeviceSubCategory)
class DeviceSubCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'category']
    list_filter = ['category']
    search_fields = ['name']

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']

@admin.register(DeviceType)
class DeviceTypeAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']

@admin.register(DeviceUsage)
class DeviceUsageAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']

@admin.register(DeviceTransferRequest)
class DeviceTransferRequestAdmin(admin.ModelAdmin):
    list_display = ['device', 'from_department', 'to_department', 'status', 'requested_at']
    list_filter = ['status', 'requested_at', 'from_department', 'to_department']
    search_fields = ['device__name', 'reason']

@admin.register(DeviceCleaningLog)
class DeviceCleaningLogAdmin(admin.ModelAdmin):
    list_display = ['device', 'cleaned_by', 'cleaned_at']
    list_filter = ['cleaned_at']
    search_fields = ['device__name', 'cleaned_by__username']

@admin.register(DeviceSterilizationLog)
class DeviceSterilizationLogAdmin(admin.ModelAdmin):
    list_display = ['device', 'sterilized_by', 'sterilized_at']
    list_filter = ['sterilized_at']
    search_fields = ['device__name', 'sterilized_by__username']

@admin.register(DeviceMaintenanceLog)
class DeviceMaintenanceLogAdmin(admin.ModelAdmin):
    list_display = ['device']
    search_fields = ['device__name']

# CMMS Models
@admin.register(ServiceRequest)
class ServiceRequestAdmin(admin.ModelAdmin):
    list_display = ['title', 'device', 'status', 'priority']
    list_filter = ['status', 'priority', 'created_at']
    search_fields = ['title', 'device__name']

@admin.register(WorkOrder)
class WorkOrderAdmin(admin.ModelAdmin):
    list_display = ['wo_number', 'title', 'assignee', 'status', 'priority']
    list_filter = ['status', 'priority', 'wo_type']
    search_fields = ['wo_number', 'title', 'service_request__request_number']

@admin.register(JobPlan)
class JobPlanAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name', 'description']

@admin.register(JobPlanStep)
class JobPlanStepAdmin(admin.ModelAdmin):
    list_display = ['job_plan', 'step_number', 'description']
    list_filter = ['job_plan']
    search_fields = ['description']

@admin.register(PreventiveMaintenanceSchedule)
class PreventiveMaintenanceScheduleAdmin(admin.ModelAdmin):
    list_display = ['device', 'job_plan', 'frequency', 'next_due_date']
    list_filter = ['frequency', 'next_due_date']
    search_fields = ['device__name', 'job_plan__name']

@admin.register(SLADefinition)
class SLADefinitionAdmin(admin.ModelAdmin):
    list_display = ['name', 'priority', 'response_time_hours', 'resolution_time_hours']
    list_filter = ['priority']
    search_fields = ['name', 'description']

# Notification Models
@admin.register(SystemNotification)
class SystemNotificationAdmin(admin.ModelAdmin):
    list_display = ['title', 'notification_type', 'priority', 'is_read', 'created_at']
    list_filter = ['notification_type', 'priority', 'is_read', 'created_at']
    search_fields = ['title', 'message']

@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ['recipient_email', 'subject', 'created_at']
    list_filter = ['created_at']
    search_fields = ['recipient_email', 'subject']

@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ['user', 'email_enabled']
    list_filter = ['email_enabled']
    search_fields = ['user__username']

@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'notification_type', 'is_active']
    list_filter = ['notification_type', 'is_active']
    search_fields = ['name', 'subject']

@admin.register(NotificationQueue)
class NotificationQueueAdmin(admin.ModelAdmin):
    list_display = ['notification', 'status']
    list_filter = ['status']
    search_fields = ['notification__title']

# Spare Parts, Calibration and Downtime Models
@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'contact_person', 'phone', 'email', 'status']
    list_filter = ['status']
    search_fields = ['name', 'code', 'contact_person', 'email']

@admin.register(SparePart)
class SparePartAdmin(admin.ModelAdmin):
    list_display = ['name', 'part_number', 'current_stock', 'minimum_stock', 'primary_supplier', 'unit_cost']
    list_filter = ['primary_supplier', 'unit', 'status']
    search_fields = ['name', 'part_number', 'description']


# ═══════════════════════════════════════════════════════════════════════════
# DYNAMIC QR OPERATION SYSTEM ADMIN
# ═══════════════════════════════════════════════════════════════════════════

class OperationStepInline(admin.TabularInline):
    model = OperationStep
    extra = 1
    ordering = ['order']
    fields = ['order', 'entity_type', 'is_required', 'description', 'validation_rule', 'allowed_entity_ids']


@admin.register(OperationDefinition)
class OperationDefinitionAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'is_active', 'auto_execute', 'requires_confirmation', 'session_timeout_minutes']
    list_filter = ['is_active', 'auto_execute', 'requires_confirmation', 'log_to_usage', 'log_to_transfer', 'log_to_handover']
    search_fields = ['name', 'code', 'description']
    inlines = [OperationStepInline]
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'code', 'description', 'is_active')
        }),
        ('Behavior Settings', {
            'fields': ('auto_execute', 'requires_confirmation', 'session_timeout_minutes', 'allow_multiple_executions')
        }),
        ('Logging Settings', {
            'fields': ('log_to_usage', 'log_to_transfer', 'log_to_handover')
        }),
    )


@admin.register(OperationStep)
class OperationStepAdmin(admin.ModelAdmin):
    list_display = ['operation', 'order', 'entity_type', 'is_required', 'description']
    list_filter = ['operation', 'entity_type', 'is_required']
    search_fields = ['operation__name', 'entity_type', 'description']
    ordering = ['operation', 'order']


@admin.register(OperationExecution)
class OperationExecutionAdmin(admin.ModelAdmin):
    list_display = ['operation', 'session', 'executed_by', 'status', 'started_at', 'completed_at']
    list_filter = ['status', 'operation', 'started_at']
    search_fields = ['operation__name', 'session__session_id', 'executed_by__username']
    readonly_fields = ['session', 'operation', 'executed_by', 'started_at', 'completed_at', 'scanned_entities', 'result_data', 'created_logs']
    fieldsets = (
        ('Execution Info', {
            'fields': ('operation', 'session', 'executed_by', 'status')
        }),
        ('Timing', {
            'fields': ('started_at', 'completed_at')
        }),
        ('Data', {
            'fields': ('scanned_entities', 'result_data', 'error_message', 'created_logs')
        }),
    )


@admin.register(CalibrationRecord)
class CalibrationRecordAdmin(admin.ModelAdmin):
    list_display = ['device', 'calibration_date', 'next_calibration_date', 'status', 'calibration_agency', 'certificate_number']
    list_filter = ['status', 'calibration_date', 'next_calibration_date', 'calibration_agency']
    search_fields = ['device__name', 'device__serial_number', 'certificate_number', 'calibration_agency']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'calibration_date'
    
    fieldsets = (
        ('معلومات أساسية', {
            'fields': ('device', 'calibration_date', 'calibration_interval_months', 'next_calibration_date')
        }),
        ('تفاصيل المعايرة', {
            'fields': ('calibrated_by', 'calibration_agency', 'certificate_number', 'status')
        }),
        ('الملفات والملاحظات', {
            'fields': ('certificate_file', 'notes', 'cost')
        }),
        ('معلومات النظام', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('device', 'calibrated_by')

