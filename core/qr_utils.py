from django.db import models
import qrcode
from io import BytesIO
from django.core.files.base import ContentFile
from django.conf import settings
from urllib.parse import urlencode
from .secure_qr import SecureQRToken


class QRCodeMixin(models.Model):
    """Mixin to add QR code generation functionality to models
    Now uses secure tokens with HMAC signatures and full URL generation
    """
    qr_code = models.ImageField(upload_to='qr_codes/', blank=True, null=True)
    qr_token = models.CharField(max_length=200, unique=True, blank=True, null=True)
    
    class Meta:
        abstract = True
    
    def generate_qr_token(self, ephemeral=False, metadata=None):
        """
        Generate secure QR token for this entity
        """
        entity_type = self.__class__.__name__.lower()
        
        # Handle special cases for entity type mapping
        if entity_type == 'customuser':
            entity_type = 'user'
        elif entity_type == 'deviceaccessory':
            entity_type = 'accessory'
        
        return SecureQRToken.generate_token(
            entity_type=entity_type,
            entity_id=str(self.pk),
            ephemeral=ephemeral,
            metadata=metadata or {}
        )
    
    def generate_qr_url(self, token: str) -> str:
        """
        Generate full URL containing the token as URL parameter
        """
        base_url = f"{settings.QR_DOMAIN}/api/scan-qr/"
        return f"{base_url}?{urlencode({'token': token})}"
    
    def generate_qr_code(self, ephemeral=False, metadata=None):
        """
        Generate QR code image for this entity using secure tokens and full URLs
        """
        # Generate secure token
        token = self.generate_qr_token(ephemeral=ephemeral, metadata=metadata)
        
        # Generate full URL for mobile devices
        qr_url = self.generate_qr_url(token)
        
        # Update the qr_token field if not ephemeral
        if not ephemeral and hasattr(self, 'qr_token'):
            self.qr_token = token
        
        # Generate QR code image with full URL
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_url)  # Use full URL instead of raw token
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Save to BytesIO
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        # Generate filename based on entity type and ID (avoid sensitive data)
        entity_type = self.__class__.__name__.lower()
        filename = f"{entity_type}_{self.pk}_qr.png"
        
        # Save to model's qr_code field
        if hasattr(self, 'qr_code'):
            self.qr_code.save(
                filename,
                ContentFile(buffer.getvalue()),
                save=False
            )
        return self.qr_code
