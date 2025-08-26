from django.urls import path
from . import views_cmms

# هنا بنعرف مسارات URL الخاصة بنظام CMMS
# لاحظ إننا بنستخدم نفس أسلوب التسمية الموجود في المشروع

app_name = 'cmms'

urlpatterns = [
    # بلاغات الصيانة (Service Requests)
    path('service-requests/', views_cmms.service_request_list, name='service_request_list'),
    path('service-requests/create/', views_cmms.service_request_create, name='service_request_create'),
    path('service-requests/<int:sr_id>/', views_cmms.service_request_detail, name='service_request_detail'),
    path('service-requests/<int:sr_id>/update/', views_cmms.service_request_update, name='service_request_update'),
    path('service-requests/<int:sr_id>/close/', views_cmms.service_request_close, name='service_request_close'),
    
    # أوامر الشغل (Work Orders)
    path('work-orders/', views_cmms.work_order_list, name='work_order_list'),
    path('work-orders/<int:wo_id>/', views_cmms.work_order_detail, name='work_order_detail'),
    path('work-orders/<int:wo_id>/assign/', views_cmms.work_order_assign, name='work_order_assign'),
    
    # إدارة SLA
    path('sla/', views_cmms.sla_list, name='sla_list'),
    path('sla/create/', views_cmms.sla_create, name='sla_create'),
    path('sla-matrix/', views_cmms.sla_matrix_list, name='sla_matrix_list'),
    path('sla-matrix/create/', views_cmms.sla_matrix_create, name='sla_matrix_create'),
    
    # دمج مع الصفحات الموجودة
    # هنا بنعمل override للـ views الموجودة عشان نضيف عليها معلومات CMMS
    path('devices/<int:device_id>/maintenance-history/', views_cmms.device_maintenance_history, name='device_maintenance_history'),
    path('devices/<int:device_id>/detail/', views_cmms.device_detail_with_cmms, name='device_detail_with_cmms'),
    
    # API
    path('api/sr/', views_cmms.api_service_request_create, name='api_service_request_create'),
    path('api/wo/<int:wo_id>/status/', views_cmms.api_work_order_status_update, name='api_work_order_status_update'),
    path('api/devices/<int:device_id>/profile/', views_cmms.api_device_profile, name='api_device_profile'),
    
    # خطط العمل (Job Plans)
    path('job-plans/', views_cmms.job_plan_list, name='job_plan_list'),
    path('job-plans/create/', views_cmms.job_plan_create, name='job_plan_create'),
    path('job-plans/<int:plan_id>/', views_cmms.job_plan_detail, name='job_plan_detail'),
    path('job-plans/<int:plan_id>/update/', views_cmms.job_plan_update, name='job_plan_update'),
    path('job-plans/<int:plan_id>/delete/', views_cmms.job_plan_delete, name='job_plan_delete'),
    path('job-plans/steps/<int:step_id>/delete/', views_cmms.job_plan_step_delete, name='job_plan_step_delete'),
    
    # جداول الصيانة الوقائية (PM Schedules)
    path('pm-schedules/', views_cmms.pm_schedule_list, name='pm_schedule_list'),
    path('pm-schedules/create/', views_cmms.pm_schedule_create, name='pm_schedule_create'),
    path('pm-schedules/<int:schedule_id>/', views_cmms.pm_schedule_detail, name='pm_schedule_detail'),
    path('pm-schedules/<int:schedule_id>/update/', views_cmms.pm_schedule_update, name='pm_schedule_update'),
    path('pm-schedules/<int:schedule_id>/delete/', views_cmms.pm_schedule_delete, name='pm_schedule_delete'),
    path('pm-schedules/<int:schedule_id>/generate-wo/', views_cmms.pm_schedule_generate_wo, name='pm_schedule_generate_wo'),
    path('pm-schedules/<int:schedule_id>/toggle-status/', views_cmms.pm_schedule_toggle_status, name='pm_schedule_toggle_status'),
]