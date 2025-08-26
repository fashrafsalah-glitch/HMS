from django.urls import path
from . import views_spare_parts

app_name = 'spare_parts'

urlpatterns = [
    # Supplier URLs
    path('suppliers/', views_spare_parts.supplier_list, name='supplier_list'),
    path('suppliers/<int:pk>/', views_spare_parts.supplier_detail, name='supplier_detail'),
    path('suppliers/create/', views_spare_parts.supplier_create, name='supplier_create'),
    path('suppliers/<int:pk>/update/', views_spare_parts.supplier_update, name='supplier_update'),
    
    # Spare Part URLs
    path('spare-parts/', views_spare_parts.spare_part_list, name='spare_part_list'),
    path('spare-parts/<int:pk>/', views_spare_parts.spare_part_detail, name='spare_part_detail'),
    path('spare-parts/create/', views_spare_parts.spare_part_create, name='spare_part_create'),
    path('spare-parts/<int:pk>/update/', views_spare_parts.spare_part_update, name='spare_part_update'),
    path('spare-parts/transactions/create/', views_spare_parts.spare_part_transaction_create, name='spare_part_transaction_create'),
    path('spare-parts/<int:part_id>/transactions/create/', views_spare_parts.spare_part_transaction_create, name='spare_part_transaction_create_for_part'),
    path('spare-parts/export-csv/', views_spare_parts.export_spare_parts_csv, name='export_spare_parts_csv'),
    
    # Purchase Order URLs
    path('purchase-orders/', views_spare_parts.purchase_order_list, name='purchase_order_list'),
    path('purchase-orders/<int:pk>/', views_spare_parts.purchase_order_detail, name='purchase_order_detail'),
    path('purchase-orders/create/', views_spare_parts.purchase_order_create, name='purchase_order_create'),
    path('purchase-orders/<int:pk>/update/', views_spare_parts.purchase_order_update, name='purchase_order_update'),
    path('purchase-orders/<int:po_id>/items/create/', views_spare_parts.purchase_order_item_create, name='purchase_order_item_create'),
    path('purchase-order-items/<int:item_id>/update/', views_spare_parts.purchase_order_item_update, name='purchase_order_item_update'),
    path('purchase-orders/<int:pk>/receive/', views_spare_parts.purchase_order_receive_items, name='purchase_order_receive_items'),
    
    # Calibration URLs
    path('calibrations/', views_spare_parts.calibration_list, name='calibration_list'),
    path('calibrations/<int:pk>/', views_spare_parts.calibration_detail, name='calibration_detail'),
    path('calibrations/create/', views_spare_parts.calibration_create, name='calibration_create'),
    path('devices/<int:device_id>/calibrations/create/', views_spare_parts.calibration_create, name='calibration_create_for_device'),
    path('calibrations/<int:pk>/update/', views_spare_parts.calibration_update, name='calibration_update'),
    
    # Downtime URLs
    path('downtimes/', views_spare_parts.downtime_list, name='downtime_list'),
    path('downtimes/<int:pk>/', views_spare_parts.downtime_detail, name='downtime_detail'),
    path('downtimes/create/', views_spare_parts.downtime_create, name='downtime_create'),
    path('devices/<int:device_id>/downtimes/create/', views_spare_parts.downtime_create, name='downtime_create_for_device'),
    path('work-orders/<int:work_order_id>/downtimes/create/', views_spare_parts.downtime_create, name='downtime_create_for_work_order'),
    path('downtimes/<int:pk>/update/', views_spare_parts.downtime_update, name='downtime_update'),
    
    # API URLs
    path('api/spare-parts/low-stock/', views_spare_parts.api_spare_parts_low_stock, name='api_spare_parts_low_stock'),
    path('api/calibrations/due/', views_spare_parts.api_calibrations_due, name='api_calibrations_due'),
    path('api/devices/<int:device_id>/downtime-stats/', views_spare_parts.api_device_downtime_stats, name='api_device_downtime_stats'),
]