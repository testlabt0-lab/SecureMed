import uuid
import stripe
import requests
from django.conf import settings
from django.utils import timezone
from decimal import Decimal

stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', '')

class StripePaymentService:
    """Real service to handle Stripe payments."""
    
    @staticmethod
    def create_payment_intent(invoice):
        """Create a payment intent with Stripe."""
        if not stripe.api_key:
            # Fallback for dev if no key is provided
            return {
                "id": f"pi_{uuid.uuid4().hex[:14]}",
                "client_secret": f"pi_{uuid.uuid4().hex[:14]}_secret_{uuid.uuid4().hex[:14]}",
                "amount": float(invoice.final_total_with_vat),
                "currency": "SAR",
                "status": "requires_payment_method"
            }
            
        amount_cents = int(invoice.final_total_with_vat * 100)
        try:
            intent = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency='sar',
                metadata={'invoice_id': str(invoice.id)}
            )
            return {
                "id": intent.id,
                "client_secret": intent.client_secret,
                "amount": float(intent.amount / 100.0),
                "currency": intent.currency.upper(),
                "status": intent.status
            }
        except stripe.error.StripeError as e:
            raise Exception(f"Stripe error: {str(e)}")
        
    @staticmethod
    def process_webhook(payload, sig_header):
        """Process a webhook from Stripe."""
        endpoint_secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', '')
        if not endpoint_secret:
            return {"status": "success", "event": "payment_intent.succeeded"} # fallback
            
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, endpoint_secret
            )
            return {"status": "success", "event": event.type}
        except ValueError as e:
            raise Exception("Invalid payload")
        except stripe.error.SignatureVerificationError as e:
            raise Exception("Invalid signature")

class InsuranceService:
    """Service to handle TPA (Third Party Administrator) Insurance Claims via HTTP API."""
    
    @staticmethod
    def submit_claim(claim):
        """Submit a claim to an insurance API."""
        api_url = getattr(settings, 'INSURANCE_API_URL', None)
        api_key = getattr(settings, 'INSURANCE_API_KEY', '')
        
        claim.resolved_at = timezone.now()
        
        if api_url:
            try:
                response = requests.post(
                    f"{api_url}/claims/submit",
                    json={
                        "claim_id": str(claim.id),
                        "amount": float(claim.claim_amount),
                        "patient_nid": claim.invoice.patient.national_id if claim.invoice.patient else "",
                        "diagnosis": "General" # Ideally fetched from consultation
                    },
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=10
                )
                response.raise_for_status()
                data = response.json()
                is_approved = data.get("status") == "APPROVED"
                rejection_reason = data.get("rejection_reason", "")
                approved_amount = Decimal(str(data.get("approved_amount", "0.00")))
            except Exception as e:
                claim.status = 'REJECTED'
                claim.rejection_reason = f"API Error: {str(e)}"
                claim.approved_amount = Decimal('0.00')
                is_approved = False
        else:
            # Deterministic fallback for dev based on amount (avoid random.choice)
            is_approved = claim.claim_amount < Decimal('5000.00')
            rejection_reason = "Amount exceeds automatic approval limit." if not is_approved else ""
            approved_amount = claim.claim_amount if is_approved else Decimal('0.00')
            
        if is_approved:
            claim.status = 'APPROVED'
            claim.approved_amount = approved_amount
        else:
            if claim.status != 'REJECTED': # If not already set by exception
                claim.status = 'REJECTED'
                claim.rejection_reason = rejection_reason
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
