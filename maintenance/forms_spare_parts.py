from django import forms
from .models import Supplier, SparePart, DeviceCategory

class SupplierForm(forms.ModelForm):
    """نموذج إدارة الموردين"""
    
    class Meta:
        model = Supplier
        fields = [
            'name', 'code', 'contact_person', 'phone', 'email', 
            'website', 'address', 'city', 'country', 'postal_code',
            'tax_number', 'commercial_register', 'status', 'rating',
            'payment_terms', 'credit_limit', 'notes'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'اسم المورد'}),
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'كود المورد'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'الشخص المسؤول'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'رقم الهاتف'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'البريد الإلكتروني'}),
            'website': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'الموقع الإلكتروني'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'العنوان'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'المدينة'}),
            'country': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'البلد'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'الرمز البريدي'}),
            'tax_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'الرقم الضريبي'}),
            'commercial_register': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'السجل التجاري'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'rating': forms.Select(attrs={'class': 'form-control'}),
            'payment_terms': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'شروط الدفع'}),
            'credit_limit': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'حد الائتمان'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'ملاحظات'}),
        }
        labels = {
            'name': 'اسم المورد',
            'code': 'كود المورد',
            'contact_person': 'الشخص المسؤول',
            'phone': 'رقم الهاتف',
            'email': 'البريد الإلكتروني',
            'website': 'الموقع الإلكتروني',
            'address': 'العنوان',
            'city': 'المدينة',
            'country': 'البلد',
            'postal_code': 'الرمز البريدي',
            'tax_number': 'الرقم الضريبي',
            'commercial_register': 'السجل التجاري',
            'status': 'الحالة',
            'rating': 'التقييم',
            'payment_terms': 'شروط الدفع',
            'credit_limit': 'حد الائتمان',
            'notes': 'ملاحظات',
        }

    def clean_code(self):
        """التحقق من تفرد كود المورد"""
        code = self.cleaned_data['code']
        if Supplier.objects.filter(code=code).exclude(pk=self.instance.pk if self.instance else None).exists():
            raise forms.ValidationError('كود المورد موجود مسبقاً')
        return code

    def clean_email(self):
        """التحقق من صحة البريد الإلكتروني"""
        email = self.cleaned_data['email']
        if email and Supplier.objects.filter(email=email).exclude(pk=self.instance.pk if self.instance else None).exists():
            raise forms.ValidationError('البريد الإلكتروني موجود مسبقاً')
        return email


class SparePartForm(forms.ModelForm):
    """نموذج إدارة قطع الغيار"""
    
    class Meta:
        model = SparePart
        fields = [
            'name', 'part_number', 'description', 'device_category',
            'manufacturer', 'model_number', 'unit', 'current_stock',
            'minimum_stock', 'maximum_stock', 'reorder_point',
            'unit_cost', 'last_purchase_price', 'primary_supplier',
            'storage_location', 'shelf_life_months', 'status',
            'is_critical', 'is_consumable', 'image', 'datasheet'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'اسم قطعة الغيار'}),
            'part_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'رقم القطعة'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'وصف القطعة'}),
            'device_category': forms.Select(attrs={'class': 'form-control'}),
            'manufacturer': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'الشركة المصنعة'}),
            'model_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'رقم الموديل'}),
            'unit': forms.Select(attrs={'class': 'form-control'}),
            'current_stock': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'placeholder': 'المخزون الحالي'}),
            'minimum_stock': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'placeholder': 'الحد الأدنى للمخزون'}),
            'maximum_stock': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'placeholder': 'الحد الأقصى للمخزون'}),
            'reorder_point': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'placeholder': 'نقطة إعادة الطلب'}),
            'unit_cost': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': '0.01', 'placeholder': 'تكلفة الوحدة'}),
            'last_purchase_price': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': '0.01', 'placeholder': 'آخر سعر شراء'}),
            'primary_supplier': forms.Select(attrs={'class': 'form-control'}),
            'storage_location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'موقع التخزين'}),
            'shelf_life_months': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'placeholder': 'مدة الصلاحية (شهور)'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'is_critical': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_consumable': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'datasheet': forms.FileInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'name': 'اسم قطعة الغيار',
            'part_number': 'رقم القطعة',
            'description': 'الوصف',
            'device_category': 'فئة الجهاز',
            'manufacturer': 'الشركة المصنعة',
            'model_number': 'رقم الموديل',
            'unit': 'الوحدة',
            'current_stock': 'المخزون الحالي',
            'minimum_stock': 'الحد الأدنى للمخزون',
            'maximum_stock': 'الحد الأقصى للمخزون',
            'reorder_point': 'نقطة إعادة الطلب',
            'unit_cost': 'تكلفة الوحدة',
            'last_purchase_price': 'آخر سعر شراء',
            'primary_supplier': 'المورد الأساسي',
            'storage_location': 'موقع التخزين',
            'shelf_life_months': 'مدة الصلاحية (شهور)',
            'status': 'الحالة',
            'is_critical': 'حرج',
            'is_consumable': 'مستهلك',
            'image': 'الصورة',
            'datasheet': 'ورقة البيانات',
        }

    def clean_part_number(self):
        """التحقق من تفرد رقم القطعة"""
        part_number = self.cleaned_data['part_number']
        if SparePart.objects.filter(part_number=part_number).exclude(pk=self.instance.pk if self.instance else None).exists():
            raise forms.ValidationError('رقم القطعة موجود مسبقاً')
        return part_number

    def clean_stock_values(self):
        """التحقق من قيم المخزون"""
        current_stock = self.cleaned_data.get('current_stock', 0)
        minimum_stock = self.cleaned_data.get('minimum_stock', 0)
        maximum_stock = self.cleaned_data.get('maximum_stock')
        
        if minimum_stock > current_stock:
            raise forms.ValidationError('الحد الأدنى للمخزون لا يمكن أن يكون أكبر من المخزون الحالي')
        
        if maximum_stock and current_stock > maximum_stock:
            raise forms.ValidationError('المخزون الحالي لا يمكن أن يكون أكبر من الحد الأقصى')
        
        if maximum_stock and minimum_stock > maximum_stock:
            raise forms.ValidationError('الحد الأدنى لا يمكن أن يكون أكبر من الحد الأقصى')
        
        return current_stock, minimum_stock, maximum_stock

    def clean(self):
        """التحقق من صحة البيانات"""
        cleaned_data = super().clean()
        self.clean_stock_values()
        return cleaned_data


class SparePartSearchForm(forms.Form):
    """نموذج البحث في قطع الغيار"""
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'ابحث في اسم القطعة أو الرقم أو الوصف'
        }),
        label='البحث'
    )
    
    supplier = forms.ModelChoiceField(
        queryset=Supplier.objects.filter(status='active'),
        required=False,
        empty_label="كل الموردين",
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='المورد'
    )
    
    device_category = forms.ModelChoiceField(
        queryset=DeviceCategory.objects.all(),
        required=False,
        empty_label="كل الفئات",
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='فئة الجهاز'
    )
    
    status = forms.ChoiceField(
        choices=[
            ('', 'كل الحالات'),
            ('available', 'متوفر'),
            ('low_stock', 'مخزون منخفض'),
            ('out_of_stock', 'نفد المخزون'),
            ('discontinued', 'متوقف'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='الحالة'
    )
    
    low_stock = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='قطع الغيار منخفضة المخزون فقط'
    )
    
    sort_by = forms.ChoiceField(
        choices=[
            ('name', 'الاسم'),
            ('part_number', 'رقم القطعة'),
            ('current_stock', 'المخزون'),
            ('unit_cost', 'التكلفة'),
            ('primary_supplier__name', 'المورد'),
        ],
        initial='name',
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='ترتيب حسب'
    )


class SupplierSearchForm(forms.Form):
    """نموذج البحث في الموردين"""
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'ابحث في اسم المورد أو الكود أو الشخص المسؤول'
        }),
        label='البحث'
    )
    
    status = forms.ChoiceField(
        choices=[
            ('', 'كل الحالات'),
            ('active', 'نشط'),
            ('inactive', 'غير نشط'),
            ('suspended', 'معلق'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='الحالة'
    )
    
    rating = forms.ChoiceField(
        choices=[
            ('', 'كل التقييمات'),
            ('1', '1 نجمة'),
            ('2', '2 نجمة'),
            ('3', '3 نجمة'),
            ('4', '4 نجمة'),
            ('5', '5 نجمة'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='التقييم'
    )
    
    sort_by = forms.ChoiceField(
        choices=[
            ('name', 'الاسم'),
            ('code', 'الكود'),
            ('contact_person', 'الشخص المسؤول'),
            ('rating', 'التقييم'),
        ],
        initial='name',
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='ترتيب حسب'
    )