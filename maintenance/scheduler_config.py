# إعدادات الجدولة للـ CMMS
# هنا بنحدد أوقات تشغيل المهام المختلفة والإعدادات الخاصة بكل مهمة

from datetime import time, timedelta

# إعدادات عامة للجدولة
SCHEDULER_CONFIG = {
    # تشغيل المهام الأساسية كل ساعة
    'main_tasks_interval': timedelta(hours=1),
    
    # تشغيل الصيانة الوقائية يومياً في الساعة 6 صباحاً
    'preventive_maintenance': {
        'enabled': True,
        'run_time': time(6, 0),  # 6:00 AM
        'interval': timedelta(days=1),
        'advance_notice_days': 7,  # إشعار مسبق 7 أيام
    },
    
    # فحص انتهاكات SLA كل 30 دقيقة
    'sla_violations': {
        'enabled': True,
        'interval': timedelta(minutes=30),
        'warning_threshold_hours': 2,  # تحذير قبل ساعتين من الانتهاك
    },
    
    # فحص المعايرات المستحقة يومياً في الساعة 8 صباحاً
    'calibration_check': {
        'enabled': True,
        'run_time': time(8, 0),  # 8:00 AM
        'interval': timedelta(days=1),
        'advance_notice_days': 30,  # إشعار مسبق 30 يوم
        'critical_notice_days': 7,  # إشعار حرج 7 أيام
    },
    
    # فحص قطع الغيار يومياً في الساعة 9 صباحاً
    'spare_parts_check': {
        'enabled': True,
        'run_time': time(9, 0),  # 9:00 AM
        'interval': timedelta(days=1),
        'low_stock_multiplier': 1.5,  # تحذير عند 1.5 ضعف الحد الأدنى
    },
    
    # معالجة طابور الإشعارات كل 15 دقيقة
    'notification_queue': {
        'enabled': True,
        'interval': timedelta(minutes=15),
        'batch_size': 50,  # معالجة 50 إشعار في المرة
        'retry_delay_minutes': 30,  # إعادة المحاولة بعد 30 دقيقة
        'max_attempts': 3,  # الحد الأقصى للمحاولات
    },
    
    # تنظيف البيانات القديمة أسبوعياً يوم الأحد في الساعة 2 صباحاً
    'data_cleanup': {
        'enabled': True,
        'run_time': time(2, 0),  # 2:00 AM
        'interval': timedelta(days=7),
        'retention_days': {
            'read_notifications': 30,  # الإشعارات المقروءة
            'email_logs': 90,  # سجلات الإيميل
            'sent_queue_items': 7,  # عناصر الطابور المرسلة
            'completed_work_orders': 365,  # أوامر الشغل المكتملة
        }
    },
    
    # إعدادات الإشعارات
    'notifications': {
        'email_enabled': True,
        'system_enabled': True,
        'batch_email_size': 10,  # إرسال 10 إيميل في المرة
        'email_delay_seconds': 2,  # تأخير ثانيتين بين الإيميلات
    },
    
    # إعدادات الأداء
    'performance': {
        'max_execution_time_minutes': 30,  # الحد الأقصى لوقت التنفيذ
        'database_timeout_seconds': 300,  # مهلة قاعدة البيانات
        'log_slow_queries': True,  # تسجيل الاستعلامات البطيئة
        'slow_query_threshold_seconds': 5,  # عتبة الاستعلام البطيء
    },
    
    # إعدادات التسجيل
    'logging': {
        'level': 'INFO',
        'file_path': 'logs/cmms_scheduler.log',
        'max_file_size_mb': 10,  # الحد الأقصى لحجم ملف السجل
        'backup_count': 5,  # عدد ملفات النسخ الاحتياطية
        'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    }
}

# إعدادات أولويات المهام
TASK_PRIORITIES = {
    'sla_violations': 1,  # أعلى أولوية
    'notification_queue': 2,
    'preventive_maintenance': 3,
    'calibration_check': 4,
    'spare_parts_check': 5,
    'data_cleanup': 6,  # أقل أولوية
}

# إعدادات قوالب الإشعارات الافتراضية
DEFAULT_NOTIFICATION_TEMPLATES = {
    'sla_violation': {
        'subject': 'تحذير: انتهاك SLA - {device_name}',
        'email_template': '''
        تحذير: انتهاك اتفاقية مستوى الخدمة
        
        الجهاز: {device_name}
        نوع الانتهاك: {violation_type}
        طلب الخدمة: {service_request_id}
        الوقت المستحق: {due_time}
        الوقت الحالي: {current_time}
        
        يرجى اتخاذ الإجراء المناسب فوراً.
        ''',
        'system_template': 'انتهاك SLA للجهاز {device_name} - {violation_type}'
    },
    
    'pm_due': {
        'subject': 'صيانة وقائية مستحقة - {device_name}',
        'email_template': '''
        تذكير: صيانة وقائية مستحقة
        
        الجهاز: {device_name}
        تاريخ الاستحقاق: {due_date}
        نوع الصيانة: {maintenance_type}
        
        يرجى جدولة الصيانة في أقرب وقت ممكن.
        ''',
        'system_template': 'صيانة وقائية مستحقة للجهاز {device_name}'
    },
    
    'calibration_due': {
        'subject': 'معايرة مستحقة - {device_name}',
        'email_template': '''
        تذكير: معايرة مستحقة
        
        الجهاز: {device_name}
        تاريخ المعايرة المستحقة: {due_date}
        آخر معايرة: {last_calibration_date}
        
        يرجى جدولة المعايرة قبل التاريخ المستحق.
        ''',
        'system_template': 'معايرة مستحقة للجهاز {device_name}'
    },
    
    'spare_parts_low': {
        'subject': 'تحذير: مخزون منخفض - {part_name}',
        'email_template': '''
        تحذير: مخزون قطعة غيار منخفض
        
        قطعة الغيار: {part_name}
        رقم القطعة: {part_number}
        الكمية الحالية: {current_quantity}
        الحد الأدنى: {minimum_stock}
        
        يرجى طلب المزيد من هذه القطعة.
        ''',
        'system_template': 'مخزون منخفض لقطعة الغيار {part_name}'
    },
    
    'spare_parts_out': {
        'subject': 'تحذير عاجل: نفاد المخزون - {part_name}',
        'email_template': '''
        تحذير عاجل: نفاد مخزون قطعة غيار
        
        قطعة الغيار: {part_name}
        رقم القطعة: {part_number}
        الكمية الحالية: 0
        
        يرجى طلب هذه القطعة فوراً لتجنب تأخير الصيانة.
        ''',
        'system_template': 'نفاد مخزون قطعة الغيار {part_name}'
    }
}

# إعدادات أوقات العمل
WORKING_HOURS = {
    'start_time': time(8, 0),  # 8:00 AM
    'end_time': time(17, 0),   # 5:00 PM
    'working_days': [0, 1, 2, 3, 4],  # الاثنين إلى الجمعة (0=الاثنين)
    'emergency_hours': True,  # السماح بالمهام الطارئة خارج أوقات العمل
}

# إعدادات قاعدة البيانات
DATABASE_CONFIG = {
    'connection_pool_size': 5,
    'max_overflow': 10,
    'pool_timeout': 30,
    'pool_recycle': 3600,  # إعادة تدوير الاتصالات كل ساعة
}

def get_config(key, default=None):
    """
    الحصول على قيمة إعداد معين
    """
    keys = key.split('.')
    config = SCHEDULER_CONFIG
    
    for k in keys:
        if isinstance(config, dict) and k in config:
            config = config[k]
        else:
            return default
            
    return config

def is_working_hours(current_time=None):
    """
    التحقق من كون الوقت الحالي ضمن أوقات العمل
    """
    if current_time is None:
        from django.utils import timezone
        current_time = timezone.now().time()
        
    current_day = timezone.now().weekday()
    
    return (
        current_day in WORKING_HOURS['working_days'] and
        WORKING_HOURS['start_time'] <= current_time <= WORKING_HOURS['end_time']
    )

def should_run_task(task_name, last_run=None):
    """
    التحقق من ضرورة تشغيل مهمة معينة
    """
    if task_name not in SCHEDULER_CONFIG:
        return False
        
    task_config = SCHEDULER_CONFIG[task_name]
    
    if not task_config.get('enabled', True):
        return False
        
    if last_run is None:
        return True
        
    from django.utils import timezone
    now = timezone.now()
    interval = task_config.get('interval', timedelta(hours=1))
    
    return now - last_run >= interval
