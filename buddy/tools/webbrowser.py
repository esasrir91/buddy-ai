import webbrowser
from typing import Any, List
from urllib.parse import urlparse

from buddy.tools import Toolkit


class WebBrowserTools(Toolkit):
    """Tools for opening a page on the web browser"""

    def __init__(self, **kwargs):
        tools: List[Any] = []
        tools.append(self.open_page)

        super().__init__(name="webbrowser_tools", tools=tools, **kwargs)

    def open_page(self, url: str, new_window: bool = False) -> str:
        """Open a URL in a browser window
        Args:
            url (str): URL to open
            new_window (bool): If True, open in a new window, otherwise open in a new tab. Default is False.
        Returns:
            None
        """
        parsed_url = urlparse(url)
        if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
            return "Error: URL must be an absolute HTTP or HTTPS URL"
        try:
            opened = webbrowser.open_new(url) if new_window else webbrowser.open_new_tab(url)
            return "Browser opened successfully" if opened else "Error: browser could not open the URL"
        except Exception as e:
            return f"Error opening browser: {e}"
