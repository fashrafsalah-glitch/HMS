# هنا بنعمل الـ API Views للـ CMMS عشان نقدر نتعامل مع البيانات من الموبايل أو الفرونت إند
from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count, Sum
from django.utils import timezone
from datetime import timedelta

from .models import Device, DeviceAccessory
from .models import ServiceRequest, WorkOrder, JobPlan, PreventiveMaintenanceSchedule, SparePart
from .serializers import (
    DeviceSerializer, DeviceListSerializer, DeviceAccessorySerializer,
    ServiceRequestSerializer, ServiceRequestListSerializer, ServiceRequestCreateSerializer,
    WorkOrderSerializer, WorkOrderListSerializer, WorkOrderUpdateSerializer,
    SparePartSerializer, SparePartTransactionSerializer, SparePartTransactionCreateSerializer,
    JobPlanSerializer, PreventiveMaintenanceScheduleSerializer,
    CalibrationSerializer, DowntimeSerializer, PurchaseOrderSerializer
)
from .kpi_utils import get_dashboard_summary, get_critical_alerts

class StandardResultsSetPagination(PageNumberPagination):
    """
    إعدادات التصفح للـ API
    """
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

# ============= Device APIs =============

class DeviceListAPIView(generics.ListAPIView):
    """
    API لجلب قائمة الأجهزة
    """
    serializer_class = DeviceListSerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        queryset = Device.objects.select_related('department', 'category', 'subcategory')
        
        # فلترة حسب القسم
        department = self.request.query_params.get('department')
        if department:
            queryset = queryset.filter(department_id=department)
            
        # فلترة حسب الحالة
        status = self.request.query_params.get('status')
        if status:
            queryset = queryset.filter(status=status)
            
        # البحث
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(serial_number__icontains=search) |
                Q(model__icontains=search)
            )
            
        return queryset.order_by('-id')

class DeviceDetailAPIView(generics.RetrieveAPIView):
    """
    API لجلب تفاصيل جهاز معين
    """
    queryset = Device.objects.select_related('department', 'category', 'subcategory', 'room')
    serializer_class = DeviceSerializer
    permission_classes = [permissions.IsAuthenticated]

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def device_qr_scan(request, qr_token):
    """
    API لمسح QR Code الخاص بالجهاز
    """
    try:
        device = Device.objects.get(qr_token=qr_token)
        serializer = DeviceSerializer(device)
        return Response({
            'success': True,
            'device': serializer.data,
            'message': f'تم العثور على الجهاز: {device.name}'
        })
    except Device.DoesNotExist:
        return Response({
            'success': False,
            'message': 'لم يتم العثور على الجهاز'
        }, status=status.HTTP_404_NOT_FOUND)

# ============= Service Request APIs =============

class ServiceRequestListAPIView(generics.ListCreateAPIView):
    """
    API لجلب وإنشاء طلبات الخدمة
    """
    pagination_class = StandardResultsSetPagination
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ServiceRequestCreateSerializer
        return ServiceRequestListSerializer
    
    def get_queryset(self):
        queryset = ServiceRequest.objects.select_related(
            'device', 'requested_by', 'assigned_to'
        )
        
        # فلترة حسب الحالة
        status = self.request.query_params.get('status')
        if status:
            queryset = queryset.filter(status=status)
            
        # فلترة حسب الأولوية
        priority = self.request.query_params.get('priority')
        if priority:
            queryset = queryset.filter(priority=priority)
            
        # فلترة حسب نوع الطلب
        request_type = self.request.query_params.get('request_type')
        if request_type:
            queryset = queryset.filter(request_type=request_type)
            
        # فلترة حسب الجهاز
        device = self.request.query_params.get('device')
        if device:
            queryset = queryset.filter(device_id=device)
            
        # فلترة حسب المستخدم (طلباتي فقط)
        my_requests = self.request.query_params.get('my_requests')
        if my_requests == 'true':
            queryset = queryset.filter(reporter=self.request.user)
            
        return queryset.order_by('-created_at')

class ServiceRequestDetailAPIView(generics.RetrieveUpdateAPIView):
    """
    API لجلب وتحديث تفاصيل طلب خدمة
    """
    queryset = ServiceRequest.objects.select_related(
        'device', 'reporter', 'assigned_to', 'sla'
    )
    serializer_class = ServiceRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def service_request_assign(request, pk):
    """
    API لتعيين طلب خدمة لفني
    """
    service_request = get_object_or_404(ServiceRequest, pk=pk)
    
    # التحقق من الصلاحيات
    if not request.user.is_superuser and not request.user.groups.filter(name__in=['Supervisor']).exists():
        return Response({
            'success': False,
            'message': 'ليس لديك صلاحية لتعيين طلبات الخدمة'
        }, status=status.HTTP_403_FORBIDDEN)
    
    technician_id = request.data.get('technician_id')
    if not technician_id:
        return Response({
            'success': False,
            'message': 'يجب تحديد الفني'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        from django.contrib.auth.models import User
        technician = User.objects.get(id=technician_id)
        
        service_request.assigned_to = technician
        service_request.status = 'assigned'
        service_request.save()
        
        return Response({
            'success': True,
            'message': f'تم تعيين الطلب للفني {technician.get_full_name()}'
        })
        
    except User.DoesNotExist:
        return Response({
            'success': False,
            'message': 'الفني غير موجود'
        }, status=status.HTTP_404_NOT_FOUND)

# ============= Work Order APIs =============

class WorkOrderListAPIView(generics.ListAPIView):
    """
    API لجلب قائمة أوامر الشغل
    """
    serializer_class = WorkOrderListSerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        queryset = WorkOrder.objects.select_related(
            'service_request__device', 'assigned_technician', 'supervisor'
        )
        
        # فلترة حسب الحالة
        status = self.request.query_params.get('status')
        if status:
            queryset = queryset.filter(status=status)
            
        # فلترة حسب الفني
        technician = self.request.query_params.get('technician')
        if technician:
            queryset = queryset.filter(assigned_technician_id=technician)
            
        # فلترة أوامر الشغل الخاصة بي
        my_work_orders = self.request.query_params.get('my_work_orders')
        if my_work_orders == 'true':
            queryset = queryset.filter(assigned_technician=self.request.user)
            
        return queryset.order_by('-created_at')

class WorkOrderDetailAPIView(generics.RetrieveUpdateAPIView):
    """
    API لجلب وتحديث تفاصيل أمر شغل
    """
    queryset = WorkOrder.objects.select_related(
        'service_request__device', 'assigned_technician', 'supervisor'
    ).prefetch_related('spare_parts_used__spare_part')
    serializer_class = WorkOrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return WorkOrderUpdateSerializer
        return WorkOrderSerializer

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def work_order_start(request, pk):
    """
    API لبدء تنفيذ أمر شغل
    """
    work_order = get_object_or_404(WorkOrder, pk=pk)
    
    # التحقق من أن المستخدم هو الفني المعين أو مشرف
    if (work_order.assigned_technician != request.user and 
        not request.user.is_superuser and 
        not request.user.groups.filter(name__in=['Supervisor']).exists()):
        return Response({
            'success': False,
            'message': 'ليس لديك صلاحية لتنفيذ هذا الأمر'
        }, status=status.HTTP_403_FORBIDDEN)
    
    if work_order.status != 'assigned':
        return Response({
            'success': False,
            'message': 'لا يمكن بدء تنفيذ هذا الأمر في الحالة الحالية'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    work_order.status = 'in_progress'
    work_order.start_time = timezone.now()
    work_order.save()
    
    return Response({
        'success': True,
        'message': 'تم بدء تنفيذ أمر الشغل'
    })

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def work_order_complete(request, pk):
    """
    API لإكمال أمر شغل
    """
    work_order = get_object_or_404(WorkOrder, pk=pk)
    
    # التحقق من الصلاحيات
    if (work_order.assigned_technician != request.user and 
        not request.user.is_superuser and 
        not request.user.groups.filter(name__in=['Supervisor']).exists()):
        return Response({
            'success': False,
            'message': 'ليس لديك صلاحية لإكمال هذا الأمر'
        }, status=status.HTTP_403_FORBIDDEN)
    
    if work_order.status != 'in_progress':
        return Response({
            'success': False,
            'message': 'لا يمكن إكمال هذا الأمر في الحالة الحالية'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # تحديث بيانات الأمر
    work_order.status = 'resolved'
    work_order.end_time = timezone.now()
    work_order.work_performed = request.data.get('work_performed', '')
    work_order.findings = request.data.get('findings', '')
    work_order.recommendations = request.data.get('recommendations', '')
    work_order.labor_hours = request.data.get('labor_hours', 0)
    work_order.save()
    
    return Response({
        'success': True,
        'message': 'تم إكمال أمر الشغل'
    })

# ============= Spare Parts APIs =============

class SparePartListAPIView(generics.ListAPIView):
    """
    API لجلب قائمة قطع الغيار
    """
    serializer_class = SparePartSerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        queryset = SparePart.objects.select_related('supplier')
        
        # فلترة حسب الحالة
        status = self.request.query_params.get('status')
        if status:
            queryset = queryset.filter(status=status)
            
        # البحث
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(part_number__icontains=search)
            )
            
        return queryset.order_by('name')

class SparePartDetailAPIView(generics.RetrieveAPIView):
    """
    API لجلب تفاصيل قطعة غيار
    """
    queryset = SparePart.objects.select_related('supplier').prefetch_related('compatible_devices')
    serializer_class = SparePartSerializer
    permission_classes = [permissions.IsAuthenticated]

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def spare_part_transaction(request):
    """
    API لإنشاء معاملة قطعة غيار (دخول أو خروج)
    """
    serializer = SparePartTransactionCreateSerializer(data=request.data, context={'request': request})
    
    if serializer.is_valid():
        transaction = serializer.save()
        
        return Response({
            'success': True,
            'message': 'تم تسجيل المعاملة بنجاح',
            'transaction_id': transaction.id
        }, status=status.HTTP_201_CREATED)
    
    return Response({
        'success': False,
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)

# ============= Dashboard APIs =============

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def dashboard_summary(request):
    """
    API لجلب ملخص الداشبورد
    """
    department_id = request.query_params.get('department')
    summary = get_dashboard_summary(department_id=department_id)
    
    return Response({
        'success': True,
        'data': summary
    })

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def critical_alerts(request):
    """
    API لجلب التنبيهات الحرجة
    """
    department_id = request.query_params.get('department')
    alerts = get_critical_alerts(department_id=department_id)
    
    return Response({
        'success': True,
        'alerts': alerts
    })

# ============= Mobile Specific APIs =============

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def mobile_dashboard(request):
    """
    API مخصص للموبايل - داشبورد مبسط
    """
    user = request.user
    
    # أوامر الشغل الخاصة بالمستخدم
    my_work_orders = WorkOrder.objects.filter(
        assigned_technician=user,
        status__in=['assigned', 'in_progress']
    ).count()
    
    # طلبات الخدمة المعلقة
    pending_requests = ServiceRequest.objects.filter(
        assigned_to=user,
        status__in=['new', 'assigned']
    ).count()
    
    # قطع الغيار المنخفضة
    low_stock_parts = SparePart.objects.filter(status='low_stock').count()
    
    # الأجهزة خارج الخدمة
    out_of_service_devices = Device.objects.filter(status='out_of_service').count()
    
    return Response({
        'success': True,
        'data': {
            'my_work_orders': my_work_orders,
            'pending_requests': pending_requests,
            'low_stock_parts': low_stock_parts,
            'out_of_service_devices': out_of_service_devices,
            'user_name': user.get_full_name() or user.username
        }
    })

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def my_tasks(request):
    """
    API لجلب مهام المستخدم الحالي
    """
    user = request.user
    
    # أوامر الشغل المعينة للمستخدم
    work_orders = WorkOrder.objects.filter(
        assigned_technician=user,
        status__in=['assigned', 'in_progress']
    ).select_related('service_request__device')[:10]
    
    # طلبات الخدمة المعينة للمستخدم
    service_requests = ServiceRequest.objects.filter(
        assigned_to=user,
        status__in=['new', 'assigned']
    ).select_related('device')[:10]
    
    # جداول الصيانة الوقائية المستحقة
    pm_schedules = PreventiveMaintenanceSchedule.objects.filter(
        assigned_technician=user,
        status='active',
        next_due_date__lte=timezone.now().date() + timedelta(days=7)
    ).select_related('device', 'job_plan')[:5]
    
    return Response({
        'success': True,
        'data': {
            'work_orders': WorkOrderListSerializer(work_orders, many=True).data,
            'service_requests': ServiceRequestListSerializer(service_requests, many=True).data,
            'pm_schedules': PreventiveMaintenanceScheduleSerializer(pm_schedules, many=True).data
        }
    })

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def quick_service_request(request):
    """
    API لإنشاء طلب خدمة سريع من الموبايل
    """
    device_qr = request.data.get('device_qr')
    title = request.data.get('title')
    description = request.data.get('description')
    priority = request.data.get('priority', 'medium')
    
    if not device_qr or not title:
        return Response({
            'success': False,
            'message': 'يجب تحديد الجهاز والعنوان'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        device = Device.objects.get(qr_token=device_qr)
        
        service_request = ServiceRequest.objects.create(
            title=title,
            description=description or '',
            device=device,
            reporter=request.user,
            priority=priority,
            request_type='breakdown'
        )
        
        return Response({
            'success': True,
            'message': 'تم إنشاء طلب الخدمة بنجاح',
            'service_request_id': service_request.id
        }, status=status.HTTP_201_CREATED)
        
    except Device.DoesNotExist:
        return Response({
            'success': False,
            'message': 'الجهاز غير موجود'
        }, status=status.HTTP_404_NOT_FOUND)

# ============= Statistics APIs =============

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def maintenance_statistics(request):
    """
    API لجلب إحصائيات الصيانة
    """
    days = int(request.query_params.get('days', 30))
    start_date = timezone.now() - timedelta(days=days)
    
    # إحصائيات أوامر الشغل
    work_orders_stats = {
        'total': WorkOrder.objects.filter(created_at__gte=start_date).count(),
        'completed': WorkOrder.objects.filter(
            created_at__gte=start_date,
            status__in=['closed', 'qa_verified', 'resolved']
        ).count(),
        'in_progress': WorkOrder.objects.filter(
            created_at__gte=start_date,
            status='in_progress'
        ).count(),
        'overdue': WorkOrder.objects.filter(
            service_request__resolution_due__lt=timezone.now(),
            status__in=['new', 'assigned', 'in_progress']
        ).count()
    }
    
    # إحصائيات الأجهزة
    devices_stats = {
        'total': Device.objects.count(),
        'working': Device.objects.filter(status='working').count(),
        'maintenance': Device.objects.filter(status='maintenance').count(),
        'out_of_service': Device.objects.filter(status='out_of_service').count()
    }
    
    # إحصائيات قطع الغيار
    spare_parts_stats = {
        'total': SparePart.objects.count(),
        'available': SparePart.objects.filter(status='available').count(),
        'low_stock': SparePart.objects.filter(status='low_stock').count(),
        'out_of_stock': SparePart.objects.filter(status='out_of_stock').count()
    }
    
    return Response({
        'success': True,
        'data': {
            'work_orders': work_orders_stats,
            'devices': devices_stats,
            'spare_parts': spare_parts_stats,
            'period_days': days
        }
    })

# ============= Search APIs =============

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def global_search(request):
    """
    API للبحث الشامل في النظام
    """
    query = request.query_params.get('q', '').strip()
    
    if len(query) < 2:
        return Response({
            'success': False,
            'message': 'يجب أن يكون البحث أكثر من حرفين'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # البحث في الأجهزة
    devices = Device.objects.filter(
        Q(name__icontains=query) |
        Q(serial_number__icontains=query) |
        Q(model__icontains=query)
    )[:5]
    
    # البحث في طلبات الخدمة
    service_requests = ServiceRequest.objects.filter(
        Q(title__icontains=query) |
        Q(description__icontains=query)
    )[:5]
    
    # البحث في قطع الغيار
    spare_parts = SparePart.objects.filter(
        Q(name__icontains=query) |
        Q(part_number__icontains=query)
    )[:5]
    
    return Response({
        'success': True,
        'results': {
            'devices': DeviceListSerializer(devices, many=True).data,
            'service_requests': ServiceRequestListSerializer(service_requests, many=True).data,
            'spare_parts': SparePartSerializer(spare_parts, many=True).data
        }
    })
