from django.views.generic.edit import CreateView, UpdateView, DeleteView
from .utils import emit_activity

class ActivityCreateMixin(CreateView):
    activity_operation_key = None  # مثال: "patient.create"
    def form_valid(self, form):
        response = super().form_valid(form)
        if self.activity_operation_key:
            emit_activity(self.activity_operation_key, instance=self.object, user=self.request.user, action="create")
        return response

class ActivityUpdateMixin(UpdateView):
    activity_operation_key = None  # مثال: "patient.update"
    def form_valid(self, form):
        response = super().form_valid(form)
        if self.activity_operation_key:
            emit_activity(self.activity_operation_key, instance=self.object, user=self.request.user, action="update")
        return response

class ActivityDeleteMixin(DeleteView):
    activity_operation_key = None  # مثال: "patient.delete"
    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.activity_operation_key:
            emit_activity(self.activity_operation_key, instance=self.object, user=request.user, action="delete")
        return super().delete(request, *args, **kwargs)