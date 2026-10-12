from typing import Any

import requests

from buddy.utils.log import log_warning


def get_location() -> dict[str, Any]:
    """Get approximate location using IP geolocation."""
    try:
        response = requests.get("https://api.ipify.org?format=json", timeout=5)
        ip = response.json()["ip"]
        response = requests.get(f"https://ipapi.co/{ip}/json/", timeout=5)
        if response.status_code == 200:
            data = response.json()
            return {"city": data.get("city"), "region": data.get("region"), "country": data.get("country_name")}
    except (KeyError, requests.RequestException, ValueError) as e:
        log_warning(f"Failed to get location: {e}")
    return {}
