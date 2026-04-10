import base64
import hashlib
import hmac


def verify_stripe_signature(payload: bytes, signature: str, secret: str) -> bool:
    """
    Stripe sends a 'Stripe-Signature' header with format:
    t=<timestamp>,v1=<hex_digest>[,v1=...]
    For demo purposes we accept the simplified 'sha256=<hex>' format too.
    """
    try:
        mac = hmac.new(secret.encode(), payload, hashlib.sha256)
        expected = f"sha256={mac.hexdigest()}"
        # Handle both "sha256=xxx" and Stripe's "t=...,v1=xxx" formats
        if "v1=" in signature:
            parts = {p.split("=", 1)[0]: p.split("=", 1)[1] for p in signature.split(",") if "=" in p}
            timestamp = parts.get("t", "")
            v1_sig = parts.get("v1", "")
            signed_payload = f"{timestamp}.".encode() + payload
            mac2 = hmac.new(secret.encode(), signed_payload, hashlib.sha256)
            return hmac.compare_digest(v1_sig, mac2.hexdigest())
        return hmac.compare_digest(signature, expected)
    except Exception:
        return False


def verify_github_signature(payload: bytes, signature: str, secret: str) -> bool:
    """
    GitHub sends X-Hub-Signature-256 with format: sha256=<hex_digest>
    """
    try:
        mac = hmac.new(secret.encode(), payload, hashlib.sha256)
        expected = f"sha256={mac.hexdigest()}"
        return hmac.compare_digest(signature, expected)
    except Exception:
        return False


def verify_shopify_signature(payload: bytes, signature: str, secret: str) -> bool:
    """
    Shopify sends X-Shopify-Hmac-SHA256 as base64-encoded HMAC-SHA256.
    """
    try:
        mac = hmac.new(secret.encode(), payload, hashlib.sha256)
        expected = base64.b64encode(mac.digest()).decode()
        return hmac.compare_digest(signature, expected)
    except Exception:
        return False