from django.contrib import admin

# Register your models here.
from manager.models import  Department
from maintenance.models import Device
dep = Department.objects.get(id=5)
Device.objects.filter(department=dep)  # يجب أن يُرجع فقط الأجهزة المرتبطة بهذا القسم