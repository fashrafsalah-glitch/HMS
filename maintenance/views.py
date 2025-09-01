from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods, require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q, Count, Sum, Avg, F, Value, CharField
from django.db.models.functions import Concat
from django.utils import timezone
from django.utils.translation import gettext as _
from django.core.paginator import Paginator
from django.urls import reverse
from datetime import datetime, timedelta
import json
import uuid
from decimal import Decimal
from .forms import OperationDefinitionForm
import json
from .forms import CompanyForm, DeviceFormBasic, DeviceTransferForm, DeviceTypeForm, DeviceUsageForm, DeviceAccessoryForm, DeviceCategoryForm, DeviceSubCategoryForm
from .forms_cmms import ServiceRequestForm
from .models import (Company, Device, DeviceTransferRequest, DeviceType, DeviceUsage, 
                     DeviceCleaningLog, DeviceSterilizationLog, DeviceMaintenanceLog, 
                     DeviceCategory, DeviceSubCategory, PreventiveMaintenanceSchedule, 
                     WorkOrder, JobPlan, OperationDefinition, OperationStep, 
                     OperationExecution, ScanSession, DeviceUsageLog, DeviceTransferLog)
from manager.models import Department, Room, Bed, Patient

from .models import DeviceAccessory, AccessoryTransaction
from .forms import AccessoryScanForm

@login_required
def maintenance_dashboard_qr(request):
    """
    Dashboard view for maintenance module with statistics and quick actions
    """
    # Get date range for statistics (last 30 days)
    end_date = timezone.now()
    start_date = end_date - timedelta(days=30)
    
    # Statistics
    stats = {
        # Operations
        'total_operations': OperationDefinition.objects.filter(is_active=True).count(),
        'recent_executions': OperationExecution.objects.filter(
            started_at__gte=start_date
        ).count(),
        'pending_executions': OperationExecution.objects.filter(
            status='pending'
        ).count(),
        'completed_executions': OperationExecution.objects.filter(
            status='completed',
            started_at__gte=start_date
        ).count(),
        
        # Devices
        'total_devices': Device.objects.filter(availability=True).count(),
        'devices_in_use': Device.objects.filter(status='in_use').count(),
        'devices_need_maintenance': Device.objects.filter(status='needs_maintenance').count(),
        'devices_need_cleaning': Device.objects.filter(clean_status='needs_cleaning').count(),
        
        # Sessions
        'active_sessions': ScanSession.objects.filter(status='active').count(),
        'today_sessions': ScanSession.objects.filter(
            created_at__date=timezone.now().date()
        ).count(),
        
        # Logs (last 30 days)
        'usage_logs': DeviceUsageLog.objects.filter(
            started_at__gte=start_date
        ).count(),
        'transfer_logs': DeviceTransferLog.objects.filter(
            moved_at__gte=start_date
        ).count(),
        'cleaning_logs': DeviceCleaningLog.objects.filter(
            cleaned_at__gte=start_date
        ).count(),
        'maintenance_logs': DeviceMaintenanceLog.objects.filter(
            maintained_at__gte=start_date
        ).count(),
    }
    
    # Recent executions
    recent_executions = OperationExecution.objects.select_related(
        'operation', 'executed_by', 'session'
    ).order_by('-started_at')[:10]
    
    # Pending operations
    pending_operations = OperationExecution.objects.filter(
        status='pending'
    ).select_related('operation', 'executed_by').order_by('-started_at')[:5]
    
    # Active sessions
    active_sessions = ScanSession.objects.filter(
        status='active'
    ).select_related('user').order_by('-created_at')[:5]
    
    # Devices needing attention
    devices_need_attention = Device.objects.filter(
        Q(status='needs_maintenance') | 
        Q(clean_status='needs_cleaning') |
        Q(sterilization_status='needs_sterilization')
    )[:10]
    
    context = {
        'stats': stats,
        'recent_executions': recent_executions,
        'pending_operations': pending_operations,
        'active_sessions': active_sessions,
        'devices_need_attention': devices_need_attention,
        'current_time': timezone.now(),
    }
    
    return render(request, 'maintenance/dashboard.html', context)

@login_required
def operations_list(request):
    """
    List all operation definitions with CRUD actions
    """
    operations = OperationDefinition.objects.all().order_by('name')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        operations = operations.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(code__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(operations, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
    }
    return render(request, 'maintenance/operations_list.html', context)

@login_required
def operation_create(request):
    """إنشاء عملية جديدة"""
    if request.method == 'POST':
        form = OperationDefinitionForm(request.POST)
        if form.is_valid():
            operation = form.save()
            messages.success(request, f'تم إنشاء العملية "{operation.name}" بنجاح')
            return redirect('maintenance:operation_detail', operation.id)
        else:
            messages.error(request, 'يرجى تصحيح الأخطاء أدناه')
    else:
        form = OperationDefinitionForm()
    
    return render(request, 'maintenance/operation_form.html', {
        'form': form,
        'action': 'create'
    })

@login_required
def operation_edit(request, pk):
    """تعديل تعريف عملية موجودة"""
    operation = get_object_or_404(OperationDefinition, pk=pk)
    
    if request.method == 'POST':
        form = OperationDefinitionForm(request.POST, instance=operation)
        if form.is_valid():
            operation = form.save()
            messages.success(request, f'تم تحديث العملية "{operation.name_en}" بنجاح')
            return redirect('maintenance:operation_detail', operation.id)
        else:
            messages.error(request, 'يرجى تصحيح الأخطاء أدناه')
    else:
        form = OperationDefinitionForm(instance=operation)
    
    return render(request, 'maintenance/operation_form.html', {
        'form': form,
        'operation': operation,
        'action': 'edit'
    })

@login_required
def operation_delete(request, pk):
    """
    Delete an operation definition
    """
    operation = get_object_or_404(OperationDefinition, pk=pk)
    
    if request.method == 'POST':
        operation_name = operation.name_en
        operation.delete()
        messages.success(request, f'Operation "{operation_name}" deleted successfully!')
        return redirect('maintenance:operations_list')
    
    return render(request, 'maintenance/operation_confirm_delete.html', {'operation': operation})

@login_required
def operation_detail(request, pk):
    """
    View operation details including steps
    """
    operation = get_object_or_404(OperationDefinition, pk=pk)
    steps = operation.steps.all().order_by('order')
    executions = operation.executions.all().order_by('-started_at')[:10]
    
    context = {
        'operation': operation,
        'steps': steps,
        'recent_executions': executions,
    }
    return render(request, 'maintenance/operation_detail.html', context)

@login_required
def sessions_list(request):
    """
    List all scan sessions
    """
    sessions = ScanSession.objects.all().select_related('user').order_by('-created_at')
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter:
        sessions = sessions.filter(status=status_filter)
    
    # Filter by date
    date_filter = request.GET.get('date', '')
    if date_filter:
        try:
            filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
            sessions = sessions.filter(created_at__date=filter_date)
        except ValueError:
            pass
    
    # Pagination
    paginator = Paginator(sessions, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'date_filter': date_filter,
    }
    return render(request, 'maintenance/sessions_list.html', context)

@login_required
def session_detail(request, pk):
    """
    View session details including all scans and executions
    """
    session = get_object_or_404(ScanSession, pk=pk)
    executions = session.operation_executions.all().order_by('started_at')
    
    context = {
        'session': session,
        'executions': executions,
    }
    return render(request, 'maintenance/session_detail.html', context)

@login_required
def executions_list(request):
    """
    List all operation executions
    """
    executions = OperationExecution.objects.all().select_related(
        'operation', 'executed_by', 'session'
    ).order_by('-started_at')
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter:
        executions = executions.filter(status=status_filter)
    
    # Filter by operation
    operation_filter = request.GET.get('operation', '')
    if operation_filter:
        executions = executions.filter(operation_id=operation_filter)
    
    # Pagination
    paginator = Paginator(executions, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get operations for filter dropdown
    operations = OperationDefinition.objects.filter(is_active=True)
    
    context = {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'operation_filter': operation_filter,
        'operations': operations,
    }
    return render(request, 'maintenance/executions_list.html', context)

@login_required
def execution_detail(request, pk):
    """
    View execution details
    """
    execution = get_object_or_404(OperationExecution, pk=pk)
    
    context = {
        'execution': execution,
    }
    return render(request, 'maintenance/execution_detail.html', context)

@login_required
def clean_device(request, device_id):
    device = get_object_or_404(Device, id=device_id)
    device.clean_status = 'clean'
    device.last_cleaned_by = request.user
    device.last_cleaned_at = timezone.now()
    device.save()
        # إضافة سجل جديد
    DeviceCleaningLog.objects.create(device=device, cleaned_by=request.user)


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
    DeviceSterilizationLog.objects.create(device=device, sterilized_by=request.user)
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
    DeviceMaintenanceLog.objects.create(device=device, maintained_by=request.user)
    messages.success(request, f"✅ تم صيانة الجهاز بواسطة {request.user.username}")
    return redirect('maintenance:device_detail', pk=device.id)

@login_required
def maintenance_history(request, device_id):
    device = get_object_or_404(Device, id=device_id)
    logs =  device.maintenance_logs.all().order_by('-maintained_at')
    return render(request, 'maintenance/maintenance_history.html', {'device': device, 'logs': logs})

# AJAX Views for instant device status updates
@login_required
@require_POST
def ajax_clean_device(request, device_id):
    """AJAX endpoint for instant device cleaning"""
    try:
        device = get_object_or_404(Device, id=device_id)
        device.clean_status = 'clean'
        device.last_cleaned_by = request.user
        device.last_cleaned_at = timezone.now()
        device.save()
        
        # Add cleaning log
        DeviceCleaningLog.objects.create(device=device, cleaned_by=request.user)
        
        return JsonResponse({
            'success': True,
            'message': f'✅ تم تنظيف الجهاز بواسطة {request.user.username}',
            'clean_status': device.get_clean_status_display(),
            'clean_status_class': 'success',
            'last_cleaned_at': device.last_cleaned_at.strftime('%Y-%m-%d %H:%M'),
            'last_cleaned_by': str(device.last_cleaned_by)
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'خطأ في تنظيف الجهاز: {str(e)}'
        })

@login_required
@require_POST
def ajax_sterilize_device(request, device_id):
    """AJAX endpoint for instant device sterilization"""
    try:
        device = get_object_or_404(Device, id=device_id)
        device.sterilization_status = 'sterilized'
        device.last_sterilized_by = request.user
        device.last_sterilized_at = timezone.now()
        device.save()
        
        # Add sterilization log
        DeviceSterilizationLog.objects.create(device=device, sterilized_by=request.user)
        
        return JsonResponse({
            'success': True,
            'message': f'✅ تم تعقيم الجهاز بواسطة {request.user.username}',
            'sterilization_status': device.get_sterilization_status_display(),
            'sterilization_status_class': 'success',
            'last_sterilized_at': device.last_sterilized_at.strftime('%Y-%m-%d %H:%M'),
            'last_sterilized_by': str(device.last_sterilized_by)
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'خطأ في تعقيم الجهاز: {str(e)}'
        })

@login_required
@require_POST
def ajax_perform_maintenance(request, device_id):
    """AJAX endpoint for instant device maintenance"""
    try:
        device = get_object_or_404(Device, id=device_id)
        device.status = 'working'
        device.last_maintained_by = request.user
        device.last_maintained_at = timezone.now()
        device.save()
        
        # Add maintenance log
        DeviceMaintenanceLog.objects.create(device=device, maintained_by=request.user)
        
        return JsonResponse({
            'success': True,
            'message': f'✅ تم فحص الجهاز بواسطة {request.user.username}',
            'status': device.get_status_display(),
            'status_class': 'success',
            'last_maintained_at': device.last_maintained_at.strftime('%Y-%m-%d %H:%M'),
            'last_maintained_by': str(device.last_maintained_by)
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'خطأ في فحص الجهاز: {str(e)}'
        })

def assign_device(request, device_id):
    device = get_object_or_404(Device, id=device_id)
    
    # Get patients from the same department as the device
    if device.department:
        # Filter patients by device's department through their current admission
        patients = Patient.objects.filter(
            admission__department=device.department,
            admission__discharge_date__isnull=True  # Only active admissions
        ).order_by('first_name', 'last_name').distinct()
    else:
        # If device has no department, show all patients
        patients = Patient.objects.all().order_by('first_name', 'last_name')

    if request.method == 'POST':
        patient_id = request.POST.get('patient')

        if not patient_id:
            messages.error(request, "لم يتم اختيار مريض.")
            return render(request, 'maintenance/assign_device.html', {'device': device, 'patients': patients})

        try:
            patient = Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            messages.error(request, "المريض المحدد غير موجود.")
            return render(request, 'maintenance/assign_device.html', {'device': device, 'patients': patients})

        device.current_patient = patient
        device.status = 'in_use'
        device.save()
        messages.success(request, f'تم ربط الجهاز "{device.name}" بالمريض "{patient.first_name} {patient.last_name}" بنجاح.')
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
        try:
            # تنفيذ النقل
            device = transfer.device
            old_dept = device.department
            old_room = device.room
            
            device.department = transfer.to_department
            device.room = transfer.to_room
            device.save()

            transfer.is_approved = True
            transfer.approved_by = request.user
            transfer.approved_at = timezone.now()
            transfer.save()
            
            messages.success(request, f'تم الموافقة على نقل الجهاز {device.name} من {old_dept} غرفة {old_room} إلى {transfer.to_department.name} غرفة {transfer.to_room.number}')
        except Exception as e:
            messages.error(request, f'حدث خطأ أثناء الموافقة على النقل: {str(e)}')
    elif transfer.is_approved:
        messages.info(request, 'تم الموافقة على هذا الطلب مسبقاً')

    return redirect('maintenance:device_transfer_list')

@require_GET
def load_rooms(request):
    department_id = request.GET.get('department_id')
    rooms = Room.objects.filter(department_id=department_id).values('id', 'number')
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

# تم دمج هذه الوظيفة مع الوظيفة السابقة
# def device_list(request):
#    category_id = request.GET.get('category')
#    subcategory_id = request.GET.get('subcategory')
#    department_id = request.GET.get('department')
#    room_id = request.GET.get('room')
#
#    devices = Device.objects.all()

# تم تعليق الكود المتبقي من الوظيفة المكررة
#    if category_id:
#        devices = devices.filter(category_id=category_id)
#    if subcategory_id:
#        devices = devices.filter(subcategory_id=subcategory_id)
#    if department_id:
#        devices = devices.filter(department_id=department_id)
#    if room_id:
#        devices = devices.filter(room_id=room_id)

# تم تعليق الكود المتبقي من الوظيفة المكررة
#    context = {
#        'devices': devices,
#        'categories': DeviceCategory.objects.all(),
#        'subcategories': DeviceSubCategory.objects.all(),
#        'departments': Department.objects.all(),
#        'rooms': Room.objects.all(),
#    }
#    return render(request, 'maintenance/device_list.html', context)

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
    # Keep device detail page focused on device info only
    context = {
        'device': device,
    }
    return render(request, 'maintenance/device_detail.html', context)

@login_required
def redirect_to_accessories(request, pk):
    """Redirect old add-accessory URL to device detail page with accessories tab"""
    return redirect('maintenance:device_accessories', device_id=pk)

def device_edit(request, pk):
    device = get_object_or_404(Device, pk=pk)
    if request.method == 'POST':
        form = DeviceFormBasic(request.POST, instance=device)
        if form.is_valid():
            form.save()
            return redirect('maintenance:device_list')
    else:
        form = DeviceFormBasic(instance=device)
    return render(request, 'maintenance/device_form.html', {'form': form, 'device': device})

def device_delete(request, pk):
    device = get_object_or_404(Device, pk=pk)
    if request.method == 'POST':
        device.delete()
        return redirect('maintenance:device_list')
    return render(request, 'maintenance/device_confirm_delete.html', {'device': device})


# ============= Enhanced Device Transfer Views (3-Stage Workflow) =============

@login_required
def transfer_request_create(request, device_id):
    """Create a new device transfer request"""
    from .forms import DeviceTransferRequestForm
    
    device = get_object_or_404(Device, id=device_id)
    
    # Check device eligibility automatically
    temp_request = DeviceTransferRequest(device=device)
    eligibility_errors = temp_request.check_device_eligibility()
    
    if request.method == 'POST':
        form = DeviceTransferRequestForm(request.POST, device=device, user=request.user)
        if form.is_valid():
            transfer_request = form.save(commit=False)
            transfer_request.device = device
            transfer_request.from_department = device.department
            transfer_request.from_room = device.room
            transfer_request.requested_by = request.user
            transfer_request.save()
            
            messages.success(request, 'تم إرسال طلب النقل بنجاح - رقم الطلب: ' + str(transfer_request.pk))
            return redirect('maintenance:transfer_success', pk=transfer_request.pk)
        else:
            # Display specific form errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{form.fields[field].label}: {error}')
            messages.error(request, 'يرجى تصحيح الأخطاء في النموذج')
    else:
        form = DeviceTransferRequestForm(device=device, user=request.user)
    
    context = {
        'form': form, 
        'device': device,
        'eligibility_errors': eligibility_errors,
        'device_ready': len(eligibility_errors) == 0
    }
    return render(request, 'maintenance/transfer_request_form.html', context)


@login_required
def transfer_success(request, pk):
    """Show transfer request success page with monitoring info"""
    transfer_request = get_object_or_404(DeviceTransferRequest, pk=pk)
    
    context = {
        'transfer_request': transfer_request,
    }
    return render(request, 'maintenance/transfer_success.html', context)

# AJAX endpoints for dynamic form loading
@login_required
def get_department_rooms(request):
    """Get rooms for a specific department"""
    department_id = request.GET.get('department_id')
    if department_id:
        try:
            from manager.models import Room
            rooms = Room.objects.filter(department_id=department_id)
            
            # Format room names for display
            room_list = []
            for room in rooms:
                room_name = f"غرفة {room.number} - {room.get_room_type_display()}"
                room_list.append({'id': room.id, 'name': room_name})
            
            return JsonResponse({'rooms': room_list})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'rooms': []})


@login_required
def get_room_beds(request):
    """Get beds for a specific room"""
    room_id = request.GET.get('room_id')
    if room_id:
        try:
            from manager.models import Bed
            beds = Bed.objects.filter(room_id=room_id, status='available')
            
            # Format bed names for display
            bed_list = []
            for bed in beds:
                bed_name = f"سرير {bed.bed_number} - {bed.get_bed_type_display()}"
                bed_list.append({'id': bed.id, 'name': bed_name})
            
            return JsonResponse({'beds': bed_list})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'beds': []})


@login_required
def get_department_patients(request):
    """Get patients for a specific department"""
    department_id = request.GET.get('department_id')
    if department_id:
        try:
            from manager.models import Patient
            patients = Patient.objects.filter(
                admission__department_id=department_id,
                admission__discharge_date__isnull=True
            ).values('id', 'first_name', 'last_name')
            
            # Format patient names for display
            patient_list = []
            for patient in patients:
                full_name = f"{patient['first_name']} {patient['last_name']}"
                patient_list.append({'id': patient['id'], 'name': full_name})
            
            return JsonResponse({'patients': patient_list})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'patients': []})


@login_required
def transfer_request_detail(request, pk):
    """View transfer request details"""
    transfer_request = get_object_or_404(DeviceTransferRequest, pk=pk)
    
    context = {
        'transfer_request': transfer_request,
        'can_approve': transfer_request.can_approve(request.user),
        'can_accept': transfer_request.can_accept(request.user),
    }
    
    return render(request, 'maintenance/transfer_request_detail.html', context)


@login_required
def transfer_requests_list(request):
    """List all transfer requests with filters"""
    # Get filter parameters
    status_filter = request.GET.get('status', '')
    department_filter = request.GET.get('department', '')
    priority_filter = request.GET.get('priority', '')
    
    # Base queryset
    queryset = DeviceTransferRequest.objects.select_related(
        'device', 'from_department', 'to_department', 
        'requested_by', 'approved_by', 'accepted_by'
    ).order_by('-requested_at')
    
    # Apply filters
    if status_filter:
        queryset = queryset.filter(status=status_filter)
    if department_filter:
        queryset = queryset.filter(
            Q(from_department_id=department_filter) | 
            Q(to_department_id=department_filter)
        )
    if priority_filter:
        queryset = queryset.filter(priority=priority_filter)
    
    # Separate by status for tabs
    pending_requests = queryset.filter(status='pending')
    approved_requests = queryset.filter(status='approved')
    completed_requests = queryset.filter(status='accepted')
    rejected_requests = queryset.filter(status='rejected')
    
    # Pagination
    paginator = Paginator(queryset, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'pending_requests': pending_requests[:10],
        'approved_requests': approved_requests[:10],
        'completed_requests': completed_requests[:10],
        'rejected_requests': rejected_requests[:10],
        'departments': Department.objects.all(),
        'status_filter': status_filter,
        'department_filter': department_filter,
        'priority_filter': priority_filter,
    }
    
    return render(request, 'maintenance/transfer_requests_list.html', context)


@login_required
def approve_transfer_request(request, pk):
    """Approve a transfer request (Stage 2)"""
    from .forms import TransferApprovalForm
    
    transfer_request = get_object_or_404(DeviceTransferRequest, pk=pk)
    
    if not transfer_request.can_approve(request.user):
        messages.error(request, "ليس لديك صلاحية الموافقة على هذا الطلب")
        return redirect('maintenance:transfer_request_detail', pk=pk)
    
    if request.method == 'POST':
        form = TransferApprovalForm(request.POST)
        if form.is_valid():
            # Check device eligibility
            eligibility_errors = transfer_request.check_device_eligibility()
            if eligibility_errors:
                for error in eligibility_errors:
                    messages.error(request, error)
                return redirect('maintenance:transfer_request_detail', pk=pk)
            
            # Approve the request
            transfer_request.approve(
                user=request.user,
                notes=form.cleaned_data.get('approval_notes', '')
            )
            
            messages.success(request, "تمت الموافقة على طلب النقل بنجاح")
            return redirect('maintenance:transfer_request_detail', pk=pk)
    else:
        form = TransferApprovalForm()
    
    return render(request, 'maintenance/transfer_approval_form.html', {
        'form': form,
        'transfer_request': transfer_request
    })


@login_required
def accept_transfer_request(request, pk):
    """Accept a transfer request and execute it (Stage 3)"""
    from .forms import TransferAcceptanceForm
    
    transfer_request = get_object_or_404(DeviceTransferRequest, pk=pk)
    
    if not transfer_request.can_accept(request.user):
        messages.error(request, "ليس لديك صلاحية قبول هذا الطلب")
        return redirect('maintenance:transfer_request_detail', pk=pk)
    
    if request.method == 'POST':
        form = TransferAcceptanceForm(request.POST)
        if form.is_valid():
            # Final eligibility check
            eligibility_errors = transfer_request.check_device_eligibility()
            if eligibility_errors:
                for error in eligibility_errors:
                    messages.error(request, error)
                return redirect('maintenance:transfer_request_detail', pk=pk)
            
            # Accept and execute transfer
            transfer_request.accept(
                user=request.user,
                notes=form.cleaned_data.get('acceptance_notes', '')
            )
            
            messages.success(request, "تم قبول النقل وتحديث موقع الجهاز بنجاح")
            return redirect('maintenance:device_detail', pk=transfer_request.device.id)
    else:
        form = TransferAcceptanceForm()
    
    return render(request, 'maintenance/transfer_acceptance_form.html', {
        'form': form,
        'transfer_request': transfer_request
    })


@login_required
def reject_transfer_request(request, pk):
    """Reject a transfer request"""
    from .forms import TransferRejectionForm
    
    transfer_request = get_object_or_404(DeviceTransferRequest, pk=pk)
    
    # Check permissions (can reject if can approve or accept)
    if not (transfer_request.can_approve(request.user) or transfer_request.can_accept(request.user)):
        messages.error(request, "ليس لديك صلاحية رفض هذا الطلب")
        return redirect('maintenance:transfer_request_detail', pk=pk)
    
    if request.method == 'POST':
        form = TransferRejectionForm(request.POST)
        if form.is_valid():
            transfer_request.reject(
                user=request.user,
                reason=form.cleaned_data['rejection_reason']
            )
            
            messages.success(request, "تم رفض طلب النقل")
            return redirect('maintenance:transfer_requests_list')
    else:
        form = TransferRejectionForm()
    
    return render(request, 'maintenance/transfer_rejection_form.html', {
        'form': form,
        'transfer_request': transfer_request
    })


# Keep the old approve_transfer for backward compatibility
def approve_transfer(request, transfer_id):
    """Legacy approve transfer - redirect to new system"""
    return redirect('maintenance:approve_transfer_request', pk=transfer_id)

def index(request):
    # إحصائيات صيانة الأجهزة
    total_devices = Device.objects.count()
    working_devices = Device.objects.filter(status='working').count()
    needs_maintenance = Device.objects.filter(status='needs_maintenance').count()
    out_of_order = Device.objects.filter(status='out_of_order').count()
    needs_cleaning = Device.objects.filter(clean_status='needs_cleaning').count()
    needs_sterilization = Device.objects.filter(sterilization_status='needs_sterilization').count()
    
    # إحصائيات الصيانة العامة (CMMS)
    try:
        from .models import WorkOrder, ServiceRequest
        total_work_orders = WorkOrder.objects.count()
        pending_work_orders = WorkOrder.objects.filter(status='pending').count()
        total_service_requests = ServiceRequest.objects.count()
        pending_service_requests = ServiceRequest.objects.filter(status='pending').count()
    except ImportError:
        total_work_orders = 0
        pending_work_orders = 0
        total_service_requests = 0
        pending_service_requests = 0
    
    # الأجهزة الأكثر استخداماً
    popular_devices = Device.objects.filter(current_patient__isnull=False)[:5]
    
    # آخر عمليات الصيانة
    recent_maintenance = DeviceMaintenanceLog.objects.select_related('device', 'maintained_by').order_by('-maintained_at')[:5]
    
    context = {
        # إحصائيات الأجهزة
        'total_devices': total_devices,
        'working_devices': working_devices,
        'needs_maintenance': needs_maintenance,
        'out_of_order': out_of_order,
        'needs_cleaning': needs_cleaning,
        'needs_sterilization': needs_sterilization,
        
        # إحصائيات CMMS
        'total_work_orders': total_work_orders,
        'pending_work_orders': pending_work_orders,
        'total_service_requests': total_service_requests,
        'pending_service_requests': pending_service_requests,
        
        # بيانات إضافية
        'popular_devices': popular_devices,
        'recent_maintenance': recent_maintenance,
    }
    
    return render(request, 'maintenance/index.html', context)



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
    
    # Add context for patients filtering by department
    context = {
        'form': form,
    }
    return render(request, 'maintenance/add_device.html', context)





def device_info(request, pk):
    device = get_object_or_404(Device, pk=pk)
    return render(request, 'maintenance/device_info.html', {'device': device})

def add_accessory(request, pk):
    device = get_object_or_404(Device, pk=pk)
    
    if request.method == 'POST':
        form = DeviceAccessoryForm(request.POST)
        if form.is_valid():
            accessory = form.save(commit=False)
            accessory.device = device
            accessory.save()
            messages.success(request, f'تم إضافة الملحق "{accessory.name}" بنجاح للجهاز {device.name}')
            return redirect('maintenance:device_info', pk=device.id)
        else:
            messages.error(request, 'يرجى تصحيح الأخطاء في النموذج')
    else:
        form = DeviceAccessoryForm()
    
    return render(request, 'maintenance/add_accessory.html', {
        'device': device,
        'form': form
    })

def maintenance_schedule(request, device_id):
    device = get_object_or_404(Device, pk=device_id)
    
    # جلب الصيانات المجدولة للجهاز
    scheduled_maintenances = PreventiveMaintenanceSchedule.objects.filter(device=device)
    
    # جلب سجل الصيانة من DeviceMaintenanceLog
    maintenance_logs = DeviceMaintenanceLog.objects.filter(device=device).order_by('-maintained_at')[:10]
    
    # جلب أوامر العمل المرتبطة بالجهاز
    work_orders = WorkOrder.objects.filter(service_request__device=device).order_by('-created_at')[:5]
    
    if request.method == 'POST':
        from .forms import PreventiveMaintenanceScheduleForm
        form = PreventiveMaintenanceScheduleForm(request.POST, device=device)
        
        if form.is_valid():
            # إنشاء جدولة صيانة جديدة
            schedule = form.save(commit=False)
            schedule.device = device
            schedule.created_by = request.user
            
            # إذا لم يتم تحديد خطة عمل، أنشئ واحدة افتراضية
            if not schedule.job_plan:
                maintenance_type = request.POST.get('maintenance_type', 'صيانة عامة')
                job_plan, created = JobPlan.objects.get_or_create(
                    name=f"خطة صيانة {maintenance_type} - {device.name}",
                    defaults={
                        'description': f"خطة صيانة {maintenance_type} افتراضية للجهاز {device.name}",
                        'estimated_duration': 60,  # 60 دقيقة افتراضي
                        'created_by': request.user,
                        'is_active': True
                    }
                )
                schedule.job_plan = job_plan
            
            schedule.save()
            messages.success(request, f'تم جدولة الصيانة "{schedule.name}" للجهاز {device.name} بنجاح')
            return redirect('maintenance:maintenance_schedule', device_id=device_id)
        else:
            # عرض أخطاء النموذج
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{form.fields[field].label}: {error}')
    else:
        from .forms import PreventiveMaintenanceScheduleForm
        form = PreventiveMaintenanceScheduleForm(device=device)
    
    return render(request, 'maintenance/maintenance_schedule.html', {
        'device': device,
        'device_id': device_id,
        'scheduled_maintenances': scheduled_maintenances,
        'maintenance_logs': maintenance_logs,
        'work_orders': work_orders,
        'form': form
    })

@login_required
def edit_schedule(request, device_id):
    device = get_object_or_404(Device, pk=device_id)
    
    if request.method == 'POST':
        schedule_id = request.POST.get('schedule_id')
        schedule_type = request.POST.get('schedule_type')
        next_maintenance = request.POST.get('next_maintenance')
        
        try:
            schedule = get_object_or_404(PreventiveMaintenanceSchedule, id=schedule_id, device=device)
            
            from datetime import datetime
            next_date = datetime.strptime(next_maintenance, '%Y-%m-%d').date()
            
            schedule.frequency = schedule_type
            schedule.next_due_date = next_date
            schedule.save()
            
            messages.success(request, 'تم تحديث الصيانة المجدولة بنجاح')
        except ValueError:
            messages.error(request, 'تاريخ غير صحيح')
        except Exception as e:
            messages.error(request, 'حدث خطأ أثناء التحديث')
        return redirect('maintenance:maintenance_schedule', device_id=device_id)

@login_required
def delete_schedule(request, device_id):
    device = get_object_or_404(Device, pk=device_id)
    
    if request.method == 'POST':
        schedule_id = request.POST.get('schedule_id')
        
        try:
            schedule = get_object_or_404(PreventiveMaintenanceSchedule, id=schedule_id, device=device)
            schedule_name = schedule.job_plan.name
            schedule.delete()
            
            messages.success(request, f'تم حذف الصيانة المجدولة "{schedule_name}" بنجاح')
        except Exception as e:
            messages.error(request, 'حدث خطأ أثناء الحذف')
    
    return redirect('maintenance:maintenance_schedule', device_id=device_id)

# Device Operations Views
def clean_device(request, device_id):
    device = get_object_or_404(Device, pk=device_id)
    
    if request.method == 'POST':
        notes = request.POST.get('notes', '')
        DeviceCleaningLog.objects.create(
            device=device,
            cleaned_by=request.user,
            notes=notes
        )
        messages.success(request, f'تم تسجيل تنظيف الجهاز "{device.name}" بنجاح')
        return redirect('maintenance:device_info', pk=device.id)
    
    return render(request, 'maintenance/clean_device.html', {'device': device})

def sterilize_device(request, device_id):
    device = get_object_or_404(Device, pk=device_id)
    
    if request.method == 'POST':
        notes = request.POST.get('notes', '')
        method = request.POST.get('method', '')
        DeviceSterilizationLog.objects.create(
            device=device,
            sterilized_by=request.user,
            notes=notes,
            method=method
        )
        messages.success(request, f'تم تسجيل تعقيم الجهاز "{device.name}" بنجاح')
        return redirect('maintenance:device_info', pk=device.id)
    
    return render(request, 'maintenance/sterilize_device.html', {'device': device})

def perform_maintenance(request, device_id):
    device = get_object_or_404(Device, id=device_id)
    
    if request.method == 'POST':
        notes = request.POST.get('notes', '')
        maintenance_type = request.POST.get('maintenance_type', '')
        DeviceMaintenanceLog.objects.create(
            device=device,
            maintained_by=request.user,
            description=notes,
            maintenance_type=maintenance_type
        )
        
        # Update device status to working after maintenance
        device.status = 'working'
        device.last_maintained_by = request.user
        device.last_maintained_at = timezone.now()
        device.save()
        
        messages.success(request, f'تم تسجيل صيانة الجهاز "{device.name}" بنجاح وتم تغيير الحالة إلى "يعمل"')
        return redirect('maintenance:device_detail', pk=device.id)
    
    return render(request, 'maintenance/perform_maintenance.html', {'device': device})

# History Views
def cleaning_history(request, device_id):
    device = get_object_or_404(Device, pk=device_id)
    cleaning_logs = DeviceCleaningLog.objects.filter(device=device).order_by('-cleaned_at')
    return render(request, 'maintenance/cleaning_history.html', {
        'device': device,
        'cleaning_logs': cleaning_logs
    })

def sterilization_history(request, device_id):
    device = get_object_or_404(Device, pk=device_id)
    sterilization_logs = DeviceSterilizationLog.objects.filter(device=device).order_by('-sterilized_at')
    return render(request, 'maintenance/sterilization_history.html', {
        'device': device,
        'sterilization_logs': sterilization_logs
    })

def maintenance_history(request, device_id):
    device = get_object_or_404(Device, pk=device_id)
    maintenance_logs = DeviceMaintenanceLog.objects.filter(device=device).order_by('-maintained_at')
    return render(request, 'maintenance/maintenance_history.html', {
        'device': device,
        'maintenance_logs': maintenance_logs
    })

def add_emergency_request(request, pk):
    device = get_object_or_404(Device, pk=pk)
    
    if request.method == 'POST':
        form = ServiceRequestForm(request.POST, user=request.user)
        if form.is_valid():
            service_request = form.save(commit=False)
            service_request.device = device
            service_request.reporter = request.user
            service_request.request_type = 'emergency'
            # لا نحدد severity و priority هنا، بل نتركهم للمستخدم
            # التأكد من وجود العنوان
            if not service_request.title:
                service_request.title = f'طلب صيانة مستعجلة - {device.name}'
            service_request.save()
            
            messages.success(request, f'تم إنشاء طلب الصيانة المستعجلة للجهاز {device.name} بنجاح')
            return redirect('maintenance:device_detail', pk=device.pk)
        else:
            messages.error(request, 'يرجى تصحيح الأخطاء في النموذج')
    else:
        # تعبئة البيانات الافتراضية للجهاز
        initial_data = {
            'device': device,
            'title': f'طلب صيانة مستعجلة - {device.name}',
            'request_type': 'emergency',
            'severity': 'high',  # قيمة افتراضية
            'impact': 'significant',  # قيمة افتراضية
            'priority': 'high'  # قيمة افتراضية
        }
        form = ServiceRequestForm(initial=initial_data, user=request.user)
        # جعل حقل الجهاز للقراءة فقط
        form.fields['device'].widget.attrs['readonly'] = True
        form.fields['device'].widget.attrs['disabled'] = True
        
        # إضافة خصائص للحقول لحساب SLA
        form.fields['severity'].required = True
        form.fields['impact'].required = True
        form.fields['priority'].required = True
    
    context = {
        'device': device,
        'form': form,
        'title': f'طلب صيانة مستعجلة - {device.name}'
    }
    return render(request, 'maintenance/add_emergency_request.html', context)

def add_spare_part(request, pk):
    return render(request, 'maintenance/add_spare_part.html', {'device_id': pk})

@require_POST
@csrf_exempt
def ajax_calculate_sla_times(request):
    """حساب أوقات SLA بناءً على الخطورة والتأثير والأولوية"""
    try:
        data = json.loads(request.body)
        device_id = data.get('device_id')
        severity = data.get('severity')
        impact = data.get('impact')
        priority = data.get('priority')
        
        if not all([device_id, severity, impact, priority]):
            return JsonResponse({
                'success': False,
                'error': 'جميع الحقول مطلوبة'
            })
        
        # الحصول على الجهاز
        device = get_object_or_404(Device, pk=device_id)
        
        # البحث عن SLA Matrix المناسب
        try:
            from .models import SLAMatrix
            sla_matrix = SLAMatrix.objects.filter(
                device_category=device.category,
                severity=severity,
                impact=impact,
                priority=priority,
                is_active=True
            ).first()
            
            if sla_matrix:
                return JsonResponse({
                    'success': True,
                    'response_time': sla_matrix.response_time_hours,
                    'resolution_time': sla_matrix.resolution_time_hours,
                    'sla_name': sla_matrix.sla_definition.name,
                    'sla_id': sla_matrix.id
                })
            else:
                # حساب أوقات افتراضية إذا لم توجد مصفوفة SLA
                # معاملات الخطورة (كلما ارتفعت الخطورة، قل الوقت المسموح)
                severity_multipliers = {
                    'low': 2.0,      # منخفض - وقت أكثر
                    'medium': 1.0,   # متوسط - وقت عادي
                    'high': 0.5,     # عالي - وقت أقل
                    'critical': 0.25 # حرج - وقت أقل بكثير
                }
                
                # معاملات التأثير (كلما ارتفع التأثير، قل الوقت المسموح)
                impact_multipliers = {
                    'minimal': 2.0,    # طفيف - وقت أكثر
                    'moderate': 1.0,   # متوسط - وقت عادي
                    'significant': 0.5, # كبير - وقت أقل
                    'extensive': 0.25  # واسع - وقت أقل بكثير
                }
                
                # معاملات الأولوية (كلما ارتفعت الأولوية، قل الوقت المسموح)
                priority_multipliers = {
                    'low': 2.0,      # منخفض - وقت أكثر
                    'medium': 1.0,   # متوسط - وقت عادي
                    'high': 0.5,     # عالي - وقت أقل
                    'critical': 0.25 # حرج - وقت أقل بكثير
                }
                
                # حساب المعاملات
                severity_factor = severity_multipliers.get(severity, 1.0)
                impact_factor = impact_multipliers.get(impact, 1.0)
                priority_factor = priority_multipliers.get(priority, 1.0)
                
                # أوقات افتراضية للطوارئ (قيم أساسية أعلى)
                base_response = 12  # 12 ساعة
                base_resolution = 36  # 36 ساعة
                
                # المعامل النهائي (متوسط الثلاثة عوامل)
                final_multiplier = (severity_factor + impact_factor + priority_factor) / 3
                
                response_time = max(1, int(base_response * final_multiplier))
                resolution_time = max(2, int(base_resolution * final_multiplier))
                
                return JsonResponse({
                    'success': True,
                    'response_time': response_time,
                    'resolution_time': resolution_time,
                    'sla_name': 'حساب افتراضي',
                    'sla_id': None
                })
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'خطأ في حساب أوقات SLA: {str(e)}'
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'خطأ في معالجة الطلب: {str(e)}'
        })




# This function is duplicated in manager/views.py - removing to avoid conflicts
# The manager/views.py version is more complete and is the one being used

from .models import DeviceTransferRequest

def device_transfer_history(request, device_id):
    device = get_object_or_404(Device, id=device_id)
    
    # Get all transfer requests
    transfer_requests = DeviceTransferRequest.objects.filter(device=device).select_related(
        'from_department', 'to_department', 'from_room', 'to_room', 'requested_by', 'approved_by', 'accepted_by'
    ).order_by('-requested_at')
    
    # Get all transfer logs (completed transfers)
    from .models import DeviceTransferLog
    transfer_logs = DeviceTransferLog.objects.filter(device=device).select_related(
        'from_department', 'to_department', 'from_room', 'to_room', 'moved_by'
    ).order_by('-moved_at')
    
    # Combine and sort all transfer activities
    all_transfers = []
    
    # Add transfer requests
    for req in transfer_requests:
        all_transfers.append({
            'type': 'request',
            'id': req.id,
            'status': req.status,
            'from_department': req.from_department,
            'to_department': req.to_department,
            'from_room': req.from_room,
            'to_room': req.to_room,
            'date': req.requested_at,
            'user': req.requested_by,
            'reason': req.reason,
            'priority': req.priority,
            'approved_by': req.approved_by,
            'accepted_by': req.accepted_by,
            'approved_at': req.approved_at,
            'accepted_at': req.accepted_at,
        })
    
    # Add transfer logs
    for log in transfer_logs:
        all_transfers.append({
            'type': 'log',
            'id': log.id,
            'status': 'completed',
            'from_department': log.from_department,
            'to_department': log.to_department,
            'from_room': log.from_room,
            'to_room': log.to_room,
            'date': log.moved_at,
            'user': log.moved_by,
            'reason': getattr(log, 'reason', 'نقل مكتمل'),
        })
    
    # Sort by date (newest first)
    all_transfers.sort(key=lambda x: x['date'], reverse=True)

    return render(request, 'maintenance/device_transfer_history.html', {
        'device': device,
        'transfers': all_transfers,
        'transfer_requests': transfer_requests,
        'transfer_logs': transfer_logs
    })


def get_rooms(request):
    from django.template.loader import render_to_string
    department_id = request.GET.get('department_id')
    if department_id:
        try:
            rooms = Room.objects.filter(department_id=department_id).order_by('number')
            html = render_to_string('maintenance/partials/room_dropdown.html', {'rooms': rooms})
            return JsonResponse({'html': html})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    else:
        rooms = Room.objects.none()
        html = render_to_string('maintenance/partials/room_dropdown.html', {'rooms': rooms})
        return JsonResponse({'html': html})

def get_beds(request):
    from django.template.loader import render_to_string
    room_id = request.GET.get('room_id')
    if room_id:
        try:
            beds = Bed.objects.filter(room_id=room_id).order_by('bed_number')
            html = render_to_string('maintenance/partials/bed_dropdown.html', {'beds': beds})
            return JsonResponse({'html': html})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    else:
        beds = Bed.objects.none()
        html = render_to_string('maintenance/partials/bed_dropdown.html', {'beds': beds})
        return JsonResponse({'html': html})

def get_patients_by_department(request):
    department_id = request.GET.get('department_id')
    if department_id:
        # Get patients from the same department through their current admission
        patients = Patient.objects.filter(
            admission__department_id=department_id,
            admission__discharge_date__isnull=True  # Only active admissions
        ).order_by('first_name', 'last_name').distinct()
    else:
        patients = Patient.objects.none()
    
    # Generate HTML options for the select dropdown
    options_html = '<option value="">---------</option>'
    for patient in patients:
        options_html += f'<option value="{patient.id}">{patient.first_name} {patient.last_name} (MRN: {patient.mrn})</option>'
    
    return JsonResponse({'html': options_html})


def add_company(request):
    form = CompanyForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect('maintenance:device_list')
    return render(request, 'maintenance/add_company.html', {'form': form})

def add_device_type(request):
    form = DeviceTypeForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect('maintenance:device_list')
    return render(request, 'maintenance/add_device_type.html', {'form': form})

def add_device_usage(request):
    form = DeviceUsageForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect('maintenance:maintenance_index')
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


# ═══════════════════════════════════════════════════════════════════════════
# QR/BARCODE SCANNING SYSTEM
# ═══════════════════════════════════════════════════════════════════════════

import json
from django.apps import apps
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from .models import (
    ScanSession, ScanHistory, DeviceDailyUsageLog, DeviceUsageLogItem,
    DeviceTransferLog, PatientTransferLog, DeviceHandoverLog, DeviceAccessory, DeviceAccessoryUsageLog
)
from django.contrib.auth import get_user_model

User = get_user_model()

def log_qr_scan(qr_code, entity_type, entity_id, entity_data, user=None, device_type='unknown', scanner_id=None, request=None, is_secure=False, is_ephemeral=False, session_id=None, flow_name=None, flow_executed=False):
    """
    Log QR scan to database for tracking and analytics with secure token support
    """
    from .models import QRScanLog
    
    # Get IP address
    ip_address = None
    if request:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(',')[0]
        else:
            ip_address = request.META.get('REMOTE_ADDR')
    
    # Get user agent
    user_agent = request.META.get('HTTP_USER_AGENT', '') if request else ''
    
    # Extract signature from QR code if present
    token_signature = None
    if '|sig=' in qr_code:
        token_signature = qr_code.split('|sig=')[-1]
    
    # Create log entry
    scan_log = QRScanLog.objects.create(
        qr_code=qr_code,
        entity_type=entity_type,
        entity_id=entity_id,
        entity_data=entity_data,
        scanned_by=user,
        device_type=device_type,
        scanner_id=scanner_id,
        ip_address=ip_address,
        user_agent=user_agent,
        token_signature=token_signature,
        is_secure=is_secure,
        is_ephemeral=is_ephemeral,
        session_id=session_id,
        flow_name=flow_name,
        flow_executed=flow_executed,
        scanned_at=timezone.now()
    )
    
    return scan_log


def get_entity_detail_url(entity_type, entity_id):
    """
    Get detail page URL for different entity types
    """
    try:
        if entity_type == 'device':
            return reverse('maintenance:device_detail', kwargs={'pk': entity_id})
        elif entity_type == 'patient':
            return reverse('manager:patient_detail', kwargs={'pk': entity_id})
        elif entity_type == 'bed':
            return reverse('manager:bed_detail', kwargs={'pk': entity_id})
        elif entity_type == 'user' or entity_type == 'customuser':
            return reverse('hr:user_detail', kwargs={'pk': entity_id})
        elif entity_type == 'accessory' or entity_type == 'deviceaccessory':
            return reverse('maintenance:accessory_detail', kwargs={'pk': entity_id})
        else:
            return None
    except:
        return None


def parse_qr_code(raw_value):
    """
    Parse QR code and return entity type, ID, entity data, and error
    يدعم استخراج التوكن من URL كامل أو نص خام
    
    Supports formats:
    - Full URL: https://hms.my-domain.com/api/scan-qr/?token=device:uuid|sig=signature
    - Secure token: entity_type:uuid|sig=signature (e.g., device:uuid|sig=abc123)
    - Ephemeral token: entity_type:uuid|eph=1|sig=signature
    - Legacy standard: entity_type:id (e.g., device:123, patient:456)
    - Legacy patient extended: patient:id|MRN:mrn|Name:first_last|DOB:yyyy-mm-dd
    - Operation token: op:operation_type (e.g., op:usage, op:transfer)
    - Lab sample: sample:uuid (e.g., sample:abc123)
    """
    from django.apps import apps
    from core.secure_qr import SecureQRToken
    from urllib.parse import urlparse, parse_qs
    
    if not raw_value or not raw_value.strip():
        return None, None, None, "QR code is empty"
    
    # Extract token from URL or use raw value
    if raw_value.startswith("http"):
        try:
            parsed = urlparse(raw_value)
            query = parse_qs(parsed.query)
            qr_code = query.get("token", [None])[0]
            
            if not qr_code:
                return None, None, None, "No token parameter found in URL"
        except Exception as e:
            return None, None, None, f"Error parsing URL: {str(e)}"
    else:
        qr_code = raw_value
    
    try:
        # Check if it's a secure token with signature
        if '|sig=' in qr_code:
            # Parse secure token
            token_result = SecureQRToken.parse_token(qr_code)
            
            if not token_result['valid']:
                return None, None, None, token_result.get('error', 'Invalid token')
            
            entity_type = token_result['entity_type']
            entity_id = token_result['entity_id']
            ephemeral = token_result.get('ephemeral', False)
            metadata = token_result.get('metadata', {})
            
            # Map entity types to models
            model_mapping = {
                'device': ('maintenance', 'Device'),
                'patient': ('manager', 'Patient'),
                'bed': ('manager', 'Bed'),
                'room': ('manager', 'Room'),
                'user': ('hr', 'CustomUser'),
                'customuser': ('hr', 'CustomUser'),
                'accessory': ('maintenance', 'DeviceAccessory'),
                'deviceaccessory': ('maintenance', 'DeviceAccessory'),
                'department': ('manager', 'Department'),
                'doctor': ('manager', 'Doctor'),
            }
            
            if entity_type not in model_mapping:
                return None, None, None, f"Unknown entity type: {entity_type}"
            
            app_label, model_name = model_mapping[entity_type]
            model_class = apps.get_model(app_label, model_name)
            
            try:
                entity = model_class.objects.get(pk=entity_id)
                
                # Prepare entity data
                entity_data = {
                    'id': entity.pk,
                    'name': str(entity),
                    'type': entity_type,
                    'ephemeral': ephemeral,
                    'token_uuid': token_result.get('token_uuid'),
                    'metadata': metadata
                }
                
                # Add specific fields based on entity type
                if entity_type == 'device':
                    entity_data.update({
                        'status': entity.status,
                        'availability': entity.availability,
                        'clean_status': entity.clean_status,
                        'sterilization_status': entity.sterilization_status,
                        'department': str(entity.department) if entity.department else None,
                        'room': str(entity.room) if entity.room else None,
                    })
                elif entity_type == 'patient':
                    entity_data.update({
                        'full_name': f"{entity.first_name} {entity.last_name}",
                        'mrn': entity.mrn,
                        'age': entity.age if hasattr(entity, 'age') else None,
                        'gender': getattr(entity, 'gender', None),
                        'date_of_birth': entity.date_of_birth.strftime('%Y-%m-%d') if entity.date_of_birth else None,
                    })
                elif entity_type in ['bed']:
                    entity_data.update({
                        'status': entity.status,
                        'department': str(entity.department) if entity.department else None,
                        'room': str(entity.room) if entity.room else None,
                    })
                elif entity_type == 'room':
                    entity_data.update({
                        'status': entity.status,
                        'room_type': entity.get_room_type_display(),
                        'department': str(entity.department) if entity.department else None,
                        'ward': str(entity.ward) if entity.ward else None,
                        'capacity': entity.capacity,
                        'number': entity.number,
                    })
                elif entity_type in ['user', 'customuser']:
                    entity_data.update({
                        'username': entity.username,
                        'full_name': entity.get_full_name() if hasattr(entity, 'get_full_name') else str(entity),
                        'role': getattr(entity, 'role', None),
                        'department': str(entity.department) if hasattr(entity, 'department') and entity.department else None,
                    })
                elif entity_type in ['accessory', 'deviceaccessory']:
                    entity_data.update({
                        'device': str(entity.device) if entity.device else None,
                        'status': getattr(entity, 'status', None),
                    })
                
                return entity_type, entity_id, entity_data, None
                
            except model_class.DoesNotExist:
                return None, None, None, f"{entity_type.title()} with ID {entity_id} not found"
        
        # Legacy format handling below...
        # Check if it's a lab sample
        if qr_code.startswith('sample:'):
            sample_id = qr_code.split(':', 1)[1]
            lab_sample_model = apps.get_model('laboratory', 'Sample')
            
            try:
                sample = lab_sample_model.objects.get(id=sample_id)
                entity_data = {
                    'id': str(sample.id),
                    'type': 'sample',
                    'name': f"Sample {sample.sample_id}",
                    'patient': str(sample.patient) if sample.patient else None,
                    'test_name': sample.test_name if hasattr(sample, 'test_name') else None,
                    'status': sample.status if hasattr(sample, 'status') else None,
                    'collected_at': sample.collected_at.isoformat() if hasattr(sample, 'collected_at') and sample.collected_at else None
                }
                return 'sample', sample_id, entity_data, None
            except lab_sample_model.DoesNotExist:
                return None, None, None, f"Sample with ID {sample_id} not found"
        
        # Check if it's an operation token
        if qr_code.startswith('op:'):
            operation_type = qr_code.split(':', 1)[1]
            valid_operations = ['usage', 'transfer', 'handover', 'patient_transfer', 'clean', 'sterilize', 'inspect', 'maintenance']
            
            if operation_type in valid_operations:
                entity_data = {
                    'type': 'operation_token',
                    'operation': operation_type,
                    'name': f"Operation: {operation_type.title()}",
                    'description': f"Operation token for {operation_type}"
                }
                return 'operation_token', operation_type, entity_data, None
            else:
                return None, None, None, f"Unknown operation type: {operation_type}"
        
        # Check if it's a patient with extended format (legacy)
        if qr_code.startswith('patient:') and '|' in qr_code and '|sig=' not in qr_code:
            # Parse patient extended format: patient:id|MRN:mrn|Name:first_last|DOB:yyyy-mm-dd
            parts = qr_code.split('|')
            if len(parts) >= 4:
                try:
                    entity_type, entity_id = parts[0].split(':', 1)
                    entity_id = int(entity_id)
                    
                    # Extract additional patient data
                    mrn = parts[1].split(':', 1)[1] if len(parts[1].split(':', 1)) > 1 else ''
                    name = parts[2].split(':', 1)[1] if len(parts[2].split(':', 1)) > 1 else ''
                    dob = parts[3].split(':', 1)[1] if len(parts[3].split(':', 1)) > 1 else ''
                    
                    # Get patient from database
                    patient_model = apps.get_model('manager', 'Patient')
                    try:
                        entity = patient_model.objects.get(pk=entity_id)
                        
                        entity_data = {
                            'id': entity.pk,
                            'type': 'patient',
                            'name': str(entity),
                            'full_name': f"{entity.first_name} {entity.last_name}",
                            'mrn': entity.mrn,
                            'age': entity.age if hasattr(entity, 'age') else None,
                            'gender': getattr(entity, 'gender', None),
                            'date_of_birth': entity.date_of_birth.strftime('%Y-%m-%d') if entity.date_of_birth else dob,
                            'extra': {
                                'MRN': mrn,
                                'Name': name.replace('_', ' '),
                                'DOB': dob
                            }
                        }
                        
                        return 'patient', entity_id, entity_data, None
                        
                    except patient_model.DoesNotExist:
                        return None, None, None, f"Patient with ID {entity_id} not found"
                        
                except (ValueError, IndexError):
                    return None, None, None, "Invalid patient QR code format"
        
        # Standard format parsing (legacy)
        if ':' in qr_code and '|' not in qr_code:
            entity_type, entity_id = qr_code.split(':', 1)
            entity_id = int(entity_id)
        
        # Map entity types to models
        model_mapping = {
            'device': ('maintenance', 'Device'),
            'patient': ('manager', 'Patient'),
            'bed': ('manager', 'Bed'),
            'user': ('hr', 'CustomUser'),
            'customuser': ('hr', 'CustomUser'),
            'accessory': ('maintenance', 'DeviceAccessory'),
            'deviceaccessory': ('maintenance', 'DeviceAccessory'),
            'department': ('manager', 'Department'),
            'doctor': ('manager', 'Doctor'),
        }
        
        if entity_type not in model_mapping:
            return None, None, None, f"Unknown entity type: {entity_type}"
        
        app_label, model_name = model_mapping[entity_type]
        model_class = apps.get_model(app_label, model_name)
        
        try:
            entity = model_class.objects.get(pk=entity_id)
            
            # Prepare entity data
            entity_data = {
                'id': entity.pk,
                'name': str(entity),
                'type': entity_type,
            }
            
            # Add specific fields based on entity type
            if entity_type == 'device':
                entity_data.update({
                    'status': entity.status,
                    'availability': entity.availability,
                    'clean_status': entity.clean_status,
                    'sterilization_status': entity.sterilization_status,
                    'department': str(entity.department) if entity.department else None,
                    'room': str(entity.room) if entity.room else None,
                    'bed': str(entity.bed) if entity.bed else None,
                    'current_patient': str(entity.current_patient) if entity.current_patient else None,
                })
            elif entity_type == 'patient':
                entity_data.update({
                    'full_name': f"{entity.first_name} {entity.last_name}",
                    'mrn': getattr(entity, 'mrn', ''),
                    'age': entity.age if hasattr(entity, 'age') else None,
                    'gender': getattr(entity, 'gender', None),
                    'date_of_birth': entity.date_of_birth.strftime('%Y-%m-%d') if entity.date_of_birth else None,
                })
            elif entity_type == 'bed':
                entity_data.update({
                    'status': entity.status,
                    'bed_type': entity.bed_type,
                    'bed_number': entity.bed_number,
                    'room': str(entity.room) if entity.room else None,
                    'department': str(entity.department) if hasattr(entity, 'department') else None,
                })
            elif entity_type in ['user', 'customuser']:
                entity_data.update({
                    'full_name': entity.get_full_name() if hasattr(entity, 'get_full_name') else str(entity),
                    'role': getattr(entity, 'role', None),
                    'email': getattr(entity, 'email', None),
                    'job_number': getattr(entity, 'job_number', None),
                })
            elif entity_type in ['accessory', 'deviceaccessory']:
                entity_data.update({
                    'device': str(entity.device) if entity.device else None,
                    'status': entity.status,
                    'serial_number': getattr(entity, 'serial_number', None),
                    'model': getattr(entity, 'model', None),
                })
            elif entity_type == 'doctor':
                entity_data.update({
                    'full_name': entity.user.get_full_name() if entity.user else str(entity),
                    'role': 'doctor',
                    'email': entity.user.email if entity.user else None,
                })
            
            return entity_type, entity_id, entity_data, None
            
        except model_class.DoesNotExist:
            return None, None, None, f"{entity_type.title()} with ID {entity_id} not found"
    
    except ValueError:
        return None, None, None, "Invalid entity ID format"
    except Exception as e:
        return None, None, None, f"Error parsing QR code: {str(e)}"


@csrf_exempt
def scan_qr_code_api(request):
    """
    Standalone QR scanning API for dedicated scanners and mobile devices
    Works without browser interface - pure API endpoint
    Now with context-based flow management and secure token validation
    """
    from core.secure_qr import QRContextFlow
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        # Parse request data
        if request.content_type == 'application/json':
            data = json.loads(request.body) if request.body else {}
        else:
            data = request.POST.dict()
        
        qr_code = data.get('qr_code', '').strip()
        device_type = data.get('device_type', 'unknown')  # 'scanner', 'mobile', 'unknown'
        user_id = data.get('user_id')
        scanner_id = data.get('scanner_id')  # Unique ID for dedicated scanner
        session_id = data.get('session_id')  # Session ID for context flows
        
        if not qr_code:
            return JsonResponse({'error': 'QR code is required'}, status=400)
        
        # Parse QR code (now supports secure tokens)
        entity_type, entity_id, entity_data, error = parse_qr_code(qr_code)
        
        if error:
            return JsonResponse({
                'success': False,
                'error': error,
                'qr_code': qr_code
            }, status=400)
        
        # Get user if provided
        user = None
        if user_id:
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                pass
        
        # Initialize flow tracking variables
        flow_name = None
        flow_executed = False
        
        # Log the scan with enhanced data (initial log, will update if flow matches)
        scan_log = log_qr_scan(
            qr_code=qr_code,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_data=entity_data,
            user=user,
            device_type=device_type,
            scanner_id=scanner_id,
            request=request,
            is_secure=entity_data.get('token_uuid') is not None,
            is_ephemeral=entity_data.get('ephemeral', False),
            session_id=session_id
        )
        
        # Handle context-based flows for mobile devices
        if device_type == 'mobile' and user_id:
            # Start or continue session
            if not session_id:
                session_id = QRContextFlow.start_session(user_id, device_type)
            
            # Add scan to session and check for flow matches
            flow_result = QRContextFlow.add_scan(session_id, entity_type, entity_id)
            
            if 'error' in flow_result:
                # Session expired, start new one
                session_id = QRContextFlow.start_session(user_id, device_type)
                flow_result = QRContextFlow.add_scan(session_id, entity_type, entity_id)
            
            # Check if we matched a flow
            if flow_result.get('matched'):
                flow_info = flow_result['flow']
                flow_name = flow_info['name']
                
                # Update scan log with flow information
                scan_log.flow_name = flow_name
                scan_log.session_id = session_id
                
                if flow_result.get('auto_execute'):
                    # Execute flow automatically
                    execution = QRContextFlow.execute_flow(session_id)
                    flow_executed = True
                    
                    # Update scan log
                    scan_log.flow_executed = True
                    scan_log.save()
                    
                    return JsonResponse({
                        'success': True,
                        'flow_matched': True,
                        'flow_name': flow_info['name'],
                        'flow_action': flow_info['config']['action'],
                        'auto_executed': True,
                        'execution_result': execution,
                        'session_id': session_id,
                        'entity_data': entity_data,
                        'message': f"تم تنفيذ العملية: {flow_info['config']['description']}"
                    })
                else:
                    # Flow requires confirmation
                    scan_log.save()
                    
                    return JsonResponse({
                        'success': True,
                        'flow_matched': True,
                        'flow_name': flow_info['name'],
                        'flow_action': flow_info['config']['action'],
                        'requires_confirmation': True,
                        'session_id': session_id,
                        'entity_data': entity_data,
                        'message': f"تأكيد العملية: {flow_info['config']['description']}"
                    })
            else:
                # No flow matched yet, continue scanning
                return JsonResponse({
                    'success': True,
                    'flow_matched': False,
                    'scan_count': flow_result.get('scan_count', 1),
                    'current_sequence': flow_result.get('current_sequence', []),
                    'session_id': session_id,
                    'entity_type': entity_type,
                    'entity_id': entity_id,
                    'entity_data': entity_data,
                    'message': f'تم مسح {entity_type}:{entity_id}'
                })
        
        # Handle based on device type (if no context flow)
        elif device_type == 'scanner':
            # Dedicated scanner - just log and return basic info
            return JsonResponse({
                'success': True,
                'logged': True,
                'scan_id': scan_log.id,
                'entity_type': entity_type,
                'entity_id': entity_id,
                'entity_name': entity_data.get('name', str(entity_id)),
                'is_secure': entity_data.get('token_uuid') is not None,
                'is_ephemeral': entity_data.get('ephemeral', False),
                'timestamp': scan_log.scanned_at.isoformat(),
                'message': f'تم تسجيل مسح {entity_type}:{entity_id}'
            })
        
        else:
            # Unknown device type or mobile without session - return basic info
            redirect_url = get_entity_detail_url(entity_type, entity_id)
            
            return JsonResponse({
                'success': True,
                'logged': True,
                'scan_id': scan_log.id,
                'entity_type': entity_type,
                'entity_id': entity_id,
                'entity_data': entity_data,
                'redirect_url': redirect_url,
                'is_secure': entity_data.get('token_uuid') is not None,
                'is_ephemeral': entity_data.get('ephemeral', False),
                'timestamp': scan_log.scanned_at.isoformat(),
                'message': f'تم مسح {entity_type}:{entity_id}'
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Server error: {str(e)}'
        }, status=500)


@login_required
def scan_qr_code(request):
    """
    API endpoint to scan and parse QR codes with dynamic operation support
    """
    from .qr_operations import QROperationsManager
    from .models import OperationExecution
    
    print(f"[DEBUG] scan_qr_code called - Method: {request.method}")
    print(f"[DEBUG] Request body: {request.body}")
    print(f"[DEBUG] User: {request.user}")
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body) if request.body else {}
        print(f"[DEBUG] Parsed data: {data}")
        qr_code = data.get('qr_code', '').strip()
        sample_token = data.get('sample_token', '').strip()
        session_id = data.get('session_id')
        print(f"[DEBUG] QR Code: {qr_code}, Session ID: {session_id}")
        
        # Initialize operations manager
        ops_manager = QROperationsManager()
        
        if not qr_code and not sample_token:
            return JsonResponse({'error': 'QR code or sample token is required'}, status=400)
        
        # Parse QR code or sample token
        entity_type, entity_id, entity_data, error = parse_qr_code(qr_code, sample_token)
        
        if error:
            return JsonResponse({
                'success': False,
                'error': error,
                'qr_code': qr_code
            })
        
        # Check if this is a direct entity scan that should redirect
        redirect_to_page = data.get('redirect_to_page', True)  # Default to redirect
        
        if redirect_to_page and entity_type == 'device':
            # Return redirect URL for device detail page
            device_url = reverse('maintenance:device_detail', kwargs={'pk': entity_id})
            return JsonResponse({
                'success': True,
                'redirect': True,
                'redirect_url': device_url,
                'entity_type': entity_type,
                'entity_id': entity_id,
                'entity_data': entity_data,
                'message': f'تم توجيهك إلى صفحة الجهاز: {entity_data.get("name", entity_id)}'
            })
        
        elif redirect_to_page and entity_type == 'patient':
            # Return redirect URL for patient detail page (if exists)
            try:
                patient_url = reverse('manager:patient_detail', kwargs={'pk': entity_id})
                return JsonResponse({
                    'success': True,
                    'redirect': True,
                    'redirect_url': patient_url,
                    'entity_type': entity_type,
                    'entity_id': entity_id,
                    'entity_data': entity_data,
                    'message': f'تم توجيهك إلى صفحة المريض: {entity_data.get("name", entity_id)}'
                })
            except:
                # If patient detail URL doesn't exist, continue with normal flow
                pass
        
        elif redirect_to_page and entity_type == 'bed':
            # Return redirect URL for bed detail page (if exists)
            try:
                bed_url = reverse('manager:bed_detail', kwargs={'pk': entity_id})
                return JsonResponse({
                    'success': True,
                    'redirect': True,
                    'redirect_url': bed_url,
                    'entity_type': entity_type,
                    'entity_id': entity_id,
                    'entity_data': entity_data,
                    'message': f'تم توجيهك إلى صفحة السرير: {entity_data.get("name", entity_id)}'
                })
            except:
                # If bed detail URL doesn't exist, continue with normal flow
                pass
        
        # Get or create scan session
        scan_session = None
        if session_id:
            try:
                scan_session = ScanSession.objects.get(session_id=session_id, status='active')
                # Check session timeout
                if ops_manager.check_session_timeout(scan_session):
                    scan_session.status = 'expired'
                    scan_session.save()
                    scan_session = None
            except ScanSession.DoesNotExist:
                pass
        
        # Create new session if none exists
        if not scan_session:
            scan_session = ScanSession.objects.create()
            # Initialize context_json if not exists
            if not hasattr(scan_session, 'context_json') or scan_session.context_json is None:
                scan_session.context_json = {}
                scan_session.save()
        
        # Add to scan history
        scan_history = ScanHistory.objects.create(
            session=scan_session,
            scanned_code=qr_code,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_data=entity_data,
            is_valid=True
        )
        
        # Update session with basic entity tracking (backward compatibility)
        session_updated = False
        
        # First scan should be a user (doctor/nurse/staff)
        if not scan_session.user and entity_type in ['customuser', 'user', 'doctor']:
            if entity_type == 'doctor':
                # Get the user from doctor
                doctor_model = apps.get_model('manager', 'Doctor')
                doctor = doctor_model.objects.get(pk=entity_id)
                scan_session.user = doctor.user
            else:
                user_model = apps.get_model('hr', 'CustomUser')
                scan_session.user = user_model.objects.get(pk=entity_id)
            session_updated = True
        
        # Second scan can be patient or bed
        elif scan_session.user and not scan_session.patient and not scan_session.bed:
            if entity_type == 'patient':
                patient_model = apps.get_model('manager', 'Patient')
                scan_session.patient = patient_model.objects.get(pk=entity_id)
                session_updated = True
            elif entity_type == 'bed':
                bed_model = apps.get_model('manager', 'Bed')
                scan_session.bed = bed_model.objects.get(pk=entity_id)
                session_updated = True
        
        # Update last activity
        if hasattr(scan_session, 'last_activity'):
            scan_session.last_activity = timezone.now()
            session_updated = True
        
        if session_updated:
            scan_session.save()
        
        # Get all scanned entities and match to operations
        scanned_entities = ops_manager.get_scanned_entities(scan_session)
        matched_operation = ops_manager.match_operation(scanned_entities)
        
        operation_executed = False
        execution_result = None
        execution_message = None
        
        # Execute operation if matched
        if matched_operation:
            # Update session's current operation
            if hasattr(scan_session, 'current_operation'):
                scan_session.current_operation = matched_operation
                scan_session.save()
            
            # Check if we can execute multiple operations in same session
            existing_executions = apps.get_model('maintenance', 'OperationExecution').objects.filter(
                session=scan_session,
                operation=matched_operation,
                status__in=['completed', 'in_progress']
            )
            
            can_execute = matched_operation.allow_multiple_executions or not existing_executions.exists()
            
            if can_execute:
                success, execution, message = ops_manager.execute_operation(
                    matched_operation,
                    scan_session,
                    request.user,
                    scanned_entities
                )
                operation_executed = True
                execution_result = execution
                execution_message = message
        
        # Prepare response
        response_data = {
            'success': True,
            'session_id': str(scan_session.session_id),
            'entity_type': entity_type,
            'entity_id': entity_id,
            'entity_data': entity_data,
            'matched_operation': {
                'name': matched_operation.name,
                'code': matched_operation.code,
                'requires_confirmation': matched_operation.requires_confirmation
            } if matched_operation else None,
            'operation_executed': operation_executed,
            'execution': {
                'id': execution_result.id,
                'status': execution_result.status,
                'message': execution_message
            } if execution_result else None,
            'session_status': {
                'user': scan_session.user.get_full_name() if scan_session.user else None,
                'patient': str(scan_session.patient) if scan_session.patient else None,
                'bed': str(scan_session.bed) if scan_session.bed else None,
                'scan_count': scan_session.scan_history.count(),
                'current_operation': scan_session.current_operation.name if hasattr(scan_session, 'current_operation') and scan_session.current_operation else None,
            }
        }
        
        # Add validation warnings and notifications
        warnings = []
        notifications = []
        
        if entity_type == 'device':
            try:
                device = apps.get_model('maintenance', 'Device').objects.get(pk=entity_id)
                
                # Update device status when scanned for usage
                if matched_operation and matched_operation.code == 'DEVICE_USAGE' and scan_session.user and scan_session.patient:
                    device.availability = False  # Mark as in use
                    device.save()
                    notifications.append(f"🔧 تم تعيين الجهاز كمستخدم: {device.name}")
                
                # Check if we have accessories scanned in this session that need linking
                accessory_scans = scan_session.scan_history.filter(entity_type='accessory')
                for accessory_scan in accessory_scans:
                    try:
                        accessory = apps.get_model('maintenance', 'DeviceAccessory').objects.get(pk=accessory_scan.entity_id)
                        
                        # Check if accessory is already linked to this device
                        if accessory.device_id == device.id:
                            notifications.append(f"✅ الملحق {accessory.name} مربوط بالفعل بالجهاز")
                        else:
                            # Check if accessory is linked to another device
                            if accessory.device and accessory.device != device:
                                # Create transfer request
                                transfer_request = apps.get_model('maintenance', 'AccessoryTransferRequest').objects.create(
                                    accessory=accessory,
                                    from_device=accessory.device,
                                    from_department=accessory.device.department,
                                    from_room=accessory.device.room,
                                    to_device=device,
                                    to_department=device.department,
                                    to_room=device.room,
                                    requested_by=scan_session.user,
                                    reason=f"نقل تلقائي من المسح - من {accessory.device.name} إلى {device.name}"
                                )
                                notifications.append(f"📋 تم إرسال طلب نقل الملحق {accessory.name} من {accessory.device.name} إلى {device.name}")
                                warnings.append(f"⚠️ الملحق {accessory.name} مربوط حالياً بجهاز آخر - تم إرسال طلب نقل")
                            else:
                                # Link accessory to device directly
                                old_device = accessory.device
                                accessory.device = device
                                accessory.save()
                                
                                # Create transfer log
                                apps.get_model('maintenance', 'AccessoryTransferLog').objects.create(
                                    accessory=accessory,
                                    from_device=old_device,
                                    from_department=old_device.department if old_device else None,
                                    from_room=old_device.room if old_device else None,
                                    to_device=device,
                                    to_department=device.department,
                                    to_room=device.room,
                                    transferred_by=scan_session.user,
                                    notes=f"ربط تلقائي من المسح"
                                )
                                notifications.append(f"✅ تم ربط الملحق {accessory.name} بالجهاز: {device.name}")
                    except apps.get_model('maintenance', 'DeviceAccessory').DoesNotExist:
                        continue
                
                if hasattr(device, 'status') and device.status == 'maintenance':
                    warnings.append(f"⚠️ الجهاز تحت الصيانة - لا يمكن استخدامه")
                elif hasattr(device, 'status') and device.status != 'working':
                    warnings.append(f"⚠️ الجهاز في حالة: {device.get_status_display()}")
                if hasattr(device, 'availability') and not device.availability:
                    warnings.append("⚠️ الجهاز غير متاح حالياً")
                if hasattr(device, 'clean_status') and device.clean_status == 'needs_cleaning':
                    warnings.append("⚠️ الجهاز يحتاج تنظيف")
                if hasattr(device, 'sterilization_status') and device.sterilization_status == 'needs_sterilization':
                    warnings.append("⚠️ الجهاز يحتاج تعقيم")
                notifications.append(f"✅ تم مسح الجهاز: {device.name}")
            except apps.get_model('maintenance', 'Device').DoesNotExist:
                warnings.append(f"⚠️ الجهاز رقم {entity_id} غير موجود في قاعدة البيانات")
                notifications.append(f"ℹ️ تم مسح كود جهاز: device:{entity_id}")
        
        elif entity_type == 'bed':
            try:
                bed = apps.get_model('manager', 'Bed').objects.get(pk=entity_id)
                if hasattr(bed, 'status') and bed.status == 'occupied':
                    warnings.append("⚠️ السرير مشغول حالياً")
                elif hasattr(bed, 'status') and bed.status == 'maintenance':
                    warnings.append("⚠️ السرير تحت الصيانة")
                notifications.append(f"✅ تم مسح السرير: {bed.name if hasattr(bed, 'name') else bed.id}")
            except apps.get_model('manager', 'Bed').DoesNotExist:
                warnings.append(f"⚠️ السرير رقم {entity_id} غير موجود في قاعدة البيانات")
                notifications.append(f"ℹ️ تم مسح كود سرير: bed:{entity_id}")
        
        elif entity_type == 'lab_tube':
            notifications.append(f"✅ تم مسح عينة المعمل: {entity_data['test_name']}")
            if entity_data['status'] == 'verified':
                notifications.append("✅ العينة معتمدة ومكتملة")
        
        elif entity_type == 'operation_token':
            notifications.append(f"🔧 تم تحديد نوع العملية: {entity_data['operation']}")
        
        elif entity_type == 'accessory':
            try:
                accessory = apps.get_model('maintenance', 'DeviceAccessory').objects.get(pk=entity_id)
                notifications.append(f"🔧 تم مسح الملحق: {accessory.name}")
                
                # Check if we have a device scanned in this session
                device_scans = scan_session.scan_history.filter(entity_type='device')
                if device_scans.exists():
                    # Get the last scanned device
                    last_device_scan = device_scans.last()
                    target_device = apps.get_model('maintenance', 'Device').objects.get(pk=last_device_scan.entity_id)
                    
                    # Check if accessory is already linked to this device
                    if accessory.device_id == target_device.id:
                        notifications.append(f"✅ الملحق مربوط بالفعل بالجهاز: {target_device.name}")
                    else:
                        # Check if accessory is linked to another device
                        if accessory.device and accessory.device != target_device:
                            # Create transfer request
                            transfer_request = apps.get_model('maintenance', 'AccessoryTransferRequest').objects.create(
                                accessory=accessory,
                                from_device=accessory.device,
                                from_department=accessory.device.department,
                                from_room=accessory.device.room,
                                to_device=target_device,
                                to_department=target_device.department,
                                to_room=target_device.room,
                                requested_by=scan_session.user,
                                reason=f"نقل تلقائي من المسح - من {accessory.device.name} إلى {target_device.name}"
                            )
                            notifications.append(f"📋 تم إرسال طلب نقل الملحق من {accessory.device.name} إلى {target_device.name}")
                            warnings.append(f"⚠️ الملحق مربوط حالياً بجهاز آخر - تم إرسال طلب نقل")
                        else:
                            # Link accessory to device directly
                            old_device = accessory.device
                            accessory.device = target_device
                            accessory.save()
                            
                            # Create transfer log
                            apps.get_model('maintenance', 'AccessoryTransferLog').objects.create(
                                accessory=accessory,
                                from_device=old_device,
                                from_department=old_device.department if old_device else None,
                                from_room=old_device.room if old_device else None,
                                to_device=target_device,
                                to_department=target_device.department,
                                to_room=target_device.room,
                                transferred_by=scan_session.user,
                                notes=f"ربط تلقائي من المسح"
                            )
                            notifications.append(f"✅ تم ربط الملحق بالجهاز: {target_device.name}")
                else:
                    notifications.append("ℹ️ امسح جهاز لربط الملحق به")
                    
            except apps.get_model('maintenance', 'DeviceAccessory').DoesNotExist:
                warnings.append(f"⚠️ الملحق رقم {entity_id} غير موجود في قاعدة البيانات")
                notifications.append(f"ℹ️ تم مسح كود ملحق: accessory:{entity_id}")
        
        elif entity_type == 'patient':
            notifications.append(f"👤 تم مسح المريض: {entity_data.get('name', entity_id)}")
        
        elif entity_type in ['user', 'customuser']:
            notifications.append(f"👨‍⚕️ تم مسح المستخدم: {entity_data.get('name', entity_id)}")
        
        elif entity_type == 'doctor':
            notifications.append(f"👨‍⚕️ تم مسح الطبيب: {entity_data.get('name', entity_id)}")
        
        else:
            notifications.append(f"✅ تم مسح الكود: {entity_type}:{entity_id}")
        
        response_data['warnings'] = warnings
        response_data['notifications'] = notifications
        
        return JsonResponse(response_data)
    
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Server error: {str(e)}'}, status=500)


@login_required
def scan_session_page(request):
    """
    Main scanning session page - Step 3 Enhanced
    """
    # Get or create active session for user
    active_session = ScanSession.objects.filter(
        user=request.user, 
        status='active'
    ).first()
    
    if not active_session:
        active_session = ScanSession.objects.create(user=request.user)
    
    # Get recent scan history
    recent_scans = ScanHistory.objects.filter(
        session__user=request.user
    ).order_by('-scanned_at')[:20]
    
    # Get operation choices for dropdown
    operation_choices = [
        ('usage', 'استخدام الأجهزة'),
        ('transfer', 'نقل جهاز'),
        ('patient_transfer', 'نقل مريض'),
        ('handover', 'تسليم جهاز'),
        ('clean', 'تنظيف'),
        ('sterilize', 'تعقيم'),
        ('maintenance', 'صيانة'),
    ]
    
    context = {
        'session': active_session,
        'recent_scans': recent_scans,
        'operation_choices': operation_choices,
        'title': 'جلسة المسح المتكاملة - Step 3'
    }
    
    return render(request, 'maintenance/scan_session.html', context)


@csrf_exempt
@login_required
def save_scan_session(request):
    """
    Save the current scan session based on operation type
    Enhanced for Step 3: Handles all operation types
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        session_id = data.get('session_id')
        operation_type = data.get('operation_type', 'usage')
        notes = data.get('notes', '')
        
        if not session_id:
            return JsonResponse({'error': 'Session ID is required'}, status=400)
        
        # Get the scan session
        try:
            scan_session = ScanSession.objects.get(
                session_id=session_id, 
                status='active'
            )
        except ScanSession.DoesNotExist:
            return JsonResponse({'error': 'Session not found'}, status=404)
        
        created_records = []
        
        # Handle different operation types
        if operation_type == 'usage':
            # Create DeviceDailyUsageLog
            usage_log = DeviceDailyUsageLog.objects.create(
                user=scan_session.user or request.user,
                patient=scan_session.patient,
                bed=scan_session.bed,
                department=scan_session.bed.department if scan_session.bed and hasattr(scan_session.bed, 'department') else None,
                operation_type='surgery',  # Map 'usage' to valid choice
                notes=notes,
                is_completed=True,
                completed_at=timezone.now()
            )
            
            # Add scanned devices to the log
            device_scans = scan_session.scan_history.filter(entity_type='device')
            for scan in device_scans:
                try:
                    device = Device.objects.get(pk=scan.entity_id)
                    DeviceUsageLogItem.objects.create(
                        usage_log=usage_log,
                        device=device,
                        notes=f"Scanned at {scan.scanned_at.strftime('%H:%M:%S')}"
                    )
                    # Update device status
                    device.in_use = True
                    device.current_patient = scan_session.patient
                    device.usage_start_time = timezone.now()
                    device.save()
                except Device.DoesNotExist:
                    continue
            
            # Add scanned accessories
            accessory_scans = scan_session.scan_history.filter(entity_type='accessory')
            for scan in accessory_scans:
                try:
                    accessory = DeviceAccessory.objects.get(pk=scan.entity_id)
                    DeviceAccessoryUsageLog.objects.create(
                        usage_log=usage_log,
                        accessory=accessory,
                        notes=f"Scanned at {scan.scanned_at.strftime('%H:%M:%S')}"
                    )
                    # Update accessory status
                    accessory.status = 'in_use'
                    accessory.save()
                except DeviceAccessory.DoesNotExist:
                    continue
            
            created_records.append({'type': 'usage_log', 'id': usage_log.id})
        
        elif operation_type == 'transfer':
            # Handle device transfers
            device_scans = scan_session.scan_history.filter(entity_type='device')
            location_scans = scan_session.scan_history.filter(entity_type__in=['department', 'room', 'bed'])
            
            for device_scan in device_scans:
                try:
                    device = Device.objects.get(pk=device_scan.entity_id)
                    
                    # Get target location
                    to_department = None
                    to_room = None
                    to_bed = None
                    
                    for loc_scan in location_scans:
                        if loc_scan.entity_type == 'department':
                            to_department = Department.objects.get(pk=loc_scan.entity_id)
                        elif loc_scan.entity_type == 'room':
                            to_room = Room.objects.get(pk=loc_scan.entity_id)
                        elif loc_scan.entity_type == 'bed':
                            to_bed = Bed.objects.get(pk=loc_scan.entity_id)
                    
                    # Create transfer log
                    transfer_log = DeviceTransferLog.objects.create(
                        device=device,
                        from_department=device.department,
                        from_room=device.room,
                        from_bed=device.bed,
                        to_department=to_department or device.department,
                        to_room=to_room or device.room,
                        to_bed=to_bed,
                        moved_by=scan_session.user or request.user,
                        note=notes
                    )
                    
                    # Update device location
                    if to_department:
                        device.department = to_department
                    if to_room:
                        device.room = to_room
                    if to_bed:
                        device.bed = to_bed
                    device.save()
                    
                    created_records.append({'type': 'device_transfer', 'id': transfer_log.id})
                    
                except (Device.DoesNotExist, Department.DoesNotExist, Room.DoesNotExist, Bed.DoesNotExist):
                    continue
        
        elif operation_type == 'patient_transfer':
            # Handle patient transfers
            patient_scans = scan_session.scan_history.filter(entity_type='patient')
            bed_scans = scan_session.scan_history.filter(entity_type='bed')
            
            for patient_scan in patient_scans:
                for bed_scan in bed_scans:
                    try:
                        patient = Patient.objects.get(pk=patient_scan.entity_id)
                        to_bed = Bed.objects.get(pk=bed_scan.entity_id)
                        
                        # Get current patient location (from admission)
                        current_admission = patient.admission_set.filter(discharge_date__isnull=True).first()
                        
                        # Create transfer log
                        transfer_log = PatientTransferLog.objects.create(
                            patient=patient,
                            from_department=current_admission.department if current_admission else None,
                            from_bed=current_admission.bed if current_admission else None,
                            to_department=to_bed.department,
                            to_room=to_bed.room,
                            to_bed=to_bed,
                            moved_by=scan_session.user or request.user,
                            note=notes
                        )
                        
                        # Update patient location
                        if current_admission:
                            current_admission.bed = to_bed
                            current_admission.department = to_bed.department
                            current_admission.save()
                        
                        # Update bed status
                        to_bed.status = 'occupied'
                        to_bed.save()
                        
                        created_records.append({'type': 'patient_transfer', 'id': transfer_log.id})
                        
                    except (Patient.DoesNotExist, Bed.DoesNotExist):
                        continue
        
        elif operation_type == 'handover':
            # Handle device handovers
            device_scans = scan_session.scan_history.filter(entity_type='device')
            user_scans = scan_session.scan_history.filter(entity_type__in=['user', 'customuser', 'doctor'])
            
            if len(user_scans) >= 2:
                from_user_scan = user_scans[0]
                to_user_scan = user_scans[1]
                
                # Get users
                try:
                    if from_user_scan.entity_type == 'doctor':
                        from_user = Doctor.objects.get(pk=from_user_scan.entity_id).user
                    else:
                        from_user = User.objects.get(pk=from_user_scan.entity_id)
                    
                    if to_user_scan.entity_type == 'doctor':
                        to_user = Doctor.objects.get(pk=to_user_scan.entity_id).user
                    else:
                        to_user = User.objects.get(pk=to_user_scan.entity_id)
                    
                    for device_scan in device_scans:
                        try:
                            device = Device.objects.get(pk=device_scan.entity_id)
                            
                            # Create handover log
                            handover_log = DeviceHandoverLog.objects.create(
                                device=device,
                                from_user=from_user,
                                to_user=to_user,
                                note=notes
                            )
                            
                            created_records.append({'type': 'device_handover', 'id': handover_log.id})
                            
                        except Device.DoesNotExist:
                            continue
                            
                except (User.DoesNotExist, Doctor.DoesNotExist):
                    pass
        
        # Handle cleaning/sterilization/maintenance operations
        elif operation_type in ['clean', 'sterilize', 'maintenance']:
            device_scans = scan_session.scan_history.filter(entity_type='device')
            
            for device_scan in device_scans:
                try:
                    device = Device.objects.get(pk=device_scan.entity_id)
                    user = scan_session.user or request.user
                    
                    if operation_type == 'clean':
                        device.clean_status = 'clean'
                        device.last_cleaned_by = user
                        device.last_cleaned_at = timezone.now()
                        DeviceCleaningLog.objects.create(device=device, last_cleaned_by=user)
                    
                    elif operation_type == 'sterilize':
                        device.sterilization_status = 'sterilized'
                        device.last_sterilized_by = user
                        device.last_sterilized_at = timezone.now()
                        DeviceSterilizationLog.objects.create(device=device, last_sterilized_by=user)
                    
                    elif operation_type == 'maintenance':
                        device.status = 'working'
                        device.last_maintained_by = user
                        device.last_maintained_at = timezone.now()
                        DeviceMaintenanceLog.objects.create(device=device, last_maintained_by=user)
                    
                    device.save()
                    created_records.append({'type': f'device_{operation_type}', 'device_id': device.id})
                    
                except Device.DoesNotExist:
                    continue
        # Mark session as completed
        scan_session.status = 'completed'
        scan_session.save()
        
        return JsonResponse({
            'success': True,
            'operation_type': operation_type,
            'created_records': created_records,
            'message': f'تم حفظ عملية {operation_type} بنجاح'
        })
    
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Server error: {str(e)}'}, status=500)


@login_required
def device_usage_logs(request):
    """
    View device usage logs with filtering and export options
    """
    logs = DeviceUsageLogDaily.objects.all().select_related(
        'checked_by', 'device'
    )
    
    # Filtering
    user_filter = request.GET.get('user')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if user_filter:
        logs = logs.filter(checked_by_id=user_filter)
    if date_from:
        logs = logs.filter(date__gte=date_from)
    if date_to:
        logs = logs.filter(date__lte=date_to)
    
    # Get filter options
    users = User.objects.filter(deviceusagelogdaily__isnull=False).distinct()
    
    context = {
        'logs': logs.order_by('-date'),
        'users': users,
        'filters': {
            'user': user_filter,
            'date_from': date_from,
            'date_to': date_to,
        }
    }
    
    return render(request, 'maintenance/device_usage_logs.html', context)


@login_required
def export_device_usage_logs(request):
    """Export device usage logs to Excel"""
    # Implementation for exporting logs
    pass


@login_required
@require_http_methods(["POST"])
def confirm_operation(request, execution_id):
    """
    API endpoint to confirm a pending operation execution
    """
    try:
        from .models import OperationExecution
        from .qr_operations import QROperationsManager
        
        execution = OperationExecution.objects.get(
            id=execution_id,
            status='pending'
        )
        
        # Get the operations manager
        ops_manager = QROperationsManager(execution.session)
        
        # Confirm the operation
        result = ops_manager.confirm_operation(execution_id)
        
        if result['success']:
            return JsonResponse({
                'success': True,
                'message': result.get('message', 'تم تأكيد العملية بنجاح'),
                'execution_id': execution_id,
                'logs_created': result.get('logs_created', [])
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'فشل تأكيد العملية')
            }, status=400)
            
    except OperationExecution.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'العملية غير موجودة أو تم تنفيذها بالفعل'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def cancel_operation(request, execution_id):
    """
    API endpoint to cancel a pending operation execution
    """
    try:
        from .models import OperationExecution
        from .qr_operations import QROperationsManager
        
        execution = OperationExecution.objects.get(
            id=execution_id,
            status='pending'
        )
        
        # Get the operations manager
        ops_manager = QROperationsManager(execution.session)
        
        # Cancel the operation
        result = ops_manager.cancel_operation(execution_id)
        
        if result['success']:
            return JsonResponse({
                'success': True,
                'message': 'تم إلغاء العملية بنجاح',
                'execution_id': execution_id
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'فشل إلغاء العملية')
            }, status=400)
            
    except OperationExecution.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'العملية غير موجودة أو تم تنفيذها بالفعل'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


# ═══════════════════════════════════════════════════════════════════════════
# STEP 3: ADDITIONAL API ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

@csrf_exempt
@login_required
def start_scan_session(request):
    """
    Start a new scan session
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        operation_type = data.get('operation_type')
        
        # Create new session
        session = ScanSession.objects.create(user=request.user)
        
        # Set operation hint if provided
        if operation_type:
            session.context_json = {'operation_hint': operation_type}
            session.save()
        
        return JsonResponse({
            'success': True,
            'session_id': str(session.session_id),
            'state': {
                'user': request.user.get_full_name(),
                'operation_hint': operation_type,
                'scan_count': 0
            }
        })
    
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Server error: {str(e)}'}, status=500)


@csrf_exempt
@login_required
def reset_scan_session(request):
    """
    Reset/clear the current scan session
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        session_id = data.get('session_id')
        
        if session_id:
            try:
                session = ScanSession.objects.get(
                    session_id=session_id,
                    user=request.user,
                    status='active'
                )
                session.status = 'cancelled'
                session.save()
            except ScanSession.DoesNotExist:
                pass
        
        # Create new session
        new_session = ScanSession.objects.create(user=request.user)
        
        return JsonResponse({
            'success': True,
            'session_id': str(new_session.session_id),
            'message': 'تم إعادة تعيين الجلسة'
        })
    
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Server error: {str(e)}'}, status=500)


@login_required
def get_session_status(request, session_id):
    """
    Get current session status and scan history
    """
    try:
        session = ScanSession.objects.get(
            session_id=session_id,
            user=request.user
        )
        
        scan_history = session.scan_history.all().order_by('-scanned_at')
        
        return JsonResponse({
            'success': True,
            'session': {
                'id': str(session.session_id),
                'status': session.status,
                'user': session.user.get_full_name() if session.user else None,
                'patient': str(session.patient) if session.patient else None,
                'bed': str(session.bed) if session.bed else None,
                'created_at': session.created_at.isoformat(),
                'scan_count': scan_history.count(),
            },
            'scan_history': [{
                'entity_type': scan.entity_type,
                'entity_data': scan.entity_data,
                'scanned_at': scan.scanned_at.isoformat(),
                'is_valid': scan.is_valid
            } for scan in scan_history[:20]]  # Last 20 scans
        })
    
    except ScanSession.DoesNotExist:
        return JsonResponse({'error': 'Session not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': f'Server error: {str(e)}'}, status=500)


def scan_session_page(request):
    """
    QR Scan session page for scanning workflow
    """
    return render(request, 'maintenance/scan_session.html', {
        'title': 'جلسة مسح QR/Barcode'
    })


@login_required
@require_http_methods(["POST"])
def end_scan_session(request):
    """
    End the current scan session
    """
    try:
        data = json.loads(request.body)
        session_id = data.get('session_id')
        
        if session_id:
            try:
                session = ScanSession.objects.get(
                    session_id=session_id,
                    user=request.user,
                    status='active'
                )
                session.status = 'completed'
                session.save()
                
                return JsonResponse({
                    'success': True,
                    'message': 'تم إنهاء الجلسة بنجاح'
                })
            except ScanSession.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': 'الجلسة غير موجودة'
                }, status=404)
        else:
            return JsonResponse({
                'success': False,
                'error': 'معرف الجلسة مطلوب'
            }, status=400)
            
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Server error: {str(e)}'}, status=500)


def qr_test_page(request):
    """
    QR Test page for Step 2 implementation
    Test scanning of Patient, Bed, CustomUser, and DeviceAccessory QR codes
    """
    return render(request, 'maintenance/qr_test.html', {
        'title': 'اختبار نظام QR/Barcode - Step 2'
    })


@csrf_exempt
@login_required
def generate_qr_code(request):
    """
    Generate QR code for any entity with support for static and ephemeral tokens
    """
    from core.secure_qr import SecureQRToken
    import base64
    from io import BytesIO
    import qrcode
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        entity_type = data.get('entity_type')
        entity_id = data.get('entity_id')
        ephemeral = data.get('ephemeral', False)  # Default to static tokens
        metadata = data.get('metadata', {})
        
        if not entity_type or not entity_id:
            return JsonResponse({'error': 'entity_type and entity_id are required'}, status=400)
        
        # Map entity types to models
        model_mapping = {
            'bed': apps.get_model('manager', 'Bed'),
            'device': apps.get_model('maintenance', 'Device'),
            'accessory': apps.get_model('maintenance', 'DeviceAccessory'),
            'patient': apps.get_model('manager', 'Patient'),
            'user': apps.get_model('hr', 'CustomUser'),
        }
        
        if entity_type not in model_mapping:
            return JsonResponse({'error': f'Unsupported entity type: {entity_type}'}, status=400)
        
        model_class = model_mapping[entity_type]
        
        try:
            entity = model_class.objects.get(pk=entity_id)
        except model_class.DoesNotExist:
            return JsonResponse({'error': f'{entity_type} with ID {entity_id} not found'}, status=404)
        
        # Generate secure token
        token = SecureQRToken.generate_token(
            entity_type=entity_type,
            entity_id=entity_id,
            ephemeral=ephemeral,
            metadata=metadata
        )
        
        # Generate full URL with token parameter
        from urllib.parse import urlencode
        base_url = f"{settings.QR_DOMAIN}/api/scan-qr/"
        qr_url = f"{base_url}?{urlencode({'token': token})}"
        
        # Generate QR code image with URL
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_url)  # Use full URL instead of raw token
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        
        # Convert to base64 for API response
        buffer.seek(0)
        img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        # Update entity's QR token if it has the field and not ephemeral
        if hasattr(entity, 'qr_token') and not ephemeral:
            entity.qr_token = token
            entity.save()
        
        response_data = {
            'success': True,
            'qr_token': token,
            'qr_url': qr_url,
            'qr_image_base64': img_base64,
            'ephemeral': ephemeral,
            'entity_type': entity_type,
            'entity_id': entity_id,
            'entity_name': str(entity),
        }
        
        if ephemeral:
            response_data['expires_in'] = SecureQRToken.EPHEMERAL_DURATION
            response_data['message'] = f'Ephemeral QR code generated for {entity_type}, valid for {SecureQRToken.EPHEMERAL_DURATION} seconds'
        else:
            response_data['message'] = f'Static QR code generated for {entity_type}'
            if hasattr(entity, 'qr_code') and entity.qr_code:
                response_data['qr_code_url'] = entity.qr_code.url
        
        return JsonResponse(response_data)
    
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Server error: {str(e)}'}, status=500)


def test_links(request):
    return render(request, "maintenance/test_links.html")


@login_required
def qr_links_page(request):
    """
    صفحة شاملة تحتوي على جميع روابط ووظائف نظام QR Code
    Comprehensive page containing all QR Code system links and functionality
    """
    from django.conf import settings
    
    context = {
        'title': 'QR Code System Links',
        'qr_domain': getattr(settings, 'QR_DOMAIN', 'https://hms.my-domain.com'),
    }
    
    return render(request, 'maintenance/qr_links.html', context)


@login_required
def all_devices_transfer(request):
    """
    View to show all devices with transfer request functionality
    """
    # Get all devices
    devices = Device.objects.select_related('department', 'room').all()
    
    # Apply filters
    search_query = request.GET.get('search', '')
    department_filter = request.GET.get('department', '')
    status_filter = request.GET.get('status', '')
    
    if search_query:
        devices = devices.filter(
            Q(name__icontains=search_query) | 
            Q(serial_number__icontains=search_query)
        )
    
    if department_filter:
        devices = devices.filter(department_id=department_filter)
    
    if status_filter:
        devices = devices.filter(status=status_filter)
    
    # Pagination
    paginator = Paginator(devices, 12)  # 12 devices per page
    page_number = request.GET.get('page')
    devices = paginator.get_page(page_number)
    
    # Get all departments for filter dropdown
    departments = Department.objects.all().order_by('name')
    
    context = {
        'devices': devices,
        'departments': departments,
        'search_query': search_query,
        'department_filter': department_filter,
        'status_filter': status_filter,
    }
    
    return render(request, 'maintenance/all_devices_transfer.html', context)


@login_required
def transfer_test_page(request):
    """
    Test page to show all transfer-related links
    """
    return render(request, 'maintenance/transfer_test_page.html')


def mobile_qr_scan(request):
    """
    Mobile-optimized QR scanning page
    """
    return render(request, 'maintenance/mobile_qr_scan.html')


@login_required
def department_transfer_requests(request, department_id):
    """
    View to show transfer requests related to a specific department
    """
    department = get_object_or_404(Department, id=department_id)
    
    # Get transfer requests where this department is involved (either as source or destination)
    transfer_requests = DeviceTransferRequest.objects.filter(
        Q(from_department=department) | Q(to_department=department)
    ).select_related(
        'device', 'from_department', 'to_department', 
        'requested_by', 'approved_by', 'accepted_by', 'rejected_by'
    ).order_by('-requested_at')
    
    # Apply status filter
    status_filter = request.GET.get('status', '')
    if status_filter:
        transfer_requests = transfer_requests.filter(status=status_filter)
    
    # Pagination
    paginator = Paginator(transfer_requests, 20)
    page_number = request.GET.get('page')
    transfer_requests = paginator.get_page(page_number)
    
    # Statistics
    stats = {
        'total': DeviceTransferRequest.objects.filter(
            Q(from_department=department) | Q(to_department=department)
        ).count(),
        'pending': DeviceTransferRequest.objects.filter(
            Q(from_department=department) | Q(to_department=department),
            status='pending'
        ).count(),
        'approved': DeviceTransferRequest.objects.filter(
            Q(from_department=department) | Q(to_department=department),
            status='approved'
        ).count(),
        'accepted': DeviceTransferRequest.objects.filter(
            Q(from_department=department) | Q(to_department=department),
            status='accepted'
        ).count(),
        'rejected': DeviceTransferRequest.objects.filter(
            Q(from_department=department) | Q(to_department=department),
            status='rejected'
        ).count(),
    }
    
    context = {
        'department': department,
        'transfer_requests': transfer_requests,
        'status_filter': status_filter,
        'stats': stats,
    }
    
    return render(request, 'maintenance/department_transfer_requests.html', context)