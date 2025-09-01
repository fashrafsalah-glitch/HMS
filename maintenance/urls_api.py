from django.urls import path
from . import views
from . import views_accessory

urlpatterns = [
    # QR Code Scanning APIs
    path('scan-qr/', views.scan_qr_code, name='scan_qr_code'),
    path('qr-scan/', views.scan_qr_code_api, name='scan_qr_code_api'),
    
    # Session Management APIs
    path('start-session/', views.start_scan_session, name='start_scan_session'),
    path('reset-session/', views.reset_scan_session, name='reset_scan_session'),
    path('session-status/<uuid:session_id>/', views.get_session_status, name='get_session_status'),
    path('scan-session/end/', views.end_scan_session, name='end_scan_session'),
    
    # Dynamic Operation APIs
    path('operation/confirm/<int:execution_id>/', views.confirm_operation, name='confirm_operation'),
    path('operation/cancel/<int:execution_id>/', views.cancel_operation, name='cancel_operation'),
    
    # QR Generation API
    path('generate-qr/', views.generate_qr_code, name='generate_qr_code'),
    
    # Device Accessories API
    path('devices/<int:device_id>/verify-accessories/', views_accessory.verify_device_accessories, name='verify_device_accessories'),
]
