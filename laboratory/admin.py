from django.contrib import admin
from .models import (
    TestResult, TestGroup, Test, LabRequest, LabRequestItem,
    TestOrder, Sample
)

@admin.register(Test)
class TestAdmin(admin.ModelAdmin):
    list_display = ['__str__']
    search_fields = ['__str__']

@admin.register(TestGroup)
class TestGroupAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']
    filter_horizontal = ['tests']

@admin.register(LabRequest)
class LabRequestAdmin(admin.ModelAdmin):
    list_display = ['patient', 'requested_at', 'status']
    list_filter = ['status', 'requested_at']
    search_fields = ['patient__first_name', 'patient__last_name', 'patient__mrn']
    readonly_fields = ['requested_at']

@admin.register(LabRequestItem)
class LabRequestItemAdmin(admin.ModelAdmin):
    list_display = ['test', 'status']
    list_filter = ['status']
    search_fields = ['test__name']

@admin.register(TestResult)
class TestResultAdmin(admin.ModelAdmin):
    list_display = ['patient', 'test', 'status', 'verified_at']
    list_filter = ['status', 'verified_at']
    search_fields = ['patient__mrn']

@admin.register(TestOrder)
class TestOrderAdmin(admin.ModelAdmin):
    list_display = ['patient', 'tube_type', 'requested_at']
    list_filter = ['requested_at', 'tube_type']
    search_fields = ['patient__mrn', 'patient__first_name']

@admin.register(Sample)
class SampleAdmin(admin.ModelAdmin):
    list_display = ['test_order', 'token', 'tube_type', 'requested_at']
    list_filter = ['requested_at', 'tube_type']
    search_fields = ['test_order__patient__mrn', 'token']
