# 📚 نظام QR Code/Barcode - HMS
## Hospital Management System - QR Code Integration

<div align="center">

![Version](https://img.shields.io/badge/version-2.0.0-blue.svg)
![Status](https://img.shields.io/badge/status-active-success.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

</div>

---

## 📋 جدول المحتويات

- [نظرة عامة](#-نظرة-عامة)
- [الميزات الرئيسية](#-الميزات-الرئيسية)
- [البنية التقنية](#️-البنية-التقنية)
- [التثبيت والإعداد](#-التثبيت-والإعداد)
- [دورة حياة QR Code](#-دورة-حياة-qr-code)
- [الكيانات المدعومة](#-الكيانات-المدعومة)
- [العمليات الديناميكية](#-العمليات-الديناميكية)
- [API Documentation](#-api-documentation)
- [واجهات المستخدم](#-واجهات-المستخدم)
- [الأمان والحماية](#-الأمان-والحماية)
- [أوامر الإدارة](#️-أوامر-الإدارة)
- [استكشاف الأخطاء](#-استكشاف-الأخطاء)
- [أمثلة عملية](#-أمثلة-عملية)

---

## 🎯 نظرة عامة

نظام QR Code/Barcode في HMS هو نظام متكامل لإدارة وتتبع جميع الكيانات في المستشفى باستخدام تقنية الباركود. النظام يوفر:

- **توليد تلقائي** لأكواد QR عند إنشاء أي كيان جديد
- **مسح ذكي** مع تنفيذ عمليات ديناميكية
- **تتبع كامل** لجميع عمليات المسح والاستخدام
- **أمان متقدم** باستخدام التوقيع الرقمي HMAC-SHA256

---

## ✨ الميزات الرئيسية

### 🔄 التوليد التلقائي
- توليد QR تلقائي عند إنشاء أي كيان جديد
- دعم التوليد اليدوي للكيانات الموجودة
- توكنات مؤقتة للعمليات الحساسة

### 📱 المسح الذكي
- دعم المسح عبر الموبايل والماسحات المخصصة
- تعرف تلقائي على نوع الكيان
- تنفيذ عمليات ديناميكية حسب تسلسل المسح

### 📊 التتبع والتحليل
- تسجيل كامل لجميع عمليات المسح
- إحصائيات مفصلة عن الاستخدام
- تقارير الأداء والكفاءة

### 🔐 الأمان المتقدم
- توقيع رقمي HMAC-SHA256
- توكنات مؤقتة (60 ثانية) للعمليات الحساسة
- التحقق من صحة التوقيع قبل كل عملية

---

## 🏗️ البنية التقنية

```
HMS/
├── core/
│   ├── qr_utils.py              # المكتبة الأساسية لتوليد QR
│   └── secure_qr.py             # نظام الأمان والتوقيع الرقمي
│
├── maintenance/
│   ├── qr_operations.py         # مدير العمليات الديناميكية
│   ├── signals.py               # التوليد التلقائي عند الإنشاء
│   ├── models.py                # نماذج البيانات
│   ├── views.py                 # معالجات الطلبات
│   ├── api_views.py             # API endpoints
│   └── templates/
│       ├── qr_test.html         # صفحة الاختبار
│       ├── mobile_qr_scan.html  # واجهة الموبايل
│       └── scan_session.html    # إدارة الجلسات
│
├── manager/
│   └── models.py                # نماذج المرضى والأسرّة
│
├── hr/
│   └── models.py                # نماذج المستخدمين
│
└── media/
    ├── qr_codes/                # تخزين صور QR العامة
    ├── lab_qrcodes/             # QR المختبر
    └── lab_samples_qr/          # QR العينات
```

---

## 🚀 التثبيت والإعداد

### 1. تثبيت المتطلبات

```bash
pip install qrcode[pil]
pip install django-rest-framework
```

### 2. إعدادات Django

```python
# settings.py

# QR Code Settings
QR_DOMAIN = 'https://your-domain.com'
QR_SECRET_KEY = 'your-secret-key-here'

# Media Files
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
```

### 3. تشغيل Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 4. توليد QR للكيانات الموجودة

```bash
# توليد لجميع الكيانات
python manage.py populate_qr_codes --entity=all

# معاينة بدون تنفيذ
python manage.py populate_qr_codes --dry-run
```

---

## 🔄 دورة حياة QR Code

### 1️⃣ **مرحلة التوليد (Generation)**

#### التوليد التلقائي
```python
# signals.py - يعمل تلقائياً عند حفظ كيان جديد
@receiver(post_save)
def generate_qr_code_on_save(sender, instance, created, **kwargs):
    if isinstance(instance, QRCodeMixin):
        if created or not instance.qr_token:
            instance.qr_token = instance.generate_qr_token()
            instance.generate_qr_code()
            instance.save()
```

#### صيغة التوكن
```
Format: <entity_type>:<uuid>|sig=<signature>
مثال: device:a5b3c8d9-1234-5678-90ab|sig=f4a2b7c9d8e1
```

### 2️⃣ **مرحلة التخزين (Storage)**

- **قاعدة البيانات**: حفظ التوكن في حقل `qr_token`
- **الملفات**: حفظ صورة QR في `media/qr_codes/`
- **الكاش**: حفظ معلومات التوكن للوصول السريع

### 3️⃣ **مرحلة المسح (Scanning)**

```python
# معالجة المسح
def scan_qr_code(request):
    qr_code = request.POST.get('qr_code')
    parsed = SecureQRToken.parse_token(qr_code)
    
    if parsed['valid']:
        entity_type = parsed['entity_type']
        entity_id = parsed['entity_id']
        # تنفيذ العملية المناسبة
```

### 4️⃣ **مرحلة التنفيذ (Execution)**

- مطابقة تسلسل المسح مع العمليات المحددة
- تنفيذ العملية المناسبة
- تسجيل النتيجة في قاعدة البيانات

---

## 📦 الكيانات المدعومة

| الكيان | النموذج | الوصف | مثال QR Token |
|--------|----------|--------|---------------|
| **Device** | `maintenance.models.Device` | الأجهزة الطبية | `device:uuid\|sig=xxx` |
| **Patient** | `manager.models.Patient` | المرضى | `patient:uuid\|sig=xxx` |
| **Bed** | `manager.models.Bed` | الأسرّة | `bed:uuid\|sig=xxx` |
| **User** | `hr.models.CustomUser` | المستخدمين | `user:uuid\|sig=xxx` |
| **Accessory** | `maintenance.models.DeviceAccessory` | ملحقات الأجهزة | `accessory:uuid\|sig=xxx` |
| **Room** | `manager.models.Room` | الغرف | `room:uuid\|sig=xxx` |

---

## 🎮 العمليات الديناميكية

### جدول العمليات المتاحة

| رمز العملية | الوصف | التسلسل المطلوب | التنفيذ |
|------------|-------|-----------------|---------|
| `DEVICE_USAGE` | استخدام جهاز على مريض | Patient → Device | تلقائي |
| `DEVICE_TRANSFER` | نقل جهاز بين الأقسام | Device → Department | يدوي |
| `PATIENT_TRANSFER` | نقل مريض لسرير جديد | Patient → Bed | تلقائي |
| `DEVICE_HANDOVER` | تسليم جهاز بين المستخدمين | User → Device → User | يدوي |
| `ACCESSORY_USAGE` | استخدام ملحق | Accessory → Patient | تلقائي |
| `DEVICE_CLEANING` | تنظيف جهاز | Device | تلقائي |
| `DEVICE_STERILIZATION` | تعقيم جهاز | Device | تلقائي |
| `DEVICE_MAINTENANCE` | صيانة جهاز | Device | يدوي |
| `INVENTORY_CHECK` | جرد | Device | تلقائي |
| `QUALITY_CONTROL` | مراقبة الجودة | Device | تلقائي |
| `CALIBRATION` | معايرة | Device | تلقائي |
| `INSPECTION` | فحص | Device | تلقائي |

### تعريف عملية جديدة

```python
# في maintenance/models.py
OperationDefinition.objects.create(
    name="عملية جديدة",
    code="NEW_OPERATION",
    description="وصف العملية",
    requires_confirmation=True,
    auto_execute=False,
    session_timeout_minutes=10
)
```

---

## 🔌 API Documentation

### نقاط النهاية الرئيسية

#### 1. مسح QR Code
```http
POST /api/scan-qr/
Content-Type: application/json

{
    "qr_code": "device:a5b3c8d9-1234|sig=f4a2b7c9",
    "device_type": "mobile",
    "scanner_id": "scanner-001"
}

Response:
{
    "success": true,
    "entity_type": "device",
    "entity_id": "123",
    "entity_data": {...},
    "operation_matched": "DEVICE_USAGE",
    "message": "Device scan successful"
}
```

#### 2. توليد QR Code
```http
POST /maintenance/generate-qr/
Content-Type: application/json

{
    "entity_type": "device",
    "entity_id": "123",
    "ephemeral": false
}

Response:
{
    "success": true,
    "qr_token": "device:uuid|sig=xxx",
    "qr_image_url": "/media/qr_codes/device_123_qr.png"
}
```

#### 3. جلسة مسح جديدة
```http
POST /api/scan-session/start/
Content-Type: application/json

{
    "device_type": "mobile"
}

Response:
{
    "success": true,
    "session_id": "550e8400-e29b-41d4-a716",
    "expires_in": 300
}
```

#### 4. إضافة مسح لجلسة
```http
POST /api/scan-session/add/
Content-Type: application/json

{
    "session_id": "550e8400-e29b-41d4-a716",
    "qr_code": "patient:uuid|sig=xxx"
}

Response:
{
    "matched": true,
    "flow": {
        "name": "PATIENT_TRANSFER",
        "auto_execute": true
    }
}
```

---

## 🖥️ واجهات المستخدم

### 1. صفحة الروابط الرئيسية
**URL**: `/maintenance/qr-links/`

- عرض جميع روابط النظام
- معلومات API endpoints
- إحصائيات الاستخدام
- روابط سريعة للوظائف

### 2. صفحة المسح للموبايل
**URL**: `/maintenance/mobile-qr-scan/`

**الميزات**:
- واجهة محسنة للأجهزة المحمولة
- دعم الكاميرا المباشرة
- عرض النتائج الفورية
- تنفيذ العمليات مباشرة

### 3. صفحة الاختبار
**URL**: `/maintenance/qr-test/`

**الاستخدامات**:
- اختبار المسح اليدوي
- عرض تفاصيل الكيان
- التوجيه التلقائي للصفحات
- تشخيص المشاكل

### 4. إدارة الجلسات
**URL**: `/maintenance/sessions/`

- عرض الجلسات النشطة
- تاريخ المسحات
- العمليات المنفذة
- الأخطاء والتحذيرات

---

## 🔐 الأمان والحماية

### 1. التوقيع الرقمي HMAC-SHA256

```python
# core/secure_qr.py
def generate_signature(data: str) -> str:
    signature = hmac.new(
        SECRET_KEY.encode('utf-8'),
        data.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return signature[:16]  # أول 16 حرف
```

### 2. التوكنات المؤقتة (Ephemeral Tokens)

```python
# للعمليات الحساسة
token = SecureQRToken.generate_token(
    entity_type='device',
    entity_id='123',
    ephemeral=True  # صلاحية 60 ثانية
)
```

### 3. التحقق من الصلاحية

```python
def verify_signature(data: str, signature: str) -> bool:
    expected = generate_signature(data)
    return hmac.compare_digest(expected, signature)
```

### 4. حماية من الهجمات

- **Replay Attack**: استخدام التوكنات المؤقتة
- **Man-in-the-Middle**: HTTPS إجباري
- **Token Tampering**: التحقق من التوقيع
- **Brute Force**: تحديد محاولات المسح

---

## 🛠️ أوامر الإدارة

### توليد QR Codes

```bash
# لجميع الكيانات
python manage.py populate_qr_codes --entity=all

# لنوع محدد
python manage.py populate_qr_codes --entity=device
python manage.py populate_qr_codes --entity=patient
python manage.py populate_qr_codes --entity=bed
python manage.py populate_qr_codes --entity=user
python manage.py populate_qr_codes --entity=accessory

# وضع المعاينة (بدون تنفيذ)
python manage.py populate_qr_codes --dry-run
```

### تنظيف QR القديمة

```bash
# حذف QR codes غير المستخدمة
python manage.py clear_old_qr_codes

# حذف جلسات المسح المنتهية
python manage.py clear_expired_sessions
```

### إحصائيات النظام

```bash
# عرض إحصائيات الاستخدام
python manage.py qr_stats

# تصدير التقارير
python manage.py export_qr_logs --format=csv --output=report.csv
```

---

## 🐛 استكشاف الأخطاء

### الأخطاء الشائعة وحلولها

#### 1. "Token expired or not found"
**السبب**: انتهاء صلاحية التوكن المؤقت (60 ثانية)

**الحل**:
```python
# إعادة توليد التوكن
instance.qr_token = instance.generate_qr_token()
instance.save()
```

#### 2. "Invalid signature"
**السبب**: تلاعب في محتوى التوكن

**الحل**:
- التحقق من سلامة البيانات
- إعادة توليد التوكن من المصدر
- مراجعة سجلات الأمان

#### 3. "Entity not found"
**السبب**: الكيان المرتبط بالتوكن محذوف

**الحل**:
```bash
# تنظيف التوكنات القديمة
python manage.py clear_old_qr_codes
```

#### 4. "Operation not matched"
**السبب**: تسلسل المسح لا يطابق أي عملية

**الحل**:
- مراجعة تعريفات العمليات
- التأكد من الترتيب الصحيح للمسح
- إضافة عملية جديدة إذا لزم

#### 5. "Session timeout"
**السبب**: انتهاء وقت الجلسة (5 دقائق افتراضياً)

**الحل**:
```python
# تمديد وقت الجلسة
operation.session_timeout_minutes = 10
operation.save()
```

---

## 💡 أمثلة عملية

### مثال 1: نقل جهاز بين الأقسام

```python
# 1. الفني يمسح QR الجهاز
scan_1 = {
    "entity_type": "device",
    "entity_id": "123"
}

# 2. الفني يمسح QR القسم الجديد
scan_2 = {
    "entity_type": "department",
    "entity_id": "5"
}

# 3. النظام يكتشف عملية DEVICE_TRANSFER
operation = "DEVICE_TRANSFER"

# 4. التنفيذ
device = Device.objects.get(id=123)
old_dept = device.department
device.department_id = 5
device.save()

# 5. التوثيق
DeviceTransferLog.objects.create(
    device=device,
    from_department=old_dept,
    to_department_id=5,
    transferred_by=user,
    transfer_date=timezone.now()
)
```

### مثال 2: استخدام جهاز على مريض

```python
# 1. الممرض يمسح QR المريض
scan_1 = {"entity_type": "patient", "entity_id": "456"}

# 2. الممرض يمسح QR الجهاز
scan_2 = {"entity_type": "device", "entity_id": "789"}

# 3. النظام ينفذ DEVICE_USAGE تلقائياً
DeviceUsageLog.objects.create(
    patient_id=456,
    device_id=789,
    used_by=nurse,
    start_time=timezone.now()
)
```

### مثال 3: تنظيف وتعقيم جهاز

```python
# 1. مسح QR الجهاز
scan = {"entity_type": "device", "entity_id": "321"}

# 2. اختيار العملية (تنظيف أو تعقيم)
operation = "DEVICE_CLEANING"  # أو "DEVICE_STERILIZATION"

# 3. التنفيذ
device = Device.objects.get(id=321)
device.clean_status = 'clean'
device.last_cleaned_at = timezone.now()
device.last_cleaned_by = user
device.save()
```

---

## 📊 التقارير والإحصائيات

### البيانات المتاحة

1. **إحصائيات المسح**
   - عدد المسحات اليومية/الشهرية
   - أكثر الأجهزة استخداماً
   - أوقات الذروة

2. **تحليل العمليات**
   - العمليات الأكثر تنفيذاً
   - متوسط وقت التنفيذ
   - معدل النجاح/الفشل

3. **أداء المستخدمين**
   - عدد المسحات لكل مستخدم
   - العمليات المنفذة
   - الأخطاء الشائعة

### تصدير التقارير

```python
# views.py
def export_qr_report(request):
    logs = QRScanLog.objects.filter(
        created_at__gte=timezone.now() - timedelta(days=30)
    )
    
    # تصدير CSV
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="qr_report.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Date', 'User', 'Entity', 'Operation', 'Status'])
    
    for log in logs:
        writer.writerow([
            log.created_at,
            log.scanned_by,
            log.entity_type,
            log.flow_name,
            'Success' if log.flow_executed else 'Failed'
        ])
    
    return response
```

---

## 🔄 التكامل مع الأنظمة الأخرى

### 1. نظام المختبر
- QR codes للعينات
- تتبع نتائج التحاليل
- ربط العينات بالمرضى

### 2. نظام الصيدلية
- QR codes للأدوية
- تتبع الصلاحيات
- إدارة المخزون

### 3. نظام الموارد البشرية
- بطاقات الموظفين بـ QR
- تسجيل الحضور والانصراف
- الوصول للأماكن المحظورة

### 4. نظام المالية
- QR codes للفواتير
- المدفوعات الإلكترونية
- تتبع المصروفات

---

## 📈 خارطة الطريق

### الإصدار الحالي (v2.0.0)
✅ توليد QR تلقائي
✅ مسح وتنفيذ العمليات
✅ نظام أمان متقدم
✅ تتبع وإحصائيات

### الإصدار القادم (v2.1.0)
🔄 دعم NFC tags
🔄 تطبيق موبايل مخصص
🔄 تكامل مع IoT devices
🔄 AI للتنبؤ بالأعطال

### الإصدار المستقبلي (v3.0.0)
📅 Blockchain للتوثيق
📅 تحليلات متقدمة بـ ML
📅 واجهة AR للصيانة
📅 تكامل مع أنظمة خارجية

---







