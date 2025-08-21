from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from .utils import emit_activity

@receiver(user_logged_in)
def on_login(sender, request, user, **kwargs):
    emit_activity("auth.login", user=user, action="login", extra={"username": user.get_username()})

@receiver(user_logged_out)
def on_logout(sender, request, user, **kwargs):
    emit_activity("auth.logout", user=user, action="logout", extra={"username": getattr(user, "username", None)})