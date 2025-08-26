from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.db.models import Sum, Count, Q, F, ExpressionWrapper, fields
from django.db.models.functions import Coalesce
from django.contrib import messages
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import datetime, timedelta
import json
import csv

from .models import (
    Supplier, SparePart
)
from .forms_spare_parts import (
    SupplierForm, SparePartForm
)
from .forms import DowntimeForm
from .models import Device, WorkOrder, DowntimeEvent

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
            supplier = form.save()
            messages.success(request, f'تم إنشاء المورد {supplier.name} بنجاح')
            return redirect('supplier_detail', pk=supplier.pk)
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
            return redirect('supplier_detail', pk=supplier.pk)
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
        spare_parts = spare_parts.filter(quantity__lte=F('min_quantity'))
    
    # الترتيب
    sort_by = request.GET.get('sort_by', 'name')
    if sort_by not in ['name', 'part_number', 'quantity', 'primary_supplier__name']:
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
    # transactions = SparePartTransaction.objects.filter(spare_part=spare_part).order_by('-transaction_date')
    transactions = []  # Placeholder until SparePartTransaction model is created
    compatible_devices = spare_part.compatible_devices.all()
    
    # حساب إحصائيات الاستخدام
    usage_stats = {
        'total_used': 0,  # Placeholder
        'total_received': 0,  # Placeholder
        'last_used': None,  # Placeholder
        'last_received': None,  # Placeholder
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
            spare_part = form.save()
            messages.success(request, f'تم إنشاء قطعة الغيار {spare_part.name} بنجاح')
            return redirect('spare_part_detail', pk=spare_part.pk)
    else:
        form = SparePartForm()
    
    context = {
        'form': form,
        'title': 'إضافة قطعة غيار جديدة',
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
            return redirect('spare_part_detail', pk=spare_part.pk)
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
        # form = SparePartTransactionForm(request.POST)
        # Placeholder - SparePartTransactionForm not available yet
        messages.error(request, 'وظيفة المعاملات غير متاحة حالياً')
        return redirect('maintenance:spare_parts:spare_part_detail', pk=spare_part.pk if spare_part else part_id)
    else:
        # Placeholder form
        form = None
    
    context = {
        'form': form,
        'title': 'تسجيل حركة قطعة غيار',
        'spare_part': spare_part,
    }
    return render(request, 'maintenance/spare_part_transaction_form.html', context)

# =============== Purchase Order Views ===============
# Commented out until PurchaseOrder models are created
"""
@login_required
def purchase_order_list(request):
    \"\"\"عرض قائمة طلبات الشراء\"\"\"
    purchase_orders = PurchaseOrder.objects.all().select_related('primary_supplier')
    
    # البحث
    search_query = request.GET.get('search', '')
    if search_query:
        purchase_orders = purchase_orders.filter(
            Q(po_number__icontains=search_query) | 
            Q(primary_supplier__name__icontains=search_query)
        )
    
    # الفلترة
    status = request.GET.get('status')
    if status:
        purchase_orders = purchase_orders.filter(status=status)
    
    supplier_id = request.GET.get('supplier')
    if supplier_id:
        purchase_orders = purchase_orders.filter(primary_supplier_id=supplier_id)
    
    # الترتيب
    sort_by = request.GET.get('sort_by', '-ordered_date')
    if sort_by not in ['po_number', 'primary_supplier__name', 'status', 'ordered_date', '-ordered_date']:
        sort_by = '-ordered_date'
    purchase_orders = purchase_orders.order_by(sort_by)
    
    # التصفيح
    paginator = Paginator(purchase_orders, 10)  # 10 طلبات في كل صفحة
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
        'selected_status': status,
        'status_choices': [],  # Placeholder
    }
    return render(request, 'maintenance/purchase_order_list.html', context)
"""

# Placeholder functions for purchase orders until models are created
@login_required
def purchase_order_detail(request, pk):
    """عرض تفاصيل طلب الشراء - مؤقت"""
    messages.info(request, 'وظائف أوامر الشراء غير متاحة حالياً')
    return redirect('maintenance:spare_parts:spare_part_list')

@login_required
def purchase_order_create(request):
    """إنشاء طلب شراء جديد - مؤقت"""
    messages.info(request, 'وظائف أوامر الشراء غير متاحة حالياً')
    return redirect('maintenance:spare_parts:spare_part_list')

@login_required
def purchase_order_update(request, pk):
    """تحديث بيانات طلب الشراء - مؤقت"""
    messages.info(request, 'وظائف أوامر الشراء غير متاحة حالياً')
    return redirect('maintenance:spare_parts:spare_part_list')

@login_required
def purchase_order_item_create(request, po_id):
    """إضافة عنصر جديد لطلب الشراء - مؤقت"""
    messages.info(request, 'وظائف أوامر الشراء غير متاحة حالياً')
    return redirect('maintenance:spare_parts:spare_part_list')

@login_required
def purchase_order_item_update(request, item_id):
    """تحديث بيانات عنصر طلب الشراء - مؤقت"""
    messages.info(request, 'وظائف أوامر الشراء غير متاحة حالياً')
    return redirect('maintenance:spare_parts:spare_part_list')

@login_required
def purchase_order_receive_items(request, pk):
    """استلام عناصر طلب الشراء - مؤقت"""
    messages.info(request, 'وظائف أوامر الشراء غير متاحة حالياً')
    return redirect('maintenance:spare_parts:spare_part_list')

@login_required
def purchase_order_print(request, pk):
    """طباعة أمر الشراء - مؤقت"""
    messages.info(request, 'وظائف أوامر الشراء غير متاحة حالياً')
    return redirect('maintenance:spare_parts:spare_part_list')

# =============== Calibration Views ===============
# Commented out until Calibration models are created
"""
@login_required
def calibration_list(request):
    \"\"\"عرض قائمة المعايرات\"\"\"
    calibrations = Calibration.objects.all().select_related('device')
    
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
    
    calibration_type = request.GET.get('calibration_type')
    if calibration_type:
        calibrations = calibrations.filter(calibration_type=calibration_type)
    
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
        'selected_type': calibration_type,
        'due_filter': due_filter,
        'status_choices': Calibration.STATUS_CHOICES,
        'type_choices': Calibration.CALIBRATION_TYPE_CHOICES,
    }
    return render(request, 'maintenance/calibration_list.html', context)
"""

# Placeholder functions for calibrations until models are created
@login_required
def calibration_list(request):
    """عرض قائمة المعايرات - مؤقت"""
    messages.info(request, 'وظائف المعايرة غير متاحة حالياً')
    return redirect('maintenance:spare_parts:spare_part_list')

@login_required
def calibration_detail(request, pk):
    """عرض تفاصيل المعايرة - مؤقت"""
    messages.info(request, 'وظائف المعايرة غير متاحة حالياً')
    return redirect('maintenance:spare_parts:spare_part_list')

@login_required
def calibration_create(request, device_id=None):
    """إنشاء معايرة جديدة - مؤقت"""
    messages.info(request, 'وظائف المعايرة غير متاحة حالياً')
    return redirect('maintenance:spare_parts:spare_part_list')

@login_required
def calibration_update(request, pk):
    """تحديث بيانات المعايرة - مؤقت"""
    messages.info(request, 'وظائف المعايرة غير متاحة حالياً')
    return redirect('maintenance:spare_parts:spare_part_list')

# =============== Downtime Views ===============
@login_required
def downtime_list(request):
    """عرض قائمة توقفات الأجهزة"""
    downtimes = DowntimeEvent.objects.all().select_related('device', 'related_work_order')
    
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
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'sort_by': sort_by,
        'selected_type': downtime_type,
        'period': period,
        'type_choices': DowntimeEvent.DOWNTIME_TYPE_CHOICES,
    }
    return render(request, 'maintenance/downtime_list.html', context)

@login_required
def downtime_detail(request, pk):
    """عرض تفاصيل توقف الجهاز"""
    downtime = get_object_or_404(DowntimeEvent, pk=pk)
    
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
        if not device and work_order.device:
            device = work_order.device
    
    if request.method == 'POST':
        form = DowntimeForm(request.POST)
        if form.is_valid():
            downtime = form.save(commit=False)
            downtime.reported_by = request.user
            downtime.save()
            
            # تحديث حالة الجهاز إلى غير متاح
            if downtime.end_time is None:  # إذا كان التوقف مستمر
                device = downtime.device
                device.availability = 'UNAVAILABLE'
                device.save()
            
            messages.success(request, f'تم تسجيل توقف الجهاز بنجاح')
            return redirect('downtime_detail', pk=downtime.pk)
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
    downtime = get_object_or_404(DowntimeEvent, pk=pk)
    old_end_time = downtime.end_time
    
    if request.method == 'POST':
        form = DowntimeForm(request.POST, instance=downtime)
        if form.is_valid():
            downtime = form.save()
            
            # إذا تم إضافة وقت انتهاء للتوقف، تحديث حالة الجهاز إلى متاح
            if old_end_time is None and downtime.end_time is not None:
                device = downtime.device
                # تحقق من عدم وجود توقفات أخرى مفتوحة لنفس الجهاز
                other_open_downtimes = DowntimeEvent.objects.filter(
                    device=device, 
                    end_time__isnull=True
                ).exclude(pk=downtime.pk).exists()
                
                if not other_open_downtimes:
                    device.availability = 'AVAILABLE'
                    device.save()
            
            messages.success(request, f'تم تحديث بيانات توقف الجهاز بنجاح')
            return redirect('downtime_detail', pk=downtime.pk)
    else:
        form = DowntimeForm(instance=downtime)
    
    context = {
        'form': form,
        'title': f'تعديل بيانات توقف الجهاز',
        'downtime': downtime,
    }
    return render(request, 'maintenance/downtime_form.html', context)

# =============== API Views ===============
@login_required
def api_spare_parts_low_stock(request):
    """API لعرض قطع الغيار منخفضة المخزون"""
    try:
        low_stock_parts = SparePart.objects.filter(quantity__lte=F('min_quantity'))
        data = [{
            'id': part.id,
            'name': part.name,
            'part_number': part.part_number,
            'quantity': part.quantity,
            'min_quantity': part.min_quantity,
            'supplier': part.supplier.name if part.supplier else None,
            'cost': float(part.cost) if part.cost else None,
            'lead_time_days': part.lead_time_days,
        } for part in low_stock_parts]
        return JsonResponse({'status': 'success', 'data': data})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

@login_required
def api_calibrations_due(request):
    """API لعرض المعايرات المستحقة"""
    try:
        today = timezone.now().date()
        due_calibrations = Calibration.objects.filter(
            next_calibration_date__lte=today + timedelta(days=30),
            status__in=['SCHEDULED', 'PENDING']
        ).select_related('device')
        
        data = [{
            'id': cal.id,
            'device_name': cal.device.name,
            'device_id': cal.device.id,
            'calibration_date': cal.calibration_date.strftime('%Y-%m-%d') if cal.calibration_date else None,
            'next_calibration_date': cal.next_calibration_date.strftime('%Y-%m-%d') if cal.next_calibration_date else None,
            'days_remaining': (cal.next_calibration_date - today).days if cal.next_calibration_date else None,
            'status': cal.status,
            'calibration_type': cal.calibration_type,
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
        downtimes = Downtime.objects.filter(device=device)
        
        # إحصائيات حسب نوع التوقف
        downtime_by_type = {}
        for dt_type, _ in Downtime.DOWNTIME_TYPE_CHOICES:
            type_downtimes = downtimes.filter(downtime_type=dt_type)
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
    writer.writerow(['Name', 'Part Number', 'Description', 'Quantity', 'Min Quantity', 
                    'Unit', 'Location', 'Cost', 'Supplier', 'Lead Time (Days)'])
    
    spare_parts = SparePart.objects.all().select_related('primary_supplier')
    for part in spare_parts:
        writer.writerow([
            part.name,
            part.part_number,
            part.description,
            part.quantity,
            part.min_quantity,
            part.unit,
            part.location,
            part.cost,
            part.primary_supplier.name if part.primary_supplier else '',
            part.lead_time_days
        ])
    
    return response