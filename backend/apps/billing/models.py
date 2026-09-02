import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

class InsuranceProvider(models.Model):
    """Insurance companies (TPA)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('اسم الشركة'), max_length=255)
    contact_email = models.EmailField(_('البريد الإلكتروني'), blank=True)
    contact_phone = models.CharField(_('رقم الهاتف'), max_length=50, blank=True)
    api_endpoint = models.URLField(_('رابط التخاطب الآلي (API)'), blank=True)
    is_active = models.BooleanField(_('نشط'), default=True)

    class Meta:
        verbose_name = _('شركة تأمين')
        verbose_name_plural = _('شركات التأمين')

    def __str__(self):
        return self.name

class PatientInsurance(models.Model):
    """Patient's insurance policy."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, related_name='insurance_policies')
    provider = models.ForeignKey(InsuranceProvider, on_delete=models.CASCADE)
    policy_number = models.CharField(_('رقم البوليصة'), max_length=100)
    coverage_percentage = models.DecimalField(_('نسبة التغطية'), max_digits=5, decimal_places=2, default=100.00)
    expiry_date = models.DateField(_('تاريخ الانتهاء'))
    is_valid = models.BooleanField(_('صالح'), default=True)

    class Meta:
        verbose_name = _('تأمين المريض')
        verbose_name_plural = _('تأمينات المرضى')

    def __str__(self):
        return f"{self.patient} - {self.provider.name}"

class Invoice(models.Model):
    """Medical bill."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, related_name='invoices')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='invoices_created')
    
    total_amount = models.DecimalField(_('المبلغ الإجمالي'), max_digits=12, decimal_places=2, default=0.00)
    discount = models.DecimalField(_('الخصم'), max_digits=12, decimal_places=2, default=0.00)
    insurance_covered = models.DecimalField(_('تغطية التأمين'), max_digits=12, decimal_places=2, default=0.00)
    patient_payable = models.DecimalField(_('المبلغ المستحق على المريض'), max_digits=12, decimal_places=2, default=0.00)
    
    status = models.CharField(_('الحالة'), max_length=50, choices=[
        ('DRAFT', _('مسودة')),
        ('PENDING_INSURANCE', _('بانتظار موافقة التأمين')),
        ('UNPAID', _('غير مدفوعة')),
        ('PARTIAL', _('مدفوعة جزئياً')),
        ('PAID', _('مدفوعة')),
        ('CANCELLED', _('ملغاة')),
    ], default='DRAFT')
    
    created_at = models.DateTimeField(auto_now_add=True)
    due_date = models.DateTimeField(_('تاريخ الاستحقاق'), null=True, blank=True)

    class Meta:
        verbose_name = _('فاتورة')
        verbose_name_plural = _('الفواتير')
        ordering = ['-created_at']
        
    @property
    def vat_amount(self):
        """Calculates 15% VAT on the patient payable amount."""
        return float(self.patient_payable) * 0.15
        
    @property
    def final_total_with_vat(self):
        """Final amount patient has to pay including VAT."""
        return float(self.patient_payable) + self.vat_amount

    def process_payment(self, payment_method="CREDIT_CARD"):
        """Simulates payment gateway integration."""
        if self.status in ['PAID', 'CANCELLED']:
            return False, "الفاتورة مدفوعة مسبقاً أو ملغاة."
            
        # Simulate connecting to a payment gateway API
        gateway_response = {
            "status": "success",
            "transaction_id": f"TXN-{uuid.uuid4().hex[:8].upper()}",
            "amount_deducted": self.final_total_with_vat
        }
        
        if gateway_response["status"] == "success":
            self.status = 'PAID'
            self.save(update_fields=['status'])
            return True, gateway_response
        return False, "فشلت عملية الدفع."

class InvoiceItem(models.Model):
    """Items in the invoice (consultation, medicine, lab test)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    description = models.CharField(_('الوصف'), max_length=255)
    quantity = models.PositiveIntegerField(_('الكمية'), default=1)
    unit_price = models.DecimalField(_('سعر الوحدة'), max_digits=10, decimal_places=2)
    total_price = models.DecimalField(_('الإجمالي'), max_digits=10, decimal_places=2)

    def save(self, *args, **kwargs):
        self.total_price = self.quantity * self.unit_price
        super().save(*args, **kwargs)
