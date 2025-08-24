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
        """Generate QR token in format: entity_type:id or special format for Patient"""
        model_name = self.__class__.__name__.lower()
        
        # Special format for Patient: patient:<id>|MRN:<mrn>|Name:<first_last>|DOB:<yyyy-mm-dd>
        if model_name == 'patient':
            mrn = getattr(self, 'mrn', '') or ''
            first_name = getattr(self, 'first_name', '') or ''
            last_name = getattr(self, 'last_name', '') or ''
            name = f"{first_name}_{last_name}".replace(' ', '_')
            
            # Get date of birth
            dob = ''
            if hasattr(self, 'date_of_birth') and self.date_of_birth:
                dob = self.date_of_birth.strftime('%Y-%m-%d')
            elif (getattr(self, 'birth_year', None) and 
                  getattr(self, 'birth_month', None) and 
                  getattr(self, 'birth_day', None)):
                dob = f"{self.birth_year:04d}-{self.birth_month:02d}-{self.birth_day:02d}"
            
            return f"patient:{self.pk}|MRN:{mrn}|Name:{name}|DOB:{dob}"
        
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
        
        filename = f"{self.qr_token.replace(':', '_').replace('|', '_')}.png"
        self.qr_code.save(filename, ContentFile(buffer.getvalue()), save=False)
        return self.qr_code
