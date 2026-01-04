"""
Selenium tool for web automation and testing.
Provides comprehensive web browser automation capabilities.
"""

import time
import json
from typing import Any, Dict, List, Optional, Union
from pathlib import Path

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.common.action_chains import ActionChains
    from selenium.webdriver.support.ui import WebDriverWait, Select
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.firefox.options import Options as FirefoxOptions
    from selenium.webdriver.edge.options import Options as EdgeOptions
    from selenium.common.exceptions import (
        TimeoutException, NoSuchElementException, 
        WebDriverException, ElementNotInteractableException
    )
    selenium_available = True
except ImportError:
    selenium_available = False

from buddy.tools.toolkit import Toolkit
from buddy.utils.log import logger


class SeleniumTools(Toolkit):
    """
    Selenium toolkit for web automation and testing.
    
    Features:
    - Multi-browser support (Chrome, Firefox, Edge, Safari)
    - Element interaction and manipulation
    - Form handling and submission
    - Screenshot and video recording
    - Wait strategies and error handling
    - Mobile device emulation
    """

    def __init__(
        self,
        browser: str = "chrome",  # chrome, firefox, edge, safari
        headless: bool = False,
        implicit_wait: int = 10,
        page_load_timeout: int = 30,
        window_size: Optional[tuple] = None,
        user_agent: Optional[str] = None,
        download_dir: Optional[str] = None,
        **kwargs
    ):
        if not selenium_available:
            raise ImportError(
                "Selenium is not installed. Install with: pip install selenium"
            )
        
        self.browser = browser.lower()
        self.headless = headless
        self.implicit_wait = implicit_wait
        self.page_load_timeout = page_load_timeout
        self.window_size = window_size or (1920, 1080)
        self.user_agent = user_agent
        self.download_dir = download_dir
        
        self.driver = None
        self.wait = None

        super().__init__(
            name="selenium_tools",
            tools=[
                self.start_browser,
                self.navigate_to,
                self.find_element,
                self.find_elements,
                self.click_element,
                self.send_keys_to_element,
                self.get_element_text,
                self.get_element_attribute,
                self.get_page_source,
                self.get_page_title,
                self.take_screenshot,
                self.execute_javascript,
                self.wait_for_element,
                self.select_dropdown_option,
                self.switch_to_frame,
                self.switch_to_window,
                self.handle_alert,
                self.scroll_to_element,
                self.drag_and_drop,
                self.close_browser,
                self.get_cookies,
                self.set_cookie,
                self.clear_cookies,
                self.refresh_page,
                self.go_back,
                self.go_forward,
            ],
            **kwargs,
        )

    def _setup_driver_options(self):
        """Setup browser-specific options."""
        if self.browser == "chrome":
            options = ChromeOptions()
            if self.headless:
                options.add_argument("--headless")
            options.add_argument(f"--window-size={self.window_size[0]},{self.window_size[1]}")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            
            if self.user_agent:
                options.add_argument(f"--user-agent={self.user_agent}")
            
            if self.download_dir:
                prefs = {"download.default_directory": str(Path(self.download_dir).absolute())}
                options.add_experimental_option("prefs", prefs)
                
            return options
            
        elif self.browser == "firefox":
            options = FirefoxOptions()
            if self.headless:
                options.add_argument("--headless")
            
            if self.user_agent:
                options.set_preference("general.useragent.override", self.user_agent)
            
            if self.download_dir:
                options.set_preference("browser.download.dir", str(Path(self.download_dir).absolute()))
                options.set_preference("browser.download.folderList", 2)
                
            return options
            
        elif self.browser == "edge":
            options = EdgeOptions()
            if self.headless:
                options.add_argument("--headless")
            options.add_argument(f"--window-size={self.window_size[0]},{self.window_size[1]}")
            
            if self.user_agent:
                options.add_argument(f"--user-agent={self.user_agent}")
                
            return options
            
        return None

    def start_browser(self) -> str:
        """
        Start the web browser.
        
        Returns:
            Browser startup status
        """
        try:
            if self.driver is not None:
                return "Browser is already running"
            
            options = self._setup_driver_options()
            
            if self.browser == "chrome":
                self.driver = webdriver.Chrome(options=options)
            elif self.browser == "firefox":
                self.driver = webdriver.Firefox(options=options)
            elif self.browser == "edge":
                self.driver = webdriver.Edge(options=options)
            elif self.browser == "safari":
                self.driver = webdriver.Safari()
            else:
                return f"Unsupported browser: {self.browser}"
            
            # Set timeouts
            self.driver.implicitly_wait(self.implicit_wait)
            self.driver.set_page_load_timeout(self.page_load_timeout)
            
            # Set window size
            if not self.headless:
                self.driver.set_window_size(*self.window_size)
            
            # Initialize WebDriverWait
            self.wait = WebDriverWait(self.driver, 10)
            
            return json.dumps({
                'status': 'success',
                'message': f'{self.browser.title()} browser started successfully',
                'headless': self.headless,
                'window_size': self.window_size
            })
            
        except Exception as e:
            logger.error(f"Error starting browser: {e}")
            return f"Error starting browser: {e}"

    def navigate_to(self, url: str) -> str:
        """
        Navigate to a URL.
        
        Args:
            url: URL to navigate to
            
        Returns:
            Navigation status
        """
        try:
            if self.driver is None:
                return "Error: Browser not started. Please start browser first."
            
            self.driver.get(url)
            title = self.driver.title
            current_url = self.driver.current_url
            
            return json.dumps({
                'status': 'success',
                'message': f'Navigated to {url}',
                'title': title,
                'current_url': current_url
            })
            
        except Exception as e:
            logger.error(f"Error navigating to {url}: {e}")
            return f"Error navigating to {url}: {e}"

    def find_element(self, locator_type: str, locator_value: str) -> str:
        """
        Find a single element on the page.
        
        Args:
            locator_type: Type of locator (id, name, class_name, tag_name, css_selector, xpath)
            locator_value: Value of the locator
            
        Returns:
            Element information or error message
        """
        try:
            if self.driver is None:
                return "Error: Browser not started."
            
            by_mapping = {
                'id': By.ID,
                'name': By.NAME,
                'class_name': By.CLASS_NAME,
                'tag_name': By.TAG_NAME,
                'css_selector': By.CSS_SELECTOR,
                'xpath': By.XPATH,
                'link_text': By.LINK_TEXT,
                'partial_link_text': By.PARTIAL_LINK_TEXT
            }
            
            if locator_type not in by_mapping:
                return f"Invalid locator type: {locator_type}"
            
            element = self.driver.find_element(by_mapping[locator_type], locator_value)
            
            return json.dumps({
                'status': 'success',
                'message': 'Element found',
                'tag_name': element.tag_name,
                'text': element.text,
                'is_displayed': element.is_displayed(),
                'is_enabled': element.is_enabled(),
                'location': element.location,
                'size': element.size
            })
            
        except NoSuchElementException:
            return f"Element not found: {locator_type}='{locator_value}'"
        except Exception as e:
            logger.error(f"Error finding element: {e}")
            return f"Error finding element: {e}"

    def find_elements(self, locator_type: str, locator_value: str) -> str:
        """
        Find multiple elements on the page.
        
        Args:
            locator_type: Type of locator
            locator_value: Value of the locator
            
        Returns:
            List of elements information
        """
        try:
            if self.driver is None:
                return "Error: Browser not started."
            
            by_mapping = {
                'id': By.ID,
                'name': By.NAME,
                'class_name': By.CLASS_NAME,
                'tag_name': By.TAG_NAME,
                'css_selector': By.CSS_SELECTOR,
                'xpath': By.XPATH,
                'link_text': By.LINK_TEXT,
                'partial_link_text': By.PARTIAL_LINK_TEXT
            }
            
            if locator_type not in by_mapping:
                return f"Invalid locator type: {locator_type}"
            
            elements = self.driver.find_elements(by_mapping[locator_type], locator_value)
            
            elements_info = []
            for i, element in enumerate(elements):
                elements_info.append({
                    'index': i,
                    'tag_name': element.tag_name,
                    'text': element.text[:100],  # Truncate long text
                    'is_displayed': element.is_displayed(),
                    'location': element.location
                })
            
            return json.dumps({
                'status': 'success',
                'message': f'Found {len(elements)} elements',
                'count': len(elements),
                'elements': elements_info
            })
            
        except Exception as e:
            logger.error(f"Error finding elements: {e}")
            return f"Error finding elements: {e}"

    def click_element(self, locator_type: str, locator_value: str) -> str:
        """
        Click on an element.
        
        Args:
            locator_type: Type of locator
            locator_value: Value of the locator
            
        Returns:
            Click status
        """
        try:
            if self.driver is None:
                return "Error: Browser not started."
            
            by_mapping = {
                'id': By.ID,
                'name': By.NAME,
                'class_name': By.CLASS_NAME,
                'tag_name': By.TAG_NAME,
                'css_selector': By.CSS_SELECTOR,
                'xpath': By.XPATH,
                'link_text': By.LINK_TEXT,
                'partial_link_text': By.PARTIAL_LINK_TEXT
            }
            
            element = self.driver.find_element(by_mapping[locator_type], locator_value)
            element.click()
            
            return f"Successfully clicked element: {locator_type}='{locator_value}'"
            
        except ElementNotInteractableException:
            return f"Element not interactable: {locator_type}='{locator_value}'"
        except NoSuchElementException:
            return f"Element not found: {locator_type}='{locator_value}'"
        except Exception as e:
            logger.error(f"Error clicking element: {e}")
            return f"Error clicking element: {e}"

    def send_keys_to_element(self, locator_type: str, locator_value: str, text: str, clear_first: bool = True) -> str:
        """
        Send keys to an input element.
        
        Args:
            locator_type: Type of locator
            locator_value: Value of the locator
            text: Text to send
            clear_first: Whether to clear the field first
            
        Returns:
            Send keys status
        """
        try:
            if self.driver is None:
                return "Error: Browser not started."
            
            by_mapping = {
                'id': By.ID,
                'name': By.NAME,
                'class_name': By.CLASS_NAME,
                'tag_name': By.TAG_NAME,
                'css_selector': By.CSS_SELECTOR,
                'xpath': By.XPATH
            }
            
            element = self.driver.find_element(by_mapping[locator_type], locator_value)
            
            if clear_first:
                element.clear()
            
            element.send_keys(text)
            
            return f"Successfully sent keys to element: {locator_type}='{locator_value}'"
            
        except Exception as e:
            logger.error(f"Error sending keys: {e}")
            return f"Error sending keys: {e}"

    def get_element_text(self, locator_type: str, locator_value: str) -> str:
        """Get text content of an element."""
        try:
            if self.driver is None:
                return "Error: Browser not started."
            
            by_mapping = {
                'id': By.ID,
                'name': By.NAME,
                'class_name': By.CLASS_NAME,
                'tag_name': By.TAG_NAME,
                'css_selector': By.CSS_SELECTOR,
                'xpath': By.XPATH
            }
            
            element = self.driver.find_element(by_mapping[locator_type], locator_value)
            return element.text
            
        except Exception as e:
            return f"Error getting element text: {e}"

    def get_element_attribute(self, locator_type: str, locator_value: str, attribute_name: str) -> str:
        """Get attribute value of an element."""
        try:
            if self.driver is None:
                return "Error: Browser not started."
            
            by_mapping = {
                'id': By.ID,
                'name': By.NAME,
                'class_name': By.CLASS_NAME,
                'tag_name': By.TAG_NAME,
                'css_selector': By.CSS_SELECTOR,
                'xpath': By.XPATH
            }
            
            element = self.driver.find_element(by_mapping[locator_type], locator_value)
            return element.get_attribute(attribute_name) or ""
            
        except Exception as e:
            return f"Error getting element attribute: {e}"

    def get_page_source(self) -> str:
        """Get the page source HTML."""
        try:
            if self.driver is None:
                return "Error: Browser not started."
            
            return self.driver.page_source
            
        except Exception as e:
            return f"Error getting page source: {e}"

    def get_page_title(self) -> str:
        """Get the page title."""
        try:
            if self.driver is None:
                return "Error: Browser not started."
            
            return self.driver.title
            
        except Exception as e:
            return f"Error getting page title: {e}"

    def take_screenshot(self, filename: Optional[str] = None) -> str:
        """Take a screenshot of the current page."""
        try:
            if self.driver is None:
                return "Error: Browser not started."
            
            if filename is None:
                filename = f"screenshot_{int(time.time())}.png"
            
            self.driver.save_screenshot(filename)
            return f"Screenshot saved as: {filename}"
            
        except Exception as e:
            return f"Error taking screenshot: {e}"

    def execute_javascript(self, script: str) -> str:
        """Execute JavaScript code."""
        try:
            if self.driver is None:
                return "Error: Browser not started."
            
            result = self.driver.execute_script(script)
            return str(result) if result is not None else "Script executed successfully"
            
        except Exception as e:
            return f"Error executing JavaScript: {e}"

    def wait_for_element(self, locator_type: str, locator_value: str, timeout: int = 10) -> str:
        """Wait for an element to be present."""
        try:
            if self.driver is None:
                return "Error: Browser not started."
            
            by_mapping = {
                'id': By.ID,
                'name': By.NAME,
                'class_name': By.CLASS_NAME,
                'tag_name': By.TAG_NAME,
                'css_selector': By.CSS_SELECTOR,
                'xpath': By.XPATH
            }
            
            wait = WebDriverWait(self.driver, timeout)
            element = wait.until(EC.presence_of_element_located((by_mapping[locator_type], locator_value)))
            
            return f"Element appeared: {locator_type}='{locator_value}'"
            
        except TimeoutException:
            return f"Timeout waiting for element: {locator_type}='{locator_value}'"
        except Exception as e:
            return f"Error waiting for element: {e}"

    def select_dropdown_option(self, locator_type: str, locator_value: str, option_value: str, by_value: bool = True) -> str:
        """Select an option from a dropdown."""
        try:
            if self.driver is None:
                return "Error: Browser not started."
            
            by_mapping = {
                'id': By.ID,
                'name': By.NAME,
                'class_name': By.CLASS_NAME,
                'tag_name': By.TAG_NAME,
                'css_selector': By.CSS_SELECTOR,
                'xpath': By.XPATH
            }
            
            element = self.driver.find_element(by_mapping[locator_type], locator_value)
            select = Select(element)
            
            if by_value:
                select.select_by_value(option_value)
            else:
                select.select_by_visible_text(option_value)
            
            return f"Selected option '{option_value}' from dropdown"
            
        except Exception as e:
            return f"Error selecting dropdown option: {e}"

    def switch_to_frame(self, frame_reference: Union[str, int]) -> str:
        """Switch to a frame or iframe."""
        try:
            if self.driver is None:
                return "Error: Browser not started."
            
            self.driver.switch_to.frame(frame_reference)
            return f"Switched to frame: {frame_reference}"
            
        except Exception as e:
            return f"Error switching to frame: {e}"

    def switch_to_window(self, window_handle: str) -> str:
        """Switch to a different window or tab."""
        try:
            if self.driver is None:
                return "Error: Browser not started."
            
            self.driver.switch_to.window(window_handle)
            return f"Switched to window: {window_handle}"
            
        except Exception as e:
            return f"Error switching to window: {e}"

    def handle_alert(self, action: str = "accept", text: Optional[str] = None) -> str:
        """Handle JavaScript alerts."""
        try:
            if self.driver is None:
                return "Error: Browser not started."
            
            alert = self.driver.switch_to.alert
            alert_text = alert.text
            
            if action == "accept":
                alert.accept()
                return f"Alert accepted. Text was: '{alert_text}'"
            elif action == "dismiss":
                alert.dismiss()
                return f"Alert dismissed. Text was: '{alert_text}'"
            elif action == "send_keys" and text:
                alert.send_keys(text)
                alert.accept()
                return f"Sent '{text}' to alert and accepted"
            else:
                return f"Invalid action: {action}. Use 'accept', 'dismiss', or 'send_keys'"
                
        except Exception as e:
            return f"Error handling alert: {e}"

    def scroll_to_element(self, locator_type: str, locator_value: str) -> str:
        """Scroll to an element."""
        try:
            if self.driver is None:
                return "Error: Browser not started."
            
            by_mapping = {
                'id': By.ID,
                'name': By.NAME,
                'class_name': By.CLASS_NAME,
                'tag_name': By.TAG_NAME,
                'css_selector': By.CSS_SELECTOR,
                'xpath': By.XPATH
            }
            
            element = self.driver.find_element(by_mapping[locator_type], locator_value)
            self.driver.execute_script("arguments[0].scrollIntoView();", element)
            
            return f"Scrolled to element: {locator_type}='{locator_value}'"
            
        except Exception as e:
            return f"Error scrolling to element: {e}"

    def drag_and_drop(self, source_locator_type: str, source_locator_value: str, 
                     target_locator_type: str, target_locator_value: str) -> str:
        """Perform drag and drop operation."""
        try:
            if self.driver is None:
                return "Error: Browser not started."
            
            by_mapping = {
                'id': By.ID,
                'name': By.NAME,
                'class_name': By.CLASS_NAME,
                'tag_name': By.TAG_NAME,
                'css_selector': By.CSS_SELECTOR,
                'xpath': By.XPATH
            }
            
            source = self.driver.find_element(by_mapping[source_locator_type], source_locator_value)
            target = self.driver.find_element(by_mapping[target_locator_type], target_locator_value)
            
            actions = ActionChains(self.driver)
            actions.drag_and_drop(source, target).perform()
            
            return f"Dragged element from {source_locator_value} to {target_locator_value}"
            
        except Exception as e:
            return f"Error performing drag and drop: {e}"

    def get_cookies(self) -> str:
        """Get all cookies."""
        try:
            if self.driver is None:
                return "Error: Browser not started."
            
            cookies = self.driver.get_cookies()
            return json.dumps(cookies, indent=2)
            
        except Exception as e:
            return f"Error getting cookies: {e}"

    def set_cookie(self, name: str, value: str, domain: Optional[str] = None) -> str:
        """Set a cookie."""
        try:
            if self.driver is None:
                return "Error: Browser not started."
            
            cookie_dict = {'name': name, 'value': value}
            if domain:
                cookie_dict['domain'] = domain
            
            self.driver.add_cookie(cookie_dict)
            return f"Cookie set: {name}={value}"
            
        except Exception as e:
            return f"Error setting cookie: {e}"

    def clear_cookies(self) -> str:
        """Clear all cookies."""
        try:
            if self.driver is None:
                return "Error: Browser not started."
            
            self.driver.delete_all_cookies()
            return "All cookies cleared"
            
        except Exception as e:
            return f"Error clearing cookies: {e}"

    def refresh_page(self) -> str:
        """Refresh the current page."""
        try:
            if self.driver is None:
                return "Error: Browser not started."
            
            self.driver.refresh()
            return "Page refreshed"
            
        except Exception as e:
            return f"Error refreshing page: {e}"

    def go_back(self) -> str:
        """Go back to the previous page."""
        try:
            if self.driver is None:
                return "Error: Browser not started."
            
            self.driver.back()
            return "Navigated back"
            
        except Exception as e:
            return f"Error going back: {e}"

    def go_forward(self) -> str:
        """Go forward to the next page."""
        try:
            if self.driver is None:
                return "Error: Browser not started."
            
            self.driver.forward()
            return "Navigated forward"
            
        except Exception as e:
            return f"Error going forward: {e}"

    def close_browser(self) -> str:
        """Close the browser and cleanup."""
        try:
            if self.driver is None:
                return "Browser is not running"
            
            self.driver.quit()
            self.driver = None
            self.wait = None
            
            return "Browser closed successfully"
            
        except Exception as e:
            return f"Error closing browser: {e}"
