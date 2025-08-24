from django.db.models.signals import post_save
from django.dispatch import receiver
from django.apps import apps
from core.qr_utils import QRCodeMixin


@receiver(post_save)
def generate_qr_code_on_save(sender, instance, created, **kwargs):
    """
    Auto-generate QR codes for models that inherit from QRCodeMixin
    """
    # Only process instances that inherit from QRCodeMixin
    if isinstance(instance, QRCodeMixin):
        # Only generate if it's a new instance or QR code doesn't exist
        if created or not instance.qr_token or not instance.qr_code:
            try:
                # Generate QR token and code
                if not instance.qr_token:
                    instance.qr_token = instance.generate_qr_token()
                
                # Generate QR code image
                if not instance.qr_code:
                    instance.generate_qr_code()
                    # Save without triggering signals again
                    instance.save(update_fields=['qr_code', 'qr_token'])
                    
            except Exception as e:
                print(f"Error generating QR code for {instance}: {e}")


# Specific signal handlers for each model
from manager.models import Patient, Bed
from hr.models import CustomUser
from maintenance.models import Device, DeviceAccessory


@receiver(post_save, sender=Patient)
def generate_patient_qr_code(sender, instance, created, **kwargs):
    """Generate QR code for patients with special format"""
    if created or not instance.qr_token:
        try:
            instance.qr_token = instance.generate_qr_token()
            instance.generate_qr_code()
            # Use update to avoid triggering signals again
            Patient.objects.filter(pk=instance.pk).update(
                qr_token=instance.qr_token
            )
            instance.save(update_fields=['qr_code'])
        except Exception as e:
            print(f"Error generating Patient QR code: {e}")


@receiver(post_save, sender=Bed)
def generate_bed_qr_code(sender, instance, created, **kwargs):
    """Generate QR code for beds"""
    if created or not instance.qr_token:
        try:
            instance.qr_token = instance.generate_qr_token()
            instance.generate_qr_code()
            Bed.objects.filter(pk=instance.pk).update(
                qr_token=instance.qr_token
            )
            instance.save(update_fields=['qr_code'])
        except Exception as e:
            print(f"Error generating Bed QR code: {e}")


@receiver(post_save, sender=CustomUser)
def generate_user_qr_code(sender, instance, created, **kwargs):
    """Generate QR code for users (doctors, nurses, staff)"""
    if created or not instance.qr_token:
        try:
            instance.qr_token = instance.generate_qr_token()
            instance.generate_qr_code()
            CustomUser.objects.filter(pk=instance.pk).update(
                qr_token=instance.qr_token
            )
            instance.save(update_fields=['qr_code'])
        except Exception as e:
            print(f"Error generating User QR code: {e}")


@receiver(post_save, sender=DeviceAccessory)
def generate_accessory_qr_code(sender, instance, created, **kwargs):
    """Generate QR code for device accessories"""
    if created or not instance.qr_token:
        try:
            instance.qr_token = instance.generate_qr_token()
            instance.generate_qr_code()
            DeviceAccessory.objects.filter(pk=instance.pk).update(
                qr_token=instance.qr_token
            )
            instance.save(update_fields=['qr_code'])
        except Exception as e:
            print(f"Error generating DeviceAccessory QR code: {e}")


@receiver(post_save, sender='manager.Patient') 
def generate_patient_qr_code(sender, instance, created, **kwargs):
    """Generate QR code for patients - they already have QR functionality"""
    # Patients already have QR code generation in their save method
    pass


@receiver(post_save, sender='manager.Department')
def generate_department_qr_code(sender, instance, created, **kwargs):
    """Generate QR code for departments"""
    # We'll add QR fields to Department model via migration
    pass


@receiver(post_save, sender='manager.Bed')
def generate_bed_qr_code(sender, instance, created, **kwargs):
    """Generate QR code for beds"""
    # We'll add QR fields to Bed model via migration  
    pass
