# core/urls.py

from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from django.shortcuts import redirect

urlpatterns = [


     # ...
    path("i18n/", include("django.conf.urls.i18n")),  # ← يوفّر view اسمه set_language
    path("rosetta/", include("rosetta.urls")),   # <— لوحة الترجمة


    
    # Redirect root → patient list
    path("", lambda request: redirect("manager:patient_list")),

    path("admin/", admin.site.urls),

   

    # built-in auth
    path("auth/", include("django.contrib.auth.urls")),

    # super-admin panel & login
    path("superadmin/", include(("superadmin.urls", "superadmin"), namespace="superadmin")),

    # hospital-manager module
    path("patients/", include(("manager.urls", "manager"), namespace="manager")),
    path("patients/", include(("manager.urls", "patient"), namespace="patient")),  # ← alias مؤقت
    path("manager/", include(("manager.urls", "manager_api"), namespace="manager_api")),
    
      

    # HR module
    path("hr/", include(("hr.urls", "hr"), namespace="hr")),

    # staff self-service
    path("staff/", include(("staff.urls", "staff"), namespace="staff")),

    # misc shared views
    path("general/", include(("general.urls", "general"), namespace="general")),

    # laboratory namespace
    path("laboratory/", include(("laboratory.urls", "laboratory"), namespace="laboratory")),

    # maintenance namespace
    path("maintenance/", include(("maintenance.urls", "maintenance"), namespace="maintenance")),
    
    # API endpoints (accessible at root level)
    path("api/", include("maintenance.urls_api")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
