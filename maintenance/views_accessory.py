"""
ملف views_accessory.py - إدارة ملحقات الأجهزة الطبية

هذا الملف بيحتوي على كل الـ views اللي بتتعامل مع ملحقات الأجهزة في النظام:
- عرض قائمة الملحقات
- إضافة ملحق جديد
- تعديل الملحقات الموجودة
- حذف الملحقات
- مسح الباركود للملحقات
- طلبات نقل الملحقات
- الموافقة على النقل
- سجل النقل

الملف بيستخدم نظام QR codes لتتبع الملحقات وبيحافظ على سجل كامل لجميع العمليات
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.db import transaction

from .models import Device, DeviceAccessory, AccessoryTransaction, AccessoryTransferRequest, AccessoryTransferLog
from .forms import DeviceAccessoryForm, AccessoryTransactionForm, AccessoryScanForm, AccessoryTransferForm


class DeviceAccessoryListView(LoginRequiredMixin, ListView):
    """
    عرض قائمة ملحقات الجهاز - كل الملحقات بتاع جهاز معين أو كل الملحقات
    """
    model = DeviceAccessory
    template_name = 'maintenance/accessory_list.html'
    context_object_name = 'accessories'
    paginate_by = 20  # عدد الملحقات في الصفحة الواحدة

    def get_queryset(self):
        """جيب الملحقات - إما بتاع جهاز معين أو كل الملحقات"""
        device_id = self.kwargs.get('device_id')
        if device_id:
            return DeviceAccessory.objects.filter(device_id=device_id)
        return DeviceAccessory.objects.all()

    def get_context_data(self, **kwargs):
        """أضف معلومات الجهاز للـ context عشان نعرف إيه الجهاز اللي بنشوف ملحقاته"""
        context = super().get_context_data(**kwargs)
        device_id = self.kwargs.get('device_id')
        if device_id:
            context['device'] = get_object_or_404(Device, id=device_id)
        return context


class DeviceAccessoryCreateView(LoginRequiredMixin, CreateView):
    """
    إضافة ملحق جديد لجهاز معين
    """
    model = DeviceAccessory
    form_class = DeviceAccessoryForm
    template_name = 'maintenance/accessory_form.html'

    def get_context_data(self, **kwargs):
        """أضف معلومات الجهاز للـ context"""
        context = super().get_context_data(**kwargs)
        device_id = self.kwargs.get('device_id')
        context['device'] = get_object_or_404(Device, id=device_id)
        return context

    def form_valid(self, form):
        """لما النموذج يكون صحيح، ربط الملحق بالجهاز"""
        device_id = self.kwargs.get('device_id')
        form.instance.device = get_object_or_404(Device, id=device_id)
        messages.success(self.request, 'تم إضافة الملحق بنجاح')
        return super().form_valid(form)

    def get_success_url(self):
        """رجع لصفحة ملحقات الجهاز بعد الإضافة"""
        return reverse('maintenance:device_accessories', kwargs={'device_id': self.object.device.id})


class DeviceAccessoryUpdateView(LoginRequiredMixin, UpdateView):
    """
    تعديل ملحق موجود
    """
    model = DeviceAccessory
    form_class = DeviceAccessoryForm
    template_name = 'maintenance/accessory_form.html'

    def get_context_data(self, **kwargs):
        """أضف معلومات الجهاز للـ context عشان النموذج يعرف إيه الجهاز"""
        context = super().get_context_data(**kwargs)
        # تأكد إن 'device' متاح في الـ template context للـ URL reversing والعناوين
        context['device'] = self.object.device
        return context

    def form_valid(self, form):
        """لما النموذج يكون صحيح، اعرض رسالة نجاح"""
        messages.success(self.request, 'تم تحديث الملحق بنجاح')
        return super().form_valid(form)

    def get_success_url(self):
        """رجع لصفحة ملحقات الجهاز بعد التعديل"""
        return reverse('maintenance:device_accessories', kwargs={'device_id': self.object.device.id})


class DeviceAccessoryDeleteView(LoginRequiredMixin, DeleteView):
    """
    حذف ملحق من الجهاز
    """
    model = DeviceAccessory
    template_name = 'maintenance/accessory_confirm_delete.html'

    def get_success_url(self):
        """رجع لصفحة ملحقات الجهاز بعد الحذف"""
        return reverse('maintenance:device_accessories', kwargs={'device_id': self.object.device.id})

    def delete(self, request, *args, **kwargs):
        """اعرض رسالة نجاح لما يتم الحذف"""
        messages.success(self.request, 'تم حذف الملحق بنجاح')
        return super().delete(request, *args, **kwargs)


@login_required
def accessory_scan_page(request, device_id):
    """
    صفحة مسح الباركود للملحقات - بتسمح للمستخدمين بمسح QR codes للملحقات
    
    الوظائف:
    - مسح باركود الملحق
    - تسجيل نوع العملية (تسليم، إرجاع، صيانة)
    - تحديث حالة الملحق
    - عرض العمليات الحديثة
    """
    device = get_object_or_404(Device, id=device_id)
    
    if request.method == 'POST':
        form = AccessoryScanForm(request.POST)
        if form.is_valid():
            barcode = form.cleaned_data['barcode']
            transaction_type = form.cleaned_data['transaction_type']
            notes = form.cleaned_data['notes']
            
            # حاول تلاقي الملحق بالـ QR token أو الباركود
            try:
                if barcode.startswith('accessory:'):
                    # لو الباركود بيبدأ بـ accessory: استخرج الـ ID
                    accessory_id = barcode.split(':')[1]
                    accessory = DeviceAccessory.objects.get(id=accessory_id, device=device)
                else:
                    # حاول تلاقي بالـ qr_token field
                    accessory = DeviceAccessory.objects.get(qr_token=barcode, device=device)
                
                # أنشئ عملية جديدة
                AccessoryTransaction.objects.create(
                    accessory=accessory,
                    transaction_type=transaction_type,
                    to_user=request.user,
                    notes=notes,
                    scanned_barcode=barcode,
                    is_confirmed=True,
                    confirmed_at=timezone.now()
                )
                
                # حدث حالة الملحق حسب نوع العملية
                if transaction_type == 'handover':
                    accessory.status = 'in_use'  # قيد الاستخدام
                elif transaction_type == 'return':
                    accessory.status = 'available'  # متاح
                elif transaction_type == 'maintenance':
                    accessory.status = 'maintenance'  # في الصيانة
                
                accessory.save()
                
                messages.success(request, f'تم تسجيل {accessory.name} - {accessory.get_status_display()}')
                return redirect('maintenance:accessory_scan', device_id=device_id)
                
            except DeviceAccessory.DoesNotExist:
                messages.error(request, 'لم يتم العثور على الملحق بهذا الباركود')
            except Exception as e:
                messages.error(request, f'خطأ في معالجة الباركود: {str(e)}')
    else:
        form = AccessoryScanForm()
    
    # جيب العمليات الحديثة لملحقات هذا الجهاز
    recent_transactions = AccessoryTransaction.objects.filter(
        accessory__device=device
    ).order_by('-created_at')[:10]
    
    context = {
        'device': device,
        'form': form,
        'recent_transactions': recent_transactions,
    }
    return render(request, 'maintenance/accessory_scan.html', context)


@login_required
@require_POST
def verify_device_accessories(request, device_id):
    """
    API endpoint للتحقق من إن جميع ملحقات الجهاز متاحة للنقل
    
    الوظيفة: بتتحقق من إن كل الملحقات في حالة 'متاح' قبل ما يتم نقل الجهاز
    """
    device = get_object_or_404(Device, id=device_id)
    
    # جيب كل الملحقات بتاعة هذا الجهاز
    accessories = device.accessories.all()
    missing_accessories = []
    
    for accessory in accessories:
        if accessory.status != 'available':
            missing_accessories.append({
                'id': accessory.id,
                'name': accessory.name,
                'status': accessory.get_status_display(),
                'qr_token': accessory.qr_token
            })
    
    if missing_accessories:
        return JsonResponse({
            'success': False,
            'message': 'يجب استلام جميع الملحقات قبل نقل الجهاز',
            'missing_accessories': missing_accessories
        })
    
    return JsonResponse({
        'success': True,
        'message': 'جميع الملحقات متاحة للنقل'
    })


@login_required
def accessory_detail(request, pk):
    """
    عرض تفاصيل ملحق معين مع سجل العمليات بتاعه
    """
    accessory = get_object_or_404(DeviceAccessory, id=pk)
    transactions = accessory.transactions.order_by('-created_at')
    
    context = {
        'accessory': accessory,
        'transactions': transactions,
    }
    return render(request, 'maintenance/accessory_detail.html', context)


@login_required
def accessory_qr_print(request, pk):
    """
    توليد QR code لطباعة ملصقات الملحقات
    
    الوظيفة: بتتأكد من وجود QR token وصورة، وتولدهم لو مش موجودين
    """
    accessory = get_object_or_404(DeviceAccessory, id=pk)
    # تأكد من وجود QR token والصورة
    if not accessory.qr_token:
        accessory.qr_token = accessory.generate_qr_token()
    if not accessory.qr_code:
        accessory.generate_qr_code()
    accessory.save(update_fields=['qr_token', 'qr_code'])

    context = {
        'accessory': accessory,
        'device': accessory.device,
    }
    return render(request, 'maintenance/accessory_qr_print.html', context)


@login_required
def transfer_accessory(request, pk):
    """
    طلب نقل ملحق لجهاز/قسم تاني
    
    الوظيفة: بتسمح للمستخدمين بطلب نقل ملحق من مكان لآخر
    """
    accessory = get_object_or_404(DeviceAccessory, id=pk)
    
    if request.method == 'POST':
        form = AccessoryTransferForm(request.POST)
        if form.is_valid():
            transfer_request = form.save(commit=False)
            transfer_request.accessory = accessory
            transfer_request.from_device = accessory.device
            transfer_request.from_department = accessory.device.department
            transfer_request.from_room = accessory.device.room
            transfer_request.requested_by = request.user
            transfer_request.save()
            
            messages.success(request, f'تم إرسال طلب نقل الملحق {accessory.name} بنجاح')
            return redirect('maintenance:accessory_detail', pk=accessory.id)
    else:
        form = AccessoryTransferForm()
    
    context = {
        'accessory': accessory,
        'form': form,
    }
    return render(request, 'maintenance/accessory_transfer.html', context)


@login_required
def approve_accessory_transfer(request, transfer_id):
    """
    الموافقة على طلب نقل ملحق
    
    الوظائف:
    - الموافقة على النقل وتحديث موقع الملحق
    - رفض النقل مع سبب
    - إنشاء سجل النقل
    """
    transfer_request = get_object_or_404(AccessoryTransferRequest, id=transfer_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'approve':
            with transaction.atomic():
                # وافق على النقل
                transfer_request.is_approved = True
                transfer_request.approved_by = request.user
                transfer_request.approved_at = timezone.now()
                transfer_request.save()
                
                # حدث موقع الملحق
                accessory = transfer_request.accessory
                old_device = accessory.device
                
                if transfer_request.to_device:
                    accessory.device = transfer_request.to_device
                
                accessory.save()
                
                # أنشئ سجل النقل
                AccessoryTransferLog.objects.create(
                    accessory=accessory,
                    from_device=transfer_request.from_device,
                    from_department=transfer_request.from_department,
                    from_room=transfer_request.from_room,
                    to_device=transfer_request.to_device,
                    to_department=transfer_request.to_department,
                    to_room=transfer_request.to_room,
                    transferred_by=request.user,
                    notes=f"نقل موافق عليه: {transfer_request.reason}"
                )
                
                messages.success(request, f'تم الموافقة على نقل الملحق {accessory.name} بنجاح')
                
        elif action == 'reject':
            # رفض النقل مع سبب
            transfer_request.rejection_reason = request.POST.get('rejection_reason', '')
            transfer_request.approved_by = request.user
            transfer_request.approved_at = timezone.now()
            transfer_request.save()
            
            messages.info(request, f'تم رفض طلب نقل الملحق {transfer_request.accessory.name}')
    
    return redirect('maintenance:accessory_detail', pk=transfer_request.accessory.id)


@login_required
def accessory_transfer_history(request, pk):
    """
    عرض سجل نقل ملحق معين
    
    الوظيفة: بتعرض كل طلبات النقل وسجلات النقل الفعلية لملحق معين
    """
    accessory = get_object_or_404(DeviceAccessory, id=pk)
    
    # جيب طلبات النقل والسجلات
    transfer_requests = AccessoryTransferRequest.objects.filter(
        accessory=accessory
    ).select_related(
        'from_device', 'to_device', 'from_department', 'to_department',
        'requested_by', 'approved_by'
    ).order_by('-requested_at')
    
    transfer_logs = AccessoryTransferLog.objects.filter(
        accessory=accessory
    ).select_related(
        'from_device', 'to_device', 'from_department', 'to_department',
        'transferred_by'
    ).order_by('-transferred_at')
    
    context = {
        'accessory': accessory,
        'transfer_requests': transfer_requests,
        'transfer_logs': transfer_logs,
    }
    return render(request, 'maintenance/accessory_transfer_history.html', context)
