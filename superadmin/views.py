from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import TemplateView, UpdateView, ListView, CreateView, UpdateView, DeleteView
from django.shortcuts import redirect
from django.urls import reverse_lazy, reverse
from django.contrib.auth import logout
from django.contrib import messages
from django.views import View
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth.views import LoginView

from .forms import HospitalForm, SuperAdminSystemSettingsForm
from .models import Hospital, SystemSettings
from hr.models import CustomUser


class SuperAdminRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.role == 'super_admin'


class CustomLoginView(LoginView):
    template_name = 'registration/login.html'
    redirect_authenticated_user = True

    def get_redirect_url(self):
        user = self.request.user
        if user.is_authenticated:
            # حوّل حسب الدور
            if user.role == 'super_admin':
                return reverse_lazy('superadmin:hospital_list')
            elif user.role == 'hospital_manager':
                return reverse_lazy('manager:patient_list')
            elif user.role == 'hr':
                return reverse_lazy('hr:staff_list')
            elif user.role == 'doctor':
                # عدّل الوجهة المناسبة للطبيب (لو عندك صفحة للطبيب)
                return reverse_lazy('manager:patient_list')
            elif user.role == 'nurse':
                # مثال: صفحة جدول المناوبات
                return reverse_lazy('hr:shift_patient_list')
            elif user.role == 'technician':
                return reverse_lazy('maintenance:maintenance_list')
            else:
                # أي دور آخر - صفحة عامة آمنة
                return reverse_lazy('core:home')

        # مهم: لا ترجع صفحة login هنا نهائيًا
        return reverse_lazy('core:home')

    def get_success_url(self):
        return self.get_redirect_url()

# User Management Views
class UserListView(LoginRequiredMixin, SuperAdminRequiredMixin, ListView):
    model = CustomUser
    template_name = 'users/user_list.html'
    context_object_name = 'users'


class UserCreateView(LoginRequiredMixin, SuperAdminRequiredMixin, CreateView):
    model = CustomUser
    form_class = UserCreationForm
    template_name = 'users/user_form.html'
    success_url = reverse_lazy('superadmin:user_list')


class UserUpdateView(LoginRequiredMixin, SuperAdminRequiredMixin, UpdateView):
    model = CustomUser
    form_class = UserChangeForm
    template_name = 'users/user_form.html'
    success_url = reverse_lazy('superadmin:user_list')


class UserDeleteView(LoginRequiredMixin, SuperAdminRequiredMixin, DeleteView):
    model = CustomUser
    template_name = 'users/user_confirm_delete.html'
    success_url = reverse_lazy('superadmin:user_list')


# Hospital Management Views
class HospitalCreateView(LoginRequiredMixin, CreateView):
    model = Hospital
    form_class = HospitalForm
    template_name = 'hospitals/create_hospital.html'
    success_url = reverse_lazy('superadmin:hospital_list')

    def get(self, request, *args, **kwargs):
        if request.user.role != 'super_admin':
            messages.error(request, "Only Super Admins can create hospitals.")
        return super().get(request, *args, **kwargs)

    def form_valid(self, form):
        messages.success(self.request, f"Hospital '{form.instance.name}' and manager created successfully.")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, f"Error creating hospital: {form.errors.as_text()}")
        return super().form_invalid(form)


class HospitalListView(LoginRequiredMixin, SuperAdminRequiredMixin, ListView):
    model = Hospital
    template_name = 'hospitals/hospital_list.html'
    context_object_name = 'hospitals'


# System Settings View
class SuperAdminSystemSettingsUpdateView(LoginRequiredMixin, SuperAdminRequiredMixin, UpdateView):
    model = SystemSettings
    form_class = SuperAdminSystemSettingsForm
    template_name = 'system_settings/system_settings.html'
    success_url = reverse_lazy('superadmin:hospital_list')  # Changed from 'payroll_list'

    def get_object(self):
        system_settings = SystemSettings.objects.first()
        if not system_settings:
            system_settings = SystemSettings.objects.create()
        return system_settings

    def form_valid(self, form):
        messages.success(self.request, "System settings updated successfully.")
        return super().form_valid(form)


# Logout View
class CustomLogoutView(View):
    def post(self, request, *args, **kwargs):
        logout(request)
        return redirect('superadmin:login')

    def get(self, request, *args, **kwargs):
        return redirect('superadmin:login')