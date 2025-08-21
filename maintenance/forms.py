from django import forms
from .models import Company, Device, DeviceCategory, DeviceSubCategory, DeviceType, DeviceUsage , current_patient
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
    department = forms.ModelChoiceField(queryset=Department.objects.all(), required=True, label="New Department")
    room = forms.ModelChoiceField(queryset=Room.objects.all(), required=True, label="New Room")

class DeviceFormDetailed(forms.ModelForm):
    class Meta:
        model = Device
        fields = [
            'technical_specifications', 'classification', 'uses', 'complications_risks',
            'half_life',
            # ... أضف باقي الحقول الاختيارية هنا
        ]
        
class DeviceTransferForm(forms.ModelForm):
    class Meta:
        model = Device
        fields = ['department', 'room']     



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

