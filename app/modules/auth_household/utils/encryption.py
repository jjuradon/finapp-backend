# app/modules/auth_household/utils/encryption.py
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# Standard AES-256 key size is 32 bytes
# In production, this key should come from settings / KMS.
# For now, we use a fallback static key for development consistency.
_DEV_KEY = b"32bytesdevkeyforencryption123456"


def encrypt_field(plaintext: str, key: bytes = _DEV_KEY) -> bytes:
    """Encrypts plaintext string using AES-256-GCM."""
    if not plaintext:
        return b""
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)  # GCM recommended nonce size is 12 bytes
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    return nonce + ciphertext


def decrypt_field(ciphertext: bytes, key: bytes = _DEV_KEY) -> str:
    """Decrypts ciphertext bytes using AES-256-GCM."""
    if not ciphertext:
        return ""
    aesgcm = AESGCM(key)
    nonce = ciphertext[:12]
    actual_ciphertext = ciphertext[12:]
    decrypted = aesgcm.decrypt(nonce, actual_ciphertext, None)
    return decrypted.decode("utf-8")
