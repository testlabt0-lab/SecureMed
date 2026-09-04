import json 
import base64 
import hashlib 
from cryptography .hazmat .primitives .asymmetric import rsa ,padding 
from cryptography .hazmat .primitives import hashes ,serialization 
from django .conf import settings 

class DigitalSignatureService :
    """
    Simulates a PKI (Public Key Infrastructure) service for digitally signing
    electronic prescriptions and medical reports to ensure non-repudiation and integrity.
    """

    @staticmethod 
    def generate_key_pair (password :str =None ):
        """Generates a new RSA key pair for a doctor."""
        private_key =rsa .generate_private_key (
        public_exponent =65537 ,
        key_size =2048 ,
        )
        public_key =private_key .public_key ()

        # Comment_409
        if password :
            encryption_algorithm =serialization .BestAvailableEncryption (password .encode ('utf-8'))
        else :
            encryption_algorithm =serialization .NoEncryption ()

        private_pem =private_key .private_bytes (
        encoding =serialization .Encoding .PEM ,
        format =serialization .PrivateFormat .PKCS8 ,
        encryption_algorithm =encryption_algorithm 
        )

        # Comment_410
        public_pem =public_key .public_bytes (
        encoding =serialization .Encoding .PEM ,
        format =serialization .PublicFormat .SubjectPublicKeyInfo 
        )

        return private_pem .decode ('utf-8'),public_pem .decode ('utf-8')

    @staticmethod 
    def sign_prescription (prescription_data :dict ,private_key_pem :str ,password :str =None )->str :
        """
        Signs the prescription data using the doctor's private key.
        Returns a base64 encoded signature.
        """
        # Comment_411
        canonical_data =json .dumps (prescription_data ,sort_keys =True ).encode ('utf-8')

        # Comment_412
        private_key =serialization .load_pem_private_key (
        private_key_pem .encode ('utf-8'),
        password =password .encode ('utf-8')if password else None ,
        )

        # Comment_413
        signature =private_key .sign (
        canonical_data ,
        padding .PSS (
        mgf =padding .MGF1 (hashes .SHA256 ()),
        salt_length =padding .PSS .MAX_LENGTH 
        ),
        hashes .SHA256 ()
        )

        return base64 .b64encode (signature ).decode ('utf-8')

    @staticmethod 
    def verify_prescription_signature (prescription_data :dict ,signature_b64 :str ,public_key_pem :str )->bool :
        """
        Verifies that the prescription was signed by the owner of the public key
        and that the data has not been tampered with.
        """
        try :
            canonical_data =json .dumps (prescription_data ,sort_keys =True ).encode ('utf-8')
            signature =base64 .b64decode (signature_b64 )

            public_key =serialization .load_pem_public_key (
            public_key_pem .encode ('utf-8')
            )

            public_key .verify (
            signature ,
            canonical_data ,
            padding .PSS (
            mgf =padding .MGF1 (hashes .SHA256 ()),
            salt_length =padding .PSS .MAX_LENGTH 
            ),
            hashes .SHA256 ()
            )
            return True 
        except Exception :
            return False 
