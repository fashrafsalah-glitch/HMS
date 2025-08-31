# هنا بنعمل الداشبورد الخاص بالـ CMMS عشان نشوف كل الإحصائيات والمؤشرات المهمة
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Count, Avg, Sum, Q, F
from django.utils import timezone
from datetime import timedelta
import json
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
            created_at__lt=timezone.now() - timezone.timedelta(days=7),  # استخدام created_at بدلاً من resolution_due
            service_request__device__department_id=department_id if department_id else None
        ).count() if department_id else WorkOrder.objects.filter(
            status__in=['new', 'assigned', 'in_progress', 'wait_parts', 'resolved'],
            created_at__lt=timezone.now() - timezone.timedelta(days=7)  # استخدام created_at بدلاً من resolution_due
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
    from django.db.models import Count, Q
    from datetime import datetime, timedelta
    from .models import DeviceTransferRequest, DeviceTransferLog
    import calendar
    
    department_id = request.GET.get('department')
    
    # جلب الأجهزة مع فلترة القسم
    devices = Device.objects.all()
    if department_id:
        devices = devices.filter(department_id=department_id)
    
    # حساب إحصائيات الأجهزة العامة
    total_devices = devices.count()
    down_devices = devices.filter(status='out_of_order').count()
    
    # جلب بيانات تنقلات الأجهزة الحقيقية من قاعدة البيانات
    # جمع البيانات من DeviceTransferRequest و DeviceTransferLog
    current_year = datetime.now().year
    transfer_data_by_month = {}
    
    # تهيئة البيانات لكل شهر
    for month in range(1, 13):
        month_name = calendar.month_name[month]
        arabic_months = {
            'January': 'يناير', 'February': 'فبراير', 'March': 'مارس',
            'April': 'أبريل', 'May': 'مايو', 'June': 'يونيو',
            'July': 'يوليو', 'August': 'أغسطس', 'September': 'سبتمبر',
            'October': 'أكتوبر', 'November': 'نوفمبر', 'December': 'ديسمبر'
        }
        transfer_data_by_month[month] = {
            'name': arabic_months.get(month_name, month_name),
            'departments': {}
        }
    
    # جلب طلبات النقل المكتملة من DeviceTransferRequest
    completed_requests = DeviceTransferRequest.objects.filter(
        status='approved',
        requested_at__year=current_year
    ).select_related('to_department', 'device')
    
    # جلب سجلات النقل من DeviceTransferLog
    transfer_logs = DeviceTransferLog.objects.filter(
        moved_at__year=current_year
    ).select_related('to_department', 'device')
    
    # معالجة طلبات النقل المكتملة
    for transfer_request in completed_requests:
        month = transfer_request.requested_at.month
        dept_name = transfer_request.to_department.name if transfer_request.to_department else 'غير محدد'
        
        if dept_name not in transfer_data_by_month[month]['departments']:
            transfer_data_by_month[month]['departments'][dept_name] = 0
        transfer_data_by_month[month]['departments'][dept_name] += 1
    
    # معالجة سجلات النقل
    for log in transfer_logs:
        month = log.moved_at.month
        dept_name = log.to_department.name if log.to_department else 'غير محدد'
        
        if dept_name not in transfer_data_by_month[month]['departments']:
            transfer_data_by_month[month]['departments'][dept_name] = 0
        transfer_data_by_month[month]['departments'][dept_name] += 1
    
    # تحضير بيانات الشارت
    # جلب أهم 5 أقسام من حيث عدد النقلات
    all_departments = {}
    for month_data in transfer_data_by_month.values():
        for dept, count in month_data['departments'].items():
            if dept not in all_departments:
                all_departments[dept] = 0
            all_departments[dept] += count
    
    # ترتيب الأقسام حسب عدد النقلات
    top_departments = sorted(all_departments.items(), key=lambda x: x[1], reverse=True)[:5]
    
    # إنشاء بيانات الشارت للأقسام الأكثر نشاطاً
    device_transfer_chart_data = {
        'labels': [transfer_data_by_month[i]['name'] for i in range(1, 13)],
        'datasets': []
    }
    
    # ألوان مختلفة لكل قسم
    colors = [
        {'bg': 'rgba(255, 99, 132, 0.6)', 'border': 'rgba(255, 99, 132, 1)'},
        {'bg': 'rgba(54, 162, 235, 0.6)', 'border': 'rgba(54, 162, 235, 1)'},
        {'bg': 'rgba(255, 206, 86, 0.6)', 'border': 'rgba(255, 206, 86, 1)'},
        {'bg': 'rgba(75, 192, 192, 0.6)', 'border': 'rgba(75, 192, 192, 1)'},
        {'bg': 'rgba(153, 102, 255, 0.6)', 'border': 'rgba(153, 102, 255, 1)'}
    ]
    
    for idx, (dept_name, total_count) in enumerate(top_departments):
        if idx >= 5:  # أقصى 5 أقسام
            break
            
        monthly_data = []
        for month in range(1, 13):
            count = transfer_data_by_month[month]['departments'].get(dept_name, 0)
            monthly_data.append(count)
        
        color = colors[idx % len(colors)]
        device_transfer_chart_data['datasets'].append({
            'label': dept_name,
            'data': monthly_data,
            'backgroundColor': color['bg'],
            'borderColor': color['border'],
            'borderWidth': 3,
            'fill': True,
            'tension': 0.4,
            'pointBackgroundColor': color['border'],
            'pointBorderColor': '#fff',
            'pointBorderWidth': 3,
            'pointRadius': 6,
            'pointHoverRadius': 8
        })
    
    # حساب نقاط الأداء لكل جهاز
    device_scores = []
    performance_categories = {'excellent': 0, 'very_good': 0, 'good': 0, 'fair': 0, 'poor': 0}
    
    for device in devices[:20]:  # أول 20 جهاز بس عشان الصفحة متبطئش
        try:
            score = get_device_performance_score(device.id)
            mtbf = calculate_mtbf(device_id=device.id)
            mttr = calculate_mttr(device_id=device.id)
            availability = calculate_availability(device_id=device.id)
            
            # تصنيف الأداء
            if score >= 90:
                performance_categories['excellent'] += 1
                performance_color = 'success'
            elif score >= 80:
                performance_categories['very_good'] += 1
                performance_color = 'info'
            elif score >= 70:
                performance_categories['good'] += 1
                performance_color = 'primary'
            elif score >= 50:
                performance_categories['fair'] += 1
                performance_color = 'warning'
            else:
                performance_categories['poor'] += 1
                performance_color = 'danger'
            
            device_scores.append({
                'device': device,
                'score': score,
                'mtbf': mtbf,
                'mttr': mttr,
                'availability': availability,
                'performance_score': score,
                'performance_color': performance_color,
                'failures_count': ServiceRequest.objects.filter(device=device, request_type='corrective').count(),
                'total_downtime': round(mttr * ServiceRequest.objects.filter(device=device, request_type='corrective').count(), 1)
            })
        except Exception as e:
            # في حالة حدوث خطأ، نضع قيم افتراضية ونسجل الخطأ
            print(f"خطأ في حساب إحصائيات الجهاز {device.name}: {str(e)}")
            
            # حساب قيم بديلة بسيطة
            mtbf_fallback = 168  # أسبوع افتراضي
            mttr_fallback = 4    # 4 ساعات افتراضي
            availability_fallback = 85 if device.status == 'working' else 30
            
            device_scores.append({
                'device': device,
                'score': availability_fallback,
                'mtbf': mtbf_fallback,
                'mttr': mttr_fallback,
                'availability': availability_fallback,
                'performance_score': availability_fallback,
                'performance_color': 'success' if availability_fallback > 80 else 'warning',
                'failures_count': ServiceRequest.objects.filter(device=device, request_type='corrective').count(),
                'total_downtime': mttr_fallback
            })
            if availability_fallback > 80:
                performance_categories['very_good'] += 1
            else:
                performance_categories['fair'] += 1
    
    # ترتيب الأجهزة حسب النقاط (الأسوأ أولاً للجدول)
    worst_performing_devices = sorted(device_scores, key=lambda x: x['score'])[:10]
    
    # حساب متوسط الإحصائيات - نحسب دائماً من الأجهزة الموجودة
    from .kpi_utils import calculate_mtbf, calculate_mttr, calculate_availability
    
    # حساب الإحصائيات العامة
    avg_mtbf = calculate_mtbf(department_id=department_id)
    avg_mttr = calculate_mttr(department_id=department_id) 
    avg_uptime = calculate_availability(department_id=department_id)
    
    # إذا كانت القيم لا تزال صفر، نحسب بناءً على حالات الأجهزة مباشرة
    if avg_uptime == 0:
        working_devices = devices.filter(status='working').count()
        needs_check_devices = devices.filter(status='needs_check').count()
        needs_maintenance_devices = devices.filter(status='needs_maintenance').count()
        out_of_order_devices = devices.filter(status='out_of_order').count()
        
        if total_devices > 0:
            avg_uptime = (
                (working_devices * 95) + 
                (needs_check_devices * 75) + 
                (needs_maintenance_devices * 40) + 
                (out_of_order_devices * 0)
            ) / total_devices
    
    if avg_mtbf == 0:
        avg_mtbf = 168 if total_devices > 0 else 0  # أسبوع افتراضي
    
    if avg_mttr == 0:
        if needs_maintenance_devices > 0:
            avg_mttr = 8  # 8 ساعات للأجهزة التي تحتاج صيانة
        elif needs_check_devices > 0:
            avg_mttr = 4  # 4 ساعات للأجهزة التي تحتاج تفقد
        else:
            avg_mttr = 2  # ساعتان للأجهزة العاملة
    
    # بيانات تحليل الأعطال حسب النوع
    failure_types = ServiceRequest.objects.filter(request_type='corrective').values('request_type').annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    # إضافة تحليل حسب الخطورة بدلاً من failure_type
    severity_analysis = ServiceRequest.objects.filter(request_type='corrective').values('severity').annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    failure_types_labels = [f['severity'] or 'غير محدد' for f in severity_analysis]
    failure_types_data = [f['count'] for f in severity_analysis]
    
    # بيانات استخدام الأقسام
    department_usage = devices.values('department__name').annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    department_usage_labels = [d['department__name'] or 'غير محدد' for d in department_usage]
    department_usage_data = [d['count'] for d in department_usage]
    
    # بيانات توزيع الأجهزة حسب العمر (استخدام production_date بدلاً من purchase_date)
    from datetime import datetime
    current_year = datetime.now().year
    device_age_data = {
        'less_than_1_year': devices.filter(production_date__year=current_year).count(),
        'one_to_3_years': devices.filter(production_date__year__in=[current_year-1, current_year-2]).count(),
        'three_to_5_years': devices.filter(production_date__year__in=[current_year-3, current_year-4]).count(),
        'five_to_7_years': devices.filter(production_date__year__in=[current_year-5, current_year-6]).count(),
        'more_than_7_years': devices.filter(production_date__year__lt=current_year-6).count()
    }
    
    # جلب الأقسام للفلترة
    departments = Department.objects.all().order_by('name')
    
    context = {
        'device_scores': device_scores,
        'worst_performing_devices': worst_performing_devices,
        'departments': departments,
        'selected_department_id': department_id,
        'page_title': 'أداء الأجهزة',
        'device_stats': {
            'avg_uptime': avg_uptime,
            'avg_mtbf': avg_mtbf,
            'avg_mttr': avg_mttr,
            'down_devices_count': down_devices,
            'total_devices': total_devices
        },
        'device_performance_data': performance_categories,
        'failure_types_labels': failure_types_labels,
        'failure_types_data': failure_types_data,
        'department_usage_labels': department_usage_labels,
        'department_usage_data': department_usage_data,
        'device_age_data': device_age_data,
        'device_transfer_chart_data': json.dumps(device_transfer_chart_data),  # إضافة بيانات الشارت الحقيقية
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
    
    # فلترة أوامر الشغل حسب القسم والتاريخ
    work_orders = WorkOrder.objects.filter(
        created_at__gte=timezone.now() - timedelta(days=days)
    )
    
    if department_id:
        work_orders = work_orders.filter(service_request__device__department_id=department_id)
    
    # إحصائيات أوامر الشغل الأساسية
    total_work_orders = work_orders.count()
    completed_work_orders = work_orders.filter(status='closed')
    
    # حساب متوسط وقت الإنجاز
    avg_completion_time = 0
    if completed_work_orders.exists():
        completion_times = []
        for wo in completed_work_orders:
            if wo.actual_end and wo.actual_start:
                completion_time = (wo.actual_end - wo.actual_start).total_seconds() / 3600
                completion_times.append(completion_time)
        avg_completion_time = sum(completion_times) / len(completion_times) if completion_times else 0
    
    # حساب نسبة الالتزام بالـ SLA
    sla_compliant = work_orders.filter(
        service_request__resolution_due__gte=F('actual_end')
    ).count() if work_orders.filter(actual_end__isnull=False).exists() else 0
    sla_compliance = (sla_compliant / total_work_orders * 100) if total_work_orders > 0 else 0
    
    # أوامر الشغل المتأخرة
    overdue_work_orders_count = work_orders.filter(
        status__in=['new', 'assigned', 'in_progress', 'wait_parts', 'resolved'],
        service_request__resolution_due__lt=timezone.now()
    ).count()
    
    # إحصائيات أوامر الشغل للكاردات
    work_order_stats = {
        'total_work_orders': total_work_orders,
        'avg_completion_time': round(avg_completion_time, 1),
        'sla_compliance': round(sla_compliance, 1),
        'sla_compliance_color': 'success' if sla_compliance >= 80 else 'warning' if sla_compliance >= 60 else 'danger',
        'overdue_work_orders': overdue_work_orders_count
    }
    
    # توزيع أوامر الشغل حسب الحالة
    work_order_status = {
        'new': work_orders.filter(status='new').count(),
        'assigned': work_orders.filter(status='assigned').count(),
        'in_progress': work_orders.filter(status='in_progress').count(),
        'wait_parts': work_orders.filter(status='wait_parts').count(),
        'resolved': work_orders.filter(status='resolved').count(),
        'closed': work_orders.filter(status='closed').count(),
        'cancelled': work_orders.filter(status='cancelled').count()
    }
    
    # توزيع أوامر الشغل حسب النوع
    work_order_type = {
        'corrective': work_orders.filter(service_request__request_type='corrective').count(),
        'preventive': work_orders.filter(service_request__request_type='preventive').count(),
        'inspection': work_orders.filter(service_request__request_type='inspection').count(),
        'calibration': work_orders.filter(service_request__request_type='calibration').count(),
        'upgrade': work_orders.filter(service_request__request_type='upgrade').count() if work_orders.filter(service_request__request_type='upgrade').exists() else 0,
        'installation': work_orders.filter(service_request__request_type='installation').count() if work_orders.filter(service_request__request_type='installation').exists() else 0
    }
    
    # توزيع أوامر الشغل حسب الأولوية
    work_order_priority = {
        'critical': work_orders.filter(service_request__priority='critical').count(),
        'high': work_orders.filter(service_request__priority='high').count(),
        'medium': work_orders.filter(service_request__priority='medium').count(),
        'low': work_orders.filter(service_request__priority='low').count()
    }
    
    # اتجاهات أوامر الشغل (آخر 12 أسبوع)
    weeks = []
    new_orders = []
    completed_orders = []
    
    for i in range(12):
        week_start = timezone.now() - timedelta(weeks=i+1)
        week_end = timezone.now() - timedelta(weeks=i)
        
        week_label = f"الأسبوع {12-i}"
        weeks.append(week_label)
        
        week_new = work_orders.filter(created_at__range=[week_start, week_end]).count()
        week_completed = work_orders.filter(
            status='closed',
            actual_end__range=[week_start, week_end]
        ).count()
        
        new_orders.append(week_new)
        completed_orders.append(week_completed)
    
    work_order_trends = {
        'weeks': weeks,
        'new_orders': new_orders,
        'completed_orders': completed_orders
    }
    
    # أوامر الشغل حسب القسم
    departments_list = Department.objects.all()
    dept_names = []
    dept_counts = []
    
    for dept in departments_list:
        dept_work_orders = work_orders.filter(service_request__device__department=dept).count()
        if dept_work_orders > 0:
            dept_names.append(dept.name)
            dept_counts.append(dept_work_orders)
    
    department_work_orders = {
        'departments': dept_names,
        'counts': dept_counts
    }
    
    # إحصائيات الفنيين
    from hr.models import CustomUser
    technicians = CustomUser.objects.filter(role='technician')
    technician_stats = []
    
    for tech in technicians:
        tech_work_orders = work_orders.filter(assignee=tech)
        tech_completed = tech_work_orders.filter(status='closed')
        tech_overdue = tech_work_orders.filter(
            status__in=['new', 'assigned', 'in_progress', 'wait_parts', 'resolved'],
            service_request__resolution_due__lt=timezone.now()
        )
        
        # حساب متوسط وقت الإنجاز للفني
        tech_completion_times = []
        for wo in tech_completed:
            if wo.actual_end and wo.actual_start:
                completion_time = (wo.actual_end - wo.actual_start).total_seconds() / 3600
                tech_completion_times.append(completion_time)
        
        tech_avg_completion = sum(tech_completion_times) / len(tech_completion_times) if tech_completion_times else 0
        
        # حساب نسبة الالتزام بالـ SLA للفني
        tech_sla_compliant = tech_work_orders.filter(
            service_request__resolution_due__gte=F('actual_end')
        ).count() if tech_work_orders.filter(actual_end__isnull=False).exists() else 0
        tech_sla_compliance = (tech_sla_compliant / tech_work_orders.count() * 100) if tech_work_orders.count() > 0 else 0
        
        if tech_work_orders.count() > 0:
            technician_stats.append({
                'name': f"{tech.first_name} {tech.last_name}",
                'total_work_orders': tech_work_orders.count(),
                'completed_work_orders': tech_completed.count(),
                'overdue_work_orders': tech_overdue.count(),
                'avg_completion_time': round(tech_avg_completion, 1),
                'sla_compliance': round(tech_sla_compliance, 1),
                'sla_compliance_color': 'success' if tech_sla_compliance >= 80 else 'warning' if tech_sla_compliance >= 60 else 'danger'
            })
    
    # أوامر الشغل الأكثر تأخيراً
    overdue_work_orders = work_orders.filter(
        status__in=['new', 'assigned', 'in_progress', 'wait_parts', 'resolved'],
        service_request__resolution_due__lt=timezone.now()
    ).order_by('service_request__resolution_due')
    
    # جلب الأقسام للفلترة
    departments = Department.objects.all().order_by('name')
    
    context = {
        'work_order_stats': work_order_stats,
        'work_order_status': work_order_status,
        'work_order_type': work_order_type,
        'work_order_priority': work_order_priority,
        'work_order_trends': work_order_trends,
        'department_work_orders': department_work_orders,
        'technician_stats': technician_stats,
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
    from django.db.models import Sum, Count, Avg, F, Q, Max
    from .models import SparePartTransaction
    
    # حساب إحصائيات قطع الغيار
    spare_parts_stats = calculate_spare_parts_stats()
    
    # حساب القيمة الإجمالية للمخزون من البيانات الحقيقية
    total_inventory_value = SparePart.objects.aggregate(
        total_value=Sum(F('current_stock') * F('unit_cost'))
    )['total_value'] or 0
    
    # حساب معدل دوران المخزون الحقيقي
    # معدل دوران المخزون = إجمالي الاستهلاك السنوي / متوسط المخزون
    annual_consumption = SparePartTransaction.objects.filter(
        transaction_type='out',
        transaction_date__gte=timezone.now() - timedelta(days=365)
    ).aggregate(total=Sum('quantity'))['total'] or 0
    
    avg_inventory = SparePart.objects.aggregate(
        avg_stock=Avg('current_stock')
    )['avg_stock'] or 1
    
    inventory_turnover = annual_consumption / avg_inventory if avg_inventory > 0 else 0
    
    # إضافة بيانات مفقودة للإحصائيات
    spare_parts_stats.update({
        'total_value': total_inventory_value,
        'below_threshold_count': spare_parts_stats.get('low_stock_parts', 0) + spare_parts_stats.get('out_of_stock_parts', 0),
        'below_threshold_color': 'danger' if spare_parts_stats.get('low_stock_parts', 0) + spare_parts_stats.get('out_of_stock_parts', 0) > 0 else 'success',
        'inventory_turnover': round(inventory_turnover, 1)
    })
    
    # قطع الغيار الأكثر استخداماً - بيانات حقيقية
    most_used_parts = []
    # جلب قطع الغيار مع عدد مرات الاستخدام الحقيقي
    parts_usage = SparePart.objects.annotate(
        usage_count=Count('transactions', filter=Q(transactions__transaction_type='out')),
        last_transaction=Max('transactions__transaction_date')
    ).filter(usage_count__gt=0).order_by('-usage_count')[:10]
    
    for part in parts_usage:
        most_used_parts.append({
            'part_number': part.part_number,
            'name': part.name,
            'category': part.device_category.name if part.device_category else 'عام',
            'usage_count': part.usage_count,
            'last_used': part.last_transaction or part.created_at,
            'current_stock': part.current_stock,
            'stock_status': 'متاح' if part.current_stock > part.minimum_stock else 'منخفض' if part.current_stock > 0 else 'نفد',
            'stock_status_color': 'success' if part.current_stock > part.minimum_stock else 'warning' if part.current_stock > 0 else 'danger'
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
    
    # بيانات الرسوم البيانية - بيانات حقيقية
    # توزيع قطع الغيار حسب الفئة
    category_data = SparePart.objects.values('device_category__name').annotate(
        count=Count('id')
    ).order_by('-count')
    
    spare_parts_category = {
        'categories': [item['device_category__name'] or 'غير محدد' for item in category_data],
        'counts': [item['count'] for item in category_data]
    }
    
    # توزيع قطع الغيار حسب الموردين
    supplier_data = SparePart.objects.values('primary_supplier__name').annotate(
        count=Count('id')
    ).order_by('-count')[:8]
    
    supplier_distribution = {
        'suppliers': [item['primary_supplier__name'] or 'غير محدد' for item in supplier_data],
        'counts': [item['count'] for item in supplier_data]
    }
    
    # اتجاهات الاستهلاك - بيانات حقيقية من المعاملات
    import calendar
    monthly_consumption = {}
    for i in range(6):
        month_start = timezone.now().replace(day=1) - timedelta(days=30*i)
        month_end = month_start.replace(day=calendar.monthrange(month_start.year, month_start.month)[1])
        
        month_transactions = SparePartTransaction.objects.filter(
            transaction_type='out',
            transaction_date__range=[month_start, month_end]
        )
        
        monthly_consumption[month_start.strftime('%Y-%m')] = {
            'name': calendar.month_name[month_start.month],
            'quantity': month_transactions.aggregate(total=Sum('quantity'))['total'] or 0,
            'cost': month_transactions.aggregate(
                total=Sum(F('quantity') * F('spare_part__unit_cost'))
            )['total'] or 0
        }
    
    # ترتيب البيانات حسب التاريخ
    sorted_months = sorted(monthly_consumption.items())
    consumption_trends = {
        'months': [data['name'] for _, data in sorted_months],
        'quantities': [data['quantity'] for _, data in sorted_months],
        'costs': [float(data['cost']) for _, data in sorted_months]
    }
    
    # تكلفة قطع الغيار حسب الجهاز - بيانات حقيقية
    device_cost_data = SparePartTransaction.objects.filter(
        transaction_type='out',
        device__isnull=False,
        transaction_date__gte=timezone.now() - timedelta(days=365)
    ).values('device__name').annotate(
        total_cost=Sum(F('quantity') * F('spare_part__unit_cost'))
    ).order_by('-total_cost')[:10]
    
    device_cost = {
        'devices': [item['device__name'] for item in device_cost_data],
        'costs': [float(item['total_cost'] or 0) for item in device_cost_data]
    }
    
    # تكلفة قطع الغيار حسب القسم - بيانات حقيقية
    department_cost_data = SparePartTransaction.objects.filter(
        transaction_type='out',
        device__department__isnull=False,
        transaction_date__gte=timezone.now() - timedelta(days=365)
    ).values('device__department__name').annotate(
        total_cost=Sum(F('quantity') * F('spare_part__unit_cost'))
    ).order_by('-total_cost')[:10]
    
    department_cost = {
        'departments': [item['device__department__name'] for item in department_cost_data],
        'costs': [float(item['total_cost'] or 0) for item in department_cost_data]
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

def calculate_real_sla_compliance(work_orders):
    """حساب نسبة الالتزام بالـ SLA الحقيقية"""
    if not work_orders.exists():
        return 0
    
    compliant_count = 0
    total_count = work_orders.count()
    
    for wo in work_orders:
        if wo.actual_end and wo.service_request.resolution_due:
            if wo.actual_end <= wo.service_request.resolution_due:
                compliant_count += 1
    
    return (compliant_count / total_count * 100) if total_count > 0 else 0

@login_required
def maintenance_trends(request):
    """
    اتجاهات الصيانة
    هنا بنشوف إزاي الأداء بيتغير على مدار الوقت
    """
    from django.db.models import Count, Avg, Sum, F, Q
    from datetime import datetime, timedelta
    import calendar
    from .models import SparePartTransaction
    
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
            'corrective': month_requests.filter(request_type='corrective').count(),
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
    breakdown_count = service_requests.filter(request_type='corrective').count()
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
    failure_reasons_data = service_requests.filter(request_type='corrective').values('description')
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
            'sla_compliance': calculate_real_sla_compliance(month_completed) if month_completed.exists() else 0
        }
    
    kpi_trends = {
        'time_periods': [data['name'] for data in monthly_data.values()],
        'response_time': [round(monthly_kpis.get(key, {}).get('response_time', 0), 1) for key in monthly_data.keys()],
        'repair_time': [round(monthly_kpis.get(key, {}).get('repair_time', 0), 1) for key in monthly_data.keys()],
        'sla_compliance': [round(monthly_kpis.get(key, {}).get('sla_compliance', 85), 0) for key in monthly_data.keys()]
    }
    
    # تكاليف الصيانة - بيانات حقيقية من معاملات قطع الغيار
    monthly_costs = {}
    for month_key, month_data in monthly_data.items():
        year, month = month_key.split('-')
        month_start = datetime(int(year), int(month), 1)
        month_end = month_start.replace(day=calendar.monthrange(int(year), int(month))[1])
        
        # تكلفة قطع الغيار الحقيقية
        parts_cost = SparePartTransaction.objects.filter(
            transaction_type='out',
            transaction_date__range=[month_start, month_end]
        ).aggregate(
            total=Sum(F('quantity') * F('spare_part__unit_cost'))
        )['total'] or 0
        
        # تقدير تكلفة العمالة بناءً على ساعات العمل الفعلية
        month_work_orders = work_orders.filter(
            created_at__year=int(year),
            created_at__month=int(month),
            status='closed'
        )
        
        total_labor_hours = 0
        for wo in month_work_orders:
            if wo.actual_end and wo.actual_start:
                labor_hours = (wo.actual_end - wo.actual_start).total_seconds() / 3600
                total_labor_hours += labor_hours
        
        labor_cost = total_labor_hours * 50  # 50 ريال/ساعة كمتوسط
        
        monthly_costs[month_key] = {
            'parts_cost': float(parts_cost),
            'labor_cost': labor_cost,
            'other_cost': (float(parts_cost) + labor_cost) * 0.1  # 10% تكاليف إضافية
        }
    
    cost_trends = {
        'time_periods': [data['name'] for data in monthly_data.values()],
        'parts_cost': [monthly_costs.get(key, {}).get('parts_cost', 0) for key in monthly_data.keys()],
        'labor_cost': [monthly_costs.get(key, {}).get('labor_cost', 0) for key in monthly_data.keys()],
        'other_cost': [monthly_costs.get(key, {}).get('other_cost', 0) for key in monthly_data.keys()]
    }
    
    # توزيع الصيانة حسب الأقسام الحقيقي
    departments_list = Department.objects.all()
    dept_maintenance_data = {}
    
    for dept in departments_list:
        dept_requests = service_requests.filter(device__department=dept)
        dept_maintenance_data[dept.name] = {
            'corrective': dept_requests.filter(request_type='corrective').count(),
            'preventive': dept_requests.filter(request_type='preventive').count()
        }
    
    department_maintenance = {
        'departments': list(dept_maintenance_data.keys()),
        'corrective': [data['corrective'] for data in dept_maintenance_data.values()],
        'preventive': [data['preventive'] for data in dept_maintenance_data.values()]
    }
    
    # توزيع الصيانة حسب نوع الجهاز
    device_types = service_requests.values('device__device_type__name').annotate(
        corrective_count=Count('id', filter=Q(request_type='corrective')),
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
    تصدير تقرير الداشبورد الشامل بصيغة PDF
    """
    from django.http import HttpResponse
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from datetime import datetime
    import json
    
    department_id = request.GET.get('department')
    export_format = request.GET.get('format', 'pdf')
    
    if export_format == 'json':
        # جلب البيانات الشاملة
        dashboard_data = get_dashboard_summary(department_id=department_id)
        response = HttpResponse(
            json.dumps(dashboard_data, indent=2, ensure_ascii=False, default=str),
            content_type='application/json; charset=utf-8'
        )
        response['Content-Disposition'] = 'attachment; filename="cmms_dashboard_report.json"'
        return response
    
    # إنشاء تقرير PDF شامل
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="maintenance_comprehensive_report.pdf"'
    
    # إعداد المستند
    doc = SimpleDocTemplate(response, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
    
    # إعداد الأنماط
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=30,
        alignment=1,  # Center alignment
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=12,
        textColor=colors.darkblue,
    )
    
    # محتوى التقرير
    story = []
    
    # Main Title
    story.append(Paragraph("Comprehensive Maintenance Management System Report", title_style))
    story.append(Paragraph(f"Report Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
    story.append(Spacer(1, 20))
    
    # Data Collection
    try:
        from .models import Device, WorkOrder, SparePart, SparePartTransaction, CalibrationRecord
        
        # Device Statistics
        story.append(Paragraph("Device Statistics", heading_style))
        total_devices = Device.objects.count()
        active_devices = Device.objects.filter(availability=True).count()
        inactive_devices = total_devices - active_devices
        
        devices_data = [
            ['Description', 'Count'],
            ['Total Devices', str(total_devices)],
            ['Available Devices', str(active_devices)],
            ['Unavailable Devices', str(inactive_devices)],
        ]
        
        devices_table = Table(devices_data)
        devices_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(devices_table)
        story.append(Spacer(1, 20))
        
        # Work Order Statistics
        story.append(Paragraph("Work Order Statistics", heading_style))
        total_work_orders = WorkOrder.objects.count()
        pending_orders = WorkOrder.objects.filter(status='pending').count()
        in_progress_orders = WorkOrder.objects.filter(status='in_progress').count()
        completed_orders = WorkOrder.objects.filter(status='completed').count()
        
        work_orders_data = [
            ['Status', 'Count'],
            ['Total Work Orders', str(total_work_orders)],
            ['Pending', str(pending_orders)],
            ['In Progress', str(in_progress_orders)],
            ['Completed', str(completed_orders)],
        ]
        
        work_orders_table = Table(work_orders_data)
        work_orders_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(work_orders_table)
        story.append(Spacer(1, 20))
        
        # Spare Parts Statistics
        story.append(Paragraph("Spare Parts Statistics", heading_style))
        total_spare_parts = SparePart.objects.count()
        low_stock_parts = SparePart.objects.filter(quantity__lte=models.F('minimum_stock_level')).count()
        out_of_stock_parts = SparePart.objects.filter(quantity=0).count()
        
        spare_parts_data = [
            ['Description', 'Count'],
            ['Total Spare Parts', str(total_spare_parts)],
            ['Low Stock', str(low_stock_parts)],
            ['Out of Stock', str(out_of_stock_parts)],
        ]
        
        spare_parts_table = Table(spare_parts_data)
        spare_parts_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(spare_parts_table)
        story.append(Spacer(1, 20))
        
        # Calibration Statistics
        story.append(Paragraph("Calibration Statistics", heading_style))
        total_calibrations = CalibrationRecord.objects.count()
        overdue_calibrations = CalibrationRecord.objects.filter(
            next_calibration_date__lt=datetime.now().date()
        ).count()
        
        calibration_data = [
            ['Description', 'Count'],
            ['Total Calibrations', str(total_calibrations)],
            ['Overdue Calibrations', str(overdue_calibrations)],
        ]
        
        calibration_table = Table(calibration_data)
        calibration_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(calibration_table)
        story.append(Spacer(1, 20))
        
        # Device List
        story.append(PageBreak())
        story.append(Paragraph("Device List", heading_style))
        
        devices = Device.objects.all()[:20]  # First 20 devices
        devices_list_data = [['Device Name', 'Department', 'Status', 'Installation Date']]
        
        for device in devices:
            status = 'Available' if device.availability else 'Unavailable'
            install_date = device.installation_date.strftime('%Y-%m-%d') if device.installation_date else '-'
            devices_list_data.append([
                device.name,
                device.department.name if device.department else '-',
                status,
                install_date
            ])
        
        devices_list_table = Table(devices_list_data)
        devices_list_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(devices_list_table)
        
    except Exception as e:
        story.append(Paragraph(f"Error retrieving data: {str(e)}", styles['Normal']))
    
    # إنشاء المستند
    doc.build(story)
    return response
