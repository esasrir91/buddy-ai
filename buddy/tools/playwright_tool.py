"""
Playwright tool for web automation and testing.
Provides browser automation capabilities with support for multiple browsers.
Uses synchronous API to avoid event loop conflicts.
"""

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

try:
    from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright

    playwright_available = True
except ImportError:
    playwright_available = False

from buddy.tools.toolkit import Toolkit
from buddy.utils.log import logger


class PlaywrightTools(Toolkit):
    """
    Playwright toolkit for web automation, testing, and scraping.
    Supports Chrome, Firefox, Safari, and Edge browsers.
    Uses synchronous API for better integration.
    """

    def __init__(
        self,
        browser_type: str = "chromium",  # chromium, firefox, webkit
        headless: bool = True,
        timeout: int = 30000,  # 30 seconds
        viewport: Optional[Dict[str, int]] = None,
        user_agent: Optional[str] = None,
        **kwargs,
    ):
        if not playwright_available:
            raise ImportError(
                "Playwright is not installed. Install it with: pip install playwright && playwright install"
            )

        self.browser_type = browser_type
        self.headless = headless
        self.timeout = timeout
        self.viewport = viewport or {"width": 1280, "height": 720}
        self.user_agent = user_agent

        # Use sync API
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None

        super().__init__(
            name="playwright_tools",
            tools=[
                self.start_browser,
                self.navigate_to_page,
                self.click_element,
                self.fill_input,
                self.find_element,
                self.find_elements,
                self.get_text_content,
                self.get_page_html,
                self.get_page_title,
                self.take_screenshot,
                self.wait_for_element,
                self.execute_javascript,
                self.get_element_attributes,
                self.submit_form,
                self.scroll_page,
                self.close_browser,
            ],
            **kwargs,
        )

    def _ensure_browser(self):
        """Ensure browser is running using sync API."""
        if self._playwright is None:
            self._playwright = sync_playwright().start()

        if self._browser is None:
            if self.browser_type == "chromium":
                self._browser = self._playwright.chromium.launch(headless=self.headless)
            elif self.browser_type == "firefox":
                self._browser = self._playwright.firefox.launch(headless=self.headless)
            elif self.browser_type == "webkit":
                self._browser = self._playwright.webkit.launch(headless=self.headless)
            else:
                raise ValueError(f"Unsupported browser type: {self.browser_type}")

        if self._context is None:
            context_options = {"viewport": self.viewport}
            if self.user_agent:
                context_options["user_agent"] = self.user_agent
            self._context = self._browser.new_context(**context_options)

        if self._page is None:
            self._page = self._context.new_page()
            self._page.set_default_timeout(self.timeout)

    def start_browser(self) -> str:
        """
        Start the web browser.

        Returns:
            Browser startup status
        """
        try:
            if self._browser is not None:
                return "Browser is already running"

            self._ensure_browser()

            return json.dumps(
                {
                    "status": "success",
                    "message": f"{self.browser_type.title()} browser started successfully",
                    "headless": self.headless,
                    "window_size": self.viewport,
                }
            )

        except Exception as e:
            logger.error(f"Error starting browser: {e}")
            return f"Error starting browser: {e}"

    def navigate_to_page(self, url: str) -> str:
        """Navigate to a webpage."""
        try:
            self._ensure_browser()
            self._page.goto(url)
            title = self._page.title()
            return f"Successfully navigated to '{title}' at {url}"
        except Exception as e:
            logger.error(f"Error navigating to {url}: {e}")
            return f"Error navigating to {url}: {e}"

    def click_element(self, locator_type: str, locator_value: str) -> str:
        """Click on an element."""
        try:
            self._ensure_browser()
            selector = self._get_selector(locator_type, locator_value)
            if "Error:" in selector:
                return selector
            self._page.locator(selector).click()
            return f"Successfully clicked element: {locator_type}='{locator_value}'"
        except Exception as e:
            logger.error(f"Error clicking element: {e}")
            return f"Error clicking element: {e}"

    def fill_input(self, locator_type: str, locator_value: str, text: str) -> str:
        """Fill an input field with text."""
        try:
            self._ensure_browser()
            selector = self._get_selector(locator_type, locator_value)
            if "Error:" in selector:
                return selector
            self._page.locator(selector).fill(text)
            return f"Successfully filled '{locator_type}={locator_value}' with text: {text}"
        except Exception as e:
            logger.error(f"Error filling input: {e}")
            return f"Error filling input: {e}"

    def find_element(self, locator_type: str, locator_value: str) -> str:
        """Find a single element on the page."""
        try:
            self._ensure_browser()
            selector = self._get_selector(locator_type, locator_value)
            if "Error:" in selector:
                return selector

            locator = self._page.locator(selector)
            if locator.count() == 0:
                return f"Element not found: {locator_type}='{locator_value}'"

            element = locator.first
            return json.dumps(
                {
                    "status": "success",
                    "message": "Element found",
                    "tag_name": element.evaluate("el => el.tagName"),
                    "text": element.text_content() or "",
                    "is_visible": element.is_visible(),
                    "is_enabled": element.is_enabled(),
                    "bounding_box": element.bounding_box(),
                }
            )
        except Exception as e:
            logger.error(f"Error finding element: {e}")
            return f"Error finding element: {e}"

    def find_elements(self, locator_type: str, locator_value: str) -> str:
        """Find multiple elements on the page."""
        try:
            self._ensure_browser()
            selector = self._get_selector(locator_type, locator_value)
            if "Error:" in selector:
                return selector

            locator = self._page.locator(selector)
            count = locator.count()

            if count == 0:
                return json.dumps({"status": "success", "message": "No elements found", "count": 0, "elements": []})

            elements_info = []
            for i in range(min(count, 10)):  # Limit to first 10 elements
                element = locator.nth(i)
                elements_info.append(
                    {
                        "index": i,
                        "tag_name": element.evaluate("el => el.tagName"),
                        "text": (element.text_content() or "")[:100],  # Truncate long text
                        "is_visible": element.is_visible(),
                        "bounding_box": element.bounding_box(),
                    }
                )

            return json.dumps(
                {"status": "success", "message": f"Found {count} elements", "count": count, "elements": elements_info}
            )
        except Exception as e:
            logger.error(f"Error finding elements: {e}")
            return f"Error finding elements: {e}"

    def get_text_content(self, locator_type: str, locator_value: str) -> str:
        """Get text content of an element."""
        try:
            self._ensure_browser()
            selector = self._get_selector(locator_type, locator_value)
            if "Error:" in selector:
                return selector
            locator = self._page.locator(selector)
            if locator.count() == 0:
                return f"Element not found: {locator_type}='{locator_value}'"
            return locator.first.text_content() or ""
        except Exception as e:
            logger.error(f"Error getting text content: {e}")
            return f"Error getting text content: {e}"

    def get_page_html(self, selector: Optional[str] = None) -> str:
        """Get HTML content of the page or specific element."""
        try:
            self._ensure_browser()
            if selector:
                locator = self._page.locator(selector)
                if locator.count() == 0:
                    return f"Element not found: {selector}"
                return locator.first.inner_html()
            return self._page.content()
        except Exception as e:
            logger.error(f"Error getting HTML: {e}")
            return f"Error getting HTML: {e}"

    def get_page_title(self) -> str:
        """Get the title of the current page."""
        try:
            self._ensure_browser()
            return self._page.title()
        except Exception as e:
            logger.error(f"Error getting page title: {e}")
            return f"Error getting page title: {e}"

    def take_screenshot(self, path: Optional[str] = None, full_page: bool = False) -> str:
        """Take a screenshot of the current page."""
        try:
            self._ensure_browser()
            screenshot_path = path or f"screenshot_{int(time.time())}.png"
            self._page.screenshot(path=screenshot_path, full_page=full_page)
            return f"Screenshot saved to: {screenshot_path}"
        except Exception as e:
            logger.error(f"Error taking screenshot: {e}")
            return f"Error taking screenshot: {e}"

    def wait_for_element(self, locator_type: str, locator_value: str, timeout: Optional[int] = None) -> str:
        """Wait for an element to appear on the page."""
        try:
            self._ensure_browser()
            selector = self._get_selector(locator_type, locator_value)
            if "Error:" in selector:
                return selector
            wait_timeout = timeout or self.timeout
            self._page.wait_for_selector(selector, timeout=wait_timeout)
            return f"Element appeared: {locator_type}='{locator_value}'"
        except Exception as e:
            logger.error(f"Error waiting for element: {e}")
            return f"Error waiting for element: {e}"

    def execute_javascript(self, script: str) -> str:
        """Execute JavaScript code on the page."""
        try:
            self._ensure_browser()
            result = self._page.evaluate(script)
            return str(result) if result is not None else "Script executed successfully"
        except Exception as e:
            logger.error(f"Error executing JavaScript: {e}")
            return f"Error executing JavaScript: {e}"

    def get_element_attributes(self, locator_type: str, locator_value: str, attributes: List[str]) -> str:
        """Get attributes of an element."""
        try:
            self._ensure_browser()
            selector = self._get_selector(locator_type, locator_value)
            if "Error:" in selector:
                return selector
            locator = self._page.locator(selector)
            if locator.count() == 0:
                return f"Element not found: {locator_type}='{locator_value}'"

            attrs = {}
            element = locator.first
            for attr in attributes:
                value = element.get_attribute(attr)
                attrs[attr] = value
            return json.dumps(attrs, indent=2)
        except Exception as e:
            logger.error(f"Error getting element attributes: {e}")
            return f"Error getting element attributes: {e}"

    def submit_form(self, locator_type: str, locator_value: str) -> str:
        """Submit a form."""
        try:
            self._ensure_browser()
            selector = self._get_selector(locator_type, locator_value)
            if "Error:" in selector:
                return selector
            self._page.locator(selector).press("Enter")
            return f"Form submitted: {locator_type}='{locator_value}'"
        except Exception as e:
            logger.error(f"Error submitting form: {e}")
            return f"Error submitting form: {e}"

    def scroll_page(self, direction: str = "down", pixels: int = 500) -> str:
        """Scroll the page."""
        try:
            self._ensure_browser()
            script_map = {
                "down": f"window.scrollBy(0, {pixels})",
                "up": f"window.scrollBy(0, -{pixels})",
                "right": f"window.scrollBy({pixels}, 0)",
                "left": f"window.scrollBy(-{pixels}, 0)",
            }

            if direction not in script_map:
                return f"Invalid direction: {direction}. Use 'up', 'down', 'left', or 'right'."

            self._page.evaluate(script_map[direction])
            return f"Scrolled {direction} by {pixels} pixels"
        except Exception as e:
            logger.error(f"Error scrolling page: {e}")
            return f"Error scrolling page: {e}"

    def close_browser(self) -> str:
        """Close the browser and cleanup resources."""
        try:
            if self._page:
                self._page.close()
                self._page = None
            if self._context:
                self._context.close()
                self._context = None
            if self._browser:
                self._browser.close()
                self._browser = None
            if self._playwright:
                self._playwright.stop()
                self._playwright = None
            return "Browser closed successfully"
        except Exception as e:
            logger.error(f"Error closing browser: {e}")
            return f"Error closing browser: {e}"

    def _get_selector(self, locator_type: str, locator_value: str) -> str:
        """Convert locator type and value to appropriate selector."""
        by_mapping = {
            "id": f"#{locator_value}",
            "name": f"[name='{locator_value}']",
            "class_name": f".{locator_value}",
            "tag_name": locator_value,
            "css_selector": locator_value,
            "xpath": f"xpath={locator_value}",
            "link_text": f"text={locator_value}",
            "partial_link_text": f"text*={locator_value}",
        }

        if locator_type not in by_mapping:
            return f"Error: Invalid locator type: {locator_type}"

        return by_mapping[locator_type]
