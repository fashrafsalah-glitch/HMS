from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from django.http import JsonResponse
from django.urls import reverse
from django.core.paginator import Paginator

from .models import (Device, ServiceRequest, WorkOrder, JobPlan, JobPlanStep, 
                     PreventiveMaintenanceSchedule, SLADefinition)
from .forms_cmms import (ServiceRequestForm, WorkOrderForm, WorkOrderUpdateForm, 
                        SLADefinitionForm, JobPlanForm, JobPlanStepForm, PMScheduleForm)

# بلاغات الصيانة (Service Requests)

@login_required
def service_request_list(request):
    """عرض قائمة البلاغات مع إمكانية الفلترة"""
    # هنا بنجيب البلاغات حسب صلاحيات المستخدم
    if request.user.is_superuser:
        # المدير يشوف كل البلاغات
        service_requests = ServiceRequest.objects.all()
    elif request.user.groups.filter(name='Supervisor').exists():
        # المشرف يشوف بلاغات قسمه
        if hasattr(request.user, 'department'):
            service_requests = ServiceRequest.objects.filter(device__department=request.user.department)
        else:
            service_requests = ServiceRequest.objects.none()
    else:
        # المستخدم العادي يشوف البلاغات اللي هو عملها بس
        service_requests = ServiceRequest.objects.filter(reporter=request.user)
    
    # فلترة حسب الحالة
    status_filter = request.GET.get('status', '')
    if status_filter:
        service_requests = service_requests.filter(status=status_filter)
    
    # فلترة حسب نوع البلاغ
    request_type_filter = request.GET.get('request_type', '')
    if request_type_filter:
        service_requests = service_requests.filter(request_type=request_type_filter)
    
    # فلترة حسب القسم
    department_filter = request.GET.get('department', '')
    if department_filter:
        service_requests = service_requests.filter(device__department=department_filter)
    
    # فلترة حسب البحث
    search_query = request.GET.get('search', '')
    if search_query:
        service_requests = service_requests.filter(
            Q(title__icontains=search_query) | 
            Q(description__icontains=search_query) | 
            Q(device__name__icontains=search_query) | 
            Q(device__serial_number__icontains=search_query)
        )
    
    # ترتيب النتائج
    service_requests = service_requests.order_by('-created_at')
    
    context = {
        'service_requests': service_requests,
        'status_filter': status_filter,
        'request_type_filter': request_type_filter,
        'department_filter': department_filter,
        'search_query': search_query,
        'status_choices': ServiceRequest.status.field.choices,
        'request_type_choices': ServiceRequest.request_type.field.choices,
    }
    
    return render(request, 'maintenance/cmms/service_request_list.html', context)

@login_required
def service_request_create(request):
    """إنشاء بلاغ جديد"""
    # إذا تم تحديد جهاز من قبل
    device_id = request.GET.get('device_id')
    initial_data = {}
    
    if device_id:
        try:
            device = Device.objects.get(id=device_id)
            initial_data['device'] = device
        except Device.DoesNotExist:
            pass
    
    if request.method == 'POST':
        form = ServiceRequestForm(request.POST, user=request.user)
        if form.is_valid():
            service_request = form.save(commit=False)
            service_request.reporter = request.user
            service_request.save()
            
            messages.success(request, 'تم إنشاء البلاغ بنجاح')
            return redirect('service_request_detail', sr_id=service_request.id)
    else:
        form = ServiceRequestForm(user=request.user, initial=initial_data)
    
    context = {
        'form': form,
        'device_id': device_id,
    }
    
    return render(request, 'maintenance/cmms/service_request_create.html', context)

@login_required
def service_request_detail(request, sr_id):
    """عرض تفاصيل البلاغ وأوامر الشغل المرتبطة"""
    service_request = get_object_or_404(ServiceRequest, id=sr_id)
    work_orders = service_request.work_orders.all().order_by('-created_at')
    
    # التحقق من صلاحية المستخدم لعرض البلاغ
    if not request.user.is_superuser and not request.user.groups.filter(name='Supervisor').exists():
        if hasattr(request.user, 'department') and service_request.device.department != request.user.department:
            if service_request.reporter != request.user:
                messages.error(request, 'ليس لديك صلاحية لعرض هذا البلاغ')
                return redirect('service_request_list')
    
    # نموذج إنشاء أمر شغل جديد
    if request.method == 'POST' and service_request.can_convert_to_wo():
        wo_form = WorkOrderForm(request.POST, user=request.user, service_request=service_request)
        if wo_form.is_valid():
            work_order = wo_form.save(commit=False)
            work_order.service_request = service_request
            work_order.created_by = request.user
            work_order.save()
            
            messages.success(request, 'تم إنشاء أمر الشغل بنجاح')
            return redirect('work_order_detail', wo_id=work_order.id)
    else:
        wo_form = WorkOrderForm(user=request.user, service_request=service_request)
    
    context = {
        'service_request': service_request,
        'work_orders': work_orders,
        'wo_form': wo_form,
    }
    
    return render(request, 'maintenance/cmms/service_request_detail.html', context)

@login_required
def service_request_update(request, sr_id):
    """تحديث بيانات البلاغ"""
    service_request = get_object_or_404(ServiceRequest, id=sr_id)
    
    # التحقق من صلاحية المستخدم لتعديل البلاغ
    if not request.user.is_superuser and service_request.reporter != request.user:
        if not request.user.groups.filter(name='Supervisor').exists():
            messages.error(request, 'ليس لديك صلاحية لتعديل هذا البلاغ')
            return redirect('service_request_detail', sr_id=service_request.id)
    
    if request.method == 'POST':
        form = ServiceRequestForm(request.POST, instance=service_request, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم تحديث البلاغ بنجاح')
            return redirect('service_request_detail', sr_id=service_request.id)
    else:
        form = ServiceRequestForm(instance=service_request, user=request.user)
    
    context = {
        'form': form,
        'service_request': service_request,
    }
    
    return render(request, 'maintenance/cmms/service_request_update.html', context)

@login_required
def service_request_close(request, sr_id):
    """إغلاق البلاغ"""
    service_request = get_object_or_404(ServiceRequest, id=sr_id)
    
    # التحقق من صلاحية المستخدم لإغلاق البلاغ
    if not request.user.is_superuser and not request.user.groups.filter(name='Supervisor').exists():
        messages.error(request, 'ليس لديك صلاحية لإغلاق هذا البلاغ')
        return redirect('service_request_detail', sr_id=service_request.id)
    
    # التحقق من عدم وجود أوامر شغل مفتوحة
    open_work_orders = service_request.work_orders.filter(
        status__in=['new', 'assigned', 'in_progress', 'wait_parts', 'on_hold', 'resolved']
    ).exists()
    
    if open_work_orders:
        messages.error(request, 'لا يمكن إغلاق البلاغ لوجود أوامر شغل مفتوحة')
        return redirect('service_request_detail', sr_id=service_request.id)
    
    service_request.status = 'closed'
    service_request.closed_at = timezone.now()
    service_request.save()
    
    messages.success(request, 'تم إغلاق البلاغ بنجاح')
    return redirect('service_request_detail', sr_id=service_request.id)

# أوامر الشغل (Work Orders)

@login_required
def work_order_list(request):
    """عرض قائمة أوامر الشغل مع إمكانية الفلترة"""
    # هنا بنجيب أوامر الشغل حسب صلاحيات المستخدم
    if request.user.is_superuser:
        # المدير يشوف كل أوامر الشغل
        work_orders = WorkOrder.objects.all()
    elif request.user.groups.filter(name='Supervisor').exists():
        # المشرف يشوف أوامر شغل قسمه
        if hasattr(request.user, 'department'):
            work_orders = WorkOrder.objects.filter(service_request__device__department=request.user.department)
        else:
            work_orders = WorkOrder.objects.none()
    elif request.user.groups.filter(name='Technician').exists():
        # الفني يشوف أوامر الشغل المسندة إليه
        work_orders = WorkOrder.objects.filter(assignee=request.user)
    else:
        # المستخدم العادي يشوف أوامر الشغل المرتبطة ببلاغاته
        work_orders = WorkOrder.objects.filter(service_request__reporter=request.user)
    
    # فلترة حسب الحالة
    status_filter = request.GET.get('status', '')
    if status_filter:
        work_orders = work_orders.filter(status=status_filter)
    
    # فلترة حسب الفني المسؤول
    assignee_filter = request.GET.get('assignee', '')
    if assignee_filter:
        work_orders = work_orders.filter(assignee_id=assignee_filter)
    
    # فلترة حسب القسم
    department_filter = request.GET.get('department', '')
    if department_filter:
        work_orders = work_orders.filter(service_request__device__department=department_filter)
    
    # فلترة حسب البحث
    search_query = request.GET.get('search', '')
    if search_query:
        work_orders = work_orders.filter(
            Q(service_request__title__icontains=search_query) | 
            Q(description__icontains=search_query) | 
            Q(service_request__device__name__icontains=search_query) | 
            Q(service_request__device__serial_number__icontains=search_query)
        )
    
    # ترتيب النتائج
    work_orders = work_orders.order_by('-created_at')
    
    context = {
        'work_orders': work_orders,
        'status_filter': status_filter,
        'assignee_filter': assignee_filter,
        'department_filter': department_filter,
        'search_query': search_query,
        'status_choices': WorkOrder.status.field.choices,
    }
    
    return render(request, 'maintenance/cmms/work_order_list.html', context)

@login_required
def work_order_detail(request, wo_id):
    """عرض تفاصيل أمر الشغل والتعليقات"""
    work_order = get_object_or_404(WorkOrder, id=wo_id)
    comments = work_order.comments.all().order_by('created_at')
    
    # التحقق من صلاحية المستخدم لعرض أمر الشغل
    if not request.user.is_superuser and not request.user.groups.filter(name='Supervisor').exists():
        if work_order.assignee != request.user and work_order.service_request.reporter != request.user:
            if hasattr(request.user, 'department') and work_order.service_request.device.department != request.user.department:
                messages.error(request, 'ليس لديك صلاحية لعرض أمر الشغل هذا')
                return redirect('work_order_list')
    
    # نموذج تحديث حالة أمر الشغل
    if request.method == 'POST' and 'update_status' in request.POST:
        update_form = WorkOrderUpdateForm(request.POST, instance=work_order, user=request.user)
        if update_form.is_valid():
            # إذا تم تغيير الحالة إلى تم التحقق، نسجل من قام بالتحقق
            if update_form.cleaned_data['status'] == 'qa_verified' and work_order.status != 'qa_verified':
                work_order.qa_verified_by = request.user
                work_order.qa_verified_at = timezone.now()
            
            update_form.save()
            messages.success(request, 'تم تحديث حالة أمر الشغل بنجاح')
            return redirect('work_order_detail', wo_id=work_order.id)
    else:
        update_form = WorkOrderUpdateForm(instance=work_order, user=request.user)
    
    # تم إزالة نموذج التعليقات مؤقتاً حتى يتم تطبيق نموذج WorkOrderComment
    comment_form = None
    
    context = {
        'work_order': work_order,
        'comments': comments,
        'update_form': update_form,
        'comment_form': comment_form,
    }
    
    return render(request, 'maintenance/cmms/work_order_detail.html', context)

@login_required
def work_order_assign(request, wo_id):
    """تعيين فني لأمر الشغل"""
    work_order = get_object_or_404(WorkOrder, id=wo_id)
    
    # التحقق من صلاحية المستخدم لتعيين فني
    if not request.user.is_superuser and not request.user.groups.filter(name='Supervisor').exists():
        messages.error(request, 'ليس لديك صلاحية لتعيين فني')
        return redirect('work_order_detail', wo_id=work_order.id)
    
    # التحقق من أن أمر الشغل في حالة تسمح بالتعيين
    if work_order.status not in ['new', 'assigned']:
        messages.error(request, 'لا يمكن تعيين فني لأمر شغل في هذه الحالة')
        return redirect('work_order_detail', wo_id=work_order.id)
    
    if request.method == 'POST':
        assignee_id = request.POST.get('assignee')
        if assignee_id:
            try:
                assignee = User.objects.get(id=assignee_id)
                work_order.assignee = assignee
                work_order.status = 'assigned'
                work_order.save()
                
                # إضافة تعليق تلقائي
                WorkOrderComment.objects.create(
                    work_order=work_order,
                    user=request.user,
                    comment=f'تم تعيين {assignee.get_full_name() or assignee.username} كفني مسؤول'
                )
                
                messages.success(request, 'تم تعيين الفني بنجاح')
            except User.DoesNotExist:
                messages.error(request, 'الفني غير موجود')
        else:
            messages.error(request, 'يجب اختيار فني')
    
    return redirect('work_order_detail', wo_id=work_order.id)

# إدارة SLA

@login_required
def sla_list(request):
    """عرض قائمة اتفاقيات مستوى الخدمة"""
    # التحقق من صلاحية المستخدم
    if not request.user.is_superuser and not request.user.groups.filter(name='Supervisor').exists():
        messages.error(request, 'ليس لديك صلاحية لعرض اتفاقيات مستوى الخدمة')
        return redirect('service_request_list')
    
    slas = SLA.objects.all()
    
    context = {
        'slas': slas,
    }
    
    return render(request, 'maintenance/cmms/sla_list.html', context)

@login_required
def sla_create(request):
    """إنشاء اتفاقية مستوى خدمة جديدة"""
    # التحقق من صلاحية المستخدم
    if not request.user.is_superuser and not request.user.groups.filter(name='Supervisor').exists():
        messages.error(request, 'ليس لديك صلاحية لإنشاء اتفاقية مستوى خدمة')
        return redirect('sla_list')
    
    if request.method == 'POST':
        form = SLAForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم إنشاء اتفاقية مستوى الخدمة بنجاح')
            return redirect('sla_list')
    else:
        form = SLAForm()
    
    context = {
        'form': form,
    }
    
    return render(request, 'maintenance/cmms/sla_create.html', context)

@login_required
def sla_matrix_list(request):
    """عرض مصفوفة اتفاقيات مستوى الخدمة"""
    # التحقق من صلاحية المستخدم
    if not request.user.is_superuser and not request.user.groups.filter(name='Supervisor').exists():
        messages.error(request, 'ليس لديك صلاحية لعرض مصفوفة اتفاقيات مستوى الخدمة')
        return redirect('service_request_list')
    
    sla_matrix = SLAMatrix.objects.all()
    
    # تنظيم المصفوفة في شكل جدول
    severity_choices = dict(SEVERITY_CHOICES)
    impact_choices = dict(IMPACT_CHOICES)
    
    matrix_table = {}
    for severity in severity_choices.keys():
        matrix_table[severity] = {}
        for impact in impact_choices.keys():
            matrix_table[severity][impact] = None
    
    for entry in sla_matrix:
        matrix_table[entry.severity][entry.impact] = entry.sla
    
    context = {
        'matrix_table': matrix_table,
        'severity_choices': severity_choices,
        'impact_choices': impact_choices,
    }
    
    return render(request, 'maintenance/cmms/sla_matrix_list.html', context)

@login_required
def sla_matrix_create(request):
    """إنشاء أو تحديث عنصر في مصفوفة اتفاقيات مستوى الخدمة"""
    # التحقق من صلاحية المستخدم
    if not request.user.is_superuser and not request.user.groups.filter(name='Supervisor').exists():
        messages.error(request, 'ليس لديك صلاحية لتعديل مصفوفة اتفاقيات مستوى الخدمة')
        return redirect('sla_matrix_list')
    
    # التحقق من وجود عنصر موجود بالفعل
    severity = request.GET.get('severity')
    impact = request.GET.get('impact')
    instance = None
    
    if severity and impact:
        try:
            instance = SLAMatrix.objects.get(severity=severity, impact=impact)
        except SLAMatrix.DoesNotExist:
            pass
    
    if request.method == 'POST':
        form = SLAMatrixForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم حفظ عنصر المصفوفة بنجاح')
            return redirect('sla_matrix_list')
    else:
        initial_data = {}
        if severity:
            initial_data['severity'] = severity
        if impact:
            initial_data['impact'] = impact
        
        form = SLAMatrixForm(instance=instance, initial=initial_data)
    
    context = {
        'form': form,
        'instance': instance,
    }
    
    return render(request, 'maintenance/cmms/sla_matrix_create.html', context)

# دمج مع الصفحات الموجودة

@login_required
def device_maintenance_history(request, device_id):
    """عرض تاريخ صيانة الجهاز مع إضافة البلاغات وأوامر الشغل"""
    device = get_object_or_404(Device, id=device_id)
    
    # جلب سجلات الصيانة الموجودة
    maintenance_logs = device.maintenance_logs.all().order_by('-maintained_at')
    
    # جلب البلاغات وأوامر الشغل
    service_requests = device.service_requests.all().order_by('-created_at')
    
    # تجميع كل السجلات في قائمة واحدة مرتبة زمنيًا
    all_activities = []
    
    # إضافة سجلات الصيانة
    for log in maintenance_logs:
        all_activities.append({
            'type': 'maintenance_log',
            'date': log.maintained_at,
            'object': log,
            'user': log.maintained_by,
            'description': 'صيانة روتينية',
        })
    
    # إضافة البلاغات
    for sr in service_requests:
        all_activities.append({
            'type': 'service_request',
            'date': sr.created_at,
            'object': sr,
            'user': sr.reporter,
            'description': sr.title,
        })
        
        # إضافة أوامر الشغل المرتبطة بكل بلاغ
        for wo in sr.work_orders.all():
            all_activities.append({
                'type': 'work_order',
                'date': wo.created_at,
                'object': wo,
                'user': wo.created_by,
                'description': f'أمر شغل: {sr.title}',
            })
    
    # ترتيب الأنشطة حسب التاريخ (الأحدث أولاً)
    all_activities.sort(key=lambda x: x['date'], reverse=True)
    
    context = {
        'device': device,
        'all_activities': all_activities,
    }
    
    return render(request, 'maintenance/maintenance_history.html', context)

@login_required
def device_detail_with_cmms(request, device_id):
    """عرض تفاصيل الجهاز مع إضافة معلومات CMMS"""
    device = get_object_or_404(Device, id=device_id)
    
    # جلب البلاغات المفتوحة
    open_service_requests = device.service_requests.filter(
        status__in=['new', 'in_progress', 'on_hold']
    ).order_by('-created_at')
    
    # جلب أوامر الشغل المفتوحة
    open_work_orders = WorkOrder.objects.filter(
        service_request__device=device,
        status__in=['new', 'assigned', 'in_progress', 'wait_parts', 'on_hold', 'resolved']
    ).order_by('-created_at')
    
    # إضافة المعلومات إلى السياق
    context = {
        'device': device,
        'open_service_requests': open_service_requests,
        'open_work_orders': open_work_orders,
    }
    
    # استدعاء العرض الأصلي
    return render(request, 'maintenance/device_detail.html', context)

# API لتطبيقات الموبايل أو الواجهة الأمامية

@login_required
def api_service_request_create(request):
    """API لإنشاء بلاغ جديد"""
    if request.method != 'POST':
        return JsonResponse({'error': 'يجب استخدام طريقة POST'}, status=405)
    
    try:
        data = request.POST.copy()
        device_id = data.get('device_id')
        title = data.get('title')
        description = data.get('description')
        request_type = data.get('request_type', 'breakdown')
        severity = data.get('severity', 'medium')
        impact = data.get('impact', 'moderate')
        
        # التحقق من البيانات المطلوبة
        if not all([device_id, title, description]):
            return JsonResponse({'error': 'يجب توفير جميع البيانات المطلوبة'}, status=400)
        
        # التحقق من وجود الجهاز
        try:
            device = Device.objects.get(id=device_id)
        except Device.DoesNotExist:
            return JsonResponse({'error': 'الجهاز غير موجود'}, status=404)
        
        # إنشاء البلاغ
        service_request = ServiceRequest.objects.create(
            device=device,
            reporter=request.user,
            title=title,
            description=description,
            request_type=request_type,
            severity=severity,
            impact=impact
        )
        
        return JsonResponse({
            'success': True,
            'service_request_id': service_request.id,
            'message': 'تم إنشاء البلاغ بنجاح'
        })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def api_work_order_status_update(request, wo_id):
    """API لتحديث حالة أمر الشغل"""
    if request.method != 'POST':
        return JsonResponse({'error': 'يجب استخدام طريقة POST'}, status=405)
    
    try:
        work_order = get_object_or_404(WorkOrder, id=wo_id)
        
        # التحقق من صلاحية المستخدم
        if not request.user.is_superuser and work_order.assignee != request.user:
            if not request.user.groups.filter(name='Supervisor').exists():
                return JsonResponse({'error': 'ليس لديك صلاحية لتحديث حالة أمر الشغل'}, status=403)
        
        data = request.POST.copy()
        new_status = data.get('status')
        resolution = data.get('resolution', '')
        notes = data.get('notes', '')
        
        # التحقق من صحة الحالة الجديدة
        if new_status not in dict(WO_STATUS_CHOICES):
            return JsonResponse({'error': 'حالة غير صالحة'}, status=400)
        
        # تحديث أمر الشغل
        work_order.status = new_status
        if resolution:
            work_order.resolution = resolution
        if notes:
            work_order.notes = notes
        
        # إذا تم تغيير الحالة إلى تم التحقق، نسجل من قام بالتحقق
        if new_status == 'qa_verified' and work_order.status != 'qa_verified':
            work_order.qa_verified_by = request.user
            work_order.qa_verified_at = timezone.now()
        
        work_order.save()
        
        # إضافة تعليق تلقائي
        comment_text = f'تم تغيير الحالة إلى {dict(WO_STATUS_CHOICES)[new_status]}'
        WorkOrderComment.objects.create(
            work_order=work_order,
            user=request.user,
            comment=comment_text
        )
        
        return JsonResponse({
            'success': True,
            'message': 'تم تحديث حالة أمر الشغل بنجاح'
        })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def api_device_profile(request, device_id):
    """API لعرض ملف الجهاز الكامل (تاريخ الصيانة، البلاغات، أوامر الشغل)"""
    try:
        device = get_object_or_404(Device, id=device_id)
        
        # جمع البيانات
        maintenance_logs = [{
            'id': log.id,
            'date': log.maintained_at.strftime('%Y-%m-%d %H:%M'),
            'user': log.maintained_by.get_full_name() or log.maintained_by.username,
            'type': 'maintenance_log',
            'description': 'صيانة روتينية',
        } for log in device.maintenance_logs.all().order_by('-maintained_at')[:10]]
        
        service_requests = [{
            'id': sr.id,
            'date': sr.created_at.strftime('%Y-%m-%d %H:%M'),
            'user': sr.reporter.get_full_name() or sr.reporter.username,
            'type': 'service_request',
            'title': sr.title,
            'status': sr.get_status_display(),
            'request_type': sr.get_request_type_display(),
        } for sr in device.service_requests.all().order_by('-created_at')[:10]]
        
        work_orders = [{
            'id': wo.id,
            'date': wo.created_at.strftime('%Y-%m-%d %H:%M'),
            'user': wo.created_by.get_full_name() or wo.created_by.username,
            'type': 'work_order',
            'title': wo.service_request.title,
            'status': wo.get_status_display(),
            'assignee': wo.assignee.get_full_name() if wo.assignee else 'غير معين',
        } for wo in WorkOrder.objects.filter(service_request__device=device).order_by('-created_at')[:10]]
        
        # إحصائيات
        total_maintenance = device.maintenance_logs.count()
        total_service_requests = device.service_requests.count()
        total_work_orders = WorkOrder.objects.filter(service_request__device=device).count()
        
        # حساب متوسط وقت الإصلاح (MTTR)
        completed_work_orders = WorkOrder.objects.filter(
            service_request__device=device,
            status__in=['closed', 'qa_verified'],
            start_time__isnull=False,
            end_time__isnull=False
        )
        
        mttr_minutes = 0
        if completed_work_orders.exists():
            total_minutes = 0
            for wo in completed_work_orders:
                duration = wo.end_time - wo.start_time
                total_minutes += duration.total_seconds() / 60
            
            mttr_minutes = total_minutes / completed_work_orders.count()
        
        return JsonResponse({
            'device': {
                'id': device.id,
                'name': device.name,
                'serial_number': device.serial_number,
                'model': device.model,
                'status': device.status,
                'department': device.department.name if hasattr(device, 'department') and device.department else 'غير محدد',
                'room': device.room.name if hasattr(device, 'room') and device.room else 'غير محدد',
            },
            'maintenance_logs': maintenance_logs,
            'service_requests': service_requests,
            'work_orders': work_orders,
            'statistics': {
                'total_maintenance': total_maintenance,
                'total_service_requests': total_service_requests,
                'total_work_orders': total_work_orders,
                'mttr_minutes': round(mttr_minutes, 2),
            }
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# الصيانة الوقائية (Preventive Maintenance)

@login_required
def job_plan_list(request):
    """عرض قائمة خطط العمل"""
    # التحقق من صلاحيات المستخدم
    if not request.user.is_superuser and not request.user.groups.filter(name__in=['Supervisor', 'Technician']).exists():
        messages.error(request, 'ليس لديك صلاحية لعرض خطط العمل')
        return redirect('dashboard')
    
    job_plans = JobPlan.objects.all().order_by('name')
    
    # فلترة حسب البحث
    search_query = request.GET.get('search', '')
    if search_query:
        job_plans = job_plans.filter(
            Q(name__icontains=search_query) | 
            Q(description__icontains=search_query)
        )
    
    # ترقيم الصفحات
    paginator = Paginator(job_plans, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'job_plans': page_obj,
        'search_query': search_query,
    }
    
    return render(request, 'maintenance/cmms/job_plan_list.html', context)

@login_required
def job_plan_create(request):
    """إنشاء خطة عمل جديدة"""
    # التحقق من صلاحيات المستخدم
    if not request.user.is_superuser and not request.user.groups.filter(name='Supervisor').exists():
        messages.error(request, 'ليس لديك صلاحية لإنشاء خطط العمل')
        return redirect('job_plan_list')
    
    if request.method == 'POST':
        form = JobPlanForm(request.POST)
        if form.is_valid():
            job_plan = form.save(commit=False)
            job_plan.created_by = request.user
            job_plan.save()
            
            messages.success(request, 'تم إنشاء خطة العمل بنجاح')
            return redirect('job_plan_detail', plan_id=job_plan.id)
    else:
        form = JobPlanForm()
    
    context = {
        'form': form,
        'is_create': True,
    }
    
    return render(request, 'maintenance/cmms/job_plan_form.html', context)

@login_required
def job_plan_detail(request, plan_id):
    """عرض تفاصيل خطة العمل وخطواتها"""
    job_plan = get_object_or_404(JobPlan, id=plan_id)
    steps = job_plan.steps.all().order_by('step_number')
    pm_schedules = job_plan.pm_schedules.all().order_by('next_due_date')
    
    # نموذج إضافة خطوة جديدة
    if request.method == 'POST':
        step_form = JobPlanStepForm(request.POST)
        if step_form.is_valid():
            step = step_form.save(commit=False)
            step.job_plan = job_plan
            # تحديد رقم الخطوة التالي تلقائياً
            if not step.step_number:
                last_step = steps.last()
                step.step_number = (last_step.step_number + 1) if last_step else 1
            step.save()
            
            messages.success(request, 'تم إضافة الخطوة بنجاح')
            return redirect('job_plan_detail', plan_id=job_plan.id)
    else:
        step_form = JobPlanStepForm()
    
    context = {
        'job_plan': job_plan,
        'steps': steps,
        'pm_schedules': pm_schedules,
        'step_form': step_form,
    }
    
    return render(request, 'maintenance/cmms/job_plan_detail.html', context)

@login_required
def job_plan_update(request, plan_id):
    """تحديث خطة العمل"""
    job_plan = get_object_or_404(JobPlan, id=plan_id)
    
    # التحقق من صلاحيات المستخدم
    if not request.user.is_superuser and not request.user.groups.filter(name='Supervisor').exists():
        messages.error(request, 'ليس لديك صلاحية لتعديل خطط العمل')
        return redirect('job_plan_detail', plan_id=job_plan.id)
    
    if request.method == 'POST':
        form = JobPlanForm(request.POST, instance=job_plan)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم تحديث خطة العمل بنجاح')
            return redirect('job_plan_detail', plan_id=job_plan.id)
    else:
        form = JobPlanForm(instance=job_plan)
    
    context = {
        'form': form,
        'job_plan': job_plan,
        'is_create': False,
    }
    
    return render(request, 'maintenance/cmms/job_plan_form.html', context)

@login_required
def job_plan_delete(request, plan_id):
    """حذف خطة العمل"""
    job_plan = get_object_or_404(JobPlan, id=plan_id)
    
    # التحقق من صلاحيات المستخدم
    if not request.user.is_superuser:
        messages.error(request, 'ليس لديك صلاحية لحذف خطط العمل')
        return redirect('job_plan_detail', plan_id=job_plan.id)
    
    # التحقق من عدم وجود جداول صيانة مرتبطة
    if job_plan.pm_schedules.exists():
        messages.error(request, 'لا يمكن حذف خطة العمل لوجود جداول صيانة مرتبطة بها')
        return redirect('job_plan_detail', plan_id=job_plan.id)
    
    job_plan.delete()
    messages.success(request, 'تم حذف خطة العمل بنجاح')
    return redirect('job_plan_list')

@login_required
def job_plan_step_delete(request, step_id):
    """حذف خطوة من خطة العمل"""
    step = get_object_or_404(JobPlanStep, id=step_id)
    job_plan = step.job_plan
    
    # التحقق من صلاحيات المستخدم
    if not request.user.is_superuser and not request.user.groups.filter(name='Supervisor').exists():
        messages.error(request, 'ليس لديك صلاحية لحذف خطوات العمل')
        return redirect('job_plan_detail', plan_id=job_plan.id)
    
    step.delete()
    messages.success(request, 'تم حذف الخطوة بنجاح')
    return redirect('job_plan_detail', plan_id=job_plan.id)

@login_required
def pm_schedule_list(request):
    """عرض قائمة جداول الصيانة الوقائية"""
    # التحقق من صلاحيات المستخدم
    if not request.user.is_superuser and not request.user.groups.filter(name__in=['Supervisor', 'Technician']).exists():
        messages.error(request, 'ليس لديك صلاحية لعرض جداول الصيانة الوقائية')
        return redirect('dashboard')
    
    pm_schedules = PreventiveMaintenanceSchedule.objects.all().order_by('next_due_date')
    
    # فلترة حسب الحالة
    status_filter = request.GET.get('status', '')
    if status_filter:
        pm_schedules = pm_schedules.filter(status=status_filter)
    
    # فلترة حسب القسم
    department_filter = request.GET.get('department', '')
    if department_filter:
        pm_schedules = pm_schedules.filter(device__department=department_filter)
    
    # فلترة حسب البحث
    search_query = request.GET.get('search', '')
    if search_query:
        pm_schedules = pm_schedules.filter(
            Q(name__icontains=search_query) | 
            Q(description__icontains=search_query) | 
            Q(device__name__icontains=search_query) | 
            Q(job_plan__name__icontains=search_query)
        )
    
    # ترقيم الصفحات
    paginator = Paginator(pm_schedules, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'pm_schedules': page_obj,
        'status_filter': status_filter,
        'department_filter': department_filter,
        'search_query': search_query,
        'status_choices': PreventiveMaintenanceSchedule.status.field.choices,
    }
    
    return render(request, 'maintenance/cmms/pm_schedule_list.html', context)

@login_required
def pm_schedule_create(request):
    """إنشاء جدول صيانة وقائية جديد"""
    # التحقق من صلاحيات المستخدم
    if not request.user.is_superuser and not request.user.groups.filter(name='Supervisor').exists():
        messages.error(request, 'ليس لديك صلاحية لإنشاء جداول الصيانة الوقائية')
        return redirect('pm_schedule_list')
    
    # إذا تم تحديد جهاز من قبل
    device_id = request.GET.get('device_id')
    initial_data = {}
    
    if device_id:
        try:
            device = Device.objects.get(id=device_id)
            initial_data['device'] = device
        except Device.DoesNotExist:
            pass
    
    if request.method == 'POST':
        form = PMScheduleForm(request.POST, user=request.user)
        if form.is_valid():
            pm_schedule = form.save(commit=False)
            pm_schedule.created_by = request.user
            pm_schedule.save()
            
            messages.success(request, 'تم إنشاء جدول الصيانة الوقائية بنجاح')
            return redirect('pm_schedule_detail', schedule_id=pm_schedule.id)
    else:
        form = PMScheduleForm(user=request.user, initial=initial_data)
    
    context = {
        'form': form,
        'is_create': True,
        'device_id': device_id,
    }
    
    return render(request, 'maintenance/cmms/pm_schedule_form.html', context)

@login_required
def pm_schedule_detail(request, schedule_id):
    """عرض تفاصيل جدول الصيانة الوقائية"""
    schedule = get_object_or_404(PreventiveMaintenanceSchedule, id=schedule_id)
    history = PMScheduleHistory.objects.filter(pm_schedule=schedule).order_by('-created_at')
    
    # التحقق من صلاحيات المستخدم
    if not request.user.is_superuser and not request.user.groups.filter(name__in=['Supervisor', 'Technician']).exists():
        if hasattr(request.user, 'department') and schedule.device.department != request.user.department:
            messages.error(request, 'ليس لديك صلاحية لعرض هذا الجدول')
            return redirect('pm_schedule_list')
    
    # حساب موعد الصيانة القادم
    next_maintenance_date = None
    if schedule.status == 'active':
        next_maintenance_date = schedule.next_due_date
    
    # إحصائيات أوامر الشغل
    work_orders = WorkOrder.objects.filter(pm_schedule_history__pm_schedule=schedule)
    total_work_orders = work_orders.count()
    completed_work_orders = work_orders.filter(status__in=['closed', 'qa_verified']).count()
    cancelled_work_orders = work_orders.filter(status='cancelled').count()
    active_work_orders = total_work_orders - completed_work_orders - cancelled_work_orders
    
    # حساب نسبة الالتزام بالجدول
    compliance_rate = 0
    if total_work_orders > 0:
        compliance_rate = round((completed_work_orders / total_work_orders) * 100)
    
    context = {
        'schedule': schedule,
        'history': history,
        'next_maintenance_date': next_maintenance_date,
        'total_work_orders': total_work_orders,
        'completed_work_orders': completed_work_orders,
        'cancelled_work_orders': cancelled_work_orders,
        'active_work_orders': active_work_orders,
        'compliance_rate': compliance_rate,
    }
    
    return render(request, 'maintenance/cmms/pm_schedule_detail.html', context)

@login_required
def pm_schedule_update(request, schedule_id):
    """تحديث جدول الصيانة الوقائية"""
    pm_schedule = get_object_or_404(PreventiveMaintenanceSchedule, id=schedule_id)
    
    # التحقق من صلاحيات المستخدم
    if not request.user.is_superuser and not request.user.groups.filter(name='Supervisor').exists():
        messages.error(request, 'ليس لديك صلاحية لتعديل جداول الصيانة الوقائية')
        return redirect('pm_schedule_detail', schedule_id=pm_schedule.id)
    
    if request.method == 'POST':
        form = PMScheduleForm(request.POST, instance=pm_schedule, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم تحديث جدول الصيانة الوقائية بنجاح')
            return redirect('pm_schedule_detail', schedule_id=pm_schedule.id)
    else:
        form = PMScheduleForm(instance=pm_schedule, user=request.user)
    
    context = {
        'form': form,
        'pm_schedule': pm_schedule,
        'is_create': False,
    }
    
    return render(request, 'maintenance/cmms/pm_schedule_form.html', context)

@login_required
def pm_schedule_delete(request, schedule_id):
    """حذف جدول الصيانة الوقائية"""
    pm_schedule = get_object_or_404(PreventiveMaintenanceSchedule, id=schedule_id)
    
    # التحقق من صلاحيات المستخدم
    if not request.user.is_superuser:
        messages.error(request, 'ليس لديك صلاحية لحذف جداول الصيانة الوقائية')
        return redirect('pm_schedule_detail', schedule_id=pm_schedule.id)
    
    pm_schedule.delete()
    messages.success(request, 'تم حذف جدول الصيانة الوقائية بنجاح')
    return redirect('pm_schedule_list')

@login_required
def pm_schedule_generate_wo(request, schedule_id):
    """إنشاء أمر عمل يدوياً من جدول الصيانة الوقائية"""
    pm_schedule = get_object_or_404(PreventiveMaintenanceSchedule, id=schedule_id)
    
    # التحقق من صلاحيات المستخدم
    if not request.user.is_superuser and not request.user.groups.filter(name='Supervisor').exists():
        messages.error(request, 'ليس لديك صلاحية لإنشاء أوامر عمل')
        return redirect('pm_schedule_detail', schedule_id=pm_schedule.id)
    
    # إنشاء أمر العمل
    try:
        work_order = pm_schedule.generate_work_order()
        messages.success(request, 'تم إنشاء أمر العمل بنجاح')
        return redirect('work_order_detail', wo_id=work_order.id)
    except Exception as e:
        messages.error(request, f'حدث خطأ أثناء إنشاء أمر العمل: {str(e)}')
        return redirect('pm_schedule_detail', schedule_id=pm_schedule.id)

@login_required
def pm_schedule_toggle_status(request, schedule_id):
    """تفعيل/تعطيل جدول الصيانة الوقائية"""
    pm_schedule = get_object_or_404(PreventiveMaintenanceSchedule, id=schedule_id)
    
    # التحقق من صلاحيات المستخدم
    if not request.user.is_superuser and not request.user.groups.filter(name='Supervisor').exists():
        messages.error(request, 'ليس لديك صلاحية لتغيير حالة جداول الصيانة الوقائية')
        return redirect('pm_schedule_detail', schedule_id=pm_schedule.id)
    
    # تغيير الحالة
    if pm_schedule.status == 'active':
        pm_schedule.status = 'inactive'
        messages.success(request, 'تم تعطيل جدول الصيانة الوقائية بنجاح')
    elif pm_schedule.status == 'inactive':
        pm_schedule.status = 'active'
        messages.success(request, 'تم تفعيل جدول الصيانة الوقائية بنجاح')
    
    pm_schedule.save()
    return redirect('pm_schedule_detail', schedule_id=pm_schedule.id)