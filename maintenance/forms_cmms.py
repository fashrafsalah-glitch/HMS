from django import forms
from .models import *
from django.contrib.auth import get_user_model

User = get_user_model()

class ServiceRequestForm(forms.ModelForm):
    """نموذج إنشاء وتعديل البلاغات"""
    
    # هنا بنعمل حقل مخفي عشان نعرف إذا كان البلاغ تلقائي ولا لأ
    is_auto_generated = forms.BooleanField(required=False, widget=forms.HiddenInput())
    auto_generated_reason = forms.CharField(required=False, widget=forms.HiddenInput())
    
    class Meta:
        model = ServiceRequest
        fields = ['device', 'title', 'description', 'request_type', 'severity', 'impact', 'is_auto_generated', 'auto_generated_reason']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }
    
    def __init__(self, *args, **kwargs):
        # هنا بناخد المستخدم الحالي عشان نعرف الأجهزة المتاحة له
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # هنا بنعدل شكل الفورم عشان يبقى أحلى
        for field_name, field in self.fields.items():
            if field_name not in ['is_auto_generated', 'auto_generated_reason']:
                field.widget.attrs['class'] = 'form-control'
        
        # هنا بنفلتر الأجهزة حسب صلاحيات المستخدم
        if self.user:
            # لو المستخدم مش أدمن، هنفلتر الأجهزة حسب القسم بتاعه
            if not self.user.is_superuser and hasattr(self.user, 'department'):
                self.fields['device'].queryset = Device.objects.filter(department=self.user.department)
    
    def save(self, commit=True):
        """حفظ طلب الخدمة مع ربط Job Plan المناسب"""
        instance = super().save(commit=False)
        
        # ربط Job Plan المناسب بناءً على نوع الجهاز ونوع الطلب
        if not instance.estimated_hours:
            try:
                job_plan = JobPlan.objects.filter(
                    device_category=instance.device.category,
                    job_type=instance.request_type,
                    is_active=True
                ).first()
                
                if job_plan:
                    instance.estimated_hours = job_plan.estimated_hours
            except Exception:
                # قيمة افتراضية إذا لم يوجد Job Plan
                if instance.request_type == 'emergency':
                    instance.estimated_hours = 2.0
                elif instance.request_type == 'preventive':
                    instance.estimated_hours = 4.0
                else:
                    instance.estimated_hours = 3.0
        
        if commit:
            instance.save()
        return instance

class WorkOrderForm(forms.ModelForm):
    """نموذج إنشاء وتعديل أوامر الشغل"""
    
    class Meta:
        model = WorkOrder
        fields = ['description', 'assignee']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }
    
    def __init__(self, *args, **kwargs):
        # هنا بناخد المستخدم الحالي والبلاغ المرتبط
        self.user = kwargs.pop('user', None)
        self.service_request = kwargs.pop('service_request', None)
        super().__init__(*args, **kwargs)
        
        # هنا بنعدل شكل الفورم عشان يبقى أحلى
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
        
        # هنا بنفلتر الفنيين اللي ممكن يتعينوا على أمر الشغل
        # فلترة بناءً على رول المستخدم
        technicians = User.objects.filter(role='technician', is_active=True)
        self.fields['assignee'].queryset = technicians
        self.fields['assignee'].required = False  # ممكن نعمل أمر شغل بدون تعيين فني في البداية

class WorkOrderUpdateForm(forms.ModelForm):
    """نموذج تحديث حالة أمر الشغل"""
    
    class Meta:
        model = WorkOrder
        fields = ['status', 'completion_notes', 'qa_notes']
        widgets = {
            'completion_notes': forms.Textarea(attrs={'rows': 4}),
            'qa_notes': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # هنا بنعدل شكل الفورم عشان يبقى أحلى
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
        
        # هنا بنحدد الحالات المتاحة حسب الحالة الحالية والصلاحيات
        instance = kwargs.get('instance')
        if instance and self.user:
            available_statuses = []
            current_status = instance.status
            
            # هنا بنحدد الحالات المتاحة حسب الحالة الحالية
            if current_status == 'new':
                available_statuses = ['new', 'assigned', 'cancelled']
            elif current_status == 'assigned':
                available_statuses = ['assigned', 'in_progress', 'cancelled']
            elif current_status == 'in_progress':
                available_statuses = ['in_progress', 'wait_parts', 'on_hold', 'resolved', 'cancelled']
            elif current_status == 'wait_parts':
                available_statuses = ['wait_parts', 'in_progress', 'cancelled']
            elif current_status == 'on_hold':
                available_statuses = ['on_hold', 'in_progress', 'cancelled']
            elif current_status == 'resolved':
                available_statuses = ['resolved', 'qa_verified', 'in_progress']
            elif current_status == 'qa_verified':
                available_statuses = ['qa_verified', 'closed', 'in_progress']
            elif current_status == 'closed':
                available_statuses = ['closed']
            elif current_status == 'cancelled':
                available_statuses = ['cancelled']
            
            # هنا بنفلتر الحالات المتاحة حسب الصلاحيات
            # دي محتاجة تتعدل حسب نظام الصلاحيات في المشروع
            if not self.user.is_superuser:
                # مثلًا: فقط المشرفين يمكنهم التحقق من الجودة
                if 'qa_verified' in available_statuses and not self.user.groups.filter(name='Supervisor').exists():
                    available_statuses.remove('qa_verified')
            
            # هنا بنحط الحالات المتاحة في الفورم
            status_choices = [(status, dict(WorkOrder.status.field.choices)[status]) for status in available_statuses]
            self.fields['status'].choices = status_choices

# Commented out forms for models not yet implemented
# class WorkOrderCommentForm(forms.ModelForm):
#     """نموذج إضافة تعليق على أمر الشغل"""
#     
#     class Meta:
#         model = WorkOrderComment
#         fields = ['comment']
#         widgets = {
#             'comment': forms.Textarea(attrs={'rows': 2, 'placeholder': 'أضف تعليقًا...'}),
#         }
#     
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.fields['comment'].widget.attrs['class'] = 'form-control'

class SLADefinitionForm(forms.ModelForm):
    """نموذج إنشاء وتعديل تعريف اتفاقية مستوى الخدمة"""
    
    class Meta:
        model = SLADefinition
        fields = ['name', 'description', 'severity', 'priority', 'response_time_hours', 'resolution_time_hours', 'device_category']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'

# Commented out form for model not yet implemented
# class SLAMatrixForm(forms.ModelForm):
#     """نموذج إنشاء وتعديل مصفوفة اتفاقية مستوى الخدمة"""
#     
#     class Meta:
#         model = SLAMatrix
#         fields = ['severity', 'impact', 'sla']
#     
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         for field_name, field in self.fields.items():
#             field.widget.attrs['class'] = 'form-control'


class JobPlanForm(forms.ModelForm):
    """نموذج إنشاء وتعديل خطة العمل للصيانة الوقائية"""
    
    class Meta:
        model = JobPlan
        fields = ['name', 'description', 'device_category', 'job_type', 'estimated_hours', 'instructions', 'safety_notes']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'instructions': forms.Textarea(attrs={'rows': 4}),
            'safety_notes': forms.Textarea(attrs={'rows': 2}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'


class JobPlanStepForm(forms.ModelForm):
    """نموذج إنشاء وتعديل خطوات العمل في خطة الصيانة الوقائية"""
    
    class Meta:
        model = JobPlanStep
        fields = ['step_number', 'title', 'description', 'estimated_minutes']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 2}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control' 
class PMScheduleForm(forms.ModelForm):
    """نموذج إنشاء وتعديل جدول الصيانة الوقائية"""
    
    class Meta:
        model = PreventiveMaintenanceSchedule
        fields = ['name', 'description', 'device', 'job_plan', 'frequency', 'interval_days', 'start_date', 'end_date', 'assigned_to']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # تنسيق الحقول
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
        
        # تحديد الأجهزة المتاحة حسب صلاحيات المستخدم
        if self.user and not self.user.is_superuser and hasattr(self.user, 'department'):
            self.fields['device'].queryset = Device.objects.filter(department=self.user.department)
        
        # تحديد الفنيين المتاحين للتعيين
        # فلترة الفنيين بناءً على الرول
        technicians = User.objects.filter(role='technician', is_active=True)
        self.fields['assigned_to'].queryset = technicians
        
        # إخفاء حقول معينة حسب التكرار المختار (إذا كانت موجودة)
        instance = kwargs.get('instance')
        if instance:
            if instance.frequency != 'weekly' and 'day_of_week' in self.fields:
                self.fields['day_of_week'].widget = forms.HiddenInput()
            if instance.frequency != 'monthly' and 'day_of_month' in self.fields:
                self.fields['day_of_month'].widget = forms.HiddenInput()

# =============== Work Order Parts Forms ===============
class WorkOrderPartRequestForm(forms.ModelForm):
    """نموذج طلب قطع الغيار من المخزن لأمر الشغل"""
    
    class Meta:
        model = WorkOrderPart
        fields = ['spare_part', 'quantity_requested', 'notes']
        widgets = {
            'spare_part': forms.Select(attrs={
                'class': 'form-control',
                'data-live-search': 'true'
            }),
            'quantity_requested': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'placeholder': 'الكمية المطلوبة'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'ملاحظات حول القطعة المطلوبة'
            }),
        }
        labels = {
            'spare_part': 'قطعة الغيار',
            'quantity_requested': 'الكمية المطلوبة',
            'notes': 'ملاحظات',
        }
    
    def __init__(self, *args, **kwargs):
        self.work_order = kwargs.pop('work_order', None)
        super().__init__(*args, **kwargs)
        
        # فلترة قطع الغيار حسب فئة الجهاز
        if self.work_order and self.work_order.service_request.device:
            device = self.work_order.service_request.device
            if device.category:
                self.fields['spare_part'].queryset = SparePart.objects.filter(
                    device_category=device.category,
                    current_stock__gt=0
                ).order_by('name')
        
        # تنسيق الحقول
        for field_name, field in self.fields.items():
            if field_name != 'spare_part':
                field.widget.attrs['class'] = 'form-control'
    
    def clean_quantity_requested(self):
        quantity = self.cleaned_data['quantity_requested']
        if quantity <= 0:
            raise forms.ValidationError('يجب أن تكون الكمية أكبر من صفر')
        return quantity

class WorkOrderPartIssueForm(forms.ModelForm):
    """نموذج صرف قطع الغيار لأمر الشغل"""
    
    class Meta:
        model = WorkOrderPart
        fields = ['quantity_used', 'notes']
        widgets = {
            'quantity_used': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'placeholder': 'الكمية المصروفة'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'ملاحظات حول الصرف'
            }),
        }
        labels = {
            'quantity_used': 'الكمية المصروفة',
            'notes': 'ملاحظات',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # تنسيق الحقول
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
    
    def clean_quantity_used(self):
        quantity = self.cleaned_data['quantity_used']
        instance = self.instance
        
        if quantity <= 0:
            raise forms.ValidationError('يجب أن تكون الكمية أكبر من صفر')
        
        # التحقق من أن الكمية لا تتجاوز الكمية المطلوبة
        if instance and quantity > instance.quantity_requested:
            raise forms.ValidationError(f'الكمية المصروفة لا يمكن أن تتجاوز الكمية المطلوبة ({instance.quantity_requested})')
        
        # التحقق من توفر المخزون
        if instance and instance.spare_part:
            if quantity > instance.spare_part.current_stock:
                raise forms.ValidationError(f'المخزون المتاح غير كافي. المتاح: {instance.spare_part.current_stock}')
        
        return quantity