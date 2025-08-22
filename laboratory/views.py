# laboratory/views.py
import json
from datetime import timedelta
from itertools import groupby
from datetime import timedelta, datetime
from django.core.exceptions import FieldDoesNotExist
import uuid
from django import forms
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DetailView, ListView, UpdateView
from django.views import generic
from manager.models import Patient
from .models import LabRequest, LabRequestItem, Test, TestGroup
# from .forms  import LabRequestForm, LabRequestItemResultForm
  # أو: from django.views.generic import ListView
from django.urls import reverse 
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Test
import uuid
from .models import TestGroup
from .forms import TestGroupForm
from django.db.models import Q
from io import BytesIO
from .forms import LabRequestForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.files.base import ContentFile
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
)
from django.forms import inlineformset_factory, modelformset_factory
from manager.models import Patient
from .models import Test, TestGroup, TestOrder, LabRequest, Sample
from .forms import LabRequestItemResultForm, TestResultForm, TestResultFormSet
from django.forms import modelformset_factory
import qrcode
from .forms import TestResultForm , TestForm #, TestGroupForm
from .forms import LabRequestForm, LabRequestItemResultForm, TestForm, TestGroupForm

from django.utils import timezone
from django.db import transaction
from django.contrib.auth.decorators import login_required, permission_required
from django.views.generic import ListView, UpdateView
from django.urls import reverse_lazy

from .models import TestResult, Test, TestOrder, LabRequest, Sample 
#from .forms import TestResultForm, TestResultFormSet
import base64
from io import BytesIO
import qrcode
from django.urls import reverse
from datetime import timedelta
from itertools import groupby
from django.utils import timezone
from django.views.generic import TemplateView
from django.shortcuts import get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from manager.models import Patient
from .models import LabRequestItem  # تأكد أن الموديل بهذا الاسم

from django.db.models import Q
from datetime import timedelta
from django.utils import timezone

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .models import TestGroup, Test
from django import forms
from .models import Test, TestGroup
from .forms import LabRequestForm, LabRequestItemResultForm, TestForm, TestGroupForm

from django.contrib import messages
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from .models import Test
from .forms import TestForm


# --- TestGroup views (النسخة الوحيدة المعتمدة) ---
from django import forms
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView

from .models import TestGroup
from .forms import TestGroupForm

from django import forms
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView

from .models import TestGroup, Test
from .forms import TestGroupForm

class TestGroupListView(LoginRequiredMixin, ListView):
    model = TestGroup
    template_name = "laboratory/testgroup_list.html"
    context_object_name = "groups"
    paginate_by = 20

    def get_queryset(self):
        return TestGroup.objects.all().order_by("name").prefetch_related("tests")

class TestGroupCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    permission_required = "laboratory.add_testgroup"
    model = TestGroup
    form_class = TestGroupForm
    template_name = "laboratory/testgroup_form.html"
    success_url = reverse_lazy("laboratory:testgroup_list")

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # عدّل tests لو حابب، بدون لمس name
        form.fields["tests"].queryset = Test.objects.all().order_by("english_name")
        return form

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # نقرأ العداد الذي وضعناه على الفورم (إن وُجد)
        form = ctx.get("form")
        ctx["tests_count"] = getattr(form, "_test_count", None)
        return ctx

class TestGroupUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    permission_required = "laboratory.change_testgroup"
    model = TestGroup
    form_class = TestGroupForm
    template_name = "laboratory/testgroup_form.html"
    success_url = reverse_lazy("laboratory:testgroup_list")

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        qs = Test.objects.all().order_by("english_name")
        form.fields["tests"].queryset = qs
        form.fields["tests"].widget = forms.CheckboxSelectMultiple()
        form._test_count = qs.count()
        return form

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        form = ctx.get("form")
        ctx["tests_count"] = getattr(form, "_test_count", None)
        return ctx


class TestGroupDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    permission_required = "laboratory.delete_testgroup"
    model = TestGroup
    template_name = "laboratory/testgroup_confirm_delete.html"
    success_url = reverse_lazy("laboratory:testgroup_list")



# --- مثال إنشاء طلب معمل (إن لم يكن موجود عندك) ---
class LabRequestCreateView(LoginRequiredMixin, CreateView):
    model = LabRequest
    form_class = LabRequestForm
    template_name = "laboratory/lab_request_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.patient = get_object_or_404(
            Patient, pk=kwargs["patient_id"], hospital=request.user.hospital
        )
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["patient"] = self.patient
        ctx["groups"] = TestGroup.objects.prefetch_related("tests").order_by("name")
        return ctx

    def form_valid(self, form):
        # لا تحفظ قبل تعيين المريض
        obj = form.save(commit=False)
        obj.patient = self.patient
        obj.requested_by = self.request.user
        if not getattr(obj, "requested_at", None):
            obj.requested_at = timezone.now()
        obj.save()
        form.save_m2m()  # في حالتك قد لا تحتاجها، لكن لا ضرر

        # اجمع التحاليل المختارة
        chosen_tests = list(form.cleaned_data.get("tests") or [])
        if obj.group and not chosen_tests:
            # لو اختار مجموعة ولم يختَر يدويًا
            chosen_tests = list(obj.group.tests.filter(active=True))

        if not chosen_tests:
            # امنع طلب بلا عناصر
            obj.delete()
            form.add_error("tests", "اختر تحليلًا واحدًا على الأقل أو مجموعة تحتوي تحاليل.")
            return self.form_invalid(form)

        # أنشئ عناصر الطلب
        with transaction.atomic():
            for t in chosen_tests:
                LabRequestItem.objects.get_or_create(
                    request=obj, test=t,
                    defaults={
                        "unit": t.unit or "",
                        "ref_min": t.ref_min,
                        "ref_max": t.ref_max,
                    },
                )

        messages.success(self.request, "تم إنشاء طلب المختبر.")
        return redirect(self.get_success_url(obj))

    def get_success_url(self, obj=None):
        obj = obj or self.object
        return reverse("laboratory:lab_request_detail", args=[obj.pk])
class TestListView(LoginRequiredMixin, ListView):
    model = Test
    template_name = "laboratory/test_list.html"
    paginate_by = 20

    def get_queryset(self):
        qs = Test.objects.all().order_by("category", "english_name")  # بدون subcategory
        q = self.request.GET.get("q")
        if q:
            qs = qs.filter(english_name__icontains=q)
        return qs

class TestCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    permission_required = "laboratory.add_test"
    model = Test
    form_class = TestForm
    template_name = "laboratory/test_form.html"
    success_url = reverse_lazy("laboratory:test_list")

    def form_valid(self, form):
        messages.success(self.request, "تم حفظ التحليل بنجاح.")
        return super().form_valid(form)

    def form_invalid(self, form):
        # اعرض الأخطاء بشكل واضح
        messages.error(self.request, "لم يتم الحفظ. فضلاً صحّح الأخطاء بالأسفل.")
        return super().form_invalid(form)

class TestUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    permission_required = "laboratory.change_test"
    model = Test
    form_class = TestForm
    template_name = "laboratory/test_form.html"
    success_url = reverse_lazy("laboratory:test_list")

class TestDeleteView(DeleteView):
    model = Test
    success_url = reverse_lazy("laboratory:test_list")

    def post(self, request, *args, **kwargs):
        try:
            return super().post(request, *args, **kwargs)
        except ProtectedError:
            messages.error(request, _("Cannot delete this test because it is used in results."))
            return redirect(self.success_url)

class TestCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    permission_required = "laboratory.add_test"
    model = Test
    form_class = TestForm
    template_name = "laboratory/test_form.html"
    success_url = reverse_lazy("laboratory:test_list")

class TestUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    permission_required = "laboratory.change_test"
    model = Test
    form_class = TestForm
    template_name = "laboratory/test_form.html"
    success_url = reverse_lazy("laboratory:test_list")



   



@login_required
def testgroup_tests_api(request, pk):
    grp = get_object_or_404(TestGroup, pk=pk)
    data = list(
        grp.tests.filter(active=True)
        .order_by("english_name")
        .values("id", "english_name", "unit", "ref_min", "ref_max")
    )
    return JsonResponse({"tests": data})

@login_required
def patient_lab_results_print(request, patient_id):
    patient = get_object_or_404(Patient, pk=patient_id, hospital=request.user.hospital)
    rng = request.GET.get("range", "all")  # all | today | 5d

    qs = (
        LabRequestItem.objects
        .select_related("test", "request")
        .filter(request__patient=patient)
    )
    today = timezone.localdate()
    if rng == "today":
        qs = qs.filter(
            Q(observed_at__date=today) |
            (Q(observed_at__isnull=True) & Q(request__requested_at__date=today))
        )
    elif rng == "5d":
        since = timezone.now() - timedelta(days=5)
        qs = qs.filter(
            Q(observed_at__gte=since) |
            (Q(observed_at__isnull=True) & Q(request__requested_at__gte=since))
        )

    qs = qs.order_by("test__english_name", "-observed_at", "-request__requested_at", "-id")

    # بيانات المريض
    dob = getattr(patient, "date_of_birth", None)
    age = None
    if dob:
        today_d = timezone.localdate()
        age = today_d.year - dob.year - ((today_d.month, today_d.day) < (dob.month, dob.day))
    gender = getattr(patient, "gender", None) or getattr(patient, "sex", None) or ""
    mrn = getattr(patient, "mrn", None) or getattr(patient, "medical_record_number", None) or ""

    ctx = {
        "patient": patient,
        "age": age,
        "gender": gender,
        "mrn": mrn,
        "items": qs,
        "range": rng,
        "generated_at": timezone.localtime(),
    }
    return _render_pdf_or_html(request, "laboratory/patient_lab_results_print.html", ctx,
                               f"lab-results-{patient_id}.pdf")

class PatientLabResultsView(LoginRequiredMixin, TemplateView):
    template_name = "patients/patient_lab_results.html"

    def _get_patient(self):
        pid = self.kwargs.get("patient_id") or self.kwargs.get("pk")
        return get_object_or_404(Patient, pk=pid, hospital=self.request.user.hospital)

    @staticmethod
    def _ts_ms(dt):
        """حوّل datetime إلى milliseconds since epoch (لـ Chart.js)."""
        if not dt:
            return None
        try:
            dt = timezone.localtime(dt)
        except Exception:
            pass
        return int(dt.timestamp() * 1000)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        patient = self._get_patient()
        ctx["patient"] = patient

        # فلاتر الواجهة
        rng  = self.request.GET.get("range", "all")   # all | today | 5d
        view = self.request.GET.get("view",  "table") # table | chart
        res  = self.request.GET.get("res",   "auto")  # auto | hour | day
        ctx.update({"range": rng, "view": view, "res": res})

        # المصدر: عناصر طلبات هذا المريض
        qs = (
            LabRequestItem.objects
            .select_related("test", "request")
            .filter(request__patient=patient)
        )

        # فلترة المدى الزمني (نستخدم observed_at إن وُجد وإلا requested_at)
        today = timezone.localdate()
        if rng == "today":
            qs = qs.filter(
                Q(observed_at__date=today) |
                (Q(observed_at__isnull=True) & Q(request__requested_at__date=today))
            )
        elif rng == "5d":
            since = timezone.now() - timedelta(days=5)
            qs = qs.filter(
                Q(observed_at__gte=since) |
                (Q(observed_at__isnull=True) & Q(request__requested_at__gte=since))
            )

        # مهم: groupby يحتاج ترتيب بالـ test_id
        qs = qs.order_by("test_id", "-observed_at", "-request__requested_at", "-id")

        # تجميع للجدول
        grouped = []
        for _test_id, group in groupby(qs, key=lambda x: x.test_id):
            rows = list(group)
            if rows:
                grouped.append({"test": rows[0].test, "rows": rows})
        ctx["grouped"] = grouped

        # تجهيز بيانات الرسم: نقاط رقمية فقط (value_num) + حدود مرجعية
        chart_series = []
        tz = timezone.get_current_timezone()

        for g in grouped:
            points = []
            ref_min_val = None
            ref_max_val = None
            unit_val    = None

            for it in g["rows"]:
                # التقط مرّة واحدة ref/unit إن توفّرت
                if ref_min_val is None and it.ref_min is not None:
                    try: ref_min_val = float(it.ref_min)
                    except Exception: pass
                if ref_max_val is None and it.ref_max is not None:
                    try: ref_max_val = float(it.ref_max)
                    except Exception: pass
                if unit_val is None and it.unit:
                    unit_val = it.unit

                # أضف النقطة إن كانت رقمية
                if it.value_num is None:
                    continue
                ts = it.observed_at or getattr(it.request, "completed_at", None) or it.request.requested_at
                t_ms = self._ts_ms(ts)
                if t_ms is None:
                    continue
                try:
                    y = float(it.value_num)
                except Exception:
                    continue
                points.append({"t": t_ms, "y": y})

            if not points:
                continue

            # تحديد وحدة الزمن
            if res in ("hour", "day"):
                time_unit = res
            else:
                per_day = {}
                for p in points:
                    d = datetime.fromtimestamp(p["t"] / 1000, tz=tz).date().isoformat()
                    per_day[d] = per_day.get(d, 0) + 1
                time_unit = "hour" if any(c > 1 for c in per_day.values()) else "day"

            points.sort(key=lambda p: p["t"])
            label = getattr(g["test"], "english_name", None) or str(g["test"])

            chart_series.append({
                "label": label,
                "data": points,
                "timeUnit": time_unit,
                "ref_min": ref_min_val,
                "ref_max": ref_max_val,
                "unit": unit_val or "",
            })

        ctx["chart_series"] = chart_series
        ctx["chart_series_json"] = json.dumps(chart_series)
        return ctx
# -------- إنشاء طلب --------


# -------- قائمة الطلبات مع فلاتر --------
class LabRequestListView(LoginRequiredMixin, ListView):
    model = LabRequest
    template_name = "laboratory/lab_request_list.html"
    paginate_by = 25

    def get_queryset(self):
        qs = LabRequest.objects.select_related("patient", "group")
        p   = self.request.GET.get("patient")
        st  = self.request.GET.get("status")
        t   = self.request.GET.get("test")
        cat = self.request.GET.get("category")
        d1  = self.request.GET.get("from")
        d2  = self.request.GET.get("to")

        if p:   qs = qs.filter(patient_id=p)
        if st:  qs = qs.filter(status=st)
        if d1:  qs = qs.filter(requested_at__date__gte=d1)
        if d2:  qs = qs.filter(requested_at__date__lte=d2)
        if t:   qs = qs.filter(items__test_id=t).distinct()
        if cat: qs = qs.filter(items__test__category=cat).distinct()

        return qs.order_by("-requested_at", "-id")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["tests"] = Test.objects.filter(active=True)
        ctx["categories"] = dict(Test.CATEGORY_CHOICES)
        return ctx
    
class HospitalContextMixin:
    """يوحّد منطق فلترة الكائنات حسب مستشفى المستخدم."""
    hospital_field_map = {
        Patient: "hospital",
        # إن كان لديك موديلات فيها hospital مباشرة، أضفها هنا
    }

    def get_hospital(self):
        user = self.request.user
        if not hasattr(user, "hospital") or user.hospital is None:
            raise Http404("No hospital bound to your account.")
        return user.hospital

    def filter_by_hospital(self, qs):
        model = qs.model
        hospital = self.get_hospital()

        # إذا كان الموديل نفسه لا يحوي hospital، نحاول عبر علاقات معروفة
        if hasattr(model, "hospital"):
            return qs.filter(hospital=hospital)

        # إن كان مرتبطًا بالمريض مثل TestOrder/LabRequest
        if model is TestOrder:
            return qs.filter(patient__hospital=hospital)
        if model is LabRequest:
            return qs.filter(patient__hospital=hospital)
        if model is Patient:
            return qs.filter(hospital=hospital)

        # Test / TestGroup عادة بيانات مرجعية عامة (بدون hospital)
        return qs

    def get_queryset(self):
        qs = super().get_queryset()
        return self.filter_by_hospital(qs)


def _render_pdf_or_html(request, template_name, context, pdf_filename):
    """حاول استخدام WeasyPrint؛ لو غير متاح نرجع HTML عادي."""
    try:
        from weasyprint import HTML
        html_string = render_to_string(template_name, context)
        pdf = HTML(string=html_string, base_url=request.build_absolute_uri("/")).write_pdf()
        return HttpResponse(
            pdf,
            content_type="application/pdf",
            headers={"Content-Disposition": f'inline; filename="{pdf_filename}"'},
        )
    except Exception:
        return render(request, template_name, context)



# -------- تفاصيل الطلب + إدخال نتائج --------
class LabRequestDetailView(LoginRequiredMixin, HospitalContextMixin, DetailView):
    model = LabRequest
    template_name = "laboratory/lab_request_detail.html"


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obj = self.object

        # لو مافيش ملف QR محفوظ، نولّد واحد Base64 للعرض فقط
        has_file = getattr(obj, "qr_code", None) and getattr(obj.qr_code, "name", "")
        if not has_file:
            scan_url = self.request.build_absolute_uri(
                reverse("laboratory:lab_request_scan", args=[str(obj.token)])
            )
            img = qrcode.make(scan_url)
            buf = BytesIO()
            img.save(buf, format="PNG")
            context["qr_data_uri"] = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()

        return context

    def get_queryset(self):
        return LabRequest.objects.select_related("patient", "group").prefetch_related("items__test")

    def post(self, request, *args, **kwargs):
        """
        يدعم تغيير حالة العنصر أو الطلب عبر أزرار في الشاشة (بجوار كل عنصر).
        """
        self.object = self.get_object()
        action   = request.POST.get("action")
        item_id  = request.POST.get("item_id")
        item = None
        if item_id:
            item = get_object_or_404(LabRequestItem, pk=item_id, request=self.object)

        now = timezone.now()
        user = request.user

        if action == "accept":
            self.object.status = LabRequest.STATUS_ACCEPTED
            self.object.accepted_at = now
            self.object.accepted_by = user
            self.object.save(update_fields=["status","accepted_at","accepted_by"])

        elif action == "prepare_tube" and item:
            item.tube_prepared_at = now
            item.tube_prepared_by = user
            item.save(update_fields=["tube_prepared_at","tube_prepared_by"])

        elif action == "collect" and item:
            item.sample_collected_at = now
            item.sample_collected_by = user
            item.save(update_fields=["sample_collected_at","sample_collected_by"])
            # لو كل العناصر تم سحبها، حرّك حالة الطلب
            if not self.object.items.filter(sample_collected_at__isnull=True).exists():
                self.object.status = LabRequest.STATUS_COLLECTED
                self.object.collected_at = now
                self.object.collected_by = user
                self.object.save(update_fields=["status","collected_at","collected_by"])

        elif action == "dispatch" and item:
            item.sample_dispatched_at = now
            item.sample_dispatched_by = user
            item.save(update_fields=["sample_dispatched_at","sample_dispatched_by"])
            if not self.object.items.filter(sample_dispatched_at__isnull=True).exists():
                self.object.status = LabRequest.STATUS_DISPATCHED
                self.object.dispatched_at = now
                self.object.dispatched_by = user
                self.object.save(update_fields=["status","dispatched_at","dispatched_by"])

        elif action == "receive" and item:
            item.sample_received_at = now
            item.sample_received_by = user
            item.status = LabRequestItem.STATUS_IN_LAB
            item.save(update_fields=["sample_received_at","sample_received_by","status"])
            if not self.object.items.filter(sample_received_at__isnull=True).exists():
                self.object.status = LabRequest.STATUS_RECEIVED
                self.object.received_at = now
                self.object.received_by = user
                self.object.save(update_fields=["status","received_at","received_by"])

        messages.success(request, "تم تحديث الحالة.")
        return redirect("laboratory:lab_request_detail", pk=self.object.pk)


# -------- تحرير نتيجة عنصر --------
class LabRequestItemUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    permission_required = "laboratory.change_labrequestitem"
    model = LabRequestItem
    form_class = LabRequestItemResultForm

    template_name = "laboratory/lab_item_result_form.html"



def form_valid(self, form):
    resp = super().form_valid(form)
    req = self.object.request  # الطلب المرتبط بعنصر النتيجة
    self.object = form.save()

        # الطلب الأب
    req = self.object.request

        # ✅ الخيار (أ): دوماً عدّل الطلب إلى Completed بعد إدخال نتيجة عنصر
    req.status = LabRequest.STATUS_COMPLETED
    req.completed_at = timezone.now()
    req.completed_by = self.request.user
    req.save(update_fields=["status", "completed_at", "completed_by"])


     # إن كان لديك حقل حالة على العنصر نفسه (اختياري)
    if hasattr(self.object, "status"):
            try:
                self.object.status = getattr(self.object.__class__, "STATUS_COMPLETED", "completed")
                self.object.save(update_fields=["status"])
            except Exception:
                pass

        # رسالة نجاح وتوجيه
    messages.success(self.request, "تم حفظ النتيجة وتحديث الحالة إلى Completed.")
    return super().form_valid(form)

    def get_success_url(self):
        return (
            self.request.POST.get("next")
            or self.request.GET.get("next")
            or reverse("laboratory:lab_request_detail", args=[self.object.request_id])
        )


def get_success_url(self):
        # لو مرّرت ?next= يرجّع له؛ وإلا يرجّع لتفاصيل الطلب
        return (
            self.request.POST.get("next")
            or self.request.GET.get("next")
            or reverse("laboratory:lab_request_detail", args=[self.object.request_id])
        )


# -------- مسح QR لتحريك الطلب/العينة --------
@login_required
def lab_request_scan(request, token):
    req = get_object_or_404(LabRequest, token=token)
    # مثال بسيط: كل مسح ينقل الطلب للمرحلة التالية (اختياري حسب سياستك)
    now = timezone.now()
    if req.status == LabRequest.STATUS_SUBMITTED:
        req.status = LabRequest.STATUS_ACCEPTED; req.accepted_at = now; req.accepted_by = request.user
    elif req.status == LabRequest.STATUS_ACCEPTED:
        req.status = LabRequest.STATUS_COLLECTED; req.collected_at = now; req.collected_by = request.user
    elif req.status == LabRequest.STATUS_COLLECTED:
        req.status = LabRequest.STATUS_DISPATCHED; req.dispatched_at = now; req.dispatched_by = request.user
    elif req.status == LabRequest.STATUS_DISPATCHED:
        req.status = LabRequest.STATUS_RECEIVED; req.received_at = now; req.received_by = request.user
    req.save()
    messages.info(request, f"Request moved to {req.get_status_display()}")
    return redirect("laboratory:lab_request_detail", pk=req.pk)


@login_required
def sample_scan(request, token):
    item = get_object_or_404(LabRequestItem, sample_token=token)
    # بمجرد المسح نعتبرها وصلت للمعمل
    if item.status == LabRequestItem.STATUS_PENDING:
        item.status = LabRequestItem.STATUS_IN_LAB
        item.sample_received_at = timezone.now()
        item.sample_received_by = request.user
        item.save(update_fields=["status","sample_received_at","sample_received_by"])
    messages.info(request, f"Sample for {item.test} marked as received in lab.")
    return redirect("laboratory:lab_request_detail", pk=item.request_id)


# ═══════════════════════════════════════════════════════════════════════════
# STEP 3: LABORATORY SAMPLE SCAN INTERFACE
# ═══════════════════════════════════════════════════════════════════════════

@login_required
def lab_sample_scan_page(request):
    """
    Laboratory sample scanning interface - Step 3
    """
    context = {
        'title': 'مسح عينات المختبر - Step 3',
        'scan_types': [
            ('receive', 'استلام العينة'),
            ('process', 'معالجة العينة'),
            ('complete', 'إكمال التحليل'),
            ('reject', 'رفض العينة'),
        ]
    }
    return render(request, 'laboratory/sample_scan.html', context)


from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
@login_required
def update_sample_status(request):
    """
    Update lab sample status via API
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        sample_token = data.get('sample_token')
        action = data.get('action')
        notes = data.get('notes', '')
        
        if not sample_token or not action:
            return JsonResponse({'error': 'Missing required fields'}, status=400)
        
        # Get the lab request item
        try:
            item = LabRequestItem.objects.select_related(
                'request__patient', 'test'
            ).get(sample_token=sample_token)
        except LabRequestItem.DoesNotExist:
            return JsonResponse({'error': 'Sample not found'}, status=404)
        
        now = timezone.now()
        user = request.user
        
        # Update based on action
        if action == 'receive':
            if item.status == LabRequestItem.STATUS_PENDING:
                item.status = LabRequestItem.STATUS_IN_LAB
                item.sample_received_at = now
                item.sample_received_by = user
                item.save(update_fields=['status', 'sample_received_at', 'sample_received_by'])
                message = 'تم استلام العينة بنجاح'
            else:
                message = 'العينة مستلمة مسبقاً'
        
        elif action == 'process':
            if item.status in [LabRequestItem.STATUS_PENDING, LabRequestItem.STATUS_IN_LAB]:
                item.status = LabRequestItem.STATUS_IN_LAB
                if not item.sample_received_at:
                    item.sample_received_at = now
                    item.sample_received_by = user
                item.save(update_fields=['status', 'sample_received_at', 'sample_received_by'])
                message = 'تم بدء معالجة العينة'
            else:
                message = 'العينة قيد المعالجة'
        
        elif action == 'complete':
            # This would typically redirect to result entry
            message = 'يرجى إدخال نتائج التحليل'
            return JsonResponse({
                'success': True,
                'message': message,
                'redirect_url': reverse('laboratory:lab_item_result', args=[item.pk])
            })
        
        elif action == 'reject':
            item.status = 'rejected'  # Assuming you have this status
            item.save(update_fields=['status'])
            message = 'تم رفض العينة'
        
        else:
            return JsonResponse({'error': 'Invalid action'}, status=400)
        
        # Return updated sample info
        return JsonResponse({
            'success': True,
            'message': message,
            'sample': {
                'token': str(item.sample_token),
                'test_name': item.test.english_name,
                'patient_name': str(item.request.patient),
                'status': item.get_status_display() if hasattr(item, 'get_status_display') else item.status,
                'received_at': item.sample_received_at.isoformat() if item.sample_received_at else None,
                'received_by': item.sample_received_by.get_full_name() if item.sample_received_by else None,
            }
        })
    
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Server error: {str(e)}'}, status=500)

class LabDashboardView(LoginRequiredMixin, generic.TemplateView):
    template_name = "laboratory/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        # عدادات أساسية
        ctx["requests_pending"] = LabRequest.objects.exclude(status=LabRequest.STATUS_COMPLETED).count()
        ctx["requests_today"]   = LabRequest.objects.filter(requested_at__date=timezone.now().date()).count()

        # آخر 10 طلبات
        ctx["lab_requests"] = (
            LabRequest.objects
            .select_related("patient", "group")
            .prefetch_related("items__test")
            .order_by("-requested_at", "-id")[:10]
        )

        # (اختياري) لو حابب تعرض تجميعات سريعة
        ctx["top_tests"] = (
            Test.objects.filter(request_items__isnull=False)
            .distinct()
            .order_by("english_name")[:10]
        )
        return ctx
    

 # -------------------------------------------------------------------
# Master data: Test CRUD
# -------------------------------------------------------------------
class TestListView(LoginRequiredMixin, ListView):
    model = Test
    template_name = "laboratory/test_list.html"
    paginate_by = 20

    def get_queryset(self):
        qs = Test.objects.all().order_by("category", "english_name")  # لا subcategory
        q = self.request.GET.get("q")
        if q:
            qs = qs.filter(english_name__icontains=q)
        return qs


class TestCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    permission_required = "laboratory.add_test"
    model = Test
    form_class = TestForm
    template_name = "laboratory/test_form.html"
    success_url = reverse_lazy("laboratory:test_list")

    def form_valid(self, form):
        messages.success(self.request, "Test created.")
        return super().form_valid(form)

class TestUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    permission_required = "laboratory.change_test"
    model = Test
    form_class = TestForm
    template_name = "laboratory/test_form.html"
    success_url = reverse_lazy("laboratory:test_list")

    def form_valid(self, form):
        messages.success(self.request, "Test updated.")
        return super().form_valid(form)

class TestDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    permission_required = "laboratory.delete_test"
    model = Test
    template_name = "laboratory/confirm_delete.html"
    success_url = reverse_lazy("laboratory:test_list")

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Test deleted.")
        return super().delete(request, *args, **kwargs)
    

@login_required
def get_sample_info(request, sample_token):
    """
    Get detailed sample information by token
    """
    try:
        item = LabRequestItem.objects.select_related(
            'request__patient', 'test', 'sample_received_by'
        ).get(sample_token=sample_token)
        
        return JsonResponse({
            'success': True,
            'sample': {
                'token': str(item.sample_token),
                'test_name': item.test.english_name,
                'test_arabic_name': getattr(item.test, 'arabic_name', ''),
                'patient_name': str(item.request.patient),
                'patient_mrn': getattr(item.request.patient, 'mrn', ''),
                'status': item.get_status_display() if hasattr(item, 'get_status_display') else item.status,
                'unit': item.unit or '',
                'ref_min': item.ref_min,
                'ref_max': item.ref_max,
                'tube_prepared_at': item.tube_prepared_at.isoformat() if item.tube_prepared_at else None,
                'sample_collected_at': item.sample_collected_at.isoformat() if item.sample_collected_at else None,
                'sample_received_at': item.sample_received_at.isoformat() if item.sample_received_at else None,
                'sample_received_by': item.sample_received_by.get_full_name() if item.sample_received_by else None,
                'request_id': item.request.pk,
                'requested_at': item.request.requested_at.isoformat(),
            }
        })
    
    except LabRequestItem.DoesNotExist:
        return JsonResponse({'error': 'Sample not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': f'Server error: {str(e)}'}, status=500)


    # -------------------------------------------------------------------
# Master data: TestGroup CRUD
# -------------------------------------------------------------------
class TestGroupListView(LoginRequiredMixin, ListView):
    model = TestGroup
    template_name = "laboratory/testgroup_list.html"
    paginate_by = 20

    def get_queryset(self):
        qs = TestGroup.objects.all().order_by("name").prefetch_related("tests")
        q = self.request.GET.get("q")
        if q:
            qs = qs.filter(name__icontains=q)
        return qs


class TestResultForm(forms.ModelForm):
    class Meta:
        model = TestResult
        fields = [
            "test", "value_num", "observed_value", "unit",
            "ref_min", "ref_max", "status", "notes", "observed_at",
        ]
        widgets = {
            "observed_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }

TestResultFormSet = inlineformset_factory(
    parent_model=TestOrder,
    model=TestResult,
    form=TestResultForm,
    fields=[
        "test", "value_num", "observed_value", "unit",
        "ref_min", "ref_max", "status", "notes", "observed_at",
    ],
    extra=0,
    can_delete=True,
)

def testorder_add(request, patient_id):
    """إنشاء أمر معمل قديم (TestOrder) لمريض محدد."""
    patient = get_object_or_404(Patient, pk=patient_id, hospital=request.user.hospital)

    from .forms import TestOrderForm  # استيراد محلي لتجنب دورات
    if request.method == "POST":
        form = TestOrderForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            order.patient = patient
            order.save()
            form.save_m2m()

            # أنشئ عينة واحدة مرتبطة بالأمر (يمكنك توسيع المنطق لاحقًا)
            Sample.objects.create(test_order=order, tube_type=order.tube_type or "")

            messages.success(request, "Lab order submitted.")
            return redirect("laboratory:testorder_print", pk=order.pk)
    else:
        form = TestOrderForm()

    return render(request, "laboratory/testorder_form.html", {"form": form, "patient": patient})

# ----- 3.1 قائمة النتائج مع فلاتر بسيطة -----
class TestResultListView(LoginRequiredMixin, ListView):
    model = TestResult
    template_name = "laboratory/test_results_list.html"
    paginate_by = 25

    def get_queryset(self):
        qs = TestResult.objects.select_related("patient", "test", "order", "request")
        # فلاتر GET
        patient_id = self.request.GET.get("patient")
        status     = self.request.GET.get("status")
        test_id    = self.request.GET.get("test")
        cat        = self.request.GET.get("category")
        date_from  = self.request.GET.get("from")
        date_to    = self.request.GET.get("to")

        if patient_id:
            qs = qs.filter(patient_id=patient_id)
        if status in [TestResult.STATUS_DRAFT, TestResult.STATUS_VERIFIED]:
            qs = qs.filter(status=status)
        if test_id:
            qs = qs.filter(test_id=test_id)
        if cat:
            qs = qs.filter(test__category=cat)
        if date_from:
            qs = qs.filter(observed_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(observed_at__date__lte=date_to)

        return qs.order_by("-observed_at", "-id")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["tests"] = Test.objects.all().order_by("english_name")
        ctx["categories"] = dict(Test.CATEGORY_CHOICES)
        # تمرير patient اختياريًا لإظهار أزرار العودة
        ctx["patient_id"] = self.request.GET.get("patient", "")
        return ctx


def testorder_queue(request):
    # مثال: اعرض الطلبات غير المكتملة مرتبة بالأقدمية
    qs = (
        TestOrder.objects
        .select_related("patient")
        .prefetch_related("tests")
        .filter(status__in=["PENDING", "COLLECTING", "IN_PROGRESS"])
        .order_by("created_at")
    )
    return render(request, "laboratory/testorder_queue.html", {"orders": qs})





class TestOrderQueueView(LoginRequiredMixin, HospitalContextMixin, ListView):
    """طابور العمل للأوامر ذات الحالة submitted."""
    model = TestOrder
    template_name = "laboratory/testorder_queue.html"
    paginate_by = 25

   
    def get_queryset(self):
        qs = TestOrder.objects.all()

        # جرّب معرفة اسم حقل الحالة فعليًا
        status_field = None
        for cand in ("status", "state", "order_status", "phase"):
            try:
                TestOrder._meta.get_field(cand)
                status_field = cand
                break
            except FieldDoesNotExist:
                continue

        if not status_field:
            # لا يوجد حقل حالة أصلاً: اعرض الكل بترتيب زمني
            return qs.order_by("-requested_at")

        # إن وُجد حقل حالة، فلترة “طابور الانتظار” أو ما يقاربه
        field = TestOrder._meta.get_field(status_field)
        choices = {c[0] for c in getattr(field, "choices", [])} if getattr(field, "choices", None) else set()
        preferred = ("queued", "queue", "submitted", "pending", "new", "awaiting")

        queue_value = next((v for v in preferred if (not choices or v in choices)), None)
        if queue_value:
            return qs.filter(**{status_field: queue_value})

        not_done = [v for v in ("in_progress", "processing", "collected") if (not choices or v in choices)]
        if not_done:
            return qs.filter(**{f"{status_field}__in": not_done})

        return qs.order_by("-requested_at")

@login_required
def testorder_print(request, pk):
    """طباعة/عرض أمر معمل واحد مع أكواد العينة."""
    order = get_object_or_404(
        TestOrder.objects.select_related("patient").prefetch_related("tests","samples"),
        pk=pk,
    )
    ctx = {"order": order}
    return _render_pdf_or_html(request, "laboratory/testorder_print.html", ctx, f"order-{order.id}.pdf")


@login_required
def sample_barcode_print(request, sample_id):
    """طباعة/عرض QR لعينة واحدة."""
    sample = get_object_or_404(Sample.objects.select_related("test_order"), pk=sample_id)
    ctx = {"sample": sample}
    return _render_pdf_or_html(request, "laboratory/sample_barcode_print.html", ctx, f"sample-{sample.id}.pdf")


@login_required
def sample_scan(request, token):
    """مسح QR لعينة → يفتح صفحة طباعة أمرها."""
    sample = get_object_or_404(Sample, token=token)
    return redirect("laboratory:testorder_print", pk=sample.test_order_id)

@login_required
@permission_required("laboratory.add_testresult", raise_exception=True)
@transaction.atomic
def add_results_for_request(request, request_id):
    # اجلب الطلب + المريض + الاختبارات
    req = get_object_or_404(
        LabRequest.objects.select_related("patient").prefetch_related("tests"),
        pk=request_id
    )
    patient = req.patient

    # أنشئ نتائج مبدئية لأي اختبار ما له نتيجة بعد
    existing_test_ids = set(
        TestResult.objects.filter(request=req).values_list("test_id", flat=True)
    )
    missing_tests = [t for t in req.tests.all() if t.id not in existing_test_ids]
    for t in missing_tests:
        TestResult.objects.create(
            patient=patient,
            request=req,
            test=t,
            unit=t.unit or "",
            ref_min=t.ref_min,
            ref_max=t.ref_max,
            status=TestResult.STATUS_DRAFT,
        )
