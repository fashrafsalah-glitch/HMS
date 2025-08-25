# هنا بنعمل الـ URLs للـ API عشان نقدر نوصل للـ endpoints من الموبايل أو الفرونت إند
from django.urls import path
from . import api_views

app_name = 'maintenance_api'

urlpatterns = [
    # ============= Device APIs =============
    path('devices/', api_views.DeviceListAPIView.as_view(), name='device_list'),
    path('devices/<int:pk>/', api_views.DeviceDetailAPIView.as_view(), name='device_detail'),
    path('devices/qr/<str:qr_token>/', api_views.device_qr_scan, name='device_qr_scan'),
    
    # ============= Service Request APIs =============
    path('service-requests/', api_views.ServiceRequestListAPIView.as_view(), name='service_request_list'),
    path('service-requests/<int:pk>/', api_views.ServiceRequestDetailAPIView.as_view(), name='service_request_detail'),
    path('service-requests/<int:pk>/assign/', api_views.service_request_assign, name='service_request_assign'),
    path('service-requests/quick/', api_views.quick_service_request, name='quick_service_request'),
    
    # ============= Work Order APIs =============
    path('work-orders/', api_views.WorkOrderListAPIView.as_view(), name='work_order_list'),
    path('work-orders/<int:pk>/', api_views.WorkOrderDetailAPIView.as_view(), name='work_order_detail'),
    path('work-orders/<int:pk>/start/', api_views.work_order_start, name='work_order_start'),
    path('work-orders/<int:pk>/complete/', api_views.work_order_complete, name='work_order_complete'),
    
    # ============= Spare Parts APIs =============
    path('spare-parts/', api_views.SparePartListAPIView.as_view(), name='spare_part_list'),
    path('spare-parts/<int:pk>/', api_views.SparePartDetailAPIView.as_view(), name='spare_part_detail'),
    path('spare-parts/transaction/', api_views.spare_part_transaction, name='spare_part_transaction'),
    
    # ============= Dashboard APIs =============
    path('dashboard/summary/', api_views.dashboard_summary, name='dashboard_summary'),
    path('dashboard/alerts/', api_views.critical_alerts, name='critical_alerts'),
    path('dashboard/mobile/', api_views.mobile_dashboard, name='mobile_dashboard'),
    
    # ============= User Tasks APIs =============
    path('my-tasks/', api_views.my_tasks, name='my_tasks'),
    
    # ============= Statistics APIs =============
    path('statistics/', api_views.maintenance_statistics, name='maintenance_statistics'),
    
    # ============= Search APIs =============
    path('search/', api_views.global_search, name='global_search'),
]
