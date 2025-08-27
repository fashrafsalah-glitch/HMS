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
    
    # قطع الغيار الأكثر استخداماً
    # TODO: Implement SparePartTransaction model for tracking usage
    most_used_parts = []
    
    # قطع الغيار المحتاجة إعادة طلب
    parts_need_reorder = SparePart.objects.filter(
        Q(current_stock__lte=F('minimum_stock')) | Q(current_stock=0)
    ).order_by('current_stock')[:10]
    
    # قطع الغيار الأغلى
    expensive_parts = SparePart.objects.filter(
        unit_cost__isnull=False
    ).order_by('-unit_cost')[:10]
    
    context = {
        'spare_parts_stats': spare_parts_stats,
        'most_used_parts': most_used_parts,
        'parts_need_reorder': parts_need_reorder,
        'expensive_parts': expensive_parts,
        'page_title': 'تحليلات قطع الغيار',
    }
    
    return render(request, 'maintenance/dashboard/spare_parts_analytics.html', context)

@login_required
def maintenance_trends(request):
    """
    اتجاهات الصيانة
    هنا بنشوف إزاي الأداء بيتغير على مدار الوقت
    """
    department_id = request.GET.get('department')
    months = int(request.GET.get('months', 6))
    
    # جلب الاتجاهات الشهرية
    from .kpi_utils import get_monthly_trends
    monthly_trends = get_monthly_trends(department_id=department_id, months=months)
    
    # حساب المؤشرات الحالية للمقارنة
    current_metrics = {
        'mtbf': calculate_mtbf(department_id=department_id),
        'mttr': calculate_mttr(department_id=department_id),
        'availability': calculate_availability(department_id=department_id),
        'pm_compliance': calculate_pm_compliance(department_id=department_id),
    }
    
    # جلب الأقسام للفلترة
    departments = Department.objects.all().order_by('name')
    
    context = {
        'monthly_trends': monthly_trends,
        'current_metrics': current_metrics,
        'departments': departments,
        'selected_department_id': department_id,
        'selected_months': months,
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
