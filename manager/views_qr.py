from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
import os

@login_required
@require_http_methods(["POST"])
def generate_qr(request, entity_type, entity_id):
    if entity_type == 'bed':
        from .models import Bed
        obj = get_object_or_404(Bed, pk=entity_id)
    else:
        messages.error(request, "نوع الكيان غير مدعوم")
        return redirect('manager:bed_list')
    
    # توليد كود QR
    obj.generate_qr_code()
    obj.save()
    
    messages.success(request, "تم توليد كود QR بنجاح")
    return redirect('manager:bed_list')
