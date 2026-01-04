import json
from typing import Any, Dict, List, Optional
from os import getenv

from buddy.tools import Toolkit
from buddy.utils.log import log_debug, logger

try:
    import requests
except ImportError:
    raise ImportError("`requests` not installed. Please install using `pip install requests`")


class IPGeolocationTools(Toolkit):
    def __init__(
        self,
        ipapi_key: Optional[str] = None,
        ipgeolocation_key: Optional[str] = None,
        **kwargs
    ):
        """Initialize IP Geolocation Tools.

        Args:
            ipapi_key (Optional[str]): ipapi.com API key
            ipgeolocation_key (Optional[str]): ipgeolocation.io API key
        """
        self.ipapi_key = ipapi_key or getenv("IPAPI_KEY")
        self.ipgeolocation_key = ipgeolocation_key or getenv("IPGEOLOCATION_KEY")
        
        tools: List[Any] = [
            self.get_ip_location,
            self.get_current_ip_location,
            self.bulk_ip_lookup,
            self.get_ip_security_info,
        ]

        super().__init__(name="ip_geolocation", tools=tools, **kwargs)

    def get_ip_location(self, ip_address: str, provider: str = "ipapi") -> str:
        """Get geolocation information for an IP address.

        Args:
            ip_address (str): IP address to lookup
            provider (str): Provider to use ('ipapi' or 'ipgeolocation')

        Returns:
            str: Geolocation data or error message
        """
        try:
            if provider == "ipapi":
                return self._get_ipapi_location(ip_address)
            elif provider == "ipgeolocation":
                return self._get_ipgeolocation_location(ip_address)
            else:
                return json.dumps({"error": "Unsupported provider"})
        except Exception as e:
            return json.dumps({"error": f"Failed to get IP location: {str(e)}"})

    def _get_ipapi_location(self, ip_address: str) -> str:
        """Get location using ipapi.com."""
        try:
            url = f"http://api.ipapi.com/{ip_address}"
            params = {}
            
            if self.ipapi_key:
                params["access_key"] = self.ipapi_key

            response = requests.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            return json.dumps({
                "ip": data.get("ip"),
                "country": data.get("country_name"),
                "country_code": data.get("country_code"),
                "region": data.get("region_name"),
                "city": data.get("city"),
                "latitude": data.get("latitude"),
                "longitude": data.get("longitude"),
                "timezone": data.get("time_zone", {}).get("id"),
                "isp": data.get("connection", {}).get("isp"),
                "provider": "ipapi"
            })
        except Exception as e:
            return json.dumps({"error": f"ipapi lookup failed: {str(e)}"})

    def _get_ipgeolocation_location(self, ip_address: str) -> str:
        """Get location using ipgeolocation.io."""
        try:
            url = "https://api.ipgeolocation.io/ipgeo"
            params = {"ip": ip_address}
            
            if self.ipgeolocation_key:
                params["apiKey"] = self.ipgeolocation_key

            response = requests.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            return json.dumps({
                "ip": data.get("ip"),
                "country": data.get("country_name"),
                "country_code": data.get("country_code2"),
                "region": data.get("state_prov"),
                "city": data.get("city"),
                "latitude": float(data.get("latitude", 0)),
                "longitude": float(data.get("longitude", 0)),
                "timezone": data.get("time_zone", {}).get("name"),
                "isp": data.get("isp"),
                "provider": "ipgeolocation"
            })
        except Exception as e:
            return json.dumps({"error": f"ipgeolocation lookup failed: {str(e)}"})

    def get_current_ip_location(self) -> str:
        """Get geolocation of current public IP.

        Returns:
            str: Current IP geolocation data or error message
        """
        try:
            # First get current public IP
            ip_response = requests.get("https://httpbin.org/ip")
            ip_response.raise_for_status()
            current_ip = ip_response.json()["origin"]
            
            # Then get location for that IP
            return self.get_ip_location(current_ip)
        except Exception as e:
            return json.dumps({"error": f"Failed to get current IP location: {str(e)}"})

    def bulk_ip_lookup(self, ip_addresses: List[str], provider: str = "ipapi") -> str:
        """Lookup multiple IP addresses.

        Args:
            ip_addresses (List[str]): List of IP addresses to lookup
            provider (str): Provider to use

        Returns:
            str: Bulk lookup results or error message
        """
        try:
            results = []
            
            for ip in ip_addresses:
                try:
                    location_result = self.get_ip_location(ip, provider)
                    location_data = json.loads(location_result)
                    results.append({
                        "ip": ip,
                        "status": "success",
                        "data": location_data
                    })
                except Exception as e:
                    results.append({
                        "ip": ip,
                        "status": "error",
                        "error": str(e)
                    })
            
            return json.dumps({"results": results})
        except Exception as e:
            return json.dumps({"error": f"Bulk lookup failed: {str(e)}"})

    def get_ip_security_info(self, ip_address: str) -> str:
        """Get security information about an IP address.

        Args:
            ip_address (str): IP address to check

        Returns:
            str: Security information or error message
        """
        try:
            if not self.ipgeolocation_key:
                return json.dumps({"error": "ipgeolocation API key required for security info"})

            url = "https://api.ipgeolocation.io/ipgeo"
            params = {
                "ip": ip_address,
                "apiKey": self.ipgeolocation_key,
                "fields": "security"
            }

            response = requests.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            security = data.get("security", {})
            
            return json.dumps({
                "ip": ip_address,
                "is_threat": security.get("is_threat"),
                "threat_types": security.get("threat_types", []),
                "is_bogon": security.get("is_bogon"),
                "is_cloud_provider": security.get("is_cloud_provider"),
                "is_tor": security.get("is_tor"),
                "is_proxy": security.get("is_proxy"),
                "is_anonymous": security.get("is_anonymous"),
                "is_known_attacker": security.get("is_known_attacker"),
                "is_known_abuser": security.get("is_known_abuser"),
                "is_spam": security.get("is_spam")
            })
        except Exception as e:
            return json.dumps({"error": f"Failed to get security info: {str(e)}"})