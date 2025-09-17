# هنا بنحسب الـ KPIs والإحصائيات المهمة للـ CMMS عشان نعرف أداء الصيانة إزاي
from django.db.models import Count, Avg, Sum, Q, F
from django.db import models
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Device, SLADefinition
from .models import ServiceRequest, WorkOrder, PreventiveMaintenanceSchedule, SparePart
import calendar

def calculate_mtbf(device_id=None, department_id=None, days=30):
    """
    حساب متوسط الوقت بين الأعطال (MTBF) باستخدام الأوقات الفعلية من Work Orders
    """
    # تحديد الفترة الزمنية
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)
    
    # جلب الأجهزة
    devices = Device.objects.all()
    if device_id:
        devices = devices.filter(id=device_id)
    if department_id:
        devices = devices.filter(department_id=department_id)
    
    total_mtbf = 0
    device_count = 0
    
    for device in devices:
        # جلب أوامر الشغل للأعطال التصحيحية والطارئة
        work_orders = WorkOrder.objects.filter(
            service_request__device=device,
            service_request__request_type__in=['corrective', 'breakdown'],
            created_at__range=[start_date, end_date]
        ).order_by('created_at')
        
        failure_count = work_orders.count()
        
        if failure_count >= 2:
            # حساب الفترات بين الأعطال باستخدام الأوقات الفعلية
            intervals = []
            for i in range(1, failure_count):
                prev_wo = work_orders[i-1]
                curr_wo = work_orders[i]
                
                # استخدام actual_end إذا متوفر، وإلا استخدام created_at
                prev_end = prev_wo.actual_end if prev_wo.actual_end else prev_wo.created_at
                curr_start = curr_wo.actual_start if curr_wo.actual_start else curr_wo.created_at
                
                interval_hours = (curr_start - prev_end).total_seconds() / 3600
                if interval_hours > 0:
                    intervals.append(interval_hours)
            
            if intervals:
                device_mtbf = sum(intervals) / len(intervals)
                total_mtbf += device_mtbf
                device_count += 1
        elif failure_count == 1:
            # عطل واحد فقط - نحسب من بداية الفترة
            first_wo = work_orders.first()
            first_failure = first_wo.actual_start if first_wo.actual_start else first_wo.created_at
            hours_to_failure = (first_failure - start_date).total_seconds() / 3600
            if hours_to_failure > 0:
                total_mtbf += hours_to_failure
                device_count += 1
        else:
            # لا توجد أعطال - الجهاز يعمل بدون مشاكل
            if device.status == 'working':
                # نعتبر أن الجهاز عمل طوال الفترة
                estimated_mtbf = days * 24
                total_mtbf += estimated_mtbf
                device_count += 1
            elif device.status == 'needs_check':
                estimated_mtbf = days * 20  # 80% من الفترة
                total_mtbf += estimated_mtbf
                device_count += 1
            elif device.status == 'needs_maintenance':
                estimated_mtbf = days * 12  # 50% من الفترة
                total_mtbf += estimated_mtbf
                device_count += 1
            # نتجاهل الأجهزة المعطلة out_of_order
    
    return total_mtbf / device_count if device_count > 0 else 720  # متوسط شهر إذا لم توجد بيانات

def calculate_mttr(device_id=None, department_id=None, days=30):
    """
    حساب متوسط وقت الإصلاح (MTTR) باستخدام الأوقات الفعلية من Work Orders
    """
    from .models import SLADefinition, JobPlan
    
    # تحديد الفترة الزمنية
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)
    
    # جلب أوامر الشغل للأعطال التصحيحية والطارئة
    work_orders = WorkOrder.objects.filter(
        created_at__range=[start_date, end_date],
        service_request__request_type__in=['corrective', 'breakdown']
    )
    
    if device_id:
        work_orders = work_orders.filter(service_request__device_id=device_id)
    if department_id:
        work_orders = work_orders.filter(service_request__device__department_id=department_id)
    
    total_repair_time = 0
    valid_orders = 0
    
    for wo in work_orders:
        repair_time = 0
        
        # استخدام actual_hours إذا متوفرة
        if hasattr(wo, 'actual_hours') and wo.actual_hours:
            repair_time = float(wo.actual_hours)
        # استخدام الفرق بين actual_start و actual_end
        elif wo.actual_start and wo.actual_end:
            repair_time = (wo.actual_end - wo.actual_start).total_seconds() / 3600
        # استخدام estimated_hours إذا متوفرة
        elif hasattr(wo, 'estimated_hours') and wo.estimated_hours:
            repair_time = float(wo.estimated_hours)
        # تقدير من الفرق بين created_at و updated_at للأوامر المكتملة
        elif wo.status in ['closed', 'qa_verified','resolved'] and wo.updated_at and wo.created_at:
            repair_time = (wo.updated_at - wo.created_at).total_seconds() / 3600
            # تحديد حد أقصى معقول
            repair_time = min(repair_time, 72)  # حد أقصى 3 أيام
        # للأوامر المفتوحة، نحسب الوقت المنقضي حتى الآن
        elif wo.status in ['new', 'assigned', 'in_progress', 'wait_parts']:
            repair_time = (timezone.now() - wo.created_at).total_seconds() / 3600
            # تحديد حد أقصى معقول
            repair_time = min(repair_time, 48)  # حد أقصى يومين للأوامر المفتوحة
        else:
            # تقدير بناءً على الأولوية
            if wo.service_request.priority == 'critical':
                repair_time = 2
            elif wo.service_request.priority == 'high':
                repair_time = 4
            elif wo.service_request.priority == 'medium':
                repair_time = 8
            else:
                repair_time = 24
        
        if repair_time > 0:
            total_repair_time += repair_time
            valid_orders += 1
    
    # إذا لم توجد أوامر شغل، نستخدم تقديرات بناءً على الأجهزة
    if valid_orders == 0:
        devices = Device.objects.all()
        if device_id:
            devices = devices.filter(id=device_id)
        if department_id:
            devices = devices.filter(department_id=department_id)
        
        # إذا لم توجد أجهزة، نرجع قيمة افتراضية
        if not devices.exists():
            return 4.0
        
        total_estimated_mttr = 0
        device_count = 0
        
        for device in devices:
            # البحث عن SLA مناسب
            applicable_sla = None
            if device.category:
                sla_definitions = SLADefinition.objects.filter(
                    is_active=True,
                    device_category=device.category
                )
                if sla_definitions.exists():
                    applicable_sla = sla_definitions.first()
            
            # البحث عن خطة عمل مناسبة
            job_plan_duration = None
            if device.category:
                job_plans = JobPlan.objects.filter(device_category=device.category, is_active=True)
                if job_plans.exists():
                    job_plan = job_plans.first()
                    if hasattr(job_plan, 'estimated_hours') and job_plan.estimated_hours:
                        job_plan_duration = float(job_plan.estimated_hours)
            
            # تحديد MTTR بناءً على المصادر المتاحة
            if applicable_sla:
                estimated_mttr = float(applicable_sla.resolution_time_hours)
            elif job_plan_duration:
                estimated_mttr = job_plan_duration
            else:
                # تقدير بناءً على حالة الجهاز
                if device.status == 'working':
                    estimated_mttr = 2.0
                elif device.status == 'needs_check':
                    estimated_mttr = 4.0
                elif device.status == 'needs_maintenance':
                    estimated_mttr = 8.0
                elif device.status == 'out_of_order':
                    estimated_mttr = 24.0
                else:
                    estimated_mttr = 6.0
            
            total_estimated_mttr += estimated_mttr
            device_count += 1
        
        return total_estimated_mttr / device_count if device_count > 0 else 4.0
    
    return total_repair_time / valid_orders if valid_orders > 0 else 4.0

def calculate_availability(device_id=None, department_id=None, days=30):
    """
    حساب نسبة التوفر (Availability) بناءً على SLA وخطط العمل والبيانات الفعلية
    """
    from .models import SLADefinition, JobPlan
    
    # تحديد الفترة الزمنية
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)
    
    # جلب الأجهزة
    devices = Device.objects.all()
    if device_id:
        devices = devices.filter(id=device_id)
    if department_id:
        devices = devices.filter(department_id=department_id)
    
    total_availability = 0
    device_count = 0
    
    for device in devices:
        # البحث عن SLA مناسب للجهاز
        applicable_sla = None
        if device.category:
            sla_definitions = SLADefinition.objects.filter(
                is_active=True,
                device_category=device.category
            )
            if sla_definitions.exists():
                applicable_sla = sla_definitions.first()
        
        # حساب التوفر بناءً على أوامر الشغل الفعلية
        corrective_work_orders = WorkOrder.objects.filter(
            service_request__device=device,
            service_request__request_type='corrective',
            created_at__range=[start_date, end_date]
        )
        
        total_downtime_hours = 0
        
        # حساب الـ downtime من أوامر الشغل المكتملة
        completed_orders = corrective_work_orders.filter(status__in=['closed', 'qa_verified'])
        for wo in completed_orders:
            if wo.actual_start and wo.actual_end:
                downtime = (wo.actual_end - wo.actual_start).total_seconds() / 3600
            elif applicable_sla:
                downtime = applicable_sla.resolution_time_hours
            else:
                # تقدير بناءً على الأولوية
                if wo.service_request.priority == 'critical':
                    downtime = 2
                elif wo.service_request.priority == 'high':
                    downtime = 4
                elif wo.service_request.priority == 'medium':
                    downtime = 8
                else:
                    downtime = 24
            
            total_downtime_hours += downtime
        
        # حساب الـ downtime من أوامر الشغل المفتوحة
        open_orders = corrective_work_orders.filter(
            status__in=['new', 'assigned', 'in_progress', 'wait_parts']
        )
        
        for wo in open_orders:
            # حساب الوقت المنقضي منذ بداية العطل
            elapsed_time = (timezone.now() - wo.created_at).total_seconds() / 3600
            
            if applicable_sla:
                # إذا تجاوز الوقت المحدد في SLA، نحسب كامل الوقت
                expected_resolution = applicable_sla.resolution_time_hours
                downtime = max(elapsed_time, expected_resolution)
            else:
                downtime = elapsed_time
            
            total_downtime_hours += downtime
        
        # حساب نسبة التوفر الأساسية
        total_period_hours = days * 24
        uptime_hours = max(0, total_period_hours - total_downtime_hours)
        device_availability = (uptime_hours / total_period_hours) * 100
        
        # تطبيق تأثير حالة الجهاز على التوفر
        if device.status == 'out_of_order':
            device_availability = 0
        elif device.status == 'needs_maintenance':
            # إذا كان هناك SLA، نستخدم نسبة مبنية على مدى تجاوز SLA
            if applicable_sla:
                device_availability = min(device_availability, 40)
            else:
                device_availability = min(device_availability, 30)
        elif device.status == 'needs_check':
            if applicable_sla:
                device_availability = min(device_availability, 80)
            else:
                device_availability = min(device_availability, 70)
        elif device.status == 'working':
            if applicable_sla:
                device_availability = min(device_availability, 98)  # SLA عادة يستهدف 98%+
            else:
                device_availability = min(device_availability, 95)
        
        # تطبيق تأثير الصيانة الوقائية المجدولة
        try:
            pm_schedules = PreventiveMaintenanceSchedule.objects.filter(
                device=device,
                next_due_date__range=[start_date.date(), end_date.date()]
            )
            
            for pm in pm_schedules:
                if pm.job_plan:
                    # محاولة الحصول على الوقت المقدر من خطة العمل
                    pm_downtime = 0
                    if hasattr(pm.job_plan, 'estimated_hours') and pm.job_plan.estimated_hours:
                        pm_downtime = float(pm.job_plan.estimated_hours)
                    elif hasattr(pm.job_plan, 'estimated_duration') and pm.job_plan.estimated_duration:
                        pm_downtime = pm.job_plan.estimated_duration.total_seconds() / 3600
                    else:
                        # تقدير افتراضي للصيانة الوقائية (ساعتان)
                        pm_downtime = 2
                    
                    total_downtime_hours += pm_downtime
                    # إعادة حساب التوفر
                    uptime_hours = max(0, total_period_hours - total_downtime_hours)
                    device_availability = (uptime_hours / total_period_hours) * 100
        except Exception as e:
            # في حالة وجود خطأ، نتجاهل تأثير الصيانة الوقائية
            pass
        
        total_availability += max(0, device_availability)
        device_count += 1
    
    return total_availability / device_count if device_count > 0 else 0

def calculate_pm_compliance(department_id=None, device_id=None, days=30):
    """
    حساب نسبة الالتزام بالصيانة الوقائية
    هنا بنشوف قد إيه بنلتزم بجداول الصيانة الوقائية
    """
    # تحديد الفترة الزمنية
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)
    
    # جلب جداول الصيانة الوقائية المستحقة في الفترة
    pm_schedules = PreventiveMaintenanceSchedule.objects.filter(
        is_active=True,
        next_due_date__range=[start_date.date(), end_date.date()]
    )
    
    if device_id:
        pm_schedules = pm_schedules.filter(device_id=device_id)
    elif department_id:
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
            created_at__range=[start_date, end_date],
            status__in=['closed', 'qa_verified' ,'resolved']
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
    
    # جلب أوامر الشغل (بدون تقييد بالفترة الزمنية أولاً لنرى كل البيانات)
    work_orders = WorkOrder.objects.all()
    
    if department_id:
        work_orders = work_orders.filter(service_request__device__department_id=department_id)
    
    # إحصائيات حسب الحالة (جميع أوامر الشغل)
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
    
    # إضافة إحصائيات الفترة الزمنية المحددة
    period_work_orders = work_orders.filter(created_at__range=[start_date, end_date])
    stats['period_total'] = period_work_orders.count()
    
    # حساب النسب المئوية
    if stats['total'] > 0:
        stats['completion_rate'] = ((stats['closed'] + stats['qa_verified'] + stats['resolved']) / stats['total']) * 100
        stats['in_progress_rate'] = ((stats['assigned'] + stats['in_progress'] + stats['wait_parts']) / stats['total']) * 100
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
        if sr and sr.resolution_due and timezone.now() > sr.resolution_due:
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
        if part.unit_cost and part.current_stock:
            total_inventory_value += part.unit_cost * part.current_stock
    
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
        last_calibration = device.calibration_records.filter(
            status__in=['closed', 'completed', 'resolved']
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
    import calendar
    from django.db.models import Count, Avg, Q
    from .models import ServiceRequest, WorkOrder, Device
    
    trends = []
    
    for i in range(months):
        # حساب تاريخ بداية ونهاية الشهر
        current_date = timezone.now().replace(day=1) - timedelta(days=i*30)
        month_start = current_date.replace(day=1)
        
        # حساب نهاية الشهر بدقة
        if month_start.month == 12:
            month_end = month_start.replace(year=month_start.year + 1, month=1) - timedelta(days=1)
        else:
            month_end = month_start.replace(month=month_start.month + 1) - timedelta(days=1)
        
        # فلتر الأجهزة حسب القسم إن وجد
        devices_filter = Q()
        if department_id:
            devices_filter = Q(department_id=department_id)
        
        # حساب إحصائيات أوامر الشغل للشهر المحدد
        work_orders_month = WorkOrder.objects.filter(
            created_at__range=[month_start, month_end]
        )
        if department_id:
            work_orders_month = work_orders_month.filter(
                service_request__device__department_id=department_id
            )
        
        total_wo = work_orders_month.count()
        completed_wo = work_orders_month.filter(status__in=['closed', 'qa_verified', 'resolved']).count()
        overdue_wo = work_orders_month.filter(
            actual_end__isnull=True,
            service_request__resolution_due__lt=timezone.now()
        ).count()
        
        # حساب نسب الأداء للشهر
        completion_rate = (completed_wo / total_wo * 100) if total_wo > 0 else 0
        overdue_rate = (overdue_wo / total_wo * 100) if total_wo > 0 else 0
        
        # حساب متوسط وقت الإصلاح للشهر
        completed_orders = work_orders_month.filter(
            status__in=['closed', 'qa_verified', 'resolved'],
            actual_end__isnull=False,
            actual_start__isnull=False
        )
        
        if completed_orders.exists():
            total_repair_time = 0
            count = 0
            for wo in completed_orders:
                repair_time = (wo.actual_end - wo.actual_start).total_seconds() / 3600
                total_repair_time += repair_time
                count += 1
            mttr = total_repair_time / count if count > 0 else 0
        else:
            mttr = 0
        
        # حساب نسبة التوفر (تقدير بناءً على أوامر الشغل)
        # نسبة التوفر = 100 - (نسبة الأعطال * متوسط وقت الإصلاح / 24)
        failure_rate = (total_wo / 30) if total_wo > 0 else 0  # معدل الأعطال في اليوم
        availability = max(0, 100 - (failure_rate * mttr / 24 * 100))
        
        # حساب الالتزام بالصيانة الوقائية للشهر
        preventive_orders = work_orders_month.filter(
            service_request__request_type='preventive'
        ).count()
        pm_compliance = (preventive_orders / total_wo * 100) if total_wo > 0 else 0
        
        month_data = {
            'month': month_start.strftime('%Y-%m'),
            'month_name': calendar.month_name[month_start.month],
            'mtbf': 720 / failure_rate if failure_rate > 0 else 720,  # تقدير MTBF بالساعات
            'mttr': round(mttr, 1),
            'availability': round(availability, 1),
            'pm_compliance': round(pm_compliance, 1),
            'total_work_orders': total_wo,
            'completion_rate': round(completion_rate, 1),
            'overdue_rate': round(overdue_rate, 1),
        }
        
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
    # للأجهزة الجديدة بدون أعطال، نعطي النقاط الكاملة
    from .models import WorkOrder
    
    # فحص وجود أعطال فعلية للجهاز
    has_failures = WorkOrder.objects.filter(
        service_request__device_id=device_id,
        service_request__request_type='corrective',
        status__in=['closed', 'qa_verified','resolved']
    ).exists()
    
    if not has_failures:
        # الجهاز مالوش أعطال = النقاط الكاملة
        score += 20
    elif mttr > 0:
        mttr_score = max(0, 20 - (mttr / 24) * 20)  # 24 ساعة = يوم
        score += mttr_score
    else:
        score += 20
    
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
        created_at__lt=timezone.now() - timezone.timedelta(days=7)  # استخدام created_at بدلاً من resolution_due
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
            'url': f'/maintenance/cmms/work-orders/{wo.id}/',
            'created_at': wo.service_request.resolution_due,
        })
    
    # قطع الغيار المنتهية
    out_of_stock_parts = SparePart.objects.filter(current_stock=0)[:5]
    for part in out_of_stock_parts:
        alerts.append({
            'type': 'out_of_stock',
            'severity': 'medium',
            'title': f'قطعة غيار منتهية: {part.name}',
            'description': f'رقم القطعة: {part.part_number}',
            'url': f'/maintenance/spare-parts/{part.id}/',
            'created_at': timezone.now(),
        })
    
    # قطع الغيار بمخزون منخفض
    low_stock_parts = SparePart.objects.filter(current_stock__lte=models.F('minimum_stock'))[:5]
    for part in low_stock_parts:
        alerts.append({
            'type': 'low_stock',
            'severity': 'low',
            'title': f'مخزون منخفض: {part.name}',
            'description': f'الكمية المتبقية: {part.current_stock}',
            'url': f'/maintenance/spare-parts/{part.id}/',
            'created_at': timezone.now(),
        })
    
    # الأجهزة المحتاجة معايرة
    devices_need_calibration = Device.objects.filter(
        calibration_records__next_calibration_date__lte=timezone.now().date() + timedelta(days=7)
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