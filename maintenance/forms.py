from django import forms
from django.apps import apps
from .models import *
from django.utils.translation import gettext_lazy as _

class CompanyForm(forms.ModelForm):
    class Meta:
        model = apps.get_model("maintenance", "Company")
        fields = "__all__"


class DeviceFormBasic(forms.ModelForm):
    class Meta:
        model = Device
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # تحميل Lazy لموديل Company (بدل الاستيراد المباشر)
        Company = apps.get_model("maintenance", "Company")
        self.fields["manufacture_company"].queryset = Company.objects.all()

        # لو في bed field
        self.fields["bed"].queryset = Bed.objects.none()


class DeviceTransferForm(forms.ModelForm):
    class Meta:
        model = DeviceTransfer
        fields = "__all__"


class DeviceTypeForm(forms.ModelForm):
    class Meta:
        model = DeviceType
        fields = "__all__"


class DeviceUsageForm(forms.ModelForm):
    class Meta:
        model = DeviceUsageLog
        fields = "__all__"


class DeviceCategoryForm(forms.ModelForm):
    class Meta:
        model = DeviceCategory
        fields = "__all__"


class DeviceSubCategoryForm(forms.ModelForm):
    class Meta:
        model = DeviceSubCategory
        fields = "__all__"


class DeviceAccessoryForm(forms.ModelForm):
    class Meta:
        model = DeviceAccessory
        fields = "__all__"


class AccessoryScanForm(forms.Form):
    qr_code = forms.CharField(label="رمز QR", max_length=100)
    notes = forms.CharField(label="ملاحظات", widget=forms.Textarea, required=False)


class AccessoryTransactionForm(forms.ModelForm):
    class Meta:
        model = AccessoryTransaction
        fields = "__all__"


class AccessoryTransferForm(forms.ModelForm):
    class Meta:
        model = AccessoryTransferLog
        fields = "__all__"


class DowntimeForm(forms.ModelForm):
    """نموذج إدارة توقفات الأجهزة"""
    
    class Meta:
        model = DowntimeEvent
        fields = [
            'device', 'start_time', 'end_time', 'downtime_type',
            'reason', 'impact_description', 'related_work_order',
            'cost_impact'
        ]
        widgets = {
            'device': forms.Select(attrs={'class': 'form-control'}),
            'start_time': forms.DateTimeInput(
                attrs={
                    'class': 'form-control',
                    'type': 'datetime-local'
                }
            ),
            'end_time': forms.DateTimeInput(
                attrs={
                    'class': 'form-control',
                    'type': 'datetime-local'
                }
            ),
            'downtime_type': forms.Select(attrs={'class': 'form-control'}),
            'reason': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'سبب التوقف'
            }),
            'impact_description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'وصف التأثير'
            }),
            'related_work_order': forms.Select(attrs={'class': 'form-control'}),
            'cost_impact': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'step': '0.01',
                'placeholder': 'التأثير المالي'
            }),
        }
        labels = {
            'device': 'الجهاز',
            'start_time': 'وقت بداية التوقف',
            'end_time': 'وقت نهاية التوقف',
            'downtime_type': 'نوع التوقف',
            'reason': 'سبب التوقف',
            'impact_description': 'وصف التأثير',
            'related_work_order': 'أمر الشغل المرتبط',
            'cost_impact': 'التأثير المالي',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # فلترة أوامر الشغل حسب الجهاز المحدد
        if 'initial' in kwargs and 'device' in kwargs['initial']:
            device = kwargs['initial']['device']
            self.fields['related_work_order'].queryset = WorkOrder.objects.filter(
                service_request__device=device
            )
        else:
            self.fields['related_work_order'].queryset = WorkOrder.objects.none()

    def clean(self):
        """التحقق من صحة البيانات"""
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        
        if start_time and end_time and start_time >= end_time:
            raise forms.ValidationError('وقت بداية التوقف يجب أن يكون قبل وقت النهاية')
        
        return cleaned_data


class DowntimeSearchForm(forms.Form):
    """نموذج البحث في التوقفات"""
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'ابحث في اسم الجهاز أو سبب التوقف'
        }),
        label='البحث'
    )
    
    downtime_type = forms.ChoiceField(
        choices=[
            ('', 'كل الأنواع'),
            ('planned', 'مخطط'),
            ('unplanned', 'غير مخطط'),
            ('emergency', 'طوارئ'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='نوع التوقف'
    )
    
    period = forms.ChoiceField(
        choices=[
            ('', 'كل الفترات'),
            ('today', 'اليوم'),
            ('week', 'الأسبوع'),
            ('month', 'الشهر'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='الفترة الزمنية'
    )
    
    sort_by = forms.ChoiceField(
        choices=[
            ('device__name', 'اسم الجهاز'),
            ('start_time', 'وقت البدء'),
            ('-start_time', 'وقت البدء (تنازلي)'),
            ('downtime_type', 'نوع التوقف'),
        ],
        initial='-start_time',
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='ترتيب حسب'
    )


class CalibrationForm(forms.Form):
    """نموذج إدارة المعايرة (مؤقت)"""
    
    device = forms.ModelChoiceField(
        queryset=None,  # سيتم تحديده في __init__
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='الجهاز'
    )
    
    calibration_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label='تاريخ المعايرة'
    )
    
    next_calibration_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label='تاريخ المعايرة التالية'
    )
    
    certificate_number = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'رقم الشهادة'
        }),
        label='رقم الشهادة'
    )
    
    calibration_agency = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'جهة المعايرة'
        }),
        label='جهة المعايرة'
    )
    
    cost = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': 0,
            'step': '0.01',
            'placeholder': 'التكلفة'
        }),
        label='التكلفة'
    )
    
    notes = forms.CharField(
        max_length=500,
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'ملاحظات'
        }),
        label='ملاحظات'
    )

    def __init__(self, *args, **kwargs):
        from .models import Device
        super().__init__(*args, **kwargs)
        self.fields['device'].queryset = Device.objects.all()

    def clean(self):
        """التحقق من صحة البيانات"""
        cleaned_data = super().clean()
        calibration_date = cleaned_data.get('calibration_date')
        next_calibration_date = cleaned_data.get('next_calibration_date')
        
        if calibration_date and next_calibration_date and calibration_date >= next_calibration_date:
            raise forms.ValidationError('تاريخ المعايرة يجب أن يكون قبل تاريخ المعايرة التالية')
        
        return cleaned_data


class SparePartTransactionForm(forms.Form):
    """نموذج معاملات قطع الغيار (مؤقت)"""
    
    TRANSACTION_TYPES = [
        ('in', 'وارد'),
        ('out', 'صادر'),
        ('adjustment', 'تعديل'),
        ('return', 'إرجاع'),
    ]
    
    transaction_type = forms.ChoiceField(
        choices=TRANSACTION_TYPES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='نوع المعاملة'
    )
    
    quantity = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'الكمية'
        }),
        label='الكمية'
    )
    
    reference_number = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'رقم المرجع'
        }),
        label='رقم المرجع'
    )
    
    notes = forms.CharField(
        max_length=500,
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'ملاحظات'
        }),
        label='ملاحظات'
    )

    def __init__(self, *args, **kwargs):
        self.spare_part = kwargs.pop('spare_part', None)
        super().__init__(*args, **kwargs)
        
        if self.spare_part:
            # تحديث الكمية القصوى حسب المخزون المتاح
            if 'transaction_type' in self.data and self.data['transaction_type'] == 'out':
                max_quantity = self.spare_part.current_stock
                self.fields['quantity'].widget.attrs['max'] = max_quantity
                self.fields['quantity'].help_text = f'الكمية المتاحة: {max_quantity}'

    def clean(self):
        """التحقق من صحة البيانات"""
        cleaned_data = super().clean()
        transaction_type = cleaned_data.get('transaction_type')
        quantity = cleaned_data.get('quantity')
        
        if transaction_type == 'out' and self.spare_part:
            if quantity > self.spare_part.current_stock:
                raise forms.ValidationError(
                    f'الكمية المطلوبة ({quantity}) أكبر من المخزون المتاح ({self.spare_part.current_stock})'
                )
        
        return cleaned_data
