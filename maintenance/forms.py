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

        # لو في bed field - السماح بجميع الأسرة في البداية
        if 'bed' in self.fields:
            if self.data.get('room'):
                # إذا كان هناك room محدد في البيانات، فلتر الأسرة حسب الغرفة
                try:
                    room_id = int(self.data.get('room'))
                    self.fields["bed"].queryset = Bed.objects.filter(room_id=room_id)
                except (ValueError, TypeError):
                    self.fields["bed"].queryset = Bed.objects.all()
            elif self.instance and self.instance.pk and self.instance.room:
                # إذا كان هذا تعديل جهاز موجود، فلتر الأسرة حسب غرفة الجهاز الحالية
                self.fields["bed"].queryset = Bed.objects.filter(room=self.instance.room)
            else:
                # السماح بجميع الأسرة إذا لم يتم تحديد غرفة
                self.fields["bed"].queryset = Bed.objects.all()


class DeviceTransferForm(forms.ModelForm):
    class Meta:
        model = DeviceTransferRequest
        fields = ['to_department', 'to_room']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['to_department'].label = "القسم الجديد"
        self.fields['to_room'].label = "الغرفة الجديدة"
        
        # Add CSS classes
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})


class DeviceTransferRequestForm(forms.ModelForm):
    """Enhanced Device Transfer Request Form with validation"""
    
    class Meta:
        model = DeviceTransferRequest
        fields = [
            'to_department', 'to_room', 'to_bed', 'patient',
            'reason', 'reason_details', 'priority',
            'device_checked', 'device_cleaned', 'device_sterilized',
            'include_accessories'
        ]
        widgets = {
            'to_department': forms.Select(attrs={'class': 'form-control', 'required': True}),
            'to_room': forms.Select(attrs={'class': 'form-control'}),
            'to_bed': forms.Select(attrs={'class': 'form-control'}),
            'patient': forms.Select(attrs={'class': 'form-control'}),
            'reason': forms.Select(attrs={'class': 'form-control', 'required': True}),
            'reason_details': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'تفاصيل إضافية عن سبب النقل...'
            }),
            'priority': forms.Select(attrs={'class': 'form-control'}),
            'device_checked': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'device_cleaned': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'device_sterilized': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'include_accessories': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'to_department': 'القسم المستهدف',
            'to_room': 'الغرفة المستهدفة',
            'to_bed': 'السرير المستهدف',
            'patient': 'المريض',
            'reason': 'سبب النقل',
            'reason_details': 'تفاصيل السبب',
            'priority': 'الأولوية',
            'device_checked': 'تم فحص الجهاز',
            'device_cleaned': 'تم تنظيف الجهاز',
            'device_sterilized': 'تم تعقيم الجهاز',
            'include_accessories': 'نقل الإكسسوارات مع الجهاز',
        }
    
    def __init__(self, *args, **kwargs):
        self.device = kwargs.pop('device', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Dynamic filtering for rooms based on department
        if 'to_department' in self.data:
            try:
                department_id = int(self.data.get('to_department'))
                self.fields['to_room'].queryset = Room.objects.filter(department_id=department_id)
                
                # Filter beds based on room
                if 'to_room' in self.data:
                    room_id = int(self.data.get('to_room'))
                    self.fields['to_bed'].queryset = Bed.objects.filter(room_id=room_id, status='available')
            except (ValueError, TypeError):
                self.fields['to_room'].queryset = Room.objects.none()
                self.fields['to_bed'].queryset = Bed.objects.none()
        else:
            self.fields['to_room'].queryset = Room.objects.none()
            self.fields['to_bed'].queryset = Bed.objects.none()
        
        # Filter active patients only
        from manager.models import Patient
        self.fields['patient'].queryset = Patient.objects.all().order_by('first_name', 'last_name')
        self.fields['patient'].required = False
        
        # Make bed optional
        self.fields['to_bed'].required = False
        
        # Set initial values if editing
        if self.instance.pk:
            if self.instance.to_department:
                self.fields['to_room'].queryset = Room.objects.filter(
                    department=self.instance.to_department
                )
            if self.instance.to_room:
                self.fields['to_bed'].queryset = Bed.objects.filter(
                    room=self.instance.to_room
                )
    
    def clean(self):
        """Validate transfer request data"""
        cleaned_data = super().clean()
        to_department = cleaned_data.get('to_department')
        reason = cleaned_data.get('reason')
        patient = cleaned_data.get('patient')
        to_bed = cleaned_data.get('to_bed')
        
        # Check if device is provided
        if self.device:
            # Check device eligibility
            temp_request = DeviceTransferRequest(device=self.device)
            errors = temp_request.check_device_eligibility()
            if errors and not self.cleaned_data.get('device_checked'):
                raise forms.ValidationError(
                    'يجب معالجة المشاكل التالية قبل النقل: ' + ', '.join(errors)
                )
            
            # Prevent transfer to same department
            if to_department and self.device.department == to_department:
                raise forms.ValidationError('لا يمكن نقل الجهاز إلى نفس القسم الحالي')
        
        # If patient is selected, bed should also be selected
        if patient and not to_bed:
            raise forms.ValidationError('يجب تحديد السرير عند نقل الجهاز لمريض محدد')
        
        # If reason is 'other', details must be provided
        if reason == 'other' and not cleaned_data.get('reason_details'):
            raise forms.ValidationError('يجب توضيح السبب عند اختيار "أخرى"')
        
        return cleaned_data


class TransferApprovalForm(forms.Form):
    """Form for approving transfer request"""
    approval_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'ملاحظات الموافقة (اختياري)'
        }),
        label='ملاحظات الموافقة'
    )


class TransferPickupForm(forms.Form):
    """Form for picking up transfer request"""
    pickup_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'ملاحظات الاستلام (اختياري)'
        }),
        label='ملاحظات الاستلام'
    )


class TransferAcceptanceForm(forms.Form):
    """Form for accepting transfer request"""
    acceptance_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'ملاحظات القبول النهائي (اختياري)'
        }),
        label='ملاحظات القبول النهائي'
    )


class TransferRejectionForm(forms.Form):
    """Form for rejecting transfer request"""
    rejection_reason = forms.CharField(
        required=True,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'سبب الرفض (مطلوب)'
        }),
        label='سبب الرفض'
    )


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


class AccessoryTransferForm(forms.Form):
    """نموذج طلب نقل ملحق"""
    to_department = forms.ModelChoiceField(
        queryset=None,
        label="القسم المستهدف",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    to_room = forms.ModelChoiceField(
        queryset=None,
        label="الغرفة المستهدفة",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    to_device = forms.ModelChoiceField(
        queryset=None,
        label="الجهاز المستهدف",
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    reason = forms.CharField(
        label="سبب النقل",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'اذكر سبب طلب نقل الملحق...'
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from manager.models import Department, Room
        from .models import Device
        
        self.fields['to_department'].queryset = Department.objects.all()
        self.fields['to_room'].queryset = Room.objects.all()
        self.fields['to_device'].queryset = Device.objects.all()
        
        # إذا كان هناك بيانات مرسلة (POST)
        if self.data:
            try:
                department_id = int(self.data.get('to_department'))
                self.fields['to_room'].queryset = Room.objects.filter(department_id=department_id)
                
                room_id = self.data.get('to_room')
                if room_id:
                    room_id = int(room_id)
                    self.fields['to_device'].queryset = Device.objects.filter(room_id=room_id)
            except (ValueError, TypeError):
                pass


class DowntimeForm(forms.ModelForm):
    """نموذج إدارة توقفات الأجهزة"""
    
    class Meta:
        model = DeviceDowntime
        fields = [
            'device', 'start_time', 'end_time', 'reason', 
            'description', 'work_order'
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
            'reason': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'وصف التوقف'
            }),
            'work_order': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'device': 'الجهاز',
            'start_time': 'وقت بداية التوقف',
            'end_time': 'وقت نهاية التوقف',
            'reason': 'سبب التوقف',
            'description': 'وصف التوقف',
            'work_order': 'أمر الشغل المرتبط',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # فلترة أوامر الشغل حسب الجهاز المحدد
        if 'initial' in kwargs and 'device' in kwargs['initial']:
            device = kwargs['initial']['device']
            self.fields['work_order'].queryset = WorkOrder.objects.filter(
                service_request__device=device
            )
        else:
            self.fields['work_order'].queryset = WorkOrder.objects.none()

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


class SparePartTransactionForm(forms.ModelForm):
    """نموذج معاملات قطع الغيار"""
    
    class Meta:
        model = SparePartTransaction
        fields = ['transaction_type', 'quantity', 'reference_number', 'notes', 'work_order', 'device']
        widgets = {
            'transaction_type': forms.Select(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'الكمية',
                'min': '1'
            }),
            'reference_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'رقم المرجع'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'ملاحظات'
            }),
            'work_order': forms.Select(attrs={'class': 'form-control'}),
            'device': forms.Select(attrs={'class': 'form-control'}),
        }

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


class SparePartRequestForm(forms.ModelForm):
    """نموذج طلب قطعة غيار"""
    
    class Meta:
        model = SparePartRequest
        fields = ['spare_part', 'quantity_requested', 'priority', 'work_order', 'device', 'reason', 'notes']
        widgets = {
            'spare_part': forms.Select(attrs={'class': 'form-control'}),
            'quantity_requested': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'placeholder': 'الكمية المطلوبة'
            }),
            'priority': forms.Select(attrs={'class': 'form-control'}),
            'work_order': forms.Select(attrs={'class': 'form-control'}),
            'device': forms.Select(attrs={'class': 'form-control'}),
            'reason': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'اذكر سبب الطلب'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'ملاحظات إضافية (اختياري)'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        work_order = kwargs.pop('work_order', None)
        device = kwargs.pop('device', None)
        super().__init__(*args, **kwargs)
        
        # تحديد قطع الغيار المتاحة فقط
        self.fields['spare_part'].queryset = SparePart.objects.filter(
            status='available'
        ).order_by('name')
        
        # تحديد أوامر العمل المفتوحة فقط
        self.fields['work_order'].queryset = WorkOrder.objects.filter(
            status__in=['open', 'in_progress']
        ).order_by('-created_at')
        self.fields['work_order'].required = False
        
        # تحديد الأجهزة المتاحة
        self.fields['device'].queryset = Device.objects.filter(
            status='active'
        ).order_by('name')
        self.fields['device'].required = False
        
        # تحديد القيم الافتراضية
        if work_order:
            self.fields['work_order'].initial = work_order
            if work_order.service_request.device:
                self.fields['device'].initial = work_order.service_request.device
        
        if device:
            self.fields['device'].initial = device
    
    def clean(self):
        cleaned_data = super().clean()
        spare_part = cleaned_data.get('spare_part')
        quantity_requested = cleaned_data.get('quantity_requested')
        
        if spare_part and quantity_requested:
            # التحقق من توفر المخزون
            if quantity_requested > spare_part.current_stock:
                raise forms.ValidationError(
                    f'الكمية المطلوبة ({quantity_requested}) أكبر من المخزون المتاح ({spare_part.current_stock})'
                )
        
        return cleaned_data


class RequestApprovalForm(forms.Form):
    """نموذج الموافقة على طلب قطعة غيار"""
    
    quantity_approved = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'الكمية المعتمدة'
        }),
        label='الكمية المعتمدة'
    )
    
    approval_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'ملاحظات الموافقة (اختياري)'
        }),
        label='ملاحظات الموافقة'
    )
    
    def __init__(self, *args, **kwargs):
        self.spare_request = kwargs.pop('spare_request', None)
        super().__init__(*args, **kwargs)
        
        if self.spare_request:
            # تحديد الكمية الافتراضية
            self.fields['quantity_approved'].initial = self.spare_request.quantity_requested
            
            # تحديد الحد الأقصى للكمية
            max_quantity = min(
                self.spare_request.quantity_requested,
                self.spare_request.spare_part.current_stock
            )
            self.fields['quantity_approved'].widget.attrs['max'] = max_quantity
            self.fields['quantity_approved'].help_text = f'الحد الأقصى: {max_quantity}'
    
    def clean_quantity_approved(self):
        quantity_approved = self.cleaned_data['quantity_approved']
        
        if self.spare_request:
            # التحقق من عدم تجاوز الكمية المطلوبة
            if quantity_approved > self.spare_request.quantity_requested:
                raise forms.ValidationError(
                    f'الكمية المعتمدة لا يمكن أن تتجاوز الكمية المطلوبة ({self.spare_request.quantity_requested})'
                )
            
            # التحقق من توفر المخزون
            if quantity_approved > self.spare_request.spare_part.current_stock:
                raise forms.ValidationError(
                    f'الكمية المعتمدة تتجاوز المخزون المتاح ({self.spare_request.spare_part.current_stock})'
                )
        
        return quantity_approved


class SupplierForm(forms.ModelForm):
    """نموذج إدارة الموردين"""
    
    class Meta:
        model = Supplier
        fields = ['name', 'contact_person', 'email', 'phone', 'address', 'notes']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'اسم المورد'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'الشخص المسؤول'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'البريد الإلكتروني'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'رقم الهاتف'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'العنوان'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'ملاحظات إضافية'}),
        }


class SparePartForm(forms.ModelForm):
    """نموذج إدارة قطع الغيار"""
    
    class Meta:
        model = SparePart
        fields = [
            'name', 'part_number', 'description', 'device_category', 'manufacturer', 
            'model_number', 'unit', 'current_stock', 'minimum_stock', 'maximum_stock', 
            'unit_cost', 'primary_supplier', 'storage_location', 'status', 'is_critical'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'اسم قطعة الغيار'}),
            'part_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'الرقم التسلسلي'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'وصف قطعة الغيار'}),
            'device_category': forms.Select(attrs={'class': 'form-control'}),
            'manufacturer': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'الشركة المصنعة'}),
            'model_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'رقم الموديل'}),
            'unit': forms.Select(attrs={'class': 'form-control'}),
            'current_stock': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'minimum_stock': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'maximum_stock': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'unit_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'primary_supplier': forms.Select(attrs={'class': 'form-control'}),
            'storage_location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'موقع التخزين'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'is_critical': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        minimum_stock = cleaned_data.get('minimum_stock')
        maximum_stock = cleaned_data.get('maximum_stock')
        current_stock = cleaned_data.get('current_stock')
        
        if minimum_stock and maximum_stock and minimum_stock > maximum_stock:
            raise forms.ValidationError('الحد الأدنى للمخزون لا يمكن أن يكون أكبر من الحد الأقصى')
        
        if current_stock and maximum_stock and current_stock > maximum_stock:
            raise forms.ValidationError('المخزون الحالي لا يمكن أن يتجاوز الحد الأقصى')
        
        return cleaned_data


class PreventiveMaintenanceScheduleForm(forms.ModelForm):
    """نموذج جدولة الصيانة الوقائية والمعايرة"""
    
    class Meta:
        model = PreventiveMaintenanceSchedule
        fields = [
            'name', 'description', 'job_plan', 'frequency',
            'start_date', 'end_date', 'assigned_to', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'اسم الجدولة (مثل: صيانة وقائية شهرية)',
                'required': True
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'وصف تفصيلي للصيانة المطلوبة'
            }),
            'job_plan': forms.Select(attrs={
                'class': 'form-control',
                'required': True
            }),
            'frequency': forms.Select(attrs={
                'class': 'form-control',
                'required': True
            }),
            'start_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'required': True
            }),
            'end_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'assigned_to': forms.Select(attrs={
                'class': 'form-control'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
        labels = {
            'name': 'اسم الجدولة',
            'description': 'الوصف',
            'job_plan': 'خطة العمل',
            'frequency': 'التكرار',
            'start_date': 'تاريخ البدء',
            'end_date': 'تاريخ الانتهاء',
            'assigned_to': 'مُعين إلى',
            'is_active': 'نشط'
        }

    def __init__(self, *args, **kwargs):
        device = kwargs.pop('device', None)
        super().__init__(*args, **kwargs)
        
        # فلترة خطط العمل النشطة فقط
        self.fields['job_plan'].queryset = JobPlan.objects.filter(is_active=True)
        
        # فلترة المستخدمين (الفنيين فقط)
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.fields['assigned_to'].queryset = User.objects.filter(is_active=True)
        
        # إضافة خيار فارغ
        self.fields['assigned_to'].empty_label = "اختر الفني المسؤول"
        self.fields['job_plan'].empty_label = "اختر خطة العمل"

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        # التحقق من صحة التواريخ
        if start_date and end_date and start_date >= end_date:
            raise forms.ValidationError("تاريخ الانتهاء يجب أن يكون بعد تاريخ البدء")
        
        return cleaned_data


class CalibrationRecordForm(forms.ModelForm):
    """نموذج إضافة سجل معايرة جديد"""
    
    class Meta:
        model = CalibrationRecord
        fields = [
            'calibration_date', 'calibration_interval_months',
            'calibrated_by', 'certificate_number', 'calibration_agency', 
            'status', 'notes', 'certificate_file'
        ]
        widgets = {
            'calibration_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'required': True
            }),
            'calibration_interval_months': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '60',
                'value': '12'
            }),
            'calibrated_by': forms.Select(attrs={
                'class': 'form-control'
            }),
            'certificate_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'رقم شهادة المعايرة'
            }),
            'calibration_agency': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'اسم جهة المعايرة'
            }),
            'status': forms.Select(attrs={
                'class': 'form-control'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'ملاحظات إضافية'
            }),
            'certificate_file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.jpg,.jpeg,.png'
            })
        }
        labels = {
            'calibration_date': 'تاريخ المعايرة',
            'calibration_interval_months': 'فترة المعايرة (بالشهور)',
            'calibrated_by': 'تم المعايرة بواسطة',
            'certificate_number': 'رقم الشهادة',
            'calibration_agency': 'جهة المعايرة',
            'status': 'حالة المعايرة',
            'notes': 'ملاحظات',
            'certificate_file': 'ملف الشهادة'
        }

    def __init__(self, *args, **kwargs):
        device = kwargs.pop('device', None)
        super().__init__(*args, **kwargs)
        
        # فلترة المستخدمين النشطين
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.fields['calibrated_by'].queryset = User.objects.filter(is_active=True)
        self.fields['calibrated_by'].empty_label = "اختر الفني المسؤول"

    def clean(self):
        cleaned_data = super().clean()
        return cleaned_data


class OperationDefinitionForm(forms.ModelForm):
    """نموذج إدارة تعريفات العمليات"""
    
    class Meta:
        model = OperationDefinition
        fields = [
            'name', 'code', 'description', 'auto_execute', 'requires_confirmation', 
            'session_timeout_minutes', 'allow_multiple_executions',
            'log_to_usage', 'log_to_transfer', 'log_to_handover', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'اسم العملية',
                'required': True
            }),
            'code': forms.Select(attrs={
                'class': 'form-control',
                'required': True
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'وصف العملية'
            }),
            'auto_execute': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'requires_confirmation': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'session_timeout_minutes': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '60',
                'value': '10'
            }),
            'allow_multiple_executions': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'log_to_usage': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'log_to_transfer': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'log_to_handover': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
        labels = {
            'name': _('Operation Name'),
            'code': _('Operation Code'),
            'description': _('Description'),
            'auto_execute': _('Auto Execute'),
            'requires_confirmation': _('Requires Confirmation'),
            'session_timeout_minutes': _('Session Timeout (minutes)'),
            'allow_multiple_executions': _('Allow Multiple Executions'),
            'log_to_usage': _('Log to Usage'),
            'log_to_transfer': _('Log to Transfer'),
            'log_to_handover': _('Log to Handover'),
            'is_active': _('Active'),
        }
    
    def clean(self):
        """التحقق من صحة البيانات"""
        cleaned_data = super().clean()
        auto_execute = cleaned_data.get('auto_execute')
        requires_confirmation = cleaned_data.get('requires_confirmation')
        
        # التحقق من عدم تعارض الإعدادات
        if auto_execute and requires_confirmation:
            raise forms.ValidationError(
                _('An operation cannot be both auto-execute and require confirmation')
            )
        
        return cleaned_data
