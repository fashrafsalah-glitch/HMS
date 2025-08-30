from django.db import models
from django.conf import settings
from django.core.files.base import ContentFile
from io import BytesIO
import qrcode


class QRCodeMixin(models.Model):
    """Mixin to add QR code functionality to any model"""
    qr_code = models.ImageField(upload_to='qr_codes/', blank=True, null=True)
    qr_token = models.CharField(max_length=200, unique=True, blank=True, null=True)
    
    class Meta:
        abstract = True
    
    def generate_qr_token(self):
        """Generate simple permanent QR token in format: entity_type:id"""
        model_name = self.__class__.__name__.lower()
        
        # Map model names to desired prefixes
        model_mapping = {
            'customuser': 'user',
            'deviceaccessory': 'accessory'
        }
        
        prefix = model_mapping.get(model_name, model_name)
        return f"{prefix}:{self.pk}"
    
    def generate_qr_code(self):
        """Generate QR code image"""
        if not self.qr_token:
            self.qr_token = self.generate_qr_token()
        
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(self.qr_token)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        
        filename = f"{self.qr_token.replace(':', '_')}.png"
        self.qr_code.save(filename, ContentFile(buffer.getvalue()), save=False)
        return self.qr_code
