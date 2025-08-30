from django.contrib import admin
from .models import (
    Device, DeviceCategory, DeviceSubCategory, Company, DeviceType, DeviceUsage,
    DeviceDailyUsageLog, DeviceUsageLogItem, ScanSession, ScanHistory,
    DeviceTransferLog, PatientTransferLog, DeviceHandoverLog, DeviceAccessory, DeviceAccessoryUsageLog,
    DeviceTransferRequest, DeviceCleaningLog, DeviceSterilizationLog, DeviceMaintenanceLog,
    OperationDefinition, OperationStep, OperationExecution
)

from .models import (
    ServiceRequest, WorkOrder, JobPlan, JobPlanStep, PreventiveMaintenanceSchedule,
    SLADefinition, Supplier, SparePart, SystemNotification, EmailLog,
    NotificationPreference, NotificationTemplate, NotificationQueue
)

@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'model', 'status', 'availability', 'department', 'qr_token']
    list_filter = ['status', 'availability', 'clean_status', 'sterilization_status', 'department']
    search_fields = ['name', 'model', 'serial_number', 'qr_token']
    readonly_fields = ['qr_code', 'qr_token', 'created_at']
    
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # Generate QR code if not exists
        if not obj.qr_code or not obj.qr_token:
            obj.generate_qr_code()
            obj.save(update_fields=['qr_code', 'qr_token'])

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

admin.site.register(DeviceCategory)
admin.site.register(DeviceSubCategory)
admin.site.register(Company)
admin.site.register(DeviceType)
admin.site.register(DeviceUsage)
admin.site.register(DeviceCleaningLog)
admin.site.register(DeviceSterilizationLog)
admin.site.register(DeviceMaintenanceLog)
admin.site.register(DeviceTransferRequest)

# CMMS Models
admin.site.register(ServiceRequest)
admin.site.register(WorkOrder)
admin.site.register(JobPlan)
admin.site.register(JobPlanStep)
admin.site.register(PreventiveMaintenanceSchedule)
admin.site.register(SLADefinition)

# Notification Models
admin.site.register(SystemNotification)
admin.site.register(EmailLog)
admin.site.register(NotificationPreference)
admin.site.register(NotificationTemplate)
admin.site.register(NotificationQueue)

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


