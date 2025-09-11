# manager/urls.py
from django.urls import include, path

from .views import MedicalRecordCreateView,  SurgicalOperationsDepartmentDeleteView, SurgicalOperationsDepartmentUpdateView, department_devices
from . import views  # ← هذا هو المطلوب
from . import views
from . import views_qr
from .views import patient_report_view
from .views import (
    VitalSignCreateView, VitalSignUpdateView, VitalSignListView, VitalSignDeleteView,
)


from .views import (
    # ─── core / patients ──────────────────────────────────────────
    ObsToObsCreateView, PatientListView, PatientCreateView, patient_edit, PatientDetailView,
    download_patient_pdf, download_qr_code, download_wristband,

    # admissions & transfers
    AdmissionListView, AdmissionCreateView, discharge_admission,
    transfer_create, AdmissionPrintView, admission_print, load_beds,

    # visits, diagnoses, prescriptions
    VisitListView, VisitCreateView, DiagnosisCreateView,
    PrescriptionCreateView, FollowUpCreateView,
    PrescriptionListView, PrescriptionDetailView, dispense_action,

    # appointments
    AppointmentListView, AppointmentCreateView,
    AppointmentUpdateView, AppointmentCancelView,

    # doctors
    DoctorListView, DoctorCreateView, DoctorUpdateView,
    DoctorDeleteView, DoctorDetailView,

    # infrastructure
    BedListView, BedCreateView, BedUpdateView, BedDeleteView, BedDetailView,
    BuildingListView, BuildingCreateView,
    FloorListView, FloorCreateView,
    WardListView, WardCreateView,
    RoomListView, RoomCreateView, RoomDetailView,
    ajax_load_floors, ajax_load_wards, ajax_load_rooms,

    # departments & clinics
    department_list, add_department, department_detail,
    edit_department, delete_department, department_tree,
    department_page, department_doctors, department_patients, department_staffs,
    department_beds, department_rooms,
    clinic_list, clinic_create,

    # ICD-11 autocomplete
    icd11_autocomplete,

    # medical record & PDF settings
    medical_record_print, pdf_settings,

    # extras
    MedicationListView, MedicationCreateView,
    ObservationFormCreateView, 
    FluidBalanceCreateView, ImmunizationCreateView,
    ProgramCreateView, FormCreateView, ProcedureCreateView,
    RadiologyOrderCreateView,

    # pharmacy request workflow
    PrescriptionRequestCreateView, PharmacyRequestListView,
    PharmacyRequestDetailView, pharmacy_request_pdf_download,
    pharmacy_request_scan,

    # emergency / surgical departments
    EmergencyDepartmentListView, EmergencyDepartmentCreateView,
    SurgicalOperationsDepartmentListView, SurgicalOperationsDepartmentCreateView,

    # user admin
    HRUserCreateView,
    patient_report_view,
)

app_name = "manager"

urlpatterns = [
    # ─── patients ────────────────────────────────────────────────
    path("",                     PatientListView.as_view(),  name="patient_list"),
    path("create/",              PatientCreateView.as_view(), name="patient_create"),
    path("<int:patient_id>/edit/", patient_edit,              name="patient_edit"),
    path("<int:pk>/",            PatientDetailView.as_view(), name="patient_detail"),

    # PDF / QR / wrist-band
    path("<int:patient_id>/pdf/",      download_patient_pdf,    name="patient_pdf"),
    path("<int:patient_id>/wristband/",download_wristband,      name="download_wristband"),
    path("<int:patient_id>/qrcode/",   download_qr_code,        name="download_qr_code"),

    # ─── admissions & transfers ─────────────────────────────────
    path("admissions/",                 AdmissionListView.as_view(), name="admission_list"),
    path("admissions/new/",             AdmissionCreateView.as_view(), name="admission_create"),
    path("admissions/<int:admission_id>/discharge/", discharge_admission, name="discharge_admission"),
    path("admissions/<int:admission_id>/transfer/",  transfer_create,     name="transfer_create"),
    path("admissions/<int:admission_id>/print/",     admission_print,     name="admission_print"),
    path("ajax/load-beds/",             load_beds,                        name="ajax_load_beds"),

    # ─── visits & diagnoses ─────────────────────────────────────
    path("visits/",            VisitListView.as_view(), name="visit_list"),
    path("visits/new/",        VisitCreateView.as_view(), name="visit_create"),

    # patient-specific diagnosis (FIX for NoReverseMatch)
    path("patients/<int:patient_id>/diagnoses/new/",
         DiagnosisCreateView.as_view(),
         name="diagnosis_create"),

    # visit-specific diagnosis
    path("visits/<int:visit_id>/diagnoses/new/",
         DiagnosisCreateView.as_view(),
         name="visit_diagnosis_create"),

    # prescriptions

    path("visits/<int:visit_id>/prescriptions/new/",
         PrescriptionCreateView.as_view(),
         name="visit_prescription_create"),

path(
    "patients/<int:patient_id>/prescriptions/new/",
    PrescriptionCreateView.as_view(),
    name="prescription_create"       
),

    path("prescriptions/list/",
         PrescriptionListView.as_view(),
         name="prescription_list"),
    path("prescriptions/<int:pk>/",
         PrescriptionDetailView.as_view(),
         name="prescription_detail"),
    path("prescriptions/<int:prescription_id>/followup/new/",
         FollowUpCreateView.as_view(),
         name="followup_create"),
    path("pharmacy/dispense/", dispense_action, name="dispense_action"),

    # ─── appointments ───────────────────────────────────────────
    path("appointments/",                 AppointmentListView.as_view(), name="appointment_list"),
    path("appointments/new/",             AppointmentCreateView.as_view(), name="appointment_create"),
    path("appointments/<int:pk>/edit/",   AppointmentUpdateView.as_view(), name="appointment_edit"),
    path("appointments/<int:pk>/cancel/", AppointmentCancelView.as_view(), name="appointment_cancel"),

    # ─── doctors ────────────────────────────────────────────────
    path("doctors/",                DoctorListView.as_view(),   name="doctor_list"),
    path("doctors/add/",            DoctorCreateView.as_view(), name="doctor_add"),
    path("doctors/<int:pk>/edit/",  DoctorUpdateView.as_view(), name="doctor_edit"),
    path("doctors/<int:pk>/delete/",DoctorDeleteView.as_view(), name="doctor_delete"),
    path("doctors/<int:pk>/",       DoctorDetailView.as_view(), name="doctor_detail"),

    # ─── infrastructure (buildings → beds) ──────────────────────
    path("buildings/",       BuildingListView.as_view(), name="building_list"),
    path("buildings/add/",   BuildingCreateView.as_view(), name="building_add"),

    path("floors/",          FloorListView.as_view(),    name="floor_list"),
    path("floors/add/",      FloorCreateView.as_view(),  name="floor_add"),

    path("wards/",           WardListView.as_view(),     name="ward_list"),
    path("wards/add/",       WardCreateView.as_view(),   name="ward_add"),

    path("rooms/",           RoomListView.as_view(),     name="room_list"),
    path("rooms/add/",       RoomCreateView.as_view(),   name="room_add"),
    path("rooms/<int:pk>/",  RoomDetailView.as_view(),   name="room_detail"),

    path("beds/",            BedListView.as_view(),      name="bed_list"),
    path("beds/add/",        BedCreateView.as_view(),    name="bed_add"),
    path("beds/<int:pk>/edit/",   BedUpdateView.as_view(), name="bed_edit"),
    path("beds/<int:pk>/delete/", BedDeleteView.as_view(), name="bed_delete"),
    path("generate-qr/<str:entity_type>/<int:entity_id>/", views_qr.generate_qr, name="generate_qr"),
    path("beds/<int:pk>/",        BedDetailView.as_view(), name="bed_detail"),

    # dependent-dropdown AJAX
    path("ajax/load-floors/", ajax_load_floors, name="ajax_load_floors"),
    path("ajax/load-wards/",  ajax_load_wards,  name="ajax_load_wards"),
    path("ajax/load-rooms/",  ajax_load_rooms,  name="ajax_load_rooms"),
    
    # API endpoints
    path("api/rooms/", views.rooms_api, name="rooms_api"),

    # ─── departments & clinics ──────────────────────────────────
    path("departments/",                department_list,          name="department_list"),
    
    path("departments/add/",            add_department,           name="department_add"),
    path("departments/tree/",           department_tree,          name="department_tree"),
    path("departments/<int:pk>/",       department_detail,        name="department_detail"),
    path("departments/<int:pk>/edit/",  edit_department,          name="department_edit"),
    path("departments/<int:pk>/delete/",delete_department,        name="department_delete"),
    # Unified combined page (keeps old name for reverse compatibility)
    path("departments/<int:department_id>/page/",      views.department_surgical_combined,      name="department_page"),
    path("departments/generate-qr/", views.generate_department_qr_codes, name="generate_department_qr_codes"),
    path("departments/<int:department_id>/download-qr/", views.download_department_qr, name="download_department_qr"),
    path("departments/<int:department_id>/doctors/",   department_doctors,   name="department_doctors"),
    path("departments/<int:department_id>/patients/",  department_patients,  name="department_patients"),
    path("departments/<int:department_id>/staffs/",  department_staffs,      name="department_staffs"),
    path("departments/<int:department_id>/beds/",      department_beds,      name="department_beds"),
    path("departments/<int:department_id>/rooms/",     department_rooms,     name="department_rooms"),
    path('departments/<int:department_id>/devices/',   department_devices, name='department_devices'),

    path("clinics/",         clinic_list,   name="clinic_list"),
    path("clinics/create/",  clinic_create, name="clinic_create"),

# ─── medical records, vitals, I&O, etc. ─────────────────────
path(
    "medical-records/create/",
    MedicalRecordCreateView.as_view(),
    name="medical_record_create",
),
path(
    "medical-records/create/<int:patient_id>/",
    MedicalRecordCreateView.as_view(),
    name="medical_record_create_with_patient",
),
path(
    "medical-records/print/",
    medical_record_print,
    name="medical_record_print",
),
    path('medical-records/<int:pk>/update/', views.MedicalRecordUpdateView.as_view(), name='medical_record_update'),
    path("medical-records/<int:pk>/", views.MedicalRecordDetailView.as_view(), name="medical_record_detail"),

    path("records/<int:record_id>/vitals/",     VitalSignListView.as_view(),   name="vitals_list"),
    path("records/<int:record_id>/vitals/new/", VitalSignCreateView.as_view(), name="vitals_create"),
    path("vitals/<int:pk>/edit/",               VitalSignUpdateView.as_view(), name="vitals_update"),
    path("vitals/<int:pk>/delete/",             VitalSignDeleteView.as_view(), name="vitals_delete"),

    path("fluid-balance/new/",   FluidBalanceCreateView.as_view(),    name="fluid_balance_create"),
    path("immunizations/new/",   ImmunizationCreateView.as_view(),    name="immunization_create"),
    path("programs/new/",        ProgramCreateView.as_view(),         name="program_create"),
    path("forms/new/",           FormCreateView.as_view(),            name="form_create"),
    path("procedures/new/",      ProcedureCreateView.as_view(),       name="procedure_create"),
    path("radiology-orders/new/",RadiologyOrderCreateView.as_view(),  name="radiology_order_create"),
    path("observation/new/",     ObservationFormCreateView.as_view(), name="observation_create"),
    path("obstoobs/new/", ObsToObsCreateView.as_view(), name="obstoobs_create"),

    
    # ─── medications & pharmacy requests ────────────────────────
    path("medications/",       MedicationListView.as_view(),  name="medication_list"),
    path("medications/new/",   MedicationCreateView.as_view(),name="medication_create"),

    path("requests/",                 PharmacyRequestListView.as_view(),   name="pharmacy_request_list"),
    path("requests/new/",             PrescriptionRequestCreateView.as_view(), name="pharmacy_request_new"),
    path("requests/<int:pk>/",        PharmacyRequestDetailView.as_view(), name="pharmacy_request_detail"),
    path("requests/<int:pk>/pdf/",    pharmacy_request_pdf_download,       name="pharmacy_request_pdf"),
    path("requests/scan/<uuid:token>/", pharmacy_request_scan,             name="pharmacy_request_scan"),

    # ─── emergency & surgical departments ───────────────────────
    path("emergency-departments/",      EmergencyDepartmentListView.as_view(),      name="emergency_department_list"),
    path("emergency-departments/new/",  EmergencyDepartmentCreateView.as_view(),    name="emergency_department_create"),
    # Point surgical operations list to combined page (no department header)
    path("surgical-operations/",        views.department_surgical_combined, name="surgical_operations_department_list"),
    path("surgical-operations/<int:pk>/", views.SurgicalOperationsDepartmentDetailView.as_view(), name="surgical_operations_department_detail"),
    path("surgical-operations/new/",    SurgicalOperationsDepartmentCreateView.as_view(), name="surgical_operations_department_create"),
    path(
        'surgical-operations/<int:pk>/edit/',
        SurgicalOperationsDepartmentUpdateView.as_view(),
        name='surgical_operations_department_edit'
    ),
    path('surgical-operations/<int:pk>/delete/', SurgicalOperationsDepartmentDeleteView.as_view(), name='surgical_operations_department_delete'),  # ← هذا هو المطلوب
    # ─── misc ───────────────────────────────────────────────────
    path("pdf-settings/",  pdf_settings,           name="pdf_settings"),
    path("ajax/icd11-autocomplete/", icd11_autocomplete, name="icd11_autocomplete"),

    # HR users
    path("hr-users/add/", HRUserCreateView.as_view(), name="hr_user_add"),



    path("patients/<int:patient_id>/pdf/", download_patient_pdf, name="patient_pdf"),

    
    path("<int:pk>/report/", views.patient_report_view, name="patient_report"),

    # إعدادات تقرير المريض
    path("patient-report-settings/", views.patient_report_settings, name="patient_report_settings"),
    
   
    
   path("", PatientListView.as_view(), name="patient_list"),     # ==> /patients/
   path("<int:pk>/", PatientDetailView.as_view(), name="patient_detail"),  # ==> /patients/1/

   # Step 3: Patient dashboard and search API
   path("<int:patient_id>/dashboard/", views.patient_dashboard, name="patient_dashboard"),
   path("api/patient-search/", views.patient_search_api, name="patient_search_api"),

   # path("patients/<int:pk>/lab-results/", 
     # include(("laboratory.patient_results_urls", "laboratory"), namespace="laboratory")),
   
     

]
