from django import forms
from .models import Supplier, SparePart

class SupplierForm(forms.ModelForm):
    """نموذج إنشاء وتعديل الموردين"""
    
    class Meta:
        model = Supplier
        fields = ['name', 'code', 'contact_person', 'phone', 'email', 'address', 'website', 'notes', 'status']
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'


class SparePartForm(forms.ModelForm):
    """نموذج إنشاء وتعديل قطع الغيار"""
    
    class Meta:
        model = SparePart
        fields = ['name', 'part_number', 'description', 'current_stock', 'minimum_stock', 
                 'unit', 'storage_location', 'unit_cost', 'primary_supplier', 
                 'compatible_devices', 'image', 'device_category']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'compatible_devices': forms.SelectMultiple(attrs={'class': 'select2'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
            if field_name == 'compatible_devices':
                field.widget.attrs['class'] = 'form-control select2'


# تم حذف النماذج التي تستخدم نماذج غير موجودة مؤقتاً
# سيتم إضافتها لاحقاً عند إنشاء النماذج المطلوبة