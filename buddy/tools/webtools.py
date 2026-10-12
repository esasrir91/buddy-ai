import httpx
from urllib.parse import urlparse

from buddy.tools import Toolkit
from buddy.utils.log import logger


class WebTools(Toolkit):
    """
    A toolkit for working with web-related tools.
    """

    def __init__(self, retries: int = 3, **kwargs):
        if retries < 1:
            raise ValueError("retries must be greater than 0")
        super().__init__(name="web_tools", **kwargs)

        self.retries = retries

        self.register(self.expand_url)

    def expand_url(self, url: str) -> str:
        """
        Expands a shortened URL to its final destination using HTTP HEAD requests with retries.

        :param url: The URL to expand.

        :return: The final destination URL if successful; otherwise, returns the original URL.
        """
        parsed_url = urlparse(url)
        if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
            return "Error: URL must be an absolute HTTP or HTTPS URL"

        timeout = 5
        for attempt in range(1, self.retries + 1):
            try:
                response = httpx.head(url, follow_redirects=True, timeout=timeout)
                final_url = response.url
                logger.info(f"expand_url: {url} expanded to {final_url} on attempt {attempt}")
                return str(final_url)
            except Exception as e:
                logger.error(f"Error expanding URL {url} on attempt {attempt}: {e}")

        return url
