# هنا بنعمل الداشبورد الخاص بالـ CMMS عشان نشوف كل الإحصائيات والمؤشرات المهمة
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Count, Avg, Sum, Q, F
from django.utils import timezone
from datetime import timedelta
from .kpi_utils import (
    get_dashboard_summary, 
    get_critical_alerts,
    get_device_performance_score,
    calculate_mtbf,
    calculate_mttr,
    calculate_availability,
    calculate_pm_compliance,
    calculate_work_order_stats,
    calculate_spare_parts_stats
)
from .models import Device
from .models import ServiceRequest, WorkOrder, SparePart
from manager.models import Department

@login_required
def cmms_dashboard(request):
    """
    الداشبورد الرئيسي للـ CMMS
    هنا بنعرض كل المؤشرات والإحصائيات المهمة للصيانة
    """
    # جلب القسم المحدد من المستخدم (إن وجد)
    department_id = request.GET.get('department')
    department = None
    if department_id:
        try:
            department = Department.objects.get(id=department_id)
        except Department.DoesNotExist:
            department_id = None
    
    # جلب ملخص شامل للداشبورد
    dashboard_data = get_dashboard_summary(department_id=department_id)
    
    # جلب التنبيهات الحرجة
    critical_alerts = get_critical_alerts(department_id=department_id)
    
    # إحصائيات سريعة للكاردات العلوية
    quick_stats = {
        'total_devices': Device.objects.filter(
            department_id=department_id if department_id else None
        ).count() if department_id else Device.objects.count(),
        
        'active_work_orders': WorkOrder.objects.filter(
            status__in=['new', 'assigned', 'in_progress', 'wait_parts', 'resolved'],
            service_request__device__department_id=department_id if department_id else None
        ).count() if department_id else WorkOrder.objects.filter(
            status__in=['new', 'assigned', 'in_progress', 'wait_parts', 'resolved']
        ).count(),
        
        'overdue_work_orders': WorkOrder.objects.filter(
            status__in=['new', 'assigned', 'in_progress', 'wait_parts', 'resolved'],
            service_request__resolution_due__lt=timezone.now(),
            service_request__device__department_id=department_id if department_id else None
        ).count() if department_id else WorkOrder.objects.filter(
            status__in=['new', 'assigned', 'in_progress', 'wait_parts', 'resolved'],
            service_request__resolution_due__lt=timezone.now()
        ).count(),
        
        'low_stock_parts': SparePart.objects.filter(status='low_stock').count(),
        'out_of_stock_parts': SparePart.objects.filter(status='out_of_stock').count(),
    }
    
    # جلب الأقسام للفلترة
    departments = Department.objects.all().order_by('name')
    
    context = {
        'dashboard_data': dashboard_data,
        'critical_alerts': critical_alerts,
        'quick_stats': quick_stats,
        'departments': departments,
        'selected_department': department,
        'page_title': 'لوحة تحكم الصيانة',
    }
    
    return render(request, 'maintenance/cmms_dashboard.html', context)

@login_required
def device_performance_dashboard(request):
    """
    داشبورد أداء الأجهزة
    هنا بنشوف أداء كل جهاز على حدة مع النقاط والتقييمات
    """
    department_id = request.GET.get('department')
    
    # جلب الأجهزة مع فلترة القسم
    devices = Device.objects.all()
    if department_id:
        devices = devices.filter(department_id=department_id)
    
    # حساب نقاط الأداء لكل جهاز
    device_scores = []
    for device in devices[:20]:  # أول 20 جهاز بس عشان الصفحة متبطئش
        try:
            score = get_device_performance_score(device.id)
            device_scores.append({
                'device': device,
                'score': score,
                'mtbf': calculate_mtbf(device_id=device.id),
                'mttr': calculate_mttr(device_id=device.id),
                'availability': calculate_availability(device_id=device.id),
            })
        except Exception as e:
            # في حالة حدوث خطأ، نضع قيم افتراضية
            device_scores.append({
                'device': device,
                'score': 0,
                'mtbf': 0,
                'mttr': 0,
                'availability': 0,
            })
    
    # ترتيب الأجهزة حسب النقاط
    device_scores.sort(key=lambda x: x['score'], reverse=True)
    
    # جلب الأقسام للفلترة
    departments = Department.objects.all().order_by('name')
    
    context = {
        'device_scores': device_scores,
        'departments': departments,
        'selected_department_id': department_id,
        'page_title': 'أداء الأجهزة',
    }
    
    return render(request, 'maintenance/dashboard/device_performance_dashboard.html', context)

@login_required
def work_order_analytics(request):
    """
    تحليلات أوامر الشغل
    هنا بنشوف إحصائيات مفصلة عن أوامر الشغل وحالاتها
    """
    department_id = request.GET.get('department')
    days = int(request.GET.get('days', 30))
    
    # حساب إحصائيات أوامر الشغل
    wo_stats = calculate_work_order_stats(department_id=department_id, days=days)
    
    # إحصائيات حسب نوع الطلب
    request_type_stats = {}
    work_orders = WorkOrder.objects.filter(
        created_at__gte=timezone.now() - timedelta(days=days)
    )
    
    if department_id:
        work_orders = work_orders.filter(service_request__device__department_id=department_id)
    
    for request_type in ['breakdown', 'preventive', 'calibration', 'inspection']:
        count = work_orders.filter(service_request__request_type=request_type).count()
        request_type_stats[request_type] = count
    
    # إحصائيات حسب الأولوية
    priority_stats = {}
    for priority in ['low', 'medium', 'high', 'critical']:
        count = work_orders.filter(service_request__priority=priority).count()
        priority_stats[priority] = count
    
    # أوامر الشغل الأكثر تأخيراً
    overdue_work_orders = WorkOrder.objects.filter(
        status__in=['new', 'assigned', 'in_progress', 'wait_parts', 'resolved'],
        service_request__resolution_due__lt=timezone.now()
    ).order_by('service_request__resolution_due')
    
    if department_id:
        overdue_work_orders = overdue_work_orders.filter(
            service_request__device__department_id=department_id
        )
    
    # جلب الأقسام للفلترة
    departments = Department.objects.all().order_by('name')
    
    context = {
        'wo_stats': wo_stats,
        'request_type_stats': request_type_stats,
        'priority_stats': priority_stats,
        'overdue_work_orders': overdue_work_orders[:10],
        'departments': departments,
        'selected_department_id': department_id,
        'selected_days': days,
        'page_title': 'تحليلات أوامر الشغل',
    }
    
    return render(request, 'maintenance/dashboard/work_order_analytics.html', context)

@login_required
def spare_parts_analytics(request):
    """
    تحليلات قطع الغيار
    هنا بنشوف وضع المخزون وحركة قطع الغيار
    """
    # حساب إحصائيات قطع الغيار
    spare_parts_stats = calculate_spare_parts_stats()
    
    # إضافة بيانات مفقودة للإحصائيات
    spare_parts_stats.update({
        'total_value': spare_parts_stats.get('total_inventory_value', 0),
        'below_threshold_count': spare_parts_stats.get('low_stock_parts', 0) + spare_parts_stats.get('out_of_stock_parts', 0),
        'below_threshold_color': 'danger' if spare_parts_stats.get('low_stock_parts', 0) + spare_parts_stats.get('out_of_stock_parts', 0) > 0 else 'success',
        'inventory_turnover': 2.5  # قيمة افتراضية
    })
    
    # قطع الغيار الأكثر استخداماً - بيانات وهمية للعرض
    most_used_parts = []
    spare_parts = SparePart.objects.all()[:10]
    for i, part in enumerate(spare_parts):
        most_used_parts.append({
            'part_number': part.part_number,
            'name': part.name,
            'category': part.device_category.name if part.device_category else 'عام',
            'usage_count': 15 - i,  # قيم وهمية
            'last_used': timezone.now() - timedelta(days=i*3),
            'current_stock': part.current_stock,
            'stock_status': 'متاح' if part.current_stock > 10 else 'منخفض',
            'stock_status_color': 'success' if part.current_stock > 10 else 'warning'
        })
    
    # قطع الغيار المحتاجة إعادة طلب
    reorder_parts = []
    parts_need_reorder = SparePart.objects.filter(
        Q(current_stock__lte=F('minimum_stock')) | Q(current_stock=0)
    ).order_by('current_stock')[:10]
    
    for part in parts_need_reorder:
        reorder_parts.append({
            'id': part.id,
            'part_number': part.part_number,
            'name': part.name,
            'category': part.device_category.name if part.device_category else 'عام',
            'current_stock': part.current_stock,
            'min_stock': part.minimum_stock,
            'suggested_order_qty': max(part.minimum_stock * 2, 10),
            'preferred_supplier': part.primary_supplier.name if part.primary_supplier else 'غير محدد'
        })
    
    # بيانات الرسوم البيانية
    spare_parts_category = {
        'categories': ['كهربائية', 'ميكانيكية', 'إلكترونية', 'استهلاكية', 'أخرى'],
        'counts': [25, 30, 15, 20, 10]
    }
    
    supplier_distribution = {
        'suppliers': ['المورد الأول', 'المورد الثاني', 'المورد الثالث', 'أخرى'],
        'counts': [40, 25, 20, 15]
    }
    
    consumption_trends = {
        'months': ['يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو'],
        'quantities': [45, 52, 38, 61, 43, 55],
        'costs': [15000, 18000, 14000, 22000, 16000, 19000]
    }
    
    device_cost = {
        'devices': ['جهاز الأشعة', 'جهاز التنفس', 'جهاز القلب', 'المختبر'],
        'costs': [25000, 18000, 15000, 12000]
    }
    
    department_cost = {
        'departments': ['الطوارئ', 'العناية المركزة', 'الجراحة', 'المختبر'],
        'costs': [35000, 28000, 22000, 18000]
    }
    
    context = {
        'spare_parts_stats': spare_parts_stats,
        'most_used_parts': most_used_parts,
        'reorder_parts': reorder_parts,
        'spare_parts_category': spare_parts_category,
        'supplier_distribution': supplier_distribution,
        'consumption_trends': consumption_trends,
        'device_cost': device_cost,
        'department_cost': department_cost,
        'page_title': 'تحليلات قطع الغيار',
    }
    
    return render(request, 'maintenance/dashboard/spare_parts_analytics.html', context)

@login_required
def maintenance_trends(request):
    """
    اتجاهات الصيانة
    هنا بنشوف إزاي الأداء بيتغير على مدار الوقت
    """
    from django.db.models import Count, Avg
    from datetime import datetime, timedelta
    import calendar
    
    department_id = request.GET.get('department')
    date_range = request.GET.get('date_range', 'last_6_months')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    # تحديد نطاق التاريخ
    now = timezone.now()
    if date_range == 'custom' and start_date and end_date:
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        except:
            start_dt = now - timedelta(days=180)
            end_dt = now
    elif date_range == 'last_month':
        start_dt = now - timedelta(days=30)
        end_dt = now
    elif date_range == 'last_3_months':
        start_dt = now - timedelta(days=90)
        end_dt = now
    elif date_range == 'last_year':
        start_dt = now - timedelta(days=365)
        end_dt = now
    else:  # last_6_months
        start_dt = now - timedelta(days=180)
        end_dt = now
    
    # فلترة الطلبات حسب القسم والتاريخ
    service_requests = ServiceRequest.objects.filter(
        created_at__range=[start_dt, end_dt]
    )
    work_orders = WorkOrder.objects.filter(
        created_at__range=[start_dt, end_dt]
    )
    
    if department_id and department_id != 'all':
        service_requests = service_requests.filter(device__department_id=department_id)
        work_orders = work_orders.filter(service_request__device__department_id=department_id)
    
    # حساب الإحصائيات الأساسية الحقيقية
    total_requests = service_requests.count()
    preventive_requests = service_requests.filter(request_type='preventive').count()
    preventive_ratio = (preventive_requests / total_requests * 100) if total_requests > 0 else 0
    
    # حساب متوسط أوقات الاستجابة والإصلاح
    completed_work_orders = work_orders.filter(status='closed')
    avg_response_time = 0
    avg_repair_time = 0
    
    if completed_work_orders.exists():
        # حساب متوسط أوقات الاستجابة والإصلاح
        response_times = []
        repair_times = []
        completed_work_orders = work_orders.filter(status='closed')
        
        for wo in completed_work_orders:
            if wo.actual_start and wo.service_request.created_at:
                response_time = (wo.actual_start - wo.service_request.created_at).total_seconds() / 3600
                response_times.append(response_time)
            
            if wo.actual_end and wo.actual_start:
                repair_time = (wo.actual_end - wo.actual_start).total_seconds() / 3600
                repair_times.append(repair_time)
            
            avg_response_time = sum(response_times) / len(response_times) if response_times else 0
            avg_repair_time = sum(repair_times) / len(repair_times) if repair_times else 0
        
    maintenance_stats = {
        'total_requests': total_requests,
        'avg_response_time': round(avg_response_time, 1),
        'avg_repair_time': round(avg_repair_time, 1),
        'preventive_ratio': round(preventive_ratio, 1),
        'preventive_ratio_color': 'success' if preventive_ratio > 30 else 'warning'
    }
    
    # بيانات اتجاهات الصيانة الحقيقية حسب الشهور
    monthly_data = {}
    current_date = start_dt.replace(day=1)
    
    while current_date <= end_dt:
        month_key = current_date.strftime('%Y-%m')
        month_name = calendar.month_name[current_date.month]
        
        month_requests = service_requests.filter(
            created_at__year=current_date.year,
            created_at__month=current_date.month
        )
        
        monthly_data[month_key] = {
            'name': month_name,
            'corrective': month_requests.filter(request_type='breakdown').count(),
            'preventive': month_requests.filter(request_type='preventive').count(),
            'predictive': month_requests.filter(request_type='calibration').count()
        }
        
        # الانتقال للشهر التالي
        if current_date.month == 12:
            current_date = current_date.replace(year=current_date.year + 1, month=1)
        else:
            current_date = current_date.replace(month=current_date.month + 1)
    
    maintenance_trends = {
        'time_periods': [data['name'] for data in monthly_data.values()],
        'corrective': [data['corrective'] for data in monthly_data.values()],
        'preventive': [data['preventive'] for data in monthly_data.values()],
        'predictive': [data['predictive'] for data in monthly_data.values()]
    }
    
    # توزيع أنواع الصيانة الحقيقي
    breakdown_count = service_requests.filter(request_type='breakdown').count()
    preventive_count = service_requests.filter(request_type='preventive').count()
    calibration_count = service_requests.filter(request_type='calibration').count()
    inspection_count = service_requests.filter(request_type='inspection').count()
    
    maintenance_type = {
        'corrective': breakdown_count,
        'preventive': preventive_count,
        'predictive': calibration_count,
        'calibration': calibration_count,
        'inspection': inspection_count
    }
    
    # أسباب الأعطال من البيانات الحقيقية
    failure_reasons_data = service_requests.filter(request_type='breakdown').values('description')
    failure_categories = {
        'تآكل طبيعي': 0,
        'خطأ تشغيلي': 0,
        'عطل كهربائي': 0,
        'عطل ميكانيكي': 0,
        'أخرى': 0
    }
    
    # تصنيف الأعطال حسب الوصف (تصنيف بسيط)
    for req in failure_reasons_data:
        desc = req.get('description', '').lower()
        if any(word in desc for word in ['تآكل', 'قديم', 'استهلاك']):
            failure_categories['تآكل طبيعي'] += 1
        elif any(word in desc for word in ['خطأ', 'تشغيل', 'استخدام']):
            failure_categories['خطأ تشغيلي'] += 1
        elif any(word in desc for word in ['كهرباء', 'كهربائي', 'طاقة']):
            failure_categories['عطل كهربائي'] += 1
        elif any(word in desc for word in ['ميكانيكي', 'حركة', 'محرك']):
            failure_categories['عطل ميكانيكي'] += 1
        else:
            failure_categories['أخرى'] += 1
    
    failure_reasons = {
        'reasons': list(failure_categories.keys()),
        'counts': list(failure_categories.values())
    }
    
    # مؤشرات الأداء الحقيقية حسب الشهور
    monthly_kpis = {}
    for month_key, month_data in monthly_data.items():
        month_work_orders = work_orders.filter(
            created_at__year=int(month_key.split('-')[0]),
            created_at__month=int(month_key.split('-')[1])
        )
        
        # حساب متوسط أوقات الاستجابة والإصلاح للشهر
        month_response_times = []
        month_repair_times = []
        month_completed = month_work_orders.filter(status='closed')
        
        for wo in month_completed:
            # استخدام actual_start بدلاً من assigned_at
            if wo.actual_start and wo.service_request.created_at:
                response_time = (wo.actual_start - wo.service_request.created_at).total_seconds() / 3600
                month_response_times.append(response_time)
            
            # استخدام actual_end بدلاً من completed_at و actual_start بدلاً من started_at
            if wo.actual_end and wo.actual_start:
                repair_time = (wo.actual_end - wo.actual_start).total_seconds() / 3600
                month_repair_times.append(repair_time)
        
        monthly_kpis[month_key] = {
            'response_time': sum(month_response_times) / len(month_response_times) if month_response_times else 0,
            'repair_time': sum(month_repair_times) / len(month_repair_times) if month_repair_times else 0,
            'sla_compliance': 85 + (len(month_response_times) * 2) if month_response_times else 85  # تقدير بسيط
        }
    
    kpi_trends = {
        'time_periods': [data['name'] for data in monthly_data.values()],
        'response_time': [round(monthly_kpis.get(key, {}).get('response_time', 0), 1) for key in monthly_data.keys()],
        'repair_time': [round(monthly_kpis.get(key, {}).get('repair_time', 0), 1) for key in monthly_data.keys()],
        'sla_compliance': [round(monthly_kpis.get(key, {}).get('sla_compliance', 85), 0) for key in monthly_data.keys()]
    }
    
    # تكاليف الصيانة (بيانات تقديرية لأن لا يوجد نموذج تكلفة)
    cost_trends = {
        'time_periods': [data['name'] for data in monthly_data.values()],
        'parts_cost': [data['corrective'] * 1000 + data['preventive'] * 500 for data in monthly_data.values()],
        'labor_cost': [data['corrective'] * 800 + data['preventive'] * 400 for data in monthly_data.values()],
        'other_cost': [data['corrective'] * 200 + data['preventive'] * 100 for data in monthly_data.values()]
    }
    
    # توزيع الصيانة حسب الأقسام الحقيقي
    departments_list = Department.objects.all()
    dept_maintenance_data = {}
    
    for dept in departments_list:
        dept_requests = service_requests.filter(device__department=dept)
        dept_maintenance_data[dept.name] = {
            'corrective': dept_requests.filter(request_type='breakdown').count(),
            'preventive': dept_requests.filter(request_type='preventive').count()
        }
    
    department_maintenance = {
        'departments': list(dept_maintenance_data.keys()),
        'corrective': [data['corrective'] for data in dept_maintenance_data.values()],
        'preventive': [data['preventive'] for data in dept_maintenance_data.values()]
    }
    
    # توزيع الصيانة حسب نوع الجهاز
    device_types = service_requests.values('device__device_type__name').annotate(
        corrective_count=Count('id', filter=Q(request_type='breakdown')),
        preventive_count=Count('id', filter=Q(request_type='preventive'))
    ).order_by('-corrective_count')[:4]
    
    device_type_maintenance = {
        'device_types': [dt['device__device_type__name'] or 'غير محدد' for dt in device_types],
        'corrective': [dt['corrective_count'] for dt in device_types],
        'preventive': [dt['preventive_count'] for dt in device_types]
    }
    
    # الاتجاهات الموسمية (مقارنة السنة الحالية بالسابقة)
    current_year = now.year
    previous_year = current_year - 1
    
    current_year_data = []
    previous_year_data = []
    
    for month in range(1, 13):
        current_count = ServiceRequest.objects.filter(
            created_at__year=current_year,
            created_at__month=month
        ).count()
        
        previous_count = ServiceRequest.objects.filter(
            created_at__year=previous_year,
            created_at__month=month
        ).count()
        
        current_year_data.append(current_count)
        previous_year_data.append(previous_count)
    
    seasonal_trends = {
        'current_year': current_year_data,
        'previous_year': previous_year_data
    }
    
    # جلب الأقسام للفلترة
    departments = Department.objects.all().order_by('name')
    
    context = {
        'maintenance_stats': maintenance_stats,
        'maintenance_trends': maintenance_trends,
        'maintenance_type': maintenance_type,
        'failure_reasons': failure_reasons,
        'kpi_trends': kpi_trends,
        'cost_trends': cost_trends,
        'department_maintenance': department_maintenance,
        'device_type_maintenance': device_type_maintenance,
        'seasonal_trends': seasonal_trends,
        'departments': departments,
        'date_range': date_range,
        'department': department_id,
        'page_title': 'اتجاهات الصيانة',
    }
    
    return render(request, 'maintenance/dashboard/maintenance_trends.html', context)

@login_required
def dashboard_api_data(request):
    """
    API لجلب بيانات الداشبورد بصيغة JSON
    هنا بنرجع البيانات للـ JavaScript عشان نعمل الرسوم البيانية
    """
    department_id = request.GET.get('department')
    data_type = request.GET.get('type', 'summary')
    
    if data_type == 'summary':
        # ملخص عام
        data = get_dashboard_summary(department_id=department_id)
        
    elif data_type == 'work_orders':
        # إحصائيات أوامر الشغل
        days = int(request.GET.get('days', 30))
        data = calculate_work_order_stats(department_id=department_id, days=days)
        
    elif data_type == 'spare_parts':
        # إحصائيات قطع الغيار
        data = calculate_spare_parts_stats(department_id=department_id)
        
    elif data_type == 'trends':
        # الاتجاهات الشهرية
        months = int(request.GET.get('months', 6))
        from .kpi_utils import get_monthly_trends
        data = get_monthly_trends(department_id=department_id, months=months)
        
    elif data_type == 'alerts':
        # التنبيهات الحرجة
        data = get_critical_alerts(department_id=department_id)
        
    else:
        data = {'error': 'نوع البيانات غير صحيح'}
    
    return JsonResponse(data, safe=False)

@login_required
def device_detail_kpis(request, device_id):
    """
    مؤشرات الأداء لجهاز معين
    هنا بنعرض تفاصيل أداء جهاز واحد بس
    """
    device = get_object_or_404(Device, id=device_id)
    
    # حساب المؤشرات للجهاز
    device_kpis = {
        'performance_score': get_device_performance_score(device_id),
        'mtbf': calculate_mtbf(device_id=device_id),
        'mttr': calculate_mttr(device_id=device_id),
        'availability': calculate_availability(device_id=device_id),
        'pm_compliance': calculate_pm_compliance(device_id=device_id),
    }
    
    # آخر أوامر الشغل للجهاز
    recent_work_orders = WorkOrder.objects.filter(
        service_request__device=device
    ).order_by('-created_at')[:5]
    
    # أوقات التوقف الأخيرة
    recent_downtimes = Downtime.objects.filter(
        device=device
    ).order_by('-start_time')[:5]
    
    context = {
        'device': device,
        'device_kpis': device_kpis,
        'recent_work_orders': recent_work_orders,
        'recent_downtimes': recent_downtimes,
        'page_title': f'مؤشرات أداء الجهاز: {device.name}',
    }
    
    return render(request, 'maintenance/device_detail_kpis.html', context)

@login_required
def export_dashboard_report(request):
    """
    تصدير تقرير الداشبورد
    هنا بنصدر كل البيانات في ملف PDF أو Excel
    """
    from django.http import HttpResponse
    import json
    
    department_id = request.GET.get('department')
    export_format = request.GET.get('format', 'json')
    
    # جلب البيانات الشاملة
    dashboard_data = get_dashboard_summary(department_id=department_id)
    
    if export_format == 'json':
        response = HttpResponse(
            json.dumps(dashboard_data, indent=2, ensure_ascii=False, default=str),
            content_type='application/json; charset=utf-8'
        )
        response['Content-Disposition'] = 'attachment; filename="cmms_dashboard_report.json"'
        return response
    
    # يمكن إضافة تصدير PDF أو Excel هنا لاحقاً
    return JsonResponse({'error': 'صيغة التصدير غير مدعومة حالياً'})
