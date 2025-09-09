"""
ملف views_cmms.py - نظام إدارة الصيانة المحوسب (CMMS)

هذا الملف بيحتوي على كل الـ views اللي بتتعامل مع نظام CMMS في المستشفى:
- إدارة بلاغات الصيانة (Service Requests)
- إدارة أوامر الشغل (Work Orders)
- إدارة خطط العمل (Job Plans)
- إدارة الصيانة الوقائية (Preventive Maintenance)
- إدارة اتفاقيات مستوى الخدمة (SLA)
- داشبورد الفنيين
- APIs للموبايل والواجهة الأمامية

النظام بيسمح بتتبع كامل لعمليات الصيانة من البلاغ لحد الإصلاح
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q, Sum
from django.http import JsonResponse
from django.urls import reverse
from django.core.paginator import Paginator
from django.views.decorators.csrf import csrf_exempt

from .models import (Device, ServiceRequest, WorkOrder, JobPlan, JobPlanStep, 
                     PreventiveMaintenanceSchedule, SLADefinition, SR_TYPE_CHOICES, WO_STATUS_CHOICES,
                     WorkOrderPart, SparePart, SparePartRequest)
from .forms_cmms import (ServiceRequestForm, WorkOrderForm, WorkOrderUpdateForm, 
                        SLADefinitionForm, JobPlanForm, JobPlanStepForm, PMScheduleForm,
                        WorkOrderPartRequestForm, WorkOrderPartIssueForm)
from .forms import SparePartRequestForm

# ========================================
# بلاغات الصيانة (Service Requests)
# ========================================

@login_required
def service_request_list(request):
    """
    عرض قائمة البلاغات مع إمكانية الفلترة والبحث
    
    الوظائف:
    - عرض البلاغات حسب صلاحيات المستخدم
    - فلترة حسب الحالة ونوع البلاغ والقسم
    - بحث في العنوان والوصف واسم الجهاز
    - ترتيب النتائج حسب التاريخ
    """
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
        'status_choices': [
            ('new', 'جديد'),
            ('assigned', 'تم التعيين'),
            ('in_progress', 'قيد التنفيذ'),
            ('on_hold', 'معلق'),
            ('resolved', 'تم الحل'),
            ('closed', 'مغلق'),
            ('cancelled', 'ملغي'),
        ],
        'request_type_choices': [
            ('breakdown', 'عطل'),
            ('preventive', 'صيانة وقائية'),
            ('inspection', 'فحص'),
            ('calibration', 'معايرة'),
            ('upgrade', 'ترقية'),
            ('installation', 'تركيب'),
        ],
    }
    
    # Debug: Add a simple test context
    context['debug_message'] = 'View is working'
    context['service_requests_count'] = service_requests.count()
    
    return render(request, 'maintenance/cmms/service_request_list.html', context)

@login_required
def service_request_create(request):
    """
    إنشاء بلاغ صيانة جديد
    
    الوظائف:
    - إنشاء بلاغ جديد من المستخدم
    - ربط البلاغ بجهاز معين (لو تم تحديده)
    - حفظ البلاغ مع المستخدم المنشئ
    """
    # إذا تم تحديد جهاز من قبل
    device_id = request.GET.get('device')
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
            return redirect('maintenance:cmms:service_request_detail', sr_id=service_request.id)
    else:
        form = ServiceRequestForm(user=request.user, initial=initial_data)
    
    context = {
        'form': form,
        'device_id': device_id,
    }
    
    return render(request, 'maintenance/cmms/service_request_create.html', context)

@login_required
def service_request_detail(request, sr_id):
    """
    عرض تفاصيل البلاغ وأوامر الشغل المرتبطة
    
    الوظائف:
    - عرض تفاصيل كاملة للبلاغ
    - عرض أوامر الشغل المرتبطة
    - التحقق من صلاحيات المستخدم
    - نموذج إنشاء أمر شغل جديد
    """
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
            return redirect('maintenance:cmms:work_order_detail', wo_id=work_order.id)
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
    """
    تحديث بيانات البلاغ
    
    الوظائف:
    - تعديل بيانات البلاغ الموجود
    - التحقق من صلاحيات المستخدم للتعديل
    - حفظ التعديلات وعرض رسالة نجاح
    """
    service_request = get_object_or_404(ServiceRequest, id=sr_id)
    
    # التحقق من صلاحية المستخدم لتعديل البلاغ
    if not request.user.is_superuser and service_request.reporter != request.user:
        if not request.user.groups.filter(name='Supervisor').exists():
            messages.error(request, 'ليس لديك صلاحية لتعديل هذا البلاغ')
            return redirect('maintenance:cmms:service_request_detail', sr_id=service_request.id)
    
    if request.method == 'POST':
        form = ServiceRequestForm(request.POST, instance=service_request, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم تحديث البلاغ بنجاح')
            return redirect('maintenance:cmms:service_request_detail', sr_id=service_request.id)
    else:
        form = ServiceRequestForm(instance=service_request, user=request.user)
    
    context = {
        'form': form,
        'service_request': service_request,
    }
    
    return render(request, 'maintenance/cmms/service_request_update.html', context)

@login_required
def service_request_close(request, sr_id):
    """
    إغلاق البلاغ
    
    الوظائف:
    - إغلاق البلاغ بعد انتهاء العمل عليه
    - التحقق من عدم وجود أوامر شغل مفتوحة
    - التحقق من صلاحيات المستخدم للإغلاق
    """
    service_request = get_object_or_404(ServiceRequest, id=sr_id)
    
    # التحقق من صلاحية المستخدم لإغلاق البلاغ
    if not request.user.is_superuser and not request.user.groups.filter(name='Supervisor').exists():
        messages.error(request, 'ليس لديك صلاحية لإغلاق هذا البلاغ')
        return redirect('maintenance:cmms:service_request_detail', sr_id=service_request.id)
    
    # التحقق من عدم وجود أوامر شغل مفتوحة
    open_work_orders = service_request.work_orders.filter(
        status__in=['new', 'assigned', 'in_progress', 'wait_parts', 'on_hold', 'resolved']
    ).exists()
    
    if open_work_orders:
        messages.error(request, 'لا يمكن إغلاق البلاغ لوجود أوامر شغل مفتوحة')
        return redirect('maintenance:cmms:service_request_detail', sr_id=service_request.id)
    
    service_request.status = 'closed'
    service_request.closed_at = timezone.now()
    service_request.save()
    
    messages.success(request, 'تم إغلاق البلاغ بنجاح')
    return redirect('maintenance:cmms:service_request_detail', sr_id=service_request.id)

# ========================================
# أوامر الشغل (Work Orders)
# ========================================

@login_required
def work_order_list(request):
    """
    عرض قائمة أوامر الشغل مع إمكانية الفلترة والبحث
    
    الوظائف:
    - عرض أوامر الشغل حسب صلاحيات المستخدم
    - فلترة حسب الحالة والفني المسؤول والقسم
    - بحث في العنوان والوصف واسم الجهاز
    - ترتيب النتائج حسب التاريخ
    """
    # هنا بنجيب أوامر الشغل حسب صلاحيات المستخدم مع معلومات الجهاز والقسم
    if request.user.is_superuser:
        # المدير يشوف كل أوامر الشغل
        work_orders = WorkOrder.objects.select_related('service_request__device__department', 'assignee').all()
    elif request.user.groups.filter(name='Supervisor').exists():
        # المشرف يشوف أوامر شغل قسمه
        if hasattr(request.user, 'department'):
            work_orders = WorkOrder.objects.select_related('service_request__device__department', 'assignee').filter(service_request__device__department=request.user.department)
        else:
            work_orders = WorkOrder.objects.none()
    elif request.user.role == 'technician':
        # الفني يشوف أوامر الشغل المسندة إليه
        work_orders = WorkOrder.objects.select_related('service_request__device__department', 'assignee').filter(assignee=request.user)
    else:
        # المستخدم العادي يشوف أوامر الشغل المرتبطة ببلاغاته
        work_orders = WorkOrder.objects.select_related('service_request__device__department', 'assignee').filter(service_request__reporter=request.user)
    
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
        'status_choices': [
            ('new', 'جديد'),
            ('assigned', 'تم التعيين'),
            ('in_progress', 'جاري العمل'),
            ('wait_parts', 'انتظار قطع غيار'),
            ('on_hold', 'معلق'),
            ('resolved', 'تم الحل'),
            ('qa_verified', 'تم التحقق'),
            ('closed', 'مغلق'),
            ('cancelled', 'ملغي'),
        ],
    }
    
    return render(request, 'maintenance/cmms/work_order_list.html', context)

@login_required
def work_order_detail(request, wo_id):
    """
    عرض تفاصيل أمر الشغل والتعليقات
    
    الوظائف:
    - عرض تفاصيل كاملة لأمر الشغل
    - عرض التعليقات المرتبطة
    - التحقق من صلاحيات المستخدم
    - تحديث حالة أمر الشغل
    - تحديث حالة الجهاز
    - عرض قطع الغيار المطلوبة
    """
    work_order = get_object_or_404(WorkOrder, id=wo_id)
    comments = work_order.comments.all().order_by('created_at')
    
    # تحديد صلاحيات المستخدم
    is_doctor = hasattr(request.user, 'role') and request.user.role == 'doctor'
    is_technician = hasattr(request.user, 'role') and request.user.role == 'technician'
    is_hospital_manager = hasattr(request.user, 'role') and request.user.role in ['hospital_manager', 'super_admin']
    
    # التحقق من صلاحية المستخدم لعرض أمر الشغل
    if not (is_technician or is_hospital_manager or is_doctor or request.user.is_superuser):
        if work_order.assignee != request.user and work_order.service_request.reporter != request.user:
            if hasattr(request.user, 'department') and work_order.service_request.device.department != request.user.department:
                messages.error(request, 'ليس لديك صلاحية لعرض أمر الشغل هذا')
                return redirect('work_order_list')
    
    # صلاحيات التعديل (للفنيين والمسؤولين فقط - الأطباء لا يمكنهم التعديل)
    can_edit = is_technician or is_hospital_manager or request.user.is_superuser
    
    # تحقق من إن كان المستخدم يقدر يحدث الحالة
    can_update_status = can_edit  # فقط الفنيين والمسؤولين يمكنهم تحديث الحالة
    
    # صلاحيات إدارة قطع الغيار (للفنيين والمسؤولين فقط)
    can_request_parts = can_edit
    can_issue_parts = is_hospital_manager or request.user.is_superuser
    
    # معالجة النماذج المرسلة
    if request.method == 'POST':
        # إذا كان الطبيب يحاول تعيين فني
        if is_doctor and 'assign_technician' in request.POST:
            # سيتم التعامل مع تعيين الفني في دالة منفصلة
            pass
        
        # الفنيون والمسؤولون فقط يمكنهم تحديث حالة أمر الشغل
        elif can_edit and 'update_status' in request.POST:
            update_form = WorkOrderUpdateForm(request.POST, instance=work_order, user=request.user)
            if update_form.is_valid():
                # تحديث حالة أمر الشغل
                work_order = update_form.save()
                
                # تحديث التكاليف تلقائياً عند اختيار "تم الحل"
                if work_order.status == 'completed':
                    work_order.update_costs()
                
                # إضافة تعليق تلقائي عند تغيير الحالة
                if 'status' in update_form.changed_data:
                    comment_text = f"تم تغيير حالة أمر الشغل إلى: {work_order.get_status_display()}"
                    # سيتم إضافة التعليق عند تفعيل نموذج التعليقات
                
                messages.success(request, 'تم تحديث حالة أمر الشغل بنجاح')
                return redirect('maintenance:cmms:work_order_detail', wo_id=work_order.id)
        
        # تحديث حالة الجهاز (للفنيين والمسؤولين فقط)
        elif can_edit and 'update_device_status' in request.POST:
            if work_order.service_request and work_order.service_request.device:
                device = work_order.service_request.device
                old_status = device.get_status_display()
                device.status = 'working'
                device.save()
                
                messages.success(request, f'تم تغيير حالة الجهاز من "{old_status}" إلى "يعمل" بنجاح')
                return redirect('maintenance:cmms:work_order_detail', wo_id=work_order.id)
        
        elif not can_edit and not is_doctor:
            messages.error(request, 'ليس لديك صلاحية لإجراء هذا الإجراء')
    else:
        update_form = WorkOrderUpdateForm(instance=work_order, user=request.user)
    
    # نموذج التعليقات
    from .forms_cmms import WorkOrderCommentForm
    comment_form = WorkOrderCommentForm()
    
    # جلب قطع الغيار المطلوبة من WorkOrderPart وSparePartRequest
    parts_requested = work_order.parts_used.all().order_by('-requested_at')
    spare_part_requests = work_order.spare_part_requests.all().order_by('-created_at')
    
    # إحصائيات قطع الغيار
    spare_requests_stats = {
        'total_requested': spare_part_requests.count(),
        'pending': spare_part_requests.filter(status='pending').count(),
        'approved': spare_part_requests.filter(status='approved').count(),
        'fulfilled': spare_part_requests.filter(status='fulfilled').count(),
        'rejected': spare_part_requests.filter(status='rejected').count(),
    }
    
    parts_stats = {
        'total_requested': parts_requested.count(),
        'total_issued': parts_requested.filter(status='issued').count(),
        'total_cost': parts_requested.aggregate(total=Sum('total_cost'))['total'] or 0,
        'spare_requests_stats': spare_requests_stats,
    }
    
    # Check if device needs status change from inspection to working
    device_needs_status_change = (
        work_order.service_request and 
        work_order.service_request.device and 
        work_order.service_request.device.status == 'needs_check' and
        work_order.status in ['resolved', 'qa_verified', 'closed']
    )
    
    context = {
        'work_order': work_order,
        'comments': comments,
        'status_form': update_form,
        'comment_form': comment_form,
        'can_update_status': can_update_status,
        'can_edit': can_edit,
        'is_doctor': is_doctor,
        'is_technician': is_technician,
        'is_hospital_manager': is_hospital_manager,
        'device_needs_status_change': device_needs_status_change,
        'parts_requested': parts_requested,
        'spare_part_requests': spare_part_requests,
        'parts_stats': parts_stats,
        'can_request_parts': can_request_parts,
        'can_issue_parts': can_issue_parts,
    }
    
    # اختيار التمبليت حسب دور المستخدم
    if is_doctor or (hasattr(request.user, 'role') and request.user.role == 'nurse'):
        template_name = 'maintenance/work_order_detail.html'  # تمبليت مبسط للأطباء والممرضين
    else:
        template_name = 'maintenance/cmms/work_order_detail.html'  # تمبليت كامل للفنيين والمسؤولين
    
    return render(request, template_name, context)

@login_required
def work_order_create(request):
    """
    إنشاء أمر شغل جديد
    
    الوظائف:
    - إنشاء أمر شغل من بلاغ موجود
    - ربط أمر الشغل بتوقف الجهاز (downtime)
    - التحقق من صلاحيات المستخدم
    - ربط التوقف بأمر الشغل
    """
    # التحقق من وجود بلاغ مرتبط
    service_request_id = request.GET.get('service_request')
    service_request = None
    if service_request_id:
        service_request = get_object_or_404(ServiceRequest, id=service_request_id)
        
        # التحقق من صلاحية المستخدم لإنشاء أمر شغل لهذا البلاغ
        if not request.user.is_superuser and not request.user.groups.filter(name='Supervisor').exists():
            if hasattr(request.user, 'department') and service_request.device.department != request.user.department:
                messages.error(request, 'ليس لديك صلاحية لإنشاء أمر شغل لهذا البلاغ')
                return redirect('maintenance:service_request_list')
    
    # التحقق من وجود توقف مرتبط (downtime)
    downtime_id = request.GET.get('downtime')
    downtime = None
    device_id = request.GET.get('device')
    
    # إذا كان هناك توقف، نحصل على معلوماته
    if downtime_id and device_id:
        # استخدام نموذج DeviceDowntime الموجود في المشروع
        from .models import DeviceDowntime
        try:
            downtime = DeviceDowntime.objects.get(id=downtime_id, device_id=device_id)
        except:
            # إذا لم يتم العثور على التوقف، نتجاهله
            pass
    
    if request.method == 'POST':
        wo_form = WorkOrderForm(request.POST, user=request.user, service_request=service_request)
        if wo_form.is_valid():
            work_order = wo_form.save(commit=False)
            if service_request:
                work_order.service_request = service_request
            work_order.created_by = request.user
            work_order.save()
            
            # إذا كان هناك توقف، نربطه بأمر الشغل
            if downtime:
                downtime.related_work_order = work_order
                downtime.save()
            
            messages.success(request, 'تم إنشاء أمر الشغل بنجاح')
            return redirect('maintenance:cmms:work_order_detail', wo_id=work_order.id)
    else:
        wo_form = WorkOrderForm(user=request.user, service_request=service_request)
        
        # إذا كان هناك توقف، نضيف وصفه إلى وصف أمر الشغل
        if downtime and not wo_form.initial.get('description'):
            wo_form.initial['description'] = f"معالجة توقف الجهاز: {downtime.reason}\n\nتفاصيل التوقف: {downtime.details}"
    
    context = {
        'form': wo_form,
        'service_request': service_request,
        'downtime': downtime,
    }
    
    return render(request, 'maintenance/cmms/work_order_form.html', context)

@login_required
def work_order_assign(request, wo_id):
    """
    تعيين فني لأمر الشغل
    
    الوظائف:
    - تعيين فني مسؤول لأمر الشغل
    - التحقق من صلاحيات المستخدم للتعيين
    - التحقق من حالة أمر الشغل
    - جلب قائمة الفنيين المتاحين
    """
    from django.contrib.auth import get_user_model
    from django.contrib.auth.models import Group
    
    User = get_user_model()
    work_order = get_object_or_404(WorkOrder, id=wo_id)
    
    # التحقق من صلاحية المستخدم لتعيين فني (الأطباء والمسؤولين)
    if not request.user.is_superuser and request.user.role not in ['hospital_manager', 'super_admin', 'doctor']:
        messages.error(request, 'ليس لديك صلاحية لتعيين فني')
        return redirect('maintenance:cmms:work_order_detail', wo_id=work_order.id)
    
    # التحقق من أن أمر الشغل في حالة تسمح بالتعيين
    if work_order.status not in ['new', 'assigned']:
        messages.error(request, 'لا يمكن تعيين فني لأمر شغل في هذه الحالة')
        return redirect('maintenance:cmms:work_order_detail', wo_id=work_order.id)
    
    # جلب قائمة الفنيين المتاحين (بناءً على الرول)
    available_technicians = User.objects.filter(
        role='technician',
        is_active=True
    ).order_by('first_name', 'last_name')
    
    if request.method == 'POST':
        assignee_id = request.POST.get('assignee')
        if assignee_id:
            try:
                assignee = User.objects.get(id=assignee_id)
                work_order.assignee = assignee
                work_order.status = 'assigned'
                work_order.save()
                
                # إضافة تعليق تلقائي (إذا كان WorkOrderComment موجود)
                try:
                    from .models import WorkOrderComment
                    WorkOrderComment.objects.create(
                        work_order=work_order,
                        user=request.user,
                        comment=f'تم تعيين {assignee.get_full_name() or assignee.username} كفني مسؤول'
                    )
                except:
                    pass  # تجاهل إذا لم يكن WorkOrderComment موجود
                
                messages.success(request, 'تم تعيين الفني بنجاح')
                return redirect('maintenance:cmms:work_order_detail', wo_id=work_order.id)
            except User.DoesNotExist:
                messages.error(request, 'الفني غير موجود')
        else:
            messages.error(request, 'يجب اختيار فني')
    
    context = {
        'work_order': work_order,
        'available_technicians': available_technicians,
    }
    
    return render(request, 'maintenance/cmms/work_order_assign.html', context)

# ========================================
# داشبورد الفني
# ========================================

@login_required
def technician_dashboard(request):
    """
    داشبورد خاص بالفني
    
    الوظائف:
    - عرض إحصائيات أوامر الشغل المسندة للفني
    - عرض أوامر الشغل الحديثة والعاجلة
    - عرض أوامر الشغل المتأخرة
    - إحصائيات سريعة عن الأداء
    """
    from django.contrib.auth import get_user_model
    from django.db.models import Count, Q
    from datetime import datetime, timedelta
    
    User = get_user_model()
    
    # التحقق من أن المستخدم فني
    if request.user.role != 'technician':
        messages.error(request, 'هذه الصفحة مخصصة للفنيين فقط')
        return redirect('/')
    
    # إحصائيات أوامر الشغل المسندة للفني
    my_work_orders = WorkOrder.objects.filter(assignee=request.user)
    
    # إحصائيات سريعة
    stats = {
        'total_assigned': my_work_orders.count(),
        'new_orders': my_work_orders.filter(status='new').count(),
        'in_progress': my_work_orders.filter(status='in_progress').count(),
        'on_hold': my_work_orders.filter(status='on_hold').count(),
        'completed_today': my_work_orders.filter(
            status__in=['resolved', 'qa_verified', 'closed'],
            updated_at__date=datetime.now().date()
        ).count(),
    }
    
    # أوامر الشغل الحديثة (آخر 10)
    recent_work_orders = my_work_orders.select_related(
        'service_request__device__department'
    ).order_by('-created_at')[:10]
    
    # أوامر الشغل العاجلة (high priority)
    urgent_work_orders = my_work_orders.filter(
        service_request__severity='critical',
        status__in=['new', 'assigned', 'in_progress']
    ).select_related('service_request__device__department')[:5]
    
    # أوامر الشغل المتأخرة (أكثر من 3 أيام)
    three_days_ago = datetime.now() - timedelta(days=3)
    overdue_work_orders = my_work_orders.filter(
        created_at__lt=three_days_ago,
        status__in=['new', 'assigned', 'in_progress']
    ).select_related('service_request__device__department')[:5]
    
    context = {
        'stats': stats,
        'recent_work_orders': recent_work_orders,
        'urgent_work_orders': urgent_work_orders,
        'overdue_work_orders': overdue_work_orders,
        'user': request.user,
    }
    
    return render(request, 'maintenance/cmms/technician_dashboard.html', context)

# ========================================
# إدارة اتفاقيات مستوى الخدمة (SLA)
# ========================================

@login_required
def sla_list(request):
    """
    عرض قائمة اتفاقيات مستوى الخدمة
    
    الوظائف:
    - عرض جميع اتفاقيات مستوى الخدمة مع البيانات الكاملة
    - التحقق من صلاحيات المستخدم للعرض
    - حساب إحصائيات SLA
    """
    # التحقق من صلاحية المستخدم
    if not request.user.is_superuser and not request.user.groups.filter(name='Supervisor').exists():
        messages.error(request, 'ليس لديك صلاحية لعرض اتفاقيات مستوى الخدمة')
        return redirect('maintenance:cmms:service_request_list')
    
    # جلب جميع SLAs مع البيانات المرتبطة
    slas = SLADefinition.objects.select_related('device_category').all().order_by('-created_at')
    
    # حساب الإحصائيات
    total_slas = slas.count()
    active_slas = slas.filter(is_active=True).count()
    
    # حساب متوسط أوقات الاستجابة والحل
    avg_response_time = 0
    avg_resolution_time = 0
    
    if slas.exists():
        total_response = sum([sla.response_time_hours for sla in slas if sla.response_time_hours])
        total_resolution = sum([sla.resolution_time_hours for sla in slas if sla.resolution_time_hours])
        
        avg_response_time = round(total_response / total_slas, 1) if total_slas > 0 else 0
        avg_resolution_time = round(total_resolution / total_slas, 1) if total_slas > 0 else 0
    
    # جلب بيانات مصفوفة SLA
    sla_matrix = []
    try:
        from .models import SLAMatrix
        sla_matrix = SLAMatrix.objects.select_related('device_category', 'sla_definition').all()
        print(f"DEBUG: SLA Matrix count: {sla_matrix.count()}")
        if sla_matrix.exists():
            first_matrix = sla_matrix.first()
            print(f"DEBUG: First matrix - Category: {first_matrix.device_category.name if first_matrix.device_category else 'None'}")
    except Exception as e:
        print(f"خطأ في جلب مصفوفة SLA: {e}")
        import traceback
        traceback.print_exc()
        sla_matrix = []
    
    context = {
        'slas': slas,
        'total_slas': total_slas,
        'active_slas': active_slas,
        'inactive_slas': total_slas - active_slas,
        'avg_response_time': avg_response_time,
        'avg_resolution_time': avg_resolution_time,
        'sla_matrix': sla_matrix,
        'total_matrix_entries': len(sla_matrix),
    }
    
    return render(request, 'maintenance/cmms/sla_list.html', context)

@login_required
def sla_create(request):
    """
    إنشاء اتفاقية مستوى خدمة جديدة
    
    الوظائف:
    - إنشاء اتفاقية مستوى خدمة جديدة
    - التحقق من صلاحيات المستخدم للإنشاء
    - عرض نموذج إنشاء SLA
    """
    # التحقق من صلاحية المستخدم
    if not request.user.is_superuser and not request.user.groups.filter(name='Supervisor').exists():
        messages.error(request, 'ليس لديك صلاحية لإنشاء اتفاقية مستوى خدمة')
        return redirect('maintenance:cmms:sla_list')
    
    if request.method == 'POST':
        form = SLADefinitionForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم إنشاء اتفاقية مستوى الخدمة بنجاح')
            return redirect('maintenance:cmms:sla_list')
    else:
        form = SLADefinitionForm()
    
    context = {
        'form': form,
    }
    
    return render(request, 'maintenance/cmms/sla_create.html', context)

@login_required
def sla_edit(request, sla_id):
    """
    تعديل اتفاقية مستوى خدمة
    
    الوظائف:
    - تعديل اتفاقية مستوى خدمة موجودة
    - التحقق من صلاحيات المستخدم للتعديل
    - عرض نموذج التعديل مع البيانات الحالية
    """
    sla = get_object_or_404(SLADefinition, id=sla_id)
    
    # التحقق من صلاحية المستخدم
    if not request.user.is_superuser and not request.user.groups.filter(name='Supervisor').exists():
        messages.error(request, 'ليس لديك صلاحية لتعديل اتفاقية مستوى خدمة')
        return redirect('maintenance:cmms:sla_list')
    
    if request.method == 'POST':
        form = SLADefinitionForm(request.POST, instance=sla)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم تحديث اتفاقية مستوى الخدمة بنجاح')
            return redirect('maintenance:cmms:sla_list')
    else:
        form = SLADefinitionForm(instance=sla)
    
    context = {
        'form': form,
        'sla': sla,
    }
    
    return render(request, 'maintenance/cmms/sla_edit.html', context)

@login_required
def sla_delete(request, sla_id):
    """
    حذف اتفاقية مستوى خدمة
    
    الوظائف:
    - حذف اتفاقية مستوى خدمة موجودة
    - التحقق من صلاحيات المستخدم للحذف
    - عرض تأكيد الحذف
    """
    sla = get_object_or_404(SLADefinition, id=sla_id)
    
    # التحقق من صلاحية المستخدم
    if not request.user.is_superuser and not request.user.groups.filter(name='Supervisor').exists():
        messages.error(request, 'ليس لديك صلاحية لحذف اتفاقية مستوى خدمة')
        return redirect('maintenance:cmms:sla_list')
    
    if request.method == 'POST':
        sla_name = sla.name
        sla.delete()
        messages.success(request, f'تم حذف اتفاقية مستوى الخدمة "{sla_name}" بنجاح')
        return redirect('maintenance:cmms:sla_list')
    
    context = {
        'sla': sla,
    }
    
    return render(request, 'maintenance/cmms/sla_delete.html', context)


@login_required
def sla_matrix_list(request):
    """
    عرض مصفوفة اتفاقيات مستوى الخدمة
    
    الوظائف:
    - عرض مصفوفة SLA حسب الشدة والتأثير
    - تنظيم المصفوفة في شكل جدول
    - التحقق من صلاحيات المستخدم للعرض
    """
    # التحقق من صلاحية المستخدم
    if not request.user.is_superuser and not request.user.groups.filter(name='Supervisor').exists():
        messages.error(request, 'ليس لديك صلاحية لعرض مصفوفة اتفاقيات مستوى الخدمة')
        return redirect('service_request_list')
    
    # sla_matrix = SLAMatrix.objects.all()
    sla_matrix = []  # Placeholder حتى يتم إنشاء نموذج SLAMatrix
    
    # تنظيم المصفوفة في شكل جدول
    # severity_choices = dict(SEVERITY_CHOICES)
    # impact_choices = dict(IMPACT_CHOICES)
    severity_choices = {'high': 'عالي', 'medium': 'متوسط', 'low': 'منخفض'}
    impact_choices = {'high': 'عالي', 'medium': 'متوسط', 'low': 'منخفض'}
    
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
    """
    إنشاء أو تحديث عنصر في مصفوفة اتفاقيات مستوى الخدمة
    """
    from .models import SLAMatrix, SLADefinition, DeviceCategory
    from django import forms
    
    # إنشاء Form مؤقت
    class SLAMatrixForm(forms.ModelForm):
        class Meta:
            model = SLAMatrix
            fields = ['device_category', 'severity', 'impact', 'priority', 'sla_definition']
            widgets = {
                'device_category': forms.Select(attrs={'class': 'form-control'}),
                'severity': forms.Select(attrs={'class': 'form-control'}),
                'impact': forms.Select(attrs={'class': 'form-control'}),
                'priority': forms.Select(attrs={'class': 'form-control'}),
                'sla_definition': forms.Select(attrs={'class': 'form-control'}),
            }
    
    if request.method == 'POST':
        form = SLAMatrixForm(request.POST)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, 'تم إضافة عنصر جديد لمصفوفة SLA بنجاح')
                return redirect('maintenance:cmms:sla_list')
            except Exception as e:
                messages.error(request, f'خطأ في حفظ البيانات: {str(e)}')
        else:
            messages.error(request, 'يرجى تصحيح الأخطاء في النموذج')
    else:
        form = SLAMatrixForm()
    
    context = {
        'form': form,
        'device_categories': DeviceCategory.objects.all(),
        'sla_definitions': SLADefinition.objects.all(),
    }
    
    return render(request, 'maintenance/cmms/sla_matrix_create.html', context)

@login_required
def sla_matrix_regenerate(request):
    """
    إعادة توليد مصفوفة SLA يدوياً
    """
    if request.method == 'POST':
        try:
            from .models import SLAMatrix, DeviceCategory, SLADefinition, SEVERITY_CHOICES, IMPACT_CHOICES, PRIORITY_CHOICES
            
            # حذف جميع مدخلات المصفوفة الموجودة
            SLAMatrix.objects.all().delete()
            
            # الحصول على جميع الفئات وتعريفات SLA الموجودة (المنشأة يدوياً)
            categories = DeviceCategory.objects.all()
            available_slas = list(SLADefinition.objects.all())
            
            if not available_slas:
                return JsonResponse({
                    'success': False,
                    'message': 'لا توجد تعريفات SLA. يرجى إنشاء تعريفات SLA أولاً.'
                })
            
            # إنشاء جميع التركيبات: عدد الفئات × 4 severity × 4 impact × عدد SLA
            severity_choices = [choice[0] for choice in SEVERITY_CHOICES]
            impact_choices = [choice[0] for choice in IMPACT_CHOICES]
            
            created_count = 0
            
            # إضافة priority_choices
            priority_choices = [choice[0] for choice in PRIORITY_CHOICES]
            
            for category in categories:
                for sla in available_slas:
                    # تحديد الأولوية المرتبطة بهذا SLA
                    sla_priority = sla.priority if sla.priority else 'medium'  # افتراضي متوسط
                    
                    for severity in severity_choices:
                        for impact in impact_choices:
                            # إنشاء مدخل فقط للأولوية المطابقة لأولوية SLA
                            SLAMatrix.objects.create(
                                device_category=category,
                                severity=severity,
                                impact=impact,
                                priority=sla_priority,
                                sla_definition=sla
                            )
                            created_count += 1  
            
            return JsonResponse({
                'success': True,
                'created_count': created_count,
                'message': f'تم إنشاء {created_count} مدخل جديد في مصفوفة SLA'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'طريقة غير مسموحة'})

# ========================================
# دمج مع الصفحات الموجودة
# ========================================

@login_required
def device_maintenance_history(request, device_id):
    """
    عرض تاريخ صيانة الجهاز مع إضافة البلاغات وأوامر الشغل
    
    الوظائف:
    - عرض سجل كامل لصيانة الجهاز
    - دمج سجلات الصيانة والبلاغات وأوامر الشغل
    - ترتيب الأنشطة حسب التاريخ
    - عرض تفاصيل كل نشاط
    """
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
    """
    عرض تفاصيل الجهاز مع إضافة معلومات CMMS
    
    الوظائف:
    - عرض تفاصيل الجهاز الأساسية
    - عرض البلاغات المفتوحة المرتبطة بالجهاز
    - عرض أوامر الشغل المفتوحة
    - دمج معلومات CMMS مع صفحة تفاصيل الجهاز
    """
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

# ========================================
# APIs لتطبيقات الموبايل أو الواجهة الأمامية
# ========================================

@login_required
def api_service_request_create(request):
    """
    API لإنشاء بلاغ جديد
    
    الوظائف:
    - إنشاء بلاغ جديد عبر API
    - التحقق من البيانات المطلوبة
    - ربط البلاغ بالجهاز والمستخدم
    """
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
    """
    API لتحديث حالة أمر الشغل
    
    الوظائف:
    - تحديث حالة أمر الشغل عبر API
    - التحقق من صلاحيات المستخدم
    - إضافة تعليق تلقائي عند تغيير الحالة
    - تسجيل من قام بالتحقق
    """
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
    """
    API لعرض ملف الجهاز الكامل (تاريخ الصيانة، البلاغات، أوامر الشغل)
    
    الوظائف:
    - عرض معلومات الجهاز الأساسية
    - عرض سجل الصيانة (آخر 10 سجلات)
    - عرض البلاغات (آخر 10 بلاغات)
    - عرض أوامر الشغل (آخر 10 أوامر)
    - حساب إحصائيات الأداء (MTTR)
    """
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
            status__in=['closed', 'qa_verified', 'resolved'],
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


# ========================================
# الصيانة الوقائية (Preventive Maintenance)
# ========================================

@login_required
def job_plan_list(request):
    """
    عرض قائمة خطط العمل
    
    الوظائف:
    - عرض جميع خطط العمل المتاحة
    - فلترة حسب البحث في الاسم والوصف
    - ترقيم الصفحات (10 خطط في الصفحة)
    - التحقق من صلاحيات المستخدم
    """
    # التحقق من صلاحيات المستخدم
    if not request.user.is_superuser and not request.user.groups.filter(name__in=['Supervisor', 'Technician']).exists():
        messages.error(request, 'ليس لديك صلاحية لعرض خطط العمل')
        return redirect('maintenance:dashboard:cmms_dashboard')
    
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
    """
    إنشاء خطة عمل جديدة
    
    الوظائف:
    - إنشاء خطة عمل جديدة
    - التحقق من صلاحيات المستخدم للإنشاء
    - ربط الخطة بالمستخدم المنشئ
    - عرض نموذج إنشاء الخطة
    """
    # التحقق من صلاحيات المستخدم
    if not request.user.is_superuser and not request.user.groups.filter(name='Supervisor').exists():
        messages.error(request, 'ليس لديك صلاحية لإنشاء خطط العمل')
        return redirect('maintenance:cmms:job_plan_list')
    
    if request.method == 'POST':
        form = JobPlanForm(request.POST)
        if form.is_valid():
            job_plan = form.save(commit=False)
            job_plan.created_by = request.user
            job_plan.save()
            
            messages.success(request, 'تم إنشاء خطة العمل بنجاح')
            return redirect('maintenance:cmms:job_plan_detail', plan_id=job_plan.id)
    else:
        form = JobPlanForm()
    
    context = {
        'form': form,
        'is_create': True,
    }
    
    return render(request, 'maintenance/cmms/job_plan_form.html', context)

@login_required
def job_plan_detail(request, plan_id):
    """
    عرض تفاصيل خطة العمل وخطواتها
    
    الوظائف:
    - عرض تفاصيل خطة العمل
    - عرض خطوات الخطة مرتبة حسب الرقم
    - عرض جداول الصيانة الوقائية المرتبطة
    - إضافة خطوات جديدة للخطة
    - تحديد رقم الخطوة تلقائياً
    """
    job_plan = get_object_or_404(JobPlan, id=plan_id)
    steps = job_plan.steps.all().order_by('step_number')
    pm_schedules = job_plan.pm_schedules.select_related('device', 'device__department', 'assigned_to').all().order_by('next_due_date')
    
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
            return redirect('maintenance:cmms:job_plan_detail', plan_id=job_plan.id)
    else:
        step_form = JobPlanStepForm()
    
    # Debug information
    debug_info = {
        'job_plan_id': job_plan.id,
        'job_plan_name': job_plan.name,
        'pm_schedules_count': pm_schedules.count(),
        'pm_schedules_list': [
            {
                'id': pm.id,
                'name': pm.name,
                'device_name': pm.device.name if pm.device else 'No Device',
                'job_plan_id': pm.job_plan_id
            } for pm in pm_schedules
        ]
    }
    
    context = {
        'job_plan': job_plan,
        'steps': steps,
        'pm_schedules': pm_schedules,
        'step_form': step_form,
        'debug_info': debug_info,
    }
    
    return render(request, 'maintenance/cmms/job_plan_detail.html', context)

@login_required
def job_plan_update(request, plan_id):
    """
    تحديث خطة العمل
    
    الوظائف:
    - تحديث خطة عمل موجودة
    - التحقق من صلاحيات المستخدم للتعديل
    - عرض نموذج التعديل مع البيانات الحالية
    - حفظ التعديلات وعرض رسالة نجاح
    """
    job_plan = get_object_or_404(JobPlan, id=plan_id)
    
    # التحقق من صلاحيات المستخدم
    if not request.user.is_superuser and not request.user.groups.filter(name='Supervisor').exists():
        messages.error(request, 'ليس لديك صلاحية لتعديل خطط العمل')
        return redirect('maintenance:cmms:job_plan_detail', plan_id=job_plan.id)
    
    if request.method == 'POST':
        form = JobPlanForm(request.POST, instance=job_plan)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم تحديث خطة العمل بنجاح')
            return redirect('maintenance:cmms:job_plan_detail', plan_id=job_plan.id)
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
    """
    حذف خطة العمل
    
    الوظائف:
    - حذف خطة عمل موجودة
    - التحقق من صلاحيات المستخدم للحذف
    - التحقق من عدم وجود جداول صيانة مرتبطة
    - عرض رسالة نجاح بعد الحذف
    """
    job_plan = get_object_or_404(JobPlan, id=plan_id)
    
    # التحقق من صلاحيات المستخدم
    if not request.user.is_superuser:
        messages.error(request, 'ليس لديك صلاحية لحذف خطط العمل')
        return redirect('maintenance:cmms:job_plan_detail', plan_id=job_plan.id)
    
    # التحقق من عدم وجود جداول صيانة مرتبطة
    if job_plan.pm_schedules.exists():
        messages.error(request, 'لا يمكن حذف خطة العمل لوجود جداول صيانة مرتبطة بها')
        return redirect('maintenance:cmms:job_plan_detail', plan_id=job_plan.id)
    
    job_plan.delete()
    messages.success(request, 'تم حذف خطة العمل بنجاح')
    return redirect('maintenance:cmms:job_plan_list')

@login_required
def job_plan_add_step(request, plan_id):
    """
    إضافة خطوة جديدة لخطة العمل
    
    الوظائف:
    - إضافة خطوة جديدة لخطة عمل موجودة
    - التحقق من صلاحيات المستخدم للإضافة
    - معالجة نموذج إضافة الخطوة
    - العودة لصفحة تعديل الخطة
    """
    job_plan = get_object_or_404(JobPlan, id=plan_id)
    
    # التحقق من صلاحيات المستخدم
    if not request.user.is_superuser and not request.user.groups.filter(name='Supervisor').exists():
        messages.error(request, 'ليس لديك صلاحية لإضافة خطوات العمل')
        return redirect('maintenance:cmms:job_plan_update', plan_id=job_plan.id)
    
    if request.method == 'POST':
        step_id = request.POST.get('step_id')
        step_number = request.POST.get('step_number')
        title = request.POST.get('title', '')
        description = request.POST.get('description')
        estimated_minutes = request.POST.get('estimated_minutes')
        
        if step_id:
            # تعديل خطوة موجودة
            step = get_object_or_404(JobPlanStep, id=step_id, job_plan=job_plan)
            step.step_number = step_number
            step.title = title
            step.description = description
            step.estimated_minutes = estimated_minutes
            step.save()
            messages.success(request, 'تم تحديث الخطوة بنجاح')
        else:
            # إضافة خطوة جديدة
            # التحقق من رقم الخطوة وتجنب التكرار
            if not step_number:
                # إذا لم يتم تحديد رقم الخطوة، استخدم الرقم التالي المتاح
                last_step = JobPlanStep.objects.filter(job_plan=job_plan).order_by('-step_number').first()
                step_number = (last_step.step_number + 1) if last_step else 1
            else:
                step_number = int(step_number)
                # التحقق من وجود خطوة بنفس الرقم
                if JobPlanStep.objects.filter(job_plan=job_plan, step_number=step_number).exists():
                    messages.error(request, f'يوجد بالفعل خطوة برقم {step_number}. يرجى اختيار رقم آخر.')
                    return redirect('maintenance:cmms:job_plan_update', plan_id=job_plan.id)
            
            JobPlanStep.objects.create(
                job_plan=job_plan,
                step_number=step_number,
                title=title,
                description=description,
                estimated_minutes=estimated_minutes
            )
            messages.success(request, 'تم إضافة الخطوة بنجاح')
    
    return redirect('maintenance:cmms:job_plan_update', plan_id=job_plan.id)

@login_required
def job_plan_step_delete(request, step_id):
    """
    حذف خطوة من خطة العمل
    
    الوظائف:
    - حذف خطوة من خطة عمل موجودة
    - التحقق من صلاحيات المستخدم للحذف
    - العودة لصفحة تفاصيل الخطة
    - عرض رسالة نجاح بعد الحذف
    """
    step = get_object_or_404(JobPlanStep, id=step_id)
    job_plan = step.job_plan
    
    # التحقق من صلاحيات المستخدم
    if not request.user.is_superuser and not request.user.groups.filter(name='Supervisor').exists():
        messages.error(request, 'ليس لديك صلاحية لحذف خطوات العمل')
        return redirect('maintenance:cmms:job_plan_detail', plan_id=job_plan.id)
    
    step.delete()
    messages.success(request, 'تم حذف الخطوة بنجاح')
    return redirect('maintenance:cmms:job_plan_detail', plan_id=job_plan.id)

@login_required
def pm_schedule_list(request):
    """
    عرض قائمة جداول الصيانة الوقائية
    
    الوظائف:
    - عرض جميع جداول الصيانة الوقائية
    - فلترة حسب الحالة والقسم
    - بحث في الاسم والوصف واسم الجهاز
    - ترقيم الصفحات (10 جداول في الصفحة)
    - التحقق من صلاحيات المستخدم
    """
    # التحقق من صلاحيات المستخدم - السماح للجميع بالعرض للتشخيص
    # if not request.user.is_superuser and not request.user.groups.filter(name__in=['Supervisor', 'Technician']).exists():
    #     messages.error(request, 'ليس لديك صلاحية لعرض جداول الصيانة الوقائية')
    #     return redirect('dashboard')
    
    pm_schedules = PreventiveMaintenanceSchedule.objects.select_related(
        'device', 
        'device__department', 
        'device__device_type',
        'job_plan',
        'assigned_to',
        'created_by'
    ).order_by('next_due_date')
    
    # فلترة حسب الحالة
    status_filter = request.GET.get('status', '')
    if status_filter:
        if status_filter == 'active':
            pm_schedules = pm_schedules.filter(is_active=True)
        elif status_filter == 'inactive':
            pm_schedules = pm_schedules.filter(is_active=False)
    
    # فلترة حسب الجهاز
    device_filter = request.GET.get('device', '')
    if device_filter:
        pm_schedules = pm_schedules.filter(device_id=device_filter)
    
    # فلترة حسب التكرار
    frequency_filter = request.GET.get('frequency', '')
    if frequency_filter:
        pm_schedules = pm_schedules.filter(frequency=frequency_filter)
    
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
    
    # Calculate counts for dashboard cards
    all_schedules = PreventiveMaintenanceSchedule.objects.all()
    active_count = all_schedules.filter(is_active=True).count()
    inactive_count = all_schedules.filter(is_active=False).count()
    completed_count = 0  # This would need a completed field in the model
    total_count = all_schedules.count()
    
    # Get devices for filter dropdown
    from maintenance.models import Device
    devices = Device.objects.all()
    
    context = {
        'schedules': page_obj,  # Template expects 'schedules', not 'pm_schedules'
        'pm_schedules': page_obj,  # Keep both for compatibility
        'status_filter': status_filter,
        'device_filter': device_filter,
        'frequency_filter': frequency_filter,
        'department_filter': department_filter,
        'search_query': search_query,
        'status_choices': [('active', 'نشط'), ('inactive', 'غير نشط')],
        'active_count': active_count,
        'inactive_count': inactive_count,
        'completed_count': completed_count,
        'total_count': total_count,
        'devices': devices,
        'debug_info': {
            'total_schedules': total_count,
            'filtered_schedules': pm_schedules.count(),
            'user_role': getattr(request.user, 'role', 'No role'),
            'is_superuser': request.user.is_superuser,
            'user_groups': list(request.user.groups.values_list('name', flat=True)),
        }
    }
    
    return render(request, 'maintenance/cmms/pm_schedule_list.html', context)

@login_required
def pm_schedule_create(request):
    """
    إنشاء جدول صيانة وقائية جديد
    
    الوظائف:
    - إنشاء جدول صيانة وقائية جديد
    - ربط الجدول بجهاز معين (لو تم تحديده)
    - التحقق من صلاحيات المستخدم للإنشاء
    - ربط الجدول بالمستخدم المنشئ
    """
    # التحقق من صلاحيات المستخدم
    if not request.user.is_superuser and not request.user.groups.filter(name='Supervisor').exists():
        messages.error(request, 'ليس لديك صلاحية لإنشاء جداول الصيانة الوقائية')
        return redirect('maintenance:cmms:pm_schedule_list')
    
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
            
            # تعيين تاريخ الاستحقاق التالي إذا لم يكن محدداً
            if not pm_schedule.next_due_date:
                from datetime import date, timedelta
                if pm_schedule.start_date:
                    pm_schedule.next_due_date = pm_schedule.start_date
                else:
                    pm_schedule.next_due_date = date.today()
            
            pm_schedule.save()
            
            messages.success(request, 'تم إنشاء جدول الصيانة الوقائية بنجاح')
            return redirect('maintenance:cmms:pm_schedule_detail', schedule_id=pm_schedule.id)
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
    """
    عرض تفاصيل جدول الصيانة الوقائية
    
    الوظائف:
    - عرض تفاصيل جدول الصيانة الوقائية
    - عرض تاريخ الصيانة
    - حساب موعد الصيانة القادم
    - إحصائيات أوامر الشغل المرتبطة بالجدول
    - حساب نسبة الالتزام بالجدول
    """
    schedule = get_object_or_404(PreventiveMaintenanceSchedule, id=schedule_id)
    
    # التحقق من صلاحيات المستخدم
    if not request.user.is_superuser and not request.user.groups.filter(name__in=['Supervisor', 'Technician']).exists():
        if hasattr(request.user, 'department') and schedule.device.department != request.user.department:
            messages.error(request, 'ليس لديك صلاحية لعرض هذا الجدول')
            return redirect('pm_schedule_list')
    
    # حساب موعد الصيانة القادم
    next_maintenance_date = None
    if schedule.is_active and schedule.next_due_date:
        next_maintenance_date = schedule.next_due_date
    
    # إحصائيات أوامر الشغل المرتبطة بجدول الصيانة الوقائية المحدد
    work_orders = WorkOrder.objects.filter(
        pm_schedule=schedule
    )
    total_work_orders = work_orders.count()
    completed_work_orders = work_orders.filter(status__in=['resolved', 'qa_verified', 'closed']).count()
    cancelled_work_orders = work_orders.filter(status='cancelled').count()
    in_progress_work_orders = work_orders.filter(status__in=['new', 'assigned', 'in_progress', 'wait_parts', 'on_hold']).count()
    active_work_orders = in_progress_work_orders
    
    # حساب نسبة الالتزام بالجدول
    compliance_rate = 0
    if total_work_orders > 0:
        compliance_rate = round((completed_work_orders / total_work_orders) * 100)
    
    # استخدام أوامر الشغل كتاريخ للصيانة
    history = work_orders.order_by('-created_at')
    
    context = {
        'schedule': schedule,
        'history': history,
        'next_maintenance_date': next_maintenance_date,
        'total_work_orders': total_work_orders,
        'completed_work_orders': completed_work_orders,
        'cancelled_work_orders': cancelled_work_orders,
        'active_work_orders': active_work_orders,
        'compliance_rate': compliance_rate,
        'today': timezone.now().date(),
    }
    
    return render(request, 'maintenance/cmms/pm_schedule_detail.html', context)

@login_required
def pm_schedule_update(request, schedule_id):
    """
    تحديث جدول الصيانة الوقائية
    
    الوظائف:
    - تحديث جدول صيانة وقائية موجود
    - التحقق من صلاحيات المستخدم للتعديل
    - عرض نموذج التعديل مع البيانات الحالية
    - حفظ التعديلات وعرض رسالة نجاح
    """
    pm_schedule = get_object_or_404(PreventiveMaintenanceSchedule, id=schedule_id)
    
    # التحقق من صلاحيات المستخدم
    if not request.user.is_superuser and not request.user.groups.filter(name='Supervisor').exists():
        messages.error(request, 'ليس لديك صلاحية لتعديل جداول الصيانة الوقائية')
        return redirect('maintenance:cmms:pm_schedule_detail', schedule_id=pm_schedule.id)
    
    if request.method == 'POST':
        form = PMScheduleForm(request.POST, instance=pm_schedule, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم تحديث جدول الصيانة الوقائية بنجاح')
            return redirect('maintenance:cmms:pm_schedule_detail', schedule_id=pm_schedule.id)
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
    """
    حذف جدول الصيانة الوقائية
    
    الوظائف:
    - حذف جدول صيانة وقائية موجود
    - التحقق من صلاحيات المستخدم للحذف
    - عرض رسالة نجاح بعد الحذف
    """
    pm_schedule = get_object_or_404(PreventiveMaintenanceSchedule, id=schedule_id)
    
    # التحقق من صلاحيات المستخدم
    if not request.user.is_superuser:
        messages.error(request, 'ليس لديك صلاحية لحذف جداول الصيانة الوقائية')
        return redirect('maintenance:cmms:pm_schedule_detail', schedule_id=pm_schedule.id)
    
    pm_schedule.delete()
    messages.success(request, 'تم حذف جدول الصيانة الوقائية بنجاح')
    return redirect('maintenance:cmms:pm_schedule_list')

@login_required
def pm_schedule_generate_wo(request, schedule_id):
    """
    إنشاء أمر شغل يدوياً من جدول الصيانة الوقائية
    
    يتم استخدام هذا العرض لإنشاء أمر شغل فوري من جدول صيانة وقائية محدد.
    يتطلب صلاحيات مشرف أو مدير للوصول.
    
    المعاملات:
    - schedule_id: معرف جدول الصيانة الوقائية
    
    العمليات:
    - التحقق من صلاحيات المستخدم للإنشاء
    - معالجة الأخطاء وعرض رسائل مناسبة
    """
    pm_schedule = get_object_or_404(PreventiveMaintenanceSchedule, id=schedule_id)
    
    # التحقق من صلاحيات المستخدم
    if not request.user.is_superuser and not request.user.groups.filter(name='Supervisor').exists():
        messages.error(request, 'ليس لديك صلاحية لإنشاء أوامر عمل')
        return redirect('maintenance:cmms:pm_schedule_detail', schedule_id=pm_schedule.id)
    
    try:
        # استخدام الطريقة الموجودة في النموذج
        work_order = pm_schedule.generate_work_order()
        if work_order:
            messages.success(request, f'تم إنشاء أمر العمل بنجاح - رقم الأمر: {work_order.wo_number}')
            return redirect('maintenance:cmms:work_order_detail', wo_id=work_order.id)
        else:
            messages.warning(request, 'يوجد أمر عمل مفتوح بالفعل أو تم إكمال الصيانة اليوم')
            return redirect('maintenance:cmms:pm_schedule_detail', schedule_id=pm_schedule.id)
        
    except Exception as e:
        messages.error(request, f'حدث خطأ أثناء إنشاء أمر العمل: {str(e)}')
        return redirect('maintenance:cmms:pm_schedule_detail', schedule_id=pm_schedule.id)


@login_required
@csrf_exempt
def test_pm_generation(request):
    """
    اختبار إنشاء أوامر الصيانة الوقائية التلقائية
    """
    if not request.user.is_superuser:
        messages.error(request, 'ليس لديك صلاحية لاستخدام هذه الوظيفة')
        return redirect('maintenance:cmms:pm_schedule_list')
    
    try:
        from .signals import check_and_generate_pm_work_orders
        created_count = check_and_generate_pm_work_orders()
        
        if created_count > 0:
            messages.success(request, f'تم إنشاء {created_count} أمر صيانة وقائية جديد')
        else:
            messages.info(request, 'لا توجد جداول صيانة وقائية مستحقة حالياً')
            
        # عرض معلومات إضافية للتشخيص
        total_schedules = PreventiveMaintenanceSchedule.objects.count()
        active_schedules = PreventiveMaintenanceSchedule.objects.filter(is_active=True).count()
        
        from datetime import date
        today = date.today()
        due_schedules = PreventiveMaintenanceSchedule.objects.filter(
            is_active=True,
            next_due_date__lte=today
        ).count()
        
        # إضافة معلومات تشخيصية
        future_schedules = PreventiveMaintenanceSchedule.objects.filter(
            is_active=True,
            next_due_date__gt=today
        ).count()
        
        messages.info(request, f'إجمالي الجداول: {total_schedules} | النشطة: {active_schedules} | المستحقة: {due_schedules} | مستقبلية: {future_schedules}')
        messages.info(request, f'اليوم: {today} - النظام ينشئ أوامر شغل فقط للجداول المستحقة اليوم أو قبله')
        
    except Exception as e:
        messages.error(request, f'حدث خطأ أثناء اختبار إنشاء أوامر الصيانة: {str(e)}')
    
    return redirect('maintenance:cmms:pm_schedule_list')

@login_required
def pm_schedule_toggle_status(request, schedule_id):
    """
    تفعيل/تعطيل جدول الصيانة الوقائية
    
{{ ... }}
    الوظائف:
    - تبديل حالة جدول الصيانة الوقائية
    - تفعيل أو تعطيل الجدول
    - التحقق من صلاحيات المستخدم
    - عرض رسائل نجاح مناسبة
    """
    pm_schedule = get_object_or_404(PreventiveMaintenanceSchedule, id=schedule_id)
    
    # التحقق من صلاحيات المستخدم
    if not request.user.is_superuser and not request.user.groups.filter(name='Supervisor').exists():
        messages.error(request, 'ليس لديك صلاحية لتغيير حالة جداول الصيانة الوقائية')
        return redirect('maintenance:cmms:pm_schedule_detail', schedule_id=pm_schedule.id)
    
    # تغيير الحالة
    if pm_schedule.is_active:
        pm_schedule.is_active = False
        messages.success(request, 'تم تعطيل جدول الصيانة الوقائية بنجاح')
    else:
        pm_schedule.is_active = True
        messages.success(request, 'تم تفعيل جدول الصيانة الوقائية بنجاح')
    
    pm_schedule.save()
    return redirect('maintenance:cmms:pm_schedule_detail', schedule_id=pm_schedule.id)

@login_required
def work_order_update_status(request, wo_id):
    """
    تحديث حالة أمر الشغل
    
    الوظائف:
    - تحديث حالة أمر الشغل
    - إضافة ملاحظات الإنجاز
    - تسجيل وقت الإنجاز
    - التحقق من صحة الحالة الجديدة
    """
    work_order = get_object_or_404(WorkOrder, id=wo_id)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        completion_notes = request.POST.get('completion_notes', '')
        
        # Debug logging
        print(f"DEBUG: Received status: {new_status}")
        print(f"DEBUG: Current actual_start: {work_order.actual_start}")
        
        if new_status in ['new', 'assigned', 'in_progress', 'wait_parts', 'on_hold', 'resolved', 'qa_verified', 'closed', 'cancelled']:
            old_status = work_order.status
            work_order.status = new_status
            if completion_notes:
                work_order.completion_notes = completion_notes
            
            # تسجيل وقت البدء الفعلي عند تغيير الحالة إلى "جاري العمل"
            if new_status == 'in_progress' and not work_order.actual_start:
                work_order.actual_start = timezone.now()
                print(f"DEBUG: Set actual_start to: {work_order.actual_start}")
            
            # تسجيل وقت الانتهاء الفعلي عند الإنجاز
            if new_status in ['resolved', 'qa_verified', 'closed']:
                work_order.completed_at = timezone.now()
                if not work_order.actual_end:
                    work_order.actual_end = timezone.now()
                
                # حساب الساعات الفعلية إذا كان وقت البدء متوفر
                if work_order.actual_start and work_order.actual_end:
                    time_diff = work_order.actual_end - work_order.actual_start
                    work_order.actual_hours = round(time_diff.total_seconds() / 3600, 2)
                    print(f"DEBUG: Calculated actual_hours: {work_order.actual_hours}")
            
            # حفظ أمر العمل أولاً
            work_order.save()
            print(f"DEBUG: After save - actual_start: {work_order.actual_start}")
            
            # تحديث حالة الجهاز إلى "يعمل" عند إكمال أمر العمل (بعد الحفظ)
            if new_status in ['resolved', 'qa_verified', 'closed']:
                # الحصول على الجهاز من service_request أو pm_schedule
                device = None
                if work_order.service_request:
                    device = work_order.service_request.device
                elif work_order.pm_schedule:
                    device = work_order.pm_schedule.device
                
                if device:
                    print(f"DEBUG: Checking device {device.id} status: {device.status}")
                    
                    # التحقق من عدم وجود أوامر عمل أخرى مفتوحة (باستثناء الصيانة الوقائية والفحص)
                    other_open_orders = device.service_requests.exclude(
                        request_type__in=['preventive', 'inspection']
                    ).filter(
                        work_orders__status__in=['new', 'assigned', 'in_progress']
                    ).exclude(work_orders__id=work_order.id)
                    
                    print(f"DEBUG: Other open work orders (excluding preventive/inspection): {other_open_orders.count()}")
                    
                    if device.status == 'needs_maintenance' and not other_open_orders.exists():
                        print(f"DEBUG: Updating device {device.id} status to working")
                        device.status = 'working'
                        device.save()
                        print(f"DEBUG: Device {device.id} new status: {device.status}")
                        messages.success(request, f'تم تحديث حالة الجهاز {device.name} إلى "يعمل" بعد إكمال أمر العمل')
                    else:
                        print(f"DEBUG: Cannot update - other critical open orders exist")
                        for sr in other_open_orders:
                            for wo in sr.work_orders.filter(status__in=['new', 'assigned', 'in_progress']):
                                print(f"DEBUG: Critical open work order: WO {wo.id} - Status: {wo.status} - Type: {sr.request_type} - Title: {wo.title}")
                else:
                    print(f"DEBUG: Device status is not needs_maintenance: {device.status}")
            
            messages.success(request, f'تم تحديث حالة أمر الشغل من {old_status} إلى {new_status} بنجاح')
        else:
            messages.error(request, f'حالة غير صحيحة: {new_status}')
    
    return redirect('maintenance:cmms:work_order_detail', wo_id=work_order.id)

@login_required
def work_order_add_comment(request, wo_id):
    """
    إضافة تعليق لأمر الشغل
    
    الوظائف:
    - إضافة تعليق جديد لأمر الشغل باستخدام WorkOrderComment model
    - تسجيل التوقيت والمستخدم
    - التحقق من عدم إضافة تعليق فارغ
    """
    work_order = get_object_or_404(WorkOrder, id=wo_id)
    
    if request.method == 'POST':
        from .forms_cmms import WorkOrderCommentForm
        from .models import WorkOrderComment
        
        form = WorkOrderCommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.work_order = work_order
            comment.user = request.user
            comment.save()
            messages.success(request, 'تم إضافة التعليق بنجاح')
        else:
            messages.error(request, 'لا يمكن إضافة تعليق فارغ')
    
    return redirect('maintenance:cmms:work_order_detail', wo_id=work_order.id)

@login_required
def work_order_update_costs(request, wo_id):
    """تحديث تكاليف أمر الشغل تلقائياً"""
    work_order = get_object_or_404(WorkOrder, id=wo_id)
    
    # التحقق من صلاحية المستخدم
    if not request.user.is_superuser and not request.user.groups.filter(name__in=['Supervisor', 'Manager']).exists():
        if work_order.assignee != request.user:
            messages.error(request, 'ليس لديك صلاحية لتحديث تكاليف هذا الأمر')
            return redirect('maintenance:cmms:work_order_detail', wo_id=work_order.id)
    
    if request.method == 'POST':
        try:
            # الحصول على معدل الساعة من النموذج أو استخدام القيمة الافتراضية
            hourly_rate = float(request.POST.get('hourly_rate', 50))
            
            # تحديث التكاليف
            work_order.update_costs(hourly_rate)
            
            messages.success(request, f'تم تحديث التكاليف بنجاح - التكلفة الإجمالية: {work_order.total_cost} ريال')
        except Exception as e:
            messages.error(request, f'حدث خطأ أثناء تحديث التكاليف: {str(e)}')
    
    return redirect('maintenance:cmms:work_order_detail', wo_id=work_order.id)

# =============== Work Order Parts Management ===============
@login_required
def work_order_parts_list(request, wo_id):
    """عرض قائمة قطع الغيار المطلوبة لأمر الشغل"""
    work_order = get_object_or_404(WorkOrder, id=wo_id)
    
    # التحقق من صلاحية المستخدم
    if not request.user.is_superuser and not request.user.groups.filter(name='Supervisor').exists():
        if work_order.assignee != request.user and work_order.service_request.reporter != request.user:
            messages.error(request, 'ليس لديك صلاحية لعرض قطع الغيار لهذا الأمر')
            return redirect('maintenance:cmms:work_order_detail', wo_id=wo_id)
    
    parts_requested = work_order.parts_used.all().order_by('-requested_at')
    
    # صلاحيات المستخدم
    can_request_parts = (
        work_order.assignee == request.user or 
        request.user.is_superuser or 
        request.user.groups.filter(name='Supervisor').exists()
    )
    can_issue_parts = (
        request.user.is_superuser or 
        request.user.groups.filter(name='Supervisor').exists()
    )
    
    # إحصائيات قطع الغيار
    parts_stats = {
        'total_requested': parts_requested.count(),
        'total_issued': parts_requested.filter(status='issued').count(),
        'total_cost': parts_requested.aggregate(total=Sum('total_cost'))['total'] or 0,
    }
    
    context = {
        'work_order': work_order,
        'parts_requested': parts_requested,
        'can_request_parts': can_request_parts,
        'can_issue_parts': can_issue_parts,
        'parts_stats': parts_stats,
    }
    
    return render(request, 'maintenance/cmms/work_order_parts_list.html', context)

@login_required
def work_order_part_request(request, wo_id):
    """طلب قطع غيار جديدة لأمر الشغل - يربط بنظام إدارة المخزون"""
    work_order = get_object_or_404(WorkOrder, id=wo_id)
    
    # التحقق من صلاحية المستخدم
    if not request.user.is_superuser and not request.user.groups.filter(name='Supervisor').exists():
        if work_order.assignee != request.user:
            messages.error(request, 'ليس لديك صلاحية لطلب قطع غيار لهذا الأمر')
            return redirect('maintenance:cmms:work_order_detail', wo_id=wo_id)
    
    if request.method == 'POST':
        spare_part_id = request.POST.get('spare_part')
        quantity = int(request.POST.get('quantity', 1))
        priority = request.POST.get('priority', 'medium')
        reason = request.POST.get('reason', '')
        notes = request.POST.get('notes', '')
        
        if spare_part_id:
            spare_part = get_object_or_404(SparePart, id=spare_part_id)
            
            # إنشاء طلب قطعة غيار في نظام إدارة المخزون
            spare_request = SparePartRequest.objects.create(
                requester=request.user,
                spare_part=spare_part,
                quantity_requested=quantity,
                priority=priority,
                work_order=work_order,
                device=work_order.service_request.device if work_order.service_request else None,
                reason=reason or f'طلب قطعة غيار لأمر العمل {work_order.wo_number}',
                notes=notes
            )
            
            messages.success(request, f'تم إرسال طلب قطعة الغيار برقم {spare_request.request_number} بنجاح')
            return redirect('maintenance:cmms:work_order_detail', wo_id=work_order.id)
        else:
            messages.error(request, 'يرجى اختيار قطعة غيار')
    
    # قائمة قطع الغيار المتاحة
    spare_parts = SparePart.objects.filter(status='available').order_by('name')
    
    context = {
        'spare_parts': spare_parts,
        'work_order': work_order,
        'title': f'طلب قطع غيار لأمر العمل {work_order.wo_number}',
        'device': work_order.service_request.device if work_order.service_request else None,
    }
    
    return render(request, 'maintenance/request_spare_part.html', context)

@login_required
def work_order_part_issue(request, wo_id, part_id):
    """صرف قطع الغيار المطلوبة"""
    work_order = get_object_or_404(WorkOrder, id=wo_id)
    work_order_part = get_object_or_404(WorkOrderPart, id=part_id, work_order=work_order)
    
    # التحقق من صلاحية المستخدم
    if not request.user.is_superuser and not request.user.groups.filter(name='Supervisor').exists():
        messages.error(request, 'ليس لديك صلاحية لصرف قطع الغيار')
        return redirect('maintenance:cmms:work_order_parts_list', wo_id=work_order.id)
    
    if request.method == 'POST':
        form = WorkOrderPartIssueForm(request.POST, instance=work_order_part)
        if form.is_valid():
            part_request = form.save(commit=False)
            part_request.issued_by = request.user
            part_request.issued_at = timezone.now()
            part_request.status = 'issued'
            
            # تحديث المخزون
            spare_part = work_order_part.spare_part
            if spare_part.current_stock >= part_request.quantity_used:
                spare_part.current_stock -= part_request.quantity_used
                spare_part.save()
                
                # حساب التكلفة الإجمالية
                if spare_part.unit_cost:
                    part_request.total_cost = spare_part.unit_cost * part_request.quantity_used
                
                part_request.save()
                messages.success(request, 'تم صرف قطع الغيار بنجاح')
            else:
                messages.error(request, 'المخزون غير كافي لصرف الكمية المطلوبة')
                return redirect('maintenance:cmms:work_order_part_issue', wo_id=work_order.id, part_id=part_id)
            
            return redirect('maintenance:cmms:work_order_parts_list', wo_id=work_order.id)
    else:
        form = WorkOrderPartIssueForm(instance=work_order_part)
    
    context = {
        'form': form,
        'work_order': work_order,
        'work_order_part': work_order_part,
        'title': 'صرف قطع الغيار',
    }
    
    return render(request, 'maintenance/cmms/work_order_part_issue_form.html', context)

@login_required
def work_order_part_cancel(request, wo_id, part_id):
    """إلغاء طلب قطع غيار"""
    work_order = get_object_or_404(WorkOrder, id=wo_id)
    work_order_part = get_object_or_404(WorkOrderPart, id=part_id, work_order=work_order)
    
    # التحقق من صلاحية المستخدم
    if not request.user.is_superuser and not request.user.groups.filter(name='Supervisor').exists():
        if work_order.assignee != request.user:
            messages.error(request, 'ليس لديك صلاحية لإلغاء طلب قطع الغيار')
            return redirect('maintenance:cmms:work_order_parts_list', wo_id=work_order.id)
    
    # التحقق من أن الطلب لم يتم صرفه بعد
    if work_order_part.status != 'requested':
        messages.error(request, 'لا يمكن إلغاء طلب تم صرفه بالفعل')
        return redirect('maintenance:cmms:work_order_parts_list', wo_id=work_order.id)
    
    work_order_part.delete()
    messages.success(request, 'تم إلغاء طلب قطع الغيار بنجاح')
    
    return redirect('maintenance:cmms:work_order_parts_list', wo_id=work_order.id)

@login_required
def work_order_part_return(request, wo_id, part_id):
    """إرجاع قطع غيار مصروفة"""
    work_order = get_object_or_404(WorkOrder, id=wo_id)
    work_order_part = get_object_or_404(WorkOrderPart, id=part_id, work_order=work_order)
    
    # التحقق من صلاحية المستخدم
    if not request.user.is_superuser and not request.user.groups.filter(name='Supervisor').exists():
        if work_order.assignee != request.user:
            messages.error(request, 'ليس لديك صلاحية لإرجاع قطع الغيار')
            return redirect('maintenance:cmms:work_order_parts_list', wo_id=work_order.id)
    
    # التحقق من أن القطعة تم صرفها
    if work_order_part.status != 'issued' or work_order_part.quantity_used <= 0:
        messages.error(request, 'لا يمكن إرجاع قطعة لم يتم صرفها')
        return redirect('maintenance:cmms:work_order_parts_list', wo_id=work_order.id)
    
    if request.method == 'POST':
        return_quantity = int(request.POST.get('return_quantity', 0))
        
        if return_quantity > 0 and return_quantity <= work_order_part.quantity_used:
            # إرجاع الكمية للمخزون
            spare_part = work_order_part.spare_part
            spare_part.current_stock += return_quantity
            spare_part.save()
            
            # تحديث الكمية المستخدمة
            work_order_part.quantity_used -= return_quantity
            if work_order_part.quantity_used == 0:
                work_order_part.status = 'returned'
            
            # تحديث التكلفة
            if spare_part.unit_cost:
                work_order_part.total_cost = spare_part.unit_cost * work_order_part.quantity_used
            
            work_order_part.save()
            
            messages.success(request, f'تم إرجاع {return_quantity} قطعة للمخزون بنجاح')
        else:
            messages.error(request, 'كمية الإرجاع غير صحيحة')
    
    return redirect('maintenance:cmms:work_order_parts_list', wo_id=work_order.id)


# ========================================
# AJAX Views
# ========================================

@login_required
def get_users_by_type(request):
    """
    Get users based on their role from CustomUser model
    Used in PM Schedule and Device forms
    """
    from django.contrib.auth import get_user_model
    import logging
    
    logger = logging.getLogger(__name__)
    User = get_user_model()
    
    user_type = request.GET.get('type', '')
    logger.info(f'AJAX request for user type: {user_type}')
    
    if not user_type:
        return JsonResponse({'users': [], 'message': 'No type specified'})
    
    # Filter users based on their role field in CustomUser model
    users = User.objects.filter(
        role=user_type,
        is_active=True
    ).select_related('hospital').order_by('full_name', 'first_name', 'last_name')
    
    # Format users data
    users_data = [{
        'id': user.id,
        'name': user.full_name or f"{user.first_name} {user.last_name}".strip() or user.username,
        'username': user.username,
        'role': user.get_role_display(),
        'specialty': user.specialty or '',
        'job_number': user.job_number or '',
        'phone': user.phone_number or '',
        'email': user.email or '',
        'hospital': user.hospital.name if user.hospital else '',
    } for user in users[:50]]  # Limit to 50 users for performance
    
    logger.info(f'Found {len(users_data)} users with role {user_type}')
    
    return JsonResponse({
        'users': users_data,
        'count': len(users_data),
        'type': user_type,
        'type_display': dict(User.ROLE_CHOICES).get(user_type, user_type)
    })