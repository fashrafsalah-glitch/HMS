from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
import os

@login_required
@require_http_methods(["GET", "POST"])
def generate_qr(request, entity_type, entity_id):
    if entity_type == 'bed':
        from .models import Bed
        obj = get_object_or_404(Bed, pk=entity_id)
        redirect_url = 'manager:bed_list'
    elif entity_type == 'room':
        from .models import Room
        obj = get_object_or_404(Room, pk=entity_id)
        redirect_url = 'manager:room_detail'
        redirect_kwargs = {'pk': entity_id}
    else:
        messages.error(request, "نوع الكيان غير مدعوم")
        return redirect('manager:room_list')
    
    # توليد كود QR
    obj.generate_qr_code()
    obj.save()
    
    messages.success(request, "تم توليد كود QR بنجاح")
    
    if entity_type == 'room':
        return redirect(redirect_url, **redirect_kwargs)
    else:
        return redirect(redirect_url)
