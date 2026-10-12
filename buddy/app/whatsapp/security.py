import hashlib
import hmac
import os
from typing import Optional


def is_development_mode() -> bool:
    """Check if the application is running in development mode."""
    return os.getenv("APP_ENV", "production").lower() == "development"


def get_app_secret() -> str:
    """
    Get the WhatsApp app secret from environment variables.
    """
    app_secret = os.getenv("WHATSAPP_APP_SECRET")

    if not app_secret:
        raise ValueError("WHATSAPP_APP_SECRET environment variable is not set in production mode")

    return app_secret


def validate_webhook_signature(payload: bytes, signature_header: Optional[str]) -> bool:
    """
    Validate the webhook payload using SHA256 signature.
    Signature validation can only be bypassed when explicitly enabled.

    Args:
        payload: The raw request payload bytes
        signature_header: The X-Hub-Signature-256 header value

    Returns:
        bool: True if signature is valid or in development mode, False otherwise
    """
    if is_development_mode() and os.getenv("WHATSAPP_ALLOW_UNSIGNED_WEBHOOKS", "false").lower() == "true":
        return True

    if not signature_header or not signature_header.startswith("sha256="):
        return False

    try:
        app_secret = get_app_secret()
    except ValueError:
        return False
    expected_signature = signature_header.split("sha256=")[1]

    # Calculate signature
    hmac_obj = hmac.new(app_secret.encode("utf-8"), payload, hashlib.sha256)
    calculated_signature = hmac_obj.hexdigest()

    # Compare signatures using constant-time comparison
    return hmac.compare_digest(calculated_signature, expected_signature)
