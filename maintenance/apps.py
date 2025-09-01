from django.apps import AppConfig


class MaintenanceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'maintenance'
    
    def ready(self):
        """تشغيل المهام التلقائية عند بدء التطبيق"""
        import maintenance.signals
        try:
            from .tasks import start_maintenance_tasks
            start_maintenance_tasks()
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"خطأ في بدء مهام الصيانة التلقائية: {str(e)}")
