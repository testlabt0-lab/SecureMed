"""
Cryptographic utilities for SecureMed.

Security requirement #3: Encrypted tokens (وسم مشفر)
Security requirement #6: Encryption in transit (تشفير الاتصال DV <-> DB)

Uses AES-256 for field-level encryption and SHA-256 for biometric hashing.
"""
import os 
import base64 
import hashlib 
import hmac 
import secrets 
from cryptography .fernet import Fernet 
from cryptography .hazmat .primitives import hashes 
from cryptography .hazmat .primitives .kdf .pbkdf2 import PBKDF2HMAC 
from cryptography .hazmat .primitives .asymmetric import rsa ,padding 
from cryptography .hazmat .primitives import serialization 
from cryptography .hazmat .primitives .ciphers import Cipher ,algorithms ,modes 
from django .conf import settings 


_FERNET_CACHE ={}# Comment_311


def _derive_fernet_key (encryption_key :str )->bytes :
    """Derive a Fernet key from an encryption key value.

    ⚠️ Expensive: PBKDF2-HMAC-SHA256 with 100,000 iterations costs
    ~50ms on a laptop CPU and ~150-200ms on Render's free-tier CPU.
    Must never run per-field — get_fernet() caches the derived instance.
    """
    salt =b'securemed_salt_v1'# Comment_312
    kdf =PBKDF2HMAC (
    algorithm =hashes .SHA256 (),
    length =32 ,
    salt =salt ,
    iterations =100000 ,
    )
    return base64 .urlsafe_b64encode (kdf .derive (encryption_key .encode ('utf-8')))


def _get_fernet_key ():
    """Backward-compatible helper (uncached) for the active ENCRYPTION_KEY."""
    return _derive_fernet_key (settings .ENCRYPTION_KEY )


def get_fernet ():
    """Get Fernet instance for encryption/decryption.

    The PBKDF2 derivation is deterministic (static salt + fixed key), so the
    derived key is identical on every call — caching the Fernet instance per
    key value changes nothing cryptographically (same key ⇒ same ciphertext,
    fully compatible with all previously stored data), it only removes the
    repeated 100k-iteration KDF cost.

    Before this cache, every encrypted field paid ~150-200ms on Render:
    a 20-patient page (5 encrypted fields each) = 100 KDF runs ≈ 17s.
    """
    key =settings .ENCRYPTION_KEY 
    instance =_FERNET_CACHE .get (key )
    if instance is None :
        instance =Fernet (_derive_fernet_key (key ))
        _FERNET_CACHE [key ]=instance 
    return instance 


def encrypt_field (value ):
    """Encrypt a field value using AES-256 (Fernet)."""
    if value is None :
        return None 
    if isinstance (value ,str ):
        value =value .encode ('utf-8')
    return get_fernet ().encrypt (value ).decode ('utf-8')


def decrypt_field (encrypted_value ):
    """Decrypt a field value."""
    if not encrypted_value :
        return None 
    if isinstance (encrypted_value ,str ):
        encrypted_value =encrypted_value .encode ('utf-8')
    return get_fernet ().decrypt (encrypted_value ).decode ('utf-8')


def hash_biometric (template ,salt ):
    """
    Hash biometric template with salt using SHA-256.

    Security: NEVER store raw biometric data. Always store salted hash.
    """
    if isinstance (template ,str ):
        template =template .encode ('utf-8')
    if isinstance (salt ,str ):
        salt =salt .encode ('utf-8')

        # Comment_313
    hasher =hashlib .sha256 ()
    hasher .update (salt )
    hasher .update (template )

    # Comment_314
    digest =hasher .digest ()
    for _ in range (10000 ):
        h =hashlib .sha256 ()
        h .update (salt )
        h .update (digest )
        digest =h .digest ()

    return digest .hex ()


def generate_challenge ():
    """
    Generate a challenge-response pair for biometric authentication.

    Returns:
        tuple: (challenge, expected_response)
    """
    challenge =secrets .token_hex (32 )
    # Comment_315
    session_key =secrets .token_bytes (32 )
    expected_response =hmac .new (
    session_key ,challenge .encode ('utf-8'),hashlib .sha256 
    ).hexdigest ()
    return challenge ,f'{expected_response }:{session_key .hex ()}'


def verify_challenge (expected ,response ):
    """Verify challenge response."""
    try :
        expected_response ,session_key_hex =expected .split (':')
        session_key =bytes .fromhex (session_key_hex )
        computed =hmac .new (
        session_key ,response .encode ('utf-8'),hashlib .sha256 
        ).hexdigest ()
        return hmac .compare_digest (expected_response ,computed )
    except Exception :
        return False 


def generate_jwt_keypair ():
    """Generate RSA key pair for JWT signing (RS256)."""
    private_key =rsa .generate_private_key (
    public_exponent =65537 ,
    key_size =2048 ,
    )
    public_key =private_key .public_key ()

    private_pem =private_key .private_bytes (
    encoding =serialization .Encoding .PEM ,
    format =serialization .PrivateFormat .PKCS8 ,
    encryption_algorithm =serialization .NoEncryption (),
    )
    public_pem =public_key .public_bytes (
    encoding =serialization .Encoding .PEM ,
    format =serialization .PublicFormat .SubjectPublicKeyInfo ,
    )
    return private_pem .decode ('utf-8'),public_pem .decode ('utf-8')


def generate_aes_key ():
    """Generate a random AES-256 key."""
    return base64 .urlsafe_b64encode (os .urandom (32 )).decode ('utf-8')


def encrypt_with_aes (data ,key ):
    """Encrypt data with AES-256-GCM."""
    if isinstance (data ,str ):
        data =data .encode ('utf-8')
    if isinstance (key ,str ):
        key =base64 .urlsafe_b64decode (key .encode ('utf-8'))
    iv =os .urandom (12 )
    cipher =Cipher (algorithms .AES (key ),modes .GCM (iv ))
    encryptor =cipher .encryptor ()
    ciphertext =encryptor .update (data )+encryptor .finalize ()
    return base64 .urlsafe_b64encode (
    iv +encryptor .tag +ciphertext 
    ).decode ('utf-8')


def decrypt_with_aes (encrypted ,key ):
    """Decrypt AES-256-GCM encrypted data."""
    if isinstance (encrypted ,str ):
        encrypted =base64 .urlsafe_b64decode (encrypted .encode ('utf-8'))
    if isinstance (key ,str ):
        key =base64 .urlsafe_b64decode (key .encode ('utf-8'))

    iv =encrypted [:12 ]
    tag =encrypted [12 :28 ]
    ciphertext =encrypted [28 :]

    cipher =Cipher (algorithms .AES (key ),modes .GCM (iv ,tag ))
    decryptor =cipher .decryptor ()
    return (decryptor .update (ciphertext )+decryptor .finalize ()).decode ('utf-8')
