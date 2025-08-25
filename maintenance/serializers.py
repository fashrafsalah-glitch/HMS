# هنا بنعمل الـ Serializers للـ API عشان نقدر نتعامل مع البيانات بصيغة JSON
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Device, DeviceCategory, DeviceSubCategory, DeviceAccessory
from .models import (
    ServiceRequest, WorkOrder, SLADefinition, JobPlan, 
    PreventiveMaintenanceSchedule, SparePart, Supplier
)
from manager.models import Department, Room

class UserSerializer(serializers.ModelSerializer):
    """
    سيريالايزر للمستخدمين
    هنا بنعرض بيانات المستخدم الأساسية بس
    """
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'full_name', 'email']
        
    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or obj.username

class DepartmentSerializer(serializers.ModelSerializer):
    """
    سيريالايزر للأقسام
    """
    class Meta:
        model = Department
        fields = ['id', 'name', 'description']

class DeviceCategorySerializer(serializers.ModelSerializer):
    """
    سيريالايزر لفئات الأجهزة
    """
    class Meta:
        model = DeviceCategory
        fields = ['id', 'name', 'description']

class DeviceSubCategorySerializer(serializers.ModelSerializer):
    """
    سيريالايزر للفئات الفرعية للأجهزة
    """
    category = DeviceCategorySerializer(read_only=True)
    
    class Meta:
        model = DeviceSubCategory
        fields = ['id', 'name', 'description', 'category']

class DeviceSerializer(serializers.ModelSerializer):
    """
    سيريالايزر للأجهزة
    هنا بنعرض كل تفاصيل الجهاز مع العلاقات
    """
    category = DeviceCategorySerializer(read_only=True)
    subcategory = DeviceSubCategorySerializer(read_only=True)
    department = DepartmentSerializer(read_only=True)
    room = serializers.StringRelatedField(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    clean_status_display = serializers.CharField(source='get_clean_status_display', read_only=True)
    sterilization_status_display = serializers.CharField(source='get_sterilization_status_display', read_only=True)
    
    class Meta:
        model = Device
        fields = [
            'id', 'name', 'serial_number', 'model', 'manufacturer',
            'category', 'subcategory', 'department', 'room',
            'status', 'status_display', 'clean_status', 'clean_status_display',
            'sterilization_status', 'sterilization_status_display',
            'purchase_date', 'warranty_expiry', 'last_maintained_at',
            'last_cleaned_at', 'last_sterilized_at', 'notes',
            'qr_token', 'qr_code'
        ]

class DeviceAccessorySerializer(serializers.ModelSerializer):
    """
    سيريالايزر لملحقات الأجهزة
    """
    device = DeviceSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = DeviceAccessory
        fields = [
            'id', 'name', 'serial_number', 'model', 'device',
            'status', 'status_display', 'purchase_date', 'warranty_expiry',
            'notes', 'qr_token', 'qr_code'
        ]

class SupplierSerializer(serializers.ModelSerializer):
    """
    سيريالايزر للموردين
    """
    class Meta:
        model = Supplier
        fields = [
            'id', 'name', 'contact_person', 'email', 'phone',
            'website', 'address', 'notes', 'created_at'
        ]

class SparePartSerializer(serializers.ModelSerializer):
    """
    سيريالايزر لقطع الغيار
    """
    supplier = SupplierSerializer(read_only=True)
    compatible_devices = DeviceSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = SparePart
        fields = [
            'id', 'name', 'part_number', 'supplier', 'cost', 'quantity',
            'unit', 'minimum_stock', 'location', 'lead_time_days',
            'status', 'status_display', 'notes', 'datasheet_url',
            'image', 'compatible_devices', 'created_at', 'updated_at'
        ]

class SparePartTransactionSerializer(serializers.ModelSerializer):
    """
    سيريالايزر لمعاملات قطع الغيار
    """
    spare_part = SparePartSerializer(read_only=True)
    user = UserSerializer(read_only=True)
    device = DeviceSerializer(read_only=True)
    transaction_type_display = serializers.CharField(source='get_transaction_type_display', read_only=True)
    
    class Meta:
        model = SparePartTransaction
        fields = [
            'id', 'spare_part', 'transaction_type', 'transaction_type_display',
            'quantity', 'date', 'reference_number', 'work_order',
            'device', 'user', 'notes', 'created_at'
        ]

class SLASerializer(serializers.ModelSerializer):
    """
    سيريالايزر لاتفاقيات مستوى الخدمة
    """
    class Meta:
        model = SLA
        fields = [
            'id', 'name', 'description', 'response_time_hours',
            'resolution_time_hours', 'is_active', 'created_at'
        ]

class ServiceRequestSerializer(serializers.ModelSerializer):
    """
    سيريالايزر لطلبات الخدمة
    """
    device = DeviceSerializer(read_only=True)
    requested_by = UserSerializer(read_only=True)
    assigned_to = UserSerializer(read_only=True)
    sla = SLASerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    request_type_display = serializers.CharField(source='get_request_type_display', read_only=True)
    
    class Meta:
        model = ServiceRequest
        fields = [
            'id', 'title', 'description', 'device', 'requested_by',
            'assigned_to', 'status', 'status_display', 'priority',
            'priority_display', 'request_type', 'request_type_display',
            'sla', 'response_due', 'resolution_due', 'is_auto_generated',
            'created_at', 'updated_at'
        ]

class WorkOrderSparePartUsageSerializer(serializers.ModelSerializer):
    """
    سيريالايزر لاستخدام قطع الغيار في أوامر الشغل
    """
    spare_part = SparePartSerializer(read_only=True)
    
    class Meta:
        model = WorkOrderSparePartUsage
        fields = ['id', 'spare_part', 'quantity_used', 'cost_per_unit', 'total_cost']

class WorkOrderSerializer(serializers.ModelSerializer):
    """
    سيريالايزر لأوامر الشغل
    """
    service_request = ServiceRequestSerializer(read_only=True)
    assigned_technician = UserSerializer(read_only=True)
    supervisor = UserSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    spare_parts_used = WorkOrderSparePartUsageSerializer(many=True, read_only=True)
    total_cost = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = WorkOrder
        fields = [
            'id', 'service_request', 'assigned_technician', 'supervisor',
            'status', 'status_display', 'start_time', 'end_time',
            'work_performed', 'findings', 'recommendations',
            'labor_hours', 'labor_cost', 'total_cost', 'spare_parts_used',
            'created_at', 'updated_at'
        ]

class JobPlanSerializer(serializers.ModelSerializer):
    """
    سيريالايزر لخطط العمل
    """
    created_by = UserSerializer(read_only=True)
    
    class Meta:
        model = JobPlan
        fields = [
            'id', 'name', 'description', 'instructions', 'estimated_duration',
            'required_skills', 'safety_notes', 'tools_required',
            'is_active', 'created_by', 'created_at', 'updated_at'
        ]

class PreventiveMaintenanceScheduleSerializer(serializers.ModelSerializer):
    """
    سيريالايزر لجداول الصيانة الوقائية
    """
    device = DeviceSerializer(read_only=True)
    job_plan = JobPlanSerializer(read_only=True)
    assigned_technician = UserSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    frequency_display = serializers.CharField(source='get_frequency_display', read_only=True)
    
    class Meta:
        model = PreventiveMaintenanceSchedule
        fields = [
            'id', 'device', 'job_plan', 'assigned_technician',
            'frequency', 'frequency_display', 'frequency_value',
            'next_due_date', 'last_completed_date', 'status',
            'status_display', 'notes', 'created_at', 'updated_at'
        ]

class CalibrationSerializer(serializers.ModelSerializer):
    """
    سيريالايزر للمعايرة
    """
    device = DeviceSerializer(read_only=True)
    performed_by = UserSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Calibration
        fields = [
            'id', 'device', 'calibration_date', 'next_calibration_date',
            'performed_by', 'calibration_standard', 'results',
            'status', 'status_display', 'certificate_number',
            'notes', 'created_at'
        ]

class DowntimeSerializer(serializers.ModelSerializer):
    """
    سيريالايزر لأوقات التوقف
    """
    device = DeviceSerializer(read_only=True)
    reported_by = UserSerializer(read_only=True)
    reason_display = serializers.CharField(source='get_reason_display', read_only=True)
    duration_hours = serializers.SerializerMethodField()
    
    class Meta:
        model = Downtime
        fields = [
            'id', 'device', 'start_time', 'end_time', 'reason',
            'reason_display', 'description', 'reported_by',
            'duration_hours', 'created_at'
        ]
        
    def get_duration_hours(self, obj):
        """
        حساب مدة التوقف بالساعات
        """
        if obj.end_time:
            duration = obj.end_time - obj.start_time
            return round(duration.total_seconds() / 3600, 2)
        return None

class PurchaseOrderItemSerializer(serializers.ModelSerializer):
    """
    سيريالايزر لعناصر أوامر الشراء
    """
    spare_part = SparePartSerializer(read_only=True)
    
    class Meta:
        model = PurchaseOrderItem
        fields = [
            'id', 'spare_part', 'quantity_ordered', 'quantity_received',
            'unit_cost', 'total_cost'
        ]

class PurchaseOrderSerializer(serializers.ModelSerializer):
    """
    سيريالايزر لأوامر الشراء
    """
    supplier = SupplierSerializer(read_only=True)
    created_by = UserSerializer(read_only=True)
    items = PurchaseOrderItemSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = PurchaseOrder
        fields = [
            'id', 'order_number', 'supplier', 'created_by',
            'order_date', 'expected_delivery_date', 'actual_delivery_date',
            'status', 'status_display', 'payment_terms', 'notes',
            'total_amount', 'items', 'created_at', 'updated_at'
        ]

# سيريالايزرز مبسطة للاستخدام في القوائم
class DeviceListSerializer(serializers.ModelSerializer):
    """
    سيريالايزر مبسط للأجهزة في القوائم
    """
    department_name = serializers.CharField(source='department.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Device
        fields = ['id', 'name', 'serial_number', 'model', 'department_name', 'status', 'status_display']

class ServiceRequestListSerializer(serializers.ModelSerializer):
    """
    سيريالايزر مبسط لطلبات الخدمة في القوائم
    """
    device_name = serializers.CharField(source='device.name', read_only=True)
    requested_by_name = serializers.CharField(source='requested_by.get_full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    
    class Meta:
        model = ServiceRequest
        fields = [
            'id', 'title', 'device_name', 'requested_by_name',
            'status', 'status_display', 'priority', 'priority_display',
            'created_at'
        ]

class WorkOrderListSerializer(serializers.ModelSerializer):
    """
    سيريالايزر مبسط لأوامر الشغل في القوائم
    """
    device_name = serializers.CharField(source='service_request.device.name', read_only=True)
    technician_name = serializers.CharField(source='assigned_technician.get_full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = WorkOrder
        fields = [
            'id', 'device_name', 'technician_name', 'status',
            'status_display', 'start_time', 'end_time', 'created_at'
        ]

# سيريالايزرز للإنشاء والتحديث
class ServiceRequestCreateSerializer(serializers.ModelSerializer):
    """
    سيريالايزر لإنشاء طلبات خدمة جديدة
    """
    class Meta:
        model = ServiceRequest
        fields = [
            'title', 'description', 'device', 'priority', 'request_type'
        ]
        
    def create(self, validated_data):
        # إضافة المستخدم الحالي كطالب الخدمة
        validated_data['requested_by'] = self.context['request'].user
        return super().create(validated_data)

class WorkOrderUpdateSerializer(serializers.ModelSerializer):
    """
    سيريالايزر لتحديث أوامر الشغل
    """
    class Meta:
        model = WorkOrder
        fields = [
            'status', 'work_performed', 'findings', 'recommendations',
            'labor_hours', 'labor_cost'
        ]

class SparePartTransactionCreateSerializer(serializers.ModelSerializer):
    """
    سيريالايزر لإنشاء معاملات قطع الغيار
    """
    class Meta:
        model = SparePartTransaction
        fields = [
            'spare_part', 'transaction_type', 'quantity',
            'reference_number', 'work_order', 'device', 'notes'
        ]
        
    def create(self, validated_data):
        # إضافة المستخدم الحالي
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)
