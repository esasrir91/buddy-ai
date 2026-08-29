"""BrowserUseToolset – browser automation client toolset.

Mirrors Anthropic's ``browser_toolset_20260801`` client toolset but works
with **any LLM**.  Provides a rich set of browser control actions via
Playwright (preferred) or Selenium as a fallback.

Member tools:

* ``navigate``      – go to a URL
* ``screenshot``    – capture current page as image
* ``click``         – click an element by CSS selector or coordinates
* ``fill``          – fill a form field
* ``select_option`` – choose a dropdown option
* ``press_key``     – send a keyboard event
* ``scroll``        – scroll the page or an element
* ``get_page_text`` – extract visible text content
* ``find``          – locate elements by selector
* ``read_page``     – structured page content extraction
* ``new_tab``       – open a new browser tab
* ``switch_tab``    – switch between open tabs
* ``close_tab``     – close a tab
* ``execute_js``    – run JavaScript in the page

When using Claude, call ``to_anthropic_toolset()`` to emit the native
``browser_toolset_20260801`` declaration.

Usage::

    from buddy.tools.browser import BrowserUseToolset

    agent = Agent(model=..., tools=[BrowserUseToolset(headless=True)])
"""

from __future__ import annotations

import base64
import json
import logging
from typing import Any, Dict, List, Optional

from buddy.tools.toolkit import Toolkit

logger = logging.getLogger(__name__)

ANTHROPIC_TOOLSET_TYPE = "browser_toolset_20260801"


class BrowserUseToolset(Toolkit):
    """Control a web browser via Playwright or Selenium for web automation.

    Equivalent to Anthropic's ``browser_toolset_20260801`` client toolset.
    All operations target a shared browser instance.  Call ``navigate``
    first to open a page, then use the other tools to interact with it.

    Parameters
    ----------
    headless:
        Run the browser without a visible window.  Defaults to ``True``.
    browser:
        Browser to use: ``"chromium"`` (default), ``"firefox"``, or ``"webkit"``.
    timeout:
        Default action timeout in milliseconds.
    viewport_width / viewport_height:
        Browser window dimensions.
    user_agent:
        Custom user-agent string.
    enable_javascript:
        If ``False``, disable JavaScript in the page.
    allowed_domains:
        If set, restrict navigation to these domains.
    """

    ANTHROPIC_TOOLSET_TYPE = ANTHROPIC_TOOLSET_TYPE

    def __init__(
        self,
        headless: bool = True,
        browser: str = "chromium",
        timeout: int = 30_000,
        viewport_width: int = 1280,
        viewport_height: int = 800,
        user_agent: Optional[str] = None,
        enable_javascript: bool = True,
        allowed_domains: Optional[List[str]] = None,
        **kwargs: Any,
    ):
        self._headless = headless
        self._browser_type = browser
        self._timeout = timeout
        self._viewport = {"width": viewport_width, "height": viewport_height}
        self._user_agent = user_agent
        self._enable_js = enable_javascript
        self._allowed_domains = set(allowed_domains or [])

        # Lazy-initialised browser state
        self._playwright: Any = None
        self._browser_obj: Any = None
        self._context: Any = None
        self._pages: List[Any] = []
        self._active_idx: int = 0

        super().__init__(
            name="browser_use",
            tools=[
                self.navigate,
                self.screenshot,
                self.click,
                self.fill,
                self.select_option,
                self.press_key,
                self.scroll,
                self.get_page_text,
                self.find,
                self.read_page,
                self.new_tab,
                self.switch_tab,
                self.close_tab,
                self.execute_js,
            ],
            instructions=(
                "Use the browser tools to control a web browser. "
                "Start with navigate() to open a page, then use click/fill/select_option "
                "for interactions, screenshot() to verify the state, and get_page_text() "
                "or read_page() to extract content."
            ),
            **kwargs,
        )

    # ── browser lifecycle ────────────────────────────────────────────────────

    def _ensure_browser(self) -> None:
        if self._browser_obj is not None:
            return
        try:
            self._start_playwright()
        except ImportError:
            logger.warning("Playwright not installed. Falling back to Selenium.")
            self._start_selenium()

    def _start_playwright(self) -> None:
        from playwright.sync_api import sync_playwright  # type: ignore
        self._playwright = sync_playwright().__enter__()
        launcher = getattr(self._playwright, self._browser_type)
        self._browser_obj = launcher.launch(headless=self._headless)
        self._context = self._browser_obj.new_context(
            viewport=self._viewport,
            user_agent=self._user_agent,
            java_script_enabled=self._enable_js,
        )
        self._pages = [self._context.new_page()]
        self._active_idx = 0
        self._driver = None  # sentinel: using Playwright

    def _start_selenium(self) -> None:
        from selenium import webdriver  # type: ignore
        from selenium.webdriver.chrome.options import Options  # type: ignore

        opts = Options()
        if self._headless:
            opts.add_argument("--headless=new")
        opts.add_argument(f"--window-size={self._viewport['width']},{self._viewport['height']}")
        if self._user_agent:
            opts.add_argument(f"user-agent={self._user_agent}")
        self._driver = webdriver.Chrome(options=opts)
        self._browser_obj = "selenium"
        self._playwright = None

    @property
    def _page(self) -> Any:
        if self._browser_obj == "selenium":
            return self._driver
        if not self._pages:
            return None
        return self._pages[self._active_idx]

    def _check_domain(self, url: str) -> Optional[str]:
        if not self._allowed_domains:
            return None
        from urllib.parse import urlparse
        domain = urlparse(url).netloc
        if not any(domain.endswith(d) for d in self._allowed_domains):
            return json.dumps({"error": f"Domain '{domain}' is not in the allowed list."})
        return None

    def _b64_screenshot(self) -> str:
        if self._browser_obj == "selenium":
            return base64.b64encode(self._driver.get_screenshot_as_png()).decode()
        return base64.b64encode(self._page.screenshot()).decode()

    # ── tool methods ─────────────────────────────────────────────────────────

    def navigate(self, url: str, wait_until: str = "load") -> str:
        """Navigate the browser to the specified URL.

        Opens the URL in the current browser tab. The browser waits until
        the page reaches the specified load state before returning.

        Args:
            url: The URL to navigate to (must include http:// or https://).
            wait_until: Page load state to wait for: "load", "domcontentloaded",
                        or "networkidle".

        Returns:
            str: Confirmation with page title and final URL.
        """
        blocked = self._check_domain(url)
        if blocked:
            return blocked
        self._ensure_browser()
        try:
            if self._browser_obj == "selenium":
                self._driver.get(url)
                return json.dumps({"url": self._driver.current_url, "title": self._driver.title})
            self._page.goto(url, wait_until=wait_until, timeout=self._timeout)
            return json.dumps({"url": self._page.url, "title": self._page.title()})
        except Exception as exc:
            return json.dumps({"error": str(exc)})

    def screenshot(self, full_page: bool = False) -> str:
        """Capture the current page as a base64-encoded PNG image.

        Take a screenshot to see the current visual state of the browser.
        Use this after navigation or interactions to verify what happened.

        Args:
            full_page: If True, capture the entire scrollable page.

        Returns:
            str: JSON with base64-encoded PNG image data.
        """
        self._ensure_browser()
        try:
            if self._browser_obj == "selenium":
                data = base64.b64encode(self._driver.get_screenshot_as_png()).decode()
            else:
                data = base64.b64encode(self._page.screenshot(full_page=full_page)).decode()
            return json.dumps({"type": "image", "format": "png", "data": data})
        except Exception as exc:
            return json.dumps({"error": str(exc)})

    def click(self, selector: str, button: str = "left") -> str:
        """Click an element identified by a CSS selector.

        Scrolls the element into view if needed, then clicks it.

        Args:
            selector: CSS selector for the element to click.
            button: Mouse button: "left" (default), "right", or "middle".

        Returns:
            str: Confirmation message or error.
        """
        self._ensure_browser()
        try:
            if self._browser_obj == "selenium":
                from selenium.webdriver.common.by import By  # type: ignore
                el = self._driver.find_element(By.CSS_SELECTOR, selector)
                el.click()
            else:
                self._page.click(selector, button=button, timeout=self._timeout)
            return f"Clicked: {selector}"
        except Exception as exc:
            return json.dumps({"error": str(exc)})

    def fill(self, selector: str, value: str, clear_first: bool = True) -> str:
        """Fill a form input with the specified value.

        Focuses the element, optionally clears its current value, then types
        the new value. Works for text inputs, textareas, and contenteditable elements.

        Args:
            selector: CSS selector for the input element.
            value: The value to enter.
            clear_first: If True, clear any existing value before typing.

        Returns:
            str: Confirmation message or error.
        """
        self._ensure_browser()
        try:
            if self._browser_obj == "selenium":
                from selenium.webdriver.common.by import By  # type: ignore
                el = self._driver.find_element(By.CSS_SELECTOR, selector)
                if clear_first:
                    el.clear()
                el.send_keys(value)
            else:
                if clear_first:
                    self._page.fill(selector, value, timeout=self._timeout)
                else:
                    self._page.type(selector, value, timeout=self._timeout)
            return f"Filled '{selector}' with value."
        except Exception as exc:
            return json.dumps({"error": str(exc)})

    def select_option(self, selector: str, value: str) -> str:
        """Select an option from a dropdown (select element).

        Args:
            selector: CSS selector for the select element.
            value: The option value or visible text to select.

        Returns:
            str: Confirmation message or error.
        """
        self._ensure_browser()
        try:
            if self._browser_obj == "selenium":
                from selenium.webdriver.common.by import By  # type: ignore
                from selenium.webdriver.support.ui import Select  # type: ignore
                el = Select(self._driver.find_element(By.CSS_SELECTOR, selector))
                el.select_by_value(value)
            else:
                self._page.select_option(selector, value=value, timeout=self._timeout)
            return f"Selected '{value}' in '{selector}'."
        except Exception as exc:
            return json.dumps({"error": str(exc)})

    def press_key(self, key: str, selector: Optional[str] = None) -> str:
        """Press a keyboard key, optionally focused on a specific element.

        Args:
            key: Key name (e.g. "Enter", "Escape", "Tab", "ArrowDown").
            selector: Optional CSS selector to focus before pressing.

        Returns:
            str: Confirmation message or error.
        """
        self._ensure_browser()
        try:
            if self._browser_obj == "selenium":
                from selenium.webdriver.common.by import By  # type: ignore
                from selenium.webdriver.common.keys import Keys  # type: ignore
                key_map = {"Enter": Keys.ENTER, "Escape": Keys.ESCAPE, "Tab": Keys.TAB}
                k = key_map.get(key, key)
                el = (self._driver.find_element(By.CSS_SELECTOR, selector)
                      if selector else self._driver.find_element(By.TAG_NAME, "body"))
                el.send_keys(k)
            else:
                if selector:
                    self._page.focus(selector)
                self._page.keyboard.press(key)
            return f"Pressed key: '{key}'."
        except Exception as exc:
            return json.dumps({"error": str(exc)})

    def scroll(self, x: int = 0, y: int = 500, selector: Optional[str] = None) -> str:
        """Scroll the page or a specific element.

        Args:
            x: Horizontal scroll amount in pixels.
            y: Vertical scroll amount in pixels (positive = down).
            selector: Optional CSS selector of element to scroll within.

        Returns:
            str: Confirmation message or error.
        """
        self._ensure_browser()
        try:
            if self._browser_obj == "selenium":
                self._driver.execute_script(f"window.scrollBy({x}, {y});")
            else:
                if selector:
                    self._page.eval_on_selector(selector, f"el => el.scrollBy({x}, {y})")
                else:
                    self._page.evaluate(f"window.scrollBy({x}, {y})")
            return f"Scrolled by ({x}, {y})."
        except Exception as exc:
            return json.dumps({"error": str(exc)})

    def get_page_text(self, selector: str = "body") -> str:
        """Extract the visible text content of the page or a specific element.

        Returns all readable text, stripped of HTML tags. Use this to read
        article content, search results, or any text-based page content.

        Args:
            selector: CSS selector to limit extraction to a specific section.

        Returns:
            str: The visible text content (up to 50 000 characters).
        """
        self._ensure_browser()
        try:
            if self._browser_obj == "selenium":
                from selenium.webdriver.common.by import By  # type: ignore
                el = self._driver.find_element(By.CSS_SELECTOR, selector)
                text = el.text
            else:
                text = self._page.inner_text(selector)
            return text[:50_000] if len(text) > 50_000 else text
        except Exception as exc:
            return json.dumps({"error": str(exc)})

    def find(self, selector: str, attribute: Optional[str] = None) -> str:
        """Find elements matching a CSS selector.

        Returns details about all matching elements including their text,
        tag name, and optionally a specific attribute value.

        Args:
            selector: CSS selector to search for.
            attribute: Optional HTML attribute to extract (e.g. "href", "src").

        Returns:
            str: JSON list of matching element details.
        """
        self._ensure_browser()
        try:
            if self._browser_obj == "selenium":
                from selenium.webdriver.common.by import By  # type: ignore
                elements = self._driver.find_elements(By.CSS_SELECTOR, selector)
                results = []
                for el in elements[:20]:
                    info: Dict[str, Any] = {"tag": el.tag_name, "text": el.text[:200]}
                    if attribute:
                        info[attribute] = el.get_attribute(attribute)
                    results.append(info)
            else:
                handles = self._page.query_selector_all(selector)[:20]
                results = []
                for h in handles:
                    info = {
                        "tag": h.evaluate("el => el.tagName.toLowerCase()"),
                        "text": (h.inner_text() or "")[:200],
                    }
                    if attribute:
                        info[attribute] = h.get_attribute(attribute)
                    results.append(info)
            return json.dumps({"count": len(results), "elements": results})
        except Exception as exc:
            return json.dumps({"error": str(exc)})

    def read_page(self) -> str:
        """Extract structured information from the current page.

        Returns page title, URL, meta description, headings hierarchy,
        all links, and main text content in a structured format.

        Returns:
            str: JSON with structured page information.
        """
        self._ensure_browser()
        try:
            if self._browser_obj == "selenium":
                title = self._driver.title
                url = self._driver.current_url
                js = """
                return {
                    meta: document.querySelector('meta[name="description"]')?.content || '',
                    headings: Array.from(document.querySelectorAll('h1,h2,h3')).slice(0,20).map(h=>({tag:h.tagName,text:h.innerText})),
                    links: Array.from(document.querySelectorAll('a[href]')).slice(0,30).map(a=>({text:a.innerText,href:a.href})),
                    text: document.body?.innerText?.slice(0,5000) || ''
                }
                """
                data = self._driver.execute_script(js)
            else:
                title = self._page.title()
                url = self._page.url
                data = self._page.evaluate("""() => ({
                    meta: document.querySelector('meta[name="description"]')?.content || '',
                    headings: Array.from(document.querySelectorAll('h1,h2,h3')).slice(0,20).map(h=>({tag:h.tagName,text:h.innerText})),
                    links: Array.from(document.querySelectorAll('a[href]')).slice(0,30).map(a=>({text:a.innerText,href:a.href})),
                    text: document.body?.innerText?.slice(0,5000)||''
                })""")
            return json.dumps({"title": title, "url": url, **data})
        except Exception as exc:
            return json.dumps({"error": str(exc)})

    def new_tab(self, url: Optional[str] = None) -> str:
        """Open a new browser tab, optionally navigating to a URL.

        Args:
            url: Optional URL to open in the new tab.

        Returns:
            str: JSON with the new tab index and URL.
        """
        self._ensure_browser()
        try:
            if self._browser_obj == "selenium":
                self._driver.switch_to.new_window("tab")
                if url:
                    self._driver.get(url)
                idx = len(self._driver.window_handles) - 1
            else:
                page = self._context.new_page()
                self._pages.append(page)
                idx = len(self._pages) - 1
                self._active_idx = idx
                if url:
                    page.goto(url, timeout=self._timeout)
            return json.dumps({"tab_index": idx, "url": url or "about:blank"})
        except Exception as exc:
            return json.dumps({"error": str(exc)})

    def switch_tab(self, tab_index: int) -> str:
        """Switch to a different browser tab by index.

        Args:
            tab_index: Zero-based index of the tab to switch to.

        Returns:
            str: Confirmation with current URL.
        """
        self._ensure_browser()
        try:
            if self._browser_obj == "selenium":
                handles = self._driver.window_handles
                self._driver.switch_to.window(handles[tab_index])
                return json.dumps({"tab_index": tab_index, "url": self._driver.current_url})
            if tab_index < 0 or tab_index >= len(self._pages):
                return json.dumps({"error": f"Tab {tab_index} does not exist."})
            self._active_idx = tab_index
            return json.dumps({"tab_index": tab_index, "url": self._pages[tab_index].url})
        except Exception as exc:
            return json.dumps({"error": str(exc)})

    def close_tab(self, tab_index: Optional[int] = None) -> str:
        """Close a browser tab.

        Args:
            tab_index: Index of the tab to close. Defaults to the active tab.

        Returns:
            str: Confirmation message.
        """
        self._ensure_browser()
        try:
            idx = tab_index if tab_index is not None else self._active_idx
            if self._browser_obj == "selenium":
                handles = self._driver.window_handles
                self._driver.switch_to.window(handles[idx])
                self._driver.close()
                if self._driver.window_handles:
                    self._driver.switch_to.window(self._driver.window_handles[-1])
            else:
                if idx < len(self._pages):
                    self._pages[idx].close()
                    self._pages.pop(idx)
                    self._active_idx = max(0, min(self._active_idx, len(self._pages) - 1))
            return f"Closed tab {idx}."
        except Exception as exc:
            return json.dumps({"error": str(exc)})

    def execute_js(self, script: str) -> str:
        """Execute JavaScript in the current page context.

        Use for advanced interactions that aren't covered by other tools,
        such as triggering custom events or reading complex page state.

        Args:
            script: JavaScript code to execute.  Use ``return`` to get a value.

        Returns:
            str: The return value of the script (JSON-serialised).
        """
        self._ensure_browser()
        try:
            if self._browser_obj == "selenium":
                result = self._driver.execute_script(script)
            else:
                result = self._page.evaluate(script)
            return json.dumps({"result": result})
        except Exception as exc:
            return json.dumps({"error": str(exc)})

    def __del__(self) -> None:
        try:
            if self._browser_obj == "selenium" and self._driver:
                self._driver.quit()
            elif self._browser_obj and self._playwright:
                self._browser_obj.close()
                self._playwright.__exit__(None, None, None)
        except Exception:
            pass

    def to_anthropic_toolset(self, configs: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Return the native Anthropic browser-use toolset declaration."""
        entry: Dict[str, Any] = {"type": self.ANTHROPIC_TOOLSET_TYPE}
        if configs:
            entry["configs"] = configs
        return entry
