from django.urls import path, include
from . import views
from . import views_accessory
from . import views_cmms

app_name = 'maintenance'

urlpatterns = [
    
    path('', views.index, name='maintenance_index'),
    path('devices/', views.device_list, name='device_list'),
    path('devices/add/', views.add_device, name='add_device'),
    path('devices/<int:pk>/', views.device_detail, name='device_detail'),
    path('devices/<int:pk>/edit/', views.device_edit, name='device_edit'),
    path('devices/<int:pk>/delete/', views.device_delete, name='device_delete'),
    
    path('devices/<int:device_id>/transfer/', views.transfer_device, name='device_transfer'),
     
    path('device/<int:device_id>/transfer-history/', views.device_transfer_history, name='device_transfer_history'),

    path('devices/department/<int:department_id>/', views.department_devices, name='department_devices'),
    path('transfers/<int:transfer_id>/approve/', views.approve_transfer, name='approve_transfer'),
      # تصنيفات جديدة
    path('categories/add/', views.add_device_category, name='add_device_category'),
    path('subcategories/add/', views.add_device_subcategory, name='add_device_subcategory'),
    path('ajax/load-subcategories/', views.load_subcategories, name='ajax_load_subcategories'),
    path('ajax/load-rooms/', views.load_rooms, name='ajax_load_rooms'),
    path('device/<int:pk>/info/', views.device_info, name='device_info'),
    path('device/<int:pk>/add-accessory/', views.redirect_to_accessories, name='add_accessory'),
    path('device/<int:pk>/maintenance-schedule/', views.maintenance_schedule, name='maintenance_schedule'),
    path('device/<int:pk>/emergency-request/', views.add_emergency_request, name='add_emergency_request'),
    path('device/<int:pk>/add-spare-part/', views.add_spare_part, name='add_spare_part'),
   
    path('ajax/get-rooms/', views.get_rooms, name='get_rooms'),
    path('ajax/get-beds/', views.get_beds, name='get_beds'),


   path('companies/add/', views.add_company, name='add_company'),
   
   path('device-types/add/', views.add_device_type, name='add_device_type'),
   path('device-usages/add/', views.add_device_usage, name='add_device_usage'),


    # تعديل وحذف الشركات
    path('company/edit/<int:pk>/', views.edit_company, name='edit_company'),
    path('company/delete/<int:pk>/', views.delete_company, name='delete_company'),

    # تعديل وحذف نوع الجهاز
    path('device-type/edit/<int:pk>/', views.edit_device_type, name='edit_device_type'),
    path('device-type/delete/<int:pk>/', views.delete_device_type, name='delete_device_type'),

    # تعديل وحذف استخدام الجهاز
    path('device-usage/edit/<int:pk>/', views.edit_device_usage, name='edit_device_usage'),
    path('device-usage/delete/<int:pk>/', views.delete_device_usage, name='delete_device_usage'),

    path('devices/<int:device_id>/assign/', views.assign_device, name='assign_device'),
    path('devices/<int:device_id>/release/', views.release_device, name='release_device'),




    path('device/<int:device_id>/clean/', views.clean_device, name='clean_device'),
    path('device/<int:device_id>/sterilize/', views.sterilize_device, name='sterilize_device'),
    path('device/<int:device_id>/maintain/', views.perform_maintenance, name='perform_maintenance'),


    path('device/<int:device_id>/sterilization_history/', views.sterilization_history, name='sterilization_history'),
    path('device/<int:device_id>/cleaning_history/', views.cleaning_history, name='cleaning_history'),
    path('device/<int:device_id>/maintenance_history/', views.maintenance_history, name='maintenance_history'),

    # QR/Barcode Scanning System URLs
    path('scan/', views.scan_session_page, name='scan_session'),
    path('api/scan-qr/', views.scan_qr_code, name='scan_qr_code'),
    path('qr-test/', views.qr_test_page, name='qr_test_page'),
    path('api/save-session/', views.save_scan_session, name='save_scan_session'),
    path('usage-logs/', views.device_usage_logs, name='device_usage_logs'),
    path('usage-logs/export/', views.export_device_usage_logs, name='export_device_usage_logs'),

    # Step 3: Additional API endpoints
    path('api/start-session/', views.start_scan_session, name='start_scan_session'),
    path('api/reset-session/', views.reset_scan_session, name='reset_scan_session'),
    path('api/session-status/<uuid:session_id>/', views.get_session_status, name='get_session_status'),
    path('api/generate-qr/', views.generate_qr_code, name='generate_qr_code'),

    # Device Accessories URLs
    path('devices/<int:device_id>/accessories/', views_accessory.DeviceAccessoryListView.as_view(), name='device_accessories'),
    path('devices/<int:device_id>/accessories/add/', views_accessory.DeviceAccessoryCreateView.as_view(), name='accessory_create'),
    path('accessories/<int:pk>/edit/', views_accessory.DeviceAccessoryUpdateView.as_view(), name='accessory_edit'),
    path('accessories/<int:pk>/delete/', views_accessory.DeviceAccessoryDeleteView.as_view(), name='accessory_delete'),
    path('accessories/<int:pk>/', views_accessory.accessory_detail, name='accessory_detail'),
    path('accessories/<int:pk>/qr-print/', views_accessory.accessory_qr_print, name='accessory_qr_print'),
    path('devices/<int:device_id>/accessories/scan/', views_accessory.accessory_scan_page, name='accessory_scan'),
    path('api/devices/<int:device_id>/verify-accessories/', views_accessory.verify_device_accessories, name='verify_device_accessories'),

    # Accessory Transfer URLs
    path('accessories/<int:pk>/transfer/', views_accessory.transfer_accessory, name='accessory_transfer'),
    path('accessories/<int:pk>/transfer-history/', views_accessory.accessory_transfer_history, name='accessory_transfer_history'),
    path('accessory-transfers/<int:transfer_id>/approve/', views_accessory.approve_accessory_transfer, name='approve_accessory_transfer'),
        
    # CMMS URLs
    path('cmms/', include('maintenance.urls_cmms', namespace='cmms')),
    
    # Spare Parts, Calibration and Downtime URLs - نظام قطع الغيار والمعايرة والتوقف
    path('spare-parts/', include('maintenance.urls_spare_parts', namespace='spare_parts')),
    path("test-links/", views.test_links, name="test_links"),

]