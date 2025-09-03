from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Sum, F
from django.utils import timezone
from datetime import timedelta
from django.http import HttpResponse, JsonResponse
import csv

from .models import (
    Supplier, SparePart, SparePartRequest, SparePartTransaction, 
    Calibration, CalibrationRecord,
    Device, WorkOrder, DeviceDowntime, CALIBRATION_STATUS_CHOICES
)
from .forms import (
    SupplierForm, SparePartForm, SparePartTransactionForm,
    CalibrationForm, DowntimeForm, SparePartRequestForm, RequestApprovalForm
)

# =============== Helper Functions ===============
def is_inventory_manager(user):
    """التحقق من صلاحيات مدير المخزون"""
    return user.is_authenticated and (
        user.is_superuser or 
        user.role == 'inventory_manager'
    )

# =============== Inventory Management Views ===============
@login_required
def inventory_dashboard(request):
    """لوحة تحكم مدير المخزون"""
    
    # إحصائيات المخزون الأساسية
    total_spare_parts = SparePart.objects.count()
    total_stock_value = sum(
        part.get_total_value() for part in SparePart.objects.all()
    )
    
    # قطع الغيار منخفضة المخزون
    low_stock_parts = SparePart.objects.filter(
        current_stock__lte=F('minimum_stock')
    ).count()
    
    # قطع الغيار النافدة
    out_of_stock_parts = SparePart.objects.filter(current_stock=0).count()
    
    # إحصائيات الطلبات
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    # طلبات اليوم
    today_requests = SparePartRequest.objects.filter(
        created_at__date=today
    ).count()
    
    # طلبات في الانتظار
    pending_requests = SparePartRequest.objects.filter(
        status='pending'
    ).count()
    
    # طلبات عاجلة
    urgent_requests = SparePartRequest.objects.filter(
        status='pending',
        priority='urgent'
    ).count()
    
    # طلبات الأسبوع الماضي
    week_requests = SparePartRequest.objects.filter(
        created_at__date__gte=week_ago
    ).count()
    
    # إحصائيات المعاملات
    today_transactions = SparePartTransaction.objects.filter(
        transaction_date__date=today
    ).count()
    
    week_transactions = SparePartTransaction.objects.filter(
        transaction_date__date__gte=week_ago
    ).count()
    
    # قيمة المعاملات الصادرة هذا الشهر
    month_out_value = SparePartTransaction.objects.filter(
        transaction_date__date__gte=month_ago,
        transaction_type='out'
    ).aggregate(
        total=Sum('quantity')
    )['total'] or 0
    
    # قوائم البيانات للعرض
    recent_requests = SparePartRequest.objects.select_related(
        'spare_part', 'requester', 'work_order'
    ).order_by('-created_at')[:10]
    
    low_stock_items = SparePart.objects.filter(
        current_stock__lte=F('minimum_stock')
    ).order_by('current_stock')[:10]
    
    recent_transactions = SparePartTransaction.objects.select_related(
        'spare_part', 'created_by'
    ).order_by('-transaction_date')[:10]
    
    # أكثر قطع الغيار استخداماً (آخر 30 يوم)
    most_used_parts = SparePartTransaction.objects.filter(
        transaction_date__date__gte=month_ago,
        transaction_type='out'
    ).values(
        'spare_part__name', 'spare_part__id'
    ).annotate(
        total_used=Sum('quantity')
    ).order_by('-total_used')[:10]
    
    # بيانات المعاملات لآخر 7 أيام
    chart_data = []
    for i in range(7):
        date = today - timedelta(days=i)
        in_count = SparePartTransaction.objects.filter(
            transaction_date__date=date,
            transaction_type='in'
        ).count()
        out_count = SparePartTransaction.objects.filter(
            transaction_date__date=date,
            transaction_type='out'
        ).count()
        
        chart_data.append({
            'date': date.strftime('%Y-%m-%d'),
            'date_ar': date.strftime('%d/%m'),
            'in': in_count,
            'out': out_count
        })
    
    chart_data.reverse()  # ترتيب تصاعدي
    
    # توزيع حالات الطلبات
    request_status_data = []
    for status, label in SparePartRequest.STATUS_CHOICES:
        count = SparePartRequest.objects.filter(status=status).count()
        if count > 0:
            request_status_data.append({
                'status': status,
                'label': label,
                'count': count
            })
    
    # بيانات الشارتس الحقيقية
    available_parts = SparePart.objects.filter(current_stock__gt=F('minimum_stock')).count()
    low_stock_count = low_stock_parts
    out_of_stock_count = out_of_stock_parts
    unavailable_parts = SparePart.objects.filter(status='discontinued').count()
    
    # بيانات الشارت الشهرية (آخر 6 أشهر)
    monthly_labels = []
    monthly_in = []
    monthly_out = []
    
    for i in range(6):
        month_date = today - timedelta(days=30*i)
        month_start = month_date.replace(day=1)
        if i == 0:
            month_end = today
        else:
            next_month = month_start.replace(month=month_start.month + 1) if month_start.month < 12 else month_start.replace(year=month_start.year + 1, month=1)
            month_end = next_month - timedelta(days=1)
        
        monthly_labels.insert(0, month_date.strftime('%m/%Y'))
        
        in_transactions = SparePartTransaction.objects.filter(
            transaction_date__date__gte=month_start,
            transaction_date__date__lte=month_end,
            transaction_type='in'
        ).aggregate(total=Sum('quantity'))['total'] or 0
        
        out_transactions = SparePartTransaction.objects.filter(
            transaction_date__date__gte=month_start,
            transaction_date__date__lte=month_end,
            transaction_type='out'
        ).aggregate(total=Sum('quantity'))['total'] or 0
        
        monthly_in.insert(0, in_transactions)
        monthly_out.insert(0, out_transactions)

    context = {
        # إحصائيات أساسية
        'total_spare_parts': total_spare_parts,
        'total_stock_value': total_stock_value,
        'low_stock_count': low_stock_count,
        'pending_requests_count': pending_requests,
        
        # قوائم البيانات
        'requests': recent_requests,
        'low_stock_items': low_stock_items,
        'recent_transactions': recent_transactions,
        'most_used_parts': most_used_parts,
        
        # بيانات الشارتس الحقيقية
        'stock_status': {
            'available': available_parts,
            'low_stock': low_stock_count,
            'out_of_stock': out_of_stock_count,
            'unavailable': unavailable_parts
        },
        'monthly_labels': monthly_labels,
        'monthly_in': monthly_in,
        'monthly_out': monthly_out,
        
        # معلومات إضافية
        'current_date': today,
        'page_title': 'لوحة تحكم مدير المخزون',
    }
    
    return render(request, 'maintenance/inventory_dashboard.html', context)

@login_required
def pending_requests(request):
    """عرض الطلبات في الانتظار"""
    # عرض جميع الطلبات مع تبويب حسب الحالة
    all_requests = SparePartRequest.objects.select_related(
        'spare_part', 'requester', 'work_order', 'device'
    ).order_by('-priority', '-created_at')
    
    # فلترة حسب الحالة المطلوبة
    status_filter = request.GET.get('status', 'pending')
    requests_list = all_requests.filter(status=status_filter)
    
    # فلترة حسب الأولوية
    priority_filter = request.GET.get('priority')
    if priority_filter:
        requests_list = requests_list.filter(priority=priority_filter)
    
    # فلترة حسب قطعة الغيار
    part_filter = request.GET.get('spare_part')
    if part_filter:
        requests_list = requests_list.filter(spare_part_id=part_filter)
    
    # البحث
    search = request.GET.get('search')
    if search:
        requests_list = requests_list.filter(
            Q(request_number__icontains=search) |
            Q(spare_part__name__icontains=search) |
            Q(requester__first_name__icontains=search) |
            Q(requester__last_name__icontains=search)
        )
    
    # تقسيم الصفحات
    paginator = Paginator(requests_list, 20)
    page_number = request.GET.get('page')
    requests = paginator.get_page(page_number)
    
    # قائمة قطع الغيار للفلتر
    spare_parts = SparePart.objects.all().order_by('name')
    
    # إحصائيات الطلبات حسب الحالة
    pending_count = all_requests.filter(status='pending').count()
    approved_count = all_requests.filter(status='approved').count()
    fulfilled_count = all_requests.filter(status='fulfilled').count()
    rejected_count = all_requests.filter(status='rejected').count()
    
    context = {
        'requests': requests,
        'spare_parts': spare_parts,
        'priority_choices': SparePartRequest.PRIORITY_CHOICES,
        'current_priority': priority_filter,
        'current_part': part_filter,
        'search_query': search,
        'current_status': status_filter,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'fulfilled_count': fulfilled_count,
        'rejected_count': rejected_count,
        'page_title': f'طلبات قطع الغيار - {dict(SparePartRequest.STATUS_CHOICES).get(status_filter, "جميع الطلبات")}',
    }
    
    return render(request, 'maintenance/pending_requests_manager.html', context)

@login_required
def approve_request(request, request_id):
    """الموافقة على طلب قطعة غيار"""
    spare_request = get_object_or_404(SparePartRequest, id=request_id)
    
    if not spare_request.can_approve():
        messages.error(request, 'لا يمكن الموافقة على هذا الطلب')
        return redirect('maintenance:spare_parts:pending_requests')
    
    if request.method == 'POST':
        try:
            approval_notes = request.POST.get('notes', '')
            
            # تحديث الطلب
            spare_request.status = 'approved'
            spare_request.quantity_approved = spare_request.quantity_requested
            spare_request.approved_by = request.user
            spare_request.approved_at = timezone.now()
            spare_request.approval_notes = approval_notes
            spare_request.save()
            
            messages.success(request, f'تمت الموافقة على الطلب {spare_request.request_number} بنجاح')
            # إعادة التوجيه لصفحة الطلبات الموافق عليها بدلاً من المعلقة
            return redirect('maintenance:spare_parts:inventory_dashboard')
            
        except Exception as e:
            messages.error(request, f'حدث خطأ أثناء الموافقة على الطلب: {str(e)}')
            return redirect('maintenance:spare_parts:pending_requests')
    
    context = {
        'spare_request': spare_request,
        'page_title': f'الموافقة على الطلب {spare_request.request_number}',
    }
    
    return render(request, 'maintenance/approve_request.html', context)

@login_required
def fulfill_request(request, request_id):
    """تنفيذ طلب قطعة غيار"""
    spare_request = get_object_or_404(SparePartRequest, id=request_id)
    
    if not spare_request.can_fulfill():
        messages.error(request, 'لا يمكن تنفيذ هذا الطلب')
        return redirect('maintenance:spare_parts:pending_requests')
    
    if request.method == 'POST':
        try:
            notes = request.POST.get('notes', '')
            
            # التحقق من توفر المخزون
            if spare_request.quantity_requested > spare_request.spare_part.current_stock:
                messages.error(request, f'المخزون غير كافي. المطلوب: {spare_request.quantity_requested}, المتاح: {spare_request.spare_part.current_stock}')
                return redirect('maintenance:spare_parts:pending_requests')
            
            # تحديث حالة الطلب
            quantity_to_deduct = spare_request.quantity_approved or spare_request.quantity_requested
            spare_request.spare_part.current_stock -= quantity_to_deduct
            spare_request.spare_part.update_status()
            spare_request.spare_part.save()
            
            # إنشاء معاملة قطع الغيار
            stock_before = spare_request.spare_part.current_stock + quantity_to_deduct
            stock_after = spare_request.spare_part.current_stock
            
            transaction = SparePartTransaction.objects.create(
                spare_part=spare_request.spare_part,
                transaction_type='out',
                quantity=quantity_to_deduct,
                stock_before=stock_before,
                stock_after=stock_after,
                created_by=request.user,
                notes=f'صرف لأمر الشغل: {spare_request.work_order.wo_number if spare_request.work_order else "غير محدد"}',
                reference_number=spare_request.request_number
            )
            
            # تحديث الطلب
            spare_request.status = 'fulfilled'
            spare_request.fulfilled_by = request.user
            spare_request.fulfilled_at = timezone.now()
            spare_request.transaction = transaction
            spare_request.save()
            
            # تحديث تكاليف أمر الشغل إذا كان مرتبط بأمر شغل
            if spare_request.work_order:
                spare_request.work_order.update_costs()
            
            messages.success(request, f'تم تنفيذ الطلب {spare_request.request_number} بنجاح')
            return redirect('maintenance:spare_parts:pending_requests')
            
        except Exception as e:
            messages.error(request, f'حدث خطأ أثناء تنفيذ الطلب: {str(e)}')
            return redirect('maintenance:spare_parts:pending_requests')
    
    context = {
        'spare_request': spare_request,
        'page_title': f'تنفيذ الطلب {spare_request.request_number}',
    }
    
    return render(request, 'maintenance/fulfill_request.html', context)

@login_required
def reject_request(request, request_id):
    """رفض طلب قطعة غيار"""
    spare_request = get_object_or_404(SparePartRequest, id=request_id)
    
    if request.method == 'POST':
        try:
            reason = request.POST.get('reason', 'تم الرفض من قبل المدير')
            
            spare_request.status = 'rejected'
            spare_request.rejected_by = request.user
            spare_request.rejected_at = timezone.now()
            spare_request.rejection_reason = reason
            spare_request.save()
            
            messages.success(request, f'تم رفض الطلب {spare_request.request_number} بنجاح')
            return redirect('maintenance:spare_parts:pending_requests')
            
        except Exception as e:
            messages.error(request, f'حدث خطأ أثناء رفض الطلب: {str(e)}')
            return redirect('maintenance:spare_parts:pending_requests')
    
    context = {
        'spare_request': spare_request,
        'page_title': f'رفض الطلب {spare_request.request_number}',
    }
    
    return render(request, 'maintenance/reject_request.html', context)

@login_required
def request_spare_part(request, work_order_id=None, device_id=None):
    """طلب قطعة غيار من الفني"""
    work_order = None
    device = None
    
    if work_order_id:
        work_order = get_object_or_404(WorkOrder, id=work_order_id)
        if work_order.service_request.device:
            device = work_order.service_request.device
    
    if device_id:
        device = get_object_or_404(Device, id=device_id)
    
    if request.method == 'POST':
        spare_part_id = request.POST.get('spare_part')
        quantity = int(request.POST.get('quantity', 1))
        priority = request.POST.get('priority', 'medium')
        reason = request.POST.get('reason', '')
        notes = request.POST.get('notes', '')
        
        spare_part = get_object_or_404(SparePart, id=spare_part_id)
        
        # إنشاء الطلب
        spare_request = SparePartRequest.objects.create(
            requester=request.user,
            spare_part=spare_part,
            quantity_requested=quantity,
            priority=priority,
            work_order=work_order,
            device=device,
            reason=reason,
            notes=notes
        )
        
        messages.success(request, f'تم إرسال طلب قطعة الغيار برقم {spare_request.request_number}')
        
        if work_order:
            return redirect('maintenance:work_order_detail', pk=work_order.id)
        elif device:
            return redirect('maintenance:device_detail', pk=device.id)
        else:
            return redirect('maintenance:spare_parts:spare_part_list')
    
    # قائمة قطع الغيار
    spare_parts = SparePart.objects.filter(status='available').order_by('name')
    
    context = {
        'spare_parts': spare_parts,
        'work_order': work_order,
        'device': device,
        'priority_choices': SparePartRequest.PRIORITY_CHOICES,
        'page_title': 'طلب قطعة غيار',
    }
    
    return render(request, 'maintenance/request_spare_part.html', context)

@login_required
def my_requests(request):
    """عرض طلبات المستخدم الحالي"""
    requests_list = SparePartRequest.objects.filter(
        requester=request.user
    ).select_related(
        'spare_part', 'work_order', 'device', 'approved_by', 'fulfilled_by'
    ).order_by('-created_at')
    
    # فلترة حسب الحالة
    status_filter = request.GET.get('status')
    if status_filter:
        requests_list = requests_list.filter(status=status_filter)
    
    # تقسيم الصفحات
    paginator = Paginator(requests_list, 20)
    page_number = request.GET.get('page')
    requests = paginator.get_page(page_number)
    
    context = {
        'requests': requests,
        'status_choices': SparePartRequest.STATUS_CHOICES,
        'current_status': status_filter,
        'page_title': 'طلباتي',
    }
    
    return render(request, 'maintenance/my_requests.html', context)

# =============== Supplier Views ===============
@login_required
def supplier_list(request):
    """عرض قائمة الموردين"""
    suppliers = Supplier.objects.all().order_by('name')
    
    # البحث
    search_query = request.GET.get('search', '')
    if search_query:
        suppliers = suppliers.filter(
            Q(name__icontains=search_query) | 
            Q(contact_person__icontains=search_query) | 
            Q(email__icontains=search_query) | 
            Q(phone__icontains=search_query)
        )
    
    # الترتيب
    sort_by = request.GET.get('sort_by', 'name')
    if sort_by not in ['name', 'contact_person', 'email', 'phone']:
        sort_by = 'name'
    suppliers = suppliers.order_by(sort_by)
    
    # التصفيح
    paginator = Paginator(suppliers, 10)  # 10 موردين في كل صفحة
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'sort_by': sort_by,
    }
    return render(request, 'maintenance/supplier_list.html', context)

@login_required
def supplier_detail(request, pk):
    """عرض تفاصيل المورد"""
    supplier = get_object_or_404(Supplier, pk=pk)
    spare_parts = SparePart.objects.filter(primary_supplier=supplier)
    # purchase_orders = PurchaseOrder.objects.filter(supplier=supplier).order_by('-ordered_date')
    purchase_orders = []  # Placeholder until PurchaseOrder model is created
    
    context = {
        'supplier': supplier,
        'spare_parts': spare_parts,
        'purchase_orders': purchase_orders,
    }
    return render(request, 'maintenance/supplier_detail.html', context)

@login_required
def supplier_create(request):
    """إنشاء مورد جديد"""
    if request.method == 'POST':
        form = SupplierForm(request.POST)
        if form.is_valid():
            supplier = form.save(commit=False)
            supplier.created_by = request.user
            supplier.save()
            messages.success(request, f'تم إنشاء المورد {supplier.name} بنجاح')
            return redirect('maintenance:spare_parts:supplier_detail', pk=supplier.pk)
    else:
        form = SupplierForm()
    
    context = {
        'form': form,
        'title': 'إضافة مورد جديد',
    }
    return render(request, 'maintenance/supplier_form.html', context)

@login_required
def supplier_update(request, pk):
    """تحديث بيانات المورد"""
    supplier = get_object_or_404(Supplier, pk=pk)
    if request.method == 'POST':
        form = SupplierForm(request.POST, instance=supplier)
        if form.is_valid():
            supplier = form.save()
            messages.success(request, f'تم تحديث بيانات المورد {supplier.name} بنجاح')
            return redirect('maintenance:spare_parts:supplier_detail', pk=supplier.pk)
    else:
        form = SupplierForm(instance=supplier)
    
    context = {
        'form': form,
        'title': f'تعديل بيانات المورد: {supplier.name}',
        'supplier': supplier,
    }
    return render(request, 'maintenance/supplier_form.html', context)

# =============== Spare Part Views ===============
@login_required
def spare_part_list(request):
    """عرض قائمة قطع الغيار"""
    spare_parts = SparePart.objects.all().select_related('primary_supplier')
    
    # البحث
    search_query = request.GET.get('search', '')
    if search_query:
        spare_parts = spare_parts.filter(
            Q(name__icontains=search_query) | 
            Q(part_number__icontains=search_query) | 
            Q(description__icontains=search_query) |
            Q(primary_supplier__name__icontains=search_query)
        )
    
    # الفلترة
    supplier_id = request.GET.get('supplier')
    if supplier_id:
        spare_parts = spare_parts.filter(primary_supplier_id=supplier_id)
    
    low_stock = request.GET.get('low_stock')
    if low_stock == 'true':
        spare_parts = spare_parts.filter(current_stock__lte=F('minimum_stock'))
    
    # الترتيب
    sort_by = request.GET.get('sort_by', 'name')
    if sort_by not in ['name', 'part_number', 'current_stock', 'primary_supplier__name']:
        sort_by = 'name'
    spare_parts = spare_parts.order_by(sort_by)
    
    # التصفيح
    paginator = Paginator(spare_parts, 20)  # 20 قطعة في كل صفحة
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # قائمة الموردين للفلترة
    suppliers = Supplier.objects.filter(status='active').order_by('name')
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'sort_by': sort_by,
        'suppliers': suppliers,
        'selected_supplier': supplier_id,
        'low_stock': low_stock,
    }
    return render(request, 'maintenance/spare_part_list.html', context)

@login_required
def spare_part_detail(request, pk):
    """عرض تفاصيل قطعة الغيار"""
    spare_part = get_object_or_404(SparePart, pk=pk)
    transactions = spare_part.transactions.all().order_by('-transaction_date')
    compatible_devices = spare_part.compatible_devices.all()
    
    # حساب إحصائيات الاستخدام
    in_transactions = transactions.filter(transaction_type='in')
    out_transactions = transactions.filter(transaction_type='out')
    
    usage_stats = {
        'total_used': sum(t.quantity for t in out_transactions),
        'total_received': sum(t.quantity for t in in_transactions),
        'last_used': out_transactions.first().transaction_date if out_transactions.exists() else None,
        'last_received': in_transactions.first().transaction_date if in_transactions.exists() else None,
    }
    
    context = {
        'spare_part': spare_part,
        'transactions': transactions,
        'compatible_devices': compatible_devices,
        'usage_stats': usage_stats,
    }
    return render(request, 'maintenance/spare_part_detail.html', context)

@login_required
def spare_part_create(request):
    """إنشاء قطعة غيار جديدة"""
    if request.method == 'POST':
        form = SparePartForm(request.POST, request.FILES)
        if form.is_valid():
            spare_part = form.save(commit=False)
            spare_part.created_by = request.user
            spare_part.save()
            messages.success(request, f'تم إنشاء قطعة الغيار {spare_part.name} بنجاح')
            return redirect('maintenance:spare_parts:spare_part_detail', pk=spare_part.pk)
        else:
            messages.error(request, 'يرجى تصحيح الأخطاء في النموذج')
    else:
        form = SparePartForm()
    
    context = {
        'form': form,
        'title': 'إضافة قطعة غيار جديدة',
        'spare_part': None,  # للتوافق مع القالب
    }
    return render(request, 'maintenance/spare_part_form.html', context)

@login_required
def spare_part_update(request, pk):
    """تحديث بيانات قطعة الغيار"""
    spare_part = get_object_or_404(SparePart, pk=pk)
    if request.method == 'POST':
        form = SparePartForm(request.POST, request.FILES, instance=spare_part)
        if form.is_valid():
            spare_part = form.save()
            messages.success(request, f'تم تحديث بيانات قطعة الغيار {spare_part.name} بنجاح')
            return redirect('maintenance:spare_parts:spare_part_detail', pk=spare_part.pk)
    else:
        form = SparePartForm(instance=spare_part)
    
    context = {
        'form': form,
        'title': f'تعديل بيانات قطعة الغيار: {spare_part.name}',
        'spare_part': spare_part,
    }
    return render(request, 'maintenance/spare_part_form.html', context)

@login_required
def spare_part_transaction_create(request, part_id=None):
    """إنشاء حركة جديدة لقطعة غيار"""
    spare_part = None
    if part_id:
        spare_part = get_object_or_404(SparePart, pk=part_id)
    
    if request.method == 'POST':
        form = SparePartTransactionForm(request.POST, spare_part=spare_part)
        if form.is_valid():
            # حفظ المعاملة
            transaction = form.save(commit=False)
            transaction.spare_part = spare_part
            transaction.created_by = request.user
            transaction.stock_before = spare_part.current_stock
            
            # تحديث المخزون حسب نوع المعاملة
            transaction_type = form.cleaned_data['transaction_type']
            quantity = form.cleaned_data['quantity']
            
            if transaction_type == 'in':
                spare_part.current_stock += quantity
                messages.success(request, f'تم إضافة {quantity} قطعة للمخزون')
            elif transaction_type == 'out':
                if spare_part.current_stock >= quantity:
                    spare_part.current_stock -= quantity
                    messages.success(request, f'تم خصم {quantity} قطعة من المخزون')
                else:
                    messages.error(request, f'المخزون الحالي ({spare_part.current_stock}) غير كافي لخصم {quantity} قطعة')
                    return render(request, 'maintenance/spare_part_transaction_form.html', {
                        'form': form,
                        'spare_part': spare_part,
                        'title': 'إضافة حركة قطعة غيار'
                    })
            elif transaction_type == 'adjustment':
                # تعديل المخزون إلى قيمة محددة
                spare_part.current_stock = quantity
                messages.success(request, f'تم تعديل المخزون إلى {quantity} قطعة')
            elif transaction_type == 'return':
                spare_part.current_stock += quantity
                messages.success(request, f'تم إرجاع {quantity} قطعة للمخزون')
            
            # حفظ المخزون الجديد وحالة قطعة الغيار
            transaction.stock_after = spare_part.current_stock
            spare_part.update_status()  # تحديث الحالة بناءً على المخزون الجديد
            spare_part.save()
            
            # حفظ المعاملة
            transaction.save()
            
            if spare_part:
                return redirect('maintenance:spare_parts:spare_part_detail', pk=spare_part.pk)
            else:
                return redirect('maintenance:spare_parts:spare_part_list')
    else:
        form = SparePartTransactionForm(spare_part=spare_part)
    
    context = {
        'form': form,
        'title': 'تسجيل حركة قطعة غيار',
        'spare_part': spare_part,
    }
    return render(request, 'maintenance/spare_part_transaction_form.html', context)

# =============== Calibration Views ===============
@login_required
def calibration_list(request):
    """عرض قائمة المعايرات"""
    calibrations = CalibrationRecord.objects.all().select_related('device')
    
    # البحث
    search_query = request.GET.get('search', '')
    if search_query:
        calibrations = calibrations.filter(
            Q(device__name__icontains=search_query) | 
            Q(certificate_number__icontains=search_query)
        )
    
    # الفلترة
    status = request.GET.get('status')
    if status:
        calibrations = calibrations.filter(status=status)
    
    # الفلترة حسب تاريخ المعايرة القادمة
    due_filter = request.GET.get('due')
    today = timezone.now().date()
    if due_filter == 'overdue':
        calibrations = calibrations.filter(next_calibration_date__lt=today)
    elif due_filter == 'upcoming':
        calibrations = calibrations.filter(
            next_calibration_date__gte=today,
            next_calibration_date__lte=today + timedelta(days=30)
        )
    
    # الترتيب
    sort_by = request.GET.get('sort_by', 'next_calibration_date')
    if sort_by not in ['device__name', 'calibration_date', 'next_calibration_date', 'status']:
        sort_by = 'next_calibration_date'
    calibrations = calibrations.order_by(sort_by)
    
    # التصفيح
    paginator = Paginator(calibrations, 10)  # 10 معايرات في كل صفحة
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'sort_by': sort_by,
        'selected_status': status,
        'due_filter': due_filter,
        'status_choices': CALIBRATION_STATUS_CHOICES,
    }
    return render(request, 'maintenance/calibration_list.html', context)

@login_required
def calibration_detail(request, pk):
    """عرض تفاصيل المعايرة"""
    calibration = get_object_or_404(CalibrationRecord, pk=pk)
    
    context = {
        'calibration': calibration,
    }
    return render(request, 'maintenance/calibration_detail.html', context)

@login_required
def calibration_create(request, device_id=None):
    """إنشاء معايرة جديدة"""
    device = None
    if device_id:
        device = get_object_or_404(Device, pk=device_id)
    
    if request.method == 'POST':
        form = CalibrationForm(request.POST, request.FILES)
        if form.is_valid():
            # Create CalibrationRecord instance
            calibration = CalibrationRecord.objects.create(
                device=form.cleaned_data['device'],
                calibration_date=form.cleaned_data['calibration_date'],
                next_calibration_date=form.cleaned_data['next_calibration_date'],
                certificate_number=form.cleaned_data.get('certificate_number', ''),
                calibration_agency=form.cleaned_data.get('calibration_agency', ''),
                notes=form.cleaned_data.get('notes', ''),
                cost=form.cleaned_data.get('cost'),
                status='completed'
            )
            messages.success(request, 'تم إنشاء المعايرة بنجاح')
            return redirect('maintenance:spare_parts:calibration_detail', pk=calibration.pk)
        else:
            messages.error(request, 'يرجى تصحيح الأخطاء في النموذج')
    else:
        initial_data = {}
        if device:
            initial_data['device'] = device
        form = CalibrationForm(initial=initial_data)
    
    context = {
        'form': form,
        'title': 'إضافة معايرة جديدة',
        'device': device,
    }
    return render(request, 'maintenance/calibration_form.html', context)

@login_required
def calibration_update(request, pk):
    """تحديث بيانات المعايرة"""
    calibration = get_object_or_404(CalibrationRecord, pk=pk)
    
    if request.method == 'POST':
        # form = CalibrationForm(request.POST, request.FILES, instance=calibration)
        # Placeholder - CalibrationForm not available yet
        messages.error(request, 'وظيفة تحديث المعايرة غير متاحة حالياً')
        return redirect('maintenance:spare_parts:calibration_detail', pk=calibration.pk)
    else:
        # Placeholder form
        form = None
    
    context = {
        'form': form,
        'title': f'تعديل بيانات المعايرة: {calibration.device.name}',
        'calibration': calibration,
    }
    return render(request, 'maintenance/calibration_form.html', context)

# =============== Downtime Views ===============
@login_required
def downtime_list(request):
    """عرض قائمة توقفات الأجهزة"""
    downtimes = DeviceDowntime.objects.all().select_related('device', 'work_order')
    
    # البحث
    search_query = request.GET.get('search', '')
    if search_query:
        downtimes = downtimes.filter(
            Q(device__name__icontains=search_query) | 
            Q(reason__icontains=search_query)
        )
    
    # الفلترة
    downtime_type = request.GET.get('downtime_type')
    if downtime_type:
        downtimes = downtimes.filter(downtime_type=downtime_type)
    
    # الفلترة حسب الفترة الزمنية
    period = request.GET.get('period')
    today = timezone.now().date()
    if period == 'today':
        downtimes = downtimes.filter(start_time__date=today)
    elif period == 'week':
        downtimes = downtimes.filter(start_time__date__gte=today - timedelta(days=7))
    elif period == 'month':
        downtimes = downtimes.filter(start_time__date__gte=today - timedelta(days=30))
    
    # الترتيب
    sort_by = request.GET.get('sort_by', '-start_time')
    if sort_by not in ['device__name', 'start_time', '-start_time', 'downtime_type']:
        sort_by = '-start_time'
    downtimes = downtimes.order_by(sort_by)
    
    # التصفيح
    paginator = Paginator(downtimes, 10)  # 10 توقفات في كل صفحة
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # إحصائيات للرسوم البيانية
    all_downtimes = DeviceDowntime.objects.all()
    
    # إحصائيات أسباب التوقف
    stats = {
        'breakdown_count': all_downtimes.filter(reason='breakdown').count(),
        'maintenance_count': all_downtimes.filter(reason='maintenance').count(),
        'calibration_count': all_downtimes.filter(reason='calibration').count(),
        'power_count': all_downtimes.filter(reason='power_failure').count(),
        'other_count': all_downtimes.filter(reason='other').count(),
    }
    
    # الأجهزة الأكثر توقفاً
    from django.db.models import Count
    top_devices = all_downtimes.values('device__name').annotate(
        count=Count('id')
    ).order_by('-count')[:5]
    
    top_devices_names = [device['device__name'] for device in top_devices]
    top_devices_counts = [device['count'] for device in top_devices]
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'sort_by': sort_by,
        'selected_type': downtime_type,
        'period': period,
        'type_choices': DeviceDowntime.DOWNTIME_TYPE_CHOICES,
        'stats': stats,
        'top_devices_names': top_devices_names,
        'top_devices_counts': top_devices_counts,
    }
    return render(request, 'maintenance/downtime_list.html', context)

@login_required
def downtime_detail(request, pk):
    """عرض تفاصيل توقف الجهاز"""
    downtime = get_object_or_404(DeviceDowntime, pk=pk)
    
    context = {
        'downtime': downtime,
    }
    return render(request, 'maintenance/downtime_detail.html', context)

@login_required
def downtime_create(request, device_id=None, work_order_id=None):
    """إنشاء توقف جديد للجهاز"""
    device = None
    work_order = None
    
    if device_id:
        device = get_object_or_404(Device, pk=device_id)
    
    if work_order_id:
        work_order = get_object_or_404(WorkOrder, pk=work_order_id)
        if not device and work_order.service_request.device:
            device = work_order.service_request.device
    
    if request.method == 'POST':
        form = DowntimeForm(request.POST)
        if form.is_valid():
            downtime = form.save(commit=False)
            downtime.reported_by = request.user
            downtime.save()
            
            # تحديث حالة الجهاز إلى غير متاح
            if downtime.end_time is None:  # إذا كان التوقف مستمر
                device = downtime.device
                device.availability = False
                device.save()
            
            messages.success(request, f'تم تسجيل توقف الجهاز بنجاح')
            return redirect('maintenance:spare_parts:downtime_detail', pk=downtime.pk)
    else:
        initial_data = {}
        if device:
            initial_data['device'] = device
        if work_order:
            initial_data['work_order'] = work_order
        form = DowntimeForm(initial=initial_data)
    
    context = {
        'form': form,
        'title': 'تسجيل توقف جديد للجهاز',
        'device': device,
        'work_order': work_order,
    }
    return render(request, 'maintenance/downtime_form.html', context)

@login_required
def downtime_update(request, pk):
    """تحديث بيانات توقف الجهاز"""
    downtime = get_object_or_404(DeviceDowntime, pk=pk)
    old_end_time = downtime.end_time
    
    if request.method == 'POST':
        form = DowntimeForm(request.POST, instance=downtime)
        if form.is_valid():
            downtime = form.save()
            
            # إذا تم إضافة وقت انتهاء للتوقف، تحديث حالة الجهاز إلى متاح
            if old_end_time is None and downtime.end_time is not None:
                device = downtime.device
                # تحقق من عدم وجود توقفات أخرى مفتوحة لنفس الجهاز
                other_open_downtimes = DeviceDowntime.objects.filter(
                    device=device, 
                    end_time__isnull=True
                ).exclude(pk=downtime.pk).exists()
                
                if not other_open_downtimes:
                    device.availability = True
                    device.save()
            
            messages.success(request, f'تم تحديث بيانات توقف الجهاز بنجاح')
            return redirect('maintenance:spare_parts:downtime_detail', pk=downtime.pk)
    else:
        form = DowntimeForm(instance=downtime)
    
    context = {
        'form': form,
        'title': f'تعديل بيانات توقف الجهاز',
        'downtime': downtime,
    }
    return render(request, 'maintenance/downtime_form.html', context)


@login_required
def spare_part_transaction_list(request):
    """عرض قائمة معاملات قطع الغيار"""
    transactions = SparePartTransaction.objects.select_related(
        'spare_part', 'created_by'
    ).order_by('-transaction_date')
    
    # Filters
    transaction_type = request.GET.get('transaction_type')
    spare_part_id = request.GET.get('spare_part')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if transaction_type:
        transactions = transactions.filter(transaction_type=transaction_type)
    
    if spare_part_id:
        transactions = transactions.filter(spare_part_id=spare_part_id)
    
    if date_from:
        transactions = transactions.filter(transaction_date__date__gte=date_from)
    
    if date_to:
        transactions = transactions.filter(transaction_date__date__lte=date_to)
    
    # Pagination
    paginator = Paginator(transactions, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get spare parts for filter dropdown
    spare_parts = SparePart.objects.all().order_by('name')
    
    context = {
        'page_obj': page_obj,
        'spare_parts': spare_parts,
        'title': 'معاملات المخزون',
        'transaction_types': SparePartTransaction.TRANSACTION_TYPES,
        'filters': {
            'transaction_type': transaction_type,
            'spare_part': spare_part_id,
            'date_from': date_from,
            'date_to': date_to,
        }
    }
    return render(request, 'maintenance/spare_part_transaction_list.html', context)

# =============== API Views ===============
@login_required
def api_spare_parts_low_stock(request):
    """API لعرض قطع الغيار منخفضة المخزون"""
    try:
        low_stock_parts = SparePart.objects.filter(current_stock__lte=F('minimum_stock'))
        data = [{
            'id': part.id,
            'name': part.name,
            'part_number': part.part_number,
            'current_stock': part.current_stock,
            'minimum_stock': part.minimum_stock,
            'supplier': part.primary_supplier.name if part.primary_supplier else None,
            'unit_cost': float(part.unit_cost) if part.unit_cost else None,
        } for part in low_stock_parts]
        return JsonResponse({'status': 'success', 'data': data})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

@login_required
def api_calibrations_due(request):
    """API لعرض المعايرات المستحقة"""
    try:
        today = timezone.now().date()
        due_calibrations = CalibrationRecord.objects.filter(
            next_calibration_date__lte=today + timedelta(days=30),
            status__in=['completed', 'due']
        ).select_related('device')
        
        data = [{
            'id': cal.id,
            'device_name': cal.device.name,
            'device_id': cal.device.id,
            'calibration_date': cal.calibration_date.strftime('%Y-%m-%d') if cal.calibration_date else None,
            'next_calibration_date': cal.next_calibration_date.strftime('%Y-%m-%d') if cal.next_calibration_date else None,
            'days_remaining': (cal.next_calibration_date - today).days if cal.next_calibration_date else None,
            'status': cal.status,
        } for cal in due_calibrations]
        return JsonResponse({'status': 'success', 'data': data})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

@login_required
def api_device_downtime_stats(request, device_id):
    """API لعرض إحصائيات توقف الجهاز"""
    try:
        device = get_object_or_404(Device, pk=device_id)
        
        # حساب إجمالي وقت التوقف
        downtimes = DeviceDowntime.objects.filter(device=device)
        
        # إحصائيات حسب نوع التوقف
        downtime_by_type = {}
        for dt_type, _ in DeviceDowntime.DOWNTIME_TYPE_CHOICES:
            type_downtimes = downtimes.filter(reason=dt_type)
            total_hours = 0
            for dt in type_downtimes:
                if dt.end_time and dt.start_time:
                    duration = dt.end_time - dt.start_time
                    total_hours += duration.total_seconds() / 3600
            downtime_by_type[dt_type] = round(total_hours, 2)
        
        # إحصائيات حسب الشهر (آخر 12 شهر)
        today = timezone.now().date()
        months_data = []
        for i in range(11, -1, -1):
            month_start = (today.replace(day=1) - timedelta(days=i*30)).replace(day=1)
            month_end = (month_start.replace(month=month_start.month+1, day=1) - timedelta(days=1)) \
                if month_start.month < 12 else month_start.replace(year=month_start.year+1, month=1, day=1) - timedelta(days=1)
            
            month_downtimes = downtimes.filter(start_time__date__gte=month_start, start_time__date__lte=month_end)
            total_hours = 0
            for dt in month_downtimes:
                if dt.end_time and dt.start_time:
                    duration = dt.end_time - dt.start_time
                    total_hours += duration.total_seconds() / 3600
            
            months_data.append({
                'month': month_start.strftime('%Y-%m'),
                'month_name': month_start.strftime('%b %Y'),
                'hours': round(total_hours, 2)
            })
        
        data = {
            'device_id': device.id,
            'device_name': device.name,
            'downtime_by_type': downtime_by_type,
            'monthly_data': months_data,
            'current_status': 'down' if downtimes.filter(end_time__isnull=True).exists() else 'up',
        }
        
        return JsonResponse({'status': 'success', 'data': data})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

@login_required
def export_spare_parts_csv(request):
    """تصدير قطع الغيار بصيغة CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="spare_parts.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Name', 'Part Number', 'Description', 'Current Stock', 'Minimum Stock', 
                    'Unit', 'Storage Location', 'Unit Cost', 'Supplier', 'Status'])
    
    spare_parts = SparePart.objects.all().select_related('primary_supplier')
    for part in spare_parts:
        writer.writerow([
            part.name,
            part.part_number,
            part.description,
            part.current_stock,
            part.minimum_stock,
            part.unit,
            part.storage_location,
            part.unit_cost,
            part.primary_supplier.name if part.primary_supplier else '',
            part.status
        ])
    
    return response