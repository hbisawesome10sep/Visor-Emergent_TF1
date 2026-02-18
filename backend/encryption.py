"""
AES-256-GCM field-level encryption for sensitive financial data.
Each user gets a unique data encryption key (DEK) encrypted with the master key.
"""
import os
import base64
import hashlib
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

MASTER_KEY = os.environ.get("ENCRYPTION_MASTER_KEY", "")


def _get_master_key_bytes() -> bytes:
    """Derive a 32-byte key from the master key string."""
    return hashlib.sha256(MASTER_KEY.encode()).digest()


def generate_user_dek() -> str:
    """Generate a random 256-bit data encryption key for a user, encrypted with master key."""
    raw_dek = AESGCM.generate_key(bit_length=256)
    master = _get_master_key_bytes()
    aesgcm = AESGCM(master)
    nonce = os.urandom(12)
    encrypted_dek = aesgcm.encrypt(nonce, raw_dek, None)
    return base64.b64encode(nonce + encrypted_dek).decode()


def _decrypt_user_dek(encrypted_dek_b64: str) -> bytes:
    """Decrypt a user's DEK using the master key."""
    raw = base64.b64decode(encrypted_dek_b64)
    nonce, ciphertext = raw[:12], raw[12:]
    master = _get_master_key_bytes()
    aesgcm = AESGCM(master)
    return aesgcm.decrypt(nonce, ciphertext, None)


def encrypt_field(plaintext: str, encrypted_dek_b64: str) -> str:
    """Encrypt a single field value using the user's DEK."""
    if not plaintext or not encrypted_dek_b64:
        return plaintext
    dek = _decrypt_user_dek(encrypted_dek_b64)
    aesgcm = AESGCM(dek)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), None)
    return "ENC:" + base64.b64encode(nonce + ciphertext).decode()


def decrypt_field(encrypted_value: str, encrypted_dek_b64: str) -> str:
    """Decrypt a single field value using the user's DEK."""
    if not encrypted_value or not encrypted_value.startswith("ENC:"):
        return encrypted_value
    if not encrypted_dek_b64:
        return encrypted_value
    raw = base64.b64decode(encrypted_value[4:])
    nonce, ciphertext = raw[:12], raw[12:]
    dek = _decrypt_user_dek(encrypted_dek_b64)
    aesgcm = AESGCM(dek)
    return aesgcm.decrypt(nonce, ciphertext, None).decode()


def encrypt_sensitive_fields(doc: dict, dek: str, fields: list) -> dict:
    """Encrypt specified fields in a document."""
    for field in fields:
        if field in doc and doc[field]:
            doc[field] = encrypt_field(str(doc[field]), dek)
    return doc


def decrypt_sensitive_fields(doc: dict, dek: str, fields: list) -> dict:
    """Decrypt specified fields in a document."""
    for field in fields:
        if field in doc and doc[field] and isinstance(doc[field], str) and doc[field].startswith("ENC:"):
            doc[field] = decrypt_field(doc[field], dek)
    return doc
