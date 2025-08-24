from django import forms
from .models import Company, Device, DeviceCategory, DeviceSubCategory, DeviceType, DeviceUsage, current_patient, DeviceAccessory, AccessoryTransaction, AccessoryTransferRequest, AccessoryTransferLog
# maintenance/forms.py
from django import forms
from manager.models import Department, Room , Bed
from django import forms
from .models import Device



class DeviceFormBasic(forms.ModelForm):
    class Meta:
        model = Device
        fields = [
            'name', 'category', 'subcategory',
            'brief_description', 'manufacturer', 'model', 'serial_number',
            'manufacture_company', 'supplier_company', 'maintenance_company', 'production_date',
            'device_classification', 'device_type', 'device_usage',
            'department', 'room', 'bed' 
        ]
        widgets = {
            'production_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super(DeviceFormBasic, self).__init__(*args, **kwargs)

        # تقيد الغرف حسب القسم المختار (إن وجد)
        if 'department' in self.data:
            try:
                department_id = int(self.data.get('department'))
                self.fields['room'].queryset = Room.objects.filter(department_id=department_id).order_by('name')
            except (ValueError, TypeError):
                self.fields['room'].queryset = Room.objects.none()
        elif self.instance.pk and self.instance.department:
            self.fields['room'].queryset = Room.objects.filter(department=self.instance.department).order_by('name')
        else:
            self.fields['room'].queryset = Room.objects.none()

        # تقيد الأسرة حسب الغرفة المختارة (إن وجدت)
        if 'room' in self.data:
            try:
                room_id = int(self.data.get('room'))
                self.fields['bed'].queryset = Bed.objects.filter(room_id=room_id).order_by('bed_number')
            except (ValueError, TypeError):
                self.fields['bed'].queryset = Bed.objects.none()
        elif self.instance.pk and self.instance.room:
            self.fields['bed'].queryset = Bed.objects.filter(room=self.instance.room).order_by('bed_number')
        else:
            self.fields['bed'].queryset = Bed.objects.none()

class DeviceFormBasic(forms.ModelForm):
    class Meta:
        model = Device
        fields = [
            'name', 'category', 'subcategory',
            'brief_description', 'manufacturer', 'model', 'serial_number',
            'manufacture_company', 'supplier_company', 'maintenance_company', 'production_date',
            'device_classification', 'device_type', 'device_usage',
            'department', 'room', 'bed'  ,'status', 'availability', 'clean_status', 'sterilization_status'
        ]
        widgets = {
            'production_date': forms.DateInput(attrs={'type': 'date'}),
            'room': forms.Select(),  # ← بدون hx-get
            'bed': forms.Select(),   # ← بدون hx-get
        }
       



class DeviceTransferForm(forms.Form):
    department = forms.ModelChoiceField(
        queryset=Department.objects.all(), 
        required=True, 
        label="القسم الجديد",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    room = forms.ModelChoiceField(
        queryset=Room.objects.none(), 
        required=False, 
        label="الغرفة الجديدة",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    reason = forms.CharField(
        max_length=500,
        required=False,
        label="سبب النقل",
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # تقيد الغرف حسب القسم المختار
        if 'department' in self.data:
            try:
                department_id = int(self.data.get('department'))
                self.fields['room'].queryset = Room.objects.filter(department_id=department_id).order_by('name')
            except (ValueError, TypeError):
                self.fields['room'].queryset = Room.objects.none()

class DeviceFormDetailed(forms.ModelForm):
    class Meta:
        model = Device
        fields = [
            'technical_specifications', 'classification', 'uses', 'complications_risks',
            'half_life',
            # ... أضف باقي الحقول الاختيارية هنا
        ]     



class DeviceCategoryForm(forms.ModelForm):
    class Meta:
        model = DeviceCategory
        fields = ['name']

class DeviceSubCategoryForm(forms.ModelForm):
    class Meta:
        model = DeviceSubCategory
        fields = ['category', 'name']        

class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = ['name']

class DeviceTypeForm(forms.ModelForm):
    class Meta:
        model = DeviceType
        fields = ['name']

class DeviceUsageForm(forms.ModelForm):
    class Meta:
        model = DeviceUsage
        fields = ['name']

class DeviceForm(forms.ModelForm):
    class Meta:
        model = Device
        fields = [
            'name', 'serial_number', 'model', 'device_type',
            'device_usage', 'status', 'clean_status', 'sterilization_status',
            'current_patient'  # تأكد من وجود هذا الحقل
        ]
        labels = {
            'status': 'حالة الجهاز',
            'clean_status': 'حالة النظافة',
            'sterilization_status': 'حالة التعقيم',
            'current_patient': 'المريض المستخدم حاليًا',
        }


class DeviceAccessoryForm(forms.ModelForm):
    class Meta:
        model = DeviceAccessory
        fields = ['name', 'description', 'serial_number', 'model', 'manufacturer', 
                 'purchase_date', 'warranty_expiry', 'status']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'purchase_date': forms.DateInput(attrs={'type': 'date'}),
            'warranty_expiry': forms.DateInput(attrs={'type': 'date'}),
        }
        labels = {
            'name': 'اسم الملحق',
            'description': 'الوصف',
            'serial_number': 'الرقم التسلسلي',
            'model': 'الموديل',
            'manufacturer': 'الشركة المصنعة',
            'purchase_date': 'تاريخ الشراء',
            'warranty_expiry': 'انتهاء الضمان',
            'status': 'الحالة',
        }


class AccessoryTransactionForm(forms.ModelForm):
    class Meta:
        model = AccessoryTransaction
        fields = ['transaction_type', 'from_user', 'to_user', 'from_department', 
                 'to_department', 'notes', 'scanned_barcode']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
        labels = {
            'transaction_type': 'نوع العملية',
            'from_user': 'من المستخدم',
            'to_user': 'إلى المستخدم',
            'from_department': 'من القسم',
            'to_department': 'إلى القسم',
            'notes': 'ملاحظات',
            'scanned_barcode': 'الباركود الممسوح',
        }


class AccessoryScanForm(forms.Form):
    barcode = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'placeholder': 'امسح الباركود أو أدخله يدوياً',
            'autofocus': True,
            'class': 'form-control'
        }),
        label='باركود الملحق'
    )
    transaction_type = forms.ChoiceField(
        choices=AccessoryTransaction.TRANSACTION_TYPES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='نوع العملية'
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        label='ملاحظات'
    )


class AccessoryTransferForm(forms.ModelForm):
    """Form for requesting accessory transfers between devices/departments"""
    
    class Meta:
        model = AccessoryTransferRequest
        fields = ['to_device', 'to_department', 'to_room', 'reason']
        widgets = {
            'reason': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'to_device': forms.Select(attrs={'class': 'form-control'}),
            'to_department': forms.Select(attrs={'class': 'form-control'}),
            'to_room': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'to_device': 'نقل إلى جهاز',
            'to_department': 'نقل إلى قسم',
            'to_room': 'نقل إلى غرفة',
            'reason': 'سبب النقل',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Make device field optional for department/room transfers
        self.fields['to_device'].required = False
        self.fields['to_department'].required = False
        self.fields['to_room'].required = False
        
        # Filter rooms based on selected department
        if 'to_department' in self.data:
            try:
                department_id = int(self.data.get('to_department'))
                self.fields['to_room'].queryset = Room.objects.filter(department_id=department_id).order_by('name')
            except (ValueError, TypeError):
                self.fields['to_room'].queryset = Room.objects.none()
        else:
            self.fields['to_room'].queryset = Room.objects.none()
    
    def clean(self):
        cleaned_data = super().clean()
        to_device = cleaned_data.get('to_device')
        to_department = cleaned_data.get('to_department')
        
        # Must specify either device or department
        if not to_device and not to_department:
            raise forms.ValidationError('يجب تحديد الجهاز المستهدف أو القسم المستهدف على الأقل')
        
        return cleaned_data

