"""
AES-256-GCM decryption for LLM API keys.
Format: base64(iv_12bytes + ciphertext + tag_16bytes)
Must match apps/portal/lib/encrypt.ts encryption format.
"""

import base64
import hashlib
import os
import re

IV_LEN = 12
TAG_LEN = 16
ENC_PREFIX = "enc:"


def _get_key() -> bytes:
    raw = os.getenv("LLM_CONFIG_ENCRYPTION_KEY")
    if not raw or len(raw) < 16:
        raise ValueError("LLM_CONFIG_ENCRYPTION_KEY must be set (32+ chars) for decryption")
    if len(raw) == 64 and re.match(r"^[0-9a-fA-F]+$", raw):
        return bytes.fromhex(raw)
    if len(raw) == 44 and re.match(r"^[A-Za-z0-9+/=]+$", raw):
        b = base64.b64decode(raw)
        if len(b) == 32:
            return b
    return hashlib.sha256(raw.encode()).digest()


def decrypt_llm_key(ciphertext: str) -> str:
    """Decrypt ciphertext. If prefixed with 'enc:', decrypts; else returns as-is (plain)."""
    if not ciphertext:
        return ""
    if not ciphertext.startswith(ENC_PREFIX):
        return ciphertext
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    key = _get_key()
    buf = base64.b64decode(ciphertext[len(ENC_PREFIX) :])
    if len(buf) < IV_LEN + TAG_LEN:
        raise ValueError("Invalid encrypted payload")
    iv = buf[:IV_LEN]
    tag = buf[-TAG_LEN:]
    enc = buf[IV_LEN:-TAG_LEN]
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(iv, enc + tag, None).decode("utf8")
