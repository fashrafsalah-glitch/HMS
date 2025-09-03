# manager/views.py
from datetime import datetime
import json
import re
# from unittest import TestResult        # ← still used in the context block

from laboratory.models import LabRequest
import wave
from django import forms
from django.views.generic import (
    ListView, CreateView, UpdateView, DeleteView, DetailView
)

from hr.models import CustomUser
from django.conf import settings
from django.views.generic import DetailView
from django.shortcuts import get_object_or_404
from .models import Patient, MedicalRecord

from django.db.models import Q

from .models import PDFSettings 
from . import views
from .models import   TestOrder, TestResult

from laboratory.models import LabRequest
from .forms import DispenseActionForm, FluidBalanceForm, ImmunizationForm, ObsToObsForm, PDFSettingsForm, PrescriptionRequestForm, PrescriptionRequestItemFormSet, VitalSignForm
from django.template.loader import render_to_string
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse, reverse_lazy
from django.db import transaction
# import pandas as pd # type: ignore - moved to function level to avoid loading during migrations
from django.views.decorators.http import require_GET
from django.utils.module_loading import import_string
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse, reverse_lazy
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.http import Http404, HttpResponse, HttpResponseRedirect, JsonResponse
from django.conf import settings
from django.template.loader import render_to_string
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.messages.views import SuccessMessageMixin   # ←  add this
from django.urls import reverse, reverse_lazy
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
# ──────────────────────────── 3rd‑party libs ────────────────────────────
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib import colors
from django.utils.decorators import method_decorator
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image as ReportLabImage
)
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
import qrcode
from PIL import Image, ImageDraw, ImageFont
import io
import os

from maintenance.models import Device, DeviceTransferRequest  # تأكد من المسار حسب تطبيقك
from manager.models import Department

import arabic_reshaper
from bidi.algorithm import get_display
from django.contrib.auth.decorators import login_required
from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session




from django.views.generic import DetailView
from django.shortcuts import get_object_or_404
from django.db import transaction
from .models import Patient, MedicalRecord

# ──────────────────────────── Project imports ────────────────────────────
# Forms
from .forms import (
    AdmissionForm, AppointmentForm, BacteriologyResultForm, BedForm,
    BuildingForm, ClinicForm, DepartmentForm, DiagnosisForm, DischargeForm,
    DoctorForm, EmergencyDepartmentForm, FloorForm, FollowUpForm, FormForm,
    MedicalRecordForm, MedicationForm, ObservationForm, PACSForm, PatientForm,
    PrescriptionForm, ProgramForm, RadiologyOrderForm, RoomForm,
    SurgicalOperationsDepartmentForm, TransferForm, VisitForm, WardForm,
    ProcedureForm
)

# Models  (NO ObservationForm here – that is a form, not a model)
from .models import (
    DispenseRecord, EmergencyDepartment, FluidBalance, Immunization, LabRequestForm, ObsToObs, Observation, PDFSettings, Patient, Admission,
    Department, Doctor, Bed, Building, Floor, PharmacyRequest, PrescriptionRequest, Sample,TestOrder, TestResult,
    SurgicalOperationsDepartment, TestOrder, VitalSign, Ward, Room, Clinic, Transfer,
    MedicalRecord, Appointment, Visit, Diagnosis, Medication, Prescription,
    FollowUp, RadiologyOrder, BacteriologyResult, PACS, Program, Form,
    Procedure, PrescriptionRequestItem
)
from django.shortcuts import render, get_object_or_404
from django.http import Http404
from .models import Patient, MedicalRecord, VitalSign

from superadmin.models import Hospital
from hr.models import CustomUser
from general import models  # used by a couple of list‑view filters
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from .models import Patient, PDFSettings

from django.shortcuts import render, get_object_or_404
from .models import Patient, MedicalRecord, PDFSettings

from .models import PatientReportSettings
from .forms import PatientReportSettingsForm

from django.apps import apps

@login_required
def patient_report_settings(request):
    """
    صفحة إعدادات تقرير المريض. تدعم ?hospital=<id> لضمان ضبط إعدادات نفس المستشفى.
    """
    hid = request.GET.get("hospital")
    if hid:
        hospital = get_object_or_404(Hospital, pk=hid)
    else:
        # الافتراضي: مستشفى المستخدم الحالي
        hospital = request.user.hospital

    prs, _ = PatientReportSettings.objects.get_or_create(hospital=hospital)

    if request.method == "POST":
        form = PatientReportSettingsForm(request.POST, instance=prs)
        if form.is_valid():
            form.save()
            messages.success(request, "Patient report settings saved.")
            # أعد التحميل مع hospital لضمان عدم ضياع السياق
            return redirect(f"{reverse('manager:patient_report_settings')}?hospital={hospital.id}")
    else:
        form = PatientReportSettingsForm(instance=prs)

    return render(
        request,
        "patient_report_settings/patient_report_settings_form.html",
        {"form": form, "hospital": hospital},
    )


@login_required
def patient_report_view(request, pk):
    """
    صفحة تقرير المريض. نقرأ الإعدادات والـ PDF من مستشفى (patient.hospital).
    """
    # تأكيد أن هذا المريض يتبع مستشفى المستخدم (سياسة أمان)
    patient = get_object_or_404(Patient, pk=pk, hospital=request.user.hospital)

    # اقرأ الإعدادات من مستشفى المريض
    prs, _ = PatientReportSettings.objects.get_or_create(hospital=patient.hospital)
    pdf_settings, _ = PDFSettings.objects.get_or_create(hospital=patient.hospital)

    # اختيار سجل واحد (اختياري عبر GET ?record=<id>)
    q_record_id = request.GET.get("record")
    record = None
    if q_record_id:
        record = MedicalRecord.objects.filter(id=q_record_id, patient=patient).first()

    # السجلات
    records = MedicalRecord.objects.filter(patient=patient).order_by("-created_at")
    if record:
        records = records.filter(id=record.id)

    ctx = {
        "patient": patient,
        "records": records,
        "record": record,
        "prs": prs,
        "pdf_settings": pdf_settings,
    }
    return render(request, "patients/patient_report.html", ctx)

class HospitalmanagerRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return (
            self.request.user.is_authenticated and
            (self.request.user.role == "hospital_manager" or self.request.user.is_superuser)
        )

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            messages.error(self.request, "Please log in to access this page.")
            return redirect(settings.LOGIN_URL)
        
        # Redirect doctors to staff patient list (only for patient-related pages)
        if (hasattr(self.request.user, 'role') and 
            self.request.user.role == 'doctor' and 
            'patient' in self.request.path.lower()):
            messages.info(self.request, "تم توجيهك لقائمة المرضى الخاصة بالطاقم الطبي")
            return redirect("staff:patient_list")
        
        messages.error(self.request, "You need hospital‑manager privileges to access this page.")
        return redirect("/")

class HRUserForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, label="Password")
    hospital = forms.ModelChoiceField(queryset=Hospital.objects.all(), required=True)

    class Meta:
        model = CustomUser
        fields = [
            "username", "email", "password", "hospital",
            "hire_date", "salary_base", "national_id"
        ]

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        user.role = "hr"
        if commit:
            user.save()
        return user

class HRUserCreateView(LoginRequiredMixin,
                       HospitalmanagerRequiredMixin,
                       CreateView):
    model = CustomUser
    form_class = HRUserForm
    template_name = "users/hr_user_form.html"
    success_url = reverse_lazy("manager:patient_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["initial"]["hospital"] = self.request.user.hospital
        return kwargs

    def form_valid(self, form):
        if form.cleaned_data["hospital"] != self.request.user.hospital:
            form.add_error("hospital", "You can only create HR users for your own hospital.")
            return self.form_invalid(form)
        messages.success(self.request, "HR user created successfully.")
        return super().form_valid(form)

# Patient Views
class PatientListView(LoginRequiredMixin,
                      HospitalmanagerRequiredMixin,
                      ListView):
    model = Patient
    template_name = "patients/patient_list.html"
    context_object_name = "patients"

    def get_queryset(self):
        if not self.request.user.hospital:
            raise Http404("User is not associated with a hospital.")
        return Patient.objects.filter(hospital=self.request.user.hospital)

class PatientDetailView(LoginRequiredMixin,
                        HospitalmanagerRequiredMixin,
                        DetailView):
    model               = Patient
    template_name       = "patients/patient_detail.html"
    context_object_name = "patient"

    def get_queryset(self):
        return Patient.objects.filter(hospital=self.request.user.hospital)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        patient = self.object

        # اختر السجل الحالي: الأحدث (بالـ id تنازليًا). عدّل المعيار إذا شئت.
        qs = MedicalRecord.objects.filter(patient=patient).order_by("-id")
        record = qs.first()

        # إن لم يوجد أي سجل، أنشئ واحدًا (أضف الحقول الإلزامية إن وُجدت في نموذجك)
        if record is None:
            defaults = {}
            if hasattr(MedicalRecord, "hospital") and hasattr(self.request.user, "hospital"):
                defaults["hospital"] = self.request.user.hospital
            if hasattr(MedicalRecord, "created_by"):
                defaults["created_by"] = self.request.user
            record = MedicalRecord.objects.create(patient=patient, **defaults)

        ctx["record"] = record                 # السجل الذي تستخدمه الروابط {% url 'manager:vitals_create' record_id=record.id %}
        ctx["medical_records"] = qs            # لجدول الـ Flow Sheet
        ctx["vitals"] = record.vitals.order_by("-taken_at")
        return ctx

        # ── pull all records just once, order oldest→newest ───────────────
        medrecs = list(
            MedicalRecord.objects
            .filter(patient=patient)
            .order_by("created_at")
        )

        # ── build “allergy → earliest date” map ───────────────────────────
        allergy_dates: dict[str, datetime] = {}
        splitter = re.compile(r"[,;\n]+")
        for rec in medrecs:
            for field in (rec.allergies, rec.allergic_history):
                if not field:
                    continue
                for raw in splitter.split(field):
                    name = raw.strip()
                    if name and name not in allergy_dates:
                        allergy_dates[name] = rec.created_at

        # keep insertion order (Python 3.7+ dicts do)
        ctx["allergies"] = [
            (name, allergy_dates[name]) for name in allergy_dates
        ]

        # ── everything else stays exactly as before ───────────────────────
        ctx.update({
            "admissions":         Admission.objects.filter(patient=patient),
            "medical_records":    medrecs,                       # reuse list
            "appointments":       Appointment.objects.filter(patient=patient),
            "samples":            Sample.objects.filter(test_order__patient=patient),
            "visits":             Visit.objects.filter(patient=patient),
            "test_orders":        TestOrder.objects.filter(patient=patient),
            "test_results":       TestResult.objects.filter(test_order__patient=patient),
            "samples":            Sample.objects.filter(test_order__patient=patient),
            "diagnoses":          Diagnosis.objects.filter(patient=patient),
            "prescriptions":      Prescription.objects.filter(patient=patient),
            "radiology_orders":   RadiologyOrder.objects.filter(patient=patient),
            "bacteriology_results": BacteriologyResult.objects.filter(patient=patient),
            "pacs_records":       PACS.objects.filter(patient=patient),
            "programs":           Program.objects.filter(patient=patient),
            "forms":              Form.objects.filter(patient=patient),
            "observation_forms":  Observation.objects.filter(patient=patient),
            "procedures":         Procedure.objects.filter(patient=patient),

            "vitals": VitalSign.objects.filter(
                medical_record__patient=patient
            ).order_by("-taken_at"),

            "fluid_balances": FluidBalance.objects.filter(
                medical_record__patient=patient
            ).order_by("-recorded_at"),
        })
        return ctx

class PrescriptionDetailView(LoginRequiredMixin, HospitalmanagerRequiredMixin, DetailView):
    model = Prescription
    template_name = "pharmacy/prescription_detail.html"
    context_object_name = "prescription"

    def get_queryset(self):
        # restrict to your hospital's patients
        return Prescription.objects.filter(patient__hospital=self.request.user.hospital)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["dispense_history"] = self.object.dispense_history.all()
        return ctx

class PrescriptionListView(LoginRequiredMixin, HospitalmanagerRequiredMixin, ListView):
    model = Prescription
    template_name = 'pharmacy/prescription_list.html'
    context_object_name = 'prescriptions'

    def get_queryset(self):
        # only show prescriptions for patients in your hospital
        return Prescription.objects.filter(patient__hospital=self.request.user.hospital)

@login_required
def dispense_action(request):
    """
    Scan patient + prescription barcodes, record a DispenseRecord and update Rx status.
    """
    if request.method == "POST":
        form = DispenseActionForm(request.POST)
        if form.is_valid():
            pcode = form.cleaned_data["prescription_barcode"]
            patcode = form.cleaned_data["patient_barcode"]
            action = form.cleaned_data["action"]

            # find prescription
            try:
                rx = Prescription.objects.get(barcode=pcode)
            except Prescription.DoesNotExist:
                form.add_error("prescription_barcode", "No matching prescription found.")
                return render(request, "pharmacy/dispense_form.html", {"form": form})

            # verify patient wristband matches
            wrist = getattr(rx.patient, "barcode", None) or str(rx.patient.mrn)
            if patcode != wrist:
                form.add_error("patient_barcode", "Patient barcode does not match this prescription.")
                return render(request, "pharmacy/dispense_form.html", {"form": form})

            # record the action
            DispenseRecord.objects.create(
                prescription=rx,
                action=action,
                performed_by=request.user,
                patient_barcode_scanned=True,
                medication_barcode_scanned=True
            )
            # update prescription status
            rx.status = action
            rx.save(update_fields=["status"])
            messages.success(request, f"{rx.get_status_display()} recorded.")
            return redirect(reverse("manager:prescription_detail", args=[rx.pk]))
    else:
        form = DispenseActionForm()

    return render(request, "pharmacy/dispense_form.html", {"form": form})

class PatientCreateView(LoginRequiredMixin,
                        HospitalmanagerRequiredMixin,
                        CreateView):
    model         = Patient
    form_class    = PatientForm
    template_name = "patients/patient_form.html"
    success_url   = reverse_lazy("manager:patient_list")

    def form_valid(self, form):
        """
        Save the patient ➜ ensure an “OPD” department exists ➜
        create an active out-patient visit.
        """
        patient = form.save(commit=False)
        patient.hospital = self.request.user.hospital

        try:
            with transaction.atomic():
                # ① save the new patient row
                patient.save()

                # ② make sure this hospital has an OPD department
                opd_dept, _ = Department.objects.get_or_create(
                    name="OPD",
                    hospital=self.request.user.hospital,
                    defaults={
                        "department_type": "department",   # or "unit" as you prefer
                        "is_active": True,
                    },
                )

                # ③ create the initial OPD (out-patient) visit
                Visit.objects.create(
                    patient    = patient,
                    hospital   = self.request.user.hospital,
                    department = opd_dept,
                    visit_type = "outpatient",
                    visit_date = timezone.now(),
                    status     = "active",
                )

        except Exception as exc:
            # roll back + show an error near the top of the form
            form.add_error(None, f"Error creating patient/visit: {exc}")
            return self.form_invalid(form)

        messages.success(
            self.request,
            f"Patient {patient.first_name} {patient.last_name} created and added to OPD."
        )
        return super().form_valid(form)


def patient_edit(request, patient_id):
    patient = get_object_or_404(
        Patient, id=patient_id, hospital=request.user.hospital
    )
    if request.method == "POST":
        form = PatientForm(request.POST, request.FILES, instance=patient)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                f"Patient {patient.first_name} {patient.last_name} updated successfully."
            )
            return redirect("manager:patient_list")
    else:
        form = PatientForm(instance=patient)
    return render(
        request, "patients/patient_form.html",
        {"form": form, "patient": patient, "is_edit": True}
    )

# Admission Views
class AdmissionListView(LoginRequiredMixin, HospitalmanagerRequiredMixin, ListView):
    model = Admission
    template_name = 'admissions/admission_list.html'
    context_object_name = 'admissions'

    def get_queryset(self):
        return Admission.objects.filter(patient__hospital=self.request.user.hospital)

class AdmissionCreateView(LoginRequiredMixin,
                           HospitalmanagerRequiredMixin,
                           CreateView):
    model = Admission
    form_class = AdmissionForm
    template_name = "admissions/admission_form.html"
    success_url = reverse_lazy("manager:admission_list")

    # ---------------- helper setters ----------------
    def get_initial(self):
        initial = super().get_initial()
        pid = self.request.GET.get("patient")
        if pid:
            initial["patient"] = pid
        return initial

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["hospital"] = self.request.user.hospital
        return kwargs

    # ---------------- main logic (NOW ATOMIC) -------
    def form_valid(self, form):
        """
        Admit the patient **only if** the chosen bed is still free.
        The bed row is locked until the transaction ends, so two
        concurrent requests can't grab the same bed.
        """
        with transaction.atomic():
            admission = form.save(commit=False)

            if not admission.bed_id:                      # safety net
                form.add_error("bed", "You must choose a bed.")
                return self.form_invalid(form)

            # Lock that bed row
            bed = (
                Bed.objects
                .select_for_update()
                .get(pk=admission.bed_id)
            )

            if bed.status != "available":
                form.add_error("bed", "This bed is no longer available.")
                return self.form_invalid(form)

            bed.status = "occupied"
            bed.save(update_fields=["status"])
            admission.save()

        messages.success(
            self.request,
            f"Medical team notified for admission of {admission.patient}."
        )
        return super().form_valid(form)
# ────────────────────────────────────────────────────────────────────────


# ── Discharge view (function) ───────────────────────────────────────────
def discharge_admission(request, admission_id):
    admission = get_object_or_404(
        Admission,
        id=admission_id,
        patient__hospital=request.user.hospital
    )

    if request.method == "POST":
        form = DischargeForm(request.POST, instance=admission)
        if form.is_valid():
            with transaction.atomic():
                admission = form.save(commit=False)

                if admission.discharge_date is None:
                    admission.discharge_date = timezone.now()

                if admission.bed_id:                      # lock & free bed
                    bed = (
                        Bed.objects
                        .select_for_update()
                        .get(pk=admission.bed_id)
                    )
                    bed.status = "available"
                    bed.save(update_fields=["status"])

                admission.save()

            messages.success(
                request,
                "Financial system updated and insurance notified."
            )
            if "schedule_follow_up" in request.POST:
                return redirect(
                    "manager:appointment_create",
                    patient_id=admission.patient.id
                )
            return redirect("manager:admission_list")
    else:
        form = DischargeForm(instance=admission)

    return render(
        request,
        "admissions/discharge_form.html",
        {"form": form, "admission": admission}
    )
# ────────────────────────────────────────────────────────────────────────


# ── Transfer view (function) ────────────────────────────────────────────
def transfer_create(request, admission_id):
    admission = get_object_or_404(
        Admission,
        id=admission_id,
        patient__hospital=request.user.hospital
    )

    if request.method == "POST":
        form = TransferForm(request.POST, request.FILES, hospital=request.user.hospital)
        form.instance.admission = admission

        if form.is_valid():
            with transaction.atomic():
                transfer = form.save(commit=False)
                transfer.admission        = admission
                transfer.from_department  = admission.department

                # ---------- INTERNAL TRANSFER ----------
                if transfer.transfer_type == "internal":
                    transfer.to_hospital = None

                    # release current bed
                    if admission.bed_id:
                        old_bed = (
                            Bed.objects
                            .select_for_update()
                            .get(pk=admission.bed_id)
                        )
                        old_bed.status = "available"
                        old_bed.save(update_fields=["status"])

                    # move to new department / bed
                    if transfer.to_department:
                        admission.department = transfer.to_department
                    if transfer.new_bed_id:
                        new_bed = (
                            Bed.objects
                            .select_for_update()
                            .get(pk=transfer.new_bed_id)
                        )
                        if new_bed.status != "available":
                            form.add_error("new_bed", "Selected bed is no longer free.")
                            return render(
                                request,
                                "admissions/transfer_form.html",
                                {"form": form, "admission": admission}
                            )
                        new_bed.status = "occupied"
                        new_bed.save(update_fields=["status"])
                        admission.bed = new_bed
                    else:
                        admission.bed = None

                # ---------- EXTERNAL TRANSFER ----------
                elif transfer.transfer_type == "external":
                    transfer.to_department = None
                    transfer.new_bed       = None

                    if admission.bed_id:
                        old_bed = (
                            Bed.objects
                            .select_for_update()
                            .get(pk=admission.bed_id)
                        )
                        old_bed.status = "available"
                        old_bed.save(update_fields=["status"])
                    admission.bed = None

                transfer.save()
                admission.save()

            messages.success(request, "تم نقل المريض بنجاح.")
            return redirect("manager:admission_list")

    else:
        form = TransferForm(hospital=request.user.hospital)

    return render(
        request,
        "admissions/transfer_form.html",
        {"form": form, "admission": admission}
    )

def load_beds(request):
    department_id = request.GET.get('department')
    beds = Bed.objects.filter(department_id=department_id, department__hospital=request.user.hospital, status='available')
    return JsonResponse(list(beds.values('id', 'bed_number')), safe=False)

# Doctor Views
class DoctorListView(LoginRequiredMixin, HospitalmanagerRequiredMixin, ListView):
    model = Doctor
    template_name = 'doctors/doctor_list.html'
    context_object_name = 'doctors'

    def get_queryset(self):
        return Doctor.objects.filter(departments__hospital=self.request.user.hospital)

class AdmissionPrintView(LoginRequiredMixin, HospitalmanagerRequiredMixin, DetailView):
    model = Admission
    template_name = 'admissions/admission_print.html'
    context_object_name = 'admission'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['hospital'] = self.request.user.hospital
        context['clerk'] = self.request.user
        return context

def admission_print(request, admission_id):
    admission = get_object_or_404(Admission, id=admission_id)
    patient = admission.patient
    hospital = patient.hospital
    doctor = admission.treating_doctor
    bed = admission.bed if admission.bed else None

    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # Check primary font path
    font_path = '/Users/ye/Downloads/HMS/Janna LT Bold.ttf'
    # Alternative paths - check in order
    alt_paths = [
        os.path.join(settings.BASE_DIR, 'Janna LT Bold.ttf'),
        os.path.join(settings.BASE_DIR, 'static', 'fonts', 'JannaLTBold.ttf')
    ]
    
    # Try the primary path first
    if os.path.exists(font_path):
        pdfmetrics.registerFont(TTFont('Arabic', font_path))
    else:
        # Try alternative paths
        font_registered = False
        for alt_path in alt_paths:
            if os.path.exists(alt_path):
                pdfmetrics.registerFont(TTFont('Arabic', alt_path))
                font_registered = True
                break
        
        # If no font found, use a default font
        if not font_registered:
            # Use a standard font if Arabic font is not available
            pdfmetrics.registerFont(TTFont('Arabic', 'Helvetica'))

    def prepare_arabic_text(text):
        if not text:
            return ""
        reshaped_text = arabic_reshaper.reshape(str(text))
        return get_display(reshaped_text)

    qr = qrcode.QRCode(version=1, box_size=10, border=1)
    qr.add_data(f"Admission ID: {admission_id}, Patient MRN: {patient.mrn}")
    qr.make(fit=True)
    qr_img = qr.make_image(fill='black', back_color='white')
    qr_buffer = io.BytesIO()
    qr_img.save(qr_buffer, format="PNG")
    qr_buffer.seek(0)
    qr_image = ImageReader(qr_buffer)

    p.drawImage(qr_image, 50, 700, width=80, height=80)
    p.setFont("Arabic", 14)
    title = prepare_arabic_text("جواب دخول")
    p.drawString(150, 750, title)

    p.setFont("Arabic", 10)
    hospital_line = prepare_arabic_text(f"اسم المستشفي: {hospital.name}")
    p.drawString(150, 730, hospital_line)
    address = hospital.address if hasattr(hospital, 'address') else "غير متوفر"
    address_line = prepare_arabic_text(f"عنوان: {address}")
    p.drawString(150, 710, address_line)
    admission_id_line = prepare_arabic_text(f"رقم القبول: {admission_id}")
    p.drawString(150, 690, admission_id_line)
    date_line = prepare_arabic_text(f"التاريخ: {admission.admission_date.strftime('%Y/%m/%d')}")
    p.drawString(150, 670, date_line)

    y_position = 650
    data = [
        [prepare_arabic_text("ت"), prepare_arabic_text("رقم السرير"), prepare_arabic_text("أم السرير"), 
         prepare_arabic_text("الوحدة"), prepare_arabic_text("الدور"), prepare_arabic_text("القسم")],
        ["1", prepare_arabic_text(bed.bed_number if bed else "غير متوفر"), 
         prepare_arabic_text(bed.get_bed_type_display() if bed else "غير متوفر"), 
         prepare_arabic_text(bed.ward.name if bed else "غير متوفر"), 
         str(bed.floor.floor_number) if bed else "غير متوفر", 
         prepare_arabic_text(admission.department.name if admission.department else "غير متوفر")],
        ["2", "", "", "", "", ""],
        ["3", "", "", "", "", ""],
        ["4", "", "", "", "", ""],
    ]
    table = Table(data, colWidths=[0.5*inch, 1*inch, 1*inch, 1.5*inch, 1*inch, 1.5*inch])
    table.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, -1), 'Arabic', 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
    ]))
    table.wrapOn(p, width, height)
    table.drawOn(p, 50, y_position - len(data) * 25)

    y_position -= (len(data) * 25 + 40)
    age = patient.age
    initial_diagnosis = "غير متوفر"
    if hasattr(admission, 'diagnosis_set') and admission.diagnosis_set.exists():
        initial_diagnosis = admission.diagnosis_set.first().name
    physician_name = doctor.user.full_name if doctor else 'غير متوفر'
    clerk_name = request.user.full_name if hasattr(request.user, 'full_name') else 'غير متوفر'

    patient_data = [
        [prepare_arabic_text("السجل الطبي"), prepare_arabic_text(patient.mrn)],
        [prepare_arabic_text("الاسم الكامل"), prepare_arabic_text(f"{patient.first_name} {patient.last_name}")],
        [prepare_arabic_text("الجنس"), prepare_arabic_text(patient.get_gender_display())],
        [prepare_arabic_text("العمر"), prepare_arabic_text(f"{age['years']} سنة، {age['months']} شهر، {age['days']} يوم")],
        [prepare_arabic_text("سبب القبول"), prepare_arabic_text(admission.reason_for_admission or 'غير متوفر')],
        [prepare_arabic_text("التشخيص الأولي"), prepare_arabic_text(initial_diagnosis)],
        [prepare_arabic_text("الطبيب المعالج"), prepare_arabic_text(physician_name)],
        [prepare_arabic_text("وقت القبول"), prepare_arabic_text(admission.admission_date.strftime('%Y-%m-%d %H:%M:%S'))],
        [prepare_arabic_text("موظف المعلومات"), prepare_arabic_text(clerk_name)],
    ]
    patient_table = Table(patient_data, colWidths=[2*inch, 4*inch])
    patient_table.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, -1), 'Arabic', 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.black),
        ('LEFTPADDING', (1, 0), (1, -1), 10),
    ]))
    patient_table.wrapOn(p, width, height)
    patient_table.drawOn(p, 50, y_position - len(patient_data) * 25)

    y_position -= (len(patient_data) * 25 + 40)
    p.setFont("Arabic", 10)
    p.drawString(50, y_position, prepare_arabic_text("رخص مكتب القبول: ___________________"))
    p.drawString(300, y_position, prepare_arabic_text("رخص أمين وحدة القبول: ___________________"))

    p.showPage()
    p.save()

    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="admission_{admission_id}.pdf"'
    return response

class DoctorCreateView(LoginRequiredMixin, HospitalmanagerRequiredMixin, CreateView):
    model = Doctor
    form_class = DoctorForm
    template_name = 'doctors/doctor_form.html'
    success_url = reverse_lazy('manager:doctor_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['hospital'] = self.request.user.hospital
        return kwargs

    def form_valid(self, form):
        doctor = form.save()
        messages.success(self.request, "Doctor assigned successfully.")
        return super().form_valid(form)

class DoctorUpdateView(LoginRequiredMixin, HospitalmanagerRequiredMixin, UpdateView):
    model = Doctor
    form_class = DoctorForm
    template_name = 'doctors/doctor_form.html'
    success_url = reverse_lazy('manager:doctor_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['hospital'] = self.request.user.hospital
        return kwargs

    def get_queryset(self):
        return Doctor.objects.filter(departments__hospital=self.request.user.hospital)

class DoctorDeleteView(LoginRequiredMixin, HospitalmanagerRequiredMixin, DeleteView):
    model = Doctor
    template_name = 'doctors/doctor_confirm_delete.html'
    success_url = reverse_lazy('manager:doctor_list')

    def get_queryset(self):
        return Doctor.objects.filter(departments__hospital=self.request.user.hospital)

class DoctorDetailView(LoginRequiredMixin, HospitalmanagerRequiredMixin, DetailView):
    model = Doctor
    template_name = 'doctors/doctor_detail.html'

    def get_queryset(self):
        return Doctor.objects.filter(departments__hospital=self.request.user.hospital)

# Infrastructure Views
class BuildingListView(LoginRequiredMixin, HospitalmanagerRequiredMixin, ListView):
    model = Building
    template_name = 'buildings/building_list.html'
    context_object_name = 'buildings'

    def get_queryset(self):
        return Building.objects.filter(hospital=self.request.user.hospital)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['hospital_id'] = self.request.user.hospital.id
        return context

class BuildingCreateView(LoginRequiredMixin, HospitalmanagerRequiredMixin, CreateView):
    model = Building
    form_class = BuildingForm
    template_name = 'buildings/building_form.html'
    success_url = reverse_lazy('manager:building_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['hospital'] = self.request.user.hospital
        return kwargs

    def form_valid(self, form):
        form.instance.hospital = self.request.user.hospital
        messages.success(self.request, "Building created successfully.")
        return super().form_valid(form)

class FloorListView(LoginRequiredMixin, HospitalmanagerRequiredMixin, ListView):
    model = Floor
    template_name = 'floors/floor_list.html'
    context_object_name = 'floors'

    def get_queryset(self):
        if not self.request.user.hospital:
            raise Http404("User is not associated with a hospital.")
        return Floor.objects.filter(building__hospital=self.request.user.hospital)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['hospital_id'] = self.request.user.hospital.id
        return context

class FloorCreateView(LoginRequiredMixin, HospitalmanagerRequiredMixin, CreateView):
    model = Floor
    form_class = FloorForm
    template_name = 'floors/floor_form.html'
    success_url = reverse_lazy('manager:floor_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['hospital'] = self.request.user.hospital
        return kwargs

class WardListView(LoginRequiredMixin, HospitalmanagerRequiredMixin, ListView):
    model = Ward
    template_name = 'wards/ward_list.html'
    context_object_name = 'wards'

    def get_queryset(self):
        if not self.request.user.hospital:
            raise Http404("User is not associated with a hospital.")
        return Ward.objects.filter(floor__building__hospital=self.request.user.hospital)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['hospital_id'] = self.request.user.hospital.id
        return context

class WardCreateView(LoginRequiredMixin, HospitalmanagerRequiredMixin, CreateView):
    model = Ward
    form_class = WardForm
    template_name = 'wards/ward_form.html'
    success_url = reverse_lazy('manager:ward_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['hospital'] = self.request.user.hospital
        return kwargs

class RoomListView(LoginRequiredMixin, HospitalmanagerRequiredMixin, ListView):
    model = Room
    template_name = 'rooms/room_list.html'
    context_object_name = 'rooms'

    def get_queryset(self):
        if not self.request.user.hospital:
            raise Http404("User is not associated with a hospital.")
        return Room.objects.filter(ward__floor__building__hospital=self.request.user.hospital)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['hospital_id'] = self.request.user.hospital.id
        return context

class RoomCreateView(LoginRequiredMixin, HospitalmanagerRequiredMixin, CreateView):
    model = Room
    form_class = RoomForm
    template_name = 'rooms/room_form.html'
    success_url = reverse_lazy('manager:room_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['hospital'] = self.request.user.hospital
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['hospital_id'] = self.request.user.hospital.id
        return context

class RoomDetailView(LoginRequiredMixin, HospitalmanagerRequiredMixin, DetailView):
    model = Room
    template_name = 'rooms/room_detail.html'
    context_object_name = 'room'

    def get_queryset(self):
        if not self.request.user.hospital:
            raise Http404("User is not associated with a hospital.")
        return Room.objects.filter(ward__floor__building__hospital=self.request.user.hospital)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        room = self.get_object()
        
        # Get beds in this room
        context['beds'] = room.beds.all()
        
        # Get devices in this room
        from maintenance.models import Device
        context['devices'] = Device.objects.filter(room=room)
        
        return context

class BedListView(LoginRequiredMixin, HospitalmanagerRequiredMixin, ListView):
    model = Bed
    template_name = 'beds/bed_list.html'
    context_object_name = 'beds'

    def get_queryset(self):
        return Bed.objects.filter(room__ward__floor__building__hospital=self.request.user.hospital)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['hospital_id'] = self.request.user.hospital.id
        return context

class BedCreateView(LoginRequiredMixin, HospitalmanagerRequiredMixin, CreateView):
    model = Bed
    form_class = BedForm
    template_name = 'beds/bed_form.html'
    success_url = reverse_lazy('manager:bed_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['hospital'] = self.request.user.hospital
        return kwargs

    def form_valid(self, form):
        bed = form.save()
        messages.success(self.request, "Bed created successfully.")
        return super().form_valid(form)

class BedUpdateView(LoginRequiredMixin, HospitalmanagerRequiredMixin, UpdateView):
    model = Bed
    form_class = BedForm
    template_name = 'beds/bed_form.html'
    success_url = reverse_lazy('manager:bed_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['hospital'] = self.request.user.hospital
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        bed = self.get_object()
        initial['building'] = bed.room.ward.floor.building.id if bed.room.ward.floor.building else None
        initial['floor'] = bed.room.ward.floor.id if bed.room.ward.floor else None
        initial['ward'] = bed.room.ward.id if bed.room.ward else None
        initial['room'] = str(bed.room.id) if bed.room else None
        return initial

    def get_queryset(self):
        return Bed.objects.filter(room__ward__floor__building__hospital=self.request.user.hospital)

class BedDeleteView(LoginRequiredMixin, HospitalmanagerRequiredMixin, DeleteView):
    model = Bed
    template_name = "beds/delete_bed.html"
    success_url = reverse_lazy('manager:bed_list')

    def get_queryset(self):
        return Bed.objects.filter(room__ward__floor__building__hospital=self.request.user.hospital)

class BedDeleteView(DeleteView):
    model = Bed
    template_name = "beds/delete_bed.html"  # ← هذا يطابق اسم الملف الذي أنشأته
    
    def get_success_url(self):
        return reverse_lazy('manager:department_beds', kwargs={'department_id': self.object.room.department.id})

class BedDetailView(LoginRequiredMixin, HospitalmanagerRequiredMixin, DetailView):
    model = Bed
    template_name = 'infrastructure/bed_detail.html'

    def get_queryset(self):
        return Bed.objects.filter(room__ward__floor__building__hospital=self.request.user.hospital)

# AJAX Views for Infrastructure
def ajax_load_floors(request):
    building_id = request.GET.get('building_id')
    floors = Floor.objects.filter(building_id=building_id)
    options = ''.join([f'<option value="{floor.id}">{floor.name}</option>' for floor in floors])
    return JsonResponse({'options': options})

def ajax_load_wards(request):
    floor_id = request.GET.get('floor_id')
    wards = Ward.objects.filter(floor_id=floor_id)
    options = ''.join([f'<option value="{ward.id}">{ward.name}</option>' for ward in wards])
    return JsonResponse({'options': options})

def ajax_load_rooms(request):
    ward_id = request.GET.get('ward_id')
    rooms = Room.objects.filter(ward_id=ward_id)
    options = ''.join([f'<option value="{room.id}">{room.number}</option>' for room in rooms])
    return JsonResponse({'options': options})

def rooms_api(request):
    """API endpoint for rooms filtered by department"""
    department_id = request.GET.get('department')
    if department_id:
        rooms = Room.objects.filter(department_id=department_id)
        room_data = []
        for room in rooms:
            room_data.append({
                'id': room.id,
                'number': room.number,
                'room_type': room.room_type,
                'get_room_type_display': room.get_room_type_display()
            })
        return JsonResponse(room_data, safe=False)
    else:
        rooms = Room.objects.all()
        room_data = []
        for room in rooms:
            room_data.append({
                'id': room.id,
                'number': room.number,
                'room_type': room.room_type,
                'get_room_type_display': room.get_room_type_display()
            })
        return JsonResponse(room_data, safe=False)

# Department Views
def department_list(request):
    departments = Department.objects.filter(hospital=request.user.hospital)
    return render(request, 'departments/department_list.html', {'departments': departments})

def department_page(request, department_id):
    department = get_object_or_404(Department, id=department_id, hospital=request.user.hospital)
    return render(request, 'departments/department_page.html', {'department': department})

def department_rooms(request, department_id):
    department = get_object_or_404(Department, id=department_id, hospital=request.user.hospital)
    rooms = Room.objects.filter(department=department)
    return render(request, 'rooms/room_list.html', {'rooms': rooms, 'department': department})

def department_doctors(request, department_id):
    department = get_object_or_404(Department, id=department_id, hospital=request.user.hospital)
    doctors = Doctor.objects.filter(departments=department)
    return render(request, 'doctors/doctor_list.html', {'doctors': doctors})

def department_patients(request, department_id):
    department = get_object_or_404(Department, id=department_id, hospital=request.user.hospital)
    patients = Patient.objects.filter(admission__department=department).distinct()
    return render(request, 'patients/patient_list.html', {'patients': patients})

def department_staffs(request, department_id):
    department = get_object_or_404(Department, id=department_id, hospital=request.user.hospital)

    # فلترة الدور فقط
    role = request.GET.get('role')
    staffs = CustomUser.objects.filter(departments=department)
    if role:
        staffs = staffs.filter(role=role)

    return render(request, 'staff/staff_list.html', {
        'staff': staffs,
        'roles': CustomUser.objects.values_list('role', flat=True).distinct(),
        'is_department_view': True,
        'selected_department': department,  # لتظهر اسم القسم
    })

def department_beds(request, department_id): 
    department = get_object_or_404(Department, id=department_id, hospital=request.user.hospital)

    beds = Bed.objects.filter(room__department=department)

    return render(request, 'beds/bed_list.html', {
        'beds': beds,
        'department': department,
    })

def department_devices(request, department_id):
    department = get_object_or_404(Department, id=department_id)

    # عرض جميع الأجهزة في القسم حتى لو كان لها طلبات نقل معلقة
    actual_devices = Device.objects.filter(department=department)
    
    # حساب طلبات النقل للإحصائيات فقط
    pending_transfers = DeviceTransferRequest.objects.filter(
        device__department=department,
        status__in=['pending', 'approved']
    ).select_related('device')
    
    # طلبات النقل الصادرة من هذا القسم (فقط المعلقة وغير المكتملة)
    outgoing_transfers = DeviceTransferRequest.objects.filter(
        from_department=department,
        status__in=['pending', 'approved']
    ).select_related('device', 'to_department')

    # تجميع الأجهزة حسب الغرف
    devices_by_room = {}
    for device in actual_devices:
        room = device.room
        if room not in devices_by_room:
            devices_by_room[room] = []
        devices_by_room[room].append(device)
    
    # إحصائيات الأجهزة
    stats = {
        'working': actual_devices.filter(status='working').count(),
        'needs_maintenance': actual_devices.filter(status='needs_maintenance').count(),
        'out_of_order': actual_devices.filter(status='out_of_order').count(),
        'in_use': actual_devices.filter(in_use=True).count(),
    }
    
    # الأجهزة الحرجة
    from django.db.models import Q
    critical_devices = actual_devices.filter(
        Q(status='out_of_order') | 
        Q(status='needs_maintenance')
    )
    
    return render(request, 'maintenance/department_device_list.html', {
        'department': department,
        'actual_devices': actual_devices,
        'devices_by_room': devices_by_room,
        'pending_transfers': pending_transfers,
        'outgoing_transfers': outgoing_transfers,
        'stats': stats,
        'critical_devices': critical_devices,
        'total_devices': actual_devices.count(),
        'active_devices': actual_devices.filter(status='working').count(),
        'inactive_devices': actual_devices.filter(status='out_of_order').count() + actual_devices.filter(status='needs_maintenance').count(),
    })

def add_department(request):
    if request.method == 'POST':
        form = DepartmentForm(request.POST)
        if form.is_valid():
            department = form.save(commit=False)
            department.hospital = request.user.hospital
            department.save()
            messages.success(request, "Department created successfully.")
            return redirect('manager:department_list')
    else:
        form = DepartmentForm()
    return render(request, 'departments/add_department.html', {'form': form})

def department_detail(request, pk):
    department = get_object_or_404(Department, pk=pk, hospital=request.user.hospital)
    return render(request, 'departments/department_detail.html', {'department': department})

def department_surgical_combined(request, department_id=None):
    """
    Combined page that preserves BOTH:
    - Department hub header/buttons (when department_id is provided)
    - Surgical Operations list with search + pagination

    Used by:
    - /patients/departments/<id>/page/
    - /patients/surgical-operations/
    """
    department = None
    if department_id is not None:
        department = get_object_or_404(Department, id=department_id, hospital=request.user.hospital)

    surgical_qs = SurgicalOperationsDepartment.objects.filter(hospital=request.user.hospital)

    search_query = request.GET.get("q", "").strip()
    if search_query:
        surgical_qs = surgical_qs.filter(
            Q(name__icontains=search_query)
            | Q(surgical_type__icontains=search_query)
            | Q(location__icontains=search_query)
        )

    paginator = Paginator(surgical_qs.order_by("name"), 10)
    page = request.GET.get("page")
    try:
        surgicals = paginator.get_page(page)
    except PageNotAnInteger:
        surgicals = paginator.get_page(1)
    except EmptyPage:
        surgicals = paginator.get_page(paginator.num_pages)

    context = {
        "department": department,
        "surgicals": surgicals,           # iterable in template
        "page_obj": surgicals,            # for pagination controls
        "is_paginated": surgicals.paginator.num_pages > 1,
        "search_query": search_query,
    }
    return render(request, "combined/department_surgical.html", context)

def edit_department(request, pk):
    department = get_object_or_404(Department, pk=pk, hospital=request.user.hospital)
    if request.method == 'POST':
        form = DepartmentForm(request.POST, instance=department)
        if form.is_valid():
            form.save()
            messages.success(request, "Department updated successfully.")
            
            return redirect('manager:department_page', department_id=department.id)
    else:
        form = DepartmentForm(instance=department)
        department = get_object_or_404(Department, pk=pk)
    return render(request, 'departments/edit_department.html', {
    'form': form,
    'department': department,
})
            
    

def delete_department(request, pk):
    department = get_object_or_404(Department, pk=pk, hospital=request.user.hospital)
    if request.method == 'POST':
        department.delete()
        messages.success(request, "Department deleted successfully.")
        return redirect('manager:department_list')
    return render(request, 'departments/delete_department.html', {'department': department})

def department_tree(request):
    departments = Department.objects.filter(parent=None, hospital=request.user.hospital)
    return render(request, 'departments/department_tree.html', {
        'departments': departments,
        'hospital': request.user.hospital  # مهم لفلترة الأبناء في template
    })

# Clinic Views
def clinic_list(request):
    clinics = Clinic.objects.filter(hospital=request.user.hospital)
    return render(request, 'clinics/clinic_list.html', {'clinics': clinics})

def clinic_create(request):
    if request.method == "POST":
        form = ClinicForm(request.POST)
        if form.is_valid():
            clinic = form.save(commit=False)
            clinic.hospital = request.user.hospital
            clinic.save()
            messages.success(request, "Clinic created successfully.")
            return redirect('manager:clinic_list')
    else:
        form = ClinicForm()
    return render(request, 'clinics/clinic_form.html', {'form': form})

# Medical Record Views

class MedicalRecordCreateView(LoginRequiredMixin,
                              HospitalmanagerRequiredMixin,
                              CreateView):
    model         = MedicalRecord
    form_class    = MedicalRecordForm
    template_name = "medical_records/medical_record_form.html"

    # ─────────────────── find the patient (if any) ────────────────────────
    def dispatch(self, request, *args, **kwargs):
        # accept /create/<patient_id>/  OR  /create/?patient=<id>
        pid = kwargs.get("patient_id") or request.GET.get("patient")
        self.patient = None
        if pid:
            self.patient = get_object_or_404(
                Patient, id=pid, hospital=request.user.hospital
            )
        return super().dispatch(request, *args, **kwargs)

    # ─────────────────── inject extra kwargs into the form ────────────────
    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw["hospital"] = self.request.user.hospital
        kw["patient"]  = self.patient        # let the form hide & pre-fill it
        return kw

    # ─── tweak the form itself: hide / drop the patient field if fixed ────
    def get_form(self, form_class=None):
        form = super().get_form(form_class)

        if self.patient:
            # we already know the patient → remove the field altogether
            form.fields.pop("patient", None)

        return form

    # ─────────────────── template extras ──────────────────────────────────
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["patient"] = self.patient
        return ctx

    # ─────────────────── save & redirect ──────────────────────────────────
    def form_valid(self, form):
        # ensure patient is wired in
        if self.patient:
            form.instance.patient = self.patient

        self.object = form.save()                 # <- NOW self.object is set
        messages.success(self.request, "Medical record created.")

        return HttpResponseRedirect(
            reverse("manager:patient_detail", args=[self.object.patient.id])
        )

    # optional: dump errors to console during dev
    def form_invalid(self, form):
        print("FORM-ERRORS →", form.errors.as_json())
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse("manager:patient_detail", args=[self.object.patient.id])

class MedicalRecordDetailView(LoginRequiredMixin,
                              HospitalmanagerRequiredMixin,
                              DetailView):
    model = MedicalRecord
    template_name = "medical_records/medical_record_detail.html"
    context_object_name = "record"

class MedicalRecordUpdateView(LoginRequiredMixin,
                              HospitalmanagerRequiredMixin,
                              UpdateView):
    model = MedicalRecord
    form_class = MedicalRecordForm
    template_name = "medical_records/medical_record_form.html"

    def get_success_url(self):
        return reverse("manager:medical_record_detail", args=[self.object.id])

def pdf_settings(request):
    """
    Create or update PDF layout settings for the current hospital.
    URL name:  manager:pdf_settings
    Template : templates/pdf_settings/pdf_settings_form.html
    """
    # Get (or create) the single settings row for this hospital
    pdf_settings_obj, _ = PDFSettings.objects.get_or_create(
        hospital=request.user.hospital
    )

    if request.method == "POST":
        form = PDFSettingsForm(
            request.POST, request.FILES, instance=pdf_settings_obj
        )
        if form.is_valid():
            form.save()
            messages.success(request, "PDF settings saved.")
            return redirect("manager:pdf_settings")
    else:
        form = PDFSettingsForm(instance=pdf_settings_obj)

    return render(
        request,
        "pdf_settings/pdf_settings_form.html",   # create this template
        {"form": form}
    )

def medical_record_print(request):
    if request.method != "POST":
        return HttpResponse("Invalid request method", status=405)

    form_data = json.loads(request.POST.get('form_data', '{}'))
    selected_sections = request.POST.getlist('sections')
    patient_id = form_data.get('patient')
    patient = get_object_or_404(Patient, id=patient_id, hospital=request.user.hospital)

    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Check primary font path
    font_path = '/Users/ye/Downloads/HMS/Janna LT Bold.ttf'
    # Alternative paths - check in order
    alt_paths = [
        os.path.join(settings.BASE_DIR, 'Janna LT Bold.ttf'),
        os.path.join(settings.BASE_DIR, 'static', 'fonts', 'JannaLTBold.ttf')
    ]
    
    # Try the primary path first
    if os.path.exists(font_path):
        pdfmetrics.registerFont(TTFont('Arabic', font_path))
    else:
        # Try alternative paths
        font_registered = False
        for alt_path in alt_paths:
            if os.path.exists(alt_path):
                pdfmetrics.registerFont(TTFont('Arabic', alt_path))
                font_registered = True
                break
        
        # If no font found, use a default font
        if not font_registered:
            # Use a standard font if Arabic font is not available
            pdfmetrics.registerFont(TTFont('Arabic', 'Helvetica'))

    def prepare_arabic_text(text):
        if not text:
            return ""
        reshaped_text = arabic_reshaper.reshape(str(text))
        return get_display(reshaped_text)

    qr = qrcode.QRCode(version=1, box_size=10, border=1)
    qr.add_data(f"Patient MRN: {patient.mrn}, Medical Record Date: {form_data.get('created_at', 'N/A')}")
    qr.make(fit=True)
    qr_img = qr.make_image(fill='black', back_color='white')
    qr_buffer = io.BytesIO()
    qr_img.save(qr_buffer, format="PNG")
    qr_buffer.seek(0)
    qr_image = ImageReader(qr_buffer)

    p.drawImage(qr_image, 50, 700, width=80, height=80)
    p.setFont("Arabic", 14)
    p.drawString(150, 750, prepare_arabic_text("سجل طبي"))

    p.setFont("Arabic", 10)
    p.drawString(150, 730, prepare_arabic_text(f"اسم المستشفى: {request.user.hospital.name}"))
    address = request.user.hospital.address if hasattr(request.user.hospital, 'address') else "غير متوفر"
    p.drawString(150, 710, prepare_arabic_text(f"العنوان: {address}"))
    p.drawString(150, 690, prepare_arabic_text(f"رقم السجل الطبي: {patient.mrn}"))
    p.drawString(150, 670, prepare_arabic_text(f"التاريخ: {form_data.get('created_at', 'N/A')}"))

    y_position = 650
    section_titles = {
        'basic-info': 'المعلومات الأساسية',
        'admission-info': 'معلومات القبول',
        'chief-complaints': 'الشكاوى الرئيسية',
        'hpi': 'تاريخ المرض الحالي',
        'ros': 'مراجعة الأنظمة',
        'health-status': 'التاريخ الطبي',
        'physical-exam': 'الفحص البدني',
        'medical-decision': 'القرار الطبي',
        'interpretation': 'التفسير',
        'impression-plan': 'الانطباع والخطة',
        'professional-service': 'الخدمة المهنية',
        'patient-education': 'تثقيف المريض',
        'soap-note': 'ملاحظة SOAP',
    }

    for section in selected_sections:
        if section not in section_titles:
            continue
        p.setFont("Arabic", 12)
        p.drawString(50, y_position, prepare_arabic_text(section_titles[section]))
        y_position -= 20
        p.setFont("Arabic", 10)

        if section == 'basic-info':
            data = [
                [prepare_arabic_text("الاسم"), prepare_arabic_text(form_data.get('name', 'غير متوفر'))],
                [prepare_arabic_text("تاريخ الميلاد"), prepare_arabic_text(form_data.get('dob', 'غير متوفر'))],
                [prepare_arabic_text("الموقع"), prepare_arabic_text(form_data.get('location', 'غير متوفر'))],
                [prepare_arabic_text("رقم السجل"), prepare_arabic_text(form_data.get('mrn', 'غير متوفر'))],
                [prepare_arabic_text("الوزن"), prepare_arabic_text(form_data.get('weight', 'غير متوفر'))],
                [prepare_arabic_text("الطول"), prepare_arabic_text(form_data.get('height', 'غير متوفر'))],
                [prepare_arabic_text("مؤشر كتلة الجسم"), prepare_arabic_text(form_data.get('bmi', 'غير متوفر'))],
            ]
            table = Table(data, colWidths=[2*inch, 4*inch])
            table.setStyle(TableStyle([
                ('FONT', (0, 0), (-1, -1), 'Arabic', 10),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                ('LEFTPADDING', (1, 0), (1, -1), 10),
            ]))
            table.wrapOn(p, width, height)
            table.drawOn(p, 50, y_position - len(data) * 25)
            y_position -= len(data) * 25 + 20

        elif section == 'admission-info':
            data = [
                [prepare_arabic_text("مصدر التاريخ"), prepare_arabic_text(', '.join(form_data.get('source_history', ['غير متوفر'])) if isinstance(form_data.get('source_history'), list) else form_data.get('source_history', 'غير متوفر'))],
                [prepare_arabic_text("الحاضرين بجانب السرير"), prepare_arabic_text(', '.join(form_data.get('present_at_bedside', ['غير متوفر'])) if isinstance(form_data.get('present_at_bedside'), list) else form_data.get('present_at_bedside', 'غير متوفر'))],
                [prepare_arabic_text("مصدر الإحالة"), prepare_arabic_text(', '.join(form_data.get('referral_source', ['غير متوفر'])) if isinstance(form_data.get('referral_source'), list) else form_data.get('referral_source', 'غير متوفر'))],
                [prepare_arabic_text("قيود التاريخ"), prepare_arabic_text(', '.join(form_data.get('history_limitation', ['غير متوفر'])) if isinstance(form_data.get('history_limitation'), list) else form_data.get('history_limitation', 'غير متوفر'))],
            ]
            table = Table(data, colWidths=[2*inch, 4*inch])
            table.setStyle(TableStyle([
                ('FONT', (0, 0), (-1, -1), 'Arabic', 10),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                ('LEFTPADDING', (1, 0), (1, -1), 10),
            ]))
            table.wrapOn(p, width, height)
            table.drawOn(p, 50, y_position - len(data) * 25)
            y_position -= len(data) * 25 + 20

        elif section == 'chief-complaints':
            p.drawString(50, y_position, prepare_arabic_text(form_data.get('complaint', 'غير متوفر')))
            y_position -= 20

        elif section == 'hpi':
            data = [
                [prepare_arabic_text("البداية"), prepare_arabic_text(form_data.get('hpi_onset', 'غير متوفر'))],
                [prepare_arabic_text("الموقع"), prepare_arabic_text(form_data.get('hpi_location', 'غير متوفر'))],
                [prepare_arabic_text("الشدة"), prepare_arabic_text(form_data.get('hpi_severity', 'غير متوفر'))],
                [prepare_arabic_text("المدة"), prepare_arabic_text(form_data.get('hpi_duration', 'غير متوفر'))],
                [prepare_arabic_text("العوامل المعدلة"), prepare_arabic_text(form_data.get('hpi_modifying_factors', 'غير متوفر'))],
                [prepare_arabic_text("أخرى"), prepare_arabic_text(form_data.get('hpi_others', 'غير متوفر'))],
            ]
            table = Table(data, colWidths=[2*inch, 4*inch])
            table.setStyle(TableStyle([
                ('FONT', (0, 0), (-1, -1), 'Arabic', 10),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                ('LEFTPADDING', (1, 0), (1, -1), 10),
            ]))
            table.wrapOn(p, width, height)
            table.drawOn(p, 50, y_position - len(data) * 25)
            y_position -= len(data) * 25 + 20

        elif section == 'ros':
            p.drawString(50, y_position, prepare_arabic_text(', '.join(form_data.get('ros_constitutional', ['غير متوفر'])) if isinstance(form_data.get('ros_constitutional'), list) else form_data.get('ros_constitutional', 'غير متوفر')))
            y_position -= 20

        elif section == 'health-status':
            data = [
                [prepare_arabic_text("التاريخ الطبي السابق"), prepare_arabic_text(form_data.get('past_medical_history', 'غير متوفر'))],
                [prepare_arabic_text("التاريخ التحسسي"), prepare_arabic_text(form_data.get('allergic_history', 'غير متوفر'))],
                [prepare_arabic_text("التاريخ الاجتماعي"), prepare_arabic_text(form_data.get('social_history', 'غير متوفر'))],
                [prepare_arabic_text("التاريخ العائلي"), prepare_arabic_text(form_data.get('family_history', 'غير متوفر'))],
                [prepare_arabic_text("التاريخ الجراحي السابق"), prepare_arabic_text(form_data.get('past_surgical_history', 'غير متوفر'))],
                [prepare_arabic_text("تاريخ الأدوية"), prepare_arabic_text(form_data.get('medication_history', 'غير متوفر'))],
                [prepare_arabic_text("تاريخ التحصين"), prepare_arabic_text(form_data.get('immunization_history', 'غير متوفر'))],
                [prepare_arabic_text("التاريخ الغذائي"), prepare_arabic_text(form_data.get('nutritional_history', 'غير متوفر'))],
                [prepare_arabic_text("التاريخ النفسي"), prepare_arabic_text(form_data.get('psychiatric_history', 'غير متوفر'))],
            ]
            table = Table(data, colWidths=[2*inch, 4*inch])
            table.setStyle(TableStyle([
                ('FONT', (0, 0), (-1, -1), 'Arabic', 10),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                ('LEFTPADDING', (1, 0), (1, -1), 10),
            ]))
            table.wrapOn(p, width, height)
            table.drawOn(p, 50, y_position - len(data) * 25)
            y_position -= len(data) * 25 + 20

        elif section == 'physical-exam':
            p.drawString(50, y_position, prepare_arabic_text(', '.join(form_data.get('physical_exam_general', ['غير متوفر'])) if isinstance(form_data.get('physical_exam_general'), list) else form_data.get('physical_exam_general', 'غير متوفر')))
            y_position -= 20

        elif section == 'medical-decision':
            data = [
                [prepare_arabic_text("التشخيصات التفريقية"), prepare_arabic_text(form_data.get('differential_diagnoses', 'غير متوفر'))],
                [prepare_arabic_text("مراجعة النتائج"), prepare_arabic_text(form_data.get('result_review', 'غير متوفر'))],
            ]
            table = Table(data, colWidths=[2*inch, 4*inch])
            table.setStyle(TableStyle([
                ('FONT', (0, 0), (-1, -1), 'Arabic', 10),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                ('LEFTPADDING', (1, 0), (1, -1), 10),
            ]))
            table.wrapOn(p, width, height)
            table.drawOn(p, 50, y_position - len(data) * 25)
            y_position -= len(data) * 25 + 20

        elif section == 'interpretation':
            data = [
                [prepare_arabic_text("التفسير"), prepare_arabic_text(form_data.get('interpretation_labs', 'غير متوفر'))],
                [prepare_arabic_text("نتائج المختبر"), prepare_arabic_text(form_data.get('laboratory_results', 'غير متوفر'))],
            ]
            table = Table(data, colWidths=[2*inch, 4*inch])
            table.setStyle(TableStyle([
                ('FONT', (0, 0), (-1, -1), 'Arabic', 10),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                ('LEFTPADDING', (1, 0), (1, -1), 10),
            ]))
            table.wrapOn(p, width, height)
            table.drawOn(p, 50, y_position - len(data) * 25)
            y_position -= len(data) * 25 + 20

        elif section == 'impression-plan':
            data = [
                [prepare_arabic_text("التشخيص"), prepare_arabic_text(form_data.get('diagnosis', 'غير متوفر'))],
                [prepare_arabic_text("المسار"), prepare_arabic_text(form_data.get('course', 'غير متوفر'))],
                [prepare_arabic_text("الأوامر"), prepare_arabic_text(form_data.get('orders', 'غير متوفر'))],
            ]
            table = Table(data, colWidths=[2*inch, 4*inch])
            table.setStyle(TableStyle([
                ('FONT', (0, 0), (-1, -1), 'Arabic', 10),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                ('LEFTPADDING', (1, 0), (1, -1), 10),
            ]))
            table.wrapOn(p, width, height)
            table.drawOn(p, 50, y_position - len(data) * 25)
            y_position -= len(data) * 25 + 20

        elif section == 'professional-service':
            p.drawString(50, y_position, prepare_arabic_text(form_data.get('professional_service', 'غير متوفر')))
            y_position -= 20

        elif section == 'patient-education':
            p.drawString(50, y_position, prepare_arabic_text(form_data.get('patient_education', 'غير متوفر')))
            y_position -= 20

        elif section == 'soap-note':
            p.drawString(50, y_position, prepare_arabic_text(form_data.get('soap_note', 'غير متوفر')))
            y_position -= 20

    y_position -= 40
    p.setFont("Arabic", 10)
    p.drawString(50, y_position, prepare_arabic_text("توقيع الطبيب: ___________________"))
    p.drawString(300, y_position, prepare_arabic_text("توقيع الموظف: ___________________"))

    p.showPage()
    p.save()

    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="medical_record_{patient.mrn}.pdf"'
    return response

# Appointment Views
class AppointmentListView(LoginRequiredMixin, HospitalmanagerRequiredMixin, ListView):
    model = Appointment
    template_name = 'appointments/appointment_list.html'
    context_object_name = 'appointments'

    def get_queryset(self):
        return Appointment.objects.filter(clinic__hospital=self.request.user.hospital)

class AppointmentCreateView(LoginRequiredMixin, HospitalmanagerRequiredMixin, CreateView):
    model = Appointment
    form_class = AppointmentForm
    template_name = 'appointments/appointment_form.html'
    success_url = reverse_lazy('manager:appointment_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['hospital'] = self.request.user.hospital
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        patient_id = self.request.GET.get('patient')
        if patient_id:
            try:
                patient = Patient.objects.get(id=patient_id, hospital=self.request.user.hospital)
                initial['patient'] = patient
            except Patient.DoesNotExist:
                pass
        return initial

    def form_valid(self, form):
        appointment = form.save(commit=False)
        appointment.hospital = self.request.user.hospital
        appointment.created_by = self.request.user
        appointment.save()
        messages.success(self.request, "Appointment created successfully.")
        return super().form_valid(form)
    
# laboratory/views.py
class LabRequestCreateView(LoginRequiredMixin,
                           HospitalmanagerRequiredMixin,
                           CreateView):
    model         = LabRequest
    form_class    = LabRequestForm
    template_name = "laboratory/lab_request_form.html"

    # ---- pre-fill the hidden patient field ----
    def get_initial(self):
        initial = super().get_initial()
        patient_id = self.request.GET.get("patient")
        if patient_id:
            initial["patient"] = get_object_or_404(
                Patient,
                pk=patient_id,
                hospital=self.request.user.hospital,
            )
        return initial

    # ---- server-side additions before save ----
    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.hospital = self.request.user.hospital
        obj.status   = LabRequest.STATUS_SUBMITTED      # or whatever your default is
        obj.save()
        form.save_m2m()          # save selected tests
        messages.success(self.request, "Lab request created.")
        return redirect("manager:patient_detail", obj.patient.pk)
    

class AppointmentUpdateView(LoginRequiredMixin, HospitalmanagerRequiredMixin, UpdateView):
    model = Appointment
    form_class = AppointmentForm
    template_name = 'appointments/appointment_form.html'
    success_url = reverse_lazy('manager:appointment_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['hospital'] = self.request.user.hospital
        return kwargs

class AppointmentCancelView(LoginRequiredMixin, HospitalmanagerRequiredMixin, DeleteView):
    model = Appointment
    template_name = 'appointments/appointment_confirm_cancel.html'
    success_url = reverse_lazy('manager:appointment_list')

    def delete(self, request, *args, **kwargs):
        appointment = self.get_object()
        appointment.status = 'Canceled'
        appointment.save()
        messages.success(request, "Appointment canceled successfully.")
        return redirect(self.success_url)

# Visit Views
class VisitListView(LoginRequiredMixin, HospitalmanagerRequiredMixin, ListView):
    model = Visit
    template_name = 'visits/visit_list.html'
    context_object_name = 'visits'

    def get_queryset(self):
        return Visit.objects.filter(department__hospital=self.request.user.hospital)

class VisitCreateView(LoginRequiredMixin, HospitalmanagerRequiredMixin, CreateView):
    model = Visit
    form_class = VisitForm
    template_name = 'visits/visit_form.html'
    success_url = reverse_lazy('manager:visit_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['hospital'] = self.request.user.hospital
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        patient_id = self.request.GET.get('patient')
        if patient_id:
            try:
                patient = Patient.objects.get(id=patient_id, hospital=self.request.user.hospital)
                initial['patient'] = patient
            except Patient.DoesNotExist:
                pass
        return initial

# Diagnosis Views
class DiagnosisCreateView(LoginRequiredMixin, HospitalmanagerRequiredMixin, CreateView):
    model = Diagnosis
    form_class = DiagnosisForm
    template_name = 'diagnoses/diagnosis_form.html'
    success_url = reverse_lazy('')

    def get_initial(self):
        initial = super().get_initial()
        patient_id = self.request.GET.get('patient')
        if patient_id:
            try:
                patient = Patient.objects.get(id=patient_id, hospital=self.request.user.hospital)
                initial['patient'] = patient
            except Patient.DoesNotExist:
                pass
        return initial

    def form_valid(self, form):
        diagnosis = form.save(commit=False)
        diagnosis.patient = form.cleaned_data['patient']
        diagnosis.save()
        messages.success(self.request, "Diagnosis created successfully.")
        return super().form_valid(form)

# Prescription Views
class PrescriptionCreateView(LoginRequiredMixin, HospitalmanagerRequiredMixin, CreateView):
    model         = Prescription
    form_class    = PrescriptionForm
    template_name = 'prescriptions/prescription_form.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # map medication-id → default_dosage
        dosage_map = {
            str(m.pk): (m.default_dosage or "")
            for m in Medication.objects.all()
        }
        ctx['dosage_map_json'] = json.dumps(dosage_map)
        return ctx

    def get_initial(self):
        initial = super().get_initial()
        patient_id = self.request.GET.get('patient')
        if patient_id:
            try:
                patient = Patient.objects.get(id=patient_id, hospital=self.request.user.hospital)
                initial['patient'] = patient
            except Patient.DoesNotExist:
                pass
        return initial

    def form_valid(self, form):
        prescription = form.save(commit=False)
        
        # Make sure the patient belongs to the user's hospital
        if prescription.patient.hospital != self.request.user.hospital:
            form.add_error('patient', 'You can only create prescriptions for patients in your hospital.')
            return self.form_invalid(form)
        
        # Save the prescription
        prescription.save()
        
        # Check if we should create a pharmacy request
        send_to_pharmacy = self.request.POST.get('send_to_pharmacy') == 'True'
        
        if send_to_pharmacy:
            # Create the prescription request
            request = PrescriptionRequest.objects.create(
                patient=prescription.patient,
                create_pharmacy_request=True,
                status='submitted'
            )
            
            # Create a prescription request item
            PrescriptionRequestItem.objects.create(
                request=request,
                medication=prescription.medication,
                dosage=prescription.dosage
            )
            
            # Generate QR code (handled in the model's save method)
            request.save()
            
            # Notify user
            messages.success(
                self.request, 
                f"Prescription created and sent to pharmacy. Request ID: #{request.pk}"
            )
        else:
            messages.success(self.request, "Prescription created successfully.")
        
        return redirect('manager:patient_detail', pk=prescription.patient.id)

    def get_success_url(self):
        return reverse_lazy('manager:patient_detail', kwargs={'pk': self.object.patient.id})

# Radiology Order Views
class RadiologyOrderCreateView(LoginRequiredMixin, HospitalmanagerRequiredMixin, CreateView):
    model = RadiologyOrder
    form_class = RadiologyOrderForm
    template_name = 'radiology/radiology_order_form.html'
    success_url = reverse_lazy('manager:patient_list')

    def get_initial(self):
        initial = super().get_initial()
        patient_id = self.request.GET.get('patient')
        if patient_id:
            try:
                patient = Patient.objects.get(id=patient_id, hospital=self.request.user.hospital)
                initial['patient'] = patient
            except Patient.DoesNotExist:
                pass
        return initial

    def form_valid(self, form):
        radiology_order = form.save(commit=False)
        radiology_order.patient = form.cleaned_data['patient']
        radiology_order.save()
        messages.success(self.request, "Radiology order created successfully.")
        return super().form_valid(form)

# Bacteriology Result Views
class BacteriologyResultCreateView(LoginRequiredMixin, HospitalmanagerRequiredMixin, CreateView):
    model = BacteriologyResult
    form_class = BacteriologyResultForm
    template_name = 'bacteriology/bacteriology_result_form.html'
    success_url = reverse_lazy('manager:patient_list')

    def get_initial(self):
        initial = super().get_initial()
        patient_id = self.request.GET.get('patient')
        if patient_id:
            try:
                patient = Patient.objects.get(id=patient_id, hospital=self.request.user.hospital)
                initial['patient'] = patient
            except Patient.DoesNotExist:
                pass
        return initial

    def form_valid(self, form):
        bacteriology_result = form.save(commit=False)
        bacteriology_result.patient = form.cleaned_data['patient']
        bacteriology_result.save()
        messages.success(self.request, "Bacteriology result created successfully.")
        return super().form_valid(form)

# PACS Views
class PACSCreateView(LoginRequiredMixin, HospitalmanagerRequiredMixin, CreateView):
    model = PACS
    form_class = PACSForm
    template_name = 'pacs/pacs_form.html'
    success_url = reverse_lazy('manager:patient_list')

    def get_initial(self):
        initial = super().get_initial()
        patient_id = self.request.GET.get('patient')
        if patient_id:
            try:
                patient = Patient.objects.get(id=patient_id, hospital=self.request.user.hospital)
                initial['patient'] = patient
            except Patient.DoesNotExist:
                pass
        return initial

    def form_valid(self, form):
        pacs = form.save(commit=False)
        pacs.patient = form.cleaned_data['patient']
        pacs.save()
        messages.success(self.request, "PACS record created successfully.")
        return super().form_valid(form)

# Program Views
class ProgramCreateView(LoginRequiredMixin, HospitalmanagerRequiredMixin, CreateView):
    model = Program
    form_class = ProgramForm
    template_name = 'programs/program_form.html'
    success_url = reverse_lazy('manager:patient_list')

    def get_initial(self):
        initial = super().get_initial()
        patient_id = self.request.GET.get('patient')
        if patient_id:
            try:
                patient = Patient.objects.get(id=patient_id, hospital=self.request.user.hospital)
                initial['patient'] = patient
            except Patient.DoesNotExist:
                pass
        return initial

    def form_valid(self, form):
        program = form.save(commit=False)
        program.patient = form.cleaned_data['patient']
        program.save()
        messages.success(self.request, "Program created successfully.")
        return super().form_valid(form)

# Form Views
class FormCreateView(LoginRequiredMixin, HospitalmanagerRequiredMixin, CreateView):
    model = Form
    form_class = FormForm
    template_name = 'forms/form_form.html'
    success_url = reverse_lazy('manager:patient_list')

    def get_initial(self):
        initial = super().get_initial()
        patient_id = self.request.GET.get('patient')
        if patient_id:
            try:
                patient = Patient.objects.get(id=patient_id, hospital=self.request.user.hospital)
                initial['patient'] = patient
            except Patient.DoesNotExist:
                pass
        return initial

    def form_valid(self, form):
        form_instance = form.save(commit=False)
        form_instance.patient = form.cleaned_data['patient']
        form_instance.save()
        messages.success(self.request, "Form created successfully.")
        return super().form_valid(form)

# Observation Form Views
class ObservationFormCreateView(LoginRequiredMixin, HospitalmanagerRequiredMixin, CreateView):
    model         = Observation
    form_class    = ObservationForm
    template_name = "observation_forms/observation_form_form.html"

    def dispatch(self, request, *args, **kwargs):
        # pull the patient from the querystring and verify hospital
        patient_id = request.GET.get("patient")
        self.patient = get_object_or_404(
            Patient,
            id=patient_id,
            hospital=request.user.hospital
        )
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        # pre‐fill the FK field so your form knows who it belongs to
        initial = super().get_initial()
        initial["patient"] = self.patient.pk
        return initial

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # so your template can do `{% url 'manager:patient_detail' patient.pk %}`
        ctx["patient"] = self.patient
        return ctx

    def form_valid(self, form):
        # assign and save, with a flash message
        obs = form.save(commit=False)
        obs.patient = self.patient
        obs.save()
        messages.success(self.request, "Observation form created successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        # send you right back to that patient's detail page
         return reverse("manager:vitals_list", kwargs={"record_id": self.record.pk})

# Procedure Views
class ProcedureCreateView(LoginRequiredMixin, HospitalmanagerRequiredMixin, CreateView):
    model = Procedure
    form_class = ProcedureForm
    template_name = 'procedures/procedure_form.html'
    success_url = reverse_lazy('manager:patient_list')

    def get_initial(self):
        initial = super().get_initial()
        patient_id = self.request.GET.get('patient')
        if patient_id:
            try:
                patient = Patient.objects.get(id=patient_id, hospital=self.request.user.hospital)
                initial['patient'] = patient
            except Patient.DoesNotExist:
                pass
        return initial

    def form_valid(self, form):
        procedure = form.save(commit=False)
        procedure.patient = form.cleaned_data['patient']
        procedure.save()
        messages.success(self.request, "Procedure created successfully.")
        return super().form_valid(form)

# Vitals Create View
class VitalSignCreateView(CreateView):
    model = VitalSign
    form_class = VitalSignForm
    template_name = "vitals/vitals_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.record = get_object_or_404(MedicalRecord, pk=kwargs["record_id"])
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.medical_record = self.record
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["record"] = self.record
        return ctx

    def form_valid(self, form):
        # اربط القراءة بالسجل + عيّن من أخذ القراءة
        form.instance.medical_record = self.record
        if not form.instance.taken_by_id and self.request.user.is_authenticated:
            form.instance.taken_by = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        # ارجاع إلى قائمة العلامات لنفس السجل
        # (لو تحب ترجع لتفاصيل المريض استبدل بالسطر التالي)
        # return reverse("patient:record_detail", kwargs={"pk": self.record.pk})
        return reverse("manager:vitals_list", kwargs={"record_id": self.record.pk})

class VitalSignUpdateView(UpdateView):
    model = VitalSign
    form_class = VitalSignForm
    template_name = "vitals/vitals_form.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # نوفر record للزر "إلغاء" في القالب
        ctx["record"] = self.object.medical_record
        return ctx

    def get_success_url(self):
        return reverse("manager:vitals_list", kwargs={"record_id": self.object.medical_record_id})
    
    # ...
    def form_valid(self, form):
        if hasattr(form.instance, "taken_by") and self.request.user.is_authenticated:
            form.instance.taken_by = self.request.user
        return super().form_valid(form)

class VitalSignListView(ListView):
    model = VitalSign
    template_name = "vitals/vitals_list.html"
    context_object_name = "vitals"

    def get_queryset(self):
        self.record = get_object_or_404(MedicalRecord, pk=self.kwargs["record_id"])
        return VitalSign.objects.filter(medical_record=self.record).order_by("-taken_at")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["record"] = self.record
        return ctx

class VitalSignDeleteView(DeleteView):
    model = VitalSign
    template_name = "vitals/vitals_confirm_delete.html"

    def get_success_url(self):
        return reverse("manager:vitals_list", kwargs={"record_id": self.object.medical_record_id})
    


class FluidBalanceCreateView(LoginRequiredMixin, HospitalmanagerRequiredMixin, CreateView):
    model = FluidBalance
    form_class = FluidBalanceForm
    template_name = 'fluid_balances/fluid_balance_form.html'
    success_url = reverse_lazy('manager:patient_list')

    def dispatch(self, request, *args, **kwargs):
        # require ?patient=<id> on URL
        self.patient = get_object_or_404(
            Patient, 
            id=request.GET.get('patient'), 
            hospital=request.user.hospital
        )
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        # preselect the MOST RECENT medical record for this patient
        last_mr = (
            MedicalRecord.objects
            .filter(patient=self.patient)
            .order_by('-created_at')
            .first()
        )
        if last_mr:
            initial['medical_record'] = last_mr
        return initial

    def form_valid(self, form):
        form.instance = form.save(commit=False)
        # ensure the medical_record actually belongs to our patient
        if form.instance.medical_record.patient != self.patient:
            form.add_error('medical_record', "Invalid record for that patient.")
            return self.form_invalid(form)

        form.instance.save()
        messages.success(self.request, "Intake/Output recorded successfully.")
        return super().form_valid(form)

# Emergency Department Views
class EmergencyDepartmentListView(LoginRequiredMixin, HospitalmanagerRequiredMixin, ListView):
    model = EmergencyDepartment
    template_name = 'emergency_department/emergency_department_list.html'
    context_object_name = 'emergencies'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset().filter(hospital=self.request.user.hospital)
        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(
                models.Q(name__icontains=query) |
                models.Q(emergency_type__icontains=query) |
                models.Q(location__icontains=query)
            )
        return queryset.order_by('name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('q', '')
        return context

class EmergencyDepartmentCreateView(LoginRequiredMixin, HospitalmanagerRequiredMixin, SuccessMessageMixin, CreateView):
    model = EmergencyDepartment
    form_class = EmergencyDepartmentForm
    template_name = 'emergency_department/emergency_department_form.html'
    success_url = reverse_lazy('manager:emergency_department_list')
    success_message = "Emergency Department created successfully."

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.hospital = self.request.user.hospital
        form.current_user = self.request.user
        return super().form_valid(form)

# Surgical Operations Department Views
class SurgicalOperationsDepartmentListView(LoginRequiredMixin, HospitalmanagerRequiredMixin, ListView):
    model = SurgicalOperationsDepartment
    template_name = 'surgical_operations/surgical_operations_department_list.html'
    context_object_name = 'surgicals'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset().filter(hospital=self.request.user.hospital)
        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(
                models.Q(name__icontains=query) |
                models.Q(surgical_type__icontains=query) |
                models.Q(location__icontains=query)
            )
        return queryset.order_by('name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('q', '')
        return context

class SurgicalOperationsDepartmentCreateView(LoginRequiredMixin, HospitalmanagerRequiredMixin, SuccessMessageMixin, CreateView):
    model = SurgicalOperationsDepartment
    form_class = SurgicalOperationsDepartmentForm
    template_name = 'surgical_operations/surgical_operations_department_form.html'
    success_url = reverse_lazy('manager:surgical_operations_department_list')
    success_message = "Surgical Operations Department created successfully."

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.hospital = self.request.user.hospital
        form.current_user = self.request.user
        if not form.is_valid():
         print(form.errors)  # ← سيساعدك في تحديد السبب الحقيقي لعدم الحفظ
        return super().form_valid(form)
    

class SurgicalOperationsDepartmentUpdateView(LoginRequiredMixin, HospitalmanagerRequiredMixin, SuccessMessageMixin, UpdateView):
    model = SurgicalOperationsDepartment
    form_class = SurgicalOperationsDepartmentForm
    template_name = 'surgical_operations/surgical_operations_department_form.html'
    success_url = reverse_lazy('manager:surgical_operations_department_list')
    success_message = "Surgical Department updated successfully."

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.hospital = self.request.user.hospital
        return super().form_valid(form)   
    
class SurgicalOperationsDepartmentDeleteView(LoginRequiredMixin, HospitalmanagerRequiredMixin, DeleteView):
    model = SurgicalOperationsDepartment
    success_url = reverse_lazy('manager:surgical_operations_department_list')
    template_name = 'surgical_operations/surgical_operations_department_confirm_delete.html'
    success_message = "Surgical Operations Department deleted successfully."

class SurgicalOperationsDepartmentDetailView(LoginRequiredMixin, HospitalmanagerRequiredMixin, DetailView):
    model = SurgicalOperationsDepartment
    template_name = 'surgical_operations/surgical_operations_department_detail.html'
    context_object_name = 'surgical'
    def get_queryset(self):
        return super().get_queryset().filter(hospital=self.request.user.hospital)

# Medication and Prescription Views
class MedicationListView(LoginRequiredMixin, HospitalmanagerRequiredMixin, ListView):
    model = Medication
    template_name = 'medications/medication_list.html'
    context_object_name = 'medications'

class MedicationCreateView(LoginRequiredMixin, HospitalmanagerRequiredMixin, CreateView):
    model = Medication
    form_class = MedicationForm
    template_name = 'medications/medication_form.html'
    success_url = reverse_lazy('manager:medication_list')

class FollowUpCreateView(LoginRequiredMixin, HospitalmanagerRequiredMixin, CreateView):
    model = FollowUp
    form_class = FollowUpForm
    template_name = 'medications/followup_form.html'
    success_url = reverse_lazy('manager:visit_list')

    def form_valid(self, form):
        follow_up = form.save(commit=False)
        prescription_id = self.kwargs.get('prescription_id')
        follow_up.prescription = get_object_or_404(Prescription, id=prescription_id, patient__hospital=self.request.user.hospital)
        follow_up.save()
        messages.success(self.request, "Follow-up scheduled successfully.")
        return super().form_valid(form)

ICD11_PATH = os.path.join(settings.BASE_DIR, "static", "icd11.xlsx")   # adjust if needed

try:
    import pandas as pd
    _icd_df = (
        pd.read_excel(ICD11_PATH, engine="openpyxl")[["Code", "Title"]]
        .fillna("")
        .astype(str)
    )
except Exception as exc:            # file missing or bad format
    print(f"[ICD‑11] could not load {ICD11_PATH}: {exc}")
    import pandas as pd
    _icd_df = pd.DataFrame(columns=["Code", "Title"])


@require_GET
def icd11_autocomplete(request):
    """
    jQuery‑UI style autocomplete end‑point.
    GET parameter:  ?term=<typed_text>
    Returns:    [ {"label": "BA00 – Essential hypertension", "value": "BA00"}, ... ]
    """
    term = request.GET.get("term", "").strip().lower()
    if not term or _icd_df.empty:
        return JsonResponse([], safe=False)

    # match codes that START with the term OR titles that CONTAIN the term
    mask = (
        _icd_df["Code"].str.lower().str.startswith(term)
        | _icd_df["Title"].str.lower().str.contains(term)
    )
    subset = _icd_df[mask].head(20)          #  ‑‑ limit to 20 suggestions
    suggestions = [
        {"label": f"{row.Code} \u2013 {row.Title}", "value": row.Code}
        for _, row in subset.iterrows()
    ]
    return JsonResponse(suggestions, safe=False)

@require_GET
def icd11_autocomplete(request):
    term = request.GET.get("term", "").strip().lower()
    if not term or _icd_df.empty:
        return JsonResponse([], safe=False)
    mask = (
        _icd_df["Code"].str.lower().str.startswith(term)
        | _icd_df["Title"].str.lower().str.contains(term)
    )
    subset = _icd_df[mask].head(20)
    suggestions = [
        {"label": f"{row.Code} – {row.Title}", "value": row.Code}
        for _, row in subset.iterrows()
    ]
    return JsonResponse(suggestions, safe=False)

# PDF and QR Code Views
def download_patient_pdf(request, patient_id):
    if not (request.user.is_authenticated and request.user.role == 'hospital_manager'):
        return HttpResponse("Unauthorized", status=401)
    
    patient = get_object_or_404(Patient, id=patient_id, hospital=request.user.hospital)
    
    pdf_settings, created = PDFSettings.objects.get_or_create(hospital=request.user.hospital)
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="patient_{patient.mrn}.pdf"'
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1*inch, bottomMargin=0.5*inch)
    styles = getSampleStyleSheet()
    elements = []
    
    if pdf_settings.header_image and os.path.exists(pdf_settings.header_image.path):
        header_img = ReportLabImage(pdf_settings.header_image.path, width=2*inch, height=0.5*inch)
        elements.append(header_img)
    elif pdf_settings.header_text:
        elements.append(Paragraph(pdf_settings.header_text, styles['Title']))
    elements.append(Spacer(1, 0.2*inch))
    
    if pdf_settings.include_patient_details:
        elements.append(Paragraph("Patient Information", styles['Heading2']))
        age_str = "Not provided"
        if hasattr(patient, 'age') and isinstance(patient.age, dict):
            age = patient.age
            age_str = f"{age.get('years', 0)} years, {age.get('months', 0)} months, {age.get('days', 0)} days"
        
        patient_data = [
            ['MRN:', patient.mrn],
            ['Full Name:', f"{patient.first_name} {patient.last_name}"],
            ['Date of Birth:', patient.date_of_birth.strftime('%Y-%m-%d') if patient.date_of_birth else 'Not provided'],
            ['Age:', age_str],
            ['Gender:', patient.gender],
            ['Phone Number:', patient.phone_number],
            ['WhatsApp:', patient.whatsapp_number or 'Not provided'],
            ['Email:', patient.email or 'Not provided'],
            ['Address:', patient.address or 'Not provided'],
            ['National ID:', patient.national_id or 'Not provided'],
            ['Occupation:', patient.occupation or 'Not provided'],
            ['Religion:', patient.religion or 'Not provided'],
            ['Place of Birth:', patient.place_of_birth or 'Not provided'],
        ]
        patient_table = Table(patient_data, colWidths=[2*inch, 4*inch])
        patient_table.setStyle(TableStyle([
            ('FONT', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), pdf_settings.font_size),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('GRID', (0, 0), (-1, -1), 0.5, getattr(colors, pdf_settings.table_border_color, colors.grey)),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.black),
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ]))
        elements.append(patient_table)
        elements.append(Spacer(1, 0.3*inch))
    
    if pdf_settings.include_companion_info:
        elements.append(Paragraph("Companion Information", styles['Heading2']))
        companion_data = [
            ['Name:', patient.companion_name or 'Not provided'],
            ['Phone:', patient.companion_phone or 'Not provided'],
            ['Relationship:', patient.companion_relationship or 'Not provided'],
        ]
        companion_table = Table(companion_data, colWidths=[2*inch, 4*inch])
        companion_table.setStyle(TableStyle([
            ('FONT', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), pdf_settings.font_size),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('GRID', (0, 0), (-1, -1), 0.5, getattr(colors, pdf_settings.table_border_color, colors.grey)),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.black),
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ]))
        elements.append(companion_table)
        elements.append(Spacer(1, 0.3*inch))
    
    if pdf_settings.include_medical_records:
        elements.append(Paragraph("Medical Records", styles['Heading2']))
        medical_records = patient.medicalrecord_set.all()
        if medical_records:
            records_data = [['Created At', 'Complaint', 'Allergies']]
            for record in medical_records:
                complaint = (record.complaint or '')
                if len(complaint) > 80:
                    complaint = complaint[:77] + '...'
                records_data.append([
                    record.created_at.strftime('%Y-%m-%d %H:%M'),
                    complaint or '—',
                    record.allergies or 'None',
                ])
            records_table = Table(records_data, colWidths=[1.6*inch, 3.6*inch, 1.7*inch])
            records_table.setStyle(TableStyle([
                ('FONT', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), pdf_settings.font_size),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('GRID', (0, 0), (-1, -1), 0.5, getattr(colors, pdf_settings.table_border_color, colors.grey)),
                ('BOX', (0, 0), (-1, -1), 0.5, colors.black),
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ]))
            elements.append(records_table)
        else:
            elements.append(Paragraph("No medical records available.", styles['Normal']))
    
    def add_footer(canvas, doc):
        canvas.saveState()
        # Header (center)
        if pdf_settings.header_text:
            canvas.setFont("Helvetica", 10)
            canvas.drawCentredString(doc.pagesize[0] / 2.0, doc.pagesize[1] - 0.4*inch, pdf_settings.header_text)
        # Footer: date (left), custom text (center), page number (right)
        from datetime import datetime as _dt
        canvas.setFont("Helvetica", 9)
        canvas.drawString(0.6*inch, 0.5*inch, _dt.now().strftime('%Y-%m-%d %H:%M'))
        if pdf_settings.footer_text:
            canvas.drawCentredString(doc.pagesize[0] / 2.0, 0.5*inch, pdf_settings.footer_text)
        canvas.drawRightString(doc.pagesize[0] - 0.6*inch, 0.5*inch, f"Page {doc.page}")
        canvas.restoreState()
    
    doc.build(elements, onFirstPage=add_footer, onLaterPages=add_footer)
    response.write(buffer.getvalue())
    buffer.close()
    
    return response

def download_wristband(request, patient_id):
    if not (request.user.is_authenticated and request.user.role == 'hospital_manager'):
        return
    
def download_qr_code(request, patient_id):
    """
    Return a PNG image with a QR‑code that encodes the patient's MRN
    and full name. Used by the /<patient_id>/qrcode/ route.
    """
    if not (request.user.is_authenticated and request.user.role == "hospital_manager"):
        return HttpResponse("Unauthorized", status=401)

    patient = get_object_or_404(
        Patient, id=patient_id, hospital=request.user.hospital
    )

    # Build the QR
    qr = qrcode.QRCode(version=1, box_size=10, border=1)
    qr.add_data(f"MRN:{patient.mrn} | {patient.first_name} {patient.last_name}")
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    # Stream it back as PNG
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    response = HttpResponse(buffer, content_type="image/png")
    response["Content-Disposition"] = (
        f'attachment; filename="patient_{patient.mrn}_qrcode.png"'
    )
    return response    

class ImmunizationCreateView(LoginRequiredMixin,
                             HospitalmanagerRequiredMixin,
                             CreateView):
    model         = Immunization
    form_class    = ImmunizationForm
    template_name = "immunizations/immunization_form.html"
    success_url   = reverse_lazy("manager:patient_list")

    def get_initial(self):
        initial = super().get_initial()
        patient_id = self.request.GET.get("patient")
        if patient_id:
            initial["patient"] = patient_id
        return initial
    
class ObsToObsCreateView(LoginRequiredMixin,
                          HospitalmanagerRequiredMixin,
                          CreateView):
    model = ObsToObs
    form_class = ObsToObsForm
    template_name = 'obstoobs/obstoobs_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.patient = get_object_or_404(
            Patient, pk=request.GET.get('patient')
        )
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['patient'] = self.patient
        return ctx

    def form_valid(self, form):
        form.instance.patient = self.patient
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('manager:patient_detail', kwargs={'pk': self.patient.pk})
    
class PrescriptionRequestCreateView(CreateView):
    model = PrescriptionRequest
    form_class = PrescriptionRequestForm
    template_name = 'manager/pharmacy_request_form.html'

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)

        # ensure we always bind the formset with prefix="items"
        if self.request.POST:
            data['items'] = PrescriptionRequestItemFormSet(
                self.request.POST, prefix='items'
            )
        else:
            data['items'] = PrescriptionRequestItemFormSet(prefix='items')

        # build medication→default dosage map for JS
        dosage_map = {
            m.pk: (m.default_dosage or "")
            for m in Medication.objects.all()
        }
        data['dosage_map_json'] = json.dumps(dosage_map)

        # also pass patient so the template title works
        data['patient'] = get_object_or_404(
            self.request.user.hospital.patients,
            id=self.request.GET.get('patient')
        )
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        items = context['items']
        # save the PrescriptionRequest
        self.object = form.save(commit=False)
        self.object.patient = context['patient']
        self.object.save()

        # now bind the items to the saved object
        if items.is_valid():
            items.instance = self.object
            items.save()

        return redirect(reverse('manager:pharmacy_request_list'))

@method_decorator(login_required, name='dispatch')
class PharmacyRequestListView(ListView):
    model = PrescriptionRequest
    template_name = 'manager/pharmacy_request_list.html'
    context_object_name = 'requests'

    def get_queryset(self):
        return PrescriptionRequest.objects.filter(patient__hospital=self.request.user.hospital)

@method_decorator(login_required, name='dispatch')
class PharmacyRequestDetailView(DetailView):
    model = PrescriptionRequest
    template_name = 'manager/pharmacy_request_detail.html'
    context_object_name = 'request_obj'

@login_required
def pharmacy_request_scan(request, token):
    """
    Authenticated-only endpoint to scan a pharmacy request QR code and update its status.
    Each scan cycles through the request status from submitted → accepted → ready → dispensed.
    """
    pr = get_object_or_404(PrescriptionRequest, token=token)
    
    # Only allow authenticated users to scan and update status
    if not request.user.is_authenticated:
        messages.error(request, "You must be logged in to scan and update pharmacy requests.")
        return redirect('login')
    
    # Ensure user is authorized (either belongs to the patient's hospital or is a superuser)
    if not (request.user.is_superuser or 
            (hasattr(request.user, 'hospital') and request.user.hospital == pr.patient.hospital)):
        messages.error(request, "You don't have permission to update this pharmacy request.")
        return redirect('manager:pharmacy_request_list')
    
    # Cycle through statuses
    order = ['submitted', 'accepted', 'ready', 'dispensed']
    idx = order.index(pr.status)
    
    if idx < len(order) - 1:
        # Update to next status
        old_status = pr.get_status_display()
        pr.status = order[idx + 1]
        pr.save(update_fields=['status'])
        new_status = pr.get_status_display()
        
        # Add success message
        messages.success(
            request, 
            f"Successfully updated request #{pr.pk} status from '{old_status}' to '{new_status}'."
        )
    else:
        messages.info(request, f"Request #{pr.pk} is already in its final state (Dispensed).")
    
    # Redirect to the detail page
    return redirect('manager:pharmacy_request_detail', pk=pr.pk)

@login_required
def pharmacy_request_pdf_download(request, pk):
    """
    Generate and download a PDF for a pharmacy request with patient details,
    medication information, and QR code for scanning.
    """
    pr = get_object_or_404(PrescriptionRequest, pk=pk, patient__hospital=request.user.hospital)
    
    # Create a new PDF buffer
    buffer = io.BytesIO()
    
    # Use ReportLab to create a PDF
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=letter,
        rightMargin=72, 
        leftMargin=72,
        topMargin=72, 
        bottomMargin=72
    )
    
    # Styles
    styles = getSampleStyleSheet()
    style_title = styles['Title']
    style_heading = styles['Heading2']
    style_normal = styles['Normal']
    
    # Document elements
    elements = []
    
    # Title and hospital name
    hospital_name = pr.patient.hospital.name if hasattr(pr.patient.hospital, 'name') else "Hospital"
    elements.append(Paragraph(f"{hospital_name} - Pharmacy Request", style_title))
    elements.append(Spacer(1, 20))
    
    # Request information
    elements.append(Paragraph("Request Information", style_heading))
    elements.append(Spacer(1, 10))
    
    # Create a table for request details
    data = [
        ["Request ID:", f"#{pr.pk}"],
        ["Status:", pr.get_status_display()],
        ["Date:", pr.created_at.strftime('%Y-%m-d %H:%M')],
    ]
    table = Table(data, colWidths=[120, 350])
    table.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.grey),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 20))
    
    # Patient information
    elements.append(Paragraph("Patient Information", style_heading))
    elements.append(Spacer(1, 10))
    
    # Create a table for patient details
    data = [
        ["Name:", pr.patient.full_name],
        ["MRN:", pr.patient.mrn],
        ["Gender:", pr.patient.gender],
        ["Date of Birth:", pr.patient.date_of_birth.strftime('%Y-%m-%d') if pr.patient.date_of_birth else "N/A"],
    ]
    table = Table(data, colWidths=[120, 350])
    table.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.grey),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 20))
    
    # Medications
    elements.append(Paragraph("Medications", style_heading))
    elements.append(Spacer(1, 10))
    
    # Table for medications
    if pr.items.exists():
        med_data = [["Medication", "Dosage"]]
        for item in pr.items.all():
            med_data.append([item.medication.name, item.dosage])
        
        med_table = Table(med_data, colWidths=[240, 230])
        med_table.setStyle(TableStyle([
            ('FONT', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
        ]))
        elements.append(med_table)
    else:
        elements.append(Paragraph("No medications found for this request.", style_normal))
    
    elements.append(Spacer(1, 40))
    
    # Add QR code
    if pr.qr_code:
        elements.append(Paragraph("Scan QR Code to Update Status", style_heading))
        elements.append(Spacer(1, 10))
        
        # Add explanation text
        status_text = "This request has been fully processed."
        if pr.status == 'submitted':
            status_text = "Scan to mark as ACCEPTED"
        elif pr.status == 'accepted':
            status_text = "Scan to mark as READY"
        elif pr.status == 'ready':
            status_text = "Scan to mark as DISPENSED"
        
        elements.append(Paragraph(status_text, style_normal))
        elements.append(Spacer(1, 20))
        
        # Load and add QR code image
        qr_image = ImageReader(pr.qr_code.path)
        qr = Image(qr_image, width=150, height=150)
        qr.hAlign = 'CENTER'
        elements.append(qr)
    
    # Build the PDF document
    doc.build(elements)
    
    # Get the value of the buffer
    buffer.seek(0)
    
    # Create HTTP response with PDF
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename=pharmacy_request_{pr.pk}.pdf'
    
    return response



def download_wristband(request, patient_id):
    if not (request.user.is_authenticated and request.user.role == 'hospital_manager'):
        return HttpResponse("Unauthorized", status=401)

    patient = get_object_or_404(Patient, id=patient_id, hospital=request.user.hospital)

    # Canvas settings (high resolution wristband)
    width, height = 1000, 220
    padding = 24
    qr_size = 180
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)

    # Attempt to load a clean, readable font
    def load_font(pref_size):
        for path in [
            "arial.ttf",  # Windows
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Linux common
            "/Library/Fonts/Arial.ttf",  # macOS
        ]:
            try:
                return ImageFont.truetype(path, pref_size)
            except Exception:
                continue
        return ImageFont.load_default()

    font_title = load_font(28)
    font_label = load_font(22)
    font_value = load_font(24)
    font_small = load_font(18)

    # Latest admission to pull department/ward/doctor
    latest_adm = (
        Admission.objects.filter(patient=patient)
        .order_by("-admission_date")
        .first()
    )
    department_name = latest_adm.department.name if (latest_adm and latest_adm.department) else "-"
    ward_name = "-"
    if latest_adm and latest_adm.bed and getattr(latest_adm.bed, "room", None) and getattr(latest_adm.bed.room, "ward", None):
        ward_name = latest_adm.bed.room.ward.name or "-"
    # Doctor name: Doctor model links to hr.CustomUser via `user` which has `full_name`
    doctor_name = "-"
    if latest_adm and getattr(latest_adm, "treating_doctor", None):
        doc = latest_adm.treating_doctor
        user_obj = getattr(doc, "user", None)
        if user_obj and getattr(user_obj, "full_name", None):
            doctor_name = user_obj.full_name
        else:
            # Fallback to string representation
            doctor_name = str(doc)

    # Allergy info from last medical record
    last_record = (
        MedicalRecord.objects.filter(patient=patient).order_by("-created_at").first()
    )
    allergy_text = None
    if last_record:
        allergy_text = (last_record.allergic_history or last_record.allergies or "").strip() or None

    # Age calculation
    def calc_age(dob):
        try:
            if not dob:
                return None
            from datetime import date
            today = date.today()
            return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        except Exception:
            return None

    age = calc_age(getattr(patient, "date_of_birth", None))
    dob_str = patient.date_of_birth.strftime("%Y-%m-%d") if getattr(patient, "date_of_birth", None) else "-"
    age_str = f" / {age}y" if age is not None else ""

    # Left area text positions
    text_left = padding
    text_top = padding
    text_right_limit = width - padding - qr_size - 20

    # Title
    hospital_name = getattr(request.user.hospital, "name", "Hospital")
    draw.text((text_left, text_top), f"{hospital_name} – Patient Wristband", font=font_title, fill="black")
    text_top += 40

    # Patient details
    def write_line(label, value):
        nonlocal text_top
        draw.text((text_left, text_top), f"{label}:", font=font_label, fill="#333333")
        draw.text((text_left + 210, text_top), f"{value}", font=font_value, fill="black")
        text_top += 34

    full_name = getattr(patient, "full_name", None) or f"{getattr(patient, 'first_name', '')} {getattr(patient, 'last_name', '')}".strip()
    write_line("Patient Name", full_name or "-")
    write_line("Patient ID", patient.mrn or "-")
    write_line("Date of Birth / Age", f"{dob_str}{age_str}")
    write_line("Department / Ward", f"{department_name} / {ward_name}")
    write_line("Doctor's Name", doctor_name)

    # Allergy warning
    text_top += 6
    if allergy_text:
        # Red warning icon and text
        draw.text((text_left, text_top), "⚠", font=font_value, fill="#d32f2f")
        draw.text((text_left + 28, text_top), f"Allergy: {allergy_text}", font=font_value, fill="#d32f2f")
        text_top += 34
    else:
        draw.text((text_left, text_top), "Allergy: None Reported", font=font_value, fill="#2e7d32")
        text_top += 34

    # QR code on the right
    qr = qrcode.QRCode(version=2, box_size=6, border=0)
    qr_payload = f"MRN:{patient.mrn}|NAME:{full_name}|DOB:{dob_str}"
    qr.add_data(qr_payload)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    qr_img = qr_img.resize((qr_size, qr_size), Image.NEAREST)
    qr_x = width - padding - qr_size
    qr_y = (height - qr_size) // 2
    img.paste(qr_img, (qr_x, qr_y))

    # Optional caption under QR
    caption = "Scan for patient info"
    cap_w, cap_h = draw.textbbox((0, 0), caption, font=font_small)[2:]
    draw.text((qr_x + (qr_size - cap_w) // 2, qr_y + qr_size + 4), caption, font=font_small, fill="#555555")

    # Output as PNG
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    resp = HttpResponse(buf, content_type="image/png")
    resp['Content-Disposition'] = f'attachment; filename="wristband_{patient.mrn}.png"'
    return resp




def patient_detail(request, pk):

    LabRequest  = apps.get_model('laboratory', 'LabRequest')
    TestOrder   = apps.get_model('laboratory', 'TestOrder')
    TestResult  = apps.get_model('laboratory', 'TestResult')

    patient = get_object_or_404(Patient, pk=pk, hospital=request.user.hospital)
    lab_orders   = TestOrder.objects.filter(patient=patient).order_by('-created_at')
    lab_requests = LabRequest.objects.filter(patient=patient).order_by('-created_at')
    latest_results = TestResult.objects.filter(patient=patient).order_by('-observed_at')[:20]
    return render(request, "patients/patient_detail.html", {...})
    

    # لو LabRequest فيه حقل hospital وثبّتّه عند الإنشاء، فعّل هذا:
    # if "hospital" in [f.name for f in LabRequest._meta.fields]:
    #     lab_requests = lab_requests.filter(hospital=request.user.hospital)


# ═══════════════════════════════════════════════════════════════════════════
# STEP 3: PATIENT DASHBOARD - COMPREHENSIVE PROFILE VIEW
# ═══════════════════════════════════════════════════════════════════════════

from django.contrib.auth.decorators import login_required
from django.apps import apps

@login_required
def patient_dashboard(request, patient_id):
    """
    Comprehensive patient dashboard - Step 3
    Shows patient profile, devices, lab samples, transfers, and operations
    """
    patient = get_object_or_404(Patient, pk=patient_id, hospital=request.user.hospital)
    
    # Get related models
    Device = apps.get_model('maintenance', 'Device')
    DeviceUsageLog = apps.get_model('maintenance', 'DeviceUsageLog')
    DeviceTransferLog = apps.get_model('maintenance', 'DeviceTransferLog')
    PatientTransferLog = apps.get_model('maintenance', 'PatientTransferLog')
    LabRequest = apps.get_model('laboratory', 'LabRequest')
    LabRequestItem = apps.get_model('laboratory', 'LabRequestItem')
    
    # Current devices assigned to patient
    current_devices = Device.objects.filter(
        current_patient=patient,
        in_use=True
    ).select_related('department', 'room', 'bed')
    
    # Recent device usage logs
    recent_usage = DeviceUsageLog.objects.filter(
        patient=patient
    ).select_related('user', 'bed').prefetch_related(
        'items__device'
    ).order_by('-start_time')[:10]
    
    # Patient transfer history
    transfer_history = PatientTransferLog.objects.filter(
        patient=patient
    ).select_related(
        'from_department', 'to_department',
        'from_room', 'to_room',
        'from_bed', 'to_bed',
        'transferred_by'
    ).order_by('-transferred_at')[:10]
    
    # Lab requests and samples
    lab_requests = LabRequest.objects.filter(
        patient=patient
    ).prefetch_related(
        Prefetch(
            'items',
            queryset=LabRequestItem.objects.select_related('test')
        )
    ).order_by('-requested_at')[:10]
    
    # Recent lab samples
    lab_samples = LabRequestItem.objects.filter(
        request__patient=patient
    ).select_related(
        'test', 'request', 'sample_received_by'
    ).order_by('-request__requested_at')[:15]
    
    # Device transfer logs involving this patient's devices
    device_transfers = DeviceTransferLog.objects.filter(
        Q(device__current_patient=patient) |
        Q(device__in=current_devices)
    ).select_related(
        'device', 'transferred_by',
        'from_department', 'to_department',
        'from_room', 'to_room',
        'from_bed', 'to_bed'
    ).order_by('-transferred_at')[:10]
    
    # Statistics
    stats = {
        'total_devices': current_devices.count(),
        'total_lab_requests': lab_requests.count(),
        'pending_samples': lab_samples.filter(
            status=LabRequestItem.STATUS_PENDING
        ).count() if hasattr(LabRequestItem, 'STATUS_PENDING') else 0,
        'completed_samples': lab_samples.filter(
            Q(value_text__isnull=False) | Q(value_num__isnull=False)
        ).count(),
        'total_transfers': transfer_history.count(),
    }
    
    context = {
        'patient': patient,
        'current_devices': current_devices,
        'recent_usage': recent_usage,
        'transfer_history': transfer_history,
        'lab_requests': lab_requests,
        'lab_samples': lab_samples,
        'device_transfers': device_transfers,
        'stats': stats,
        'title': f'لوحة معلومات المريض - {patient}'
    }
    
    return render(request, 'patients/patient_dashboard.html', context)


@login_required
def patient_search_api(request):
    """
    API for patient search autocomplete
    """
    query = request.GET.get('q', '').strip()
    if len(query) < 2:
        return JsonResponse({'patients': []})
    
    patients = Patient.objects.filter(
        Q(first_name__icontains=query) |
        Q(last_name__icontains=query) |
        Q(mrn__icontains=query),
        hospital=request.user.hospital
    ).values(
        'id', 'first_name', 'last_name', 'mrn', 'date_of_birth'
    )[:20]
    
    patient_list = []
    for p in patients:
        patient_list.append({
            'id': p['id'],
            'name': f"{p['first_name']} {p['last_name']}",
            'mrn': p['mrn'],
            'dob': p['date_of_birth'].strftime('%Y-%m-%d') if p['date_of_birth'] else '',
            'display': f"{p['first_name']} {p['last_name']} (MRN: {p['mrn']})"
        })
    
    return JsonResponse({'patients': patient_list})

    