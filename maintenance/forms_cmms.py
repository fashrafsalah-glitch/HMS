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
        # دي محتاجة تتعدل حسب نظام الصلاحيات في المشروع
        # حاليًا بنفترض إن فيه جروب اسمه 'Technician' للفنيين
        technicians = User.objects.filter(groups__name='Technician')
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
        fields = ['name', 'description', 'job_type', 'estimated_hours', 'device_category']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'instructions': forms.Textarea(attrs={'rows': 4}),
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
        fields = ['name', 'description', 'device', 'job_plan', 'frequency', 'interval_days', 'start_date', 'end_date']
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
        technicians = User.objects.filter(groups__name='Technician')
        self.fields['assignee'].queryset = technicians
        
        # إخفاء حقول معينة حسب التكرار المختار
        instance = kwargs.get('instance')
        if instance:
            if instance.frequency != 'weekly':
                self.fields['day_of_week'].widget = forms.HiddenInput()
            if instance.frequency != 'monthly':
                self.fields['day_of_month'].widget = forms.HiddenInput()