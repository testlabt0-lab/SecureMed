"""
Device Fingerprinting & Forensic Evidence Model.

Stores detailed device information for security auditing and forensic analysis.
This model helps identify and track devices used in attacks, providing evidence
that can be used to attribute malicious activity to specific devices.
"""
import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone


class DeviceFingerprint(models.Model):
    """
    Stores comprehensive device fingerprint data for forensic analysis.
    
    This model captures:
    - Hardware identifiers (MAC address when available)
    - Software fingerprints (User-Agent, platform details)
    - Network information (IP, X-Forwarded headers)
    - Behavioral patterns (request timing, typical paths)
    - TLS/SSL fingerprinting data
    - Canvas/Audio fingerprint hashes (from frontend)
    """
    
    # Unique identifier for this fingerprint record
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Link to user if authenticated
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='device_fingerprints',
        help_text="Associated user account (if authenticated)"
    )
    
    # === Hardware Identifiers ===
    mac_address = models.CharField(
        max_length=17,
        null=True,
        blank=True,
        db_index=True,
        help_text="MAC address (when available via network headers or client-side JS)"
    )
    
    # === Device Fingerprint Hash ===
    # Combined hash of all fingerprint data for quick lookup
    fingerprint_hash = models.CharField(
        max_length=64,
        db_index=True,
        unique=True,
        help_text="SHA-256 hash of combined fingerprint data"
    )
    
    # === Software/Platform Information ===
    user_agent = models.TextField(
        null=True,
        blank=True,
        help_text="Full User-Agent string"
    )
    
    platform = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Operating system platform"
    )
    
    browser = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Browser name and version"
    )
    
    device_type = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        choices=[
            ('desktop', 'Desktop'),
            ('mobile', 'Mobile'),
            ('tablet', 'Tablet'),
            ('bot', 'Bot/Crawler'),
            ('unknown', 'Unknown'),
        ],
        help_text="Type of device"
    )
    
    # === Network Information ===
    ip_address = models.GenericIPAddressField(
        protocol='both',
        db_index=True,
        help_text="Client IP address"
    )
    
    ip_country = models.CharField(
        max_length=2,
        null=True,
        blank=True,
        help_text="Country code from IP geolocation"
    )
    
    ip_city = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="City from IP geolocation"
    )
    
    x_forwarded_for = models.TextField(
        null=True,
        blank=True,
        help_text="X-Forwarded-For header chain"
    )
    
    x_real_ip = models.GenericIPAddressField(
        protocol='both',
        null=True,
        blank=True,
        help_text="X-Real-IP header"
    )
    
    # === Advanced Fingerprinting Data ===
    screen_resolution = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text="Screen resolution (e.g., '1920x1080')"
    )
    
    # Browser timezone field (renamed to avoid conflict with django.utils.timezone)
    browser_timezone = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="Browser timezone"
    )
    
    language = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text="Browser language preference"
    )
    
    # Canvas fingerprint hash (from frontend JS)
    canvas_fingerprint = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        help_text="Hash of canvas fingerprint data"
    )
    
    # WebRTC leak IP (if exposed)
    webrtc_ip = models.GenericIPAddressField(
        protocol='both',
        null=True,
        blank=True,
        help_text="IP leaked via WebRTC"
    )
    
    # TLS fingerprint (JA3 hash)
    tls_fingerprint = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        help_text="JA3 TLS fingerprint hash"
    )
    
    # === Behavioral Patterns ===
    first_seen = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        help_text="First time this device was seen"
    )
    
    last_seen = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        help_text="Last time this device was seen"
    )
    
    request_count = models.PositiveIntegerField(
        default=1,
        help_text="Total number of requests from this device"
    )
    
    # === Security Flags ===
    is_suspicious = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Flagged as suspicious by security systems"
    )
    
    is_blacklisted = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Blacklisted device"
    )
    
    threat_score = models.PositiveSmallIntegerField(
        default=0,
        help_text="Threat score (0-100, higher = more dangerous)"
    )
    
    # === Forensic Evidence ===
    attack_signatures = models.JSONField(
        default=list,
        blank=True,
        help_text="List of attack signatures detected from this device"
    )
    
    waf_blocks = models.PositiveIntegerField(
        default=0,
        help_text="Number of WAF blocks triggered by this device"
    )
    
    failed_logins = models.PositiveIntegerField(
        default=0,
        help_text="Number of failed login attempts"
    )
    
    # Additional metadata
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional fingerprint metadata"
    )
    
    # Evidence notes (for forensic analysis)
    forensic_notes = models.TextField(
        blank=True,
        help_text="Forensic analyst notes about this device"
    )
    
    class Meta:
        ordering = ['-last_seen']
        indexes = [
            models.Index(fields=['fingerprint_hash']),
            models.Index(fields=['ip_address', '-last_seen']),
            models.Index(fields=['mac_address']),
            models.Index(fields=['is_suspicious']),
            models.Index(fields=['threat_score']),
        ]
        verbose_name = "Device Fingerprint"
        verbose_name_plural = "Device Fingerprints"
    
    def __str__(self):
        return f"Device {self.fingerprint_hash[:16]}... ({self.ip_address})"
    
    def update_activity(self):
        """Update last seen timestamp and request count."""
        self.last_seen = timezone.now()
        self.request_count += 1
        self.save(update_fields=['last_seen', 'request_count'])
    
    def add_threat_indicator(self, indicator_type, details=None):
        """Add a threat indicator to this device."""
        if details is None:
            details = {}
        
        # Update threat score
        score_increase = {
            'waf_block': 5,
            'failed_login': 2,
            'sql_injection': 15,
            'xss_attempt': 15,
            'brute_force': 10,
            'suspicious_behavior': 5,
        }.get(indicator_type, 3)
        
        self.threat_score = min(100, self.threat_score + score_increase)
        
        # Add to attack signatures
        signature = {
            'type': indicator_type,
            'timestamp': timezone.now().isoformat(),
            'details': details,
        }
        
        if not isinstance(self.attack_signatures, list):
            self.attack_signatures = []
        
        self.attack_signatures.append(signature)
        
        # Flag as suspicious if threshold reached
        if self.threat_score >= 30:
            self.is_suspicious = True
        
        if self.threat_score >= 70:
            self.is_blacklisted = True
        
        self.save(update_fields=['threat_score', 'attack_signatures', 
                                  'is_suspicious', 'is_blacklisted'])
    
    @classmethod
    def get_or_create_from_request(cls, request, fingerprint_data):
        """
        Get or create a device fingerprint from request data.
        
        Args:
            request: Django request object
            fingerprint_data: Dict containing fingerprint information
        
        Returns:
            tuple: (DeviceFingerprint instance, created boolean)
        """
        fingerprint_hash = fingerprint_data.get('fingerprint_hash')
        
        if not fingerprint_hash:
            # Generate hash from available data
            import hashlib
            hash_source = f"{request.META.get('HTTP_USER_AGENT', '')}{request.META.get('REMOTE_ADDR', '')}"
            fingerprint_hash = hashlib.sha256(hash_source.encode()).hexdigest()
        
        # Try to get existing fingerprint
        try:
            fp = cls.objects.get(fingerprint_hash=fingerprint_hash)
            fp.update_activity()
            return fp, False
        except cls.DoesNotExist:
            # Create new fingerprint
            fp = cls(
                fingerprint_hash=fingerprint_hash,
                ip_address=request.META.get('REMOTE_ADDR', '0.0.0.0'),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                x_forwarded_for=request.META.get('HTTP_X_FORWARDED_FOR', ''),
                **fingerprint_data
            )
            
            # Link to user if authenticated
            if hasattr(request, 'user') and request.user.is_authenticated:
                fp.user = request.user
            
            fp.save()
            return fp, True


class ForensicEvidence(models.Model):
    """
    Detailed forensic evidence log for security incidents.
    
    This model stores granular evidence that can be used in investigations
    to prove that a specific device was involved in malicious activity.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Related device fingerprint
    device = models.ForeignKey(
        DeviceFingerprint,
        on_delete=models.CASCADE,
        related_name='forensic_evidence',
        help_text="Associated device fingerprint"
    )
    
    # Evidence type
    evidence_type = models.CharField(
        max_length=50,
        choices=[
            ('network', 'Network Evidence'),
            ('application', 'Application Evidence'),
            ('authentication', 'Authentication Evidence'),
            ('injection', 'Injection Attack Evidence'),
            ('session', 'Session Hijacking Evidence'),
            ('data_exfil', 'Data Exfiltration Evidence'),
            ('other', 'Other Evidence'),
        ],
        help_text="Type of forensic evidence"
    )
    
    # Timestamp of evidence collection
    timestamp = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        help_text="When the evidence was collected"
    )
    
    # Evidence data (structured)
    evidence_data = models.JSONField(
        default=dict,
        help_text="Structured evidence data"
    )
    
    # Raw request/response data (if applicable)
    raw_request = models.TextField(
        blank=True,
        help_text="Raw HTTP request data"
    )
    
    raw_response = models.TextField(
        blank=True,
        help_text="Raw HTTP response data"
    )
    
    # Chain of custody
    collected_by = models.CharField(
        max_length=100,
        default='system',
        help_text="Who/what collected this evidence"
    )
    
    # Integrity hash (to prove evidence hasn't been tampered)
    integrity_hash = models.CharField(
        max_length=64,
        help_text="SHA-256 hash for evidence integrity verification"
    )
    
    # Case/incident reference
    incident_id = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        db_index=True,
        help_text="Related incident/case ID"
    )
    
    # Admissibility notes (for legal proceedings)
    admissibility_notes = models.TextField(
        blank=True,
        help_text="Notes on evidence admissibility and collection method"
    )
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['device', '-timestamp']),
            models.Index(fields=['evidence_type']),
            models.Index(fields=['incident_id']),
        ]
        verbose_name = "Forensic Evidence"
        verbose_name_plural = "Forensic Evidence Logs"
    
    def __str__(self):
        return f"Evidence #{self.id.short()} - {self.evidence_type} at {self.timestamp}"
    
    def save(self, *args, **kwargs):
        """Generate integrity hash before saving."""
        import hashlib
        
        if not self.integrity_hash:
            # Create hash of evidence data for integrity verification
            hash_source = f"{self.evidence_type}{self.timestamp.isoformat()}{str(self.evidence_data)}{self.raw_request}"
            self.integrity_hash = hashlib.sha256(hash_source.encode()).hexdigest()
        
        super().save(*args, **kwargs)
