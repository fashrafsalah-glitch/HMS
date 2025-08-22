from django.urls import path
from .views import (
    PatientListView, PatientDetailView, MedicalRecordCreateView,
    AppointmentCreateView, clinic_list_redirect,
    leave_request_list_redirect, shift_assignment_list_redirect,
    shift_swap_request_list_redirect
)

app_name = 'staff'

urlpatterns = [
    path('patients/', PatientListView.as_view(), name='patient_list'),
    path('patients/<int:pk>/', PatientDetailView.as_view(), name='patient_detail'),
    path('medical-records/create/', MedicalRecordCreateView.as_view(), name='medical_record_create'),
    path('appointments/new/', AppointmentCreateView.as_view(), name='appointment_create'),
    # Provide staff:clinic_list used in base.html
    path('clinics/', clinic_list_redirect, name='clinic_list'),
    path('leave-requests/', leave_request_list_redirect, name='leave_request_list'),
    path('shifts/', shift_assignment_list_redirect, name='shift_assignment_list'),
    path('shift-swaps/', shift_swap_request_list_redirect, name='shift_swap_request_list'),
]