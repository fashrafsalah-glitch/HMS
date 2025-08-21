# manager/mixins.py
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin


class HospitalmanagerRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Allows access only to authenticated users that are linked to a Hospital.
    Adjust the condition to fit your auth model.
    """

    def test_func(self):
        user = self.request.user
        return user.is_authenticated and hasattr(user, "hospital")
