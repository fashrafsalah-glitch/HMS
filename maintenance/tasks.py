"""
مهام الخلفية للصيانة - Background Tasks for Maintenance
يحتوي على المهام التي تعمل في الخلفية لإدارة الصيانة التلقائية
"""

import threading
import time
import schedule
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
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
        # جدولة المهام - للاختبار: فحص كل دقيقة
        schedule.every().minute.do(self._check_pm_schedules)
        print("DEBUG: PM schedule check scheduled every minute")
        schedule.every(5).minutes.do(self._check_sla_violations)
        schedule.every().day.at("08:00").do(self._daily_maintenance_check)
        schedule.every().day.at("18:00").do(self._send_daily_reports)
        
        logger.info("تم إعداد جدولة المهام التلقائية")
        
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(10)  # فحص كل 10 ثواني للاختبار
            except Exception as e:
                logger.error(f"خطأ في تشغيل المهام المجدولة: {str(e)}")
                time.sleep(300)  # انتظار 5 دقائق عند حدوث خطأ
    
    def _check_pm_schedules(self):
        """فحص جداول الصيانة الوقائية وإنشاء أوامر الشغل"""
        try:
            from .signals import check_and_generate_pm_work_orders
            print(f"DEBUG: Running PM check at {timezone.now()}")
            result = check_and_generate_pm_work_orders()
            print(f"DEBUG: PM check completed, result: {result}")
        except Exception as e:
            logger.error(f"خطأ في فحص الصيانة الوقائية: {str(e)}")
            print(f"DEBUG: PM check error: {str(e)}")
    
    def _check_sla_violations(self):
        """فحص انتهاكات SLA وإرسال تنبيهات"""
        try:
            from .models import ServiceRequest, WorkOrder
            from django.utils import timezone
            
            now = timezone.now()
            
            # فحص البلاغات المتأخرة
            overdue_requests = ServiceRequest.objects.filter(
                status__in=['new', 'assigned', 'in_progress'],
                created_at__lt=now - timezone.timedelta(days=7)  # استخدام created_at بدلاً من resolution_due
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
                status__in=['needs_maintenance', 'needs_check'],
                is_active=True
            )
            
            if devices_need_maintenance.exists():
                logger.info(f"يوجد {devices_need_maintenance.count()} جهاز يحتاج صيانة")
            
            # فحص قطع الغيار المنخفضة
            from .models import SparePart
            from django.db import models
            low_stock_parts = SparePart.objects.filter(
                current_stock__lte=models.F('minimum_stock'),
                is_active=True
            )
            
            if low_stock_parts.exists():
                logger.warning(f"يوجد {low_stock_parts.count()} قطعة غيار منخفضة المخزون")
                
        except Exception as e:
            logger.error(f"خطأ في الفحص اليومي: {str(e)}")
    
    def _send_daily_reports(self):
        """إرسال التقارير اليومية"""
        try:
            from .models import WorkOrder, ServiceRequest
            from datetime import date
            
            today = date.today()
            
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


# إنشاء مثيل عام للمدير
maintenance_task_runner = MaintenanceTaskRunner()


def start_maintenance_tasks():
    """بدء تشغيل مهام الصيانة التلقائية"""
    maintenance_task_runner.start()


def stop_maintenance_tasks():
    """إيقاف مهام الصيانة التلقائية"""
    maintenance_task_runner.stop()
