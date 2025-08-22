from django.contrib import messages
from django.views.generic import ListView, CreateView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import redirect
from django.urls import reverse_lazy

from manager.models import Patient, Admission, MedicalRecord, Appointment # type: ignore
from manager.forms import MedicalRecordForm, AppointmentForm # type: ignore
from hr.models import CustomUser


class StaffRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.role in ['doctor', 'nurse', 'receptionist', 'pharmacist']


class PatientListView(LoginRequiredMixin, StaffRequiredMixin, ListView):
    model = Patient
    template_name = 'patients/patient_list.html'
    context_object_name = 'patients'

    def get_queryset(self):
        return Patient.objects.filter(hospital=self.request.user.hospital)


class PatientDetailView(LoginRequiredMixin, StaffRequiredMixin, DetailView):
    model = Patient
    template_name = 'patients/patient_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        patient = self.get_object()
        context['admissions'] = Admission.objects.filter(patient=patient)
        context['medical_records'] = MedicalRecord.objects.filter(patient=patient)
        context['appointments'] = Appointment.objects.filter(patient=patient)
        return context


class MedicalRecordCreateView(LoginRequiredMixin, StaffRequiredMixin, CreateView):
    model = MedicalRecord
    form_class = MedicalRecordForm
    template_name = 'medical_records/medical_record_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['hospital'] = self.request.user.hospital
        return kwargs

    def form_valid(self, form):
        medical_record = form.save()
        messages.success(self.request, "Medical record created successfully.")
        return redirect('staff:patient_detail', pk=medical_record.patient.id)


class AppointmentCreateView(LoginRequiredMixin, StaffRequiredMixin, CreateView):
    model = Appointment
    form_class = AppointmentForm
    template_name = 'appointments/appointment_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['hospital'] = self.request.user.hospital
        return kwargs

    def form_valid(self, form):
        appointment = form.save()
        messages.success(self.request, "Appointment created successfully.")
        return redirect('staff:patient_detail', pk=appointment.patient.id)


# Simple redirect so staff namespace has a clinic_list URL
def clinic_list_redirect(request):
    return redirect('manager:clinic_list')


# Redirects to HR app for staff menu links
def leave_request_list_redirect(request):
    return redirect('hr:leave_request_list')


def shift_assignment_list_redirect(request):
    return redirect('hr:shift_assignment_list')


def shift_swap_request_list_redirect(request):
    return redirect('hr:shift_swap_request_list')