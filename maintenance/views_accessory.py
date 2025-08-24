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
    model = DeviceAccessory
    template_name = 'maintenance/accessory_list.html'
    context_object_name = 'accessories'
    paginate_by = 20

    def get_queryset(self):
        device_id = self.kwargs.get('device_id')
        if device_id:
            return DeviceAccessory.objects.filter(device_id=device_id)
        return DeviceAccessory.objects.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        device_id = self.kwargs.get('device_id')
        if device_id:
            context['device'] = get_object_or_404(Device, id=device_id)
        return context


class DeviceAccessoryCreateView(LoginRequiredMixin, CreateView):
    model = DeviceAccessory
    form_class = DeviceAccessoryForm
    template_name = 'maintenance/accessory_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        device_id = self.kwargs.get('device_id')
        context['device'] = get_object_or_404(Device, id=device_id)
        return context

    def form_valid(self, form):
        device_id = self.kwargs.get('device_id')
        form.instance.device = get_object_or_404(Device, id=device_id)
        messages.success(self.request, 'تم إضافة الملحق بنجاح')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('maintenance:device_accessories', kwargs={'device_id': self.object.device.id})


class DeviceAccessoryUpdateView(LoginRequiredMixin, UpdateView):
    model = DeviceAccessory
    form_class = DeviceAccessoryForm
    template_name = 'maintenance/accessory_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Ensure 'device' is available in the template context for URL reversing and titles
        context['device'] = self.object.device
        return context

    def form_valid(self, form):
        messages.success(self.request, 'تم تحديث الملحق بنجاح')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('maintenance:device_accessories', kwargs={'device_id': self.object.device.id})


class DeviceAccessoryDeleteView(LoginRequiredMixin, DeleteView):
    model = DeviceAccessory
    template_name = 'maintenance/accessory_confirm_delete.html'

    def get_success_url(self):
        return reverse('maintenance:device_accessories', kwargs={'device_id': self.object.device.id})

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'تم حذف الملحق بنجاح')
        return super().delete(request, *args, **kwargs)


@login_required
def accessory_scan_page(request, device_id):
    """Page for scanning accessory barcodes"""
    device = get_object_or_404(Device, id=device_id)
    
    if request.method == 'POST':
        form = AccessoryScanForm(request.POST)
        if form.is_valid():
            barcode = form.cleaned_data['barcode']
            transaction_type = form.cleaned_data['transaction_type']
            notes = form.cleaned_data['notes']
            
            # Try to find accessory by QR token or barcode
            try:
                if barcode.startswith('accessory:'):
                    accessory_id = barcode.split(':')[1]
                    accessory = DeviceAccessory.objects.get(id=accessory_id, device=device)
                else:
                    # Try to find by qr_token field
                    accessory = DeviceAccessory.objects.get(qr_token=barcode, device=device)
                
                # Create transaction
                AccessoryTransaction.objects.create(
                    accessory=accessory,
                    transaction_type=transaction_type,
                    to_user=request.user,
                    notes=notes,
                    scanned_barcode=barcode,
                    is_confirmed=True,
                    confirmed_at=timezone.now()
                )
                
                # Update accessory status based on transaction type
                if transaction_type == 'handover':
                    accessory.status = 'in_use'
                elif transaction_type == 'return':
                    accessory.status = 'available'
                elif transaction_type == 'maintenance':
                    accessory.status = 'maintenance'
                
                accessory.save()
                
                messages.success(request, f'تم تسجيل {accessory.name} - {accessory.get_status_display()}')
                return redirect('maintenance:accessory_scan', device_id=device_id)
                
            except DeviceAccessory.DoesNotExist:
                messages.error(request, 'لم يتم العثور على الملحق بهذا الباركود')
            except Exception as e:
                messages.error(request, f'خطأ في معالجة الباركود: {str(e)}')
    else:
        form = AccessoryScanForm()
    
    # Get recent transactions for this device's accessories
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
    """API endpoint to verify all device accessories are available for transfer"""
    device = get_object_or_404(Device, id=device_id)
    
    # Get all accessories for this device
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
    """Detail view for a specific accessory"""
    accessory = get_object_or_404(DeviceAccessory, id=pk)
    transactions = accessory.transactions.order_by('-created_at')
    
    context = {
        'accessory': accessory,
        'transactions': transactions,
    }
    return render(request, 'maintenance/accessory_detail.html', context)


@login_required
def accessory_qr_print(request, pk):
    """Generate QR code for printing accessory labels"""
    accessory = get_object_or_404(DeviceAccessory, id=pk)
    # Ensure QR token and image exist
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
    """Request transfer of accessory to another device/department"""
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
    """Approve accessory transfer request"""
    transfer_request = get_object_or_404(AccessoryTransferRequest, id=transfer_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'approve':
            with transaction.atomic():
                # Approve the transfer
                transfer_request.is_approved = True
                transfer_request.approved_by = request.user
                transfer_request.approved_at = timezone.now()
                transfer_request.save()
                
                # Update accessory location
                accessory = transfer_request.accessory
                old_device = accessory.device
                
                if transfer_request.to_device:
                    accessory.device = transfer_request.to_device
                
                accessory.save()
                
                # Create transfer log
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
            transfer_request.rejection_reason = request.POST.get('rejection_reason', '')
            transfer_request.approved_by = request.user
            transfer_request.approved_at = timezone.now()
            transfer_request.save()
            
            messages.info(request, f'تم رفض طلب نقل الملحق {transfer_request.accessory.name}')
    
    return redirect('maintenance:accessory_detail', pk=transfer_request.accessory.id)


@login_required
def accessory_transfer_history(request, pk):
    """View transfer history for an accessory"""
    accessory = get_object_or_404(DeviceAccessory, id=pk)
    
    # Get transfer requests and logs
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
