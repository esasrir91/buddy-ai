import hashlib
import hmac
import time
from os import getenv

from fastapi import HTTPException

def verify_slack_signature(body: bytes, timestamp: str, slack_signature: str) -> bool:
    signing_secret = getenv("SLACK_SIGNING_SECRET")
    if not signing_secret:
        raise HTTPException(status_code=500, detail="SLACK_SIGNING_SECRET is not set")

    # Ensure the request timestamp is recent (e.g., to prevent replay attacks)
    try:
        if abs(time.time() - int(timestamp)) > 60 * 5:
            return False
        body_text = body.decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return False

    sig_basestring = f"v0:{timestamp}:{body_text}"
    my_signature = (
        "v0="
        + hmac.new(signing_secret.encode("utf-8"), sig_basestring.encode("utf-8"), hashlib.sha256).hexdigest()
    )

    return hmac.compare_digest(my_signature, slack_signature)
