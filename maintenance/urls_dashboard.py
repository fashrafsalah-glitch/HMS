from django.urls import path
from . import views_dashboard

app_name = 'dashboard'

urlpatterns = [
    # Dashboard URLs
    path('', views_dashboard.cmms_dashboard, name='cmms_dashboard'),
    path('device-performance/', views_dashboard.device_performance_dashboard, name='device_performance_dashboard'),
    path('work-order-analytics/', views_dashboard.work_order_analytics, name='work_order_analytics'),
    path('spare-parts-analytics/', views_dashboard.spare_parts_analytics, name='spare_parts_analytics'),
    path('maintenance-trends/', views_dashboard.maintenance_trends, name='maintenance_trends'),
    path('export-report/', views_dashboard.export_dashboard_report, name='export_dashboard_report'),
    
    # API URLs
    path('api/data/', views_dashboard.dashboard_api_data, name='dashboard_api_data'),
]
