# أمر Django لإنشاء مصفوفة SLA للفئات الموجودة
# ينشئ مصفوفة SLA للفئات التي لا تحتوي على مصفوفة

from django.core.management.base import BaseCommand
from maintenance.signals import generate_sla_matrix_for_existing_categories

class Command(BaseCommand):
    """
    أمر لإنشاء مصفوفة SLA للفئات الموجودة التي لا تحتوي على مصفوفة
    
    الاستخدام:
    python manage.py generate_existing_sla
    """
    
    help = 'إنشاء مصفوفة SLA للفئات الموجودة التي لا تحتوي على مصفوفة'
    
    def handle(self, *args, **options):
        self.stdout.write('بدء إنشاء مصفوفة SLA للفئات الموجودة...')
        
        try:
            created_count = generate_sla_matrix_for_existing_categories()
            
            if created_count > 0:
                self.stdout.write(
                    self.style.SUCCESS(f'تم إنشاء {created_count} مدخل في مصفوفة SLA للفئات الموجودة')
                )
            else:
                self.stdout.write(
                    self.style.WARNING('لا توجد فئات تحتاج إلى إنشاء مصفوفة SLA')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'خطأ في إنشاء مصفوفة SLA: {str(e)}')
            )
            raise
