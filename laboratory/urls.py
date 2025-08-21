# laboratory/urls.py
from django.urls import path

from . import views
from .views import PatientLabResultsView

app_name = "laboratory"

urlpatterns = [
    

    # --- Lab Requests ---
    path("lab-request/new/<int:patient_id>/", views.LabRequestCreateView.as_view(), name="lab_request_add"),
    path("requests/", views.LabRequestListView.as_view(), name="lab_request_list"),
    path("requests/<int:pk>/", views.LabRequestDetailView.as_view(), name="lab_request_detail"),
    path("items/<int:pk>/result/", views.LabRequestItemUpdateView.as_view(), name="lab_item_result"),

    # --- Tests CRUD ---
    path("tests/", views.TestListView.as_view(), name="test_list"),
    path("tests/new/", views.TestCreateView.as_view(), name="test_add"),
    path("tests/<int:pk>/edit/", views.TestUpdateView.as_view(), name="test_edit"),
    path("tests/<int:pk>/delete/", views.TestDeleteView.as_view(), name="test_delete"),

    # --- TestGroups CRUD ---
    path("test-groups/", views.TestGroupListView.as_view(), name="testgroup_list"),
   #  path("test-groups/new/", views.TestGroupCreateView.as_view(), name="testgroup_add"),
    # path("test-groups/new/", views.TestGroupCreateView.as_view(), name="testgroup_add"),
    path("test-groups/create/", views.TestGroupCreateView.as_view(), name="testgroup_create"),  # ALIAS للاسم القديم
    path("test-groups/<int:pk>/edit/", views.TestGroupUpdateView.as_view(), name="testgroup_edit"),
    path("test-groups/<int:pk>/delete/", views.TestGroupDeleteView.as_view(), name="testgroup_delete"),

    # --- API: اختبارات المجموعة (لـ JS في شاشة الطلب) ---
     path("api/test-groups/<int:pk>/tests/", views.testgroup_tests_api, name="api_testgroup_tests"),

    # إنشاء طلب جديد لمريض
    path("lab-request/new/<int:patient_id>/", views.LabRequestCreateView.as_view(), name="lab_request_add"),

    # القوائم والتفاصيل
    path("requests/", views.LabRequestListView.as_view(), name="lab_request_list"),
    path("requests/<int:pk>/", views.LabRequestDetailView.as_view(), name="lab_request_detail"),

    # نتائج عنصر (تحليل واحد داخل الطلب)
    path("items/<int:pk>/result/", views.LabRequestItemUpdateView.as_view(), name="lab_item_result"),

    # مسح QR
    path("requests/scan/<uuid:token>/", views.lab_request_scan, name="lab_request_scan"),
    path("samples/scan/<uuid:token>/",  views.sample_scan,       name="sample_scan"),

      path("dashboard/", views.LabDashboardView.as_view(), name="dashboard"),

    # الموجود سابقًا:
    path("lab-request/new/<int:patient_id>/", views.LabRequestCreateView.as_view(), name="lab_request_add"),
    path("requests/", views.LabRequestListView.as_view(), name="lab_request_list"),
    path("requests/<int:pk>/", views.LabRequestDetailView.as_view(), name="lab_request_detail"),
    path("items/<int:pk>/result/", views.LabRequestItemUpdateView.as_view(), name="lab_item_result"),
    

    # (اختياري) لو عندك صفحات لإدارة التحاليل والمجموعات:
    path("tests/", views.TestListView.as_view(), name="test_list"),
     path("test-groups/", views.TestGroupListView.as_view(), name="testgroup_list"),


    # إنشاء أمر معمل قديم (Order):
    path("test-orders/add/<int:patient_id>/", views.testorder_add, name="testorder_add"), 

    
    # نتائج التحاليل
    path("test-results/", views.TestResultListView.as_view(), name="test_results_list"),

    path("test-orders/queue/", views.TestOrderQueueView.as_view(), name="testorder_queue"),



    path("requests/<int:pk>/", views.LabRequestDetailView.as_view(), name="lab_request_detail"),  # إضافة نتائج لأمر قديم
   

    path("requests/<int:request_id>/results/new/", views.add_results_for_request, name="add_results_for_request"),  # لو أضفت الفيو

     path(
        "patients/<int:patient_id>/results/",views.PatientLabResultsView.as_view(), name="patient_lab_results"),   # ← هذا هو الاسم المطلوب

     path(
    "patients/<int:patient_id>/results/print/",
    views.patient_lab_results_print,
    name="patient_lab_results_print",
),      

   # path("patients/<int:patient_id>/results/",
        # views.PatientResultsView.as_view(),
        # name="patient_results"),
  

  path("tests/", views.TestListView.as_view(), name="test_list"),
path("tests/new/", views.TestCreateView.as_view(), name="test_create"),
path("tests/<int:pk>/edit/", views.TestUpdateView.as_view(), name="test_update"),
path("tests/<int:pk>/delete/", views.TestDeleteView.as_view(), name="test_delete"),

path("test-groups/", views.TestGroupListView.as_view(), name="testgroup_list"),
path("test-groups/new/", views.TestGroupCreateView.as_view(), name="testgroup_create"),
path("test-groups/<int:pk>/edit/", views.TestGroupUpdateView.as_view(), name="testgroup_update"),
path("test-groups/<int:pk>/delete/", views.TestGroupDeleteView.as_view(), name="testgroup_delete"),
# laboratory/urls.py

    # طلبات المختبر
    path("lab-request/new/<int:patient_id>/", views.LabRequestCreateView.as_view(), name="lab_request_add"),
    path("requests/", views.LabRequestListView.as_view(), name="lab_request_list"),
    path("requests/<int:pk>/", views.LabRequestDetailView.as_view(), name="lab_request_detail"),
    path("items/<int:pk>/result/", views.LabRequestItemUpdateView.as_view(), name="lab_item_result"),

    # التحاليل (Tests)
    path("tests/", views.TestListView.as_view(), name="test_list"),
    path("tests/new/", views.TestCreateView.as_view(), name="test_create"),
    path("tests/new/", views.TestCreateView.as_view(), name="test_add"),  # alias للاسم القديم
    path("tests/<int:pk>/edit/", views.TestUpdateView.as_view(), name="test_update"),
    path("tests/<int:pk>/delete/", views.TestDeleteView.as_view(), name="test_delete"),

    # المجموعات (TestGroup)
    path("test-groups/", views.TestGroupListView.as_view(), name="testgroup_list"),
    path("test-groups/new/", views.TestGroupCreateView.as_view(), name="testgroup_create"),
    path("test-groups/new/", views.TestGroupCreateView.as_view(), name="testgroup_add"),  # alias للاسم المطلوب
    path("test-groups/<int:pk>/edit/", views.TestGroupUpdateView.as_view(), name="testgroup_update"),
    path("test-groups/<int:pk>/delete/", views.TestGroupDeleteView.as_view(), name="testgroup_delete"),

    # صفحات النتائج للمريض + طباعة
    path("patients/<int:patient_id>/results/", views.PatientLabResultsView.as_view(), name="patient_lab_results"),
    path("patients/<int:patient_id>/results/print/", views.patient_lab_results_print, name="patient_lab_results_print"),

    # مسح QR
    path("requests/scan/<uuid:token>/", views.lab_request_scan, name="lab_request_scan"),
    path("samples/scan/<uuid:token>/", views.sample_scan, name="sample_scan"),
]
    

