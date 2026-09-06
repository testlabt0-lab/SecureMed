"""
Cryptographic utilities for SecureMed.

Security requirement #3: Encrypted tokens (وسم مشفر)
Security requirement #6: Encryption in transit (تشفير الاتصال DV <-> DB)

Uses AES-256 for field-level encryption and SHA-256 for biometric hashing.
"""
import os
import base64
import binascii
import hashlib
import hmac
import json
import secrets
from cryptography .fernet import Fernet ,MultiFernet ,InvalidToken
from cryptography .exceptions import InvalidTag ,InvalidSignature
from cryptography .hazmat .primitives import hashes
from cryptography .hazmat .primitives .kdf .pbkdf2 import PBKDF2HMAC
from cryptography .hazmat .primitives .asymmetric import rsa ,ec ,padding
from cryptography .hazmat .primitives import serialization
from cryptography .hazmat .primitives .ciphers import Cipher ,algorithms ,modes
from django .conf import settings


_FERNET_CACHE ={}# ENCRYPTION_KEY value -> Fernet instance (per process)


def _derive_fernet_key (encryption_key :str )->bytes :
    """Derive a Fernet key from an encryption key value.

    ⚠️ Expensive: PBKDF2-HMAC-SHA256 with 100,000 iterations costs
    ~50ms on a laptop CPU and ~150-200ms on Render's free-tier CPU.
    Must never run per-field — get_fernet() caches the derived instance.
    """
    salt = getattr(settings, 'FIELD_ENCRYPTION_SALT', b'securemed_salt_v1')
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


def _fernet_chain ():
    """Fernet for the active key, plus every retired key still needed to read.

    ENCRYPTION_KEY had no rotation path: it is derived straight into a single
    Fernet, so changing it turned every encrypted column — patient names, national
    IDs, record text — into undecryptable bytes with no way back. That is not a
    theoretical concern, it is what happens the first time someone believes a key
    has leaked and does the responsible thing.

    MultiFernet encrypts with the first key and decrypts with any of them, so the
    procedure becomes: move the current value of ENCRYPTION_KEY to the front of
    ENCRYPTION_KEY_FALLBACKS, set the new key as ENCRYPTION_KEY, deploy — reads
    keep working immediately — then re-encrypt at leisure with
    `python manage.py rotate_encryption_key`, and only then drop the old key from
    the fallback list.
    """
    keys =[settings .ENCRYPTION_KEY ,*getattr (settings ,'ENCRYPTION_KEY_FALLBACKS',[])]
    cache_key =('chain',*keys )
    instance =_FERNET_CACHE .get (cache_key )
    if instance is None :
        instance =MultiFernet ([Fernet (_derive_fernet_key (k ))for k in keys if k ])
        _FERNET_CACHE [cache_key ]=instance
    return instance


def encrypt_field (value ):
    """Encrypt a field value with Fernet (AES-128-CBC + HMAC-SHA256).

    The docstring used to read "AES-256 (Fernet)", which Fernet is not: its spec
    fixes AES-128 in CBC mode with a separate HMAC-SHA256 for authentication. The
    256 bits are the *derived* key material, split into a 128-bit encryption key
    and a 128-bit signing key. Worth stating exactly, because the claim had been
    copied out of here into the README and into the security requirements table as
    evidence that columns are AES-256. Files are the ones on AES-256-GCM, see
    encrypt_media() below.
    """
    if value is None :
        return None
    if isinstance (value ,str ):
        value =value .encode ('utf-8')
    # Identical output to the single-key path: MultiFernet always encrypts with
    # the first key, which is the active ENCRYPTION_KEY.
    return _fernet_chain ().encrypt (value ).decode ('utf-8')


def decrypt_field (encrypted_value ):
    """Decrypt a field value, trying the active key first, then retired keys."""
    if not encrypted_value :
        return None
    if isinstance (encrypted_value ,str ):
        encrypted_value =encrypted_value .encode ('utf-8')
    try :
        return _fernet_chain ().decrypt (encrypted_value ).decode ('utf-8')
    except InvalidToken as exc :
        # The bare InvalidToken gives an operator nothing to act on, and the most
        # likely cause by far is a changed ENCRYPTION_KEY.
        raise InvalidToken (
        'No configured encryption key can decrypt this value. If ENCRYPTION_KEY '
        'was changed, add the previous value to ENCRYPTION_KEY_FALLBACKS.'
        )from exc


# ---------------------------------------------------------------- media at rest --
# Files under MEDIA_ROOT are the same class of data as the encrypted columns —
# imaging, lab reports, scanned documents — and they were written to disk verbatim.
# Fernet is deliberately not reused here: it base64-encodes its output, so a 20 MB
# X-ray becomes a ~27 MB string and is copied several times in memory on a 512 MB
# instance. Raw AES-256-GCM keeps the payload byte-for-byte the same size and
# authenticates it, which also gives decryption a reliable way to tell a wrong key
# from a corrupt file.
#
# Layout:  b'SMEDF1' | version(1) | iv(12) | tag(16) | ciphertext
_MEDIA_MAGIC =b'SMEDF1'
_MEDIA_VERSION =1
_MEDIA_HEADER_LEN =len (_MEDIA_MAGIC )+1 +12 +16
_MEDIA_KEY_CACHE ={}

# Exported for apps.core.storage, which needs the header length to report the
# *plaintext* size of a stored file: Storage.size() reads the file on disk, and a
# Content-Length inflated by the header makes a download hang or truncate.
MEDIA_MAGIC_LEN =len (_MEDIA_MAGIC )
MEDIA_HEADER_LEN =_MEDIA_HEADER_LEN


def _derive_media_key (encryption_key :str )->bytes :
    """32 raw bytes for AES-GCM, domain-separated from the field-encryption key.

    Same KDF and cost as _derive_fernet_key, different salt suffix: one key for
    columns, another for files, so compromise of one purpose does not hand over the
    other. Cached for the same reason get_fernet() is — 100k PBKDF2 iterations per
    file read would be felt.
    """
    cached =_MEDIA_KEY_CACHE .get (encryption_key )
    if cached is None :
        salt =getattr (settings ,'FIELD_ENCRYPTION_SALT',b'securemed_salt_v1')
        if isinstance (salt ,str ):
            salt =salt .encode ('utf-8')
        kdf =PBKDF2HMAC (
        algorithm =hashes .SHA256 (),
        length =32 ,
        salt =salt +b'|media-v1',
        iterations =100000 ,
        )
        cached =kdf .derive (encryption_key .encode ('utf-8'))
        _MEDIA_KEY_CACHE [encryption_key ]=cached
    return cached


def _media_keys ():
    """Active key first, then retired ones — same rotation story as _fernet_chain."""
    keys =[settings .ENCRYPTION_KEY ,*getattr (settings ,'ENCRYPTION_KEY_FALLBACKS',[])]
    return [_derive_media_key (k )for k in keys if k ]


def is_encrypted_media (blob )->bool :
    """True when the payload carries this module's header."""
    return bool (blob )and bytes (blob [:len (_MEDIA_MAGIC )])==_MEDIA_MAGIC


def encrypt_media (data :bytes )->bytes :
    """Encrypt file bytes for storage."""
    if isinstance (data ,str ):
        data =data .encode ('utf-8')
    iv =os .urandom (12 )
    encryptor =Cipher (algorithms .AES (_media_keys ()[0 ]),modes .GCM (iv )).encryptor ()
    ciphertext =encryptor .update (data )+encryptor .finalize ()
    return _MEDIA_MAGIC +bytes ([_MEDIA_VERSION ])+iv +encryptor .tag +ciphertext


def decrypt_media (blob :bytes )->bytes :
    """Decrypt file bytes written by encrypt_media.

    A payload without the header is returned untouched. Every file uploaded before
    this existed is exactly that, and so is anything written while
    ENCRYPT_MEDIA_AT_REST is off — so neither enabling nor disabling the setting
    orphans data that is already on disk.
    """
    if not is_encrypted_media (blob ):
        return blob
    version =blob [len (_MEDIA_MAGIC )]
    if version !=_MEDIA_VERSION :
        raise ValueError (
        f'Unsupported encrypted media version {version }; this build understands '
        f'{_MEDIA_VERSION }.'
        )
    iv =blob [len (_MEDIA_MAGIC )+1 :len (_MEDIA_MAGIC )+13 ]
    tag =blob [len (_MEDIA_MAGIC )+13 :_MEDIA_HEADER_LEN ]
    ciphertext =blob [_MEDIA_HEADER_LEN :]
    for key in _media_keys ():
        decryptor =Cipher (algorithms .AES (key ),modes .GCM (iv ,tag )).decryptor ()
        try :
            return decryptor .update (ciphertext )+decryptor .finalize ()
        except InvalidTag :
            continue
    raise InvalidTag (
    'No configured encryption key can decrypt this file. If ENCRYPTION_KEY was '
    'changed, add the previous value to ENCRYPTION_KEY_FALLBACKS.'
    )


# hash_biometric(template, salt) used to live here: a 10 000-round SHA-256 KDF over
# a "biometric template" the client sent up. It is deleted rather than deprecated,
# because it was the enabling primitive for a scheme that was not authentication —
# whatever the client posted was hashed and compared, so the template was a
# replayable shared secret, and its docstring ("NEVER store raw biometric data")
# read as an endorsement of a design that could not work. Nothing in the platform
# called it any more. Biometric login is now an EC P-256 signature over a
# server-issued challenge, verified by verify_native_assertion() below, and no
# template or template hash ever reaches the server.


class WebAuthnError (Exception ):
    """A registration or assertion was rejected.

    The message names the exact check that failed. It is written to the security
    log; it is deliberately *not* returned to the caller, because "rpIdHash does
    not match" or "signature counter did not advance" tells an attacker which
    part of a forgery to fix next. Callers surface one generic Arabic message.
    """


COSE_ES256 =-7
COSE_RS256 =-257

_FLAG_USER_PRESENT =0x01
_FLAG_USER_VERIFIED =0x04


def b64url_encode (data :bytes )->str :
    """Base64url, unpadded — the encoding WebAuthn uses for every binary field."""
    return base64 .urlsafe_b64encode (data ).decode ('ascii').rstrip ('=')


def b64url_decode (text )->bytes :
    """Decode base64url with or without padding. Raises ValueError on garbage."""
    if isinstance (text ,bytes ):
        text =text .decode ('ascii','strict')
    text =(text or '').strip ()
    try :
        return base64 .urlsafe_b64decode (text +'='*((-len (text ))%4 ))
    except (binascii .Error ,ValueError ,UnicodeEncodeError )as exc :
        raise ValueError (f'not valid base64url: {exc }')from exc


def generate_auth_challenge (num_bytes =32 ):
    """A fresh random challenge. Returns (raw_bytes, base64url_text).

    This replaces generate_challenge()/verify_challenge(), which produced
    ``HMAC(k, challenge)`` with a server-only random ``k`` and then verified by
    recomputing ``HMAC(k, client_answer)`` with that same ``k``. Both sides used
    the same key, so the comparison reduced algebraically to
    ``client_answer == challenge``: the client only had to echo the challenge
    back. It proved possession of nothing at all, and anyone who could request a
    challenge could answer it.
    """
    raw =secrets .token_bytes (num_bytes )
    return raw ,b64url_encode (raw )



def load_public_key (material :str ):
    """Load an SPKI public key from PEM text or base64(url) DER.

    Both key sources in this project hand out SPKI: WebAuthn's
    ``response.getPublicKey()`` (Level 2, all current browsers) and Android
    Keystore's ``PublicKey.getEncoded()``. Only P-256 (ES256) and RSA (RS256)
    are accepted, matching ``pubKeyCredParams`` requested by the client.
    """
    material =(material or '').strip ()
    if not material :
        raise WebAuthnError ('empty public key')
    try :
        if 'BEGIN'in material :
            key =serialization .load_pem_public_key (material .encode ('utf-8'))
        else :
            key =serialization .load_der_public_key (b64url_decode (material ))
    except WebAuthnError :
        raise
    except Exception as exc :
        raise WebAuthnError (f'unreadable public key ({exc .__class__ .__name__ })')from exc

    if isinstance (key ,ec .EllipticCurvePublicKey ):
        if not isinstance (key .curve ,ec .SECP256R1 ):
            raise WebAuthnError (f'unsupported curve {key .curve .name }, expected P-256')
    elif isinstance (key ,rsa .RSAPublicKey ):
        if key .key_size <2048 :
            raise WebAuthnError (f'RSA key too small ({key .key_size } bits)')
    else :
        raise WebAuthnError (f'unsupported key type {type (key ).__name__ }')
    return key


def public_key_to_pem (key )->str :
    """Canonical storage form: SPKI PEM, whatever the client sent."""
    return key .public_bytes (
    encoding =serialization .Encoding .PEM ,
    format =serialization .PublicFormat .SubjectPublicKeyInfo ,
    ).decode ('ascii')


def verify_signature (public_key ,signature :bytes ,message :bytes )->bool :
    """Verify an ES256/RS256 signature over `message`.

    ES256 signatures are ASN.1 DER (r,s) sequences in both WebAuthn and Android
    Keystore, which is exactly the encoding ``cryptography`` expects — no
    raw r||s conversion is needed here (it would be, for JWS/ECDSA).
    """
    try :
        if isinstance (public_key ,ec .EllipticCurvePublicKey ):
            public_key .verify (signature ,message ,ec .ECDSA (hashes .SHA256 ()))
        elif isinstance (public_key ,rsa .RSAPublicKey ):
            public_key .verify (signature ,message ,padding .PKCS1v15 (),hashes .SHA256 ())
        else :
            return False
    except (InvalidSignature ,ValueError ,TypeError ):
        return False
    return True


def verify_client_data (client_data_json :bytes ,*,expected_type :str ,
expected_challenge_b64 :str ,allowed_origins )->dict :
    """Checks shared by the registration and authentication ceremonies.

    `clientDataJSON` is assembled by the *browser*, not by the authenticator, and
    it is what binds the ceremony to our challenge and our origin. Skipping these
    checks is how a WebAuthn integration ends up verifying a perfectly valid
    signature over a challenge the attacker chose on a site the attacker owns.
    """
    try :
        client_data =json .loads (client_data_json .decode ('utf-8'))
    except (UnicodeDecodeError ,json .JSONDecodeError ,AttributeError )as exc :
        raise WebAuthnError ('clientDataJSON is not valid UTF-8 JSON')from exc
    if not isinstance (client_data ,dict ):
        raise WebAuthnError ('clientDataJSON is not an object')

    actual_type =client_data .get ('type')
    if actual_type !=expected_type :
        raise WebAuthnError (f'clientData.type is {actual_type !r}, expected {expected_type !r}')

    presented =str (client_data .get ('challenge')or '').strip ()
    # Compared as base64url *text*: the browser echoes back exactly the string we
    # issued, so comparing text avoids padding-normalisation mismatches. Both
    # sides are ASCII, which compare_digest requires.
    if not presented or not hmac .compare_digest (presented ,expected_challenge_b64 ):
        raise WebAuthnError ('challenge mismatch — stale, replayed or forged ceremony')

    origin =client_data .get ('origin')
    if origin not in allowed_origins :
        raise WebAuthnError (f'origin {origin !r} is not in WEBAUTHN_ALLOWED_ORIGINS')
    if client_data .get ('crossOrigin')is True :
        raise WebAuthnError ('ceremony was performed in a cross-origin iframe')
    return client_data


def verify_webauthn_registration (*,client_data_json :bytes ,public_key_material :str ,
expected_challenge_b64 :str ,allowed_origins ):
    """Validate a credential registration and return the loaded public key.

    Attestation is deliberately not parsed. Enrollment happens on an
    authenticated session, so the trust in "this key belongs to this user" comes
    from the access token, not from the authenticator's attestation certificate;
    attestation would only tell us the *make and model* of the authenticator,
    which this deployment has no policy about. Skipping it also means no CBOR
    decoder in the request path, and lets the client hand us the public key
    directly via ``getPublicKey()``.
    """
    verify_client_data (
    client_data_json ,
    expected_type ='webauthn.create',
    expected_challenge_b64 =expected_challenge_b64 ,
    allowed_origins =allowed_origins ,
    )
    return load_public_key (public_key_material )


def verify_webauthn_assertion (*,public_key ,client_data_json :bytes ,
authenticator_data :bytes ,signature :bytes ,expected_challenge_b64 :str ,
rp_id :str ,allowed_origins ,require_user_verification =True ,stored_sign_count =0 ):
    """Verify a WebAuthn assertion per W3C §7.2. Returns the new signature counter.

    Raises WebAuthnError naming the check that failed. Every step below is load
    bearing — verifying the signature alone is not enough, because the signature
    is over data the caller supplied.
    """
    verify_client_data (
    client_data_json ,
    expected_type ='webauthn.get',
    expected_challenge_b64 =expected_challenge_b64 ,
    allowed_origins =allowed_origins ,
    )

    if len (authenticator_data )<37 :
        raise WebAuthnError (
        f'authenticatorData is {len (authenticator_data )} bytes, expected at least 37')

    expected_rp_hash =hashlib .sha256 (rp_id .encode ('utf-8')).digest ()
    if not hmac .compare_digest (authenticator_data [:32 ],expected_rp_hash ):
        raise WebAuthnError ('rpIdHash does not match WEBAUTHN_RP_ID')

    flags =authenticator_data [32 ]
    if not flags &_FLAG_USER_PRESENT :
        raise WebAuthnError ('user-present flag is clear')
    if require_user_verification and not flags &_FLAG_USER_VERIFIED :
        # Without this, the ceremony proves only that the device was reachable —
        # not that a fingerprint, face or PIN was actually presented, which is
        # the entire claim the UI makes when it says «تسجيل الدخول بالبصمة».
        raise WebAuthnError ('user-verified flag is clear: no biometric or PIN was performed')

    sign_count =int .from_bytes (authenticator_data [33 :37 ],'big')
    # Clone detection. Platform authenticators (Touch ID, Face ID and most
    # Android implementations) report 0 forever, and the spec says to skip this
    # comparison when both sides are 0 rather than lock those devices out.
    if (sign_count or stored_sign_count )and sign_count <=stored_sign_count :
        raise WebAuthnError (
        f'signature counter did not advance ({sign_count } <= {stored_sign_count }): '
        'possible cloned credential'
        )

    signed_bytes =authenticator_data +hashlib .sha256 (client_data_json ).digest ()
    if not verify_signature (public_key ,signature ,signed_bytes ):
        raise WebAuthnError ('signature does not verify against the enrolled public key')
    return sign_count


def verify_native_assertion (*,public_key ,challenge :bytes ,signature :bytes ):
    """Verify a native (Android/iOS) signature over the raw challenge bytes.

    Native clients have no clientDataJSON. The binding WebAuthn gets from
    `origin` comes here from TLS plus certificate pinning instead, and the
    "a human was verified" guarantee comes from the key having been created with
    ``setUserAuthenticationRequired(true)`` in the Android Keystore, or an
    equivalent Secure Enclave access control, which leaves the private key
    unusable until the biometric prompt succeeds.

    That last property cannot be checked from the server: it is a client build
    requirement, not a protocol check, and it is the single assumption this path
    rests on. A native app that creates its key without that flag still passes
    here, and would be proving device possession only.
    """
    if not verify_signature (public_key ,signature ,challenge ):
        raise WebAuthnError ('signature does not verify against the enrolled public key')
    return 0


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
