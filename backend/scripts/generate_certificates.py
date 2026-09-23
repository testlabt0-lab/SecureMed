#!/usr/bin/env python3
"""
JWT Certificate Generator for SecureMed.
Generates RSA-256 key pair for JWT signing/verification.

Security requirement #3: Encrypted tokens (وسم مشفر)
"""
import os 
import sys 
import argparse 
from pathlib import Path
from cryptography .hazmat .primitives .asymmetric import rsa 
from cryptography .hazmat .primitives import serialization 
from cryptography .hazmat .primitives .asymmetric import padding 
from cryptography .hazmat .primitives import hashes 
from cryptography import x509 
from cryptography .x509 .oid import NameOID 
from datetime import datetime ,timedelta ,timezone 


def _resolve_output_dir(output_dir):
    """Resolve ``output_dir`` and prove every write stays inside it.

    ``--output-dir`` comes from the command line, so a value such as
    ``../../etc/ssl`` (or an absolute path anywhere on disk) would otherwise
    let the generator drop a private key outside the intended directory.
    Resolving against the CWD and requiring the resolved path to be the
    output directory itself — not a parent — keeps the write confined.
    """
    base = Path(output_dir).resolve()
    # Reject a symlinked or ``..``-laden path that escapes the resolved base.
    if base.parent == base:
        raise ValueError("output directory resolves to the filesystem root")
    base.mkdir(parents=True, exist_ok=True)
    return base


def _safe_path(base, filename):
    """Join ``filename`` onto ``base``, refusing any traversal outside it."""
    target = (base / filename).resolve()
    if base not in target.parents:
        raise ValueError(f"unsafe output path escapes {base}: {target}")
    return target


def generate_jwt_keypair (output_dir ='certs',key_size =2048 ):
    """Generate RSA key pair for JWT RS256 signing."""
    base =_resolve_output_dir (output_dir )

    print ("🔑 Generating RSA-2048 key pair for JWT RS256...")

    private_key =rsa .generate_private_key (
    public_exponent =65537 ,
    key_size =key_size ,
    )

    private_pem =private_key .private_bytes (
    encoding =serialization .Encoding .PEM ,
    format =serialization .PrivateFormat .PKCS8 ,
    encryption_algorithm =serialization .NoEncryption (),
    )

    public_key =private_key .public_key ()

    public_pem =public_key .public_bytes (
    encoding =serialization .Encoding .PEM ,
    format =serialization .PublicFormat .SubjectPublicKeyInfo ,
    )

    private_path =_safe_path (base ,'jwt_private.pem')
    public_path =_safe_path (base ,'jwt_public.pem')

    with open (private_path ,'wb')as f :
        f .write (private_pem )
    os .chmod (private_path ,0o600 )

    with open (public_path ,'wb')as f :
        f .write (public_pem )
    os .chmod (public_path ,0o644 )

    print (f"✅ Private key: {private_path } (mode 600)")
    print (f"✅ Public key:  {public_path } (mode 644)")

    return private_path ,public_path 


def generate_self_signed_cert (output_dir ='certs',common_name ='securemed.local'):
    """Generate self-signed TLS certificate for PostgreSQL SSL connection."""
    if not common_name or any(c.isspace() for c in common_name):
        raise ValueError("common_name must be a non-empty single-label hostname")
    base =_resolve_output_dir (output_dir )
    print (f"\n🔒 Generating self-signed TLS certificate for '{common_name }'...")

    private_key =rsa .generate_private_key (
    public_exponent =65537 ,
    key_size =2048 ,
    )

    subject =issuer =x509 .Name ([
    x509 .NameAttribute (NameOID .COUNTRY_NAME ,"SA"),
    x509 .NameAttribute (NameOID .STATE_OR_PROVINCE_NAME ,"Riyadh"),
    x509 .NameAttribute (NameOID .LOCALITY_NAME ,"Riyadh"),
    x509 .NameAttribute (NameOID .ORGANIZATION_NAME ,"SecureMed"),
    x509 .NameAttribute (NameOID .COMMON_NAME ,common_name ),
    ])

    cert =(
    x509 .CertificateBuilder ()
    .subject_name (subject )
    .issuer_name (issuer )
    .public_key (private_key .public_key ())
    .serial_number (x509 .random_serial_number ())
    .not_valid_before (datetime .now (timezone .utc ))
    .not_valid_after (datetime .now (timezone .utc )+timedelta (days =365 ))
    .add_extension (
    x509 .SubjectAlternativeName ([
    x509 .DNSName (common_name ),
    x509 .DNSName ("localhost"),
    x509 .DNSName ("*.securemed.local"),
    x509 .IPAddress (__import__ ('ipaddress').ip_address ("127.0.0.1")),
    ]),
    critical =False ,
    )
    .add_extension (
    x509 .BasicConstraints (ca =True ,path_length =None ),
    critical =True ,
    )
    .sign (private_key ,hashes .SHA256 ())
    )

    cert_path =_safe_path (base ,'ca.pem')
    client_cert_path =_safe_path (base ,'client.pem')
    client_key_path =_safe_path (base ,'client-key.pem')

    with open (cert_path ,'wb')as f :
        f .write (cert .public_bytes (serialization .Encoding .PEM ))

    with open (client_cert_path ,'wb')as f :
        f .write (cert .public_bytes (serialization .Encoding .PEM ))

    with open (client_key_path ,'wb')as f :
        f .write (private_key .private_bytes (
        encoding =serialization .Encoding .PEM ,
        format =serialization .PrivateFormat .TraditionalOpenSSL ,
        encryption_algorithm =serialization .NoEncryption (),
        ))
    os .chmod (client_key_path ,0o600 )

    print (f"✅ CA cert:        {cert_path }")
    print (f"✅ Client cert:    {client_cert_path }")
    print (f"✅ Client key:     {client_key_path } (mode 600)")

    return cert_path ,client_cert_path ,client_key_path 


def generate_field_encryption_key (output_dir ='certs'):
    """Generate a 32-byte AES-256 key for field-level encryption."""
    import base64 
    print ("\n🔐 Generating AES-256 field encryption key...")
    base =_resolve_output_dir (output_dir )

    key =base64 .urlsafe_b64encode (os .urandom (32 )).decode ('utf-8')

    key_path =_safe_path (base ,'field_encryption_key.txt')
    with open (key_path ,'w')as f :
        f .write (key )
    os .chmod (key_path ,0o600 )

    print (f"✅ Encryption key: {key_path } (mode 600)")
    print (f"   Add this to .env:  ENCRYPTION_KEY={key }")

    return key 


def main ():
    parser =argparse .ArgumentParser (description ='SecureMed certificate generator')
    parser .add_argument ('--output-dir',default ='certs',help ='Output directory')
    parser .add_argument ('--cn',default ='securemed.local',help ='Common Name for cert')
    parser .add_argument ('--jwt-only',action ='store_true',help ='Generate only JWT keys')
    parser .add_argument ('--tls-only',action ='store_true',help ='Generate only TLS cert')
    args =parser .parse_args ()

    print ("="*60 )
    print ("  SecureMed Certificate Generator")
    print ("  Security requirements: #3 (Encrypted tokens) + #6 (TLS)")
    print ("="*60 )

    if not args .tls_only :
        try :
            generate_jwt_keypair (args .output_dir )
            generate_field_encryption_key (args .output_dir )
        except ValueError as exc :
            print (f"❌ Refusing to write outside the output directory: {exc }",file =sys .stderr )
            sys .exit (2 )

    if not args .jwt_only :
        try :
            generate_self_signed_cert (args .output_dir ,args .cn )
        except ValueError as exc :
            print (f"❌ Invalid certificate output or Common Name: {exc }",file =sys .stderr )
            sys .exit (2 )

    print ("\n"+"="*60 )
    print ("✅ All certificates generated successfully!")
    print ("="*60 )


if __name__ =='__main__':
    main ()
