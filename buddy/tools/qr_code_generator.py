import json
from os import getenv
from typing import Any, Dict, List, Optional

from buddy.tools import Toolkit
from buddy.utils.log import log_debug, logger

try:
    import requests
except ImportError:
    raise ImportError("`requests` not installed. Please install using `pip install requests`")


class QRCodeTools(Toolkit):
    def __init__(self, **kwargs):
        """Initialize QR Code Tools."""

        tools: List[Any] = [
            self.generate_qr_code,
            self.generate_qr_code_with_logo,
            self.read_qr_code,
        ]

        super().__init__(name="qr_code", tools=tools, **kwargs)

    def generate_qr_code(
        self, data: str, size: str = "200x200", format: str = "png", error_correction: str = "M"
    ) -> str:
        """Generate a QR code.

        Args:
            data (str): Data to encode in QR code
            size (str): Image size (e.g., "200x200")
            format (str): Image format (png, jpg, svg)
            error_correction (str): Error correction level (L, M, Q, H)

        Returns:
            str: QR code generation result or error message
        """
        try:
            # Using qr-server.com API for QR code generation
            params = {"size": size, "data": data, "format": format, "ecc": error_correction}

            response = requests.get("https://api.qrserver.com/v1/create-qr-code/", params=params)
            response.raise_for_status()

            return json.dumps(
                {
                    "success": "QR code generated successfully",
                    "url": response.url,
                    "data": data,
                    "size": size,
                    "format": format,
                }
            )
        except Exception as e:
            return json.dumps({"error": f"Failed to generate QR code: {str(e)}"})

    def generate_qr_code_with_logo(self, data: str, logo_url: str, size: str = "200x200") -> str:
        """Generate a QR code with logo.

        Args:
            data (str): Data to encode in QR code
            logo_url (str): URL of logo to embed
            size (str): Image size

        Returns:
            str: QR code generation result or error message
        """
        try:
            params = {"size": size, "data": data, "logo": logo_url}

            response = requests.get("https://api.qrserver.com/v1/create-qr-code/", params=params)
            response.raise_for_status()

            return json.dumps(
                {
                    "success": "QR code with logo generated successfully",
                    "url": response.url,
                    "data": data,
                    "logo_url": logo_url,
                }
            )
        except Exception as e:
            return json.dumps({"error": f"Failed to generate QR code with logo: {str(e)}"})

    def read_qr_code(self, image_url: str) -> str:
        """Read/decode a QR code from an image URL.

        Args:
            image_url (str): URL of the image containing QR code

        Returns:
            str: Decoded data or error message
        """
        try:
            params = {"fileurl": image_url}

            response = requests.get("https://api.qrserver.com/v1/read-qr-code/", params=params)
            response.raise_for_status()

            result = response.json()
            if result and len(result) > 0:
                symbol_data = result[0]
                if symbol_data.get("symbol"):
                    return json.dumps(
                        {
                            "success": "QR code decoded successfully",
                            "data": symbol_data["symbol"][0]["data"],
                            "error": symbol_data["symbol"][0].get("error"),
                        }
                    )

            return json.dumps({"error": "No QR code found in image"})
        except Exception as e:
            return json.dumps({"error": f"Failed to read QR code: {str(e)}"})
