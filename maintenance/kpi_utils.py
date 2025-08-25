# هنا بنحسب الـ KPIs والإحصائيات المهمة للـ CMMS عشان نعرف أداء الصيانة إزاي
from django.db.models import Count, Avg, Sum, Q, F
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Device
from .models import ServiceRequest, WorkOrder, PreventiveMaintenanceSchedule, SparePart
import calendar

def calculate_mtbf(device_id=None, department_id=None, days=30):
    """
    حساب متوسط الوقت بين الأعطال (Mean Time Between Failures)
    هنا بنشوف قد إيه الجهاز بيشتغل من غير ما يعطل
    """
    # تحديد الفترة الزمنية
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)
    
    # فلترة الأجهزة
    devices = Device.objects.all()
    if device_id:
        devices = devices.filter(id=device_id)
    if department_id:
        devices = devices.filter(department_id=department_id)
    
    total_mtbf = 0
    device_count = 0
    
    for device in devices:
        # جلب أوامر الشغل المكتملة للجهاز في الفترة المحددة
        completed_work_orders = WorkOrder.objects.filter(
            service_request__device=device,
            status__in=['closed', 'qa_verified'],
            created_at__range=[start_date, end_date],
            service_request__request_type='breakdown'  # بس الأعطال، مش الصيانة الوقائية
        ).order_by('created_at')
        
        if completed_work_orders.count() > 1:
            # حساب الوقت بين كل عطل والتاني
            failure_intervals = []
            for i in range(1, len(completed_work_orders)):
                prev_failure = completed_work_orders[i-1].created_at
                current_failure = completed_work_orders[i].created_at
                interval = (current_failure - prev_failure).total_seconds() / 3600  # بالساعات
                failure_intervals.append(interval)
            
            if failure_intervals:
                device_mtbf = sum(failure_intervals) / len(failure_intervals)
                total_mtbf += device_mtbf
                device_count += 1
    
    return total_mtbf / device_count if device_count > 0 else 0

def calculate_mttr(device_id=None, department_id=None, days=30):
    """
    حساب متوسط وقت الإصلاح (Mean Time To Repair)
    هنا بنشوف قد إيه بياخد وقت عشان نصلح العطل
    """
    # تحديد الفترة الزمنية
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)
    
    # جلب أوامر الشغل المكتملة
    work_orders = WorkOrder.objects.filter(
        status__in=['closed', 'qa_verified'],
        actual_start__isnull=False,
        actual_end__isnull=False,
        created_at__range=[start_date, end_date]
    )
    
    if device_id:
        work_orders = work_orders.filter(service_request__device_id=device_id)
    if department_id:
        work_orders = work_orders.filter(service_request__device__department_id=department_id)
    
    if not work_orders.exists():
        return 0
    
    total_repair_time = 0
    for wo in work_orders:
        repair_time = (wo.actual_end - wo.actual_start).total_seconds() / 3600  # بالساعات
        total_repair_time += repair_time
    
    return total_repair_time / work_orders.count()

def calculate_availability(device_id=None, department_id=None, days=30):
    """
    حساب نسبة التوفر (Availability)
    هنا بنشوف قد إيه الجهاز متاح للاستخدام من إجمالي الوقت
    """
    # تحديد الفترة الزمنية
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)
    total_hours = days * 24
    
    # جلب أوقات التوقف
    from .models import DowntimeEvent
    downtimes = DowntimeEvent.objects.filter(
        start_time__range=[start_date, end_date]
    )
    
    if device_id:
        downtimes = downtimes.filter(device_id=device_id)
    if department_id:
        downtimes = downtimes.filter(device__department_id=department_id)
    
    total_downtime_hours = 0
    for downtime in downtimes:
        if downtime.end_time:
            downtime_duration = (downtime.end_time - downtime.start_time).total_seconds() / 3600
        else:
            # إذا لم ينته التوقف بعد، نحسب من البداية حتى الآن
            downtime_duration = (timezone.now() - downtime.start_time).total_seconds() / 3600
        
        total_downtime_hours += downtime_duration
    
    # حساب نسبة التوفر
    if device_id:
        # للجهاز الواحد
        availability = ((total_hours - total_downtime_hours) / total_hours) * 100
    else:
        # لعدة أجهزة، نحسب المتوسط
        device_count = Device.objects.filter(
            department_id=department_id if department_id else None
        ).count() or 1
        
        total_possible_hours = total_hours * device_count
        availability = ((total_possible_hours - total_downtime_hours) / total_possible_hours) * 100
    
    return max(0, min(100, availability))  # نتأكد إن النسبة بين 0 و 100

def calculate_pm_compliance(department_id=None, days=30):
    """
    حساب نسبة الالتزام بالصيانة الوقائية
    هنا بنشوف قد إيه بنلتزم بجداول الصيانة الوقائية
    """
    # تحديد الفترة الزمنية
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)
    
    # جلب جداول الصيانة الوقائية المستحقة في الفترة
    pm_schedules = PreventiveMaintenanceSchedule.objects.filter(
        status='active',
        next_due_date__range=[start_date.date(), end_date.date()]
    )
    
    if department_id:
        pm_schedules = pm_schedules.filter(device__department_id=department_id)
    
    if not pm_schedules.exists():
        return 100  # إذا مفيش جداول مستحقة، يبقى الالتزام 100%
    
    # عدد الجداول المنفذة (اللي اتعملها work orders)
    completed_schedules = 0
    for schedule in pm_schedules:
        # نشوف لو فيه work order اتعمل للجدول ده في الفترة المحددة
        wo_exists = WorkOrder.objects.filter(
            service_request__device=schedule.device,
            service_request__request_type='preventive',
            service_request__is_auto_generated=True,
            created_at__range=[start_date, end_date],
            status__in=['closed', 'qa_verified']
        ).exists()
        
        if wo_exists:
            completed_schedules += 1
    
    compliance_rate = (completed_schedules / pm_schedules.count()) * 100
    return compliance_rate

def calculate_work_order_stats(department_id=None, days=30):
    """
    حساب إحصائيات أوامر الشغل
    هنا بنجمع معلومات عن أوامر الشغل وحالاتها
    """
    # تحديد الفترة الزمنية
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)
    
    # جلب أوامر الشغل في الفترة
    work_orders = WorkOrder.objects.filter(
        created_at__range=[start_date, end_date]
    )
    
    if department_id:
        work_orders = work_orders.filter(service_request__device__department_id=department_id)
    
    # إحصائيات حسب الحالة
    stats = {
        'total': work_orders.count(),
        'new': work_orders.filter(status='new').count(),
        'assigned': work_orders.filter(status='assigned').count(),
        'in_progress': work_orders.filter(status='in_progress').count(),
        'wait_parts': work_orders.filter(status='wait_parts').count(),
        'on_hold': work_orders.filter(status='on_hold').count(),
        'resolved': work_orders.filter(status='resolved').count(),
        'qa_verified': work_orders.filter(status='qa_verified').count(),
        'closed': work_orders.filter(status='closed').count(),
        'cancelled': work_orders.filter(status='cancelled').count(),
    }
    
    # حساب النسب المئوية
    if stats['total'] > 0:
        stats['completion_rate'] = ((stats['closed'] + stats['qa_verified']) / stats['total']) * 100
        stats['in_progress_rate'] = ((stats['assigned'] + stats['in_progress']) / stats['total']) * 100
        stats['overdue_rate'] = calculate_overdue_work_orders_rate(department_id, days)
    else:
        stats['completion_rate'] = 0
        stats['in_progress_rate'] = 0
        stats['overdue_rate'] = 0
    
    return stats

def calculate_overdue_work_orders_rate(department_id=None, days=30):
    """
    حساب نسبة أوامر الشغل المتأخرة
    هنا بنشوف قد إيه من أوامر الشغل فاتت مواعيدها
    """
    # جلب أوامر الشغل المفتوحة
    work_orders = WorkOrder.objects.filter(
        status__in=['new', 'assigned', 'in_progress', 'wait_parts', 'on_hold', 'resolved']
    )
    
    if department_id:
        work_orders = work_orders.filter(service_request__device__department_id=department_id)
    
    if not work_orders.exists():
        return 0
    
    # عدد أوامر الشغل المتأخرة (اللي فاتت مواعيد SLA)
    overdue_count = 0
    for wo in work_orders:
        sr = wo.service_request
        if sr.resolution_due and timezone.now() > sr.resolution_due:
            overdue_count += 1
    
    return (overdue_count / work_orders.count()) * 100

def calculate_spare_parts_stats(department_id=None):
    """
    حساب إحصائيات قطع الغيار
    هنا بنشوف وضع المخزون وحركة قطع الغيار
    """
    spare_parts = SparePart.objects.all()
    
    # إحصائيات عامة
    stats = {
        'total_parts': spare_parts.count(),
        'available_parts': spare_parts.filter(status='available').count(),
        'low_stock_parts': spare_parts.filter(status='low_stock').count(),
        'out_of_stock_parts': spare_parts.filter(status='out_of_stock').count(),
        'on_order_parts': spare_parts.filter(status='on_order').count(),
    }
    
    # حساب النسب المئوية
    if stats['total_parts'] > 0:
        stats['availability_rate'] = (stats['available_parts'] / stats['total_parts']) * 100
        stats['low_stock_rate'] = (stats['low_stock_parts'] / stats['total_parts']) * 100
        stats['out_of_stock_rate'] = (stats['out_of_stock_parts'] / stats['total_parts']) * 100
    else:
        stats['availability_rate'] = 0
        stats['low_stock_rate'] = 0
        stats['out_of_stock_rate'] = 0
    
    # إجمالي قيمة المخزون
    total_inventory_value = 0
    for part in spare_parts:
        if part.cost and part.quantity:
            total_inventory_value += part.cost * part.quantity
    
    stats['total_inventory_value'] = total_inventory_value
    
    return stats

def calculate_calibration_compliance(department_id=None, days=30):
    """
    حساب نسبة الالتزام بالمعايرة
    هنا بنشوف قد إيه بنلتزم بمواعيد معايرة الأجهزة
    """
    # تحديد الفترة الزمنية
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)
    
    # جلب الأجهزة اللي محتاجة معايرة
    devices = Device.objects.all()
    if department_id:
        devices = devices.filter(department_id=department_id)
    
    total_devices = devices.count()
    if total_devices == 0:
        return 100
    
    # عدد الأجهزة اللي اتعايرت في الوقت المناسب
    compliant_devices = 0
    
    for device in devices:
        # آخر معايرة للجهاز
        from .models import CalibrationRecord
        last_calibration = device.calibrations.filter(
            status='completed'
        ).order_by('-calibration_date').first()
        
        if last_calibration and last_calibration.next_calibration_date:
            # إذا كان موعد المعايرة التالية لم يحن بعد، يبقى الجهاز ملتزم
            if last_calibration.next_calibration_date >= timezone.now().date():
                compliant_devices += 1
        else:
            # إذا لم تتم معايرة الجهاز من قبل، نعتبره غير ملتزم
            pass
    
    compliance_rate = (compliant_devices / total_devices) * 100
    return compliance_rate

def get_monthly_trends(department_id=None, months=6):
    """
    جلب الاتجاهات الشهرية للمؤشرات
    هنا بنشوف إزاي الأداء بيتغير على مدار الشهور
    """
    trends = []
    
    for i in range(months):
        # حساب تاريخ بداية ونهاية الشهر
        current_date = timezone.now().replace(day=1) - timedelta(days=i*30)
        month_start = current_date.replace(day=1)
        month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        
        # حساب المؤشرات للشهر
        month_data = {
            'month': month_start.strftime('%Y-%m'),
            'month_name': calendar.month_name[month_start.month],
            'mtbf': calculate_mtbf(department_id=department_id, days=30),
            'mttr': calculate_mttr(department_id=department_id, days=30),
            'availability': calculate_availability(department_id=department_id, days=30),
            'pm_compliance': calculate_pm_compliance(department_id=department_id, days=30),
        }
        
        # إحصائيات أوامر الشغل للشهر
        wo_stats = calculate_work_order_stats(department_id=department_id, days=30)
        month_data.update({
            'total_work_orders': wo_stats['total'],
            'completion_rate': wo_stats['completion_rate'],
            'overdue_rate': wo_stats['overdue_rate'],
        })
        
        trends.append(month_data)
    
    # ترتيب البيانات من الأقدم للأحدث
    trends.reverse()
    return trends

def get_dashboard_summary(department_id=None):
    """
    جلب ملخص شامل للداشبورد
    هنا بنجمع كل المؤشرات المهمة في مكان واحد
    """
    summary = {
        # المؤشرات الأساسية
        'mtbf': calculate_mtbf(department_id=department_id),
        'mttr': calculate_mttr(department_id=department_id),
        'availability': calculate_availability(department_id=department_id),
        'pm_compliance': calculate_pm_compliance(department_id=department_id),
        'calibration_compliance': calculate_calibration_compliance(department_id=department_id),
        
        # إحصائيات أوامر الشغل
        'work_order_stats': calculate_work_order_stats(department_id=department_id),
        
        # إحصائيات قطع الغيار
        'spare_parts_stats': calculate_spare_parts_stats(department_id=department_id),
        
        # الاتجاهات الشهرية
        'monthly_trends': get_monthly_trends(department_id=department_id),
        
        # تاريخ آخر تحديث
        'last_updated': timezone.now(),
    }
    
    return summary

def get_device_performance_score(device_id):
    """
    حساب نقاط أداء الجهاز
    هنا بنعطي الجهاز نقاط من 100 بناء على أدائه
    """
    device = Device.objects.get(id=device_id)
    
    # المؤشرات الأساسية للجهاز
    mtbf = calculate_mtbf(device_id=device_id)
    mttr = calculate_mttr(device_id=device_id)
    availability = calculate_availability(device_id=device_id)
    
    # حساب النقاط (من 100)
    score = 0
    
    # نقاط التوفر (40% من النقاط)
    score += (availability / 100) * 40
    
    # نقاط MTBF (30% من النقاط)
    # كلما زاد MTBF، كلما زادت النقاط
    if mtbf > 0:
        mtbf_score = min(30, (mtbf / 168) * 30)  # 168 ساعة = أسبوع
        score += mtbf_score
    
    # نقاط MTTR (20% من النقاط)
    # كلما قل MTTR، كلما زادت النقاط
    if mttr > 0:
        mttr_score = max(0, 20 - (mttr / 24) * 20)  # 24 ساعة = يوم
        score += mttr_score
    else:
        score += 20  # إذا لم يكن هناك أعطال، نعطي النقاط كاملة
    
    # نقاط الصيانة الوقائية (10% من النقاط)
    pm_compliance = calculate_pm_compliance(device_id=device_id)
    score += (pm_compliance / 100) * 10
    
    return round(score, 1)

def get_critical_alerts(department_id=None):
    """
    جلب التنبيهات الحرجة
    هنا بنجمع كل التنبيهات المهمة اللي محتاجة انتباه فوري
    """
    alerts = []
    
    # أوامر الشغل المتأخرة
    overdue_work_orders = WorkOrder.objects.filter(
        status__in=['new', 'assigned', 'in_progress', 'wait_parts', 'on_hold', 'resolved'],
        service_request__resolution_due__lt=timezone.now()
    )
    
    if department_id:
        overdue_work_orders = overdue_work_orders.filter(
            service_request__device__department_id=department_id
        )
    
    for wo in overdue_work_orders[:5]:  # أول 5 بس
        alerts.append({
            'type': 'overdue_work_order',
            'severity': 'high',
            'title': f'أمر شغل متأخر: {wo.service_request.title}',
            'description': f'الجهاز: {wo.service_request.device.name}',
            'url': f'/maintenance/work-order/{wo.id}/',
            'created_at': wo.service_request.resolution_due,
        })
    
    # قطع الغيار المنتهية
    out_of_stock_parts = SparePart.objects.filter(status='out_of_stock')[:5]
    for part in out_of_stock_parts:
        alerts.append({
            'type': 'out_of_stock',
            'severity': 'medium',
            'title': f'قطعة غيار منتهية: {part.name}',
            'description': f'رقم القطعة: {part.part_number}',
            'url': f'/maintenance/spare-part/{part.id}/',
            'created_at': timezone.now(),
        })
    
    # قطع الغيار بمخزون منخفض
    low_stock_parts = SparePart.objects.filter(status='low_stock')[:5]
    for part in low_stock_parts:
        alerts.append({
            'type': 'low_stock',
            'severity': 'low',
            'title': f'مخزون منخفض: {part.name}',
            'description': f'الكمية المتبقية: {part.quantity}',
            'url': f'/maintenance/spare-part/{part.id}/',
            'created_at': timezone.now(),
        })
    
    # الأجهزة المحتاجة معايرة
    devices_need_calibration = Device.objects.filter(
        calibrations__next_calibration_date__lte=timezone.now().date() + timedelta(days=7)
    ).distinct()[:5]
    
    if department_id:
        devices_need_calibration = devices_need_calibration.filter(department_id=department_id)
    
    for device in devices_need_calibration:
        alerts.append({
            'type': 'calibration_due',
            'severity': 'medium',
            'title': f'معايرة مستحقة: {device.name}',
            'description': f'القسم: {device.department.name if hasattr(device, "department") else "غير محدد"}',
            'url': f'/maintenance/device/{device.id}/',
            'created_at': timezone.now(),
        })
    
    # ترتيب التنبيهات حسب الأولوية والتاريخ
    severity_order = {'high': 3, 'medium': 2, 'low': 1}
    alerts.sort(key=lambda x: (severity_order.get(x['severity'], 0), x['created_at']), reverse=True)
    
    return alerts[:10]  # أول 10 تنبيهات بس