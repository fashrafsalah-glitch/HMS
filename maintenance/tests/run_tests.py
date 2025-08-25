# سكريبت لتشغيل جميع اختبارات CMMS
# يمكن استخدامه لتشغيل الاختبارات بطريقة منظمة

import os
import sys
import django
from django.conf import settings
from django.test.utils import get_runner
from django.core.management import execute_from_command_line

def run_cmms_tests():
    """تشغيل جميع اختبارات CMMS"""
    
    print("🧪 بدء تشغيل اختبارات CMMS...")
    print("=" * 50)
    
    # إعداد Django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
    django.setup()
    
    # قائمة ملفات الاختبار
    test_modules = [
        'maintenance.tests.test_models',
        'maintenance.tests.test_views', 
        'maintenance.tests.test_api',
        'maintenance.tests.test_notifications',
        'maintenance.tests.test_scheduler',
        'maintenance.tests.test_permissions'
    ]
    
    # تشغيل كل مجموعة اختبارات
    for module in test_modules:
        print(f"\n📋 تشغيل اختبارات: {module}")
        print("-" * 30)
        
        try:
            execute_from_command_line([
                'manage.py', 'test', module, '--verbosity=2'
            ])
            print(f"✅ نجح: {module}")
            
        except Exception as e:
            print(f"❌ فشل: {module}")
            print(f"الخطأ: {str(e)}")
            
    print("\n" + "=" * 50)
    print("🏁 انتهاء تشغيل الاختبارات")

def run_specific_test(test_name):
    """تشغيل اختبار محدد"""
    
    print(f"🧪 تشغيل اختبار محدد: {test_name}")
    
    try:
        execute_from_command_line([
            'manage.py', 'test', test_name, '--verbosity=2'
        ])
        print(f"✅ نجح الاختبار: {test_name}")
        
    except Exception as e:
        print(f"❌ فشل الاختبار: {test_name}")
        print(f"الخطأ: {str(e)}")

def run_coverage_report():
    """تشغيل تقرير التغطية"""
    
    print("📊 إنشاء تقرير تغطية الاختبارات...")
    
    try:
        # تشغيل الاختبارات مع تغطية
        os.system('coverage run --source=maintenance manage.py test maintenance.tests')
        
        # إنشاء التقرير
        os.system('coverage report -m')
        
        # إنشاء تقرير HTML
        os.system('coverage html')
        
        print("✅ تم إنشاء تقرير التغطية في مجلد htmlcov/")
        
    except Exception as e:
        print(f"❌ فشل في إنشاء تقرير التغطية: {str(e)}")

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='تشغيل اختبارات CMMS')
    parser.add_argument(
        '--test', 
        help='تشغيل اختبار محدد'
    )
    parser.add_argument(
        '--coverage', 
        action='store_true',
        help='إنشاء تقرير تغطية الاختبارات'
    )
    
    args = parser.parse_args()
    
    if args.coverage:
        run_coverage_report()
    elif args.test:
        run_specific_test(args.test)
    else:
        run_cmms_tests()
