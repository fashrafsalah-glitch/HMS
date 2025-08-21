# laboratory/forms.py
from django import forms
from django.forms import CheckboxSelectMultiple
from .models import LabRequest, LabRequestItem, Test, TestGroup
from django import forms
from django.forms import inlineformset_factory
from .models import TestResult, TestOrder

from django import forms
from .models import LabRequest, Test, TestGroup
from django import forms
from .models import Test, TestGroup, LabRequestItem  # أضف ما تحتاجه
from .models import Test



class TestForm(forms.ModelForm):
    # لو الموديل عنده ثابت RESULT_TYPES استخدمه؛
    # غير كده وفّر اختيارات افتراضية.
    RESULT_CHOICES = getattr(
        Test,
        "RESULT_TYPES",
        (("num", "رقمي"), ("text", "نصي"), ("bool", "ثنائي")),
    )

    class Meta:
        model = Test
        fields = ["category", "english_name", "unit", "ref_min", "ref_max", "result_type", "active"]
        widgets = {
            "category":    forms.Select(attrs={"class": "form-select"}),
            "english_name":forms.TextInput(attrs={"class": "form-control"}),
            "unit":        forms.TextInput(attrs={"class": "form-control"}),
            "ref_min":     forms.NumberInput(attrs={"class": "form-control", "step": "any"}),
            "ref_max":     forms.NumberInput(attrs={"class": "form-control", "step": "any"}),
           # "result_type": forms.Select(attrs={"class": "form-select"}, choices=RESULT_CHOICES), # pyright: ignore[reportUndefinedVariable]
            "active":      forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # لو ref_min/ref_max/unit اختيارية بالموديل خليك هادئ،
        # لو مش اختيارية في الموديل، خلِّيها اختيارية في الفورم:
        self.fields["unit"].required = False
        self.fields["ref_min"].required = False
        self.fields["ref_max"].required = False

        # حط قيمة افتراضية للـ result_type لو المستخدم ما اختارش
        if not self.instance.pk and not self.initial.get("result_type"):
            self.fields["result_type"].initial = "num"

# فورم إنشاء/تعديل تحليل
class TestForm(forms.ModelForm):
    class Meta:
        model = Test
        # استخدم فقط الحقول الموجودة فعليًا في الموديل Test
        fields = ["category", "english_name", "unit", "ref_min", "ref_max", "result_type", "active"]

# فورم إنشاء/تعديل مجموعة تحاليل
class TestGroupForm(forms.ModelForm):
    name = forms.CharField(
        label="اسم المجموعة",
        max_length=100,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "مثال: CBC Panel",
            "autocomplete": "off",
        })
    )

    tests = forms.ModelMultipleChoiceField(
        queryset=Test.objects.filter(active=True).order_by("english_name"),
        required=False,
        widget=forms.SelectMultiple(attrs={
            "class": "form-select", "size": "12", "id": "id_tests"
        }),
        label="التحاليل"
    )

    class Meta:
        model = TestGroup   # ✅ هذا هو الصحيح
        fields = ["name", "tests"]  # ✅ فقط الحقول المتعلقة بالمجموعة

    def clean(self):
        cleaned = super().clean()
        tests = cleaned.get("tests")
        if not tests or tests.count() == 0:
            raise forms.ValidationError("يجب اختيار تحليل واحد على الأقل.")
        return cleaned
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

# فورم-ست مرتبط بالأمر (يُستخدم في add_results_for_order)
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


class LabRequestForm(forms.ModelForm):
    tests = forms.ModelMultipleChoiceField(
        queryset=Test.objects.filter(active=True).order_by("english_name"),
        required=False,
        widget=forms.CheckboxSelectMultiple
    )
    class Meta:
        model = LabRequest
        fields = ["group", "tests"]

    class Meta:
        model = LabRequest
        fields = ("group", "tests")

    def clean(self):
        cleaned = super().clean()
        group = cleaned.get("group")
        tests = cleaned.get("tests")

        if not group and (not tests or len(tests) == 0):
            raise forms.ValidationError("اختر مجموعة أو واحدًا على الأقل من التحاليل.")
        return cleaned


class LabRequestItemResultForm(forms.ModelForm):
    class Meta:
        model = LabRequestItem
        fields = (
            "value_num", "value_bool", "value_text",
            "unit", "ref_min", "ref_max", "notes",
        )
        widgets = {"notes": forms.Textarea(attrs={"rows": 2})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        t = self.instance.test
        # ضبط الحقول بناءً على نوع التحليل
        if t.result_type == Test.RESULT_TYPE_NUMERIC:
            # أظهر الرقمي، أخفِ الباقي
            self.fields["value_bool"].widget = forms.HiddenInput()
            self.fields["value_text"].widget = forms.HiddenInput()
            if not self.instance.unit:
                self.fields["unit"].initial = t.unit
            if self.instance.ref_min is None:
                self.fields["ref_min"].initial = t.ref_min
            if self.instance.ref_max is None:
                self.fields["ref_max"].initial = t.ref_max

        elif t.result_type == Test.RESULT_TYPE_BOOLEAN:
            self.fields["value_num"].widget  = forms.HiddenInput()
            self.fields["unit"].widget       = forms.HiddenInput()
            self.fields["ref_min"].widget    = forms.HiddenInput()
            self.fields["ref_max"].widget    = forms.HiddenInput()
            self.fields["value_text"].widget = forms.HiddenInput()

        else:  # TEXT
            self.fields["value_num"].widget  = forms.HiddenInput()
            self.fields["unit"].widget       = forms.HiddenInput()
            self.fields["ref_min"].widget    = forms.HiddenInput()
            self.fields["ref_max"].widget    = forms.HiddenInput()
            self.fields["value_bool"].widget = forms.HiddenInput()

