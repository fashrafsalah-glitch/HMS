from django.contrib import admin
from .models import ActivityLog, OperationPrice

@admin.register(OperationPrice)
class OperationPriceAdmin(admin.ModelAdmin):
    list_display = ("operation_key", "amount")
    search_fields = ("operation_key",)

@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "user", "operation_key", "amount", "object_repr")
    list_filter = ("operation_key", "action", "timestamp")
    search_fields = ("object_repr", "extra")
    autocomplete_fields = ("user",)
