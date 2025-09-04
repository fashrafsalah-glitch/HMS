"""
مهام الخلفية للصيانة - Background Tasks for Maintenance
يحتوي على المهام التي تعمل في الخلفية لإدارة الصيانة التلقائية
"""

import threading
import time
import schedule
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

class MaintenanceTaskRunner:
    """
    مدير المهام التلقائية للصيانة
    يشغل المهام في الخلفية بدون الحاجة لتدخل بشري
    """
    
    def __init__(self):
        self.running = False
        self.thread = None
        
    def start(self):
        """بدء تشغيل المهام التلقائية"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._run_scheduler, daemon=True)
            self.thread.start()
            logger.info("تم بدء تشغيل مهام الصيانة التلقائية")
    
    def stop(self):
        """إيقاف المهام التلقائية"""
        self.running = False
        if self.thread:
            self.thread.join()
        logger.info("تم إيقاف مهام الصيانة التلقائية")
    
    def _run_scheduler(self):
        """تشغيل الجدولة في الخلفية"""
        # جدولة جميع المهام كل دقيقة للتطوير والمراقبة المكثفة
        print("=" * 80)
        print(f"DEBUG: Starting task scheduler at {timezone.now()}")
        print("=" * 80)
        
        # جدولة جميع المهام كل دقيقة
        schedule.every(1).minutes.do(self._check_pm_schedules)
        print("DEBUG: ✓ PM schedule check scheduled every 1 minute")
        
        schedule.every(1).minutes.do(self._check_sla_violations)
        print("DEBUG: ✓ SLA violations check scheduled every 1 minute")
        
        schedule.every(1).minutes.do(self._daily_maintenance_check)
        print("DEBUG: ✓ Daily maintenance check scheduled every 1 minute")
        
        schedule.every(1).minutes.do(self._send_daily_reports)
        print("DEBUG: ✓ Daily reports scheduled every 1 minute")
        
        schedule.every(1).minutes.do(self._monitor_downtime_schedules)
        print("DEBUG: ✓ Downtime monitoring scheduled every 1 minute")
        
        schedule.every(1).minutes.do(self._check_calibration_schedules)
        print("DEBUG: ✓ Calibration schedule check scheduled every 1 minute")
        
        print("=" * 80)
        print("DEBUG: All tasks scheduled to run every minute!")
        print("=" * 80)
        
        logger.info("تم إعداد جدولة المهام التلقائية")
        
        while self.running:
            try:
                current_time = timezone.now()
                print(f"\n🔄 SCHEDULER TICK: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
                print("-" * 60)
                
                # تشغيل المهام المجدولة
                pending_jobs = schedule.get_jobs()
                print(f"DEBUG: Found {len(pending_jobs)} scheduled jobs")
                
                schedule.run_pending()
                
                print(f"DEBUG: Scheduler cycle completed at {timezone.now().strftime('%H:%M:%S')}")
                print("-" * 60)
                
                time.sleep(60)  # فحص كل دقيقة
            except Exception as e:
                error_time = timezone.now()
                logger.error(f"خطأ في تشغيل المهام المجدولة في {error_time}: {str(e)}")
                print(f"❌ SCHEDULER ERROR at {error_time}: {str(e)}")
                time.sleep(60)  # انتظار دقيقة واحدة عند حدوث خطأ
    
    def _check_pm_schedules(self):
        """فحص جداول الصيانة الوقائية وإنشاء أوامر الشغل"""
        start_time = timezone.now()
        print(f"\n🔧 PREVENTIVE MAINTENANCE CHECK Started at {start_time.strftime('%H:%M:%S')}")
        try:
            from .models import PreventiveMaintenanceSchedule
            
            # عد الجداول النشطة
            active_schedules = PreventiveMaintenanceSchedule.objects.filter(is_active=True)
            print(f"   📊 Found {active_schedules.count()} active PM schedules")
            
            # عد الجداول المستحقة
            from datetime import date
            today = date.today()
            due_schedules = active_schedules.filter(next_due_date__lte=today)
            print(f"   ⏰ Found {due_schedules.count()} schedules due today or overdue")
            
            if due_schedules.exists():
                print(f"   🚀 Processing due schedules...")
                for schedule in due_schedules:
                    print(f"      - {schedule.device.name}: Due {schedule.next_due_date}")
            
            result = PreventiveMaintenanceSchedule.check_and_generate_work_orders()
            
            end_time = timezone.now()
            duration = (end_time - start_time).total_seconds()
            print(f"   ✅ PM check completed in {duration:.2f}s, result: {result}")
            
        except Exception as e:
            error_time = timezone.now()
            duration = (error_time - start_time).total_seconds()
            logger.error(f"خطأ في فحص الصيانة الوقائية: {str(e)}")
            print(f"   ❌ PM check failed after {duration:.2f}s: {str(e)}")
    
    def _check_sla_violations(self):
        """فحص انتهاكات SLA وإرسال تنبيهات"""
        try:
            from .models import ServiceRequest, WorkOrder
            
            now = timezone.now()
            
            # فحص البلاغات المتأخرة
            overdue_requests = ServiceRequest.objects.filter(
                status__in=['new', 'assigned', 'in_progress'],
                created_at__lt=now - timedelta(days=7)  # استخدام created_at بدلاً من resolution_due
            )
            
            for request in overdue_requests:
                logger.warning(f"بلاغ متأخر: {request.id} - {request.title}")
                # إرسال تنبيه للمسؤولين
                self._send_sla_violation_alert(request)
            
            # فحص أوامر الشغل المتأخرة
            overdue_work_orders = WorkOrder.objects.filter(
                status__in=['new', 'assigned', 'in_progress'],
                scheduled_end__lt=now
            )
            
            for wo in overdue_work_orders:
                logger.warning(f"أمر شغل متأخر: {wo.wo_number} - {wo.title}")
                
        except Exception as e:
            logger.error(f"خطأ في فحص انتهاكات SLA: {str(e)}")
    
    def _daily_maintenance_check(self):
        """الفحص اليومي للصيانة"""
        try:
            from .models import Device
            
            # فحص الأجهزة التي تحتاج صيانة
            devices_need_maintenance = Device.objects.filter(
                status__in=['needs_maintenance', 'needs_check']
            )
            
            if devices_need_maintenance.exists():
                logger.info(f"يوجد {devices_need_maintenance.count()} جهاز يحتاج صيانة")
            
            # فحص قطع الغيار المنخفضة
            from .models import SparePart
            from django.db import models
            low_stock_parts = SparePart.objects.filter(
                current_stock__lte=models.F('minimum_stock')
            )
            
            if low_stock_parts.exists():
                logger.warning(f"يوجد {low_stock_parts.count()} قطعة غيار منخفضة المخزون")
                
        except Exception as e:
            logger.error(f"خطأ في الفحص اليومي: {str(e)}")
    
    def _send_daily_reports(self):
        """إرسال التقارير اليومية"""
        try:
            from .models import WorkOrder, ServiceRequest
            
            today = timezone.now().date()
            
            # إحصائيات اليوم
            today_work_orders = WorkOrder.objects.filter(created_at__date=today)
            today_requests = ServiceRequest.objects.filter(created_at__date=today)
            
            logger.info(f"تقرير يومي - أوامر الشغل: {today_work_orders.count()}, البلاغات: {today_requests.count()}")
            
        except Exception as e:
            logger.error(f"خطأ في إرسال التقارير اليومية: {str(e)}")
    
    def _send_sla_violation_alert(self, service_request):
        """إرسال تنبيه انتهاك SLA"""
        try:
            from .models import SystemNotification
            
            SystemNotification.objects.create(
                title="انتهاك SLA",
                message=f"البلاغ {service_request.id} متأخر عن الموعد المحدد",
                notification_type='sla_violation',
                priority='high',
                related_object_type='service_request',
                related_object_id=service_request.id
            )
            
        except Exception as e:
            logger.error(f"خطأ في إرسال تنبيه SLA: {str(e)}")

    def _monitor_downtime_schedules(self):
        """مراقبة جداول التوقف لأوامر الشغل وطلبات الخدمة"""
        try:
            from .models import WorkOrder, ServiceRequest, DeviceDowntime
            from decimal import Decimal
            
            now = timezone.now()
            print(f"DEBUG: Running downtime monitoring at {now}")
            
            # فحص أوامر الشغل النشطة (التي لها جهاز مرتبط عبر طلب الخدمة)
            active_work_orders = WorkOrder.objects.filter(
                status__in=['new', 'assigned', 'in_progress'],
                service_request__device__isnull=False
            ).select_related('service_request__device')
            
            # فحص طلبات الخدمة النشطة
            active_service_requests = ServiceRequest.objects.filter(
                status__in=['new', 'assigned', 'in_progress'],
                device__isnull=False
            ).select_related('device')
            
            processed_count = 0
            
            # معالجة أوامر الشغل
            for wo in active_work_orders:
                device = wo.service_request.device
                processed_count += self._process_device_downtime(device, wo, None, now)
            
            # معالجة طلبات الخدمة التي ليس لها أوامر شغل نشطة
            for sr in active_service_requests:
                # التحقق من عدم وجود أوامر شغل نشطة لهذا الطلب
                has_active_wo = sr.work_orders.filter(
                    status__in=['new', 'assigned', 'in_progress']
                ).exists()
                
                if not has_active_wo:
                    processed_count += self._process_device_downtime(sr.device, None, sr, now)
            
            # فحص وإنهاء سجلات التوقف للأعمال المكتملة
            ended_count = self._end_completed_downtimes(now)
            
            if processed_count > 0:
                logger.info(f"تم معالجة {processed_count} جهاز في مراقبة التوقف")
                print(f"DEBUG: Processed {processed_count} devices for downtime monitoring")
                
            if ended_count > 0:
                logger.info(f"تم إنهاء {ended_count} سجل توقف للأعمال المكتملة")
                print(f"DEBUG: Ended {ended_count} downtime records for completed work")
                
        except Exception as e:
            logger.error(f"خطأ في مراقبة جداول التوقف: {str(e)}")
            print(f"DEBUG: Downtime monitoring error: {str(e)}")

    def _process_device_downtime(self, device, work_order, service_request, current_time):
        """معالجة توقف جهاز واحد"""
        try:
            from .models import DeviceDowntime
            
            # البحث عن توقف نشط للجهاز
            active_downtime = DeviceDowntime.objects.filter(
                device=device,
                end_time__isnull=True
            ).first()
            
            if active_downtime:
                # تحديث التوقف الموجود
                return self._update_existing_downtime(active_downtime, work_order, service_request, current_time)
            else:
                # إنشاء توقف جديد
                return self._create_new_downtime(device, work_order, service_request, current_time)
                
        except Exception as e:
            logger.error(f"خطأ في معالجة توقف الجهاز {device.id}: {str(e)}")
            print(f"DEBUG: Error processing device downtime: {str(e)}")
            return 0

    def _update_existing_downtime(self, downtime, work_order, service_request, current_time):
        """تحديث توقف موجود"""
        try:
            updated = False
            
            # تحديث أمر الشغل إذا لم يكن مربوط
            if work_order and not downtime.work_order:
                downtime.work_order = work_order
                updated = True
                
            # تحديث السبب والوصف حسب نوع العمل
            if work_order:
                new_reason = self._determine_downtime_reason(work_order.wo_type)
                if downtime.reason != new_reason:
                    downtime.reason = new_reason
                    updated = True
                    
                if not downtime.description and work_order.description:
                    downtime.description = f"أمر شغل: {work_order.title} - {work_order.description}"
                    updated = True
                    
            elif service_request:
                if not downtime.description and service_request.description:
                    downtime.description = f"طلب خدمة: {service_request.title} - {service_request.description}"
                    updated = True
            
            if updated:
                downtime.save()
                print(f"DEBUG: Updated existing downtime {downtime.id} for device {downtime.device.id}")
                return 1
                
        except Exception as e:
            logger.error(f"خطأ في تحديث التوقف الموجود: {str(e)}")
            print(f"DEBUG: Error updating downtime: {str(e)}")
            
        return 0

    def _end_completed_downtimes(self, current_time):
        """إنهاء سجلات التوقف للأعمال المكتملة"""
        try:
            from .models import DeviceDowntime, WorkOrder, ServiceRequest
            
            ended_count = 0
            
            # البحث عن سجلات التوقف النشطة
            active_downtimes = DeviceDowntime.objects.filter(
                end_time__isnull=True
            ).select_related('work_order', 'device')
            
            for downtime in active_downtimes:
                should_end = False
                end_reason = ""
                
                # فحص أمر الشغل المرتبط
                if downtime.work_order:
                    wo = downtime.work_order
                    if wo.status in ['completed', 'cancelled', 'closed']:
                        should_end = True
                        end_reason = f"تم إنهاء أمر الشغل {wo.wo_number} - الحالة: {wo.get_status_display()}"
                        # استخدام تاريخ الإكمال الفعلي من أمر الشغل
                        if hasattr(wo, 'completed_at') and wo.completed_at:
                            current_time = wo.completed_at
                            print(f"DEBUG: Using WO completed_at: {current_time} for downtime {downtime.id}")
                        elif hasattr(wo, 'actual_end') and wo.actual_end:
                            current_time = wo.actual_end
                            print(f"DEBUG: Using WO actual_end: {current_time} for downtime {downtime.id}")
                        elif wo.updated_at:
                            current_time = wo.updated_at
                            print(f"DEBUG: Using WO updated_at: {current_time} for downtime {downtime.id}")
                        # إذا لم يوجد تاريخ إكمال، استخدم الوقت الحالي
                
                # فحص طلبات الخدمة المرتبطة بالجهاز
                if not should_end:
                    # البحث عن طلبات خدمة مكتملة للجهاز
                    completed_srs = ServiceRequest.objects.filter(
                        device=downtime.device,
                        status__in=['resolved', 'closed', 'completed']
                    ).order_by('-resolved_at', '-closed_at', '-updated_at')
                    
                    # البحث عن طلبات خدمة نشطة للجهاز
                    active_srs = ServiceRequest.objects.filter(
                        device=downtime.device,
                        status__in=['new', 'assigned', 'in_progress']
                    )
                    
                    # إذا لم توجد طلبات خدمة نشطة ولا أوامر شغل نشطة
                    if not active_srs.exists():
                        active_wos = WorkOrder.objects.filter(
                            service_request__device=downtime.device,
                            status__in=['new', 'assigned', 'in_progress']
                        )
                        
                        if not active_wos.exists():
                            should_end = True
                            end_reason = "لا توجد أعمال نشطة للجهاز"
                            
                            # استخدام تاريخ حل آخر طلب خدمة إذا وجد
                            if completed_srs.exists():
                                latest_sr = completed_srs.first()
                                if hasattr(latest_sr, 'resolved_at') and latest_sr.resolved_at:
                                    current_time = latest_sr.resolved_at
                                    print(f"DEBUG: Using SR resolved_at: {current_time} for downtime {downtime.id}")
                                elif hasattr(latest_sr, 'closed_at') and latest_sr.closed_at:
                                    current_time = latest_sr.closed_at
                                    print(f"DEBUG: Using SR closed_at: {current_time} for downtime {downtime.id}")
                                elif latest_sr.updated_at:
                                    current_time = latest_sr.updated_at
                                    print(f"DEBUG: Using SR updated_at: {current_time} for downtime {downtime.id}")
                
                # إنهاء سجل التوقف إذا لزم الأمر
                if should_end:
                    downtime.end_time = current_time
                    
                    # إضافة ملاحظة الإنهاء مع التاريخ
                    end_note = f"\n\nتم الإنهاء تلقائياً: {end_reason}\nتاريخ النهاية: {current_time}"
                    if downtime.description:
                        downtime.description += end_note
                    else:
                        downtime.description = f"تم الإنهاء تلقائياً: {end_reason}\nتاريخ النهاية: {current_time}"
                    
                    downtime.save()
                    ended_count += 1
                    
                    logger.info(f"تم إنهاء سجل التوقف {downtime.id} للجهاز {downtime.device.name} في {current_time}")
                    print(f"DEBUG: Ended downtime {downtime.id} for device {downtime.device.name} at {current_time} - {end_reason}")
            
            return ended_count
            
        except Exception as e:
            logger.error(f"خطأ في إنهاء سجلات التوقف المكتملة: {str(e)}")
            print(f"DEBUG: Error ending completed downtimes: {str(e)}")
            return 0

    def _create_new_downtime(self, device, work_order, service_request, current_time):
        """إنشاء توقف جديد للجهاز"""
        try:
            from .models import DeviceDowntime
            from django.contrib.auth import get_user_model
            
            User = get_user_model()
            
            # تحديد السبب والتأثير
            reason = 'other'
            impact_description = 'توقف الجهاز عن العمل'
            financial_impact = self._get_existing_cost(work_order, service_request)
            
            if work_order:
                reason = self._determine_downtime_reason(work_order.wo_type)
                description = f"أمر شغل: {work_order.title}"
                reported_by = work_order.created_by
            elif service_request:
                reason = 'breakdown' if service_request.priority in ['high', 'critical'] else 'maintenance'
                description = f"طلب خدمة: {service_request.title}"
                reported_by = service_request.requested_by
            else:
                description = "توقف تلقائي - تم اكتشافه بواسطة النظام"
                # استخدام أول مستخدم متاح أو إنشاء مستخدم النظام
                reported_by = User.objects.filter(is_superuser=True).first()
                if not reported_by:
                    reported_by = User.objects.first()
            
            # إنشاء سجل التوقف
            downtime = DeviceDowntime.objects.create(
                device=device,
                start_time=current_time,
                reason=reason,
                description=description,
                reported_by=reported_by,
                work_order=work_order
            )
            
            # إضافة معلومات التأثير والتأثير المالي كملاحظات
            if financial_impact:
                impact_notes = f"التأثير: {impact_description}\nالتأثير المالي من أمر الشغل: {financial_impact} ريال"
            else:
                impact_notes = f"التأثير: {impact_description}\nالتأثير المالي: غير محدد"
            if downtime.description:
                downtime.description += f"\n{impact_notes}"
            else:
                downtime.description = impact_notes
            downtime.save()
            
            logger.info(f"تم إنشاء توقف جديد للجهاز {device.name} - السبب: {reason}")
            print(f"DEBUG: Created new downtime {downtime.id} for device {device.id}")
            
            return 1
            
        except Exception as e:
            logger.error(f"خطأ في إنشاء توقف جديد للجهاز {device.id}: {str(e)}")
            return 0

    def _determine_downtime_reason(self, wo_type):
        """تحديد سبب التوقف حسب نوع أمر الشغل"""
        reason_mapping = {
            'corrective': 'breakdown',
            'preventive': 'maintenance',
            'predictive': 'maintenance',
            'emergency': 'breakdown',
            'calibration': 'calibration',
            'inspection': 'maintenance'
        }
        return reason_mapping.get(wo_type, 'other')

    def _get_existing_cost(self, work_order, service_request):
        """استخراج التكلفة الموجودة من أمر الشغل أو طلب الخدمة"""
        try:
            if work_order:
                # محاولة الحصول على التكلفة من أمر الشغل
                if work_order.total_cost:
                    return float(work_order.total_cost)
                elif work_order.labor_cost or work_order.parts_cost:
                    labor = float(work_order.labor_cost or 0)
                    parts = float(work_order.parts_cost or 0)
                    return labor + parts
                elif work_order.estimated_hours:
                    # تقدير بناءً على الساعات المقدرة (50 ريال/ساعة كمعدل افتراضي)
                    return float(work_order.estimated_hours) * 50
            
            # إذا لم توجد تكلفة في أمر الشغل أو طلب الخدمة، لا نحسب شيء
            return None
            
        except Exception as e:
            logger.error(f"خطأ في استخراج التكلفة الموجودة: {str(e)}")
            return None

    def _check_calibration_schedules(self):
        """فحص المعايرات المستحقة وإنشاء Work Orders و Service Requests تلقائياً"""
        start_time = timezone.now()
        print(f"\n⚖️ CALIBRATION CHECK Started at {start_time.strftime('%H:%M:%S')}")
        try:
            from .models import CalibrationRecord, ServiceRequest, WorkOrder
            from django.db import transaction
            from datetime import date
            
            today = date.today()
            print(f"   📅 Checking calibrations for {today}")
            
            # عد جميع المعايرات
            all_calibrations = CalibrationRecord.objects.all()
            print(f"   📊 Total calibration records: {all_calibrations.count()}")
            
            # المعايرات المستحقة اليوم فقط (وليس المتأخرة)
            due_calibrations = CalibrationRecord.objects.filter(
                next_calibration_date=today,
                status__in=['due', 'overdue']
            ).select_related('device', 'calibrated_by')
            print(f"   ⏰ Found {due_calibrations.count()} calibrations due or overdue")
            
            # المعايرات القادمة خلال 30 يوم
            from datetime import timedelta
            upcoming_date = today + timedelta(days=30)
            upcoming_calibrations = CalibrationRecord.objects.filter(
                next_calibration_date__gt=today,
                next_calibration_date__lte=upcoming_date
            )
            print(f"   📅 Found {upcoming_calibrations.count()} calibrations due within 30 days")
            
            created_count = 0
            skipped_count = 0
            
            if due_calibrations.exists():
                print(f"   🚀 Processing due calibrations...")
                
            for calibration in due_calibrations:
                try:
                    days_overdue = (today - calibration.next_calibration_date).days
                    status_text = f"({days_overdue} days overdue)" if days_overdue > 0 else "(due today)"
                    print(f"      📋 Processing: {calibration.device.name} {status_text}")
                    
                    with transaction.atomic():
                        # التحقق من وجود طلب معايرة للجهاز في نفس اليوم
                        today_requests = ServiceRequest.objects.filter(
                            device=calibration.device,
                            request_type='calibration',
                            created_at__date=today
                        )
                        
                        if today_requests.exists():
                            print(f"         ⚠️ Skipped: Calibration request already created today")
                            logger.info(f"تم إنشاء طلب معايرة اليوم للجهاز {calibration.device.name}")
                            skipped_count += 1
                            continue
                        
                        # التحقق من وجود طلب معايرة محلول - تحديث تاريخ المعايرة القادم فقط
                        resolved_request = ServiceRequest.objects.filter(
                            device=calibration.device,
                            request_type='calibration',
                            status__in=['resolved', 'closed', 'completed']
                        ).order_by('-resolved_at', '-closed_at', '-updated_at').first()
                        
                        if resolved_request:
                            print(f"         ✅ Found resolved calibration - updating next calibration date")
                            # تحديث تاريخ المعايرة القادم
                            from dateutil.relativedelta import relativedelta
                            calibration.next_calibration_date = today + relativedelta(months=calibration.calibration_interval_months)
                            calibration.status = 'completed'
                            calibration.save()
                            print(f"         ✅ Next calibration date updated to: {calibration.next_calibration_date}")
                            skipped_count += 1
                            continue
                        
                        # التحقق من عدم وجود طلب معايرة مفتوح للجهاز
                        existing_request = ServiceRequest.objects.filter(
                            device=calibration.device,
                            request_type='calibration',
                            status__in=['new', 'assigned', 'in_progress']
                        ).exists()
                        
                        if existing_request:
                            print(f"         ⚠️ Skipped: Open calibration request already exists")
                            logger.info(f"يوجد طلب معايرة مفتوح للجهاز {calibration.device.name}")
                            skipped_count += 1
                            continue
                        
                        # الحصول على مستخدم النظام
                        system_user = self._get_system_user()
                        
                        # إنشاء طلب خدمة جديد للمعايرة
                        service_request = ServiceRequest.objects.create(
                            title=f"معايرة - {calibration.device.name}",
                            description=f"معايرة مستحقة للجهاز {calibration.device.name} - كل {calibration.calibration_interval_months} شهر",
                            device=calibration.device,
                            request_type='calibration',
                            priority='low',  # أولوية منخفضة
                            reporter=calibration.calibrated_by or system_user,
                            assigned_to=calibration.calibrated_by
                        )
                        print(f"         ✅ Created Service Request #{service_request.id}")
                        
                        # إنشاء أمر شغل للمعايرة
                        work_order = WorkOrder.objects.create(
                            service_request=service_request,
                            assignee=calibration.calibrated_by or system_user,
                            created_by=calibration.calibrated_by or system_user,
                            description=f"تنفيذ معايرة للجهاز {calibration.device.name}",
                            priority='low',
                            wo_type='calibration'
                        )
                        print(f"         ✅ Created Work Order #{work_order.wo_number}")
                        
                        # تحديث حالة المعايرة
                        old_status = calibration.status
                        if calibration.next_calibration_date < today:
                            calibration.status = 'overdue'
                        else:
                            calibration.status = 'due'
                        calibration.save()
                        print(f"         ✅ Updated calibration status: {old_status} → {calibration.status}")
                        
                        created_count += 1
                        logger.info(f"تم إنشاء طلب معايرة للجهاز {calibration.device.name}")
                        
                except Exception as e:
                    print(f"         ❌ Error processing {calibration.device.name}: {str(e)}")
                    logger.error(f"خطأ في إنشاء طلب معايرة للجهاز {calibration.device.name}: {str(e)}")
            
            end_time = timezone.now()
            duration = (end_time - start_time).total_seconds()
            
            logger.info(f"تم إنشاء {created_count} طلب معايرة")
            print(f"   ✅ Calibration check completed in {duration:.2f}s")
            print(f"   📊 Results: {created_count} created, {skipped_count} skipped")
            
        except Exception as e:
            error_time = timezone.now()
            duration = (error_time - start_time).total_seconds()
            logger.error(f"خطأ في فحص المعايرات المستحقة: {str(e)}")
            print(f"   ❌ Calibration check failed after {duration:.2f}s: {str(e)}")
    
    def _get_system_user(self):
        """الحصول على مستخدم النظام للعمليات التلقائية"""
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            # البحث عن مستخدم النظام
            system_user = User.objects.filter(username='system').first()
            if system_user:
                return system_user
                
            # البحث عن أول مستخدم admin
            admin_user = User.objects.filter(is_superuser=True).first()
            if admin_user:
                return admin_user
                
            # البحث عن أي مستخدم
            return User.objects.first()
            
        except Exception as e:
            logger.error(f"خطأ في الحصول على مستخدم النظام: {str(e)}")
            return None


# إنشاء مثيل عام للمدير
maintenance_task_runner = MaintenanceTaskRunner()


def start_maintenance_tasks():
    """بدء تشغيل مهام الصيانة التلقائية"""
    maintenance_task_runner.start()


def stop_maintenance_tasks():
    """إيقاف مهام الصيانة التلقائية"""
    maintenance_task_runner.stop()
