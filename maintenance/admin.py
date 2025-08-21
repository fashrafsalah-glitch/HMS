from django.contrib import admin
from .models import Device, DeviceCategory, DeviceSubCategory

admin.site.register(Device)
admin.site.register(DeviceCategory)
admin.site.register(DeviceSubCategory)

DeviceCategory.objects.all()
DeviceSubCategory.objects.all()