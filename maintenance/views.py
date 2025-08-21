from django.shortcuts import render, redirect
from .forms import CompanyForm, DeviceFormBasic, DeviceTransferForm, DeviceTypeForm, DeviceUsageForm
from .models import Company, Device, DeviceTransferRequest, DeviceType, DeviceUsage
from django.shortcuts import get_object_or_404
from .forms import DeviceFormBasic
from django.shortcuts import render, redirect
from .models import DeviceCategory, DeviceSubCategory
from .forms import DeviceCategoryForm, DeviceSubCategoryForm
from django.shortcuts import render
from .models import Device, DeviceCategory, DeviceSubCategory
from manager.models import Department, Room, Bed
from django.http import HttpResponseBadRequest, JsonResponse
from .models import DeviceSubCategory
from .models import Device, DeviceCategory, DeviceSubCategory
from manager.models import Department, Room
from django.views.decorators.http import require_GET
from maintenance.models import Device 
from django.utils.timezone import now
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from .models import DeviceTransferRequest
from django.utils import timezone
from django.contrib import messages
from django.http import JsonResponse
from django.http import JsonResponse
from django.template.loader import render_to_string
from manager.models import Patient  # افترضنا أن مرضى القسم في هذا الموديل
from .models import Device

from django.utils import timezone
from django.contrib.auth.decorators import login_required
from .models import DeviceCleaningLog, DeviceSterilizationLog, DeviceMaintenanceLog

@login_required
def clean_device(request, device_id):
    device = get_object_or_404(Device, id=device_id)
    device.clean_status = 'clean'
    device.last_cleaned_by = request.user
    device.last_cleaned_at = timezone.now()
    device.save()
        # إضافة سجل جديد
    DeviceCleaningLog.objects.create(device=device, last_cleaned_by=request.user)


    messages.success(request, f"✅ تم تنظيف الجهاز بواسطة {request.user.username}")
    return redirect('maintenance:device_detail', pk=device.id)

@login_required
def cleaning_history(request, device_id):
    device = get_object_or_404(Device, id=device_id)
    logs = device.cleaning_logs.all().order_by('-cleaned_at')
    return render(request, 'maintenance/cleaning_history.html', {'device': device, 'logs': logs})

@login_required
def sterilize_device(request, device_id):
    device = get_object_or_404(Device, id=device_id)
    device.sterilization_status = 'sterilized'
    device.last_sterilized_by = request.user
    device.last_sterilized_at = timezone.now()
    device.save()

    # إضافة سجل جديد
    DeviceSterilizationLog.objects.create(device=device, last_sterilized_by=request.user)
    messages.success(request, f"✅ تم تعقيم الجهاز بواسطة {request.user.username}")
    return redirect('maintenance:device_detail', pk=device.id)

@login_required
def sterilization_history(request, device_id):
    device = get_object_or_404(Device, id=device_id)
    logs = device.sterilization_logs.all().order_by('-sterilized_at')
    return render(request, 'maintenance/sterilization_history.html', {'device': device, 'logs': logs})

@login_required
def perform_maintenance(request, device_id):
    device = get_object_or_404(Device, id=device_id)
    device.status = 'working'
    device.last_maintained_by = request.user
    device.last_maintained_at = timezone.now()
    device.save()

    # إضافة سجل جديد
    DeviceMaintenanceLog.objects.create(device=device, last_maintained_by=request.user)
    messages.success(request, f"✅ تم صيانة الجهاز بواسطة {request.user.username}")
    return redirect('maintenance:device_detail', pk=device.id)

@login_required
def maintenance_history(request, device_id):
    device = get_object_or_404(Device, id=device_id)
    logs =  device.maintenance_logs.all().order_by('-maintained_at')
    return render(request, 'maintenance/maintenance_history.html', {'device': device, 'logs': logs})


def assign_device(request, device_id):
    device = get_object_or_404(Device, id=device_id)
    
    patients = Patient.objects.filter(admission__department=device.department).distinct()

    if request.method == 'POST':
        patient_id = request.POST.get('patient')

        if not patient_id:
            return HttpResponseBadRequest("لم يتم اختيار مريض.")

        try:
            patient = Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            return HttpResponseBadRequest("المريض المحدد غير موجود.")

        device.current_patient = patient
        device.status = 'in_use'
        device.save()
        return redirect('maintenance:device_list')

    return render(request, 'maintenance/assign_device.html', {'device': device, 'patients': patients})

def release_device(request, device_id):
    device = get_object_or_404(Device, id=device_id)
    device.current_patient = None
    device.status = 'needs_check'
    device.clean_status = 'needs_cleaning'
    device.sterilization_status = 'needs_sterilization'
    device.save()
    return redirect('maintenance:device_list')



@login_required
def approve_transfer(request, transfer_id):
    transfer = get_object_or_404(DeviceTransferRequest, id=transfer_id)

    if request.method == 'POST' and not transfer.is_approved:
        # تنفيذ النقل
        device = transfer.device
        device.department = transfer.to_department
        device.room = transfer.to_room
        device.save()

        transfer.is_approved = True
        transfer.approved_by = request.user
        transfer.approved_at = now()
        transfer.save()

    return redirect('maintenance:department_devices', department_id=transfer.to_department.id)

@require_GET
def load_rooms(request):
    department_id = request.GET.get('department_id')
    rooms = Room.objects.filter(department_id=department_id).values('id', 'name')
    return JsonResponse(list(rooms), safe=False)

def device_list(request):
    devices = Device.objects.all()

    # فلترة حسب التصنيف
    category_id = request.GET.get('category')
    if category_id:
        devices = devices.filter(category_id=category_id)

    # فلترة حسب التصنيف الفرعي
    subcategory_id = request.GET.get('subcategory')
    if subcategory_id:
        devices = devices.filter(subcategory_id=subcategory_id)

    # فلترة حسب القسم
    department_id = request.GET.get('department')
    if department_id:
        devices = devices.filter(department_id=department_id)

    # فلترة حسب الغرفة
    room_id = request.GET.get('room')
    if room_id:
        devices = devices.filter(room_id=room_id)

    categories = DeviceCategory.objects.all()
    subcategories = DeviceSubCategory.objects.all()
    departments = Department.objects.all()
    rooms = Room.objects.all()

    return render(request, 'maintenance/device_list.html', {
        'devices': devices,
        'categories': categories,
        'subcategories': subcategories,
        'departments': departments,
        'rooms': rooms,
    })

def load_subcategories(request):
    category_id = request.GET.get('category_id')
    subcategories = DeviceSubCategory.objects.filter(category_id=category_id).values('id', 'name')
    return JsonResponse(list(subcategories), safe=False)

def device_list(request):
    category_id = request.GET.get('category')
    subcategory_id = request.GET.get('subcategory')
    department_id = request.GET.get('department')
    room_id = request.GET.get('room')

    devices = Device.objects.all()

    if category_id:
        devices = devices.filter(category_id=category_id)
    if subcategory_id:
        devices = devices.filter(subcategory_id=subcategory_id)
    if department_id:
        devices = devices.filter(department_id=department_id)
    if room_id:
        devices = devices.filter(room_id=room_id)

    context = {
        'devices': devices,
        'categories': DeviceCategory.objects.all(),
        'subcategories': DeviceSubCategory.objects.all(),
        'departments': Department.objects.all(),
        'rooms': Room.objects.all(),
    }
    return render(request, 'maintenance/device_list.html', context)

def add_device_category(request):
    if request.method == 'POST':
        form = DeviceCategoryForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('maintenance:add_device')  # الرجوع إلى إضافة جهاز
    else:
        form = DeviceCategoryForm()
    return render(request, 'maintenance/device_category_form.html', {'form': form})


def add_device_subcategory(request):
    if request.method == 'POST':
        form = DeviceSubCategoryForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('maintenance:add_device')  # الرجوع إلى إضافة جهاز
    else:
        form = DeviceSubCategoryForm()
    return render(request, 'maintenance/device_subcategory_form.html', {'form': form})

def device_detail(request, pk):
    device = get_object_or_404(Device, pk=pk)
    return render(request, 'maintenance/device_detail.html', {'device': device})

def device_edit(request, pk):
    device = get_object_or_404(Device, pk=pk)
    if request.method == 'POST':
        form = DeviceFormBasic(request.POST, instance=device)
        if form.is_valid():
            form.save()
            return redirect('maintenance:device_list')
    else:
        form = DeviceFormBasic(instance=device)
    return render(request, 'maintenance/device_form.html', {'form': form})

def device_delete(request, pk):
    device = get_object_or_404(Device, pk=pk)
    if request.method == 'POST':
        device.delete()
        return redirect('maintenance:device_list')
    return render(request, 'maintenance/device_confirm_delete.html', {'device': device})

def transfer_device(request, device_id):
    device = get_object_or_404(Device, id=device_id)

    if request.method == 'POST':
        form = DeviceTransferForm(request.POST)
        if form.is_valid():
            transfer = DeviceTransferRequest.objects.create(
                device=device,
                from_department=device.department,
                to_department=form.cleaned_data['department'],
                from_room=device.room,
                to_room=form.cleaned_data['room'],
                requested_by=request.user  # تأكد أن المستخدم مسجل دخول
            )
            return redirect('maintenance:device_detail', pk=device.id)
    else:
        form = DeviceTransferForm(initial={
            'department': device.department,
            'room': device.room
        })

    return render(request, 'maintenance/device_transfer.html', {'form': form, 'device': device})



def approve_transfer(request, transfer_id):
    transfer = get_object_or_404(DeviceTransferRequest, id=transfer_id)

    if request.method == 'POST':
        transfer.is_approved = True
        transfer.approved_by = request.user
        transfer.approved_at = timezone.now()  # تسجيل وقت القبول
        transfer.save()

        device = transfer.device
        device.department = transfer.to_department
        device.room = transfer.to_room
        device.save()

        messages.success(request, "تم قبول نقل الجهاز بنجاح.")
        return redirect('maintenance:department_devices', department_id=transfer.to_department.id)
    
    return redirect('maintenance:device_detail', pk=transfer.device.id)

def index(request):
    return render(request, 'maintenance/index.html')



def add_device(request):
    if request.method == 'POST':
        form = DeviceFormBasic(request.POST)
        if form.is_valid():
            form.save()
            return redirect('maintenance:device_list')
        else:
            print("Form Errors:", form.errors)  # ← اطبع الأخطاء هنا
    else:
        form = DeviceFormBasic()
    return render(request, 'maintenance/add_device.html', {'form': form})





def device_info(request, pk):
    device = get_object_or_404(Device, pk=pk)
    return render(request, 'maintenance/device_info.html', {'device': device})

def add_accessory(request, pk):
    return render(request, 'maintenance/add_accessory.html', {'device_id': pk})

def maintenance_schedule(request, pk):
    return render(request, 'maintenance/maintenance_schedule.html', {'device_id': pk})

def add_emergency_request(request, pk):
    return render(request, 'maintenance/add_emergency_request.html', {'device_id': pk})

def add_spare_part(request, pk):
    return render(request, 'maintenance/add_spare_part.html', {'device_id': pk})





def department_devices(request, department_id):
    department = get_object_or_404(Department, id=department_id)

    # استبعاد الأجهزة التي تم طلب نقلها لهذا القسم ولم تُقبل بعد
    pending_transfers = DeviceTransferRequest.objects.filter(
        to_department=department,
        is_approved=False
    ).select_related('device')

    pending_devices_ids = [t.device.id for t in pending_transfers]

    # عرض الأجهزة الفعلية فقط التي لا تنتظر موافقة النقل
    actual_devices = Device.objects.filter(
        department=department
    ).exclude(id__in=pending_devices_ids)

    return render(request, 'maintenance/department_device_list.html', {
        'department': department,
        'actual_devices': actual_devices,
        'pending_transfers': pending_transfers
    })

from .models import DeviceTransferRequest

def device_transfer_history(request, device_id):
    device = get_object_or_404(Device, id=device_id)
    transfers = DeviceTransferRequest.objects.filter(device=device).select_related(
        'from_department', 'to_department', 'from_room', 'to_room', 'requested_by', 'approved_by'
    ).order_by('-requested_at')

    return render(request, 'maintenance/device_transfer_history.html', {
        'device': device,
        'transfers': transfers
    })


def get_rooms(request):
    department_id = request.GET.get('department_id')
    rooms = Room.objects.filter(department_id=department_id).order_by('name')
    html = render_to_string('partials/room_dropdown.html', {'rooms': rooms})
    return JsonResponse({'html': html})

def get_beds(request):
    room_id = request.GET.get('room_id')
    beds = Bed.objects.filter(room_id=room_id).order_by('name')
    html = render_to_string('partials/bed_dropdown.html', {'beds': beds})
    return JsonResponse({'html': html})


def add_company(request):
    form = CompanyForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect('device_list')
    return render(request, 'maintenance/add_company.html', {'form': form})

def add_device_type(request):
    form = DeviceTypeForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect('device_list')
    return render(request, 'maintenance/add_device_type.html', {'form': form})

def add_device_usage(request):
    form = DeviceUsageForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect('device_list')
    return render(request, 'maintenance/add_device_usage.html', {'form': form})


# تعديل شركة
def edit_company(request, pk):
    company = get_object_or_404(Company, pk=pk)
    if request.method == 'POST':
        form = CompanyForm(request.POST, instance=company)
        if form.is_valid():
            form.save()
            return redirect('company_list')
    else:
        form = CompanyForm(instance=company)
    return render(request, 'maintenance/edit_company.html', {'form': form})

# حذف شركة
def delete_company(request, pk):
    company = get_object_or_404(Company, pk=pk)
    if request.method == 'POST':
        company.delete()
        return redirect('company_list')
    return render(request, 'maintenance/confirm_delete.html', {'object': company, 'type': 'Company'})

# تعديل نوع الجهاز
def edit_device_type(request, pk):
    dtype = get_object_or_404(DeviceType, pk=pk)
    if request.method == 'POST':
        form = DeviceTypeForm(request.POST, instance=dtype)
        if form.is_valid():
            form.save()
            return redirect('device_type_list')
    else:
        form = DeviceTypeForm(instance=dtype)
    return render(request, 'maintenance/edit_device_type.html', {'form': form})

# حذف نوع الجهاز
def delete_device_type(request, pk):
    dtype = get_object_or_404(DeviceType, pk=pk)
    if request.method == 'POST':
        dtype.delete()
        return redirect('device_type_list')
    return render(request, 'maintenance/confirm_delete.html', {'object': dtype, 'type': 'Device Type'})

# تعديل استخدام الجهاز
def edit_device_usage(request, pk):
    usage = get_object_or_404(DeviceUsage, pk=pk)
    if request.method == 'POST':
        form = DeviceUsageForm(request.POST, instance=usage)
        if form.is_valid():
            form.save()
            return redirect('device_usage_list')
    else:
        form = DeviceUsageForm(instance=usage)
    return render(request, 'maintenance/edit_device_usage.html', {'form': form})

# حذف استخدام الجهاز
def delete_device_usage(request, pk):
    usage = get_object_or_404(DeviceUsage, pk=pk)
    if request.method == 'POST':
        usage.delete()
        return redirect('device_usage_list')
    return render(request, 'maintenance/confirm_delete.html', {'object': usage, 'type': 'Device Usage'})