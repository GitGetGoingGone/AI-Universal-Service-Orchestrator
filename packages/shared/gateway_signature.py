"""Gateway request signing and verification for Exclusive Gateway handshake."""

import hashlib
import hmac
import time
from typing import Optional

# Allow 5 minutes clock skew for timestamp
GATEWAY_SIGNATURE_MAX_AGE_SECONDS = 300


def _body_hash(body: bytes) -> str:
    if not body:
        return ""
    return hashlib.sha256(body).hexdigest()


def sign_request(
    method: str,
    path: str,
    body: bytes,
    secret: str,
    timestamp: Optional[int] = None,
) -> tuple[str, int]:
    """
    Produce (signature, timestamp) for Gateway outbound request.
    payload = method + newline + path + newline + body_sha256 + newline + timestamp.
    """
    if not secret:
        return "", 0
    ts = timestamp or int(time.time())
    body_hex = _body_hash(body)
    payload = f"{method.upper()}\n{path}\n{body_hex}\n{ts}"
    sig = hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).digest()
    import base64
    return base64.b64encode(sig).decode("ascii"), ts


def sign_request_no_body(method: str, path: str, secret: str, timestamp: Optional[int] = None) -> tuple[str, int]:
    """Sign without body (for middleware that does not read body). Uses empty body hash."""
    return sign_request(method, path, b"", secret, timestamp=timestamp)


def verify_request(
    method: str,
    path: str,
    body: bytes,
    signature: str,
    secret: str,
    timestamp: Optional[int] = None,
) -> bool:
    """
    Verify X-Gateway-Signature. If timestamp provided, reject if too old.
    Returns True if signature is valid and (when timestamp given) within allowed age.
    """
    if not secret or not signature:
        return False
    if timestamp is not None:
        age = abs(int(time.time()) - int(timestamp))
        if age > GATEWAY_SIGNATURE_MAX_AGE_SECONDS:
            return False
    expected_sig, _ = sign_request(method, path, body, secret, timestamp=timestamp)
    return hmac.compare_digest(signature.strip(), expected_sig)


def verify_request_no_body(
    method: str, path: str, signature: str, secret: str, timestamp: Optional[int] = None
) -> bool:
    """Verify signature computed without body (empty body hash)."""
    return verify_request(method, path, b"", signature, secret, timestamp=timestamp)
