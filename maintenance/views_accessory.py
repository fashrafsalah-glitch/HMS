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
from manager.models import Department, Room


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
    template_name = 'maintenance/add_accessory.html'

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


# تم نقل هذه الدالة إلى accessory_transfer_view في نهاية الملف


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
                transfer_request.status = 'approved'
                transfer_request.approved_by = request.user
                transfer_request.approved_at = timezone.now()
                transfer_request.save()
                
                # حدث موقع الملحق
                accessory = transfer_request.accessory
                old_device = accessory.device
                
                if transfer_request.to_device:
                    accessory.device = transfer_request.to_device
                else:
                    # إذا لم يتم تحديد جهاز، قم بإنشاء جهاز وهمي أو تحديث المعلومات
                    accessory.device = None
                
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
            transfer_request.status = 'rejected'
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


@login_required
def transfer_accessory(request, pk):
    """
    صفحة نقل الملحق - عرض فورم النقل مع AJAX للأقسام والغرف
    """
    accessory = get_object_or_404(DeviceAccessory, id=pk)
    
    if request.method == 'POST':
        form = AccessoryTransferForm(request.POST)
        if form.is_valid():
            # إنشاء طلب النقل
            transfer_request = AccessoryTransferRequest.objects.create(
                accessory=accessory,
                from_device=accessory.device,
                from_department=accessory.device.department,
                from_room=accessory.device.room,
                to_department=form.cleaned_data['to_department'],
                to_room=form.cleaned_data['to_room'],
                to_device=form.cleaned_data.get('to_device'),
                reason=form.cleaned_data['reason'],
                requested_by=request.user,
                is_approved=False
            )
            
            messages.success(request, 'تم إرسال طلب النقل بنجاح وسيتم مراجعته من قبل الإدارة')
            return redirect('maintenance:accessory_detail', pk=accessory.id)
    else:
        form = AccessoryTransferForm()
    
    context = {
        'accessory': accessory,
        'form': form,
    }
    return render(request, 'maintenance/accessory_transfer.html', context)


@login_required
def ajax_get_rooms(request):
    """
    AJAX endpoint لجلب الغرف حسب القسم - إرجاع JSON مباشر
    """
    department_id = request.GET.get('department_id')
    print(f"AJAX get_rooms called with department_id: {department_id}")
    
    if department_id:
        try:
            from manager.models import Room
            rooms = Room.objects.filter(department_id=department_id).values('id', 'number')
            rooms_list = []
            
            for room in rooms:
                rooms_list.append({
                    'id': room['id'],
                    'name': room['number'],  # استخدام number كـ name
                    'number': room['number']
                })
            
            print(f"Found {len(rooms_list)} rooms: {rooms_list}")
            
            # تحقق من وجود غرف
            if not rooms_list:
                print(f"No rooms found for department {department_id}")
                # جلب جميع الغرف للتحقق
                all_rooms = Room.objects.all().values('id', 'number', 'department_id')
                print(f"All rooms in system: {list(all_rooms)}")
            
            return JsonResponse(rooms_list, safe=False)
        except Exception as e:
            print(f"Error in ajax_get_rooms: {e}")
            import traceback
            traceback.print_exc()
            return JsonResponse({'error': str(e)}, status=500)
    
    print("No department_id provided")
    return JsonResponse([], safe=False)


@login_required
def ajax_get_devices(request):
    """
    AJAX endpoint لجلب الأجهزة حسب الغرفة
    """
    room_id = request.GET.get('room_id')
    print(f"AJAX get_devices called with room_id: {room_id}")
    
    if room_id:
        try:
            devices = Device.objects.filter(room_id=room_id).values('id', 'name')
            devices_list = list(devices)
            print(f"Found {len(devices_list)} devices: {devices_list}")
            return JsonResponse(devices_list, safe=False)
        except Exception as e:
            print(f"Error in ajax_get_devices: {e}")
            return JsonResponse({'error': str(e)}, status=500)
    
    print("No room_id provided")
    return JsonResponse([], safe=False)
