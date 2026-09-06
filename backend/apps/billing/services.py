import uuid
from django.utils import timezone
from decimal import Decimal

class StripePaymentService:
    """Mock service to handle Stripe payments."""
    
    @staticmethod
    def create_payment_intent(invoice):
        """Mock creating a payment intent with Stripe."""
        # In a real app, this would call stripe.PaymentIntent.create()
        return {
            "id": f"pi_{uuid.uuid4().hex[:14]}",
            "client_secret": f"pi_{uuid.uuid4().hex[:14]}_secret_{uuid.uuid4().hex[:14]}",
            "amount": float(invoice.final_total_with_vat),
            "currency": "SAR",
            "status": "requires_payment_method"
        }
        
    @staticmethod
    def process_webhook(payload, sig_header):
        """Mock processing a webhook from Stripe."""
        # In a real app, verify signature and process event
        return {"status": "success", "event": "payment_intent.succeeded"}

class InsuranceService:
    """Mock service to handle TPA (Third Party Administrator) Insurance Claims."""
    
    @staticmethod
    def submit_claim(claim):
        """Mock submitting a claim to an insurance API."""
        # Simulating an API call to a TPA like NPHIES (Saudi Arabia) or similar.
        
        # We will auto-approve 80% of claims for demo purposes.
        import random
        is_approved = random.choice([True, True, True, True, False])
        
        claim.resolved_at = timezone.now()
        
        if is_approved:
            claim.status = 'APPROVED'
            claim.approved_amount = claim.claim_amount
        else:
            claim.status = 'REJECTED'
            claim.rejection_reason = "Service not covered under the current policy limits."
            claim.approved_amount = Decimal('0.00')
            
        claim.save(update_fields=['status', 'approved_amount', 'resolved_at', 'rejection_reason'])
        
        # Update the invoice status
        invoice = claim.invoice
        if claim.status == 'APPROVED':
            invoice.insurance_covered = claim.approved_amount
            invoice.patient_payable = invoice.total_amount - invoice.discount - invoice.insurance_covered
            invoice.status = 'UNPAID' # Waiting for patient to pay the rest (if any)
            if invoice.patient_payable <= 0:
                invoice.status = 'PAID'
        else:
            invoice.patient_payable = invoice.total_amount - invoice.discount
            invoice.status = 'UNPAID'
            
        invoice.save(update_fields=['insurance_covered', 'patient_payable', 'status'])
        
        return claim
