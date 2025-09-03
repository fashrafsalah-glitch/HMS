# 🔧 نظام الصيانة الوقائية (Preventive Maintenance System) - HMS

## 🎯 نظرة عامة

يوفر نظام HMS نظاماً متطوراً للصيانة الوقائية يضمن الحفاظ على الأجهزة الطبية في أفضل حالاتها التشغيلية. النظام يدير الجدولة التلقائية والتنفيذ والمتابعة للصيانة الوقائية مع تتبع دقيق للأداء والتكاليف.

### 🏗️ مكونات النظام

- **📅 PM Scheduling System**: نظام الجدولة التلقائية
- **📋 Job Plans**: خطط العمل المفصلة
- **👨‍🔧 Technician Workflow**: تدفق عمل الفنيين
- **📊 Compliance Tracking**: تتبع الالتزام بالجداول
- **🤖 Automated Scheduler**: المجدول التلقائي
- **📈 Performance Analytics**: تحليلات الأداء

---

## 📅 نظام الجدولة التلقائية

### 1. 🎛️ إنشاء جداول الصيانة

#### أنواع التكرار:
```python
FREQUENCY_CHOICES = [
    ('daily', 'يومي'),
    ('weekly', 'أسبوعي'),
    ('monthly', 'شهري'),
    ('quarterly', 'ربع سنوي'),
    ('semi_annual', 'نصف سنوي'),
    ('annual', 'سنوي'),
    ('custom', 'مخصص')
]
```

#### الجدولة الذكية حسب نوع الجهاز:
- **🫁 أجهزة التنفس الصناعي**: كل 30 يوم
- **📊 أجهزة المراقبة**: كل 90 يوم
- **💉 المضخات الطبية**: كل 60 يوم
- **🩺 أجهزة الغسيل الكلوي**: كل 15 يوم
- **📷 أجهزة الأشعة**: كل 180 يوم
- **🔊 الموجات فوق الصوتية**: كل 90 يوم

### 2. 🤖 المجدول التلقائي (Scheduler)

#### المهام اليومية:
```python
def run_all_scheduled_tasks():
    """تشغيل جميع المهام المجدولة يومياً"""
    - create_due_preventive_maintenance()  # إنشاء PM مستحقة
    - check_sla_violations()               # فحص انتهاكات SLA
    - check_due_calibrations()             # فحص المعايرات
    - check_low_stock_spare_parts()        # فحص قطع الغيار
    - update_overdue_work_orders()         # تحديث المتأخرات
    - process_notification_queue()         # معالجة الإشعارات
```

#### إنشاء طلبات الصيانة تلقائياً:
```python
# عند استحقاق الصيانة
service_request = ServiceRequest.objects.create(
    title=f"صيانة وقائية - {device.name}",
    device=device,
    request_type='preventive',
    priority='medium',
    is_auto_generated=True
)
```

---

## 📋 خطط العمل (Job Plans)

### 🔧 مكونات خطة العمل

#### معلومات أساسية:
```python
class JobPlan:
    title = "اسم خطة العمل"
    description = "وصف تفصيلي للأعمال"
    device_category = "فئة الأجهزة المستهدفة"
    estimated_duration = "المدة المقدرة بالدقائق"
    required_tools = "الأدوات المطلوبة"
    safety_requirements = "متطلبات السلامة"
```

#### خطوات العمل المفصلة:
```python
class JobPlanStep:
    step_number = "رقم الخطوة"
    title = "عنوان الخطوة"
    description = "وصف تفصيلي"
    estimated_minutes = "الوقت المقدر"
    required_tools = "الأدوات المطلوبة"
    safety_notes = "ملاحظات السلامة"
    is_critical = "خطوة حرجة؟"
```

### 📝 أمثلة خطط العمل

#### خطة صيانة جهاز التنفس الصناعي:
1. **🔍 الفحص البصري** - فحص الأجزاء الخارجية
2. **🧹 التنظيف العام** - تنظيف الأسطح والمرشحات
3. **🔧 فحص الاتصالات** - التأكد من سلامة الكابلات
4. **⚡ اختبار الكهرباء** - فحص الجهد والتيار
5. **🌬️ اختبار التهوية** - قياس معدل التدفق
6. **📊 معايرة أجهزة القياس** - ضبط الحساسات
7. **✅ الاختبار النهائي** - تشغيل تجريبي كامل

---

## 👨‍🔧 تدفق عمل الفنيين

### 📱 واجهة الفني

#### لوحة المهام الوقائية:
```html
<div class="pm-dashboard">
    <div class="pm-card due-today">
        🔴 مستحقة اليوم: 5 أجهزة
    </div>
    <div class="pm-card due-week">
        🟡 مستحقة هذا الأسبوع: 12 جهاز
    </div>
    <div class="pm-card overdue">
        ⚠️ متأخرة: 2 أجهزة
    </div>
</div>
```

#### فلترة المهام:
- **📅 حسب التاريخ**: اليوم، الأسبوع، الشهر
- **📍 حسب القسم**: العناية المركزة، الطوارئ، العمليات
- **🎯 حسب الأولوية**: عالية، متوسطة، منخفضة
- **👤 المسندة للفني**: مهامي الشخصية

### 🔧 تنفيذ الصيانة الوقائية

#### خطوات التنفيذ:
1. **📋 استلام المهمة** - قبول أمر الشغل
2. **📍 الانتقال للموقع** - تحديد موقع الجهاز
3. **🔍 الفحص الأولي** - تقييم حالة الجهاز
4. **📝 تنفيذ الخطوات** - اتباع خطة العمل
5. **✅ التحقق من الجودة** - اختبار الأداء
6. **📄 التوثيق** - تسجيل النتائج
7. **🏁 إغلاق المهمة** - تأكيد الإنجاز

#### نموذج تنفيذ الخطوة:
```python
class JobPlanStepExecution:
    step = "الخطوة المرجعية"
    status = "completed/skipped/failed"
    actual_minutes = "الوقت الفعلي"
    notes = "ملاحظات التنفيذ"
    issues_found = "المشاكل المكتشفة"
    corrective_action = "الإجراء التصحيحي"
```

---

## 📊 تتبع الالتزام (Compliance Tracking)

### 📈 مؤشرات الأداء

#### نسبة الالتزام:
```python
def calculate_pm_compliance():
    """حساب نسبة الالتزام بالصيانة الوقائية"""
    total_due = scheduled_pm_count
    completed_on_time = completed_within_sla_count
    compliance_rate = (completed_on_time / total_due) * 100
    return compliance_rate
```

#### مؤشرات رئيسية:
- **📅 الالتزام بالجدول**: نسبة المهام المنجزة في الوقت
- **⏱️ متوسط وقت التنفيذ**: مقارنة بالوقت المقدر
- **🎯 معدل اكتشاف المشاكل**: المشاكل المكتشفة مبكراً
- **💰 توفير التكلفة**: مقارنة بالصيانة التصحيحية

### 🎛️ Dashboard المراقبة

#### الكاردات الرئيسية:
```javascript
{
    "pm_compliance": "95%",           // نسبة الالتزام
    "overdue_pm": 3,                 // المتأخرة
    "due_this_week": 15,             // مستحقة هذا الأسبوع
    "avg_completion_time": "2.5hrs", // متوسط وقت الإنجاز
    "cost_savings": "25000 SAR"      // التوفير المحقق
}
```

#### الرسوم البيانية:
- **📊 اتجاه الالتزام** الشهري
- **⏰ توزيع أوقات التنفيذ**
- **🔧 أنواع المشاكل** المكتشفة
- **💵 مقارنة التكاليف** وقائية vs تصحيحية

---

## 🚨 نظام التنبيهات والإشعارات

### 📧 إشعارات المجدولة

#### للفنيين:
- **📅 تذكير قبل 3 أيام** من موعد الصيانة
- **🔔 إشعار يوم الاستحقاق**
- **⚠️ تنبيه التأخير** بعد تجاوز الموعد
- **✅ تأكيد الإنجاز**

#### للمشرفين:
- **📊 تقرير أسبوعي** بالمهام المستحقة
- **🚨 تنبيه المتأخرات**
- **📈 ملخص الأداء** الشهري
- **💰 تقرير التكاليف**

### 📱 قنوات الإشعار

#### حسب نوع المستخدم:
```python
notification_preferences = {
    'technician': ['app', 'email'],
    'supervisor': ['app', 'email', 'sms'],
    'manager': ['email', 'dashboard'],
    'admin': ['all_channels']
}
```

---

## 🔄 التكامل مع الأنظمة الأخرى

### 🔗 ربط مع نظام الأعطال

#### التحويل التلقائي:
```python
def convert_pm_to_corrective(pm_work_order):
    """تحويل صيانة وقائية لتصحيحية عند اكتشاف عطل"""
    if issues_found_during_pm:
        corrective_sr = ServiceRequest.objects.create(
            title=f"عطل مكتشف أثناء الصيانة الوقائية",
            device=pm_work_order.device,
            request_type='corrective',
            priority='high',
            parent_pm=pm_work_order
        )
```

### 📦 ربط مع قطع الغيار

#### طلب قطع الغيار المجدولة:
```python
def schedule_spare_parts_for_pm():
    """طلب قطع الغيار للصيانة الوقائية المجدولة"""
    upcoming_pm = get_upcoming_pm_schedules(days=7)
    for pm in upcoming_pm:
        required_parts = pm.job_plan.required_spare_parts.all()
        for part in required_parts:
            create_spare_part_request(part, pm.scheduled_date)
```

---

## 📋 إدارة خطط العمل

### ✏️ إنشاء وتعديل خطط العمل

#### واجهة إنشاء الخطة:
```html
<form class="job-plan-form">
    <input name="title" placeholder="اسم خطة العمل">
    <select name="device_category">فئة الأجهزة</select>
    <input name="duration" placeholder="المدة المقدرة (دقيقة)">
    <textarea name="description">وصف الخطة</textarea>
    
    <!-- خطوات العمل -->
    <div class="job-steps">
        <div class="step">
            <input name="step_title" placeholder="عنوان الخطوة">
            <textarea name="step_description">وصف الخطوة</textarea>
            <input name="step_duration" placeholder="الوقت (دقيقة)">
        </div>
    </div>
</form>
```

#### مكتبة الخطط المعيارية:
- **🫁 أجهزة التنفس الصناعي** - 15 خطوة معيارية
- **📊 أجهزة المراقبة** - 10 خطوات أساسية
- **💉 المضخات الطبية** - 12 خطوة شاملة
- **🩺 أجهزة الغسيل الكلوي** - 20 خطوة مفصلة

### 📚 مكتبة المعرفة

#### قاعدة بيانات الخبرات:
```python
class MaintenanceKnowledge:
    device_type = "نوع الجهاز"
    common_issues = "المشاكل الشائعة"
    solutions = "الحلول المجربة"
    best_practices = "أفضل الممارسات"
    safety_tips = "نصائح السلامة"
    troubleshooting = "دليل استكشاف الأخطاء"
```

---

## 📊 التقارير والتحليلات

### 📈 تقارير الأداء

#### تقرير الالتزام الشهري:
```python
monthly_compliance_report = {
    'total_scheduled': 150,
    'completed_on_time': 142,
    'overdue': 8,
    'compliance_rate': '94.7%',
    'avg_completion_time': '2.3 hours',
    'issues_discovered': 23,
    'cost_savings': '18,500 SAR'
}
```

#### تقرير كفاءة الفنيين:
- **👤 الفني الأول**: 98% التزام، 2.1 ساعة متوسط
- **👤 الفني الثاني**: 95% التزام، 2.4 ساعة متوسط
- **👤 الفني الثالث**: 92% التزام، 2.8 ساعة متوسط

### 📊 تحليلات متقدمة

#### اتجاهات الصيانة:
```javascript
// رسم بياني لاتجاهات الصيانة الوقائية
const pmTrends = {
    labels: ['يناير', 'فبراير', 'مارس', 'أبريل'],
    datasets: [{
        label: 'مهام مجدولة',
        data: [45, 52, 48, 61],
        backgroundColor: 'blue'
    }, {
        label: 'مهام منجزة',
        data: [43, 49, 46, 58],
        backgroundColor: 'green'
    }]
}
```

---

## 🔧 الإعدادات والتخصيص

### ⚙️ إعدادات النظام

#### تخصيص فترات الصيانة:
```python
MAINTENANCE_FREQUENCIES = {
    'critical_devices': 15,    # أجهزة حرجة - كل 15 يوم
    'high_usage': 30,          # استخدام عالي - شهرياً
    'standard': 90,            # معياري - كل 3 أشهر
    'low_usage': 180,          # استخدام قليل - كل 6 أشهر
}
```

#### إعدادات التنبيهات:
```python
NOTIFICATION_SETTINGS = {
    'advance_warning_days': 3,      # تنبيه مسبق
    'overdue_escalation_days': 1,   # تصعيد التأخير
    'reminder_frequency_hours': 24, # تكرار التذكير
    'supervisor_cc': True           # نسخة للمشرف
}
```

### 👥 إدارة الأدوار

#### صلاحيات الفنيين:
- **👀 عرض** المهام المسندة إليهم
- **✏️ تحديث** حالة التنفيذ
- **📝 إضافة** ملاحظات ونتائج
- **📷 رفع** صور للأعمال المنجزة

#### صلاحيات المشرفين:
- **👁️ مراقبة** جميع المهام في القسم
- **👤 تعيين** الفنيين للمهام
- **✅ مراجعة** وموافقة الأعمال
- **📊 عرض** تقارير الأداء

---

## 🚀 الميزات المتقدمة

### 🤖 الذكاء الاصطناعي

#### التنبؤ بالصيانة:
```python
def predict_maintenance_needs(device):
    """التنبؤ بحاجة الجهاز للصيانة"""
    factors = {
        'usage_hours': device.total_usage_hours,
        'last_pm_date': device.last_pm_date,
        'failure_history': device.failure_count,
        'environmental_factors': device.location_conditions
    }
    return ai_model.predict_maintenance_window(factors)
```

#### تحسين الجدولة:
- **📅 تجميع المهام** في نفس القسم
- **👥 توزيع العبء** على الفنيين
- **⏰ تحسين الأوقات** لتقليل التوقف
- **🔧 تنسيق قطع الغيار** مع المهام

### 📱 التطبيق المحمول

#### للفنيين الميدانيين:
- **📋 قائمة المهام** اليومية
- **📍 خرائط الأجهزة** مع المواقع
- **📷 التوثيق المرئي** للأعمال
- **✅ تأكيد الإنجاز** فوري

---

## 🛡️ ضمان الجودة

### ✅ مراجعة الأعمال

#### نظام المراجعة المتدرج:
1. **🔍 مراجعة ذاتية** من الفني
2. **👤 مراجعة المشرف** للأعمال الحرجة
3. **🎯 مراجعة الجودة** العشوائية
4. **📊 تقييم الأداء** الدوري

#### معايير الجودة:
```python
quality_criteria = {
    'completeness': 'اكتمال جميع الخطوات',
    'accuracy': 'دقة القياسات والاختبارات',
    'documentation': 'جودة التوثيق',
    'safety': 'الالتزام بمعايير السلامة',
    'timeliness': 'الإنجاز في الوقت المحدد'
}
```

### 📋 التدقيق والمراجعة

#### سجل التدقيق:
- **📅 تاريخ ووقت** كل عملية
- **👤 المستخدم** المنفذ
- **🔄 التغييرات** المطبقة
- **📝 السبب** والمبرر

---

## 💰 إدارة التكاليف

### 📊 تتبع التكاليف

#### مكونات التكلفة:
```python
pm_cost_breakdown = {
    'labor_cost': 'تكلفة العمالة',
    'spare_parts_cost': 'تكلفة قطع الغيار',
    'tools_cost': 'تكلفة الأدوات',
    'downtime_cost': 'تكلفة التوقف',
    'overhead_cost': 'التكاليف الإضافية'
}
```

#### مقارنة التكاليف:
- **🔧 الصيانة الوقائية**: 1000 ريال/شهر
- **⚠️ الصيانة التصحيحية**: 3500 ريال/شهر
- **💰 التوفير المحقق**: 2500 ريال/شهر (71%)

### 📈 عائد الاستثمار

#### حساب ROI للصيانة الوقائية:
```python
def calculate_pm_roi():
    preventive_cost = total_pm_cost_per_year
    avoided_corrective_cost = estimated_breakdown_cost_avoided
    roi_percentage = ((avoided_corrective_cost - preventive_cost) / preventive_cost) * 100
    return roi_percentage
```

---

## ✅ الخلاصة

نظام الصيانة الوقائية في HMS يوفر:

- **📅 جدولة تلقائية ذكية** للصيانة الوقائية
- **📋 خطط عمل مفصلة** قابلة للتخصيص
- **👨‍🔧 واجهات سهلة** للفنيين والمشرفين
- **📊 تتبع دقيق للالتزام** والأداء
- **🤖 أتمتة كاملة** للعمليات الروتينية
- **📈 تحليلات متقدمة** لتحسين الأداء
- **💰 تحكم فعال** في التكاليف
- **🛡️ ضمان جودة** شامل

النظام مصمم لضمان أعلى مستويات الموثوقية والكفاءة للأجهزة الطبية، مما يقلل من الأعطال المفاجئة ويضمن استمرارية الخدمات الطبية بأقل تكلفة ممكنة. 🏥✨
