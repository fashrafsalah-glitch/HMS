from django.contrib import admin
from .models import (
    Device, DeviceCategory, DeviceSubCategory, Company, DeviceType, DeviceUsage,
    DeviceUsageLog, DeviceUsageLogItem, ScanSession, ScanHistory,
    DeviceCleaningLog, DeviceSterilizationLog, DeviceMaintenanceLog,
    DeviceTransferRequest
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

@admin.register(DeviceUsageLog)
class DeviceUsageLogAdmin(admin.ModelAdmin):
    list_display = ['session_id', 'user', 'patient', 'operation_type', 'created_at', 'is_completed']
    list_filter = ['operation_type', 'is_completed', 'created_at']
    search_fields = ['user__first_name', 'user__last_name', 'patient__first_name', 'patient__last_name']
    readonly_fields = ['session_id', 'created_at']

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