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
    """نموذج إنشاء وتعديل توقف الجهاز"""
    
    class Meta:
        model = DowntimeEvent
        fields = ['device', 'downtime_type', 'reason', 'start_time', 'end_time', 
                 'impact_description', 'cost_impact']
        widgets = {
            'device': forms.Select(attrs={'class': 'form-control select2', 'required': True}),
            'downtime_type': forms.Select(attrs={'class': 'form-control'}),
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'required': True}),
            'start_time': forms.DateTimeInput(attrs={'class': 'form-control flatpickr-datetime', 'required': True}),
            'end_time': forms.DateTimeInput(attrs={'class': 'form-control flatpickr-datetime'}),
            'impact_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'cost_impact': forms.NumberInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['impact_description'].required = False
        self.fields['cost_impact'].required = False
        self.fields['end_time'].required = False
