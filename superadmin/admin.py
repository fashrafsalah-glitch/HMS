from django.contrib import admin
from .models import Hospital, SystemSettings

@admin.register(Hospital)
class HospitalAdmin(admin.ModelAdmin):
    list_display = ['name', 'hospital_type', 'location', 'address']
    list_filter = ['hospital_type']
    search_fields = ['name', 'location', 'address']

@admin.register(SystemSettings)
class SystemSettingsAdmin(admin.ModelAdmin):
    list_display = ['system_name', 'country', 'default_attendance_method']
    search_fields = ['system_name', 'country']
