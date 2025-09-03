# 📊 نظام مؤشرات الأداء الرئيسية (KPI System) - HMS

## 🎯 نظرة عامة

يحتوي نظام HMS على نظام متطور لمؤشرات الأداء الرئيسية (KPIs) يوفر مراقبة شاملة وتحليل دقيق لأداء الصيانة والأجهزة الطبية. النظام يحسب المؤشرات تلقائياً ويعرضها في لوحات تحكم تفاعلية مع إمكانية التصدير والتحليل المتقدم.

### 🏗️ مكونات النظام

- **📈 KPI Utils (`kpi_utils.py`)**: محرك حساب المؤشرات الأساسي
- **🖥️ Dashboard Views (`views_dashboard.py`)**: واجهات عرض البيانات
- **🎨 Dashboard Templates**: قوالب HTML التفاعلية
- **📊 Real-time Calculations**: حسابات فورية للمؤشرات

---

## 📊 المؤشرات الأساسية (Core KPIs)

### 1. 🔧 متوسط وقت الإصلاح (MTTR - Mean Time To Repair)

```python
def calculate_mttr(device_id=None, department_id=None, days=30):
```

**الوظيفة**: قياس متوسط الوقت المطلوب لإصلاح الأعطال

**المعالجة**:
- حساب من الأوقات الفعلية (`actual_start` و `actual_end`)
- استخدام تقديرات SLA عند عدم توفر البيانات الفعلية
- تطبيق خطط العمل (Job Plans) للتقدير
- تصنيف حسب الأولوية والنوع

**المصادر**:
- أوامر الشغل المكتملة
- تعريفات SLA
- خطط العمل
- حالة الأجهزة

### 2. ⏰ متوسط الوقت بين الأعطال (MTBF - Mean Time Between Failures)

```python
def calculate_mtbf(device_id=None, department_id=None, days=30):
```

**الوظيفة**: قياس الموثوقية وتكرار الأعطال

**المعالجة**:
- حساب الفترات الزمنية بين الأعطال المتتالية
- تقدير بناءً على SLA للأجهزة بدون أعطال
- تطبيق عوامل حالة الجهاز
- حساب متوسط مرجح للأجهزة المتعددة

**الخوارزمية**:
```python
# للأجهزة مع أعطال متعددة
intervals = []
for i in range(1, failure_count):
    interval = curr_failure_time - prev_failure_time
    intervals.append(interval)
mtbf = sum(intervals) / len(intervals)

# للأجهزة بدون أعطال - تقدير من SLA
estimated_mtbf = sla.resolution_time_hours * 10
```

### 3. 📈 نسبة التوفر (Availability)

```python
def calculate_availability(device_id=None, department_id=None, days=30):
```

**الوظيفة**: قياس نسبة وقت تشغيل الأجهزة

**المعالجة**:
- حساب إجمالي وقت التوقف من أوامر الشغل
- تطبيق تأثير حالة الجهاز الحالية
- احتساب الصيانة الوقائية المجدولة
- مراعاة معايير SLA المستهدفة

**المعادلة**:
```python
uptime_hours = total_period_hours - total_downtime_hours
availability = (uptime_hours / total_period_hours) * 100
```

### 4. ✅ نسبة الالتزام بالصيانة الوقائية (PM Compliance)

```python
def calculate_pm_compliance(department_id=None, device_id=None, days=30):
```

**الوظيفة**: قياس الالتزام بجداول الصيانة الوقائية

**المعالجة**:
- مقارنة الجداول المستحقة مع المنفذة
- فحص أوامر الشغل الوقائية المكتملة
- حساب نسبة الإنجاز في الوقت المحدد

### 5. 📋 إحصائيات أوامر الشغل (Work Order Statistics)

```python
def calculate_work_order_stats(department_id=None, days=30):
```

**الوظيفة**: تحليل شامل لأوامر الشغل وحالاتها

**المؤشرات المحسوبة**:
- إجمالي أوامر الشغل
- معدل الإنجاز
- نسبة التأخير
- توزيع الحالات
- الاتجاهات الزمنية

### 6. 📦 إحصائيات قطع الغيار (Spare Parts Analytics)

```python
def calculate_spare_parts_stats(department_id=None):
```

**الوظيفة**: مراقبة المخزون وحركة قطع الغيار

**المؤشرات**:
- نسبة التوفر
- المخزون المنخفض
- القيمة الإجمالية
- معدل الدوران

---

## 🎛️ لوحات التحكم (Dashboards)

### 📊 لوحة التحكم الرئيسية

```python
@login_required
def cmms_dashboard(request):
```

**المميزات**:
- عرض المؤشرات الأساسية في كاردات ملونة
- التنبيهات الحرجة
- إحصائيات سريعة
- فلترة حسب القسم

**البيانات المعروضة**:
- إجمالي الأجهزة
- أوامر الشغل النشطة
- أوامر الشغل المتأخرة
- قطع الغيار المنخفضة

### 🏆 لوحة أداء الأجهزة

```python
@login_required
def device_performance_dashboard(request):
```

**المميزات**:
- نقاط أداء الأجهزة (من 100)
- تصنيف الأداء (ممتاز، جيد جداً، جيد، مقبول، ضعيف)
- تحليل الأعطال حسب النوع
- رسوم بيانية تفاعلية

**خوارزمية نقاط الأداء**:
```python
def get_device_performance_score(device_id):
    score = 0
    # نقاط التوفر (40%)
    score += (availability / 100) * 40
    # نقاط MTBF (30%)
    score += min(30, (mtbf / 168) * 30)
    # نقاط MTTR (20%)
    score += max(0, 20 - (mttr / 24) * 20)
    # نقاط الصيانة الوقائية (10%)
    score += (pm_compliance / 100) * 10
```

### 📈 تحليلات أوامر الشغل

```python
@login_required
def work_order_analytics(request):
```

**التحليلات**:
- توزيع أوامر الشغل حسب الحالة والنوع
- اتجاهات أسبوعية وشهرية
- إحصائيات الفنيين
- نسبة الالتزام بـ SLA
- أوامر الشغل المتأخرة

### 📦 تحليلات قطع الغيار

```python
@login_required
def spare_parts_analytics(request):
```

**التحليلات**:
- قطع الغيار الأكثر استخداماً
- قطع الغيار المحتاجة إعادة طلب
- توزيع حسب الفئة
- معدل دوران المخزون

---

## 📊 الرسوم البيانية والتصورات

### 🎨 أنواع الرسوم البيانية

#### 1. رسم دائري - توزيع أوامر الشغل
```javascript
// Work Order Type Distribution
const workOrderTypeChart = new Chart(ctx, {
    type: 'doughnut',
    data: {
        labels: ['تصحيحية', 'وقائية', 'فحص', 'معايرة'],
        datasets: [{
            data: [corrective_count, preventive_count, inspection_count, calibration_count]
        }]
    }
});
```

#### 2. رسم خطي - اتجاهات التكلفة
```javascript
// Maintenance Cost Trend
const costTrendChart = new Chart(ctx, {
    type: 'line',
    data: {
        labels: monthly_labels,
        datasets: [{
            label: 'تكلفة الصيانة',
            data: monthly_costs,
            borderColor: 'rgb(75, 192, 192)',
            tension: 0.1
        }]
    }
});
```

#### 3. رسم عمودي - أداء الأجهزة
```javascript
// Device Performance Categories
const performanceChart = new Chart(ctx, {
    type: 'bar',
    data: {
        labels: ['ممتاز', 'جيد جداً', 'جيد', 'مقبول', 'ضعيف'],
        datasets: [{
            data: [excellent_count, very_good_count, good_count, fair_count, poor_count]
        }]
    }
});
```

---

## 🔄 الاتجاهات والتحليل الزمني

### 📅 التحليل الشهري

```python
def get_monthly_trends(department_id=None, months=6):
```

**البيانات المحسوبة**:
- MTBF و MTTR الشهري
- نسبة التوفر
- معدل إنجاز أوامر الشغل
- الالتزام بالصيانة الوقائية
- عدد الأعطال والإصلاحات

**الخوارزمية**:
```python
for i in range(months):
    month_start = current_date - timedelta(days=i*30)
    month_end = month_start + timedelta(days=30)
    
    # حساب إحصائيات الشهر
    monthly_data = {
        'mtbf': calculate_monthly_mtbf(month_start, month_end),
        'mttr': calculate_monthly_mttr(month_start, month_end),
        'availability': calculate_monthly_availability(month_start, month_end)
    }
```

### 📊 ملخص الداشبورد الشامل

```python
def get_dashboard_summary(department_id=None):
```

**المكونات**:
- جميع المؤشرات الأساسية
- إحصائيات أوامر الشغل
- إحصائيات قطع الغيار
- الاتجاهات الشهرية
- تاريخ آخر تحديث

---

## 🚨 نظام التنبيهات الحرجة

### 🔔 أنواع التنبيهات

```python
def get_critical_alerts(department_id=None):
```

#### 1. أوامر الشغل المتأخرة
```python
overdue_work_orders = WorkOrder.objects.filter(
    status__in=['new', 'assigned', 'in_progress'],
    created_at__lt=timezone.now() - timedelta(days=7)
)
```

#### 2. قطع الغيار المنتهية
```python
out_of_stock_parts = SparePart.objects.filter(current_stock=0)
```

#### 3. المخزون المنخفض
```python
low_stock_parts = SparePart.objects.filter(
    current_stock__lte=F('minimum_stock')
)
```

#### 4. الأجهزة المحتاجة معايرة
```python
devices_need_calibration = Device.objects.filter(
    calibration_records__next_calibration_date__lte=timezone.now().date() + timedelta(days=7)
)
```

### 🎨 تصنيف التنبيهات

| النوع | الخطورة | اللون | الإجراء المطلوب |
|-------|---------|-------|------------------|
| أوامر شغل متأخرة | عالية | 🔴 أحمر | متابعة فورية |
| قطع غيار منتهية | متوسطة | 🟠 برتقالي | طلب عاجل |
| مخزون منخفض | منخفضة | 🟡 أصفر | تخطيط الطلب |
| معايرة مستحقة | متوسطة | 🔵 أزرق | جدولة المعايرة |

---

## 🎯 نقاط الأداء والتقييم

### 🏆 نظام نقاط الأجهزة

```python
def get_device_performance_score(device_id):
```

**معايير التقييم**:

| النقاط | التصنيف | اللون | الوصف |
|--------|----------|-------|--------|
| 90-100 | ممتاز | 🟢 أخضر | أداء استثنائي |
| 80-89 | جيد جداً | 🔵 أزرق | أداء جيد |
| 70-79 | جيد | 🟣 بنفسجي | أداء مقبول |
| 50-69 | مقبول | 🟡 أصفر | يحتاج تحسين |
| 0-49 | ضعيف | 🔴 أحمر | يحتاج تدخل عاجل |

**توزيع النقاط**:
- **التوفر (40%)**: نسبة وقت التشغيل
- **MTBF (30%)**: الموثوقية وقلة الأعطال
- **MTTR (20%)**: سرعة الإصلاح
- **الصيانة الوقائية (10%)**: الالتزام بالجداول

### 📊 مؤشرات الأداء المتقدمة

#### 1. معدل الأعطال (Failure Rate)
```python
failure_rate = total_failures / operational_hours
```

#### 2. كفاءة الصيانة (Maintenance Efficiency)
```python
efficiency = completed_work_orders / total_work_orders * 100
```

#### 3. التكلفة لكل ساعة تشغيل (Cost per Operating Hour)
```python
cost_per_hour = total_maintenance_cost / total_operating_hours
```

---

## 🔧 التخصيص والإعدادات

### ⚙️ معايير SLA

```python
# إعداد معايير SLA حسب فئة الجهاز
sla_configs = [
    {
        'name': 'حرج - استجابة فورية',
        'response_time_minutes': 5,
        'resolution_time_hours': 1,
        'escalation_time_minutes': 15,
    },
    {
        'name': 'عالي - استجابة سريعة', 
        'response_time_minutes': 15,
        'resolution_time_hours': 4,
        'escalation_time_minutes': 30,
    }
]
```

### 🎨 تخصيص الألوان والعتبات

```python
# عتبات الأداء
PERFORMANCE_THRESHOLDS = {
    'excellent': 90,
    'very_good': 80,
    'good': 70,
    'fair': 50,
    'poor': 0
}

# ألوان المؤشرات
KPI_COLORS = {
    'success': '#1cc88a',
    'warning': '#f6c23e', 
    'danger': '#e74a3b',
    'info': '#36b9cc',
    'primary': '#4e73df'
}
```

---

## 📱 واجهة المستخدم التفاعلية

### 🎛️ مميزات الواجهة

#### 1. فلترة ديناميكية
```javascript
// فلترة حسب القسم
$('#department-filter').change(function() {
    const departmentId = $(this).val();
    updateDashboard(departmentId);
});

// فلترة حسب الفترة الزمنية
$('.period-filter').click(function() {
    const days = $(this).data('period');
    updateKPIs(days);
});
```

#### 2. تحديث فوري للبيانات
```javascript
// تحديث تلقائي كل 5 دقائق
setInterval(function() {
    refreshKPIData();
}, 300000);
```

#### 3. تصدير التقارير
```javascript
// تصدير إلى PDF/Excel
$('#export-report').click(function() {
    exportDashboardReport();
});
```

### 📊 الرسوم البيانية التفاعلية

```javascript
// إعداد Chart.js مع التفاعل
const chartConfig = {
    type: 'line',
    data: chartData,
    options: {
        responsive: true,
        interaction: {
            intersect: false,
            mode: 'index'
        },
        plugins: {
            legend: {
                display: true,
                position: 'top'
            },
            tooltip: {
                enabled: true,
                mode: 'nearest'
            }
        },
        scales: {
            x: {
                display: true,
                title: {
                    display: true,
                    text: 'الفترة الزمنية'
                }
            },
            y: {
                display: true,
                title: {
                    display: true,
                    text: 'القيمة'
                }
            }
        }
    }
};
```

---

## 🔄 التكامل مع النظام

### 📡 API Endpoints

```python
# API لجلب بيانات KPI
@api_view(['GET'])
def kpi_data_api(request):
    department_id = request.GET.get('department')
    days = int(request.GET.get('days', 30))
    
    data = {
        'mtbf': calculate_mtbf(department_id=department_id, days=days),
        'mttr': calculate_mttr(department_id=department_id, days=days),
        'availability': calculate_availability(department_id=department_id, days=days)
    }
    
    return Response(data)
```

### 🔗 ربط مع أنظمة خارجية

```python
# تصدير البيانات لأنظمة BI
def export_kpi_data_to_bi():
    kpi_data = get_dashboard_summary()
    
    # تحويل إلى JSON للتصدير
    export_data = {
        'timestamp': timezone.now().isoformat(),
        'kpis': kpi_data,
        'department_breakdown': get_department_kpis()
    }
    
    return export_data
```

---

## 📈 التحليل المتقدم والذكاء الاصطناعي

### 🤖 التنبؤ بالأعطال

```python
def predict_equipment_failure(device_id):
    """
    تنبؤ بالأعطال بناءً على البيانات التاريخية
    """
    device_history = get_device_maintenance_history(device_id)
    
    # تحليل الأنماط
    failure_pattern = analyze_failure_patterns(device_history)
    
    # حساب احتمالية العطل
    failure_probability = calculate_failure_probability(failure_pattern)
    
    return {
        'probability': failure_probability,
        'recommended_action': get_recommended_action(failure_probability),
        'next_maintenance_date': calculate_optimal_maintenance_date(device_id)
    }
```

### 📊 تحليل الاتجاهات

```python
def analyze_kpi_trends():
    """
    تحليل اتجاهات المؤشرات للتنبؤ بالأداء المستقبلي
    """
    monthly_trends = get_monthly_trends(months=12)
    
    trends_analysis = {
        'mtbf_trend': calculate_trend_direction(monthly_trends, 'mtbf'),
        'mttr_trend': calculate_trend_direction(monthly_trends, 'mttr'),
        'availability_trend': calculate_trend_direction(monthly_trends, 'availability'),
        'recommendations': generate_improvement_recommendations()
    }
    
    return trends_analysis
```

---

## 🎯 أفضل الممارسات والتوصيات

### ✅ معايير الأداء المستهدفة

| المؤشر | الهدف الأدنى | الهدف المثالي | الوحدة |
|--------|--------------|---------------|--------|
| MTTR | < 4 ساعات | < 2 ساعة | ساعة |
| MTBF | > 168 ساعة | > 720 ساعة | ساعة |
| التوفر | > 95% | > 98% | نسبة مئوية |
| الالتزام بالصيانة الوقائية | > 90% | > 98% | نسبة مئوية |
| معدل إنجاز أوامر الشغل | > 85% | > 95% | نسبة مئوية |

### 🔧 نصائح التحسين

#### 1. تحسين MTTR
- تدريب الفنيين المتخصص
- توفير قطع الغيار الأساسية
- تحسين إجراءات التشخيص
- استخدام تقنيات الصيانة التنبؤية

#### 2. زيادة MTBF
- تطبيق برامج الصيانة الوقائية
- مراقبة حالة الأجهزة
- تحسين بيئة التشغيل
- التدريب على الاستخدام الصحيح

#### 3. رفع نسبة التوفر
- تقليل أوقات التوقف المخطط لها
- تحسين كفاءة الصيانة
- استخدام قطع غيار عالية الجودة
- تطبيق الصيانة الشرطية

---

## 🛡️ الأمان وحماية البيانات

### 🔒 أمان البيانات

```python
# تشفير البيانات الحساسة
from django.contrib.auth.decorators import login_required, permission_required

@login_required
@permission_required('maintenance.view_kpi_dashboard')
def kpi_dashboard(request):
    # التحقق من صلاحيات المستخدم
    if not request.user.has_perm('maintenance.view_department_kpi'):
        # تقييد البيانات حسب القسم
        department_id = request.user.profile.department.id
    else:
        department_id = request.GET.get('department')
```

### 📋 سجلات الوصول

```python
# تسجيل الوصول للبيانات الحساسة
def log_kpi_access(user, action, data_type):
    AuditLog.objects.create(
        user=user,
        action=action,
        data_type=data_type,
        timestamp=timezone.now(),
        ip_address=get_client_ip(request)
    )
```

---

## 🚀 الأداء والتحسين

### ⚡ تحسين الاستعلامات

```python
# استخدام select_related و prefetch_related
work_orders = WorkOrder.objects.select_related(
    'service_request__device',
    'assignee'
).prefetch_related(
    'service_request__device__category'
).filter(status='closed')

# فهرسة قاعدة البيانات
class Meta:
    indexes = [
        models.Index(fields=['created_at', 'status']),
        models.Index(fields=['device', 'request_type']),
    ]
```

### 💾 التخزين المؤقت

```python
from django.core.cache import cache

def get_cached_kpi_data(department_id, days):
    cache_key = f"kpi_data_{department_id}_{days}"
    cached_data = cache.get(cache_key)
    
    if not cached_data:
        cached_data = calculate_kpi_data(department_id, days)
        cache.set(cache_key, cached_data, timeout=300)  # 5 دقائق
    
    return cached_data
```

---

## 📞 الدعم والصيانة

### 🔍 استكشاف الأخطاء

#### مشاكل شائعة وحلولها

1. **بطء تحميل الداشبورد**
   - فحص فهارس قاعدة البيانات
   - تحسين الاستعلامات
   - تفعيل التخزين المؤقت

2. **بيانات KPI غير دقيقة**
   - التحقق من اكتمال البيانات
   - فحص إعدادات SLA
   - مراجعة حسابات التواريخ

3. **عدم ظهور الرسوم البيانية**
   - التحقق من مكتبات JavaScript
   - فحص بيانات JSON
   - مراجعة أذونات المستخدم

### 📊 مراقبة الأداء

```python
# مراقبة أداء حسابات KPI
import time
import logging

def monitor_kpi_calculation(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        execution_time = time.time() - start_time
        
        logging.info(f"KPI calculation {func.__name__} took {execution_time:.2f} seconds")
        
        if execution_time > 5:  # تحذير إذا استغرق أكثر من 5 ثوانِ
            logging.warning(f"Slow KPI calculation detected: {func.__name__}")
        
        return result
    return wrapper
```

---

## 🎯 الخلاصة والنتائج

نظام KPI في HMS يوفر:

### ✅ المميزات الرئيسية
- **مراقبة شاملة**: جميع جوانب الصيانة والأجهزة
- **حسابات دقيقة**: بناءً على البيانات الفعلية و SLA
- **واجهة تفاعلية**: رسوم بيانية وتقارير ديناميكية
- **تنبيهات ذكية**: إشعارات فورية للمشاكل الحرجة
- **تحليل متقدم**: اتجاهات وتنبؤات مستقبلية

### 📊 القيمة المضافة
- **تحسين الكفاءة**: تقليل أوقات التوقف والإصلاح
- **توفير التكاليف**: تحسين استخدام الموارد
- **اتخاذ قرارات مدروسة**: بناءً على بيانات دقيقة
- **الامتثال للمعايير**: تطبيق معايير الجودة الدولية
- **التحسين المستمر**: مراقبة الأداء وتطوير العمليات

*تم تطوير هذا النظام لضمان أعلى مستويات الكفاءة والموثوقية في إدارة الأجهزة الطبية* 🏥📊
