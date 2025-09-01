from django.contrib import admin
from django.utils.html import format_html

# Register your models here.
from manager.models import Department
from maintenance.models import Device
from .models import (
    Bed, Patient, Room, Doctor, Building, Floor, Ward,
    RadiologyOrder, MedicalRecord, Admission, Transfer,
    Clinic, Appointment, Visit, EmergencyDepartment,
    SurgicalOperationsDepartment, Diagnosis, BacteriologyResult,
    Program, Form, Laboratory, TestOrder, Sample
)

@admin.register(Bed)
class BedAdmin(admin.ModelAdmin):
    list_display = ['bed_number', 'room', 'bed_type', 'status', 'has_qr_code']
    list_filter = ['bed_type', 'status', 'room__department', 'room__ward']
    search_fields = ['bed_number', 'room__number', 'room__department__name']
    readonly_fields = ['qr_code', 'qr_token']
    actions = ['clear_old_qr_codes', 'regenerate_qr_codes']
    
    def has_qr_code(self, obj):
        return bool(obj.qr_code)
    has_qr_code.boolean = True
    has_qr_code.short_description = 'QR Code'
    
    @admin.action(description='مسح جميع رموز QR القديمة (Clear all old QR codes)')
    def clear_old_qr_codes(self, request, queryset):
        updated_count = 0
        for bed in queryset:
            if bed.qr_code:
                bed.qr_code.delete(save=False)
            bed.qr_token = None
            bed.save(update_fields=['qr_code', 'qr_token'])
            updated_count += 1
        
        self.message_user(
            request,
            f'تم مسح رموز QR من {updated_count} سرير بنجاح (Cleared QR codes from {updated_count} beds)'
        )
    
    @admin.action(description='إعادة توليد رموز QR آمنة (Regenerate secure QR codes)')
    def regenerate_qr_codes(self, request, queryset):
        updated_count = 0
        for bed in queryset:
            if bed.qr_code:
                bed.qr_code.delete(save=False)
            bed.generate_qr_code()
            bed.save(update_fields=['qr_code', 'qr_token'])
            updated_count += 1
        
        self.message_user(
            request,
            f'تم إعادة توليد رموز QR آمنة لـ {updated_count} سرير (Regenerated secure QR codes for {updated_count} beds)'
        )

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ['mrn', 'first_name', 'last_name', 'gender', 'phone_number', 'has_qr_code']
    list_filter = ['gender']
    search_fields = ['mrn', 'first_name', 'last_name', 'phone_number', 'national_id']
    readonly_fields = ['qr_code', 'qr_token', 'age']
    actions = ['clear_old_qr_codes', 'regenerate_qr_codes']
    
    def has_qr_code(self, obj):
        return bool(obj.qr_code)
    has_qr_code.boolean = True
    has_qr_code.short_description = 'QR Code'
    
    @admin.action(description='مسح جميع رموز QR القديمة (Clear all old QR codes)')
    def clear_old_qr_codes(self, request, queryset):
        updated_count = 0
        for patient in queryset:
            if patient.qr_code:
                patient.qr_code.delete(save=False)
            patient.qr_token = None
            patient.save(update_fields=['qr_code', 'qr_token'])
            updated_count += 1
        
        self.message_user(
            request,
            f'تم مسح رموز QR من {updated_count} مريض بنجاح (Cleared QR codes from {updated_count} patients)'
        )
    
    @admin.action(description='إعادة توليد رموز QR آمنة (Regenerate secure QR codes)')
    def regenerate_qr_codes(self, request, queryset):
        updated_count = 0
        for patient in queryset:
            if patient.qr_code:
                patient.qr_code.delete(save=False)
            patient.generate_qr_code()
            patient.save(update_fields=['qr_code', 'qr_token'])
            updated_count += 1
        
        self.message_user(
            request,
            f'تم إعادة توليد رموز QR آمنة لـ {updated_count} مريض (Regenerated secure QR codes for {updated_count} patients)'
        )

@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ['number', 'room_type', 'department', 'ward', 'status', 'capacity', 'has_qr_code']
    list_filter = ['room_type', 'status', 'department', 'ward']
    search_fields = ['number', 'department__name', 'ward__name']
    readonly_fields = ['qr_code', 'qr_token']
    actions = ['clear_old_qr_codes', 'regenerate_qr_codes', 'update_room_status']
    
    def has_qr_code(self, obj):
        return bool(obj.qr_code)
    has_qr_code.boolean = True
    has_qr_code.short_description = 'QR Code'
    
    @admin.action(description='مسح جميع رموز QR القديمة (Clear all old QR codes)')
    def clear_old_qr_codes(self, request, queryset):
        updated_count = 0
        for room in queryset:
            if room.qr_code:
                room.qr_code.delete(save=False)
            room.qr_token = None
            room.save(update_fields=['qr_code', 'qr_token'])
            updated_count += 1
        
        self.message_user(
            request,
            f'تم مسح رموز QR من {updated_count} غرفة بنجاح (Cleared QR codes from {updated_count} rooms)'
        )
    
    @admin.action(description='إعادة توليد رموز QR آمنة (Regenerate secure QR codes)')
    def regenerate_qr_codes(self, request, queryset):
        updated_count = 0
        for room in queryset:
            if room.qr_code:
                room.qr_code.delete(save=False)
            room.generate_qr_code()
            room.save(update_fields=['qr_code', 'qr_token'])
            updated_count += 1
        
        self.message_user(
            request,
            f'تم إعادة توليد رموز QR آمنة لـ {updated_count} غرفة (Regenerated secure QR codes for {updated_count} rooms)'
        )
    
    @admin.action(description='تحديث حالة الغرف (Update room status)')
    def update_room_status(self, request, queryset):
        # This will be used to bulk update room status
        pass

# Infrastructure Models
@admin.register(Building)
class BuildingAdmin(admin.ModelAdmin):
    list_display = ['name', 'hospital', 'location']
    list_filter = ['hospital']
    search_fields = ['name', 'location']

@admin.register(Floor)
class FloorAdmin(admin.ModelAdmin):
    list_display = ['name', 'building', 'floor_number']
    list_filter = ['building']
    search_fields = ['name', 'building__name']

@admin.register(Ward)
class WardAdmin(admin.ModelAdmin):
    list_display = ['name', 'floor', 'description']
    list_filter = ['floor__building']
    search_fields = ['name', 'floor__name']

@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ['user', 'departments_list']
    list_filter = ['departments']
    search_fields = ['user__first_name', 'user__last_name']
    filter_horizontal = ['departments']
    
    def departments_list(self, obj):
        return ", ".join([dept.name for dept in obj.departments.all()])
    departments_list.short_description = 'Departments'

@admin.register(Admission)
class AdmissionAdmin(admin.ModelAdmin):
    list_display = ['patient', 'admission_date', 'admission_type', 'department', 'bed', 'discharge_date']
    list_filter = ['admission_type', 'department']
    search_fields = ['patient__first_name', 'patient__last_name', 'patient__mrn']
    readonly_fields = ['admission_date']

@admin.register(Visit)
class VisitAdmin(admin.ModelAdmin):
    list_display = ['patient', 'visit_date', 'visit_type', 'department', 'doctor']
    list_filter = ['visit_type', 'visit_date', 'department']
    search_fields = ['patient__mrn', 'patient__first_name', 'patient__last_name']

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ['patient', 'doctor', 'date_time', 'status', 'appointment_type']
    list_filter = ['status', 'appointment_type']
    search_fields = ['patient__first_name', 'patient__last_name', 'doctor__user__first_name']

@admin.register(Diagnosis)
class DiagnosisAdmin(admin.ModelAdmin):
    list_display = ['patient', 'visit', 'doctor', 'icd_code', 'name']
    list_filter = ['visit__visit_date', 'doctor']
    search_fields = ['patient__mrn', 'icd_code', 'name', 'description']

@admin.register(MedicalRecord)
class MedicalRecordAdmin(admin.ModelAdmin):
    list_display = ['patient', 'complaint', 'created_at']
    list_filter = ['created_at']
    search_fields = ['patient__mrn', 'patient__first_name', 'complaint']
    readonly_fields = ['created_at']

@admin.register(Transfer)
class TransferAdmin(admin.ModelAdmin):
    list_display = ['admission', 'transfer_type', 'from_department', 'to_department', 'transfer_date']
    list_filter = ['transfer_type', 'transfer_date']
    search_fields = ['admission__patient__mrn']

@admin.register(Clinic)
class ClinicAdmin(admin.ModelAdmin):
    list_display = ['name', 'clinic_type', 'department', 'doctor']
    list_filter = ['clinic_type', 'department']
    search_fields = ['name', 'department__name', 'doctor__user__username']

@admin.register(EmergencyDepartment)
class EmergencyDepartmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'hospital', 'emergency_type', 'status', 'capacity']
    list_filter = ['status', 'emergency_type', 'hospital']
    search_fields = ['name', 'description']

@admin.register(SurgicalOperationsDepartment)
class SurgicalOperationsDepartmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'department', 'doctor', 'status']
    list_filter = ['status', 'department']
    search_fields = ['name', 'doctor__user__first_name', 'doctor__user__last_name']

# Register remaining models with basic admin
admin.site.register(RadiologyOrder)
admin.site.register(BacteriologyResult)
admin.site.register(Program)
admin.site.register(Form)
admin.site.register(Laboratory)
admin.site.register(TestOrder)
admin.site.register(Sample)