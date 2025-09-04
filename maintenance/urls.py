from django.urls import path, include
from . import views
from . import views_accessory
from . import views_cmms
from . import views_reports

app_name = 'maintenance'

urlpatterns = [
    # Dashboard
    path('', views.maintenance_dashboard_qr, name='maintenance_dashboard'),
    path('dashboard_qr/', views.maintenance_dashboard_qr, name='dashboard_qr'),
    
    # QR Code System
    path('qr-links/', views.qr_links_page, name='qr_links_page'),
    
    # Operations Management
    path('operations/', views.operations_list, name='operations_list'),
    path('operations/create/', views.operation_create, name='operation_create'),
    path('operations/<int:pk>/edit/', views.operation_edit, name='operation_edit'),
    path('operations/<int:pk>/delete/', views.operation_delete, name='operation_delete'),
    path('operations/<int:pk>/detail/', views.operation_detail, name='operation_detail'),
    
    # Sessions Management
    path('sessions/', views.sessions_list, name='sessions_list'),
    path('sessions/<int:pk>/', views.session_detail, name='session_detail'),
    
    # Executions Management
    path('executions/', views.executions_list, name='executions_list'),
    path('executions/<int:pk>/', views.execution_detail, name='execution_detail'),
    
    path('index/', views.index, name='maintenance_index'),
    path('devices/', views.device_list, name='device_list'),
    path('devices/add/', views.add_device, name='add_device'),
    path('devices/<int:pk>/', views.device_detail, name='device_detail'),
    path('devices/<int:pk>/edit/', views.device_edit, name='device_edit'),
    path('devices/<int:pk>/delete/', views.device_delete, name='device_delete'),
    
     
    path('device/<int:device_id>/transfer-history/', views.device_transfer_history, name='device_transfer_history'),

    path('transfers/<int:transfer_id>/approve/', views.approve_transfer, name='approve_transfer'),
    
    # Enhanced Device Transfer Workflow URLs
    path('transfer-requests/', views.transfer_requests_list, name='transfer_requests_list'),
    path('transfer-requests/<int:pk>/', views.transfer_request_detail, name='transfer_request_detail'),
    path('transfer-requests/create/<int:device_id>/', views.transfer_request_create, name='device_transfer'),
    path('transfer-success/<int:pk>/', views.transfer_success, name='transfer_success'),
    path('transfer-requests/<int:pk>/approve/', views.approve_transfer_request, name='approve_transfer_request'),
    path('transfer-requests/<int:pk>/accept/', views.accept_transfer_request, name='accept_transfer_request'),
    path('transfer-requests/<int:pk>/reject/', views.reject_transfer_request, name='reject_transfer_request'),
    
    # All Devices Transfer Page
    path('all-devices-transfer/', views.all_devices_transfer, name='all_devices_transfer'),
    
    # Department Transfer Requests
    path('department/<int:department_id>/transfer-requests/', views.department_transfer_requests, name='department_transfer_requests'),
    
    # AJAX endpoints for transfer forms
    path('ajax/get-department-rooms/', views.get_department_rooms, name='get_department_rooms'),
    path('ajax/get-room-beds/', views.get_room_beds, name='get_room_beds'),
    path('ajax/get-department-patients/', views.get_department_patients, name='get_department_patients'),
      # تصنيفات جديدة
    path('categories/add/', views.add_device_category, name='add_device_category'),
    path('subcategories/add/', views.add_device_subcategory, name='add_device_subcategory'),
    path('ajax/load-subcategories/', views.load_subcategories, name='ajax_load_subcategories'),
    path('ajax/load-rooms/', views.load_rooms, name='ajax_load_rooms'),
    path('device/<int:pk>/info/', views.device_info, name='device_info'),
    path('device/<int:pk>/add-accessory/', views.redirect_to_accessories, name='add_accessory'),
    path('device/<int:device_id>/maintenance-schedule/', views.maintenance_schedule, name='maintenance_schedule'),
    path('device/<int:device_id>/edit-schedule/', views.edit_schedule, name='edit_schedule'),
    path('device/<int:device_id>/delete-schedule/', views.delete_schedule, name='delete_schedule'),
    path('calibration-tracking/', views.calibration_tracking, name='calibration_tracking'),
    path('device/<int:pk>/emergency-request/', views.add_emergency_request, name='add_emergency_request'),
    path('device/<int:pk>/add-spare-part/', views.add_spare_part, name='add_spare_part'),
   
    path('ajax/get-rooms/', views.get_rooms, name='get_rooms'),
    path('ajax/calculate-sla-times/', views.ajax_calculate_sla_times, name='ajax_calculate_sla_times'),
    path('ajax/get-beds/', views.get_beds, name='get_beds'),
    path('ajax/get-patients-by-department/', views.get_patients_by_department, name='get_patients_by_department'),


   path('companies/add/', views.add_company, name='add_company'),
   
   path('device-types/add/', views.add_device_type, name='add_device_type'),
   path('device-usages/add/', views.add_device_usage, name='add_device_usage'),


    # تعديل وحذف الشركات
    path('company/edit/<int:pk>/', views.edit_company, name='edit_company'),
    path('company/delete/<int:pk>/', views.edit_company, name='delete_company'),

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
    path('device/<int:device_id>/maintain/', views.perform_maintenance, name='device_maintain'),
    
    # AJAX endpoints for instant device status updates
    path('ajax/device/<int:device_id>/clean/', views.ajax_clean_device, name='ajax_clean_device'),
    path('ajax/device/<int:device_id>/sterilize/', views.ajax_sterilize_device, name='ajax_sterilize_device'),
    path('ajax/device/<int:device_id>/maintain/', views.ajax_perform_maintenance, name='ajax_perform_maintenance'),


    path('device/<int:device_id>/sterilization_history/', views.sterilization_history, name='sterilization_history'),
    path('device/<int:device_id>/cleaning_history/', views.cleaning_history, name='cleaning_history'),
    path('device/<int:device_id>/maintenance_history/', views.maintenance_history, name='maintenance_history'),

    # QR/Barcode Scanning APIs
    path('api/scan-qr/', views.scan_qr_code, name='scan_qr_code'),
    path('api/qr-scan/', views.scan_qr_code_api, name='scan_qr_code_api'),
    path('scan-session/', views.scan_session_page, name='scan_session_page'),
    path('api/scan-session/end/', views.end_scan_session, name='end_scan_session'),
    
    # Dynamic Operation APIs
    path('api/operation/confirm/<int:execution_id>/', views.confirm_operation, name='confirm_operation'),
    path('api/operation/cancel/<int:execution_id>/', views.cancel_operation, name='cancel_operation'),
    path('usage-logs/', views.device_usage_logs, name='device_usage_logs'),
    path('usage-logs/export/', views.export_device_usage_logs, name='export_device_usage_logs'),

    # Step 3: Additional API endpoints
    path('api/start-session/', views.start_scan_session, name='start_scan_session'),
    path('api/reset-session/', views.reset_scan_session, name='reset_scan_session'),
    path('api/session-status/<uuid:session_id>/', views.get_session_status, name='get_session_status'),
    path('api/generate-qr/', views.generate_qr_code, name='generate_qr_code'),
    path('qr-test/', views.qr_test_page, name='qr_test_page'),
    path('mobile-qr/', views.mobile_qr_scan, name='mobile_qr_scan'),

    # Device Accessories URLs
    path('devices/<int:device_id>/accessories/', views_accessory.DeviceAccessoryListView.as_view(), name='device_accessories'),
    path('devices/<int:device_id>/accessories/add/', views_accessory.DeviceAccessoryCreateView.as_view(), name='accessory_create'),
    path('accessories/<int:pk>/edit/', views_accessory.DeviceAccessoryUpdateView.as_view(), name='accessory_edit'),
    path('accessories/<int:pk>/delete/', views_accessory.DeviceAccessoryDeleteView.as_view(), name='accessory_delete'),
    path('accessories/<int:pk>/', views_accessory.accessory_detail, name='accessory_detail'),
    path('accessories/<int:pk>/qr-print/', views_accessory.accessory_qr_print, name='accessory_qr_print'),
    path('api/devices/<int:device_id>/verify-accessories/', views_accessory.verify_device_accessories, name='verify_device_accessories'),
    path('ajax/get-rooms/', views_accessory.ajax_get_rooms, name='ajax_get_rooms'),
    path('ajax/get-devices/', views_accessory.ajax_get_devices, name='ajax_get_devices'),

    # Accessory Transfer URLs
    path('accessories/<int:pk>/transfer/', views_accessory.transfer_accessory, name='accessory_transfer'),
    path('accessories/<int:pk>/transfer-history/', views_accessory.accessory_transfer_history, name='accessory_transfer_history'),
    path('accessory-transfers/<int:transfer_id>/approve/', views_accessory.approve_accessory_transfer, name='approve_accessory_transfer'),
    # Test Page
    path('transfer-test/', views.transfer_test_page, name='transfer_test_page'),
    
    # CMMS URLs
    path('cmms/', include('maintenance.urls_cmms', namespace='cmms')),

    # Dashboard URLs
    path('dashboard/', include('maintenance.urls_dashboard', namespace='dashboard')),
    
    # Spare Parts, Calibration and Downtime URLs - نظام قطع الغيار والمعايرة والتوقف
    path('spare-parts/', include('maintenance.urls_spare_parts', namespace='spare_parts')),
    path("test-links/", views.test_links, name="test_links"),
    
    # Reports URLs
    path('department/<int:department_id>/export-report/', views_reports.export_department_devices_report, name='export_department_report'),

]