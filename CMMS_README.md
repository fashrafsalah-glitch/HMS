# نظام إدارة الصيانة المحوسب (CMMS) - نظام إدارة المستشفيات

## 📋 نظرة عامة

نظام إدارة الصيانة المحوسب (CMMS) هو إضافة شاملة لنظام إدارة المستشفيات (HMS) مبني بـ Django 5.2.5. يوفر النظام إدارة كاملة لصيانة الأجهزة الطبية، قطع الغيار، الجدولة، والتقارير مع واجهة مستخدم حديثة ونظام صلاحيات متقدم.

## ✨ المميزات الرئيسية

### 🔧 إدارة طلبات الخدمة وأوامر الشغل
- إنشاء وتتبع طلبات الصيانة
- تعيين أوامر الشغل للفنيين
- تتبع حالة العمل والتقدم
- حساب تكاليف العمالة والمواد

### 📅 الصيانة الوقائية
- جدولة الصيانة الدورية
- إنشاء تلقائي لطلبات الصيانة الوقائية
- خطط عمل مفصلة مع التعليمات
- تتبع الامتثال للجداول المحددة

### 📦 إدارة قطع الغيار
- تتبع المخزون والكميات
- تنبيهات المخزون المنخفض
- إدارة الموردين وأوامر الشراء
- تتبع استخدام قطع الغيار في أوامر الشغل

### 📊 لوحة التحكم والتقارير
- مؤشرات الأداء الرئيسية (KPIs)
- تقارير MTBF و MTTR
- إحصائيات الصيانة والتكاليف
- رسوم بيانية تفاعلية

### 🔔 نظام الإشعارات
- إشعارات انتهاك SLA
- تنبيهات الصيانة الوقائية المستحقة
- إشعارات المعايرة المطلوبة
- تنبيهات نفاد قطع الغيار

### 👥 نظام الصلاحيات (RBAC)
- أدوار محددة مسبقاً (مدير، مشرف، فني، طبيب)
- صلاحيات مفصلة لكل دور
- حماية البيانات والعمليات الحساسة

### 🤖 المهام المجدولة
- تشغيل تلقائي للمهام الدورية
- إنشاء طلبات الصيانة الوقائية
- فحص انتهاكات SLA
- تنظيف البيانات القديمة

## 🛠️ التثبيت والإعداد

### المتطلبات الأساسية

```
Python 3.8+
Django 5.2.5
PostgreSQL أو SQLite
Redis (اختياري للـ caching)
```

### خطوات التثبيت

1. **تفعيل البيئة الافتراضية**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# أو
venv\Scripts\activate  # Windows
```

2. **تثبيت المتطلبات**
```bash
pip install -r requirements.txt
```

3. **تشغيل المايجريشنز**
```bash
python manage.py migrate
```

4. **إعداد صلاحيات CMMS**
```bash
python manage.py setup_cmms_permissions
```

5. **إنشاء مستخدم مدير**
```bash
python manage.py createsuperuser
```

6. **تعيين دور المدير للمستخدم**
```bash
python manage.py assign_user_role admin CMMS_Admin
```

7. **تشغيل الخادم**
```bash
python manage.py runserver
```

## 📁 هيكل المشروع

```
maintenance/
├── models.py                    # موديلات الأجهزة الأساسية
├── models_cmms.py              # موديلات CMMS (طلبات الخدمة، أوامر الشغل)
├── models_spare_parts.py       # موديلات قطع الغيار والشراء
├── models_notifications.py     # موديلات الإشعارات
├── views_cmms.py               # صفحات CMMS
├── views_dashboard.py          # لوحة التحكم
├── api_views.py                # API endpoints
├── serializers.py              # DRF serializers
├── permissions.py              # نظام الصلاحيات
├── notifications.py            # نظام الإشعارات
├── scheduler.py                # المهام المجدولة
├── kpi_utils.py               # حساب مؤشرات الأداء
├── templates/maintenance/      # قوالب HTML
├── tests/                     # الاختبارات
└── management/commands/       # أوامر Django المخصصة
```

## 🚀 الاستخدام

### الوصول للنظام

1. **تسجيل الدخول**: `/accounts/login/`
2. **لوحة تحكم CMMS**: `/maintenance/cmms/dashboard/`
3. **طلبات الخدمة**: `/maintenance/cmms/service-requests/`
4. **أوامر الشغل**: `/maintenance/cmms/work-orders/`
5. **قطع الغيار**: `/maintenance/spare-parts/`

### الأدوار والصلاحيات

#### 🔑 مدير CMMS
- إدارة كاملة للنظام
- إنشاء وتعديل جميع البيانات
- عرض جميع التقارير
- إدارة المستخدمين والصلاحيات

#### 👨‍💼 مشرف CMMS
- إدارة طلبات الخدمة وأوامر الشغل
- تعيين المهام للفنيين
- عرض التقارير والإحصائيات
- إدارة قطع الغيار

#### 🔧 فني CMMS
- عرض أوامر الشغل المعينة له
- تحديث حالة العمل والتقدم
- تسجيل استخدام قطع الغيار
- عرض تعليمات العمل

#### 👨‍⚕️ طبيب/ممرض
- إنشاء طلبات صيانة للأجهزة
- عرض حالة الأجهزة
- تلقي إشعارات حالة الصيانة

## 📊 مؤشرات الأداء (KPIs)

### MTBF (Mean Time Between Failures)
متوسط الوقت بين الأعطال - يقيس موثوقية الجهاز

### MTTR (Mean Time To Repair)
متوسط وقت الإصلاح - يقيس كفاءة الصيانة

### نسبة التوفر (Availability)
النسبة المئوية لوقت تشغيل الجهاز

### امتثال الصيانة الوقائية
نسبة إكمال الصيانة الوقائية في الوقت المحدد

## 🔔 نظام الإشعارات

### أنواع الإشعارات

1. **انتهاك SLA**: عند تجاوز أوقات الاستجابة أو الحل
2. **صيانة وقائية مستحقة**: تذكير بالصيانة المجدولة
3. **معايرة مطلوبة**: تنبيه لمعايرة الأجهزة
4. **مخزون منخفض**: تحذير من نقص قطع الغيار
5. **تعيين أمر شغل**: إشعار الفني بمهمة جديدة

### قنوات الإشعار

- **إشعارات النظام**: داخل التطبيق
- **البريد الإلكتروني**: للإشعارات المهمة
- **قابل للتوسع**: SMS، تطبيقات الجوال

## 🤖 المهام المجدولة

### تشغيل المهام يدوياً

```bash
# تشغيل جميع المهام
python manage.py run_cmms_scheduler

# تشغيل مهمة محددة
python manage.py run_cmms_scheduler --task pm
python manage.py run_cmms_scheduler --task sla
python manage.py run_cmms_scheduler --task calibration
```

### تشغيل تلقائي (Windows Task Scheduler)

```batch
# استخدام الملف المرفق
run_cmms_scheduler.bat
```

### تشغيل تلقائي (Linux Cron)

```bash
# إضافة للـ crontab
0 */1 * * * /path/to/venv/bin/python /path/to/manage.py run_cmms_scheduler
```

## 🔧 API Documentation

### Authentication
جميع API endpoints تتطلب مصادقة. استخدم Django REST Framework authentication.

### الأجهزة
```
GET    /api/maintenance/devices/           # قائمة الأجهزة
POST   /api/maintenance/devices/           # إنشاء جهاز جديد
GET    /api/maintenance/devices/{id}/      # تفاصيل الجهاز
PUT    /api/maintenance/devices/{id}/      # تحديث الجهاز
DELETE /api/maintenance/devices/{id}/      # حذف الجهاز
```

### طلبات الخدمة
```
GET    /api/maintenance/service-requests/  # قائمة طلبات الخدمة
POST   /api/maintenance/service-requests/  # إنشاء طلب جديد
GET    /api/maintenance/service-requests/{id}/ # تفاصيل الطلب
```

### أوامر الشغل
```
GET    /api/maintenance/work-orders/       # قائمة أوامر الشغل
POST   /api/maintenance/work-orders/       # إنشاء أمر شغل
PATCH  /api/maintenance/work-orders/{id}/  # تحديث حالة أمر الشغل
```

### لوحة التحكم
```
GET    /api/maintenance/dashboard/data/    # بيانات لوحة التحكم
GET    /api/maintenance/devices/{id}/kpis/ # مؤشرات أداء الجهاز
```

## 🧪 الاختبارات

### تشغيل جميع الاختبارات
```bash
python manage.py test maintenance.tests
```

### تشغيل اختبارات محددة
```bash
python manage.py test maintenance.tests.test_models
python manage.py test maintenance.tests.test_api
python manage.py test maintenance.tests.test_permissions
```

### تشغيل مع تقرير التغطية
```bash
coverage run --source=maintenance manage.py test maintenance.tests
coverage report -m
coverage html
```

### استخدام سكريبت الاختبار المخصص
```bash
python maintenance/tests/run_tests.py
python maintenance/tests/run_tests.py --coverage
```

## ⚙️ الإعدادات

### إعدادات Django (settings.py)

```python
# إضافة للـ INSTALLED_APPS
INSTALLED_APPS = [
    # ... التطبيقات الأخرى
    'maintenance',
    'rest_framework',
    'crispy_forms',
    'crispy_bootstrap4',
]

# إعدادات REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20
}

# إعدادات البريد الإلكتروني
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'your-smtp-server.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@example.com'
EMAIL_HOST_PASSWORD = 'your-password'

# إعدادات الإشعارات
CMMS_NOTIFICATIONS = {
    'EMAIL_ENABLED': True,
    'SYSTEM_ENABLED': True,
    'DEFAULT_FROM_EMAIL': 'noreply@hospital.com',
}
```

### إعدادات URLs

```python
# في urls.py الرئيسي
urlpatterns = [
    # ... URLs الأخرى
    path('maintenance/', include('maintenance.urls')),
    path('api/maintenance/', include('maintenance.api_urls')),
]
```

## 🔒 الأمان

### حماية البيانات
- تشفير كلمات المرور
- حماية من CSRF
- تحقق من الصلاحيات في كل عملية
- تسجيل العمليات الحساسة

### النسخ الاحتياطية
```bash
# نسخ احتياطي لقاعدة البيانات
python manage.py dumpdata maintenance > backup.json

# استعادة النسخة الاحتياطية
python manage.py loaddata backup.json
```

## 📈 الأداء والتحسين

### فهرسة قاعدة البيانات
- فهارس على الحقول المستخدمة في البحث
- فهارس مركبة للاستعلامات المعقدة
- تحسين استعلامات ORM

### التخزين المؤقت
```python
# إعدادات Redis للـ caching
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}
```

## 🐛 استكشاف الأخطاء

### مشاكل شائعة

#### خطأ في المايجريشنز
```bash
# إعادة تعيين المايجريشنز
python manage.py migrate maintenance zero
python manage.py migrate maintenance
```

#### مشاكل الصلاحيات
```bash
# إعادة إعداد الصلاحيات
python manage.py setup_cmms_permissions --reset
```

#### مشاكل المهام المجدولة
```bash
# تشغيل تجريبي للمهام
python manage.py run_cmms_scheduler --dry-run --verbose
```

### السجلات (Logging)

```python
# إعدادات السجلات في settings.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'logs/cmms.log',
        },
    },
    'loggers': {
        'maintenance': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
```

## 🔄 التحديثات والصيانة

### تحديث النظام
1. نسخ احتياطي للبيانات
2. تحديث الكود
3. تشغيل المايجريشنز الجديدة
4. اختبار الوظائف الأساسية

### صيانة دورية
- تنظيف السجلات القديمة
- تحسين قاعدة البيانات
- مراجعة الأداء
- تحديث التوثيق

## 📞 الدعم والمساعدة

### الحصول على المساعدة
- مراجعة هذا التوثيق
- فحص ملفات الاختبار للأمثلة
- مراجعة السجلات للأخطاء

### المساهمة في التطوير
1. Fork المشروع
2. إنشاء branch للميزة الجديدة
3. كتابة الاختبارات
4. إرسال Pull Request

## 📝 الترخيص

هذا المشروع مرخص تحت رخصة MIT. راجع ملف LICENSE للتفاصيل.

## 🙏 شكر وتقدير

- فريق Django لإطار العمل الرائع
- مجتمع Django REST Framework
- جميع المساهمين في المكتبات المستخدمة

---

**تم تطوير هذا النظام بعناية لتلبية احتياجات إدارة الصيانة في المستشفيات. نأمل أن يساعد في تحسين كفاءة الصيانة وجودة الرعاية الصحية.**

**للاستفسارات التقنية أو طلب المساعدة، يرجى مراجعة التوثيق أو الاتصال بفريق التطوير.**
